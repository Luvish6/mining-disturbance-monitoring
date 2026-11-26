// Offline invocation of the actual frontend scorer across all frozen patches/configurations.
import fs from 'node:fs';
import path from 'node:path';
import {calculate,families} from '../frontend/src/studio-math.ts';
const root=process.argv[2],m=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'))),cfg=JSON.parse(fs.readFileSync(path.join(root,'config.json')));
for(const r of m.patches){
 const d=JSON.parse(fs.readFileSync(path.join(root,r.folder,'studio.json')));
 for(const mode of ['pair','retrospective'])for(const [preset,base] of Object.entries({equal:Array(7).fill(1/7),physical:[.25,.25,.20,.15,.025,.05,.075],adaptive:cfg.adaptive_weights[mode]}))for(const ablation of ['none',...families]){
  const weights=[...base];if(ablation!=='none')weights[families.indexOf(ablation)]=0;
  const result=calculate(d.modes[mode],weights,60);
  process.stdout.write(JSON.stringify({id:r.patch_id,mode,preset,ablation,score:result.score,mask:result.mask})+'\n');
 }
}
