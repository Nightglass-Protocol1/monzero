import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateExchanges,link} from '../../website/exchanges/catalog.mjs';

const today='2026-10-19';
const planned=()=>({id:'example',exchange:'Example',status:'planned',note:'Goal only.',updated_at:today,application_date:null,listing_fee:null,funding:null,announcements:[],pair:null,trading_url:null,deposits:null,withdrawals:null,trading:null,last_verified:null,verification_url:null});
const live=()=>({...planned(),id:'venue',status:'live',application_date:'2026-10-01',pair:'XMZ/USDT',trading_url:'https://exchange.example/trade/XMZ_USDT',deposits:'enabled',withdrawals:'enabled',trading:'active',last_verified:today,verification_url:'https://exchange.example/announcement'});
const wrap=records=>({schema:'monzero-exchanges-v1',updated_at:today,records});
const bad=records=>assert.throws(()=>validateExchanges(wrap(records),today));

test('production catalog validates and claims no live venue',()=>{
 const data=validateExchanges(JSON.parse(readFileSync(new URL('../../website/exchanges/catalog.json',import.meta.url))),today);
 assert.ok(data.records.every(r=>!['live','suspended'].includes(r.status)&&r.pair===null&&r.listing_fee===null));
});

test('planned, live and suspended records validate',()=>{
 validateExchanges(wrap([planned(),live(),{...live(),id:'old',status:'suspended',trading:'halted',deposits:'disabled'}]),today);
});

test('venue fields are required for live and forbidden before it',()=>{
 bad([{...planned(),pair:'XMZ/USDT'}]);
 bad([{...live(),verification_url:null}]);
 bad([{...live(),last_verified:'2026-10-20'}]);
 bad([{...live(),trading:'halted'}]);
 bad([{...live(),status:'suspended'}]);
 bad([{...live(),trading_url:'/relative'}]);
 bad([{...live(),pair:'USDT/XMZ'}]);
});

test('applications need dates; planned must not have one',()=>{
 bad([{...planned(),application_date:'2026-10-01'}]);
 bad([{...planned(),status:'application-submitted'}]);
 validateExchanges(wrap([{...planned(),status:'application-submitted',application_date:'2026-10-02'}]),today);
});

test('fees need a source and positive amounts; unknown keys and duplicates fail',()=>{
 bad([{...planned(),listing_fee:{amount:'5000',currency:'USD',evidence_url:null}}]);
 bad([{...planned(),listing_fee:{amount:'0.00',currency:'USD',evidence_url:'https://x.example/'}}]);
 bad([{...planned(),funding:{target:'1e4',currency:'USD',progress_url:'/fund/'}}]);
 bad([{...planned(),price:'1'}]);
 bad([planned(),planned()]);
 bad([{...planned(),note:'line\u2028break'}]);
 assert.throws(()=>validateExchanges({...wrap([]),updated_at:'2026-10-20'},today),/ahead/);
});

test('links allow HTTPS and same-site paths only',()=>{
 for(const ok of ['/fund/','https://example.org/a'])assert.equal(link(ok),true,ok);
 for(const no of ['//evil.example/','http://example.org','javascript:alert(1)','/\\evil','https://u:p@example.org/','fund/'])assert.equal(link(no),false,no);
});
