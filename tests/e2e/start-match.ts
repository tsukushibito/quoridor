import type { Page } from '@playwright/test';
export async function startDefaultMatch(page: Page): Promise<void> {
  await page.locator('#startup-new-game').click();
  await page.locator('#dialog-start').click();
  await page.locator('#startup-dialog').waitFor({ state: 'hidden' });
}
export async function restartMatch(page: Page): Promise<void> {
  await page.locator(await page.locator('#result-dialog').isVisible() ? '#result-again' : '#restart-game').click();
  if (await page.locator('#restart-dialog').isVisible()) await page.locator('#restart-confirm').click();
}
