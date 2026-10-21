import test from 'node:test';
import assert from 'node:assert/strict';
import { summariseDonations } from '../../website/homepage-funding.mjs';

const now = 1800000000;
function fixture() {
  return {
    schema: 'monzero-donations-v1', pricedAt: now - 10,
    pricesUsd: { btc: 50000, ltc: 80, bch: 300, doge: .1, eth: 2500, 'usdt-sol': 1 },
    coins: [['btc',8,'3000000'],['ltc',8,'100000000'],['bch',8,'0'],['doge',8,'0'],['eth',18,'0'],['usdt-sol',6,'1000000']].map(([id,decimals,received]) => ({id,decimals,received,fetchedAt:now - 20,current:true}))
  };
}
test('complete public-chain receipts produce an explicitly approximate total and oldest timestamp', () => {
  assert.deepEqual(summariseDonations(fixture(),now), {received:1581,stale:false,observedAt:now-20});
});
test('missing, duplicate, foreign and malformed currency records cannot become totals', () => {
  for (const change of [d => d.coins.pop(), d => {d.coins[1]=d.coins[0]}, d => {d.coins[0].id='xmz'}, d => {d.coins[0].received=null}, d => {d.coins[0].received=''}, d => {d.coins[0].received='-1'}, d => {d.coins[0].received='1e10'}, d => {d.coins[0].decimals=0}, d => {d.coins[0]=null}, d => {d.schema='other'}]) {
    const data=fixture();change(data);assert.throws(()=>summariseDonations(data,now));
  }
});
test('missing or invalid prices cannot become zero-valued donations', () => {
  for (const price of [undefined,0,-1,Infinity,NaN,'50000']) {
    const data=fixture();data.pricesUsd.btc=price;assert.throws(()=>summariseDonations(data,now));
  }
});
test('stale/undated observations stay labelled, including stale cached currencies', () => {
  for (const change of [d=>{d.pricedAt=now-1300}, d=>{d.coins[2].fetchedAt=now-1300}, d=>{d.coins[0].current=false}, d=>{delete d.pricedAt}, d=>{delete d.coins[1].fetchedAt}]) {
    const data=fixture();change(data);assert.equal(summariseDonations(data,now).stale,true);
  }
});
test('future timestamps fail closed and a complete, genuine zero is valid', () => {
  const future=fixture();future.pricedAt=now+3600;assert.throws(()=>summariseDonations(future,now));
  const zero=fixture();zero.coins.forEach(c=>{c.received='0'});assert.equal(summariseDonations(zero,now).received,0);
});
