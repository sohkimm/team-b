import { PAL } from '../theme.js'
import { fmtInt, fmtSign } from '../lib/format.js'

export function drawScatter(cv, { scatter, dir, ready }) {
  if (!cv) return
  const wrap = cv.parentElement
  const W = wrap.clientWidth, H = wrap.clientHeight
  if (W < 10 || H < 10) return
  const P = PAL
  const dpr = Math.min(2, window.devicePixelRatio || 1)
  cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + 'px'; cv.style.height = H + 'px'
  const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H)
  const pad = { l: 40, r: 12, t: 12, b: 30 }
  const size = Math.min(W - pad.l - pad.r, H - pad.t - pad.b)
  const x0 = pad.l, y0 = pad.t + ((H - pad.t - pad.b) - size) / 2
  const lo = 18, hi = 36
  const X = (v) => x0 + (v - lo) / (hi - lo) * size
  const Y = (v) => y0 + (hi - v) / (hi - lo) * size
  ctx.strokeStyle = P.grat; ctx.lineWidth = 1; ctx.fillStyle = P.tick; ctx.font = '11px ' + P.mono
  for (let v = 18; v <= 36; v += 3) {
    const xx = X(v), yy = Y(v)
    ctx.beginPath(); ctx.moveTo(xx, y0); ctx.lineTo(xx, y0 + size); ctx.moveTo(x0, yy); ctx.lineTo(x0 + size, yy); ctx.stroke()
    ctx.textAlign = 'center'; ctx.fillText(v, xx, y0 + size + 13); ctx.textAlign = 'right'; ctx.fillText(v, x0 - 5, yy + 3)
  }
  ctx.strokeStyle = P.frame; ctx.strokeRect(x0, y0, size, size)
  ctx.strokeStyle = P.oneToOne; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(X(lo), Y(lo)); ctx.lineTo(X(hi), Y(hi)); ctx.stroke(); ctx.setLineDash([])
  const cur = ready && scatter ? scatter[dir] : null
  if (cur && cur.points) {
    ctx.fillStyle = P.scatPt
    for (const p of cur.points) { ctx.beginPath(); ctx.arc(X(p[0]), Y(p[1]), 1.7, 0, 6.283); ctx.fill() }
    const s = cur.stats, bx = x0 + 8, by = y0 + 8
    ctx.fillStyle = P.boxBg; ctx.fillRect(bx, by, 152, 88); ctx.strokeStyle = P.boxStroke; ctx.strokeRect(bx, by, 152, 88)
    ctx.fillStyle = P.boxText; ctx.font = '13px ' + P.mono; ctx.textAlign = 'left'
    ctx.fillText('N    ' + fmtInt(s.N), bx + 11, by + 22)
    ctx.fillText('Bias ' + fmtSign(s.Bias), bx + 11, by + 43)
    ctx.fillText('RMSE ' + (s.RMSE == null ? '—' : s.RMSE.toFixed(3)), bx + 11, by + 64)
    ctx.fillText('R    ' + (s.R == null ? '—' : s.R.toFixed(3)), bx + 11, by + 85)
  } else {
    ctx.fillStyle = P.dim; ctx.font = '13px ' + P.mono; ctx.textAlign = 'center'
    ctx.fillText('awaiting validation', x0 + size / 2, y0 + size / 2)
  }
  const sel = scatter ? scatter[dir] : null
  const refLbl = (sel && sel.refLabel) || 'REF'
  const evalLbl = (sel && sel.evalLabel) || 'EVAL'
  ctx.fillStyle = P.dim; ctx.font = '11px ' + P.mono; ctx.textAlign = 'center'
  ctx.fillText(`REF · ${refLbl} (PSU)`, x0 + size / 2, H - 4)
  ctx.save(); ctx.translate(11, y0 + size / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(`EVAL · ${evalLbl} (PSU)`, 0, 0); ctx.restore()
}
