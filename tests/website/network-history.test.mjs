import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateHistory, historyFreshness, ranges} from '../../website/network/history.mjs';
const sample = () => ({schema:'monzero-network-history-v1',network:'mainnet',generated_at:100000,range:'24h',archive_samples:1,archive_first_observed_at:99900,archive_last_observed_at:99900,sources:['preview'],bucket_seconds:120,points:[{first_observed_at:99900,last_observed_at:99900,samples:1,mean_difficulty:1200,mean_estimated_hashrate_hps:10,minimum_difficulty:'1200',maximum_difficulty:'1200',minimum_height:20,maximum_height:20,synchronized_samples:1,all_samples_synchronized:true,minimum_tip_age_seconds:-10,maximum_tip_age_seconds:-10}]});
test('valid observations retain exact values and future block timestamps', () => {
  const d=sample(); assert.equal(validateHistory(d,'24h'), d);
  assert.equal(historyFreshness(d,100000),'recent');
  assert.equal(historyFreshness(d,100301),'stale');
  assert.equal(historyFreshness(d,99999),'clock-mismatch');
});
test('empty archives in every range', () => {
  for (const [range, duration] of Object.entries(ranges)) {
    const d={...sample(),range,archive_samples:0,archive_first_observed_at:null,archive_last_observed_at:null,sources:[],points:[],bucket_seconds:Math.max(60,Math.ceil(Math.min(100000,duration ?? 1)/720))};
    validateHistory(d,range); assert.equal(historyFreshness(d,100000),'empty');
  }
});
test('reject malformed metadata and unsupported sources', () => {
  for (const patch of [{schema:'old'},{network:'testnet'},{range:'7d'},{generated_at:'100000'},{sources:['live','preview']},{sources:['other']},{bucket_seconds:60},{archive_samples:0},{archive_last_observed_at:100001},{points:Array(722).fill(sample().points[0])}]) {
    assert.throws(()=>validateHistory({...sample(),...patch},'24h'));
  }
});
test('reject contradictory bucket values', () => {
  for (const patch of [{samples:2},{mean_difficulty:Infinity},{mean_difficulty:1199},{mean_estimated_hashrate_hps:20},{minimum_difficulty:'01'},{maximum_difficulty:'9007199254740992'},{minimum_height:0},{maximum_height:19},{synchronized_samples:0},{all_samples_synchronized:'true'},{minimum_tip_age_seconds:1},{first_observed_at:100001},{last_observed_at:100001}]) {
    const d=sample(); Object.assign(d.points[0],patch); assert.throws(()=>validateHistory(d,'24h'));
  }
});
test('gaps and decreasing heights are allowed but duplicates are rejected', () => {
  const d=sample(); d.archive_samples=2; d.archive_first_observed_at=99000;
  d.points.unshift({...d.points[0],first_observed_at:99000,last_observed_at:99000,minimum_height:30,maximum_height:30});
  validateHistory(d,'24h'); d.points[0]={...d.points[1]}; assert.throws(()=>validateHistory(d,'24h'));
});
test('full archive count must agree with exported buckets', () => {
 const d=sample(); d.range='all'; d.bucket_seconds=60;
 validateHistory(d,'all'); d.archive_samples=2; assert.throws(()=>validateHistory(d,'all'));
});
test('an archive can have no observations in the selected recent range', () => {
 const d=sample(); d.archive_first_observed_at=100; d.archive_last_observed_at=100; d.points=[];
 validateHistory(d,'24h'); assert.equal(historyFreshness(d,100000),'stale');
});
test('archive bounds cannot manufacture freshness or omit in-range samples',()=>{
 for(const patch of [{archive_last_observed_at:100000},{points:[]},{archive_first_observed_at:99800},{archive_samples:2}])assert.throws(()=>validateHistory({...sample(),...patch},'24h'));
});
test('timestamps outside renderable calendar bounds are rejected',()=>{
 const d=sample();d.generated_at=9e12;assert.throws(()=>validateHistory(d,'24h'));
});
