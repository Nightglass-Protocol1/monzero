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
