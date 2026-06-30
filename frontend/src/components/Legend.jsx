import { useEffect, useRef } from 'react'
import { turbo } from '../lib/colormap.js'
import { SAL_MIN, SAL_MAX } from '../theme.js'

// 공유 turbo 컬러바 (염분 PSU 범례) — 범위는 실데이터(dmin~dmax), 없으면 기본값
export default function Legend({ dmin, dmax }) {
  const ref = useRef(null)
  useEffect(() => {
    const cv = ref.current
    const w = (cv.width = 240), h = (cv.height = 10)
    const ctx = cv.getContext('2d')
    for (let x = 0; x < w; x++) {
      const [r, g, b] = turbo(x / (w - 1))
      ctx.fillStyle = `rgb(${r},${g},${b})`
      ctx.fillRect(x, 0, 1, h)
    }
  }, [])
  const lo = (dmin != null ? dmin : SAL_MIN)
  const hi = (dmax != null ? dmax : SAL_MAX)
  return (
    <div className="legend">
      <span className="mono" style={{ fontSize: 11, color: '#6b6f7e' }}>SALINITY (PSU)</span>
      <span className="mono" style={{ fontSize: 11, color: '#9a9da8' }}>{lo.toFixed(1)}</span>
      <canvas ref={ref} style={{ height: 10, width: 240, borderRadius: 2 }} />
      <span className="mono" style={{ fontSize: 11, color: '#9a9da8' }}>{hi.toFixed(1)}</span>
    </div>
  )
}
