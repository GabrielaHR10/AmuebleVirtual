import { expect, test } from '@playwright/test'

test('la página principal carga y conecta con el servidor', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Estudio Virtual — Santiago Muebles' })).toBeVisible()
  await expect(page.getByTestId('health')).toContainText('Servidor conectado')
  await expect(page.getByRole('button', { name: 'Subir foto' })).toBeVisible()
  await page.screenshot({ path: 'test-results/home.png' })
})
