import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const ROOM = resolve(import.meta.dirname, '../../samples/rooms/WhatsApp Image 2026-09-28 at 10.04.07 (1).jpeg')

test('subir una foto muestra el editor con la cuadrícula y las medidas estimadas', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(ROOM)
  await expect(page.getByTestId('editor')).toBeVisible({ timeout: 90_000 })
  await expect(page.getByTestId('room-card')).toContainText('Área visible')
  await page.waitForTimeout(1500) // HDRI y malla de oclusión
  await page.screenshot({ path: 'test-results/editor-grid.png' })
})
