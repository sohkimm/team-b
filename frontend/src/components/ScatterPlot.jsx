import { useEffect, useRef } from 'react'
import { drawScatter } from '../canvas/drawScatter.js'

function Seg({ active, onClick, children }) {
  return (
    <div className="seg-sm" onClick={onClick}
      style={{ background: active ? 'rgba(109,119,255,0.25)' : 'transparent', color: active ? '#aeb4ff' : '#7e818d', cursor: 'pointer' }}>
      {children}
    </div>
  )
}

export default function ScatterPlot({ scatter, dir, ready, onDir }) {
  const ref = useRef(null)
  useEffect(() => {
    const draw = () => drawScatter(ref.current, { scatter, dir, ready })
    draw()
    const raf = requestAnimationFrame(draw)   // 첫 페인트 시 레이아웃/폰트 준비 보강
    window.addEventListener('resize', draw)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', draw) }
  }, [scatter, dir, ready])
  return (
    <div className="panel panel-grow">
      <div className="panel-hd">
        <span className="panel-title">1:1 scatter</span>
        <div className="seg" style={{ marginLeft: 'auto' }}>
          <Seg active={dir === 'hilo'} onClick={() => onDir('hilo')}>HI→LO</Seg>
          <Seg active={dir === 'lohi'} onClick={() => onDir('lohi')}>LO→HI</Seg>
        </div>
      </div>
      <div className="canvas-wrap"><canvas ref={ref} /></div>
    </div>
  )
}
