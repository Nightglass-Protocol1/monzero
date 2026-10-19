import {test} from 'node:test';import assert from 'node:assert/strict';
import {validateBounties,formatReward} from '../../website/community/bounties/catalog.mjs';
const item=()=>({id:'fixture-task',title:'Fixture only',description:'Synthetic test task.',category:'Documentation',difficulty:'beginner',acceptance_criteria:['A reviewer can reproduce the instructions.'],submission_instructions:'Discuss before submitting.',discussion_url:'https://example.org/task',status:'open',review_status:'awaiting-submission',updated_at:'2026-10-19',maintainer:'Fixture maintainer',reviewed_by:'Fixture reviewer',reward_currency:'XMZ',reward_atomic:'0',funding_status:'none',funding_evidence_url:null,funding_checked_at:null,completion_evidence_url:null,completion_checked_at:null,payment_evidence_url:null,payment_checked_at:null});
const catalog=(records=[])=>({schema:'monzero-bounties-v1',updated_at:'2026-10-19',records});
test('empty catalog and reviewed unpaid tasks are valid',()=>{validateBounties(catalog());validateBounties(catalog([item()]));});
test('funded claims require positive reward and dated evidence',()=>{
 const b={...item(),funding_status:'funded',reward_atomic:'100000000000'};
 assert.throws(()=>validateBounties(catalog([b])));
 b.funding_evidence_url='https://example.org/funding';b.funding_checked_at='2026-10-19';validateBounties(catalog([b]));
 for(const patch of [{reward_atomic:'0'},{funding_checked_at:'2026-10-20'},{funding_evidence_url:'javascript:alert(1)'},{funding_evidence_url:'https://user:secret@example.org/'}])assert.throws(()=>validateBounties(catalog([{...b,...patch}])));
});
test('completed and paid statuses need separate evidence',()=>{
 const b={...item(),status:'completed',review_status:'accepted',completion_evidence_url:'https://example.org/review',completion_checked_at:'2026-10-19',funding_status:'paid',reward_atomic:'1',funding_evidence_url:'https://example.org/fund',funding_checked_at:'2026-10-18',payment_evidence_url:'https://example.org/payment',payment_checked_at:'2026-10-19'};
 validateBounties(catalog([b]));for(const field of ['completion_evidence_url','payment_evidence_url','funding_evidence_url'])assert.throws(()=>validateBounties(catalog([{...b,[field]:null}])));
});
test('invalid metadata, ambiguous amounts, controls and duplicate IDs fail',()=>{
 for(const patch of [{reward_atomic:1},{reward_atomic:'01'},{reward_atomic:'18446744073709551616'},{title:'bad\u200btext'},{updated_at:'2026-02-30'},{review_status:'accepted'},{acceptance_criteria:[]},{category:'Unknown'},{reviewed_by:''}])assert.throws(()=>validateBounties(catalog([{...item(),...patch}])));
 assert.throws(()=>validateBounties(catalog([item(),item()])));
});
test('XMZ rewards retain atomic precision',()=>{
 assert.equal(formatReward('1'),'0.00000000001 XMZ');assert.equal(formatReward('100000000000'),'1 XMZ');assert.equal(formatReward('18446744073709551615'),'184467440.73709551615 XMZ');
});
test('future dates, unknown fields and misleading cancelled funding fail',()=>{
 assert.throws(()=>validateBounties({...catalog(),updated_at:'2099-01-01'},'2026-10-19'),/Catalog date is ahead/);
 assert.throws(()=>validateBounties({...catalog(),extra:true}),/Invalid bounty catalog/);
 for(const patch of [{payout_address:'private'},{description:'bad\ud800text'},{status:'cancelled',review_status:'closed',funding_status:'funded',reward_atomic:'1',funding_evidence_url:'https://example.org/fund',funding_checked_at:'2026-10-19'}])assert.throws(()=>validateBounties(catalog([{...item(),...patch}])),/Invalid bounty catalog/);
 validateBounties(catalog([{...item(),description:'First paragraph.\nSecond paragraph.'}]));
});
test('production catalog validates and contains no test fixtures',async()=>{
 const {readFile}=await import('node:fs/promises');const d=JSON.parse(await readFile(new URL('../../website/community/bounties/catalog.json',import.meta.url),'utf8'));validateBounties(d);
 assert.ok(d.records.every(b=>!b.id.startsWith('fixture-')&&!JSON.stringify(b).includes('example.org')));
});
test('status/evidence combinations and schema bounds fail closed',()=>{
 for(const patch of [
  {status:'in-review',review_status:'under-review'},
  {status:'cancelled',review_status:'closed'}
 ])validateBounties(catalog([{...item(),...patch}]));
 for(const patch of [
  {funding_status:'paid',reward_atomic:'1'},
  {completion_evidence_url:'https://example.test/review',completion_checked_at:'2026-10-19'},
  {payment_evidence_url:'https://example.test/pay',payment_checked_at:'2026-10-19'},
  {funding_status:'proposed',reward_atomic:'1',funding_evidence_url:'https://example.test/fund',funding_checked_at:'2026-10-19'},
  {reward_atomic:'1'},{reward_currency:'BTC'},{updated_at:'2026-10-20'},
  {discussion_url:'javascript:alert(1)'},{discussion_url:'https://user:password@example.test/'},
  {title:' leading space'},{id:'not an id'},{difficulty:'easy'}
 ])assert.throws(()=>validateBounties(catalog([{...item(),...patch}]),'2026-10-19'),/Invalid bounty catalog/);
 assert.throws(()=>validateBounties({...catalog(),schema:'old'}),/Invalid bounty catalog/);
 assert.throws(()=>validateBounties(catalog(Array.from({length:201},(_,i)=>({...item(),id:`fixture-${i}`})))),/Invalid bounty catalog/);
});
