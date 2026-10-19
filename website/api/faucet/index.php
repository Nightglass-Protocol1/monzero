<?php
declare(strict_types=1);
// Faucet status only. Payouts are not implemented; see docs/FAUCET_ARCHITECTURE.md.
// This endpoint reads no configuration and cannot report anything but paused.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=300');
header('X-Content-Type-Options: nosniff');
if (!in_array($_SERVER['REQUEST_METHOD'] ?? '', ['GET', 'HEAD'], true)) {
    http_response_code(405);
    header('Allow: GET, HEAD');
    echo json_encode(['schema' => 'monzero-faucet-v1', 'status' => 'paused', 'error' => 'Claims are not accepted.']);
    exit;
}
echo json_encode(['schema' => 'monzero-faucet-v1', 'status' => 'paused',
    'reason' => 'The faucet has not been approved, funded or security tested. No claims are accepted.']);
