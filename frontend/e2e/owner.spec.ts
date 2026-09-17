import { addStaff, addZone, expect, expectNoSidewaysScroll, test, workAShift } from './fixtures'

const OWNER_PAGES = ['/overview', '/timesheets', '/payroll', '/team', '/zones', '/setup']

test('the dashboard loads with the business name and the headline numbers', async ({ ownerPage }) => {
  await ownerPage.goto('/overview')

  await expect(ownerPage.getByRole('heading', { name: 'E2E Car Wash' })).toBeVisible()
  await expect(ownerPage.getByText('Employees').first()).toBeVisible()
  await expect(ownerPage.getByText('On shift now').first()).toBeVisible()
  await expect(ownerPage.getByText('Team hours').first()).toBeVisible()
})

test('a brand new business is told what is left to set up', async ({ ownerPage }) => {
  await ownerPage.goto('/overview')

  await expect(ownerPage.getByText('Finish setting up')).toBeVisible()
  await ownerPage.getByRole('link', { name: 'Continue setup' }).click()

  await expect(ownerPage.getByRole('heading', { name: 'Set up your shop' })).toBeVisible()
})

test('every owner page opens straight from its URL', async ({ ownerPage }) => {
  // Regression: these paths are an API endpoint as well as a page, and used to answer with JSON.
  for (const path of OWNER_PAGES) {
    await ownerPage.goto(path)
    await expect(ownerPage.locator('body')).not.toContainText('"detail"')
    await expect(ownerPage.locator('main')).toBeVisible()
  }
})

test('no owner page scrolls sideways', async ({ ownerPage }) => {
  for (const path of OWNER_PAGES) {
    await ownerPage.goto(path)
    await ownerPage.waitForLoadState('networkidle')
    await expectNoSidewaysScroll(ownerPage, path)
  }
})

test('the timesheet lists a logged shift and opens the edit sheet', async ({ ownerPage, owner, request }) => {
  await addZone(request, owner)
  const eli = await addStaff(request, owner, 'employee', 'Eli Employee')
  await workAShift(request, eli)

  await ownerPage.goto('/timesheets')
  // Scoped to rows: the staff filter holds a hidden <option> with the same name.
  // Visible-only: the phone list and the desktop table both exist, one hidden by breakpoint.
  const row = ownerPage
    .locator('table tbody tr, ul li')
    .filter({ hasText: 'Eli Employee' })
    .filter({ visible: true })
    .first()
  await expect(row).toBeVisible()

  await ownerPage.getByRole('button', { name: 'Edit' }).first().click()

  await expect(ownerPage.getByRole('dialog')).toBeVisible()
  await expect(ownerPage.getByRole('heading', { name: 'Edit shift' })).toBeVisible()
  // The reason is what makes an edit auditable, so saving stays disabled until it is filled in.
  await expect(ownerPage.getByRole('button', { name: 'Save change' })).toBeDisabled()

  await ownerPage.getByLabel('Reason').fill('Forgot to clock in this morning')
  await expect(ownerPage.getByRole('button', { name: 'Save change' })).toBeEnabled()
})

test('payroll names anyone missing a code and saves the one you set', async ({ ownerPage, owner, request }) => {
  await addZone(request, owner)
  const eli = await addStaff(request, owner, 'employee', 'Eli Employee')
  await workAShift(request, eli)

  await ownerPage.goto('/payroll')

  await expect(ownerPage.getByRole('heading', { name: 'Payroll codes' })).toBeVisible()
  await expect(ownerPage.getByText(/No payroll code for/)).toContainText('Eli Employee')

  const field = ownerPage.getByLabel('Payroll code for Eli Employee')
  await field.fill('EMP-001')
  await ownerPage.getByRole('listitem').filter({ hasText: 'Eli Employee' }).getByRole('button').click()

  // The warning clears once the code is saved and the run is refetched.
  await expect(ownerPage.getByText(/No payroll code for/)).toBeHidden()
})

test('the team page shows the seat meter and the new starter', async ({ ownerPage, owner, request }) => {
  await addStaff(request, owner, 'employee', 'Eli Employee')

  await ownerPage.goto('/team')

  await expect(ownerPage.getByText('Eli Employee').first()).toBeVisible()
  await expect(ownerPage.getByText(/seat/i).first()).toBeVisible()
})
