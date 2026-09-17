import { expect, test as base, type APIRequestContext, type Page } from '@playwright/test'

export const PASSWORD = 'e2e-password-123'

export type Account = { email: string; fullName: string; token: string }

function unique(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}@sparklewash.com`
}

function bearer(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` }
}

/** Each test gets its own business, so nothing depends on the demo data or on test order. */
export async function signUpOwner(request: APIRequestContext): Promise<Account> {
  const email = unique('owner')
  const response = await request.post('/api/auth/signup', {
    data: { email, business_name: 'E2E Car Wash', full_name: 'Olivia Owner', password: PASSWORD },
  })
  expect(response.status(), await response.text()).toBe(201)
  return { email, fullName: 'Olivia Owner', token: (await response.json()).access_token }
}

export async function addStaff(
  request: APIRequestContext,
  owner: Account,
  role: 'employee' | 'manager',
  fullName: string,
): Promise<Account> {
  const email = unique(role)
  const invited = await request.post('/api/team/invites', {
    data: { email, full_name: fullName, role },
    headers: bearer(owner.token),
  })
  expect(invited.status(), await invited.text()).toBe(201)

  const token = (await invited.json()).invite_url.split('/').pop()
  const accepted = await request.post(`/api/invites/${token}/accept`, {
    data: { full_name: fullName, password: PASSWORD },
  })
  expect(accepted.status(), await accepted.text()).toBe(200)
  return { email, fullName, token: (await accepted.json()).access_token }
}

export async function addZone(request: APIRequestContext, owner: Account): Promise<void> {
  const response = await request.post('/api/locations', {
    data: { name: 'Harbour St Car Wash', latitude: -33.87, longitude: 151.2, radius_m: 150 },
    headers: bearer(owner.token),
  })
  expect(response.status(), await response.text()).toBe(201)
}

export async function workAShift(request: APIRequestContext, staff: Account): Promise<void> {
  const fix = { latitude: -33.87, longitude: 151.2, accuracy_m: 10 }
  const started = await request.post('/api/shifts/start', { data: fix, headers: bearer(staff.token) })
  expect(started.status(), await started.text()).toBe(201)
  await request.post('/api/shifts/end', { data: fix, headers: bearer(staff.token) })
}

/**
 * Signs in through the API rather than the form. The refresh cookie lands in the browser context,
 * so the app restores the session on load exactly as it would for a returning user.
 */
export async function signIn(page: Page, account: Account): Promise<void> {
  await page.context().clearCookies()
  const response = await page.request.post('/api/auth/login', {
    data: { email: account.email, password: PASSWORD },
  })
  expect(response.status(), await response.text()).toBe(200)
}

type Fixtures = {
  owner: Account
  ownerPage: Page
}

export const test = base.extend<Fixtures>({
  // Set-up runs through the standalone `request` fixture, which has its own cookie jar. Using
  // page.request would sign the browser in as whoever was created last: accepting an invite
  // returns a session, and its cookie would replace the owner's.
  // The callback is named `provide`, not Playwright's usual `use`: lint reads a bare `use(...)`
  // as React's hook and rejects it here.
  owner: async ({ request }, provide) => {
    await provide(await signUpOwner(request))
  },
  ownerPage: async ({ page, owner }, provide) => {
    await signIn(page, owner)
    await provide(page)
  },
})

export { expect }

/** The design is mobile-first and the plan is explicit: nothing may scroll sideways. */
export async function expectNoSidewaysScroll(page: Page, label = ''): Promise<void> {
  const report = await page.evaluate(() => {
    const doc = document.documentElement
    const overflow = doc.scrollWidth - doc.clientWidth
    if (overflow <= 0) return { overflow, culprits: [] as string[] }

    // Naming what actually sticks out turns a failure into something fixable.
    const culprits = [...document.querySelectorAll('*')]
      .filter((element) => element.getBoundingClientRect().right > doc.clientWidth + 1)
      .slice(0, 6)
      .map((element) => {
        const classes = (element.getAttribute('class') ?? '').split(/\s+/).slice(0, 4).join('.')
        return `${element.tagName.toLowerCase()}${classes ? `.${classes}` : ''}`
      })
    return { overflow, culprits }
  })

  expect(
    report.overflow,
    `${label} scrolls sideways by ${report.overflow}px — widest: ${report.culprits.join('  |  ')}`,
  ).toBeLessThanOrEqual(0)
}
