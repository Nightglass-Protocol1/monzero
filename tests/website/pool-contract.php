<?php
declare(strict_types=1);
require __DIR__.'/../../website/mining/dashboard/contract.php';
function check(bool $condition,string $message): void {if(!$condition)throw new RuntimeException($message);}
$address='F'.str_repeat('1',94);
$stats=['config'=>['coin'=>'monzero','coinUnits'=>100000000000],'pool'=>['hashrate'=>2000]];
$miner=['address'=>$address,'hashrate'=>1000,'pending'=>'18446744073709551615','paid'=>0,
    'workers'=>[['name'=>'<script>fixture</script>','difficulty'=>5000]],
    'payments'=>[['txid'=>str_repeat('a',64),'timestamp'=>100,'amount'=>'9007199254740993']]];
$v=poolMinerView($miner,$stats,$address,200);
check($v['pending_atomic']==='18446744073709551615','Atomic precision');
check($v['payments'][0]['amount_atomic']==='9007199254740993','Payment precision');
check($v['payments'][0]['confirmations']===null,'No invented confirmation');
check($v['pool_share_percent']===50.0,'Contribution');
check($v['active_workers']===1,'Workers');
check($v['workers'][0]['name']==='Worker connection 1','Do not expose raw login identifiers');
check(!isset($v['address']),'Do not echo address');
check($v['accepted_shares']===null && $v['hashrate_history']===null,'Unavailable fields');
$missing=poolMinerView(['address'=>$address],$stats,$address,200);
check($missing['workers']===null && $missing['pending_atomic']===null && $missing['hashrate_hps']===null,'Missing is not zero');
foreach([-1,1.2,'01','18446744073709551616',true,1e20] as $bad)check(poolAtomic($bad)===null,'Reject invalid atoms');
check(poolAtomic(0)==='0','Real zero');
check(poolLookupShape($address),'Address-shaped input');
foreach(['seed words here',str_repeat('0',95),$address.'?url=evil',null] as $bad)check(!poolLookupShape($bad),'Input boundary');
foreach([array_merge($miner,['address'=>'different']),array_merge($miner,['payments'=>[['txid'=>'bad']]])] as $bad){
 $rejected=false;try{poolMinerView($bad,$stats,$address,200);}catch(UnexpectedValueException){$rejected=true;}
 check($rejected,'Reject unmatched or malformed response');
}
check(poolMinerView(array_merge($miner,['hashrate'=>3000]),$stats,$address,200)['pool_share_percent']===null,'Do not clamp inconsistent percentage');
echo "Pool contract checks passed\n";
$key=str_repeat('a',64);
$labelled=poolMinerView($miner,$stats,$address,200,$key);
$id=$labelled['workers'][0]['label_id'];
check(preg_match('/^[0-9a-f]{64}$/',$id)===1,'Opaque label identifier');
check(poolMinerView($miner,$stats,$address,201,$key)['workers'][0]['label_id']===$id,'Stable identifier');
$otherAddress='F'.str_repeat('2',94);$other=$miner;$other['address']=$otherAddress;
check(poolMinerView($other,$stats,$otherAddress,200,$key)['workers'][0]['label_id']!==$id,'Address scoped identifier');
check(poolMinerView($miner,$stats,$address,200,str_repeat('b',64))['workers'][0]['label_id']!==$id,'Key rotation separates identifiers');
check(!str_contains(json_encode($labelled),'<script>fixture</script>'),'Raw name remains hidden');
$grouped=$miner;$grouped['workers'][]=$miner['workers'][0];
$groupedView=poolMinerView($grouped,$stats,$address,200,$key);
check($groupedView['workers'][0]['label_id']===$groupedView['workers'][1]['label_id'],'Shared login has shared label');
