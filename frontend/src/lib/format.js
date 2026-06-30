export const dash = '—'
export const fmtInt = (n) =>
  (n === null || n === undefined) ? dash : Number(n).toLocaleString('en-US')
export const fmt3 = (x) =>
  (x === null || x === undefined) ? dash : Number(x).toFixed(3)
export const fmtSign = (x) =>
  (x === null || x === undefined) ? dash : (x >= 0 ? '+' : '−') + Math.abs(x).toFixed(3)
