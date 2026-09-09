import { expect, test } from '@playwright/test';

// Backend isn't running in this environment, so these cover what's verifiable purely
// client-side: routing/guard behavior and zod validation. Once the FastAPI auth router
// exists, extend this file with a real login → dashboard flow.

test('unauthenticated visitor is redirected from a protected route to /login', async ({
  page,
}) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible();
});

test('login form shows validation errors on empty submit', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Log in' }).click();

  await expect(page.getByText('Enter a valid email address')).toBeVisible();
  await expect(page.getByText('Password is required')).toBeVisible();
});

test('navigating between login, register, and forgot-password works', async ({
  page,
}) => {
  await page.goto('/login');
  await page.getByRole('link', { name: 'Register' }).click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(
    page.getByRole('heading', { name: 'Create account' }),
  ).toBeVisible();

  await page.getByRole('link', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByRole('link', { name: 'Forgot password' }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await expect(
    page.getByRole('heading', { name: 'Reset password' }),
  ).toBeVisible();
});
