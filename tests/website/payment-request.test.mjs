import test from 'node:test';
import assert from 'node:assert/strict';
import {parseAddress,base58Decode,base58Encode,keccak256,isValidPoint} from '../../website/payments/request/address.mjs';
import {parseAmount,formatAtomic,displayAmount,encodeText,validateText,buildUri,MAX_ATOMIC} from '../../website/payments/request/uri.mjs';
import {encodeQr} from '../../website/payments/request/qr.mjs';

// Published donation/founder addresses and vectors from a throwaway offline monzero-wallet-cli
// (release-v1 host build): primary, `address new`, and `integrated_address 0123456789abcdef`.
const published=['FQLhxULkbyx4886T7196doS9GPMzexD9gXpsZJDwVjeRVdFCSoHnv7KPbBeGpzJBzHRCAs9UxqeoyFQMYbqSWYTfJJCEnHf','FS1LtxYqTVPRDV5aAhLJzQCjDz2ViLRduE3ijDZu3osWKBjMGkV1XPk4pfDUMqt1Aiezvephdqm6YD19GKFD9ZcXVUEgtLB'];
const primary='FWPbFrwvRqpWTMDJAAeT3wAGsCUvERHyEAZJySDBDTKJJxr4q9gNStxSZghEAmtgvd49oySaDP9WGV1KVDeDXFBfM748KwK';
const sub='Fj4gs1bC1Wf82NWMYCm7gaifFntWiVDz83ZYNEVtwyUmSWxPAAM8Bjy4XwbK2k91Jq5VG3ndJLHrDhs2SoYPryYEBwWxL9J';
const integrated='Fg6GGfmR37LWTMDJAAeT3wAGsCUvERHyEAZJySDBDTKJJxr4q9gNStxSZghEAmtgvd49oySaDP9WGV1KVDeDXFBfWmsEXGUWcB6U3NP9sa';

test('keccak256 is original Keccak, not SHA3',()=>{
 const hex=b=>Buffer.from(b).toString('hex');
 assert.equal(hex(keccak256(new Uint8Array())),'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470');
 assert.equal(hex(keccak256(new TextEncoder().encode('abc'))),'4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45');
 assert.equal(hex(keccak256(new Uint8Array(200).fill(0xa3))),'3a57666b048777f2c953dc4456f45a2588e1cb6f2da760122d530ac2ce607d4a');
});

test('wallet and published addresses parse with the right type',()=>{
 for(const a of [...published,primary])assert.deepEqual(parseAddress(a),{network:'mainnet',kind:'standard',address:a,paymentId:null});
 assert.equal(parseAddress(sub).kind,'subaddress');
 assert.deepEqual(parseAddress(` ${integrated}\n`),{network:'mainnet',kind:'integrated',address:integrated,paymentId:'0123456789abcdef'});
});

test('base58 round-trips and rejects bad lengths and characters',()=>{
 const bytes=base58Decode(primary);assert.equal(base58Encode(bytes),primary);
 assert.equal(base58Decode(primary.slice(0,-1)),null);
 assert.equal(base58Decode(primary.replace('F','0')),null);
 assert.equal(base58Decode('zzzzzzzzzzz'),null);
});

function reencode(mutate){
 const bytes=base58Decode(primary),body=bytes.slice(0,-4);mutate(body);
 const out=new Uint8Array(body.length+4);out.set(body);out.set(keccak256(body).subarray(0,4),body.length);return base58Encode(out);
}

test('invalid addresses fail closed with a reason',()=>{
 for(const bad of ['', 'x'.repeat(201), primary.slice(0,-1)+(primary.endsWith('K')?'L':'K'), primary.toLowerCase()])assert.ok(parseAddress(bad).error,bad);
 assert.match(parseAddress('44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A').error,/network prefix/);
 assert.match(parseAddress(reencode(b=>{b[0]=86+128;})).error,/prefix|length/);
 const offCurve=reencode(b=>{b[1]=2;b.fill(0,2,33);});assert.match(parseAddress(offCurve).error,/invalid public key/);
 const tooLong=base58Decode(primary);assert.ok(parseAddress(base58Encode(new Uint8Array([...tooLong.slice(0,-4),0,...tooLong.slice(-4)]))).error);
});

test('point check matches ge_frombytes_vartime edge cases',()=>{
 const enc=(y,sign=0)=>{const b=new Uint8Array(32);let v=y;for(let i=0;i<32;i++){b[i]=Number(v&0xffn);v>>=8n;}b[31]|=sign<<7;return b;};
 const p=(1n<<255n)-19n;
 assert.equal(isValidPoint(enc(1n)),true);
 assert.equal(isValidPoint(enc(1n,1)),false);
 assert.equal(isValidPoint(enc(p+1n)),false);
 assert.equal(isValidPoint(enc(2n)),false);
});

test('amounts follow parse_amount and print_money',()=>{
 assert.equal(parseAmount('').atomic,0n);
 assert.equal(parseAmount(' 1.5 ').atomic,150000000000n);
 assert.equal(parseAmount('.00000000001').atomic,1n);
 assert.equal(parseAmount('2.500000000000000').atomic,250000000000n);
 assert.equal(parseAmount('184467440.73709551615').atomic,MAX_ATOMIC);
 for(const bad of ['184467440.73709551616','1e3','-1','1,5','.','1.000000000001','0x10','1 2'])assert.ok(parseAmount(bad).error,bad);
 assert.equal(formatAtomic(1n),'0.00000000001');
 assert.equal(formatAtomic(150000000000n),'1.50000000000');
 assert.equal(displayAmount(150000000000n),'1.5');
 assert.equal(displayAmount(100000000000n),'1');
});

test('URIs use the wallet format and escape every reserved byte',()=>{
 assert.equal(buildUri({address:primary}),`monzero:${primary}`);
 assert.equal(buildUri({address:primary,atomic:150000000000n,recipientName:'Shop & co',description:'Order #7 = ü?'}),`monzero:${primary}?tx_amount=1.50000000000&recipient_name=Shop%20%26%20co&tx_description=Order%20%237%20%3D%20%C3%BC%3F`);
 assert.equal(encodeText('a/b+c'),'a%2Fb%2Bc');
 assert.ok(validateText('Name','line\nbreak').error);
 assert.ok(validateText('Name','x'.repeat(201)).error);
 assert.equal(validateText('Name','  ok ').text,'ok');
});

test('QR versions grow with the payload and reject oversize input',()=>{
 assert.equal(encodeQr('monzero:'+primary).version,6);
 assert.equal(encodeQr('x'.repeat(2331)).version,40);
 assert.throws(()=>encodeQr('x'.repeat(2332)),RangeError);
});
