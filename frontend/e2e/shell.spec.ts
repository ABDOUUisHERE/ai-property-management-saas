import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('shell, same-origin API and accessible empty state', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Bienvenue chez vous.');
  await expect(page.getByRole('status')).toHaveText('Connexion au service établie.');
  const audit = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(audit.violations).toEqual([]);
  await page.screenshot({ path: '../.local/p02-desktop.png', fullPage: true });
});

test('keyboard navigation and dialog restore focus', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByText('Aller au contenu')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('main')).toBeFocused();
  await page.getByRole('link', { name: 'Guide de bienvenue' }).click();
  await expect(page.getByRole('main')).toBeFocused();
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations,
  ).toEqual([]);
  const trigger = page.getByRole('button', { name: 'À propos' });
  await trigger.click();
  await expect(page.getByRole('button', { name: 'Fermer' })).toBeFocused();
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations,
  ).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Fermer' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
});

test('mobile shell has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: '../.local/p02-mobile.png', fullPage: true });
});
