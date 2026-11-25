import {useEffect, useState} from 'react';

type Metrics = {confusion_matrix: number[][]; precision: number|null; recall: number|null; dice_f1: number|null; iou: number|null; fpr: number|null};
type Patch = {id: string; group: string; split: string; crs: string; bounds: number[]; shape: number[]; assets: Record<string,string>; prediction_sha256: string; support: number; predicted_cells: number};
type ClassMetric = {precision: number|null; recall: number|null; f1: number|null; iou: number|null; fpr: number|null; support: number; predicted: number};
type MultiMetric = {confusion_matrix: number[][]; macro_f1: number|null; support: number; classes: Record<string,ClassMetric>};
type Model = {kind?: string; multiclass_metrics?: {pooled: MultiMetric; per_group: Record<string,MultiMetric>}; id: string; metrics: Record<string,{pooled: Metrics; per_group: Record<string,Metrics>}>; checkpoint_sha256: string; patches: Patch[]};
type Data = {multiclass_majority_macro_f1?: number; models: Model[]; default_model: string; status: string; operational_alerts: number; threshold: number; windows: string[][]; limitations: string; attribution: string};
const prefix='/__experimental__/';
const fmt=(v: number|null|undefined)=>v==null?'Undefined':v.toFixed(4);
export function ExperimentalPredictions() {
  const [data,setData]=useState<Data>();const [failed,setFailed]=useState(false);
  const [modelId,setModel]=useState('');const [patchId,setPatch]=useState('');
  const [layer,setLayer]=useState('binary');const [opacity,setOpacity]=useState(.7);
  useEffect(()=>{const c=new AbortController();fetch(prefix+'snapshot.json',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('Unavailable');return r.json();}).then(({data:d}: {data: Data})=>{
    if(d.status!=='NOT_VALIDATED'||d.operational_alerts!==0||d.threshold!==.5||!d.models.length||d.models.some(m=>m.patches.some(p=>p.split!=='validation')))throw Error('Invalid experimental status');setData(d);
  }).catch(()=>{if(!c.signal.aborted)setFailed(true);});return()=>c.abort();},[]);
  const model=data?.models.find(m=>m.id===(modelId||data.default_model))??data?.models[0];
  const patch=model?.patches.find(p=>p.id===patchId)??model?.patches.find(p=>p.predicted_cells>0)??model?.patches[0];
  return <>
    <div className="toolbar"><b>Experimental disturbance predictions</b><a href="#explorer">Satellite Explorer</a><span className="badge neutral">NOT VALIDATED</span></div>
    {!data?<p role="status">{failed?'Saved model snapshot unavailable. Generate it with python -B -m scripts.phase25_model_portal, then launch python -B -m scripts.phase8_planet_portal and open this view on port 5188.':'Loading saved experimental predictions…'}</p>:<div className="explorer">
      <aside className="explorer-analysis">
        <label>Experimental run<select value={model?.id} onChange={e=>{setModel(e.target.value);setLayer('binary');}}>{data.models.map(m=><option key={m.id}>{m.id}</option>)}</select></label>
        <label>VAL patch<select value={patch?.id} onChange={e=>setPatch(e.target.value)}>{model?.patches.map(p=><option key={p.id} value={p.id}>{p.id} · {p.predicted_cells} predicted cells</option>)}</select></label>
        <label>Prediction layer<select value={layer} onChange={e=>setLayer(e.target.value)}><option value="binary">{model?.kind==='multiclass'?'Three-class prediction (argmax)':'Fixed 0.50 candidate overlay'}</option><option value="probability">Uncalibrated probability</option>{model?.kind==='multiclass'&&<option value="weak">Weak pseudo-label (not truth)</option>}<option value="none">Imagery only</option></select></label>
        <label>Layer opacity<input type="range" min="0" max="1" step=".05" value={opacity} onChange={e=>setOpacity(+e.target.value)}/></label>
        <p>Saved VAL products only. No live inference. No TEST data.</p>
      </aside>
      <section className="explorer-main">
        <p className="notice">Agreement with algorithm-generated pseudo-labels — NOT verified mining detection accuracy. Operational alerts: 0. Candidate attribution: UNKNOWN.</p>
        {patch&&<><div className="explorer-map" role="region" aria-label="Before and after with experimental prediction overlay">
          <div className="explorer-map-head"><span>Before / after seasonal composites</span><span>{patch.crs} · North ↑</span></div>
          <div style={{display:'flex',gap:16,padding:16,width:'100%',boxSizing:'border-box'}}>{['before','after'].map((season,i)=><div key={season} style={{width:'50%',minWidth:0}}><p>{season} · {data.windows[i].join(' to ')} (end exclusive)</p>
            <svg viewBox="0 0 32 32" width="100%" style={{maxHeight:350}} aria-label={season+' saved 30 m image'}>
              <image href={prefix+patch.assets[season]} width="32" height="32" style={{imageRendering:'pixelated'}}/>
              {season==='after'&&layer!=='none'&&patch.assets[layer]&&<image href={prefix+patch.assets[layer]} width="32" height="32" opacity={opacity} style={{imageRendering:'pixelated'}}/>}
            </svg></div>)}</div>
          <div className="explorer-legend">RGB B4/B3/B2 · 0–0.30 reflectance. {model?.kind==='multiclass'?'Grey: stable; amber: persistent unattributed exposure; cyan: other transient. Probability view shows maximum class score (uncalibrated). Transparent: NoData/ignored target.':layer==='binary'?'Amber: prediction ≥0.50; transparent: below cutoff or NoData.':layer==='probability'?'Blue/purple low → yellow high, 0–1; uncalibrated.':'No prediction overlay.'}</div>
        </div><p>{patch.support} common-input cells; {patch.predicted_cells} predicted {model?.kind==='multiclass'?'non-stable cells (argmax)':'cells at 0.50'}. Display includes uncertain pseudo-target areas; evaluated support is smaller. Block {patch.group}, VAL. Bounds (m): {patch.bounds.join(' / ')}.</p></>}
        <h3>Pseudo-label agreement (all 12 VAL patches)</h3>{model?.multiclass_metrics?<><p>Constant TRAIN-majority baseline macro-F1: {fmt(data.multiclass_majority_macro_f1)}. Frozen multiclass rule generates the targets using future observations, so is not a comparable predictive baseline.</p><MulticlassResults value={model.multiclass_metrics}/></>:<>
        <div style={{overflowX:'auto'}}><table><thead><tr><th>Cutoff</th><th>TN / FP / FN / TP</th><th>Precision</th><th>Recall</th><th>F1/Dice</th><th>IoU</th><th>FPR</th></tr></thead><tbody>{Object.entries(model?.metrics??{}).map(([t,{pooled:m}])=><tr key={t}><td>{t}</td><td>{[...m.confusion_matrix[0],...m.confusion_matrix[1]].join(' / ')}</td><td>{fmt(m.precision)}</td><td>{fmt(m.recall)}</td><td>{fmt(m.dice_f1)}</td><td>{fmt(m.iou)}</td><td>{fmt(m.fpr)}</td></tr>)}</tbody></table></div>
        <details><summary>Per-group results at fixed 0.50</summary>{Object.entries(model?.metrics['0.5'].per_group??{}).map(([g,m])=><p key={g}>{g}: TN/FP/FN/TP {[...m.confusion_matrix[0],...m.confusion_matrix[1]].join('/')} · F1 {fmt(m.dice_f1)} · recall {fmt(m.recall)} · FPR {fmt(m.fpr)}</p>)}</details></>}
      </section>
      <aside className="explorer-details"><h2>Research limitations</h2><p>{data.limitations}</p><p>Zero false positives against weak pseudo-labels does not establish specificity against independently verified mining references. A zero-positive group has undefined recall.</p><p>{model?.kind==='multiclass'?'Three-class argmax; no threshold tuning. Future follow-up is annotation-only. No agriculture, construction or verified mining class is learned.':'Recovery settings used TRAIN only; fixed 0.50. Threshold sensitivity is descriptive, not a new operating cutoff.'}</p><details><summary>Provenance</summary><p>{data.attribution}</p><p>Checkpoint SHA-256</p><code style={{overflowWrap:'anywhere'}}>{model?.checkpoint_sha256}</code><p>Prediction SHA-256</p><code style={{overflowWrap:'anywhere'}}>{patch?.prediction_sha256}</code><p>Original scene identity certification remains incomplete.</p></details></aside>
    </div>}
  </>;
}

function MulticlassResults({value}:{value:{pooled:MultiMetric;per_group:Record<string,MultiMetric>}}) {
  const names:Record<string,string>={'0':'Stable','1':'Persistent unattributed exposure','4':'Other transient'};
  return <><p>Macro-F1 {fmt(value.pooled.macro_f1)}; {value.pooled.support} evaluated weak-labelled pixels. Predictions are argmax, original class order 0 / 1 / 4.</p><div style={{overflowX:'auto'}}><table><thead><tr><th>Weak class</th><th>Support</th><th>Predicted</th><th>Precision</th><th>Recall</th><th>F1</th><th>IoU</th><th>FPR</th></tr></thead><tbody>{Object.entries(value.pooled.classes).map(([c,m])=><tr key={c}><td>{names[c]}</td><td>{m.support}</td><td>{m.predicted}</td><td>{fmt(m.precision)}</td><td>{fmt(m.recall)}</td><td>{fmt(m.f1)}</td><td>{fmt(m.iou)}</td><td>{fmt(m.fpr)}</td></tr>)}</tbody></table></div><p>Confusion matrix (actual rows / predicted columns): {value.pooled.confusion_matrix.map(r=>'['+r.join(', ')+']').join(' ')}</p><details><summary>Per-spatial-group multiclass agreement</summary>{Object.entries(value.per_group).map(([g,m])=><p key={g}>{g}: macro-F1 {fmt(m.macro_f1)}; confusion {m.confusion_matrix.map(r=>'['+r.join(', ')+']').join(' ')}. Absent-class recall is undefined.</p>)}</details></>;
}
