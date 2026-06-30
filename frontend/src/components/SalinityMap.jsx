import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { fieldToDataURL } from '../lib/fieldImage.js'

// AOI bounds: [[South, West], [North, East]]
const AOI = [[24, 117], [38, 131]]

export default function SalinityMap({ title, subtitle, field, dmin, dmax }) {
  const elRef = useRef(null)
  const mapRef = useRef(null)
  const ovRef = useRef(null)

  // 맵 1회 생성 — AOI에 고정, 확대축소·팬 비활성 (CARTO 다크 베이스맵)
  useEffect(() => {
    const map = L.map(elRef.current, {
      zoomControl: false, attributionControl: true, zoomSnap: 0,
      dragging: false, scrollWheelZoom: false, doubleClickZoom: false,
      boxZoom: false, keyboard: false, touchZoom: false,
    })
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd', maxZoom: 19,
      attribution: '© OpenStreetMap, © CARTO',
    }).addTo(map)
    map.fitBounds(AOI, { animate: false })
    map.setMaxBounds(AOI)
    mapRef.current = map
    const fix = () => { map.invalidateSize(); map.fitBounds(AOI, { animate: false }) }
    const t = setTimeout(fix, 0)
    window.addEventListener('resize', fix)
    return () => { clearTimeout(t); window.removeEventListener('resize', fix); map.remove(); mapRef.current = null }
  }, [])

  // field 바뀌면 turbo 오버레이 갱신
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (ovRef.current) { map.removeLayer(ovRef.current); ovRef.current = null }
    const domain = (dmin != null && dmax != null) ? [dmin, dmax] : null
    const url = field ? fieldToDataURL(field, domain) : null
    if (url) {
      // 오버레이는 필드 실제 extent에 정확히 맞춤(임의 데이터 안전); 뷰는 AOI 고정
      const b = [[field.lat0, field.lon0], [field.lat1, field.lon1]]
      ovRef.current = L.imageOverlay(url, b, {
        opacity: 0.82, className: 'sss-overlay', interactive: false,
      }).addTo(map)
    }
  }, [field, dmin, dmax])

  return (
    <div className="panel panel-grow">
      <div className="panel-hd">
        <span className="panel-title" style={{ fontSize: 15 }}>{title}</span>
        <span className="mono" style={{ fontSize: 10, color: '#8e96ff' }}>{subtitle}</span>
      </div>
      <div className="map-el" ref={elRef} />
    </div>
  )
}
