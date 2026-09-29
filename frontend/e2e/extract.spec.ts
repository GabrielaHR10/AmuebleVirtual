import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const TABLE = resolve(import.meta.dirname, '../../samples/furniture/MuebleAzulEdingburgh/medidasedingburgh.png')

test('la tabla de medidas prellena el formulario (o pide escribirlas)', async ({ page, request }) => {
  test.setTimeout(180_000)
  const status = await (await request.get('/api/scenes/vlm/status')).json()
  await page.goto('/catalogo')
  await page.locator('input[name="table_image"]').setInputFiles(TABLE)
  if (status.available) {
    await expect(page.getByTestId('extracted')).toBeVisible({ timeout: 150_000 })
    await expect(page.locator('input[name="width_cm"]')).toHaveValue('198')
    await expect(page.locator('input[name="depth_cm"]')).toHaveValue('100')
    await expect(page.locator('input[name="height_cm"]')).toHaveValue('91')
    await page.screenshot({ path: 'test-results/extract.png' })
  } else {
    await expect(page.getByText(/a mano/)).toBeVisible({ timeout: 20_000 })
  }
})
