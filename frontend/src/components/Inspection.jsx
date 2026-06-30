const ORDER = ['TYPE', 'VAR', 'GRID', 'RES', 'TIME', 'CRS']

function Block({ title, color, row }) {
  return (
    <div className="ins-card">
      <div className="ins-hd" style={{ color }}>{title}</div>
      <div className="ins-grid">
        {ORDER.map((k) => (
          <div className="ins-row" key={k}><span className="ins-k">{k}</span><span className="ins-v">{row[k]}</span></div>
        ))}
      </div>
    </div>
  )
}

export default function Inspection({ inspect }) {
  return (
    <div className="panel panel-grow">
      <div className="panel-hd"><span className="panel-title">Inspection</span><span className="panel-kr">자동 파악</span></div>
      {!inspect ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }} className="muted">awaiting inspection</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1 }}>
          <Block title="A · CMEMS — EVAL" color="#8e96ff" row={inspect.a} />
          <Block title="B · SMAP — REF" color="#42c98a" row={inspect.b} />
        </div>
      )}
    </div>
  )
}
