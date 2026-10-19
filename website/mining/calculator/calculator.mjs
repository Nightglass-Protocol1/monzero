import { estimateMining } from './calculations.mjs';
const form=document.querySelector('#calculator'), status=document.querySelector('#network-status');
const results=document.querySelector('#results'), error=document.querySelector('#error');
let observation=null;
const format=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:8}).format(value);
function calculate(event) {
  event?.preventDefault();error.textContent='';results.replaceChildren();
  if (!form.reportValidity()) return;
  if (!observation || Date.now()-observation.observedAt>300000) {
    document.querySelector('#result-status').textContent='A current mainnet observation is required. Refresh network data.';return;
  }
  try {
    const values=Object.fromEntries(new FormData(form));
    for (const field of ['hashrate','watts','electricityPrice','poolFeePercent']) values[field]=Number(values[field]);
    values.hardwareCost=values.hardwareCost.trim()===''?null:Number(values.hardwareCost);
    const result=estimateMining({...values,...observation});
    const rows=[['Expected XMZ / hour',result.xmzPerHour],['Expected XMZ / day',result.xmzPerDay],
      ['Expected XMZ / week',result.xmzPerWeek],['Expected XMZ / 30 days',result.xmzPerMonth],
      ['Electricity / day (kWh)',result.kwhPerDay],[`Electricity cost / day (${values.electricityCurrency})`,result.electricityPerDay]];
    for(const [label,value] of rows) {const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=format(value);results.append(dt,dd);}
    document.querySelector('#result-status').textContent='Approximate averages at the observed difficulty and reward.';
  } catch {error.textContent='Check the input values. This combination is outside the supported calculation range.';}
}
form.addEventListener('submit',calculate);
form.addEventListener('input',()=>{results.replaceChildren();document.querySelector('#result-status').textContent='Inputs changed. Calculate again to update the estimate.';});
async function refresh() {
  const button=document.querySelector('#refresh');button.disabled=true;observation=null;results.replaceChildren();
  document.querySelector('#network-details').textContent='';status.textContent='Loading public-node data…';
  document.querySelector('#result-status').textContent='Waiting for network data.';
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetch('../../explorer/api.php',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'blocks',limit:1}),signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error('Unavailable');
    const data=await response.json(),info=data.info,header=data.headers?.[0];
    if(info?.status!=='OK'||info.nettype!=='mainnet'||info.synchronized!==true||!header
      ||header.height!==info.height-1||!Number.isFinite(header.difficulty)||header.difficulty<=0
      ||!Number.isSafeInteger(header.reward)||header.reward<0||!Number.isFinite(info.target)||info.target<=0
      ||!Number.isInteger(header.timestamp)||Date.now()/1000-header.timestamp>3600||header.timestamp>Date.now()/1000+120)
      throw new Error('Unusable observation');
    observation={difficulty:header.difficulty,rewardXmz:header.reward/1e11,observedAt:Date.now()};
    status.textContent=`Mainnet block ${header.height.toLocaleString()} · retrieved ${new Date(observation.observedAt).toLocaleString()}`;
    document.querySelector('#network-details').textContent=`Estimated network hashrate: ${format(header.difficulty/info.target)} H/s · target: ${info.target} seconds · observed block reward including fees: ${format(observation.rewardXmz)} XMZ · block time: ${new Date(header.timestamp*1000).toLocaleString()}`;
    calculate();
  } catch {status.textContent='Current mainnet data is unavailable or too old. No reward estimate is shown. Try refreshing later.';document.querySelector('#result-status').textContent='Network data unavailable.';}
  finally {clearTimeout(timer);button.disabled=false;}
}
document.querySelector('#refresh').addEventListener('click',refresh);
// Expire visible estimates too, rather than retaining an apparently current result.
setInterval(()=>{if(observation && Date.now()-observation.observedAt>300000){observation=null;results.replaceChildren();status.textContent='Observation expired. Refresh network data.';document.querySelector('#result-status').textContent='Estimate expired.';}},10000);
refresh();
