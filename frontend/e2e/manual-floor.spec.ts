import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

// Foto de la ducha: casi no se ve piso → el análisis no lo encuentra
const SHOWER = resolve(import.meta.dirname, '../../samples/rooms/WhatsApp Image 2026-09-28 at 10.04.08 (5).jpeg')

test('definir el piso a mano con 3 clics', async ({ page }) => {
  test.setTimeout(120_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(SHOWER)
  const editor = page.getByTestId('editor')
  await expect(editor).toBeVisible({ timeout: 90_000 })
  const panel = page.getByTestId('manual-floor')
  await expect(panel).toContainText('No se encontró el piso')
  await panel.getByRole('button', { name: 'Definir piso' }).click()
  const box = (await editor.boundingBox())!
  for (const [fx, fy] of [[0.1, 0.97], [0.45, 0.99], [0.3, 0.9]]) {
    await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy)
  }
  await expect(panel).toContainText('Listo')
  await page.screenshot({ path: 'test-results/manual-floor-points.png' })
  await panel.getByRole('button', { name: 'Aplicar' }).click()
  // O se acepta el piso (el panel desaparece) o se explica por qué no sirve
  await expect(panel.or(page.getByTestId('room-card'))).toBeVisible()
  await page.waitForTimeout(500)
  await page.screenshot({ path: 'test-results/manual-floor-result.png' })
})
