const form=document.querySelector('#lookup'),address=document.querySelector('#address');
const status=document.querySelector('#status'),results=document.querySelector('#results');
const workers=document.querySelector('#workers'),payments=document.querySelector('#payments');
const auto=document.querySelector('#auto');let generation=0,controller=null,selected='';
const format=n=>typeof n==='number' && Number.isFinite(n)?new Intl.NumberFormat(undefined,{maximumSignificantDigits:7}).format(n):'Unavailable';
function atomic(value) {
  if(typeof value!=='string'||!/^(0|[1-9][0-9]{0,19})$/.test(value))return 'Unavailable';
  const padded=value.padStart(12,'0');return `${padded.slice(0,-11)}.${padded.slice(-11)} XMZ`;
}
function reset() {results.replaceChildren();workers.replaceChildren();payments.replaceChildren();document.querySelector('#worker-state').textContent='No current observation.';}
function cancel() {generation++;controller?.abort();controller=null;reset();}
async function lookup(value) {
  cancel();const id=generation;controller=new AbortController();const requestController=controller;const timer=setTimeout(()=>requestController.abort(),16000);
  status.textContent='Loading pool observation…';
  try {
    const response=await fetch('api.php',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({address:value}),signal:controller.signal,cache:'no-store',referrerPolicy:'no-referrer'});
    const data=await response.json();
    if(id!==generation)return;
    if(!response.ok || data.schema!=='monzero-pool-miner-view-v1')throw new Error(response.status===429?'Lookup limit reached. Try again in one minute.':'Pool observation unavailable. Try again later.');
    if(!Number.isSafeInteger(data.observed_at)||data.observed_at<=0)throw new Error('Pool timestamp unavailable.');
    status.textContent=`Pool response retrieved ${new Date(data.observed_at*1000).toLocaleString()}. This is a dated snapshot, not a live guarantee.`;
    const rows=[['Estimated ten-minute hashrate (H/s)',format(data.hashrate_hps)],['Connected workers',format(data.active_workers)],
      ['Pool contribution (%)',format(data.pool_share_percent)],['Pending pool rewards',atomic(data.pending_atomic)],['Total reported paid',atomic(data.paid_atomic)]];
    for(const [name,value] of rows){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name;dd.textContent=value;results.append(dt,dd);}
    if(Array.isArray(data.workers)) {
      for(const worker of data.workers){const li=document.createElement('li');li.textContent=worker.name;workers.append(li);}
      document.querySelector('#worker-state').textContent=data.workers.length?'Connection numbers apply only to this snapshot. Raw worker names are hidden because they may contain identifying login information. Individual hashrate and uptime are unavailable.':'No currently connected workers reported.';
    } else document.querySelector('#worker-state').textContent='Worker data unavailable.';
    if(Array.isArray(data.payments)) {
      for(const payment of data.payments) {
        if(!/^[0-9a-f]{64}$/.test(payment.txid))continue;
        const li=document.createElement('li'),link=document.createElement('a');
        link.href=`../../explorer/#/tx/${payment.txid}`;link.textContent=payment.txid;
        li.append(`${atomic(payment.amount_atomic)} · pool payment recorded ${new Date(payment.timestamp*1000).toLocaleString()} · `,link);payments.append(li);
      }
      if(!data.payments.length){const li=document.createElement('li');li.textContent='No sent payments returned by the pool.';payments.append(li);}
    } else {const li=document.createElement('li');li.textContent='Payment history unavailable.';payments.append(li);}
  } catch(error) {if(id===generation){reset();status.textContent=error.name==='AbortError'?'Lookup timed out. Try again later.':error.message;}}
  finally {clearTimeout(timer);if(id===generation)controller=null;}
}
form.addEventListener('submit',event=>{event.preventDefault();const value=address.value.trim();
  if(![95,106].includes(value.length)||!/^[1-9A-HJ-NP-Za-km-z]+$/.test(value)){cancel();selected='';status.textContent='Enter a public XMZ mining address. Do not enter keys or seed words.';return;}
  selected=value;lookup(value);
});
address.addEventListener('input',()=>{cancel();selected='';status.textContent='Address changed. Submit a new lookup.';});
document.querySelector('#clear').addEventListener('click',()=>{cancel();selected='';address.value='';auto.checked=false;status.textContent='Dashboard cleared.';});
setInterval(()=>{if(auto.checked&&selected&&!document.hidden&&!controller)lookup(selected);},60000);
document.querySelector('#calculator-inputs').disabled=false;
