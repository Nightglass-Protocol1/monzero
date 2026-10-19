<?php
require __DIR__.'/../../website/stats/contract.php';
function check(bool $ok): void {if(!$ok)throw new RuntimeException('Contract assertion failed');}
function rejected(array $info,array $range): void {
    try {statsObservation($info,$range,1000);}catch(UnexpectedValueException $e){return;}
    throw new RuntimeException('Invalid observation accepted');
}
$hash=fn(int $n)=>str_pad(dechex($n),64,'0',STR_PAD_LEFT);
$info=['status'=>'OK','nettype'=>'mainnet','height'=>4,'target'=>120,'synchronized'=>true,'top_block_hash'=>$hash(3)];
$range=['status'=>'OK','headers'=>[]];
for($n=1;$n<=3;$n++)$range['headers'][]=['height'=>$n,'hash'=>$hash($n),'prev_hash'=>$hash($n-1),'orphan_status'=>false,'timestamp'=>100+$n,'difficulty'=>10000,'difficulty_top64'=>0,'num_txes'=>0];
$result=statsObservation($info,$range,1000);check(count($result['blocks'])===3);check($result['blocks'][0]['transactions']===0);
foreach(['nettype'=>'testnet','height'=>'4','target'=>0,'synchronized'=>'true','top_block_hash'=>$hash(99)] as $field=>$value){$bad=$info;$bad[$field]=$value;rejected($bad,$range);}
foreach(['height'=>99,'timestamp'=>null,'difficulty'=>-1,'difficulty_top64'=>1,'num_txes'=>'0','orphan_status'=>true,'prev_hash'=>$hash(99),'hash'=>'invalid'] as $field=>$value){$bad=$range;$bad['headers'][1][$field]=$value;rejected($info,$bad);}
foreach([0.5,INF,9007199254740992] as $value){$bad=$range;$bad['headers'][0]['difficulty']=$value;rejected($info,$bad);}
$bad=$range;array_pop($bad['headers']);rejected($info,$bad);
$bad=$range;$bad['headers']=array_reverse($bad['headers']);rejected($info,$bad);
$bad=$range;$bad['status']='BUSY';rejected($info,$bad);
// Timestamp order is not consensus-enforced. Preserve backward times for the UI's unavailable interval.
$bad=$range;$bad['headers'][1]['timestamp']=50;check(statsObservation($info,$bad,1000)['blocks'][1]['timestamp']===50);
$info['synchronized']=false;check(statsObservation($info,$range,1000)['synchronized']===false);
echo "Stats source contract checks passed\n";

$large=$info;$large['height']=1001;$large['top_block_hash']=$hash(1000);$window=['status'=>'OK','headers'=>[]];
for($n=281;$n<=1000;$n++)$window['headers'][]=['height'=>$n,'hash'=>$hash($n),'prev_hash'=>$hash($n-1),'orphan_status'=>false,'timestamp'=>100+$n,'difficulty'=>10000,'difficulty_top64'=>0,'num_txes'=>0];
check(count(statsObservation($large,$window,2000)['blocks'])===720);
$extra=$window;$extra['headers'][]=$extra['headers'][719];rejected($large,$extra);
$bad=$info;$bad['height']=1;rejected($bad,$range);
$bad=$info;$bad['untrusted']=true;rejected($bad,$range);
$bad=$range;$bad['untrusted']=true;rejected($info,$bad);
echo "720-header window and bootstrap-source checks passed\n";
