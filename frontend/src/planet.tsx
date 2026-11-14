import {useEffect, useRef, useState} from 'react';
import {ClipboardCheck, Crosshair, Minus, Plus} from 'lucide-react';
import './planet.css';

type Scene = {id: string; acquired: string; roi_cells: number; valid: number; clear: number; sun_elevation: number;
  sun_azimuth: number; view_angle: number; flags: Record<string, number>; zip_sha256: string};
type Evidence = {scenes: Scene[]; medians: number[]; common: number; crs: string; extent: number[];
  marker: number[]; coordinates: number[]; radius: number; receipt: string; statistics: string};
const privatePath = '/__planet_review__/';
const date = (item: Scene) => item.acquired.slice(0,10);

export function PlanetReview() {
  const [data, setData] = useState<Evidence>();
  const [unavailable, setUnavailable] = useState(false);
  const [layer, setLayer] = useState('rgb');
  const [mode, setMode] = useState('paired');
  const [swipe, setSwipe] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState([0,0]);
  const [missing, setMissing] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const drag = useRef<{x: number; y: number; start: number[]} | undefined>(undefined);
  useEffect(()=>{
    const controller = new AbortController();
    if(location.protocol !== 'http:' || location.hostname !== '127.0.0.1') {
      setUnavailable(true);
      return;
    }
    fetch(privatePath+'receipt.json',{signal:controller.signal,cache:'no-store'})
      .then(response=>{if(!response.ok)throw Error('Unavailable');return response.json();})
      .then(value=>{if(value.scenes?.length!==2 || value.marker?.length!==2)throw Error('Invalid receipt');setData(value);})
      .catch(()=>{if(!controller.signal.aborted)setUnavailable(true);});
    return ()=>controller.abort();
  },[]);
  const reset = () => {setPan([0,0]);setZoom(1);};
  const move = (x: number,y: number) => setPan(([px,py])=>[px+x,py+y]);
  function panel(items: number[], title: string, clipped=false) {
    if(!data)return null;
    return <section className="planet-panel" key={title}><h3>{title}</h3>
      <div className="planet-map" tabIndex={0} aria-label={title+' map. Use arrow keys to pan.'}
        onPointerDown={e=>{if(e.button!==0)return;drag.current={x:e.clientX,y:e.clientY,start:pan};e.currentTarget.setPointerCapture(e.pointerId);}}
        onPointerMove={e=>{const start=drag.current;if(start)setPan([start.start[0]+e.clientX-start.x,start.start[1]+e.clientY-start.y]);}}
        onLostPointerCapture={()=>{drag.current=undefined;}}
        onKeyDown={e=>{
          const axes: Record<string,number[]>={ArrowLeft:[-24,0],ArrowRight:[24,0],ArrowUp:[0,-24],ArrowDown:[0,24]};
          const step=axes[e.key];if(step){e.preventDefault();move(step[0],step[1]);}
        }}>
        {items.map((i,j)=>{
          const file=layer==='difference'?'difference.png':layer+'-'+i+'.png';
          return <div key={file} className="planet-clip" style={{clipPath:clipped&&j===1?'inset(0 0 0 '+swipe+'%)':undefined}}>
            <div className="planet-grid" style={{transform:'translate('+pan[0]+'px,'+pan[1]+'px) scale('+zoom+')'}}>
              {missing.includes(file)?<div className="planet-missing">Verified layer unavailable</div>:
                <img src={privatePath+file} draggable={false} alt={title+' '+layer+' image'}
                  onError={()=>setMissing(items=>items.includes(file)?items:[...items,file])}/>}
              <span className="planet-ring" style={{left:data.marker[0]*100+'%',top:data.marker[1]*100+'%',
                width:2*data.radius/648*100+'%'}}/>
              <span className="planet-marker" aria-label="KORPET" style={{left:data.marker[0]*100+'%',top:data.marker[1]*100+'%'}}>+</span>
            </div>
          </div>;
        })}
        {clipped && <div className="planet-divider" style={{left:swipe+'%'}}/>}
      </div>
    </section>;
  }
  return <>
    <div className="toolbar"><ClipboardCheck size={18}/><b>Reference Review</b><span>/</span><span>KORPET</span><span className="badge neutral">Private · local only</span></div>
    <div className="planet-workspace">
      <aside className="planet-queue"><h1>Review queue</h1><div className="notice">KORPET · UNKNOWN</div>
        <p>One evidence pair for diagnostic review.</p>
        {data?.scenes.map((scene,i)=><button key={scene.id} aria-pressed={mode===String(i)}
          disabled={layer==='difference'} onClick={()=>setMode(String(i))}><strong>{i===0?'Before':'After'} · {date(scene)}</strong><small>{scene.id}</small></button>)}
        {data && <p>{data.coordinates[1]}° N · {data.coordinates[0]}° E</p>}
      </aside>
      <section className="planet-center"><h2>Visual reference comparison</h2>
        {!data ? <p role="status">{unavailable ? <>Private review unavailable. Build the portal and start <code>python -B -m scripts.phase8_planet_portal</code> with the verified local products.</>:'Checking local evidence…'}</p> : <>
          <div className="planet-controls">
            <label>Layer <select value={layer} onChange={e=>setLayer(e.target.value)}>
              <option value="rgb">RGB · fixed stretch</option><option value="ndvi">NDVI</option><option value="difference">Paired NDVI difference</option>
            </select></label>
            <label>View <select value={layer==='difference'?'difference':mode} disabled={layer==='difference'} onChange={e=>setMode(e.target.value)}>
              {layer==='difference' && <option value="difference">Difference</option>}
              <option value="paired">Side by side</option><option value="swipe">Swipe</option><option value="0">Before</option><option value="1">After</option>
            </select></label>
            <button aria-label="Zoom in" onClick={()=>setZoom(Math.min(8,zoom*1.4))}><Plus size={16}/></button>
            <button aria-label="Zoom out" onClick={()=>setZoom(Math.max(1,zoom/1.4))}><Minus size={16}/></button>
            <button aria-label="Reset map view" onClick={reset}><Crosshair size={16}/></button>
          </div>
          {layer!=='difference' && mode==='swipe' && <label className="planet-swipe">Swipe position <input type="range" min="0" max="100" value={swipe} onChange={e=>setSwipe(+e.target.value)}/></label>}
          <div className={'planet-comparison'+(layer!=='difference' && mode==='paired'?' planet-paired':'')}>
            {layer==='difference' ? panel([0],'After minus before') : mode==='paired' ?
              data.scenes.map((s,i)=>panel([i],date(s))) : mode==='swipe' ?
              panel([0,1],date(data.scenes[0])+' / '+date(data.scenes[1]),true) : panel([+mode],date(data.scenes[+mode]))}
          </div>
          <p>North ↑ · Native 3 m cells · {data.crs} · Cyan cross and ring mark KORPET and the {data.radius} m radius.</p>
          <p>{layer==='rgb'?'RGB bands 6 / 4 / 2 · stored-value stretch 0–3500 · masked cells are transparent.':
            layer==='ndvi'?'NDVI (unitless) · brown −1, pale 0, green +1 · common clear cells inside 300 m.':
              'After minus before (unitless) · blue ≤−0.25, pale 0, red ≥+0.25 · common clear cells inside 300 m.'}</p>
          <h2>Evidence register</h2>
          <div className="table-scroll"><table><thead><tr><th>Scene / acquired UTC</th><th>Valid SR cells</th><th>UDM2-clear cells</th><th>Median NDVI</th></tr></thead>
            <tbody>{data.scenes.map((s,i)=><tr key={s.id}><td>{s.id}<br/>{s.acquired}</td>
              <td>{s.valid.toLocaleString()} / {s.roi_cells.toLocaleString()}</td><td>{s.clear.toLocaleString()} / {s.roi_cells.toLocaleString()}</td>
              <td>{data.medians[i].toFixed(4)}</td></tr>)}</tbody></table></div>
          <p>Paired median NDVI change {data.medians[2]>=0?'+':''}{data.medians[2].toFixed(4)} · {data.common.toLocaleString()} common clear cells within 300 m.</p>
          <details><summary>Image quality and acquisition geometry</summary>{data.scenes.map(s=><p key={s.id}>
            {date(s)} · solar elevation {s.sun_elevation}°, solar azimuth {s.sun_azimuth}°, view angle {s.view_angle}°.
            {' UDM2 flags within 300 m: '+Object.entries(s.flags).map(([key,n])=>key.replaceAll('_',' ')+' '+n).join(', ')}.
          </p>)}<p>Terrain and cast shadows can differ even when UDM2 cloud-shadow flags are clear.</p></details>
          <details id="review-methodology"><summary>Processing history and provenance</summary>
            <p>Native north-up window [{data.extent.join(', ')}] in receipt order west, east, south, north. Both SR/UDM2 grids and archives match the inspection receipts. NDVI uses NIR band 8 and red band 6. A common multiplicative scale cancels in the ratio. The viewer applies neither shifting nor reprojection.</p>
            <p>Inspection SHA-256 {data.receipt}<br/>Statistics SHA-256 {data.statistics}</p>
            {data.scenes.map(s=><p key={s.id}>{s.id} archive SHA-256 {s.zip_sha256}</p>)}
          </details>
        </>}
      </section>
      <aside className="planet-worksheet">
        <h2>Review worksheet</h2><h3>Reference status · UNKNOWN</h3>
        <p>Both dates show the southwest exposed-looking patch. Local tone and apparent edges differ. Illumination, terrain shadow, phenology, moisture and relative alignment remain plausible explanations. Land-cover change is inconclusive.</p>
        <details open><summary>Pending evidence and review</summary><ul>
          <li>Independent positional control · pending. Relative texture offsets are approximately 3–6.7 m. Document positional error ≤30 m with independent controls.</li>
          <li>Planet reviewer-use rights · unconfirmed.</li>
          <li>First reviewer · pending.</li><li>Independent second reviewer · pending.</li>
        </ul></details>
        <label htmlFor="planet-notes">Session notes</label>
        <textarea id="planet-notes" rows={7} maxLength={2000} value={notes} onChange={e=>setNotes(e.target.value)}
          placeholder="Record visible features, alternative explanations and evidence needed."/>
        <small>Notes stay in this tab until you leave the workspace or reload.</small>
      </aside>
    </div>
  </>;
}
