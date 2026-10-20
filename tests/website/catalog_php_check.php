<?php
// Reads [{kind, json}] on stdin; prints a JSON list of booleans from lib/catalogs.php.
declare(strict_types=1);
require dirname(__DIR__, 2) . '/website/lib/catalogs.php';
$today = $argv[1];
$cases = json_decode((string)stream_get_contents(STDIN), true);
echo json_encode(array_map(fn($c) => catalogProblem($c['kind'], $c['json'], $today) === null, $cases));
