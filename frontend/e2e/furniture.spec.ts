import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const ROOM = resolve(import.meta.dirname, '../../samples/rooms/WhatsApp Image 2026-09-28 at 10.04.07 (1).jpeg')

test('agregar muebles, arrastrar y girar', async ({ page }) => {
  test.setTimeout(120_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(ROOM)
  const editor = page.getByTestId('editor')
  await expect(editor).toBeVisible({ timeout: 90_000 })

  await page.getByRole('button', { name: /Sofá azul Edingburgh/ }).click()
  await expect(page.getByTestId('selected-panel')).toContainText('198 × 100 × 91 cm')
  await page.waitForTimeout(1500)
  await page.screenshot({ path: 'test-results/furniture-1-sofa.png' })

  // arrastrar el sofá hacia la izquierda y hacia atrás
  const box = (await editor.boundingBox())!
  const cx = box.x + box.width / 2
  const cy = box.y + box.height * 0.62
  await page.mouse.move(cx, cy)
  await page.mouse.down()
  await page.mouse.move(cx - 60, cy - 40, { steps: 8 })
  await page.mouse.up()
  await expect(page.getByTestId('save-status')).toHaveText('Cambios guardados', { timeout: 15_000 })

  await page.getByRole('button', { name: /Mesa de centro moderna/ }).click()
  await page.keyboard.press('q')
  await page.keyboard.press('q')
  await expect(page.getByTestId('selected-panel')).toContainText('Rotación: 30°')
  await page.waitForTimeout(2000)
  await page.screenshot({ path: 'test-results/furniture-2-mesa.png' })
})
