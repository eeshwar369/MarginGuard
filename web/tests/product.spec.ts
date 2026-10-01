import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const artifacts = path.resolve('../artifacts');
test('judge journey: evidence, counterfactual, approval, correction, stale record', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await fs.mkdir(artifacts, { recursive: true });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Explore the live workspace' })).toBeEnabled();
  await page.screenshot({ path: path.join(artifacts, '01-landing.png'), fullPage: true });
  await page.getByRole('button', { name: 'Explore the live workspace' }).click();
  await expect(
    page.getByRole('heading', { name: 'See the story behind your margin.' }),
  ).toBeVisible();
  await expect(page.getByText('₹1,33,515', { exact: true }).first()).toBeVisible();
  await page.screenshot({ path: path.join(artifacts, '02-overview.png'), fullPage: true });
  await page.getByRole('button', { name: /Discounts increased/ }).click();
  await expect(page.getByRole('dialog', { name: 'Evidence explorer' })).toBeVisible();
  await expect(page.getByText('616 matching ledger rows')).toBeVisible();
  await page.getByLabel('Search source rows').fill('L09-0001');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  // Search is literal and returns only matching identifiers; an empty result is explicit.
  await expect(page.getByText('No matching rows.')).toBeVisible();
  await page.getByLabel('Search source rows').fill('TEE-01');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.locator('.evidence-table tbody tr').first()).toBeVisible();
  await page.screenshot({ path: path.join(artifacts, '03-evidence.png'), fullPage: true });
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Investigations', exact: true })
    .click();
  await page.getByLabel('Business question').fill('Did discounts decrease?');
  await page.getByRole('button', { name: 'Run investigation' }).click();
  await expect(page.getByText('Hypothesis: discount decreased · contradicted')).toBeVisible();
  await expect(page.getByText('complete', { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(artifacts, '04-investigation.png'), fullPage: true });
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Decision lab', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Reduce shipping cost', exact: true }),
  ).toBeVisible();
  await page.getByLabel('Maximum extra return cost per order').fill('20');
  await expect(
    page.getByRole('heading', { name: 'Keep current policy', exact: true }),
  ).toBeVisible();
  await page.getByLabel('Maximum extra return cost per order').fill('4');
  await expect(
    page.getByRole('heading', { name: 'Reduce shipping cost', exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: path.join(artifacts, '05-decision-lab.png'), fullPage: true });
  await page.getByRole('button', { name: 'Create decision memo' }).click();
  await page.getByRole('button', { name: 'Review and approve' }).click();
  await expect(page.getByRole('button', { name: 'Approve decision', exact: true })).toBeDisabled();
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Approve decision', exact: true }).click();
  await expect(page.getByText(/Approved by Demo reviewer/)).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'PDF', exact: true }).click();
  const download = await downloadPromise;
  await download.saveAs(path.join(artifacts, 'sample-approved-memo.pdf'));
  await page.screenshot({ path: path.join(artifacts, '06-approved-memo.png'), fullPage: true });
  await page.getByRole('navigation').getByRole('button', { name: 'Overview', exact: true }).click();
  await page.getByRole('button', { name: /Discounts increased/ }).click();
  const line = (await page
    .locator('.evidence-table tbody tr')
    .first()
    .locator('td')
    .first()
    .locator('strong')
    .textContent())!;
  await page.getByRole('button', { name: /Found an incorrect cost/ }).click();
  await page.getByLabel('Order line ID', { exact: true }).fill(line);
  await page.getByLabel('Product cost (₹)', { exact: true }).fill('950');
  await page.getByLabel('Shipping cost (₹)', { exact: true }).fill('68');
  await page
    .getByLabel('Reason for correction')
    .fill('Updated supplier invoice after reconciliation');
  await page.getByRole('button', { name: 'Create corrected version' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Data v2' })).toBeVisible();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Decision memos', exact: true })
    .click();
  await expect(page.getByText('stale', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Review and approve' })).toHaveCount(0);
  await page.screenshot({ path: path.join(artifacts, '07-stale-memo.png'), fullPage: true });
  await page.getByRole('navigation').getByRole('button', { name: 'Activity', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Audit history' })).toBeVisible();
  await expect(page.locator('.audit-event')).not.toHaveCount(0);
  expect(errors).toEqual([]);
});
test('quality gate: duplicate quarantine blocks decisions until acknowledged', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore the live workspace' }).click();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Data sources', exact: true })
    .click();
  await page.getByRole('button', { name: 'Load quality challenge' }).click();
  await expect(page.getByRole('button', { name: 'Acknowledge quarantine' })).toBeVisible();
  await page.screenshot({ path: path.join(artifacts, '08-quality-gate.png'), fullPage: true });
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Decision lab', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Your data needs a quick review.' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Open data sources' }).click();
  await page.getByRole('button', { name: 'Acknowledge quarantine' }).click();
  await expect(
    page.getByText('Quarantine acknowledged. Issue history remains available.'),
  ).toBeVisible();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Decision lab', exact: true })
    .click();
  await expect(page.getByRole('button', { name: 'Create decision memo' })).toBeEnabled();
});
test('mobile navigation and dashboard fit a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore the live workspace' }).click();
  await expect(
    page.getByRole('heading', { name: 'See the story behind your margin.' }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: path.join(artifacts, '09-mobile.png'), fullPage: true });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Data sources', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Good decisions start with clean inputs.' }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
