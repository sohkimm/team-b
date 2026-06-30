import { describe, it, expect } from 'vitest'
import { turbo, cmapSal } from './colormap.js'

describe('colormap (turbo)', () => {
  it('clamps out-of-range t to the endpoints', () => {
    expect(turbo(-1)).toEqual(turbo(0))
    expect(turbo(2)).toEqual(turbo(1))
  })
  it('spans blue (low) to red (high)', () => {
    const blue = turbo(0.15), red = turbo(0.9)
    expect(blue[2]).toBeGreaterThan(blue[0])   // 저쪽 끝 파랑 우세
    expect(red[0]).toBeGreaterThan(red[2])     // 고쪽 끝 빨강 우세
  })
  it('cmapSal maps a salinity value to an rgb triple in range', () => {
    const c = cmapSal(27)
    expect(c).toHaveLength(3)
    expect(c.every((x) => x >= 0 && x <= 255)).toBe(true)
  })
})
