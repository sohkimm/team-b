import { describe, it, expect } from 'vitest'
import { fmtInt, fmt3, fmtSign, dash } from './format.js'

describe('format', () => {
  it('fmtInt adds thousands separators and dashes nulls', () => {
    expect(fmtInt(1772)).toBe('1,772')
    expect(fmtInt(null)).toBe(dash)
  })
  it('fmt3 fixes 3 decimals', () => {
    expect(fmt3(2.165)).toBe('2.165')
    expect(fmt3(undefined)).toBe(dash)
  })
  it('fmtSign uses unicode minus and explicit plus', () => {
    expect(fmtSign(1.71)).toBe('+1.710')
    expect(fmtSign(-0.192)).toBe('−0.192')
    expect(fmtSign(null)).toBe(dash)
  })
})
