import {useEffect, useRef, useState} from 'react';
import {Crosshair, Layers, Minus, PanelLeft, Plus} from 'lucide-react';
import './explorer.css';

const bands = ['dVV', 'dVH', 'dNDVI', 'dNDTI'] as const;
const levels = ['low', 'middle', 'high'] as const;
type Level = typeof levels[number];
type Tile = {
  id: string; district: string; split: string; bounds: number[]; shape: number[]; common: number;
  layers: Record<typeof bands[number], (number | null)[]>;
  counts: Record<string, number[] | null>;
  overlaps: Record<Level, Record<string, number | null>>;
  overlays: Partial<Record<Level, number[]>>;
  sourceHashes: Record<string, string>;
};
type Data = {tiles: Tile[]; periods: string[][]; crs: string; spacing: number; overlapSha256: string};
const colors = [[45,57,69], [255,179,80], [100,212,221], [207,129,225]];
const overlapNames = ['Neither', 'SAR only', 'Optical only', 'Both'];
const overlapFields = ['neither', 'radar_only', 'optical_only', 'joint'];
const rgb = (color: number[]) => 'rgb('+color.join(',')+')';

export function Explorer() {
  const [data, setData] = useState<Data>();
  const [failed, setFailed] = useState(false);
  const [district, setDistrict] = useState('');
  const [id, setId] = useState('');
  const [band, setBand] = useState<typeof bands[number]>('dVV');
  const [level, setLevel] = useState<Level>('middle');
  const [overlay, setOverlay] = useState(false);
  const [visible, setVisible] = useState(true);
  const [opacity, setOpacity] = useState(1);
  const [collapsed, setCollapsed] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState([0,0]);
  const [sample, setSample] = useState('');
  const drag = useRef<{x: number; y: number; pan: number[]} | undefined>(undefined);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(import.meta.env.BASE_URL+'local/explorer.json', {signal: controller.signal})
      .then(response => { if (!response.ok) throw Error('Unavailable'); return response.json(); })
      .then(value => { if (value.tiles?.length !== 6) throw Error('Invalid roster'); setData(value); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, []);
  const districts = [...new Set(data?.tiles.map(item => item.district))];
  const activeDistrict = district || districts[0];
  const tiles = data?.tiles.filter(item => item.district === activeDistrict);
  const tile = tiles?.find(item => item.id === id) ?? tiles?.[0];
  const unit = band === 'dVV' || band === 'dVH' ? 'dB' : 'unitless';
  const limit = unit === 'dB' ? 5 : 0.3;
  const categories = overlay ? tile?.overlays[level] : undefined;
  const layer = tile?.layers[band];
  const stats = tile?.overlaps[level];
  const total = tile ? tile.shape[0]*tile.shape[1] : 0;
  const reset = () => {setZoom(1); setPan([0,0]); setSample('');};
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx || !tile || !layer) return;
    const frame = ctx.createImageData(tile.shape[1], tile.shape[0]);
    layer.forEach((value, index) => {
      if (value === null) return;
      const offset = index*4;
      if (categories) {
        frame.data.set(colors[categories[index]], offset);
      } else {
        const fraction = Math.min(Math.abs(value)/limit, 1);
        const edge = value < 0 ? [64,160,232] : [247,157,72];
        frame.data.set(edge.map(target => 235+(target-235)*fraction), offset);
      }
      frame.data[offset+3] = 255;
    });
    ctx.putImageData(frame, 0, 0);
  }, [tile, layer, limit, categories]);
  return <>
    <div className="toolbar"><Layers size={18}/><b>Satellite Explorer</b><span>/</span><span>Regional monitoring</span><span className="badge neutral">Exploratory</span></div>
    <div className={'explorer'+(collapsed?' analysis-closed':'')}>
      <aside className="explorer-analysis">
        <button className="explorer-toggle" aria-expanded={!collapsed} aria-label="Toggle analysis" onClick={()=>setCollapsed(!collapsed)}><PanelLeft size={17}/>{!collapsed && 'Analysis'}</button>
        {!collapsed && <>
          <label>District<select value={activeDistrict ?? ''} onChange={e=>{setDistrict(e.target.value); reset();}}>{districts.map(name=><option key={name}>{name}</option>)}</select></label>
          <label>Tile<select value={tile?.id ?? ''} onChange={e=>{setId(e.target.value); reset();}}>{tiles?.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
          <fieldset><legend>Signed changes</legend><div className="explorer-options">{bands.map(item=><button key={item} aria-pressed={item===band && !overlay} onClick={()=>{setBand(item);setOverlay(false);setSample('');}}>{item}</button>)}</div></fieldset>
          <fieldset><legend>Threshold sensitivity</legend><div className="explorer-options">{levels.map(item=><button key={item} aria-pressed={item===level} onClick={()=>{setLevel(item);setSample('');}}>{item}</button>)}</div>
            <p>{level === 'low' ? '1 dB / 0.03' : level === 'middle' ? '2 dB / 0.06' : '3 dB / 0.09'}</p>
          </fieldset>
          <label className="explorer-check"><input type="checkbox" checked={overlay} onChange={e=>{setOverlay(e.target.checked);setSample('');}}/> Show SAR–optical overlap</label>
          <label className="explorer-check"><input type="checkbox" checked={visible} onChange={e=>setVisible(e.target.checked)}/> Layer visible</label>
          <label>Opacity · {Math.round(opacity*100)}%<input type="range" min="0" max="1" step=".05" value={opacity} onChange={e=>setOpacity(+e.target.value)}/></label>
        </>}
      </aside>
      <section className="explorer-main">
        <div className="explorer-map" role="region" aria-label="Georeferenced change map" tabIndex={0}
          onKeyDown={e=>{
            const steps: Record<string, number[]> = {ArrowLeft:[-30,0],ArrowRight:[30,0],ArrowUp:[0,-30],ArrowDown:[0,30]};
            const step = steps[e.key];
            if (step) {e.preventDefault(); setPan(([x,y])=>[x+step[0],y+step[1]]);}
          }}
          onPointerDown={e=>{
            if (e.button!==0 || (e.target as HTMLElement).closest('button')) return;
            drag.current={x:e.clientX,y:e.clientY,pan};
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerUp={()=>{drag.current=undefined;}}
          onPointerCancel={()=>{drag.current=undefined;}}
          onPointerMove={e=>{
            const start=drag.current;
            if (start) {setPan([start.pan[0]+e.clientX-start.x,start.pan[1]+e.clientY-start.y]);return;}
            if (!tile || !layer || !canvas.current || (overlay && !categories) || !visible || !opacity) {setSample('');return;}
            const rect=canvas.current.getBoundingClientRect();
            const x=Math.floor((e.clientX-rect.left)/rect.width*tile.shape[1]);
            const y=Math.floor((e.clientY-rect.top)/rect.height*tile.shape[0]);
            if (x<0 || y<0 || x>=tile.shape[1] || y>=tile.shape[0]) {setSample('');return;}
            const index=y*tile.shape[1]+x;
            const value=layer[index];
            const east=tile.bounds[0]+(x+.5)*30, north=tile.bounds[3]-(y+.5)*30;
            setSample(east+' E · '+north+' N · '+(value===null?'NoData':categories?overlapNames[categories[index]]:value.toFixed(4)+' '+unit));
          }} onPointerLeave={()=>setSample('')}>
          <div className="explorer-map-head"><span>{tile?.id ?? 'Tile map'}</span><span>{data?.crs} · North ↑</span></div>
          {tile && <canvas ref={canvas} width={tile.shape[1]} height={tile.shape[0]} aria-label="Native change raster"
            style={{opacity:visible && (!overlay || categories)?opacity:0,transform:'translate('+pan[0]+'px,'+pan[1]+'px) scale('+zoom+')'}}/>}
          {(!tile || (overlay && !categories)) && <div className="explorer-empty">{failed ? <>Local tile data unavailable. Run <code>python -m scripts.phase8_explorer_data</code> from the project root.</> : tile ? 'Middle threshold has statistics only. Select low or high for a spatial overlay.' : 'Loading local tile data…'}</div>}
          <div className="explorer-legend">
            {overlay ? categories && overlapNames.map((name,i)=><span key={name}><i style={{background:rgb(colors[i])}}/>{name}</span>) :
              <><b>{band} · {unit}</b><div className="explorer-gradient"/><div className="explorer-ticks"><span>−{limit}</span><span>0</span><span>+{limit}</span></div></>}
            {tile && <small>Checked cells · NoData</small>}
          </div>
          <div className="explorer-zoom">
            <button aria-label="Zoom in" onClick={()=>setZoom(Math.min(8,zoom*1.4))}><Plus size={17}/></button>
            <button aria-label="Zoom out" onClick={()=>setZoom(Math.max(.5,zoom/1.4))}><Minus size={17}/></button>
            <button aria-label="Reset map view" onClick={reset}><Crosshair size={17}/></button>
          </div>
          <div className="explorer-coords">{sample || (tile ? 'Projected bounds (m) · '+tile.bounds.join(' / ') : '')}</div>
        </div>
        <div className="explorer-periods">{data?.periods.map(([start,end],i)=><div key={start}><small>{i===0?'BEFORE':'AFTER'}</small><strong>{start} → {end}</strong></div>)}</div>
      </section>
      <aside className="explorer-details">
        <h2>Cross-sensor overlap</h2><p>{level} threshold · Directional unions</p>
        {stats && <>
          <div className="explorer-bar" aria-label="SAR–optical overlap distribution">{overlapFields.map((key,i)=>
            <span key={key} style={{flexGrow:stats[key]??0,background:rgb(colors[i])}}/>)}</div>
          <dl>{overlapFields.map((key,i)=><div key={key}><dt>{overlapNames[i]}</dt><dd>{stats[key]?.toLocaleString()??'—'}</dd></div>)}
            <div><dt>Jaccard</dt><dd>{stats.jaccard?.toFixed(3)??'—'}</dd></div></dl>
        </>}
        <h2>Observation quality</h2>
        {tile && <><p>{tile.common.toLocaleString()} / {total.toLocaleString()} common-valid pixels ({(100*tile.common/total).toFixed(1)}%)</p>
          <dl>{Object.entries(tile.counts).map(([key, range])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{range?.join('–')??'—'}</dd></div>)}</dl></>}
        <details id="explorer-methodology"><summary>Methodology and provenance</summary>
          <p>After minus before on the native 30 m projected grid. Display colours clip at legend endpoints. Directional radar and optical unions use the saved Phase 7 Day 2 thresholds and the common-valid denominator. Date windows use an exclusive end.</p>
          <p>Sentinel-1 GRD and Sentinel-2 SR Harmonized. Frozen split: {tile?.split ?? '—'}. KORPET reference status: UNKNOWN.</p>
          {tile && <dl className="explorer-hashes">{Object.entries({...tile.sourceHashes,overlap:data?.overlapSha256}).map(([name,hash])=><div key={name}><dt>{name}</dt><dd>{hash}</dd></div>)}</dl>}
        </details>
        <p className="notice">Exploratory satellite change. Mining attribution remains unverified.</p>
      </aside>
    </div>
  </>;
}
