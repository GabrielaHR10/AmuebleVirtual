import { copyFileSync, mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '@playwright/test'

// Genera los 3 PNG de ejemplo del 🛑 de la Fase 2. Solo corre con ENTREGA=1 (no es parte de la suite normal).
const ROOMS = resolve(import.meta.dirname, '../../samples/rooms')
const OUT = resolve(import.meta.dirname, '../test-results/entrega-fase2')

const CASES: { photo: string; items: RegExp[]; name: string }[] = [
  { photo: 'WhatsApp Image 2026-09-28 at 10.04.07 (1).jpeg', name: '1_sala', items: [/Sofá azul Edingburgh/, /Mesa de centro moderna/, /Planta en matera/] },
  { photo: 'WhatsApp Image 2026-09-28 at 10.04.08 (1).jpeg', name: '2_estudio', items: [/Sofá cama click-clack/, /Sillón moderno/] },
  { photo: 'WhatsApp Image 2026-09-28 at 10.04.08 (2).jpeg', name: '3_alcoba', items: [/Mueble bajo de madera/, /Sillón mid-century/] },
]

async function amoblar(page: Page, c: (typeof CASES)[number]) {
  await page.goto('/')
  await page.getByTestId('upload-input').setInputFiles(resolve(ROOMS, c.photo))
  await expect(page.getByTestId('editor')).toBeVisible({ timeout: 90_000 })
  if ((await page.getByLabel('Cuadrícula 1 m').isChecked())) await page.getByLabel('Cuadrícula 1 m').click()
  for (const item of c.items) {
    await page.getByRole('button', { name: item }).click()
    await page.waitForTimeout(600)
  }
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/${c.name}_editor.png` })
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar PNG' }).click()
  await (await download).saveAs(`${OUT}/${c.name}_amoblado.png`)
  copyFileSync(resolve(ROOMS, c.photo), `${OUT}/${c.name}_original.jpg`)
}

test('entrega fase 2: 3 fotos amobladas', async ({ page }) => {
  test.skip(!process.env.ENTREGA, 'Solo para generar la entrega (ENTREGA=1)')
  test.setTimeout(300_000)
  mkdirSync(OUT, { recursive: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  for (const c of CASES) await amoblar(page, c)
})
