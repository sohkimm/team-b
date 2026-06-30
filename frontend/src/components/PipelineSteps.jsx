const DEFS = [
  ['1', 'Input validation', '입력 검증', 'NetCDF gate'],
  ['2', 'Inspect + QC', '파악·품질관리', 'grid·res·CRS'],
  ['3', 'WGS84 standardize', '표준화', '→ AOI grid'],
  ['4', 'Resolution match', '해상도 정합', '→ coarser'],
  ['5', 'Validation', '검증', '1:1 · 2 dir'],
]

function styleFor(state) {
  if (state === 'done') return { col: '#d3d4da', bg: 'rgba(109,119,255,0.07)', border: 'rgba(109,119,255,0.3)', dot: '#6d77ff', anim: 'none', chip: '#6d77ff', chipCol: '#fff' }
  if (state === 'active') return { col: '#fff', bg: 'rgba(109,119,255,0.14)', border: 'rgba(109,119,255,0.6)', dot: '#9a6dff', anim: 'pulse 1.05s ease-in-out infinite', chip: '#9a6dff', chipCol: '#fff' }
  return { col: '#6b6f7e', bg: '#1a1c24', border: '#262935', dot: '#33363f', anim: 'none', chip: '#262935', chipCol: '#6b6f7e' }
}

export default function PipelineSteps({ completed, active }) {
  const pct = ((completed + (active ? 0.5 : 0)) / 5 * 100).toFixed(0) + '%'
  return (
    <div className="panel">
      <div className="panel-hd">
        <span className="panel-title">Pipeline</span><span className="panel-kr">처리 단계</span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="progress"><div style={{ width: pct }} /></div>
          <span className="mono" style={{ fontSize: 11, color: '#8e96ff', width: 40, textAlign: 'right' }}>{pct}</span>
        </div>
      </div>
      <div className="steps">
        {DEFS.map((d, idx) => {
          const n = idx + 1
          const state = n <= completed ? 'done' : (n === active ? 'active' : 'idle')
          const s = styleFor(state)
          return (
            <div className="step" key={n} style={{ background: s.bg, border: `1px solid ${s.border}` }}>
              <div className="step-hd">
                <div className="step-chip" style={{ background: s.chip, color: s.chipCol }}>{d[0]}</div>
                <div className="step-dot" style={{ background: s.dot, animation: s.anim }} />
              </div>
              <div className="step-title" style={{ color: s.col }}>{d[1]}</div>
              <div className="step-sub">{d[3]}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
