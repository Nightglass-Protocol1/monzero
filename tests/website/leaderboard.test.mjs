import test from 'node:test';
import assert from 'node:assert/strict';
import {validateReport,rank,formatRate} from '../../website/mining/leaderboard/leaderboard.mjs';

const m=(name,hashrate,blocks_found,last_seen=100)=>({name,hashrate,blocks_found,active:true,last_seen});
const report=miners=>({status:'OK',generated_at:200,active_miners:miners.length,total_hashrate:0,total_blocks:0,miners});

test('reports with pseudonymous miners validate',()=>{
 validateReport(report([m('Miner 0A1B2C3D',500,2)]),200);
 validateReport(report([]),200);
});

test('malformed or identifying reports are refused',()=>{
 for(const bad of [m('Fabc…address',1,0),m('Miner 0a1b2c3d',1,0),m('Miner 0A1B2C3D',-1,0),m('Miner 0A1B2C3D',NaN,0),m('Miner 0A1B2C3D',1,1.5),m('Miner 0A1B2C3D',1,0,201)])
  assert.throws(()=>validateReport(report([bad]),200),JSON.stringify(bad));
 assert.throws(()=>validateReport({...report([]),status:'NOT_CONFIGURED'},200));
 assert.throws(()=>validateReport({...report([]),generated_at:900},200));
});

test('rankings sort descending with stable ties and skip zero-block miners',()=>{
 const list=[m('Miner 00000002',10,0),m('Miner 00000001',10,3),m('Miner 00000003',99,1)];
 assert.deepEqual(rank(list,'hashrate').map(x=>x.name),['Miner 00000003','Miner 00000001','Miner 00000002']);
 assert.deepEqual(rank(list,'blocks_found').map(x=>x.name),['Miner 00000001','Miner 00000003']);
 assert.equal(rank(Array.from({length:80},(_,i)=>m(`Miner ${String(i).padStart(8,'0')}`,i,0)),'hashrate').length,50);
});

test('hashrate units',()=>{
 assert.equal(formatRate(0),'0.00 H/s');assert.equal(formatRate(950),'950 H/s');assert.equal(formatRate(1500),'1.50 KH/s');assert.equal(formatRate(2e6),'2.00 MH/s');
});
