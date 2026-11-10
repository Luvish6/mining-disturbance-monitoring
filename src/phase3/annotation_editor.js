(function () {
  const map = __MAP__, group = __GROUP__, candidates = __CANDIDATES__;
  const initial = __FEATURES__, imagery = __IMAGERY__;
  let selected = null;
  const status = document.getElementById('annotation-status');
  const editor = document.getElementById('evidence-properties');
  const candidate = document.getElementById('candidate-id');
  const blank = document.createElement('option'); blank.value=''; blank.textContent='Choose a recorded candidate'; candidate.appendChild(blank);
  for (const row of candidates) {
    const option=document.createElement('option'); option.value=row.candidate_id; option.textContent=row.candidate_id; candidate.appendChild(option);
    const paragraph=document.createElement('p'); paragraph.textContent=(row.site_name||row.candidate_id)+': '+row.evidence+' ';
    const source=document.createElement('a');source.href=row.source_url;source.textContent='Original source';source.target='_blank';source.rel='noopener noreferrer';paragraph.appendChild(source);
    document.getElementById('candidate-leads').appendChild(paragraph);
  }
  document.getElementById('imagery-record').textContent=JSON.stringify(imagery,null,2);
  function fresh() { return {label_id:crypto.randomUUID(),candidate_id:null,site_id:null,label:null,
    source:null,provenance:null,interpretation_date:null,reviewer:null,reviewed:false,confidence:null,
    synthetic:false,independent_reference:false,target_definition:'new_mining_related_disturbance_2023_2025',
    before_evidence_date:null,after_evidence_date:null,spatial_accuracy_m:null,evidence_urls:[],
    independent_evidence_note:null,evidence_license_note:null,annotation_state:'draft'}; }
  function select(layer) {
    selected=layer; editor.value=JSON.stringify(layer.feature.properties,null,2);
    candidate.value=layer.feature.properties.candidate_id||'';
    status.textContent='Selected '+layer.feature.properties.label_id+' (draft editing)';
  }
  function bind(layer,feature) {
    layer.feature={type:'Feature',properties:feature.properties||fresh()};
    layer.on('click',()=>select(layer));
  }
  function load(data) {
    if (data.type!=='FeatureCollection'||data.crs||!Array.isArray(data.features)) throw new Error('Use WGS84 GeoJSON FeatureCollection');
    if (data.features.some(f=>!f.geometry||!['Polygon','MultiPolygon'].includes(f.geometry.type))) throw new Error('Polygons only');
    group.clearLayers();
    L.geoJSON(data,{onEachFeature:(feature,layer)=>{bind(layer,feature);group.addLayer(layer);}});
    selected=null;editor.value='';status.textContent='Loaded '+data.features.length+' drafts; save before closing.';
  }
  load({type:'FeatureCollection',features:initial});
  map.on('draw:created',event=>{bind(event.layer,{properties:fresh()}); select(event.layer);});
  map.on('draw:deleted',()=>{selected=null;editor.value='';status.textContent='Deleted polygons are removed from the downloaded draft.';});
  function applyMetadata() {
      if(!selected) throw new Error('Select a polygon first');
      const properties=JSON.parse(editor.value);
      properties.candidate_id=candidate.value||null;
      if(!properties.label_id) throw new Error('A stable label_id is required');
      properties.annotation_state='draft';properties.reviewed=false;delete properties.second_reviewer;delete properties.review_snapshot;
      selected.feature.properties=properties;editor.value=JSON.stringify(properties,null,2);status.textContent='Draft metadata updated. Download to save.';
  }
  document.getElementById('apply-metadata').onclick=()=>{
    try{applyMetadata();}catch(error){status.textContent=error.message;}
  };
  document.getElementById('session-file').onchange=async event=>{
    try{load(JSON.parse(await event.target.files[0].text()));}catch(error){status.textContent=error.message;}
  };
  document.getElementById('save-drafts').onclick=()=>{
    try{if(selected)applyMetadata();}catch(error){status.textContent=error.message;return;}
    const value=group.toGeoJSON();
    const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/geo+json'}));
    const a=document.createElement('a');a.href=url;a.download='annotation-drafts-'+Date.now()+'.geojson';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    status.textContent='Draft downloaded. Import it with the project command before review.';
  };
})();
