const encoder = new TextEncoder()

function sse(event, data) {
  return encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
}

function makeField(kind) {
  const ny = 28
  const nx = 28
  const z = []
  let vmin = Infinity
  let vmax = -Infinity
  for (let y = 0; y < ny; y += 1) {
    const row = []
    for (let x = 0; x < nx; x += 1) {
      const coastMask = x < 4 && y > 17
      if (coastMask) {
        row.push(null)
        continue
      }
      const wave = Math.sin(x / 4.3) * 0.34 + Math.cos(y / 5.1) * 0.28
      const front = (x - y) * 0.018
      const offset = kind === 'smap' ? -0.06 : 0.08
      const value = Number((33.45 + wave + front + offset).toFixed(3))
      vmin = Math.min(vmin, value)
      vmax = Math.max(vmax, value)
      row.push(value)
    }
    z.push(row)
  }
  return { z, ny, nx, vmin, vmax, lat0: 24, lat1: 38, lon0: 117, lon1: 131 }
}

function scatterPoints(offset) {
  const points = []
  for (let i = 0; i < 180; i += 1) {
    const ref = 31.4 + (i % 30) * 0.11 + Math.sin(i * 0.37) * 0.28
    const evalValue = ref + offset + Math.cos(i * 0.23) * 0.18
    points.push([Number(ref.toFixed(3)), Number(evalValue.toFixed(3))])
  }
  return points
}

const inspect = {
  a: { TYPE: 'CMEMS', VAR: 'so', GRID: 'regular', RES: '0.125deg', TIME: '2026-01-01', CRS: 'EPSG:4326' },
  b: { TYPE: 'SMAP', VAR: 'sss', GRID: 'regular', RES: '0.250deg', TIME: '2026-01-01', CRS: 'EPSG:4326' },
}

const metrics = [
  { label: 'N', kr: 'valid pairs', hilo: 18422, lohi: 73591 },
  { label: 'Bias', kr: 'mean eval-ref', hilo: 0.042, lohi: 0.057 },
  { label: 'RMSE', kr: 'root mean square', hilo: 0.318, lohi: 0.356 },
  { label: 'R', kr: 'correlation', hilo: 0.934, lohi: 0.912 },
]

const scatter = {
  hilo: {
    refLabel: 'SMAP 0.25deg',
    evalLabel: 'CMEMS->0.25deg',
    points: scatterPoints(0.04),
    stats: { N: 18422, Bias: 0.042, RMSE: 0.318, R: 0.934 },
  },
  lohi: {
    refLabel: 'SMAP->0.125deg',
    evalLabel: 'CMEMS 0.125deg',
    points: scatterPoints(0.06),
    stats: { N: 73591, Bias: 0.057, RMSE: 0.356, R: 0.912 },
  },
}

const events = [
  { event: 'step', data: { n: 1, status: 'active' } },
  { event: 'step', data: { n: 1, status: 'done', inspect } },
  { event: 'step', data: { n: 2, status: 'active' } },
  {
    event: 'step',
    data: {
      n: 2,
      status: 'done',
      qc: [{ k: 'time overlap' }, { k: 'finite values' }, { k: 'AOI coverage' }, { k: 'unit: PSU' }],
    },
  },
  { event: 'step', data: { n: 3, status: 'active' } },
  { event: 'step', data: { n: 3, status: 'done', maps: { cmems: makeField('cmems'), smap: makeField('smap') } } },
  { event: 'step', data: { n: 4, status: 'active' } },
  {
    event: 'step',
    data: {
      n: 4,
      status: 'done',
      verdict: {
        headline: 'HI->LO averaging is the recommended comparison path.',
        bullets: ['CMEMS 0.125deg is aggregated to SMAP 0.25deg.', 'LO->HI is retained as a sensitivity check.'],
      },
    },
  },
  { event: 'step', data: { n: 5, status: 'active' } },
  { event: 'step', data: { n: 5, status: 'done', metrics, scatter } },
]

async function handleAnalyze() {
  const stream = new ReadableStream({
    async start(controller) {
      for (const event of events) {
        controller.enqueue(sse(event.event, event.data))
        await new Promise((resolve) => setTimeout(resolve, 220))
      }
      controller.enqueue(sse('done', { ok: true }))
      controller.close()
    },
  })
  return new Response(stream, {
    headers: {
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-store',
      'access-control-allow-origin': '*',
    },
  })
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    if (url.pathname === '/api/health') {
      return Response.json({ ok: true })
    }
    if (url.pathname === '/api/analyze' && request.method === 'POST') {
      return handleAnalyze()
    }
    if (url.pathname.startsWith('/api/')) {
      return Response.json({ error: 'not found' }, { status: 404 })
    }
    return env.ASSETS.fetch(request)
  },
}
