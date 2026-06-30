// 2D 염분 격자(field) → turbo 색 PNG dataURL (Leaflet imageOverlay용).
import { cmapSal } from './colormap.js'

export function fieldToDataURL(field, domain) {
  const { z, ny, nx } = field || {}
  if (!ny || !nx) return null
  const min = domain ? domain[0] : undefined
  const max = domain ? domain[1] : undefined
  const cv = document.createElement('canvas')
  cv.width = nx; cv.height = ny
  const ctx = cv.getContext('2d')
  const img = ctx.createImageData(nx, ny)
  for (let r = 0; r < ny; r++) {
    const i = ny - 1 - r   // 이미지 top=북(최대 위도)=z[ny-1]
    for (let c = 0; c < nx; c++) {
      const v = z[i][c]
      const o = (r * nx + c) * 4
      if (v == null) { img.data[o + 3] = 0; continue }   // null(육지/결측)=투명
      const [rr, gg, bb] = cmapSal(v, min, max)
      img.data[o] = rr; img.data[o + 1] = gg; img.data[o + 2] = bb; img.data[o + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
  return cv.toDataURL('image/png')
}
