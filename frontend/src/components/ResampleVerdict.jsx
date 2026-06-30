export default function ResampleVerdict({ verdict }) {
  return (
    <div className="verdict">
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Resample verdict</div>
      {!verdict ? (
        <div className="mono" style={{ textAlign: 'center', padding: '6px 0', fontSize: 10, color: '#565a68' }}>awaiting results</div>
      ) : (
        <>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#aeb4ff', marginBottom: 7 }}>{verdict.headline}</div>
          <div className="mono" style={{ fontSize: 9, lineHeight: 1.6, color: '#9a9da8' }}>
            {verdict.bullets.map((b, i) => <div key={i}>· {b}</div>)}
          </div>
        </>
      )}
    </div>
  )
}
