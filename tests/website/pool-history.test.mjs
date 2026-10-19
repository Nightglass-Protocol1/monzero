import test from 'node:test';import assert from 'node:assert/strict';
import {appendObservation,plotSegments} from '../../website/mining/dashboard/history.mjs';
const data={observed_at:1000,hashrate_hps:100,pending_atomic:'9007199254740993'};
test('bounded observations retain exact amounts and reject repeated or reversed time',()=>{
 let samples=appendObservation([],data);assert.equal(samples[0].pending,data.pending_atomic);
 assert.equal(appendObservation(samples,data),samples);
 assert.equal(appendObservation(samples,{...data,observed_at:999}),samples);
 for(let i=1;i<150;i++)samples=appendObservation(samples,{...data,observed_at:1000+i});
 assert.equal(samples.length,120);assert.equal(samples[0].at,1030);
});
test('failed lookups and long gaps are not joined',()=>{
 let samples=appendObservation([],data);
 samples=appendObservation(samples,{...data,observed_at:1060},true);
 samples=appendObservation(samples,{...data,observed_at:1200});
 assert.equal(plotSegments(samples,'hash').segments.length,3);
});
test('unavailable differs from zero and pending rewards may decrease',()=>{
 let samples=appendObservation([],{...data,hashrate_hps:null,pending_atomic:null});
 samples=appendObservation(samples,{...data,observed_at:1060,hashrate_hps:0,pending_atomic:'0'});
 const plot=plotSegments(samples,'hash');assert.equal(plot.segments.length,1);assert.equal(plot.segments[0][0][1],180);
 assert.equal(samples[1].pending,'0');
});
test('pending chart scales sub-XMZ amounts and uses real time spacing',()=>{
 let samples=appendObservation([],{...data,pending_atomic:'1000000000'});
 samples=appendObservation(samples,{...data,observed_at:1060,pending_atomic:'2000000000'});
 const {segments,max}=plotSegments(samples,'pending');assert.equal(max,.02);
 assert.deepEqual(segments[0],[[20,100],[580,20]]);
 assert.equal(plotSegments([{at:1,pending:null,gap:false}],'pending').segments.length,0);
 assert.deepEqual(plotSegments([{at:1,pending:'0',gap:false}],'pending').segments[0],[[300,180]]);
});
