import { copyFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '@playwright/test'

// 🛑 Fase 3: 3 ejemplos, muebles puestos a mano vs. sugerencia básica, con tiempos. Solo con ENTREGA=1.
const ROOMS = resolve(import.meta.dirname, '../../samples/rooms')
const OUT = resolve(import.meta.dirname, '../test-results/entrega-fase3')

const CASES = [
  { photo: 'WhatsApp Image 2026-09-28 at 10.04.07 (1).jpeg', name: '1_sala', items: [/Sofá azul Edingburgh/, /Mesa de centro moderna/, /Planta en matera/, /Sillón moderno/] },
  { photo: 'WhatsApp Image 2026-09-28 at 10.04.07.jpeg', name: '2_sala_desde_la_entrada', items: [/Sofá cama click-clack/, /Mesa de centro redonda/, /Planta en matera/] },
  { photo: 'WhatsApp Image 2026-09-28 at 10.04.08 (2).jpeg', name: '3_alcoba', items: [/Sofá cama click-clack/, /Mesa auxiliar/, /Planta en matera/] },
]

async function suggestAndExport(page: Page, name: string): Promise<number> {
  const panel = page.getByTestId('suggest-panel')
  const t0 = Date.now()
  await panel.getByRole('button', { name: 'Sugerir ubicación' }).click()
  await expect(panel.getByRole('button', { name: 'Aceptar todas' })).toBeVisible({ timeout: 200_000 })
  const seconds = (Date.now() - t0) / 1000
  const notes = await panel.locator('li').allInnerTexts()
  await panel.getByRole('button', { name: 'Aceptar todas' }).click()
  await page.waitForTimeout(2500)
  const dl = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar PNG' }).click()
  await (await dl).saveAs(`${OUT}/${name}.png`)
  writeFileSync(`${OUT}/${name}.txt`, `${seconds.toFixed(1)} s\n${notes.join('\n')}\n`)
  return seconds
}

test('entrega fase 3: a mano vs. sugerencia', async ({ page }) => {
  test.skip(!process.env.ENTREGA, 'Solo para generar la entrega (ENTREGA=1)')
  test.setTimeout(1_200_000)
  mkdirSync(OUT, { recursive: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  for (const c of CASES) {
    await page.goto('/')
    await page.getByTestId('upload-input').setInputFiles(resolve(ROOMS, c.photo))
    await expect(page.getByTestId('editor')).toBeVisible({ timeout: 90_000 })
    if (await page.getByLabel('Cuadrícula 1 m').isChecked()) await page.getByLabel('Cuadrícula 1 m').click()
    for (const item of c.items) await page.getByRole('button', { name: item }).click()
    await page.waitForTimeout(2500)
    const dl = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Exportar PNG' }).click()
    await (await dl).saveAs(`${OUT}/${c.name}_a_mano.png`)
    copyFileSync(resolve(ROOMS, c.photo), `${OUT}/${c.name}_original.jpg`)
    await suggestAndExport(page, `${c.name}_basica`)
  }
})
