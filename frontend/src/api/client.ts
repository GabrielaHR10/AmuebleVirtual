export interface Health {
  ok: boolean
  device: string
  version: string
}

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const res = await fetch('/api/health', { signal })
  if (!res.ok) throw new Error(`El servidor respondió ${res.status}`)
  return (await res.json()) as Health
}

export function describeHealth(h: Health): string {
  return `Servidor conectado · ${h.device.toUpperCase()} · v${h.version}`
}
