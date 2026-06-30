import { fmtInt, fmtSign, fmt3, dash } from '../lib/format.js'

function fmtVal(label, v) {
  if (v === null || v === undefined) return dash
  if (label === 'N') return fmtInt(v)
  if (label === 'Bias') return fmtSign(v)
  return fmt3(v)
}

export default function ValidationMetrics({ metrics }) {
  return (
    <div className="panel">
      <div className="panel-hd"><span className="panel-title">Validation metrics</span><span className="panel-kr">검증 통계</span></div>
      <div className="mtable">
        <div className="mono" style={{ fontSize: 11, color: '#565a68', paddingBottom: 10 }}>METRIC</div>
        <div className="mono" style={{ fontSize: 11, color: '#8e96ff', textAlign: 'right', paddingBottom: 10 }}>HI→LO 0.25°<div style={{ fontSize: 9, color: '#5a5fa0' }}>권장</div></div>
        <div className="mono" style={{ fontSize: 11, color: '#7e818d', textAlign: 'right', paddingBottom: 10 }}>LO→HI 0.125°<div style={{ fontSize: 9, color: '#565a68' }}>비교</div></div>
        {(metrics || []).map((m) => (
          <div style={{ display: 'contents' }} key={m.label}>
            <div className="mcell" style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: '#e6e7ea' }}>{m.label}</span>
              <span className="mono" style={{ fontSize: 10, color: '#565a68' }}>{m.kr}</span>
            </div>
            <div className="mcell mval" style={{ color: '#8e96ff' }}>{fmtVal(m.label, m.hilo)}</div>
            <div className="mcell mval" style={{ color: '#9a9da8' }}>{fmtVal(m.label, m.lohi)}</div>
          </div>
        ))}
        {!metrics && (
          <div style={{ gridColumn: '1 / -1', paddingTop: 10 }} className="muted">awaiting validation</div>
        )}
      </div>
    </div>
  )
}
