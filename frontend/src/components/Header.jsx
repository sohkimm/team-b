export default function Header() {
  return (
    <div className="hdr">
      <div className="hdr-logo">N</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <div className="hdr-title">NC Validation Pipeline</div>
        <div className="hdr-sub">범용 검증 파이프라인 · 24–38°N · 117–131°E</div>
      </div>
    </div>
  )
}
