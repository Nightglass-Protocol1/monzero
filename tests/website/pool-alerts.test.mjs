import test from 'node:test';
import assert from 'node:assert/strict';
import {createAlertMonitor,validateAlertSettings} from '../../website/mining/dashboard/alerts.mjs';
const settings={hashDropPercent:50,minimumWorkers:2};
const observation=(t,hash=100,workers=2)=>({observed_at:t,hashrate_hps:hash,active_workers:workers});
test('settings reject nonfinite, fractional worker counts and out-of-range thresholds',()=>{
 for(const value of [NaN,Infinity,0,101])assert.throws(()=>validateAlertSettings({...settings,hashDropPercent:value}));
 for(const value of [-1,1.5,1001])assert.throws(()=>validateAlertSettings({...settings,minimumWorkers:value}));
});
test('two spaced observations required; repeated timestamps and rapid clicks cannot trigger',()=>{
 const m=createAlertMonitor(settings);assert.deepEqual(m.sample(observation(1),0),[]);
 assert.deepEqual(m.sample(observation(2,20,1),60000),[]);
 assert.deepEqual(m.sample(observation(2,20,1),120000),[]);
 assert.deepEqual(m.sample(observation(3,20,1),61000),[]);
 assert.deepEqual(m.sample(observation(4,20,1),120000).map(e=>e.kind),['hashrate','workers']);
 assert.deepEqual(m.sample(observation(5,20,1),180000),[]);
});
test('recovery rearms but cooldown bounds repeated alerts',()=>{
 const m=createAlertMonitor(settings);m.sample(observation(1),0);m.sample(observation(2,0),60000);
 assert.equal(m.sample(observation(3,0),120000).length,1);
 m.sample(observation(4),180000);m.sample(observation(5,0),240000);
 assert.deepEqual(m.sample(observation(6,0),300000),[]);
 assert.equal(m.sample(observation(7,0),720000).length,0);
 assert.equal(m.sample(observation(8,0),780000).length,1);
});
test('missing metrics never count as zero and outages are separate from offline workers',()=>{
 const m=createAlertMonitor(settings);m.sample(observation(1),0);
 assert.deepEqual(m.sample(observation(2,null,null),60000),[]);
 assert.deepEqual(m.sample(null,120000),[]);
 assert.deepEqual(m.sample(null,180000).map(e=>e.kind),['lookup']);
 assert.deepEqual(m.sample(null,240000),[]);
 assert.deepEqual(m.sample(observation(3,0,0),300000),[]);
 assert.deepEqual(m.sample(observation(4,0,0),360000).map(e=>e.kind),['hashrate','workers']);
});
test('new monitor has no previous baseline, cooldown or identity',()=>{
 const m=createAlertMonitor(settings);m.sample(observation(1,0),0);assert.equal(m.baseline(),null);
 m.sample(observation(2,50),60000);assert.equal(m.baseline(),50);
 assert.equal(createAlertMonitor(settings).baseline(),null);
});

test('unknown metrics and server-time gaps break consecutive observations',()=>{
 const m=createAlertMonitor(settings);m.sample(observation(1),0);m.sample(observation(2,0),30000);
 m.sample(observation(3,null),60000);
 assert.deepEqual(m.sample(observation(4,0),90000),[]);
 assert.deepEqual(m.sample(observation(500,0),120000),[]);
 assert.equal(m.sample(observation(560,0),180000).length,1);
});

test('rapid healthy readings break a pending alert, including lookup failures',()=>{
 const m=createAlertMonitor(settings);m.sample(observation(1),0);m.sample(observation(2,0,0),60000);
 m.sample(observation(3),80000);
 assert.deepEqual(m.sample(observation(4,0,0),120000),[]);
 const n=createAlertMonitor(settings);n.sample(null,0);n.sample(observation(1),20000);
 assert.deepEqual(n.sample(null,60000),[]);
});
test('a full drop threshold triggers only at zero, with two observations',()=>{
 const m=createAlertMonitor({hashDropPercent:100,minimumWorkers:0});m.sample(observation(1),0);
 assert.deepEqual(m.sample(observation(2,1,0),60000),[]);
 assert.deepEqual(m.sample(observation(3,0,0),120000),[]);
 assert.deepEqual(m.sample(observation(4,0,0),180000).map(e=>e.kind),['hashrate']);
});

test('payments are opt-in and the first valid history is only a baseline',()=>{
 const pay=(...ids)=>ids.map(n=>({txid:n.toString(16).padStart(64,'0')}));
 const data=(at,...ids)=>({...observation(at),payments:pay(...ids)});
 const off=createAlertMonitor(settings);off.sample(data(1),0);assert.deepEqual(off.sample(data(2,1),60000),[]);
 const m=createAlertMonitor({...settings,payments:true});m.sample({...observation(1),payments:null},0);
 assert.equal(m.paymentState(),'waiting');assert.deepEqual(m.sample(data(2,1,2),60000),[]);
 assert.equal(m.paymentState(),'active');assert.deepEqual(m.sample(data(3,2,1),120000),[]);
 const events=m.sample(data(4,3,2,1),180000);assert.equal(events.length,1);assert.equal(events[0].kind,'payments');
 assert.match(events[0].message,/confirmations are not verified/);
 assert.deepEqual(m.sample(data(5,1),240000),[]);assert.deepEqual(m.sample(data(6,3,1),300000),[]);
});
test('new payments are deduplicated and grouped during cooldown',()=>{
 const m=createAlertMonitor({...settings,payments:true});
 const data=(at,...ids)=>({...observation(at),payments:ids.map(n=>({txid:n.toString(16).padStart(64,'0')}))});
 m.sample(data(1),0);assert.equal(m.sample(data(2,1,1),60000).length,1);
 assert.deepEqual(m.sample(data(3,2,1),120000),[]);
 assert.deepEqual(m.sample(data(4,3,2),180000),[]);
 const events=m.sample(data(5,3,2),660000);assert.equal(events.length,1);assert.match(events[0].message,/2 payment/);
});
test('malformed payment observations do not establish a baseline or emit alerts',()=>{
 const m=createAlertMonitor({...settings,payments:true});
 let at=0;
 for(const payments of [[{txid:'bad'}],[null],Array(51).fill({txid:'a'.repeat(64)})]){
  at++;assert.deepEqual(m.sample({...observation(at),payments},at*60000),[]);
 }
 assert.equal(m.paymentState(),'waiting');
 assert.throws(()=>validateAlertSettings({...settings,payments:'true'}));
});
test('payment identity memory is bounded without forgetting old IDs and re-alerting',()=>{
 const m=createAlertMonitor({...settings,payments:true});
 for(let batch=0;batch<21;batch++)m.sample({...observation(batch+1),payments:Array.from({length:50},(_,i)=>({txid:(batch*50+i).toString(16).padStart(64,'0')}))},batch*60000);
 assert.equal(m.paymentState(),'limit');
 assert.deepEqual(m.sample({...observation(22),payments:[{txid:'f'.repeat(64)}]},1260000),[]);
 assert.equal(createAlertMonitor({...settings,payments:true}).paymentState(),'waiting');
});

test('backfilled history after an empty baseline is newly observed, not confirmed',()=>{
 const m=createAlertMonitor({...settings,payments:true});m.sample({...observation(100),payments:[]},0);
 const event=m.sample({...observation(101),payments:[{txid:'a'.repeat(64),timestamp:1}]},60000)[0];
 assert.match(event.message,/newly reported/);assert.match(event.message,/confirmations are not verified/);
});
