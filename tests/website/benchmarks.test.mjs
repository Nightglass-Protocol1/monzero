import test from 'node:test';import assert from 'node:assert/strict';
import {validateCatalog,selectRecords,efficiency} from '../../website/mining/benchmarks/catalog.mjs';
import {readFileSync} from 'node:fs';
const a={id:'fixture-a',manufacturer:'Fixture',model:'Synthetic A',cores:4,threads:8,hashrate_hps:2000,power_watts:100,power_basis:'wall',os:'Fixture OS',miner:'Fixture miner',miner_version:'1',methodology:'Synthetic unit-test fixture only',date:'2026-10-18',status:'community',source_url:'https://example.test/a',verified_by:null,verification_url:null};
const wrap=records=>({schema:'monzero-randomx-benchmarks-v1',updated_at:'2026-10-19',records});
test('production catalog validates and excludes synthetic test identifiers',()=>{const data=validateCatalog(JSON.parse(readFileSync(new URL('../../website/mining/benchmarks/catalog.json',import.meta.url))));assert.ok(data.records.every(r=>!r.id.startsWith('fixture-') && !new URL(r.source_url).hostname.endsWith('.test')));});
test('verification requires separate evidence',()=>{assert.throws(()=>validateCatalog(wrap([{...a,status:'verified'}])));validateCatalog(wrap([{...a,status:'verified',verified_by:'Fixture reviewer',verification_url:'https://example.test/review'}]));});
test('reject malformed values and duplicate identities',()=>{for(const patch of [{id:undefined},{cores:0},{threads:1.5},{hashrate_hps:Infinity},{power_watts:0},{date:'2026-02-30'},{source_url:'javascript:alert(1)'},{verified_by:'false endorsement'}])assert.throws(()=>validateCatalog(wrap([{...a,...patch}])));assert.throws(()=>validateCatalog(wrap([a,a])));});
test('package and unknown power never enter wall efficiency ranking',()=>{assert.equal(efficiency(a),20);assert.equal(efficiency({...a,power_basis:'cpu-package'}),null);assert.equal(efficiency({...a,power_watts:null}),null);});
test('filter and order without changing catalog',()=>{const b={...a,id:'fixture-b',model:'Synthetic B',hashrate_hps:3000,power_basis:'cpu-package'};const records=[b,a];assert.equal(selectRecords(records,{sort:'efficiency'})[0].id,a.id);assert.equal(records[0],b);assert.equal(selectRecords(records,{query:'synthetic b'}).length,1);assert.equal(selectRecords(records,{status:'verified'}).length,0);});

test('strict publication fields and consistent power evidence',()=>{
 for(const patch of [{wallet_address:'must not publish'},{power_basis:'unknown'},{power_watts:null},{threads:2},{model:'misleading\u202eCPU'}])assert.throws(()=>validateCatalog(wrap([{...a,...patch}])));
 assert.throws(()=>validateCatalog({...wrap([a]),private_notes:'must not publish'}));
 assert.throws(()=>validateCatalog(wrap([{...a,status:'verified',verified_by:'Reviewer',verification_url:a.source_url}])));
 validateCatalog(wrap([{...a,power_watts:null,power_basis:'unknown'}]));
});

test('reject ambiguous evidence URLs and invisible descriptive text',()=>{
 for(const source_url of ['https://@example.test','https:example.test','https://example.test/\npath','https://example.test/\u202eimage','https://example.test/\\path','https://example.test/'+ 'a'.repeat(2048)])
  assert.throws(()=>validateCatalog(wrap([{...a,source_url}])));
 for(const model of ['\u200b','AMD\u200b','\ud800','CPU\u2028model'])
  assert.throws(()=>validateCatalog(wrap([{...a,model}])));
 for(const verification_url of [a.source_url+'#',a.source_url+'?',a.source_url+'#evidence','https://EXAMPLE.test:443/a'])
  assert.throws(()=>validateCatalog(wrap([{...a,status:'verified',verified_by:'Reviewer',verification_url}])));
});
test('overflowing calculated efficiency is unavailable rather than ranked first',()=>{
 const extreme={...a,id:'fixture-extreme',hashrate_hps:1e308,power_watts:1e-10};
 assert.equal(efficiency(extreme),null);
 assert.equal(selectRecords([extreme,a],{sort:'efficiency'})[0].id,a.id);
});
