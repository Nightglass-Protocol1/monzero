// Renders /api/miner-stats/ (opt-in, pseudonymous, self-reported) as two rankings.
const $=id=>document.getElementById(id);
const LIMIT=50;
let busy=false;

export function validateReport(data,now=Date.now()/1000){
 if(!data||data.status!=='OK'||!Number.isInteger(data.generated_at)||!Array.isArray(data.miners)||data.miners.length>10000)throw Error('Invalid report');
 if(data.generated_at>now+300)throw Error('Report from the future');
 for(const m of data.miners){
  if(!m||typeof m.name!=='string'||!/^Miner [0-9A-F]{8}$/.test(m.name)||typeof m.hashrate!=='number'||!Number.isFinite(m.hashrate)||m.hashrate<0
   ||!Number.isInteger(m.blocks_found)||m.blocks_found<0||!Number.isInteger(m.last_seen)||m.last_seen>data.generated_at)throw Error('Invalid miner');
 }
 return data;
}

export function rank(miners,key){
 return [...miners].sort((a,b)=>b[key]-a[key]||a.name.localeCompare(b.name)).filter(m=>key!=='blocks_found'||m.blocks_found>0).slice(0,LIMIT);
}

export function formatRate(h){
 for(const [unit,size] of [['MH/s',1e6],['KH/s',1e3]])if(h>=size)return `${(h/size).toFixed(2)} ${unit}`;
 return `${h.toFixed(h<10?2:0)} H/s`;
}

function rows(target,list,cells,empty,columns){
 const tbody=$(target);
 if(!list.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=columns;td.textContent=empty;tr.append(td);tbody.replaceChildren(tr);return;}
 tbody.replaceChildren(...list.map((m,i)=>{const tr=document.createElement('tr');for(const v of cells(m,i)){const td=document.createElement('td');td.textContent=v;tr.append(td);}return tr;}));
}

async function load(){
 if(busy)return;busy=true;$('refresh').disabled=true;$('status').textContent='Loading reports…';
 try{
  const response=await fetch('/api/miner-stats/',{signal:AbortSignal.timeout(10000),cache:'no-store'});
  if(!response.ok)throw Error('Unavailable');
  const data=validateReport(await response.json());
  const age=s=>{const d=Math.max(0,data.generated_at-s);return d<60?`${d}s ago`:`${Math.round(d/60)} min ago`;};
  rows('by-hashrate',rank(data.miners,'hashrate'),(m,i)=>[String(i+1),m.name,formatRate(m.hashrate),age(m.last_seen)],'No opted-in miner is reporting right now.',4);
  rows('by-blocks',rank(data.miners,'blocks_found'),(m,i)=>[String(i+1),m.name,String(m.blocks_found)],'No active reporting miner has reported finding a block.',3);
  $('status').textContent=`${data.miners.length} opted-in miner${data.miners.length===1?'':'s'} reporting, ${formatRate(data.miners.reduce((s,m)=>s+m.hashrate,0))} in total. Updated ${new Date(data.generated_at*1000).toLocaleString()}.`;
 }catch{
  $('by-hashrate').replaceChildren();$('by-blocks').replaceChildren();
  $('status').textContent='The reporting service is unavailable. This does not mean nobody is mining. Try refreshing later.';
 }finally{busy=false;$('refresh').disabled=false;}
}
if(typeof document!=='undefined'){$('refresh').addEventListener('click',load);load();}
