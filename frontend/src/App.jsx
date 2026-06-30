import { useState, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import './app.css'
import { runAnalyzeStream } from './lib/sse.js'
import Header from './components/Header.jsx'
import DataIngest from './components/DataIngest.jsx'
import Inspection from './components/Inspection.jsx'
import SalinityMap from './components/SalinityMap.jsx'
import Legend from './components/Legend.jsx'
import ValidationMetrics from './components/ValidationMetrics.jsx'
import ScatterPlot from './components/ScatterPlot.jsx'
import PipelineSteps from './components/PipelineSteps.jsx'
import QualityControl from './components/QualityControl.jsx'
import ResampleVerdict from './components/ResampleVerdict.jsx'

const A_NAME = 'dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc'
const B_NAME = 'SMAP_L3_SSS_20260101_8DAYS_V5.0.nc'
const EMPTY = {
  completed: 0, active: 0, running: false, error: null,
  inspect: null, qc: null, fields: { cmems: undefined, smap: undefined, diff: undefined },
  metrics: null, scatter: null, verdict: null,
}

// 두 격자의 실제 vmin/vmax를 합쳐 공통 색 스케일(비교 가능). 데이터 없으면 [null,null].
function salDomain(fields) {
  const fs = [fields.cmems, fields.smap].filter(Boolean)
  const mins = fs.map((f) => f.vmin).filter((v) => v != null)
  const maxs = fs.map((f) => f.vmax).filter((v) => v != null)
  if (!mins.length || !maxs.length) return [null, null]
  return [Math.min(...mins), Math.max(...maxs)]
}

export default function App() {
  const [a, setA] = useState(false)
  const [b, setB] = useState(false)
  const [aFile, setAFile] = useState(null)
  const [bFile, setBFile] = useState(null)
  const [dir, setDir] = useState('hilo')
  const [run, setRun] = useState(EMPTY)
  const abortRef = useRef(null)

  function applyEvent(ev) {
    if (ev.event === 'error') { setRun((r) => ({ ...r, running: false, active: 0, error: ev.data.detail })); return }
    if (ev.event === 'done') { setRun((r) => ({ ...r, running: false, active: 0 })); return }
    const d = ev.data
    setRun((r) => {
      const next = { ...r }
      if (d.status === 'active') next.active = d.n
      if (d.status === 'done') { next.completed = d.n; next.active = 0 }
      if (d.inspect) next.inspect = d.inspect
      if (d.qc) next.qc = d.qc
      if (d.maps) next.fields = { ...next.fields, ...d.maps }
      if (d.metrics) next.metrics = d.metrics
      if (d.scatter) next.scatter = d.scatter
      if (d.verdict) next.verdict = d.verdict
      return next
    })
  }

  async function start(demo) {
    if (abortRef.current) abortRef.current.abort()
    const ctrl = new AbortController(); abortRef.current = ctrl
    setDir('hilo')
    const fd = new FormData()
    if (demo) fd.append('demo', 'true')
    else {
      if (!aFile || !bFile) {   // null File → FormData가 "null" 문자열로 보내 422 → 방어
        setRun((r) => ({ ...r, running: false, error: 'Drop both .nc files before running.' }))
        return
      }
      fd.append('demo', 'false'); fd.append('file_a', aFile); fd.append('file_b', bFile)
    }
    setRun({ ...EMPTY, running: true })   // 가드 통과 후에만 스피너로 (기존 결과 보존)
    try {
      await runAnalyzeStream(fd, { onEvent: applyEvent, signal: ctrl.signal })
    } catch (e) {
      if (e.name !== 'AbortError') setRun((r) => ({ ...r, running: false, error: String(e.message || e) }))
    }
  }

  function reset() {
    if (abortRef.current) abortRef.current.abort()
    setA(false); setB(false); setAFile(null); setBFile(null)
    setDir('hilo'); setRun(EMPTY)
  }

  // .nc 드래그앤드롭: 1개면 해당 슬롯, 2개 동시면 파일명으로 SMAP→B(ref)·나머지→A(eval) (매칭 없으면 순서대로)
  function handleDrop(e, slot) {
    e.preventDefault()
    const files = Array.from(e.dataTransfer?.files || []).filter((f) => /\.nc$/i.test(f.name))
    if (files.length === 0) return
    if (files.length >= 2) {
      const smap = files.find((f) => /smap/i.test(f.name))
      const aSel = files.find((f) => f !== smap) || files[0]
      const bSel = smap || files[1]
      setAFile(aSel); setA(true)
      setBFile(bSel); setB(true)
    } else if (slot === 'b') {
      setBFile(files[0]); setB(true)
    } else {
      setAFile(files[0]); setA(true)
    }
  }

  const { completed, running, error, inspect, fields, metrics, scatter } = run
  const resultReady = completed >= 5
  const [dmin, dmax] = salDomain(fields)

  return (
    <div className="app">
      <Header />
      <div className="main">
        <div className="col-l">
          <DataIngest a={a} b={b} aName={A_NAME} bName={B_NAME}
            runReady={!!aFile && !!bFile && !running} running={running}
            onDropA={(e) => handleDrop(e, 'a')}
            onDropB={(e) => handleDrop(e, 'b')}
            onRun={() => start(false)} onDemo={() => start(true)} onReset={reset} />
          <PipelineSteps completed={run.completed} active={run.active} />
          <Inspection inspect={inspect} />
        </div>
        <div className="col-c">
          <div className="map-row">
            <SalinityMap title="CMEMS" subtitle="EVAL · 0.125°" field={fields.cmems} dmin={dmin} dmax={dmax} />
            <SalinityMap title="SMAP" subtitle="REF · 0.250°" field={fields.smap} dmin={dmin} dmax={dmax} />
          </div>
          <Legend dmin={dmin} dmax={dmax} />
        </div>
        <div className="col-r">
          <QualityControl qc={run.qc} />
          <ValidationMetrics metrics={metrics} />
          <ScatterPlot scatter={scatter} dir={dir} ready={resultReady} onDir={setDir} />
          <ResampleVerdict verdict={run.verdict} />
        </div>
      </div>
      {error && (
        <div style={{ position: 'fixed', bottom: 14, left: 22, padding: '8px 14px', background: 'rgba(210,80,90,0.15)', border: '1px solid rgba(210,80,90,0.5)', borderRadius: 8, color: '#ff9aa2', fontFamily: 'IBM Plex Mono,monospace', fontSize: 11 }}>⚠ {error}</div>
      )}
    </div>
  )
}
