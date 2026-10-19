import test from 'node:test';
import assert from 'node:assert/strict';
import { estimateMining } from '../../website/mining/calculator/calculations.mjs';
const base = { hashrate: 1000, unit:'H/s', difficulty:3600000, rewardXmz:2,
  watts:100, electricityPrice:0.25, poolFeePercent:1 };
test('expected work and fee calculation, 30-day month and energy', () => {
  const r=estimateMining(base); assert.equal(r.xmzPerHour,1.98);
  assert.equal(r.xmzPerDay,47.519999999999996); assert.equal(r.xmzPerMonth,1.98*720);
  assert.equal(r.kwhPerDay,2.4); assert.equal(r.electricityPerDay,0.6);
});
test('hashrate unit conversions agree', () => {
  for(const [hashrate,unit] of [[1,'KH/s'],[0.001,'MH/s']])
    assert.deepEqual(estimateMining({...base,hashrate,unit}),estimateMining(base));
});
test('zero hashrate still incurs energy cost', () => {
  const r=estimateMining({...base,hashrate:0});assert.equal(r.xmzPerDay,0);assert.equal(r.electricityPerDay,0.6);
});
test('no price means no revenue or break-even claim', () => {
  const r=estimateMining({...base,hardwareCost:100});
  for(const k of ['revenuePerDay','netPerDay','breakEvenDays'])assert.equal(r[k],null);
});
test('invalid and nonfinite inputs rejected', () => {
  for(const [key,value] of [['hashrate',-1],['watts',NaN],['difficulty',0],['difficulty',Infinity],
    ['rewardXmz',-1],['electricityPrice',-1],['poolFeePercent',101],['unit','GH/s'],['hashrate','1000'],['hardwareCost',-1]])
    assert.throws(()=>estimateMining({...base,[key]:value}),RangeError);
});
test('overflow rejected',()=>assert.throws(()=>estimateMining({...base,difficulty:Number.MIN_VALUE}),RangeError));
test('100 percent pool fee produces no expected reward',()=>assert.equal(estimateMining({...base,poolFeePercent:100}).xmzPerDay,0));
const market={verified:true,source:'fixture only',currency:'USD',price:1,observedAt:1};
test('market must be sourced and same currency',()=>{
  assert.throws(()=>estimateMining({...base,market:{...market,verified:false}}),RangeError);
  assert.throws(()=>estimateMining({...base,market,electricityCurrency:'GBP'}),RangeError);
});
test('positive net return enables hardware estimate',()=>{
  const r=estimateMining({...base,market,electricityCurrency:'USD',hardwareCost:100});
  assert.equal(r.breakEvenDays,100/r.netPerDay);
});
test('negative return never yields break-even',()=>{
  const r=estimateMining({...base,market:{...market,price:0.0001},electricityCurrency:'USD',hardwareCost:100});
  assert.ok(r.netPerDay<0);assert.equal(r.breakEvenDays,null);
});
