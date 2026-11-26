export type Matrix=(number|null)[][];
export type Part={contributions:Matrix[];valid:boolean[][];competitors:Matrix[]};
export const families=['vegetation','soil','sar','persistence','terrain','geology','environment'];
export function calculate(p:Part|undefined,weights:number[],threshold:number){
 if(!p)return null;
 const h=p.valid.length,w=p.valid[0].length,n=h*w,total=weights.reduce((a,b)=>a+b,0);
 const score=Array(n).fill(NaN) as number[],coverage=Array(n).fill(0) as number[],uncertainty=Array(n).fill(1) as number[],contributions=families.map(()=>Array(n).fill(0) as number[]),mask=Array(n).fill(false) as boolean[];
 if(total<=0)return {score,coverage,uncertainty,contributions,mask,clusters:[] as number[][]};
 for(let k=0;k<n;k++){
  const r=Math.floor(k/w),c=k%w,values=p.contributions.map(a=>a[r][c]);
  coverage[k]=values.reduce<number>((s,v,i)=>s+(v===null?0:weights[i]/total),0);
  if(coverage[k]>0)for(let i=0;i<7;i++)contributions[i][k]=(values[i]??0)*weights[i]/total/coverage[k]*100;
  if(p.valid[r][c]&&coverage[k]>=.6)score[k]=contributions.reduce((s,a)=>s+a[k],0);
  const alternate=Math.max(0,...p.competitors.map(a=>(a[r][c]??0)*100));
  mask[k]=Number.isFinite(score[k])&&score[k]>=threshold&&(values[0]??0)>=.25&&(values[1]??0)>=.25&&score[k]-alternate>=10;
  const v=values.map(x=>x??0),mean=v.reduce((a,b)=>a+b,0)/7,sd=Math.sqrt(v.reduce((a,b)=>a+(b-mean)**2,0)/7);uncertainty[k]=Math.max(0,Math.min(1,1-coverage[k]+.25*sd));
 }
 const seen=new Uint8Array(n),clusters:number[][]=[];
 for(let k=0;k<n;k++){if(!mask[k]||seen[k])continue;const q=[k];seen[k]=1;for(let a=0;a<q.length;a++){const i=q[a],r=Math.floor(i/w),c=i%w;for(const [rr,cc] of [[r-1,c],[r+1,c],[r,c-1],[r,c+1]]){const j=rr*w+cc;if(rr>=0&&rr<h&&cc>=0&&cc<w&&mask[j]&&!seen[j]){seen[j]=1;q.push(j);}}}if(q.length>=4)clusters.push(q);else for(const i of q)mask[i]=false;}
 return {score,coverage,uncertainty,contributions,mask,clusters};
}
