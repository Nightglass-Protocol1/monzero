<?php
declare(strict_types=1);
// Country-level node census storage. The collector on the node sends per-country counts only;
// this site never receives IP addresses, so it cannot store or reveal them.
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }

const CENSUS_SCHEMA = 'monzero-node-census-v1';
const CENSUS_HISTORY_DAYS = 400;
const CENSUS_STALE_SECONDS = 7200;
const CENSUS_MAX_COUNTRIES = 300;
const CENSUS_MAX_COUNT = 1000000;

function censusDir(): string {
    $configured = getenv('MONZERO_NODE_CENSUS_DIR');
    return is_string($configured) && $configured !== '' ? $configured : dirname(__DIR__, 2) . '/monzero-private/node-census';
}

function censusSecret(): string {
    $path = dirname(censusDir()) . '/node-census-config.php';
    $config = is_file($path) && !is_link($path) ? (static fn() => require $path)() : [];
    $secret = is_array($config) && is_string($config['secret'] ?? null) ? $config['secret'] : '';
    return preg_match('/\A[0-9a-f]{64}\z/', $secret) ? $secret : '';
}

function censusRead(string $name): ?array {
    $path = censusDir() . '/' . $name;
    if (!is_file($path) || is_link($path)) return null;
    $data = json_decode((string)@file_get_contents($path, false, null, 0, 4194304), true);
    return is_array($data) ? $data : null;
}

function censusWrite(string $name, array $data): void {
    $directory = censusDir();
    if (!is_dir($directory)) @mkdir($directory, 0700, true);
    if (!is_dir($directory) || is_link($directory)) throw new RuntimeException('census storage unavailable');
    $tmp = $directory . '/.' . $name . '.' . bin2hex(random_bytes(6));
    $old = umask(077);
    try {
        if (file_put_contents($tmp, json_encode($data, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)) === false || !rename($tmp, "$directory/$name"))
            throw new RuntimeException('census write failed');
    } finally { umask($old); @unlink($tmp); }
}

function censusCountsValid(mixed $c): bool {
    if (!is_array($c) || array_keys($c) !== ['observed', 'reachable', 'connected']) return false;
    foreach ($c as $v) if (!is_int($v) || $v < 0 || $v > CENSUS_MAX_COUNT) return false;
    return $c['reachable'] <= $c['observed'] && $c['connected'] <= $c['observed'];
}

// Returns null when the payload is acceptable, otherwise a short reason.
function censusProblem(mixed $p, int $now): ?string {
    if (!is_array($p) || array_keys($p) !== ['schema', 'observed_at', 'window_seconds', 'totals', 'countries', 'geo_database']) return 'shape';
    if ($p['schema'] !== CENSUS_SCHEMA || $p['window_seconds'] !== 86400) return 'schema';
    if (!is_int($p['observed_at']) || abs($now - $p['observed_at']) > 600) return 'time';
    if (!is_string($p['geo_database']) || !preg_match('/\A[A-Za-z0-9._-]{1,80}\z/', $p['geo_database'])) return 'geo_database';
    if (!censusCountsValid($p['totals']) || !is_array($p['countries']) || count($p['countries']) > CENSUS_MAX_COUNTRIES) return 'totals';
    $sum = ['observed' => 0, 'reachable' => 0, 'connected' => 0];
    foreach ($p['countries'] as $code => $counts) {
        if (!is_string($code) || !preg_match('/\A[A-Z]{2}\z/', $code) || !censusCountsValid($counts) || $counts['observed'] === 0) return 'country';
        foreach ($sum as $k => $_) $sum[$k] += $counts[$k];
    }
    return $sum === $p['totals'] ? null : 'sum';
}
