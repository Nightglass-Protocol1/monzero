import {test} from 'node:test';
import assert from 'node:assert/strict';
import {summarizeBlocks} from '../../website/network/blocks.mjs';
function fixture(gaps){let time=1000;const blocks=[{height:1,timestamp:time,difficulty:1200,transactions:0}];for(const gap of gaps){time+=gap;blocks.push({height:blocks.length+1,timestamp:time,difficulty:1200,transactions:0});}return {schema:'monzero-chain-charts-v2',network:'mainnet',target_seconds:120,height:blocks.length+1,generated_at:10000,synchronized:true,blocks};}
test('distribution includes boundary values and interval-based production rate',()=>{
 const d=summarizeBlocks(fixture([0,59,60,119,120,239,240,599,600]));
 assert.deepEqual(d.bins.map(b=>b.count),[2,2,2,2,1]);assert.equal(d.validIntervals,9);assert.equal(d.blocksPerHour,9*3600/2036);
});
test('negative timestamps are counted separately from the endpoint-based rate',()=>{
 const d=summarizeBlocks(fixture([120,-10,120]));assert.equal(d.backwards,1);assert.equal(d.validIntervals,2);assert.equal(d.blocksPerHour,3*3600/230);
});
test('single block and zero span do not imply a production rate',()=>{
 assert.equal(summarizeBlocks(fixture([])).blocksPerHour,null);assert.equal(summarizeBlocks(fixture([0])).blocksPerHour,null);
});
test('malformed metadata, incomplete windows and unsafe values are rejected',()=>{
 for(const patch of [{network:'testnet'},{schema:'old'},{height:10},{target_seconds:0},{generated_at:9e12},{synchronized:1}])assert.throws(()=>summarizeBlocks({...fixture([120]),...patch}));
 for(const patch of [{height:9},{timestamp:-1},{difficulty:NaN},{transactions:1.5}]){const d=fixture([120]);Object.assign(d.blocks[1],patch);assert.throws(()=>summarizeBlocks(d));}
});
test('full recent window starts above genesis and rejects oversized windows',()=>{
 const d=fixture(Array(719).fill(120));d.height=2000;d.blocks.forEach((b,i)=>b.height=1280+i);
 const result=summarizeBlocks(d);assert.equal(result.firstHeight,1280);assert.equal(result.lastHeight,1999);assert.equal(result.validIntervals,719);assert.equal(result.blocksPerHour,30);
 d.blocks.unshift({...d.blocks[0],height:1279});assert.throws(()=>summarizeBlocks(d));
});
test('JSON-representable malformed types and calendar boundaries',()=>{
 for(const patch of [{blocks:null},{blocks:[null]},{target_seconds:'120'},{generated_at:253402300800}])assert.throws(()=>summarizeBlocks({...fixture([]),...patch}));
 const d=fixture([]);d.generated_at=253402300799;assert.equal(summarizeBlocks(d).generatedAt,253402300799);
 for(const patch of [{timestamp:253402300800},{difficulty:'1200'},{difficulty:1e300},{difficulty:-0}]){const d=fixture([]);Object.assign(d.blocks[0],patch);assert.throws(()=>summarizeBlocks(d));}
});
