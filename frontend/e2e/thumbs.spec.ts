import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

// Genera data/catalog/<id>/thumb.png para los muebles 3D. Se corre con: uv run python scripts/make_thumbs.py (desde backend/)
// THUMB_VIEW=front|right|left guarda vistas en test-results/<vista>/ en vez de miniaturas.
const here = dirname(fileURLToPath(import.meta.url))
const catalogDir = resolve(here, '../../data/catalog')
const debugView = process.env.THUMB_VIEW // front | right | left: vistas para revisar orientación

interface Item {
  id: string
  glb_url: string | null
  yaw_offset_deg: number
}

test('miniaturas de los modelos 3D', async ({ page, request }) => {
  // Solo corre cuando lo pide scripts/make_thumbs.py (escribe en data/catalog/)
  test.skip(!process.env.MAKE_THUMBS && !debugView, 'Generación de miniaturas: usar scripts/make_thumbs.py')
  test.setTimeout(300_000)
  const items = ((await (await request.get('/api/catalog')).json()) as Item[]).filter((i) => i.glb_url)
  expect(items.length).toBeGreaterThan(0)
  await page.setViewportSize({ width: 512, height: 512 })
  for (const item of items) {
    const view = debugView ?? 'three-quarter'
    await page.goto(`/thumb?glb=${encodeURIComponent(item.glb_url!)}&yaw=${item.yaw_offset_deg}&view=${view}`)
    await page.waitForFunction(() => window.__thumbReady === true, null, { timeout: 60_000 })
    const out = debugView ? `test-results/${debugView}/${item.id}.png` : `${catalogDir}/${item.id}/thumb_512.png`
    mkdirSync(dirname(out), { recursive: true })
    await page.locator('canvas').screenshot({ path: out, omitBackground: true })
  }
})
