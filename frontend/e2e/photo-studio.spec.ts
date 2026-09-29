import { statSync } from 'node:fs'
import { readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

// PLAN 2.10: subir la primera foto, agregar 2 muebles, mover uno, exportar → PNG > 50 KB
const ROOMS = resolve(import.meta.dirname, '../../samples/rooms')
const FIRST = resolve(ROOMS, readdirSync(ROOMS).filter((f) => /\.(jpe?g|png)$/i.test(f)).sort()[0])

test('flujo completo: subir, amoblar y exportar PNG', async ({ page }) => {
  test.setTimeout(150_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(FIRST)
  const editor = page.getByTestId('editor')
  await expect(editor).toBeVisible({ timeout: 90_000 })

  await page.getByRole('button', { name: /Sofá cama click-clack/ }).click()
  const box = (await editor.boundingBox())!
  const cx = box.x + box.width / 2
  const cy = box.y + box.height * 0.62
  await page.waitForTimeout(800)
  await page.mouse.move(cx, cy)
  await page.mouse.down()
  await page.mouse.move(cx - 30, cy - 18, { steps: 8 })
  await page.mouse.up()
  await page.getByRole('button', { name: /Mesa de centro redonda/ }).click()
  await page.waitForTimeout(2000)
  await page.screenshot({ path: 'test-results/photo-studio.png' })

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar PNG' }).click()
  const file = await download
  const out = 'test-results/amoblado_e2e.png'
  await file.saveAs(out)
  expect(file.suggestedFilename()).toMatch(/^amoblado_\d{8}_\d{4}\.png$/)
  expect(statSync(out).size).toBeGreaterThan(50_000)

  const maskDl = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Máscara de muebles' }).click()
  await (await maskDl).saveAs('test-results/mascara_e2e.png')
})
