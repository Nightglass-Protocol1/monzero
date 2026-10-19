import {validateHistory,historyFreshness,ranges} from './history.mjs';
const $=id=>document.getElementById(id);
const date=n=>new Date(n*1000).toISOString().replace('T',' ').replace('.000Z',' UTC');
const number=n=>n.toLocaleString(undefined,{maximumFractionDigits:2});
let generation=0,controller,current;
function status(){
 if(!current)return;
 const state=historyFreshness(current);
 const message=({recent:'Recent observations.',stale:'Historical data — collection or export is over five minutes old.',empty:'No observations have been collected.', 'clock-mismatch':'Clock mismatch — this export is ahead of your browser clock; freshness cannot be verified.'})[state]+(current.points.length?'':' No samples in this selected range.');
 if($('status').textContent!==message)$('status').textContent=message;
}
function svgElement(name,attributes,text){const el=document.createElementNS('http://www.w3.org/2000/svg',name);for(const [k,v] of Object.entries(attributes))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;return el;}
function chart(id,key,label){
 const d=current,svg=svgElement('svg',{viewBox:'0 0 900 240',role:'img','aria-label':`${label}. Individual bucket averages; detailed values in the table below.`});
 const start=ranges[d.range]===null?(d.archive_first_observed_at??d.generated_at):Math.max(0,d.generated_at-ranges[d.range]);
 const span=Math.max(1,d.generated_at-start),maximum=Math.max(1,...d.points.map(p=>p[key]));
 svg.append(svgElement('line',{x1:100,y1:190,x2:880,y2:190,class:'axis'}));
 svg.append(svgElement('text',{x:0,y:20},number(maximum)),svgElement('text',{x:75,y:190},'0'),svgElement('text',{x:100,y:225},date(start)),svgElement('text',{x:880,y:225,'text-anchor':'end'},date(d.generated_at)));
 for(const p of d.points){const qualified=!p.all_samples_synchronized||p.maximum_tip_age_seconds>300||p.minimum_tip_age_seconds<0;
 const dot=svgElement('circle',{cx:100+((p.first_observed_at+p.last_observed_at)/2-start)/span*780,cy:190-p[key]/maximum*165,r:qualified?6:4,class:qualified?'qualified':'sample'});
 dot.append(svgElement('title',{},`${date(p.first_observed_at)} to ${date(p.last_observed_at)}: ${number(p[key])}; ${p.samples} samples${qualified?'; includes qualified observations':''}`));svg.append(dot);}
 const summary=document.createElement('p');summary.textContent=`Highest bucket mean: ${number(maximum)} ${key==='mean_estimated_hashrate_hps'?'H/s':'difficulty'}. Range: ${date(start)} to ${date(d.generated_at)}.`;$(id).replaceChildren(summary,svg);
}
function render(){
 status();const d=current;
 $('coverage').textContent=`Exported ${date(d.generated_at)}. Source: ${d.sources[0]==='preview'?'mainnet via local preview adapter':d.sources[0]==='live'?'mainnet via public site adapter':'none'}. Archive: ${d.archive_samples} observations${d.archive_samples?`, ${date(d.archive_first_observed_at)} to ${date(d.archive_last_observed_at)}`:''}. Bucket width: ${d.bucket_seconds} seconds.`;
 $('results').hidden=!d.points.length;
 chart('hash-chart','mean_estimated_hashrate_hps','Estimated network hashrate in hashes per second');chart('difficulty-chart','mean_difficulty','Mining difficulty');
 const rows=d.points.map(p=>{const tr=document.createElement('tr');for(const value of [`${date(p.first_observed_at)} / ${date(p.last_observed_at)}`,`${p.samples} / ${p.synchronized_samples}`,number(p.mean_estimated_hashrate_hps),`${p.minimum_difficulty} / ${p.maximum_difficulty}`,`${p.minimum_height} / ${p.maximum_height}`,`${p.minimum_tip_age_seconds} / ${p.maximum_tip_age_seconds}`,!p.all_samples_synchronized||p.maximum_tip_age_seconds>300||p.minimum_tip_age_seconds<0?'Includes qualified observations':'Synchronized; tip age within 0–300 seconds']){const td=document.createElement(tr.children.length?'td':'th');if(!tr.children.length)td.scope='row';td.textContent=value;tr.append(td);}return tr;});$('rows').replaceChildren(...rows);
}
async function readBounded(response){
 const reader=response.body.getReader(),chunks=[];let size=0;
 try{while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>1048576)throw Error('Oversized');chunks.push(value);}}
 catch(error){await reader.cancel().catch(()=>{});throw error;}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
 return new TextDecoder('utf-8',{fatal:true}).decode(bytes);
}
async function load(){
 const id=++generation;controller?.abort();controller=new AbortController();const active=controller;const timeout=setTimeout(()=>active.abort(),10000);
 current=null;$('results').hidden=true;$('coverage').textContent='';$('status').textContent='Loading observations…';
 try{const range=$('range').value;const response=await fetch(`data/${range}.json`,{signal:active.signal,cache:'no-cache'});if(!response.ok)throw Error('Unavailable');const raw=await readBounded(response);const data=validateHistory(JSON.parse(raw),range);if(id!==generation)return;current=data;render();}
 catch{if(id===generation){current=null;$('results').hidden=true;$('coverage').textContent='';$('status').textContent='Network history is unavailable. Try Refresh later; no missing values have been replaced with estimates.';}}
 finally{clearTimeout(timeout);}
}
$('range').disabled=false;$('refresh').disabled=false;$('range').addEventListener('change',load);$('refresh').addEventListener('click',load);setInterval(status,30000);load();
