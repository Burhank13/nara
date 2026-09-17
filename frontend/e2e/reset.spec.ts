import { expect, expectNoSidewaysScroll, test } from './fixtures'

// The token half of this flow is covered by the backend suite. Reading a real token in the
// browser would mean an endpoint that hands out reset tokens, which is not worth shipping.

test('asking for a link says the same thing whoever you are', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/forgot')

  await page.getByLabel('Email').fill('definitely-nobody@sparklewash.com')
  await page.getByRole('button', { name: 'Email me a link' }).click()

  await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible()
  await expectNoSidewaysScroll(page, '/forgot')
})

test('a dead link says so instead of asking for a password', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/reset/not-a-real-token')

  await expect(page.getByRole('heading', { name: 'This link has expired' })).toBeVisible()
  await expect(page.getByLabel('New password')).toBeHidden()
  await expectNoSidewaysScroll(page, '/reset')
})

test('the sign-in screen offers the way out', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/login')

  await page.getByRole('link', { name: 'Forgot your password?' }).click()

  await expect(page).toHaveURL(/\/forgot$/)
  await expect(page.getByRole('heading', { name: 'Forgot your password?' })).toBeVisible()
})
