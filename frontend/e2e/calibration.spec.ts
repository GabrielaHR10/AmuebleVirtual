import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const ROOM = resolve(import.meta.dirname, '../../samples/rooms/WhatsApp Image 2026-09-28 at 10.04.07 (1).jpeg')

test('calibrar medida con dos clics en el piso', async ({ page }) => {
  test.setTimeout(120_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(ROOM)
  const editor = page.getByTestId('editor')
  await expect(editor).toBeVisible({ timeout: 90_000 })
  const panel = page.getByTestId('calibration')
  await expect(panel).toContainText('actual: 1.000')

  await panel.getByRole('button', { name: 'Calibrar medida' }).click()
  const box = (await editor.boundingBox())!
  await page.mouse.click(box.x + box.width * 0.25, box.y + box.height * 0.85)
  await page.mouse.click(box.x + box.width * 0.75, box.y + box.height * 0.85)
  await expect(page.getByText(/cm en la foto/)).toBeVisible()
  await page.screenshot({ path: 'test-results/calibration.png' })
  const measured = Number((await page.getByText(/cm en la foto/).innerText()).match(/\d+/)![0])

  await panel.getByPlaceholder('cm').fill(String(Math.round(measured * 1.1)))
  await panel.getByRole('button', { name: 'Aplicar' }).click()
  const k = Number((await panel.innerText()).match(/actual: ([\d.]+)/)![1])
  expect(k).toBeGreaterThan(0.88)
  expect(k).toBeLessThan(0.94) // ≈ 1 / 1.1
  await expect(page.getByTestId('room-card')).toContainText('calibrada')
})
