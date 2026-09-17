import { addStaff, addZone, expect, expectNoSidewaysScroll, PASSWORD, signIn, test } from './fixtures'

test('signing in through the form lands on the dashboard', async ({ page, owner }) => {
  // Signing up left this context authenticated, and /login sends a signed-in user away.
  await page.context().clearCookies()
  await page.goto('/login')

  await page.getByLabel('Email').fill(owner.email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page).toHaveURL(/\/overview$/)
  await expect(page.getByRole('heading', { name: 'E2E Car Wash' })).toBeVisible()
})

test('a wrong password is refused without saying which half was wrong', async ({ page, owner }) => {
  await page.context().clearCookies()
  await page.goto('/login')

  await page.getByLabel('Email').fill(owner.email)
  await page.getByLabel('Password').fill('not-the-right-password')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByRole('alert')).toContainText(/not right/i)
  await expect(page).toHaveURL(/\/login$/)
})

test('an employee lands on their shift screen and cannot reach the owner pages', async ({ page, owner, request }) => {
  await addZone(request, owner)
  const eli = await addStaff(request, owner, 'employee', 'Eli Employee')
  await signIn(page, eli)

  await page.goto('/shift')
  await expect(page.getByRole('heading').first()).toBeVisible()

  for (const ownerOnly of ['/overview', '/team', '/payroll', '/timesheets']) {
    await page.goto(ownerOnly)
    // The guard sends them home rather than showing an empty owner screen.
    await expect(page).toHaveURL(/\/shift$/)
  }
})

test('a manager sees the team board but not the money', async ({ page, owner, request }) => {
  await addZone(request, owner)
  const marco = await addStaff(request, owner, 'manager', 'Marco Manager')
  await signIn(page, marco)

  await page.goto('/board')
  await expect(page.getByRole('heading', { name: 'Team' })).toBeVisible()

  await page.goto('/payroll')
  await expect(page).toHaveURL(/\/shift$/)
})

test('the employee screens do not scroll sideways', async ({ page, owner, request }) => {
  await addZone(request, owner)
  const eli = await addStaff(request, owner, 'employee', 'Eli Employee')
  await signIn(page, eli)

  for (const path of ['/shift', '/hours', '/availability', '/profile']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    await expectNoSidewaysScroll(page, path)
  }
})
