<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    header('Allow: POST');
    echo json_encode(['status' => 'METHOD_NOT_ALLOWED']);
    exit;
}

$url = 'http://node.monzero.org:6175/get_info';
$error = '';

if (function_exists('curl_init')) {
    $curl = curl_init($url);
    curl_setopt_array($curl, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => '{}',
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 2,
        CURLOPT_TIMEOUT => 5,
    ]);
    $response = curl_exec($curl);
    $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    $error = curl_error($curl);
    curl_close($curl);
} else {
    $context = stream_context_create(['http' => [
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\nConnection: close\r\n",
        'content' => '{}',
        'timeout' => 5,
        'ignore_errors' => true,
    ]]);
    $response = @file_get_contents($url, false, $context);
    $statusLine = $http_response_header[0] ?? '';
    preg_match('/\s(\d{3})\s/', $statusLine, $match);
    $status = isset($match[1]) ? (int)$match[1] : 0;
    $error = 'HTTP ' . $status;
}

$decoded = is_string($response) ? json_decode($response, true) : null;
if ($response === false || $status !== 200 || !is_array($decoded)) {
    http_response_code(502);
    echo json_encode(['status' => 'NODE_UNAVAILABLE']);
    error_log('Monzero node status proxy failed: ' . $error);
    exit;
}

$peerCount = (int)($decoded['incoming_connections_count'] ?? 0)
    + (int)($decoded['outgoing_connections_count'] ?? 0);
$decoded['connections_hidden'] = !empty($decoded['restricted']) && $peerCount === 0;
echo json_encode($decoded, JSON_UNESCAPED_SLASHES);
