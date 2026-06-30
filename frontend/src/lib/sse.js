// SSE 프레임 파서 + fetch ReadableStream 소비기 (EventSource는 GET 전용이라 미사용).
export function parseSSE(frame) {
  let event = 'message'
  let data = ''
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  if (!data) return null
  return { event, data: JSON.parse(data) }
}

// 백엔드 베이스 URL. 로컬 기본값 localhost:8000, 배포 시 VITE_API_URL 로 Render 주소 주입.
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function runAnalyzeStream(formData, { onEvent, signal } = {}) {
  const res = await fetch(`${API_BASE}/api/analyze`, { method: 'POST', body: formData, signal })
  if (!res.ok || !res.body) throw new Error(`stream failed (${res.status})`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const ev = parseSSE(frame)
      if (ev && onEvent) onEvent(ev)
    }
  }
}
