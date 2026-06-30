import { describe, it, expect } from 'vitest'
import { parseSSE } from './sse.js'

describe('parseSSE', () => {
  it('parses an event + json data frame', () => {
    const ev = parseSSE('event: step\ndata: {"n": 2, "status": "done"}')
    expect(ev).toEqual({ event: 'step', data: { n: 2, status: 'done' } })
  })
  it('defaults event to "message" and joins multiline data', () => {
    const ev = parseSSE('data: {"a":\ndata: 1}')
    expect(ev).toEqual({ event: 'message', data: { a: 1 } })
  })
  it('returns null for a frame with no data', () => {
    expect(parseSSE(': comment only')).toBeNull()
  })
})
