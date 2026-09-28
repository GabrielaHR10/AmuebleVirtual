import { describe, expect, it } from 'vitest'
import { describeHealth } from './client'

describe('describeHealth', () => {
  it('muestra dispositivo y versión', () => {
    expect(describeHealth({ ok: true, device: 'mps', version: '0.0.0' })).toBe(
      'Servidor conectado · MPS · v0.0.0',
    )
  })
})
