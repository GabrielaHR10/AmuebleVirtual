import { expect, test } from '@playwright/test'

test('el catálogo muestra los muebles con sus medidas', async ({ page }) => {
  await page.goto('/catalogo')
  await expect(page.getByRole('heading', { name: /Catálogo \(\d+\)/ })).toBeVisible()
  const cards = page.getByTestId('catalog-card')
  await expect(cards.first()).toBeVisible()
  expect(await cards.count()).toBeGreaterThanOrEqual(3)
  await expect(page.getByText('198 × 100 × 91 cm')).toBeVisible() // sofá azul Edingburgh
  await expect(page.getByText('Medidas sin verificar').first()).toBeVisible()
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: 'test-results/catalogo.png', fullPage: true })
})
