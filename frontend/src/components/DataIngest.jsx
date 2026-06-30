function Slot({ loaded, tag, accent, name, color }) {
  const border = loaded ? color : '#2d303b'
  const bg = loaded ? `${color}14` : 'transparent'
  return {
    style: { borderColor: border, background: bg },
    body: loaded
      ? (<><div style={{ fontSize: 28, color: '#42c98a' }}>✓</div><div className="drop-name">{name}</div></>)
      : (<><div style={{ fontSize: 30, color: '#3a3d48' }}>⤓</div><div className="mono" style={{ fontSize: 11, color: '#565a68' }}>drop .nc</div></>),
    tag, accent: loaded ? accent : '#6b6f7e',
  }
}

export default function DataIngest({ a, b, aName, bName, runReady, running, onDropA, onDropB, onRun, onDemo, onReset }) {
  const sa = Slot({ loaded: a, tag: 'DATASET A · EVAL', accent: '#8e96ff', name: aName, color: '#6d77ff' })
  const sb = Slot({ loaded: b, tag: 'DATASET B · REF', accent: '#42c98a', name: bName, color: '#42c98a' })
  const drag = (e) => e.preventDefault()
  return (
    <div className="panel">
      <div className="panel-hd"><span className="panel-title">Data Ingest</span><span className="panel-kr">자료 입력</span></div>
      <div className="drops">
        <div className="drop" style={sa.style} onDrop={onDropA} onDragOver={drag}>
          <div className="drop-tag" style={{ color: sa.accent }}>{sa.tag}</div>{sa.body}
        </div>
        <div className="drop" style={sb.style} onDrop={onDropB} onDragOver={drag}>
          <div className="drop-tag" style={{ color: sb.accent }}>{sb.tag}</div>{sb.body}
        </div>
      </div>
      <div className="ingest-btns">
        <div className="btn-demo" onClick={running ? undefined : onDemo}
          style={{
            cursor: running ? 'not-allowed' : 'pointer',
            opacity: running ? 0.55 : 1,
          }}>{running ? 'Streaming...' : 'Run demo'}</div>
        <div className="btn-run" onClick={runReady ? onRun : undefined}
          style={{
            background: runReady ? 'linear-gradient(135deg,#6d77ff,#9a6dff)' : '#23252e',
            color: runReady ? '#fff' : '#6b6f7e',
            cursor: runReady ? 'pointer' : 'not-allowed',
            boxShadow: runReady ? '0 4px 14px rgba(109,119,255,.4)' : 'none',
          }}>{running ? 'Running...' : 'Run pipeline'}</div>
        <div className="btn" onClick={onReset}>Reset</div>
      </div>
    </div>
  )
}
