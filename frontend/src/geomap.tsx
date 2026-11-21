import {useEffect, useMemo, useRef, useState} from 'react';
import {Layers, Minus, Plus, RotateCcw} from 'lucide-react';
import './geomap.css';
import {localSnapshot} from './research-data';
import {type Aoi, type Bounds, type LonLat, type View, DENSITY_BREAKS, H, W, boundsOf, densityClass, filterAois, fitView,
  lineOf, linesOf, pathOf, projector, ringsOf, zoomAt} from './geo-utils';

type Geo = {
  view_bounds: Bounds;
  districts: {name: string; geometry: {type: string; coordinates: unknown}}[];
  rivers: {goid: number; upland_km2: number; geometry: {type: string; coordinates: unknown}}[];
  chains: {upstream: string; downstream: string; reaches: number; supported: boolean; lines: LonLat[][]}[];
  stations: {id: string; river: string; name: string; code: string; lonlat: LonLat}[];
  aois: Aoi[];
  provenance: Record<string, {source: string; note?: string}>;
  unavailable: string[];
};
type LayerKey = 'districts' | 'rivers' | 'chains' | 'stations' | 'aois';
const LAYERS: [LayerKey, string, string][] = [
  ['districts', 'District boundaries', 'GAUL 2025 · observed admin data'],
  ['rivers', 'River network', 'HydroSHEDS · DEM-modelled'],
  ['chains', 'Station main stems', 'NDOID path · modelled'],
  ['stations', 'CPCB stations', 'Official register coordinates'],
  ['aois', 'Sampled AOIs (density)', 'Phase 22X · aggregate only'],
];
const DENSITY_LABELS = ['0', '< 0.5', '0.5–1.5', '1.5–3', '≥ 3'];

export function GeoMap({district}: {district: string}) {
  const [geo, setGeo] = useState<Geo>();
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [view, setView] = useState<View>({k: 1, tx: 0, ty: 0});
  const [on, setOn] = useState<Record<LayerKey, boolean>>({districts: true, rivers: true, chains: true, stations: true, aois: true});
  const [tip, setTip] = useState<{x: number; y: number; text: string}>();
  const [panel, setPanel] = useState(() => typeof innerWidth === 'number' ? innerWidth >= 1280 : true);
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{x: number; y: number; v: View} | undefined>(undefined);

  useEffect(() => {
    const c = new AbortController();
    fetch(localSnapshot + 'geo.json', {signal: c.signal})
      .then(r => { if (!r.ok) throw Error('Unavailable'); return r.json(); })
      .then(g => { setGeo(g); setState('ready'); })
      .catch(() => { if (!c.signal.aborted) setState('error'); });
    return () => c.abort();
  }, []);

  const p = useMemo(() => geo ? projector(geo.view_bounds) : undefined, [geo]);
  const shapes = useMemo(() => {
    if (!geo || !p) return undefined;
    return {
      districts: geo.districts.map(d => ({name: d.name, d: pathOf(ringsOf(d.geometry), p), rings: ringsOf(d.geometry)})),
      rivers: geo.rivers.map(r => ({goid: r.goid, w: r.upland_km2 >= 300 ? 1.6 : r.upland_km2 >= 100 ? 1.1 : .7,
        d: linesOf(r.geometry).map(l => lineOf(l, p)).join('')})),
      chains: geo.chains.map(c => ({...c, d: c.lines.map(l => lineOf(l, p)).join('')})),
    };
  }, [geo, p]);

  // Fit to the selected district (or the full study area) whenever the filter changes.
  useEffect(() => {
    if (!shapes || !p) return;
    const target = district === 'All districts' ? shapes.districts : shapes.districts.filter(d => d.name === district);
    if (!target.length) return;
    const [w, s, e, n] = boundsOf(target.flatMap(d => d.rings));
    const [x0, y0] = p([w, n]), [x1, y1] = p([e, s]);
    setView(fitView([x0, y0, x1, y1]));
  }, [district, shapes, p]);

  useEffect(() => {
    const el = svg.current;
    if (!el) return;
    const wheel = (ev: WheelEvent) => {
      ev.preventDefault();
      const r = el.getBoundingClientRect();
      const cx = (ev.clientX - r.left) * W / r.width, cy = (ev.clientY - r.top) * H / r.height;
      setView(v => zoomAt(v, ev.deltaY < 0 ? 1.2 : 1 / 1.2, cx, cy));
    };
    el.addEventListener('wheel', wheel, {passive: false});
    return () => el.removeEventListener('wheel', wheel);
  }, [state]);

  if (state !== 'ready' || !geo || !shapes || !p) return <div className="geomap-state" role={state === 'error' ? 'alert' : 'status'}>
    {state === 'loading' ? 'Loading map layers…' : <>Map layers unavailable. Run <code>python -B -m scripts.phase23_dashboard_geo</code> and reload.</>}</div>;

  const aois = filterAois(geo.aois, district);
  const scale = (ev: React.PointerEvent) => { const r = svg.current!.getBoundingClientRect(); return [W / r.width, H / r.height]; };
  const show = (ev: React.MouseEvent | React.FocusEvent, text: string) => {
    const r = svg.current!.getBoundingClientRect();
    const t = (ev.currentTarget as Element).getBoundingClientRect();
    setTip({x: t.left - r.left + t.width / 2, y: t.top - r.top, text});
  };
  const reset = () => setView(fitView((() => { const [w, s, e, n] = boundsOf(shapes.districts.flatMap(d => d.rings)); const [a, b] = p([w, n]), [c, d] = p([e, s]); return [a, b, c, d] as [number, number, number, number]; })()));
  const zoomBy = (f: number) => setView(v => zoomAt(v, f, W / 2, H / 2));

  return <div className="geomap">
    <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={'Study-area map: ' + (district === 'All districts' ? 'East and West Jaintia Hills' : district)}
      onPointerDown={ev => { (ev.target as Element).setPointerCapture?.(ev.pointerId); drag.current = {x: ev.clientX, y: ev.clientY, v: view}; }}
      onPointerMove={ev => { const d = drag.current; if (!d) return; const [sx, sy] = scale(ev); setView({...d.v, tx: d.v.tx + (ev.clientX - d.x) * sx, ty: d.v.ty + (ev.clientY - d.y) * sy}); }}
      onPointerUp={() => { drag.current = undefined; }} onPointerLeave={() => { drag.current = undefined; }}>
      <rect width={W} height={H} className="sea"/>
      <g transform={`translate(${view.tx} ${view.ty}) scale(${view.k})`}>
        {on.districts && shapes.districts.map(d => <path key={d.name} d={d.d}
          className={'district' + (district !== 'All districts' && d.name !== district ? ' dim' : '')} vectorEffect="non-scaling-stroke"/>)}
        {on.aois && aois.map(a => <path key={a.aoi} d={pathOf([a.ring], p)} className={'aoi d' + densityClass(a.density)} vectorEffect="non-scaling-stroke"
          tabIndex={0} aria-label={`AOI ${a.aoi}, ${a.district}, density ${a.density.toFixed(2)} ha per 100 ha, ${a.clusters} clusters`}
          onMouseEnter={e => show(e, `AOI ${a.aoi} · ${a.district} · ${a.split.toUpperCase()}\n${a.density.toFixed(2)} ha/100 ha · ${a.clusters} clusters`)}
          onFocus={e => show(e, `AOI ${a.aoi} · ${a.density.toFixed(2)} ha/100 ha · ${a.clusters} clusters`)}
          onMouseLeave={() => setTip(undefined)} onBlur={() => setTip(undefined)}/>)}
        {on.rivers && shapes.rivers.map(r => <path key={r.goid} d={r.d} className="river" strokeWidth={r.w} vectorEffect="non-scaling-stroke"/>)}
        {on.chains && shapes.chains.filter(c => c.supported).map(c => <path key={c.upstream} d={c.d} className="chain" vectorEffect="non-scaling-stroke"/>)}
        {on.stations && geo.stations.map(s => { const [x, y] = p(s.lonlat); return <g key={s.id} transform={`translate(${x} ${y}) scale(${1 / view.k})`}
          className="station" tabIndex={0} role="button" aria-label={`CPCB station ${s.name} ${s.code}, ${s.river} river`}
          onMouseEnter={e => show(e, `${s.river} · ${s.name} (CPCB ${s.code})`)} onFocus={e => show(e, `${s.river} · ${s.name} (CPCB ${s.code})`)}
          onMouseLeave={() => setTip(undefined)} onBlur={() => setTip(undefined)}>
          <circle r={6}/><text x={9} y={4}>{s.name}</text></g>; })}
      </g>
    </svg>
    {tip && <div className="geotip" style={{left: tip.x, top: tip.y}} role="tooltip">{tip.text}</div>}
    <div className="geozoom" role="group" aria-label="Map zoom">
      <button aria-label="Zoom in" onClick={() => zoomBy(1.4)} disabled={view.k >= 12}><Plus size={17}/></button>
      <button aria-label="Zoom out" onClick={() => zoomBy(1 / 1.4)} disabled={view.k <= 1}><Minus size={17}/></button>
      <button aria-label="Reset view" onClick={reset}><RotateCcw size={15}/></button>
    </div>
    <div className={'geolayers' + (panel ? '' : ' closed')}>
      <button className="geolayers-toggle" onClick={() => setPanel(!panel)} aria-expanded={panel}><Layers size={15}/> Layers</button>
      {panel && <>
        {LAYERS.map(([k, label, note]) => <label key={k} className={'layer l-' + k}>
          <input type="checkbox" checked={on[k]} onChange={() => setOn({...on, [k]: !on[k]})}/>
          <span className="swatch" aria-hidden/><span>{label}<small>{note}</small></span></label>)}
        {on.aois && <div className="ramp" aria-label="AOI candidate density classes, ha per 100 ha">
          {DENSITY_LABELS.map((l, i) => <span key={l}><i className={'d' + i}/>{l}</span>)}<small>ha / 100 ha · fixed classes {DENSITY_BREAKS.slice(1).join(' / ')}</small></div>}
        <small className="unavail">Not shown: {geo.unavailable.join('; ')}.</small>
      </>}
    </div>
    <div className="geonote">GAUL 2025 · HydroSHEDS FFR (modelled) · CPCB · Phase 22X — offline vector map, no basemap tiles</div>
  </div>;
}
