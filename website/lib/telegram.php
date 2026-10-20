<?php
declare(strict_types=1);
// Telegram alerts for pool miners. People message the bot privately with /watch <address>; the
// site checks the pool API (on each node check-in, at most every 5 minutes) and messages them when
// workers go offline, hashrate drops sharply or a payout is sent. It stores the chat ID and the
// watched addresses until /stop. Without ~/monzero-private/telegram-config.php everything is off.
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }
require_once __DIR__ . '/xmz-address.php';

const TG_MAX_PER_CHAT = 5;
const TG_MAX_TOTAL = 5000;
const TG_CHECK_SECONDS = 300;
const TG_DEFAULT_DROP = 50;      // percent below the usual hashrate
const TG_DEFAULT_OFFLINE = 20;   // minutes with no hashrate
const TG_HELP = "Monzero pool alerts\n\n/watch ADDRESS [name] - alerts for a pool address (up to 5)\n/list - what you watch\n/stop ADDRESS or /stop all - stop alerts and delete the address\n/drop PERCENT - alert when hashrate falls this far below usual (10-90, now %d%%)\n/offline MINUTES - alert after this long with no hashrate (10-240, now %d)\n\nThe website keeps this chat ID and the addresses you watch until you /stop. Alerts are best effort; the pool's own page is authoritative.";

function tgPrivateDir(): string { $d = getenv('MONZERO_PRIVATE_DIR'); return is_string($d) && $d !== '' ? $d : dirname(__DIR__, 2) . '/monzero-private'; }

function tgConfig(): ?array {
    $path = tgPrivateDir() . '/telegram-config.php';
    $c = is_file($path) && !is_link($path) ? (static fn() => require $path)() : null;
    if (!is_array($c) || !is_string($c['bot_token'] ?? null) || !preg_match('/\A\d{5,15}:[A-Za-z0-9_-]{30,60}\z/', $c['bot_token'])
        || !is_string($c['webhook_secret'] ?? null) || !preg_match('/\A[A-Za-z0-9_-]{32,256}\z/', $c['webhook_secret'])) return null;
    return ['bot_token' => $c['bot_token'], 'webhook_secret' => $c['webhook_secret'], 'bot_username' => is_string($c['bot_username'] ?? null) ? $c['bot_username'] : '',
        'api' => is_string($c['api'] ?? null) ? $c['api'] : 'https://api.telegram.org', 'pool_api' => is_string($c['pool_api'] ?? null) ? $c['pool_api'] : 'https://pool.monzero.org/api/miner',
        // Optional public feed: the community group or channel (@name or numeric id) the bot posts to.
        'feed_chat' => is_string($c['feed_chat'] ?? null) && preg_match('/\A(@[A-Za-z][A-Za-z0-9_]{4,31}|-?\d{5,20})\z/', $c['feed_chat']) ? $c['feed_chat'] : null,
        'feed_pin' => ($c['feed_pin'] ?? true) === true,
        'feed_pool_hours' => is_int($c['feed_pool_hours'] ?? null) && $c['feed_pool_hours'] >= 0 && $c['feed_pool_hours'] <= 168 ? $c['feed_pool_hours'] : 24,
        'pool_stats' => is_string($c['pool_stats'] ?? null) ? $c['pool_stats'] : 'https://pool.monzero.org/api/stats'];
}

function tgDb(): PDO {
    static $db = null;
    if ($db) return $db;
    $path = tgPrivateDir() . '/telegram.sqlite';
    if (!is_dir(dirname($path))) @mkdir(dirname($path), 0700, true);
    $new = !file_exists($path);
    $db = new PDO('sqlite:' . $path, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
    if ($new) @chmod($path, 0600);
    $db->exec('PRAGMA busy_timeout = 5000;');
    if ((int)$db->query('PRAGMA user_version')->fetchColumn() < 1) {
        $db->exec(<<<'SQL'
            BEGIN;
            CREATE TABLE chats (chat_id INTEGER PRIMARY KEY, drop_percent INTEGER NOT NULL, offline_minutes INTEGER NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE watches (chat_id INTEGER NOT NULL REFERENCES chats(chat_id), address TEXT NOT NULL, name TEXT NOT NULL, state TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL, PRIMARY KEY (chat_id, address));
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            PRAGMA user_version = 1;
            COMMIT;
        SQL);
    }
    return $db;
}

function tgApi(array $config, string $method, array $params): ?array {
    $context = stream_context_create(['http' => ['method' => 'POST', 'header' => 'Content-Type: application/json', 'timeout' => 8, 'ignore_errors' => true,
        'content' => json_encode($params, JSON_UNESCAPED_UNICODE)]]);
    $body = @file_get_contents(rtrim($config['api'], '/') . '/bot' . $config['bot_token'] . '/' . $method, false, $context, 0, 1048576);
    $data = is_string($body) ? json_decode($body, true) : null;
    return is_array($data) ? $data : null;
}

function tgSend(array $config, int $chat, string $text): bool {
    $r = tgApi($config, 'sendMessage', ['chat_id' => $chat, 'text' => mb_substr($text, 0, 3500), 'disable_web_page_preview' => true]);
    if (($r['ok'] ?? false) !== true && in_array($r['error_code'] ?? 0, [403, 400], true)) {
        // Blocked or deleted chat: forget it.
        tgDb()->prepare('DELETE FROM watches WHERE chat_id = ?')->execute([$chat]);
        tgDb()->prepare('DELETE FROM chats WHERE chat_id = ?')->execute([$chat]);
    }
    return ($r['ok'] ?? false) === true;
}

function tgChat(int $chat): array {
    $db = tgDb();
    $db->prepare('INSERT OR IGNORE INTO chats (chat_id, drop_percent, offline_minutes, created_at) VALUES (?, ?, ?, ?)')->execute([$chat, TG_DEFAULT_DROP, TG_DEFAULT_OFFLINE, time()]);
    $stmt = $db->prepare('SELECT * FROM chats WHERE chat_id = ?');
    $stmt->execute([$chat]);
    return $stmt->fetch();
}

function tgMeta(string $key, ?string $value = null): ?string {
    $db = tgDb();
    if ($value !== null) {
        $db->prepare('INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value')->execute([$key, $value]);
        return $value;
    }
    $stmt = $db->prepare('SELECT value FROM meta WHERE key = ?');
    $stmt->execute([$key]);
    $v = $stmt->fetchColumn();
    return $v === false ? null : (string)$v;
}

// Post to the public feed (community group or channel). Never includes miner addresses.
function tgFeedSend(array $config, string $text, bool $pin = false): bool {
    if (!$config['feed_chat']) return false;
    $r = tgApi($config, 'sendMessage', ['chat_id' => $config['feed_chat'], 'text' => mb_substr($text, 0, 3800), 'disable_web_page_preview' => true]);
    if (($r['ok'] ?? false) !== true) {
        tgMeta('feed_error', gmdate('Y-m-d H:i') . ' UTC: ' . mb_substr((string)($r['description'] ?? 'no answer from Telegram'), 0, 200));
        return false;
    }
    tgMeta('feed_ok', (string)time());
    if ($pin && isset($r['result']['message_id'])) tgApi($config, 'pinChatMessage', ['chat_id' => $config['feed_chat'], 'message_id' => $r['result']['message_id'], 'disable_notification' => false]);
    return true;
}

function tgFeedAnnouncement(array $config, object $post, string $site = 'https://monzero.org'): bool {
    $url = $post->url ?? null;
    $link = is_string($url) ? (str_starts_with($url, '/') ? $site . $url : $url) : $site . '/community/';
    return tgFeedSend($config, "📢 {$post->title}\n\n{$post->body}\n\n$link", $config['feed_pin']);
}

// Pool update every feed_pool_hours: blocks found since the last update (from the pool's running
// total), latest height, hashrate and miner count. The first run only records a baseline.
function tgFeedPool(array $config, int $now): bool {
    if (!$config['feed_chat'] || $config['feed_pool_hours'] === 0) return false;
    $last = json_decode((string)tgMeta('feed_pool'), true);
    if (is_array($last) && $now - (int)$last['at'] < $config['feed_pool_hours'] * 3600) return false;
    $context = stream_context_create(['http' => ['timeout' => 6, 'ignore_errors' => true, 'follow_location' => 0]]);
    $stats = json_decode((string)@file_get_contents($config['pool_stats'], false, $context, 0, 4194304), true);
    $pool = $stats['pool'] ?? null;
    if (!is_array($pool) || !is_int($pool['totalBlocks'] ?? null) || !is_array($pool['blocks'] ?? null)) return false;
    $height = (int)($pool['blocks'][0]['height'] ?? 0);
    tgMeta('feed_pool', json_encode(['at' => $now, 'total' => $pool['totalBlocks'], 'height' => $height]));
    if (!is_array($last)) return false;
    $found = $pool['totalBlocks'] - (int)$last['total'];
    if ($found <= 0) return false;
    $hours = max(1, (int)round(($now - (int)$last['at']) / 3600));
    $rate = (float)($pool['hashrate'] ?? 0);
    $rateText = $rate >= 1e6 ? round($rate / 1e6, 2) . ' MH/s' : ($rate >= 1e3 ? round($rate / 1e3, 1) . ' kH/s' : round($rate) . ' H/s');
    $text = "⛏ Monzero pool update\n\nBlocks found in the last $hours hours: " . number_format($found) . ($height > (int)$last['height'] ? ' (heights ' . number_format((int)$last['height'] + 1) . '–' . number_format($height) . ')' : '')
        . "\nPool hashrate: $rateText from " . (int)($pool['miners'] ?? 0) . ' miners'
        . "\n\nMine with the pool: https://pool.monzero.org/\nAlerts for your rigs: t.me/" . ($config['bot_username'] ?: 'Monzero_bot');
    return tgFeedSend($config, $text);
}

function tgShort(string $address): string { return substr($address, 0, 8) . '…' . substr($address, -6); }

// Handle one webhook update; returns the reply text (or null for nothing to say).
function tgHandle(array $update): ?string {
    $message = $update['message'] ?? null;
    if (!is_array($message) || ($message['chat']['type'] ?? '') !== 'private' || !is_int($message['chat']['id'] ?? null) || !is_string($message['text'] ?? null)) return null;
    $chat = $message['chat']['id'];
    $parts = preg_split('/\s+/', trim($message['text']), 3) ?: [''];
    $command = strtolower((string)preg_replace('/@.*\z/', '', $parts[0]));
    $db = tgDb();
    $settings = tgChat($chat);
    switch ($command) {
        case '/start':
        case '/help':
            return sprintf(TG_HELP, $settings['drop_percent'], $settings['offline_minutes']);
        case '/watch':
            $parsed = xmzParseAddress($parts[1] ?? '');
            if (isset($parsed['error'])) return $parsed['error'] . ' Send: /watch ADDRESS [name]';
            if ($parsed['network'] !== 'mainnet' || $parsed['kind'] === 'integrated') return 'Use your main mainnet address, the one your miner uses for the pool.';
            $given = mb_substr(trim((string)preg_replace('/[\p{Cc}\p{Cf}]/u', '', $parts[2] ?? '')), 0, 32);
            $name = $given ?: tgShort($parsed['address']);
            $count = $db->prepare('SELECT COUNT(*) FROM watches WHERE chat_id = ?');
            $count->execute([$chat]);
            $exists = $db->prepare('SELECT 1 FROM watches WHERE chat_id = ? AND address = ?');
            $exists->execute([$chat, $parsed['address']]);
            if (!$exists->fetchColumn()) {
                if ((int)$count->fetchColumn() >= TG_MAX_PER_CHAT) return 'You already watch ' . TG_MAX_PER_CHAT . ' addresses. /stop one first.';
                if ((int)$db->query('SELECT COUNT(*) FROM watches')->fetchColumn() >= TG_MAX_TOTAL) return 'Alerts are full right now. Please try again later.';
            }
            // Watching again keeps the earlier name unless a new one is given.
            $db->prepare('INSERT INTO watches (chat_id, address, name, created_at) VALUES (?, ?, ?, ?) ON CONFLICT (chat_id, address) DO UPDATE SET name = CASE WHEN ? THEN excluded.name ELSE watches.name END')
                ->execute([$chat, $parsed['address'], $name, time(), $given !== '' ? 1 : 0]);
            $current = $db->prepare('SELECT name FROM watches WHERE chat_id = ? AND address = ?');
            $current->execute([$chat, $parsed['address']]);
            $name = (string)$current->fetchColumn();
            return "Watching $name (" . tgShort($parsed['address']) . "). You will hear about offline workers, hashrate drops below {$settings['drop_percent']}% of usual and payouts.";
        case '/list':
            $rows = $db->prepare('SELECT address, name FROM watches WHERE chat_id = ? ORDER BY created_at');
            $rows->execute([$chat]);
            $list = array_map(fn($r) => '- ' . $r['name'] . ' (' . tgShort($r['address']) . ')', $rows->fetchAll());
            return $list ? "You watch:\n" . implode("\n", $list) . "\nDrop alert: {$settings['drop_percent']}%. Offline alert: {$settings['offline_minutes']} min." : 'You do not watch any address. Send /watch ADDRESS.';
        case '/stop':
            $target = $parts[1] ?? '';
            if (strtolower($target) === 'all') {
                $db->prepare('DELETE FROM watches WHERE chat_id = ?')->execute([$chat]);
                $db->prepare('DELETE FROM chats WHERE chat_id = ?')->execute([$chat]);
                return 'Stopped. This chat and all its addresses were deleted.';
            }
            $stmt = $db->prepare('DELETE FROM watches WHERE chat_id = ? AND (address = ? OR name = ?)');
            $stmt->execute([$chat, $target, $target]);
            return $stmt->rowCount() ? 'Stopped and deleted that address.' : 'Not found. Send /list to see what you watch, or /stop all.';
        case '/drop':
        case '/offline':
            $value = filter_var($parts[1] ?? null, FILTER_VALIDATE_INT);
            [$min, $max, $column] = $command === '/drop' ? [10, 90, 'drop_percent'] : [10, 240, 'offline_minutes'];
            if ($value === false || $value < $min || $value > $max) return "Send $command followed by a number from $min to $max.";
            $db->prepare("UPDATE chats SET $column = ? WHERE chat_id = ?")->execute([$value, $chat]);
            return $command === '/drop' ? "You will be alerted when hashrate falls $value% below usual." : "You will be alerted after $value minutes with no hashrate.";
        default:
            return 'Send /help to see the commands.';
    }
}

function tgPool(array $config, string $address): ?array {
    $context = stream_context_create(['http' => ['timeout' => 6, 'ignore_errors' => true, 'follow_location' => 0]]);
    $body = @file_get_contents($config['pool_api'] . '?address=' . rawurlencode($address), false, $context, 0, 1048576);
    $data = is_string($body) ? json_decode($body, true) : null;
    return is_array($data) && ($data['address'] ?? null) === $address && is_numeric($data['hashrate'] ?? null) && is_array($data['payments'] ?? null) ? $data : null;
}

function tgXmz(mixed $atomic): string { return rtrim(rtrim(number_format((float)$atomic / 1e11, 8, '.', ''), '0'), '.') . ' XMZ'; }

// Evaluate every watch; returns the number of messages sent. Rate limited unless $force.
function tgCheckAll(int $now, bool $force = false): int {
    $config = tgConfig();
    if (!$config) return 0;
    $db = tgDb();
    $last = (int)($db->query("SELECT value FROM meta WHERE key = 'checked_at'")->fetchColumn() ?: 0);
    if (!$force && $now - $last < TG_CHECK_SECONDS) return 0;
    $db->prepare("INSERT INTO meta (key, value) VALUES ('checked_at', ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value")->execute([(string)$now]);
    try { tgFeedPool($config, $now); } catch (Throwable $e) { error_log('Monzero telegram feed: ' . $e->getMessage()); }
    $pool = [];
    $sent = 0;
    $started = microtime(true);
    foreach ($db->query('SELECT w.*, c.drop_percent, c.offline_minutes FROM watches w JOIN chats c ON c.chat_id = w.chat_id ORDER BY w.created_at')->fetchAll() as $w) {
        if (microtime(true) - $started > 45) break;   // keep the node check-in request short; the rest wait for the next run
        $stats = $pool[$w['address']] ??= tgPool($config, $w['address']);
        if (!$stats) continue;   // pool unreachable: say nothing rather than guess
        $state = json_decode($w['state'], true) ?: [];
        $rate = (float)$stats['hashrate'];
        $messages = [];
        // Payouts: announce payment txids not seen before (the first check only records them).
        $seen = $state['payments'] ?? null;
        $txids = array_column($stats['payments'], 'txid');
        if (is_array($seen)) foreach ($stats['payments'] as $p) if (is_string($p['txid'] ?? null) && !in_array($p['txid'], $seen, true))
            $messages[] = "Payout to {$w['name']}: " . tgXmz($p['amount'] ?? 0) . ' (tx ' . substr($p['txid'], 0, 16) . '…).';
        $state['payments'] = array_slice($txids, 0, 50);
        // Offline: no hashrate for the chosen minutes.
        if ($rate > 0) {
            if (!empty($state['offline_alerted'])) $messages[] = "{$w['name']} is mining again (" . round($rate) . ' H/s).';
            $state['offline_alerted'] = false;
            $state['online_at'] = $now;
            // Usual hashrate: slow moving average while online.
            $usual = (float)($state['usual'] ?? $rate);
            $threshold = $usual * (1 - $w['drop_percent'] / 100);
            if ($rate < $threshold && empty($state['drop_alerted']) && ($state['samples'] ?? 0) >= 3) {
                $messages[] = "{$w['name']} hashrate dropped to " . round($rate) . ' H/s from about ' . round($usual) . ' H/s.';
                $state['drop_alerted'] = true;
            } elseif ($rate >= $usual * 0.9 && !empty($state['drop_alerted'])) {
                $messages[] = "{$w['name']} hashrate recovered to " . round($rate) . ' H/s.';
                $state['drop_alerted'] = false;
            }
            if (empty($state['drop_alerted'])) $state['usual'] = round($usual * 0.8 + $rate * 0.2, 2);
            $state['samples'] = ($state['samples'] ?? 0) + 1;
        } elseif (isset($state['online_at']) && empty($state['offline_alerted']) && $now - (int)$state['online_at'] >= $w['offline_minutes'] * 60) {
            $messages[] = "{$w['name']} has had no hashrate on the pool for " . intdiv($now - (int)$state['online_at'], 60) . ' minutes.';
            $state['offline_alerted'] = true;
        }
        foreach ($messages as $m) if (tgSend($config, (int)$w['chat_id'], $m)) $sent++;
        $db->prepare('UPDATE watches SET state = ? WHERE chat_id = ? AND address = ?')->execute([json_encode($state), $w['chat_id'], $w['address']]);
    }
    return $sent;
}
