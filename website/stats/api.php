<?php
declare(strict_types=1);
const NODE_RPC = 'http://node.monzero.org:6175';
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=60');
header('X-Content-Type-Options: nosniff');
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') { header('Allow: GET'); respond(['error'=>'GET required'],405); }
// Cache only public chain data; serialize refreshes to bound upstream traffic.
$cache = @fopen(sys_get_temp_dir().'/monzero-public-chain-charts-v1.json','c+');
if (!$cache || !flock($cache, LOCK_EX)) respond(['error'=>'Stats temporarily unavailable'],503);
try {
    $saved = json_decode(stream_get_contents($cache), true);
    if (is_array($saved) && ($saved['generated_at'] ?? 0) > time()-60) respond($saved);
    $info = rpc('/get_info', []);
    if (($info['status'] ?? '') !== 'OK' || ($info['nettype'] ?? '') !== 'mainnet') throw new RuntimeException('Mainnet unavailable');
    $end = (int)$info['height']-1;
    if ($end < 1) throw new RuntimeException('Chain history unavailable');
    $range = jsonRpc('get_block_headers_range', ['start_height'=>max(1,$end-719),'end_height'=>$end,'fill_pow_hash'=>false]);
    $headers = $range['headers'] ?? [];
    if (!$headers) throw new RuntimeException('No block headers');
    $blocks=[];
    foreach ($headers as $h) $blocks[]=['height'=>(int)$h['height'],'timestamp'=>(int)$h['timestamp'],'difficulty'=>(float)$h['difficulty'],'transactions'=>(int)$h['num_txes']];
    $data=['generated_at'=>time(),'network'=>'mainnet','target_seconds'=>(int)($info['target'] ?? 120),'height'=>(int)$info['height'],'synchronized'=>(bool)($info['synchronized'] ?? false),'blocks'=>$blocks];
    rewind($cache); ftruncate($cache,0); fwrite($cache,json_encode($data)); fflush($cache);
    respond($data);
} catch (Throwable $e) {
    error_log('Monzero charts: '.$e->getMessage());
    header('Cache-Control: no-store');
    respond(['error'=>'Mainnet data is temporarily unavailable. Please retry.'],502);
}
function jsonRpc(string $method, array $params): array {
    $response = rpc('/json_rpc', [
        'jsonrpc' => '2.0',
        'id' => '0',
        'method' => $method,
        'params' => $params,
    ]);
    if (isset($response['error'])) throw new RuntimeException($response['error']['message'] ?? 'RPC error');
    return $response['result'] ?? [];
}

function rpc(string $path, array $payload): array {
    // Daemon endpoints expect an empty JSON object, not an empty JSON array.
    $json = $payload === [] ? '{}' : json_encode($payload, JSON_THROW_ON_ERROR);
    if (function_exists('curl_init')) {
        $curl = curl_init(NODE_RPC . $path);
        curl_setopt_array($curl, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $json,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_TIMEOUT => 12,
        ]);
        $body = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
        $message = curl_error($curl);
        curl_close($curl);
        if ($body === false || $status !== 200) throw new RuntimeException($message ?: 'HTTP ' . $status);
    } else {
        $context = stream_context_create(['http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/json\r\nConnection: close\r\n",
            'content' => $json,
            'timeout' => 12,
            'ignore_errors' => true,
        ]]);
        $body = @file_get_contents(NODE_RPC . $path, false, $context);
        $statusLine = $http_response_header[0] ?? '';
        preg_match('/\s(\d{3})\s/', $statusLine, $match);
        $status = isset($match[1]) ? (int)$match[1] : 0;
        if ($body === false || $status !== 200) throw new RuntimeException('HTTP ' . $status);
    }
    $decoded = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
    return is_array($decoded) ? $decoded : [];
}

function respond(array $data, int $status = 200): never {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}
