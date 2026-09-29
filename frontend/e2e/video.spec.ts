import { existsSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const DIR = resolve(import.meta.dirname, '../../samples/videos')
const VIDEO = existsSync(DIR) ? readdirSync(DIR).find((f) => /\.(mp4|mov)$/i.test(f)) : undefined

test('video → fotogramas → amoblar uno en el Estudio', async ({ page }) => {
  test.skip(!VIDEO, 'No hay video en samples/videos/')
  test.setTimeout(300_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/video')
  await page.getByTestId('video-input').setInputFiles(resolve(DIR, VIDEO!))
  await expect(page.getByTestId('video-progress')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByTestId('keyframe').first()).toBeVisible({ timeout: 240_000 })
  expect(await page.getByTestId('keyframe').count()).toBeGreaterThanOrEqual(3)
  await page.getByRole('button', { name: 'Preparar fotogramas para amoblar' }).click()
  await expect(page.getByRole('button', { name: 'Amoblar este fotograma' }).first()).toBeVisible({ timeout: 120_000 })
  await expect(page.getByTestId('video-summary')).toContainText('techo')
  await page.screenshot({ path: 'test-results/video.png', fullPage: true })
  await page.getByRole('button', { name: 'Amoblar este fotograma' }).nth(2).click()
  await expect(page.getByTestId('editor')).toBeVisible({ timeout: 30_000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: 'test-results/video-editor.png' })
})
