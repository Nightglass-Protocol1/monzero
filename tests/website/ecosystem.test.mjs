import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateEcosystem} from '../../website/ecosystem/catalog.mjs';

const today='2026-10-19';
const entry=(o={})=>({id:'tool',name:'Tool',category:'Mining pools',operator:'third-party',description:'A pool.',url:'https://pool.example/',verified_at:today,...o});
const wrap=records=>({schema:'monzero-ecosystem-v1',updated_at:today,records});
const bad=records=>assert.throws(()=>validateEcosystem(wrap(records),today));

test('production directory validates; third parties are external and exchanges absent',()=>{
 const data=validateEcosystem(JSON.parse(readFileSync(new URL('../../website/ecosystem/catalog.json',import.meta.url),'utf8')),today);
 assert.ok(data.records.length>0);
 assert.ok(data.records.filter(r=>r.operator==='third-party').every(r=>r.url.startsWith('https://')));
 assert.ok(data.records.every(r=>r.category!=='Exchanges'));
});

test('entries need known category/operator, safe links and review dates',()=>{
 validateEcosystem(wrap([entry(),entry({id:'site',operator:'project',url:'/explorer/'})]),today);
 bad([entry({operator:'third-party',url:'/explorer/'})]);
 bad([entry({category:'Casinos'})]);
 bad([entry({operator:'partner'})]);
 bad([entry({url:'http://pool.example/'})]);
 bad([entry({url:'javascript:alert(1)'})]);
 bad([entry({category:'Exchanges'})]);
 bad([entry({verified_at:'2026-10-20'})]);
 bad([entry(),entry()]);
 bad([entry({extra:true})]);
 bad([entry({name:'tab\there'})]);
});
