// Turbo 컬러맵 (Anton Mikhailov 다항식 근사) + 염분→색 매핑.
import { SAL_MIN, SAL_MAX } from '../theme.js'

export function turbo(t) {
  t = Math.min(1, Math.max(0, t))
  const t2 = t * t, t3 = t2 * t, t4 = t3 * t, t5 = t4 * t
  const r = 0.13572138 + 4.61539260 * t - 42.66032258 * t2 + 132.13108234 * t3 - 152.94239396 * t4 + 60.09244020 * t5
  const g = 0.09140261 + 2.19418839 * t + 4.84296658 * t2 - 14.18503333 * t3 + 4.27729857 * t4 + 2.82956604 * t5
  const b = 0.10667330 + 12.64194608 * t - 60.58204836 * t2 + 110.36276771 * t3 - 89.90310912 * t4 + 27.34824973 * t5
  const c = (x) => Math.max(0, Math.min(255, Math.round(x * 255)))
  return [c(r), c(g), c(b)]
}

// 도메인(min~max)을 넘기면 그 범위로 정규화, 없으면 기본 18~35.2.
export const cmapSal = (v, min = SAL_MIN, max = SAL_MAX) =>
  turbo((v - min) / ((max - min) || 1))
