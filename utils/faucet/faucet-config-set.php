<?php
declare(strict_types=1);
// Command line only: change one key in ~/monzero-private/faucet-config.php, keeping a backup.
//   php faucet-config-set.php worker_secret < secret-file     (value read from stdin)
//   php faucet-config-set.php enabled true|false
// Secrets go through stdin so they never appear in a process list or shell history.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }

$key = $argv[1] ?? '';
$path = getenv('MONZERO_FAUCET_CONFIG') ?: getenv('HOME') . '/monzero-private/faucet-config.php';
if ($key === 'worker_secret') {
    $value = trim((string)stream_get_contents(STDIN));
    if (!preg_match('/\A[0-9a-f]{64}\z/', $value)) { fwrite(STDERR, "worker_secret must be 64 hex characters on stdin\n"); exit(2); }
} elseif ($key === 'enabled' && in_array($argv[2] ?? '', ['true', 'false'], true)) {
    $value = $argv[2] === 'true';
} else {
    fwrite(STDERR, "Usage: php faucet-config-set.php worker_secret < file | enabled true|false\n"); exit(2);
}
if (!is_file($path) || is_link($path)) { fwrite(STDERR, "No faucet config at $path\n"); exit(1); }
$config = (static fn() => require $path)();
if (!is_array($config)) { fwrite(STDERR, "$path does not return an array\n"); exit(1); }

$backup = $path . '.bak-' . gmdate('Ymd\THis\Z');
if (!copy($path, $backup) || !chmod($backup, 0600)) { fwrite(STDERR, "Could not write the backup $backup\n"); exit(1); }
$config[$key] = $value;
$tmp = $path . '.tmp';
$old = umask(077);
$ok = file_put_contents($tmp, "<?php return " . var_export($config, true) . ";\n") !== false && chmod($tmp, 0600) && rename($tmp, $path);
umask($old);
if (!$ok) { @unlink($tmp); fwrite(STDERR, "Could not write $path\n"); exit(1); }
echo "Set $key in $path" . ($key === 'enabled' ? ' to ' . $argv[2] : '') . " (backup: $backup)\n";
