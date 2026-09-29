import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const ROOM = resolve(import.meta.dirname, '../../samples/rooms/WhatsApp Image 2026-09-28 at 10.04.08 (2).jpeg')

test('interfaz del estudio con tres muebles, sombra y exposición', async ({ page }) => {
  test.setTimeout(120_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(ROOM)
  await expect(page.getByTestId('editor')).toBeVisible({ timeout: 90_000 })
  await page.getByPlaceholder('Buscar…').fill('sofá azul')
  await page.getByRole('button', { name: /Sofá azul Edingburgh/ }).click()
  await page.getByPlaceholder('Buscar…').fill('')
  await page.getByRole('combobox').filter({ hasText: 'Todas las categorías' }).selectOption('plant')
  await page.getByRole('button', { name: /Planta en matera/ }).click()
  await page.getByRole('combobox').filter({ hasText: 'Planta' }).selectOption('')
  await page.getByRole('button', { name: /Mesa de centro moderna/ }).click()
  await page.getByLabel(/Intensidad de sombra/).fill('0.5')
  await page.waitForTimeout(2000)
  await page.screenshot({ path: 'test-results/studio-ui.png' })
})
