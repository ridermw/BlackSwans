// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('landing page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/BlackSwans/i);
  });

  test('nav links are present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.getByRole('link', { name: /home/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /period/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /multi.*index/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /cagr/i })).toBeVisible();
  });

  test('can navigate to period comparison', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /period/i }).click();
    await expect(page).toHaveURL(/#\/period-comparison/);
  });

  test('can navigate to multi-index', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /multi.*index/i }).click();
    await expect(page).toHaveURL(/#\/multi-index/);
  });

  test('can navigate to CAGR research', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /cagr/i }).click();
    await expect(page).toHaveURL(/#\/cagr/);
  });
});

test.describe('Landing Page', () => {
  test('shows hero section with key question', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toContainText(/black swan/i);
  });

  test('shows key statistics', async ({ page }) => {
    await page.goto('/');
    // Should show some key numbers
    await expect(page.locator('body')).toContainText(/12/); // 12 indices
  });

  test('has disclaimer footer', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toContainText(/not financial advice/i);
  });

  test('dark theme applied', async ({ page }) => {
    await page.goto('/');
    const bgColor = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });
    // Should be dark (rgb values low)
    expect(bgColor).toMatch(/rgb\(\s*\d{1,2},\s*\d{1,2},\s*\d{1,2}\s*\)/);
  });
});

test.describe('Period Comparison Page', () => {
  test('loads and shows period data', async ({ page }) => {
    await page.goto('/#/period-comparison');
    // Wait for data to load
    await page.waitForSelector('text=/pre|post|full/i', { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/period/i);
  });

  test('shows claim verdicts', async ({ page }) => {
    await page.goto('/#/period-comparison');
    await page.waitForSelector('text=/CONFIRMED/i', { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/CONFIRMED/i);
  });

  test('has CAGR chart', async ({ page }) => {
    await page.goto('/#/period-comparison');
    // Plotly charts render as SVG inside .js-plotly-plot
    await page.waitForSelector('.js-plotly-plot', { timeout: 15000 });
    const charts = await page.locator('.js-plotly-plot').count();
    expect(charts).toBeGreaterThanOrEqual(1);
  });
});

test.describe('Multi-Index Page', () => {
  test('loads and shows index table', async ({ page }) => {
    await page.goto('/#/multi-index');
    await page.waitForSelector('text=/S&P 500|Nikkei|FTSE/i', { timeout: 20000 });
  });

  test('shows multiple indices', async ({ page }) => {
    await page.goto('/#/multi-index');
    await page.waitForSelector('table', { timeout: 20000 });
    const rows = await page.locator('table tbody tr').count();
    expect(rows).toBeGreaterThanOrEqual(5);
  });

  test('has kurtosis data', async ({ page }) => {
    await page.goto('/#/multi-index');
    await page.waitForSelector('text=/kurtosis/i', { timeout: 20000 });
  });
});

test.describe('CAGR Research Page', () => {
  test('loads with default settings', async ({ page }) => {
    await page.goto('/#/cagr');
    await page.waitForSelector('text=/CAGR|miss.*best|impact/i', { timeout: 15000 });
  });

  test('shows scenario table', async ({ page }) => {
    await page.goto('/#/cagr');
    // Should show CAGR percentages
    await page.waitForSelector('text=/%/', { timeout: 15000 });
  });

  test('has interactive controls', async ({ page }) => {
    await page.goto('/#/cagr');
    // Should have a ticker selector or N days control
    const selects = await page.locator('select').count();
    const inputs = await page.locator('input').count();
    expect(selects + inputs).toBeGreaterThanOrEqual(1);
  });
});

test.describe('Responsive Design', () => {
  test('mobile viewport renders', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    // Nav should still be accessible
    await expect(page.locator('nav')).toBeVisible();
  });

  test('tablet viewport renders', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('invalid route shows content', async ({ page }) => {
    await page.goto('/#/nonexistent-page');
    // Should not crash — either redirect to home or show 404
    await expect(page.locator('body')).toBeVisible();
  });
});
