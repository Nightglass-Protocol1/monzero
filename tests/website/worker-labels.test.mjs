import test from 'node:test';import assert from 'node:assert/strict';
import {parseLabels,setLabel} from '../../website/mining/dashboard/labels.mjs';
const id='a'.repeat(64);
test('label edits retain only opaque identifiers and visible text',()=>{
 const labels=setLabel({},id,' Desk CPU ');assert.deepEqual(labels,{[id]:'Desk CPU'});
 assert.deepEqual(parseLabels(JSON.stringify(labels)),labels);assert.deepEqual(setLabel(labels,id,''),{});
 assert.equal(labels[id],'Desk CPU');
});
test('invalid stored records and invisible labels are rejected',()=>{
 for(const raw of ['[]','null','{"address":"secret"}','x'.repeat(20001),JSON.stringify({[id]:'hidden\u202e'})])assert.throws(()=>parseLabels(raw));
 for(const label of ['x'.repeat(61),'\u200b','text\nlabel'])assert.throws(()=>setLabel({},id,label));
 assert.throws(()=>setLabel({},'not-an-id','label'));assert.deepEqual(parseLabels(null),{});
});
test('storage capacity is bounded',()=>{
 let labels={};for(let i=0;i<100;i++)labels=setLabel(labels,i.toString(16).padStart(64,'0'),'worker');
 assert.throws(()=>setLabel(labels,id,'one more'));assert.equal(Object.keys(parseLabels(JSON.stringify(labels))).length,100);
});
