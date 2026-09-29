import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const ROOM = resolve(import.meta.dirname, '../../samples/rooms/WhatsApp Image 2026-09-28 at 10.04.07 (1).jpeg')

test('sugerir ubicación muestra fantasmas y se pueden aceptar', async ({ page }) => {
  test.setTimeout(120_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(ROOM)
  await expect(page.getByTestId('editor')).toBeVisible({ timeout: 90_000 })
  if (await page.getByLabel('Cuadrícula 1 m').isChecked()) await page.getByLabel('Cuadrícula 1 m').click()
  for (const name of [/Sofá azul Edingburgh/, /Mesa de centro moderna/, /Planta en matera/]) {
    await page.getByRole('button', { name }).click()
  }
  await page.waitForTimeout(1500)
  await page.screenshot({ path: 'test-results/suggest-0-antes.png' })

  const panel = page.getByTestId('suggest-panel')
  await panel.getByRole('button', { name: 'Sugerir ubicación' }).click()
  await expect(page.getByTestId('ghost-item').first()).toBeVisible({ timeout: 30_000 })
  expect(await page.getByTestId('ghost-item').count()).toBeGreaterThanOrEqual(1)
  await page.waitForTimeout(1500)
  await page.screenshot({ path: 'test-results/suggest-1-fantasmas.png' })

  await panel.getByRole('button', { name: 'Aceptar todas' }).click()
  await expect(page.getByTestId('ghost-item')).toHaveCount(0)
  await page.waitForTimeout(1500)
  await page.screenshot({ path: 'test-results/suggest-2-aceptadas.png' })
})
