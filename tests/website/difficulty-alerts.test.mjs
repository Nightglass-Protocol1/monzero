import {test} from 'node:test';import assert from 'node:assert/strict';
import {createDifficultyMonitor} from '../../website/network/difficulty-alerts.mjs';
const observation=(t,d=1000)=>({generatedAt:t,lastTimestamp:t-30,synchronized:true,tipDifficulty:d});
test('threshold validation and first observation baseline',()=>{
 for(const v of [0,101,NaN,'10',null])assert.throws(()=>createDifficultyMonitor(v));
 const m=createDifficultyMonitor(10);assert.equal(m.sample(observation(1000),1000,0),null);assert.equal(m.baseline(),1000);
});
test('two spaced observations alert once with a fixed baseline',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1000),1000,0);
 assert.equal(m.sample(observation(1060,1100),1060,60000),null);
 assert.equal(m.sample(observation(1120,1100),1120,120000).direction,'up');
 assert.equal(m.sample(observation(1180,1200),1180,180000),null);assert.equal(m.baseline(),1000);
});
test('unknown, syncing, stale and future observations never establish a baseline',()=>{
 for(const o of [null,{...observation(1000),synchronized:false},observation(999),observation(1400),{...observation(1300),lastTimestamp:900},{...observation(1300),lastTimestamp:1400}]){
 const m=createDifficultyMonitor(10);assert.equal(m.sample(o,1300,0),null);assert.equal(m.baseline(),null);
 }
});
test('rapid, duplicate and backwards-clock samples cannot confirm an alert',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1000),1000,0);m.sample(observation(1060,900),1060,60000);
 assert.equal(m.sample(observation(1060,900),1060,120000),null);
 assert.equal(m.sample(observation(1061,900),1061,60001),null);
 assert.equal(m.sample(observation(1120,900),1120,1),null);
 assert.equal(m.sample(observation(1120,900),1120,120000).direction,'down');
});
test('outages and long gaps reset confirmation',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1000),1000,0);m.sample(observation(1060,1200),1060,60000);m.sample(null,1120,120000);
 assert.equal(m.sample(observation(1180,1200),1180,180000),null);
 assert.equal(m.sample(observation(1500,1200),1500,500000),null);
 assert.equal(m.sample(observation(1560,1200),1560,560000).direction,'up');
});
test('recovery rearms but cooldown still applies',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1000),1000,0);m.sample(observation(1060,1200),1060,60000);m.sample(observation(1120,1200),1120,120000);
 m.sample(observation(1180),1180,180000);m.sample(observation(1240,1200),1240,240000);assert.equal(m.sample(observation(1300,1200),1300,300000),null);
 for(let t=1360;t<1720;t+=60)assert.equal(m.sample(observation(t,1200),t,(t-1000)*1000),null);
 assert.equal(m.sample(observation(1720,1200),1720,720000).direction,'up');
});
test('a rapid opposite-direction sample breaks consecutive confirmation',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1000),1000,0);m.sample(observation(1060,1200),1060,60000);
 assert.equal(m.sample(observation(1061,800),1061,61000),null);
 assert.equal(m.sample(observation(1120,1200),1120,120000),null);
 assert.equal(m.sample(observation(1180,1200),1180,180000).direction,'up');
});
test('snapshot spacing is required independently of request spacing',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1000),1000,0);m.sample(observation(1060,1200),1060,60000);
 assert.equal(m.sample(observation(1061,1200),1061,120000),null);
 assert.equal(m.sample(observation(1090,1200),1090,150000).direction,'up');
});
test('rejected observations explain the reason',()=>{
 const m=createDifficultyMonitor(10);m.sample(observation(1001),1000,0);assert.match(m.status(),/Clock mismatch/);
 m.sample(null,1000,1);assert.match(m.status(),/Lookup failed/);
 m.sample({...observation(1000),synchronized:false},1000,2);assert.match(m.status(),/syncing/);
});
