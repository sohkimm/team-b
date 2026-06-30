export default function QualityControl({ qc }) {
  return (
    <div className="panel">
      <div className="panel-hd"><span className="panel-title">Quality Control</span><span className="panel-kr">속성 마스킹</span></div>
      {!qc ? (
        <div className="muted" style={{ textAlign: 'center', padding: '6px 0' }}>pending</div>
      ) : (
        <div className="qc-wrap">
          {qc.map((r, i) => (
            <div className="qc-chip" key={i}><span style={{ color: '#42c98a' }}>✓</span><span style={{ color: '#aeb0bb' }}>{r.k}</span></div>
          ))}
        </div>
      )}
    </div>
  )
}
