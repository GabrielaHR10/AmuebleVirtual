import { expect, test } from '@playwright/test'

test('la página principal carga, conecta con el servidor y muestra el lienzo 3D', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Estudio Virtual — Santiago Muebles' })).toBeVisible()
  await expect(page.getByTestId('health')).toContainText('Servidor conectado')
  await expect(page.locator('canvas')).toBeVisible()
  await page.waitForTimeout(500)
  await page.screenshot({ path: 'test-results/home.png' })
})
