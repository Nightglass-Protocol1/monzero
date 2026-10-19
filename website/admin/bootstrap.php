<?php
declare(strict_types=1);
// Command line only: create the single owner account and email its one-time setup link.
//   php admin/bootstrap.php security@monzero.org
// Re-running for the same pending owner replaces the link. It refuses if another owner exists.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__ . '/lib.php';

$email = adminEmail($argv[1] ?? '');
if (!$email) { fwrite(STDERR, "Usage: php admin/bootstrap.php OWNER_EMAIL\n"); exit(2); }
$db = adminDb();
adminSecret(); // create the HMAC secret now so storage problems surface here
$db->beginTransaction();
$owner = $db->query('SELECT * FROM users WHERE is_owner = 1')->fetch();
if ($owner && $owner['email'] !== $email) { $db->rollBack(); fwrite(STDERR, "An owner already exists ({$owner['email']}). Refusing.\n"); exit(1); }
if ($owner && $owner['status'] !== 'pending') { $db->rollBack(); fwrite(STDERR, "The owner account is already set up. Use the sign-in page.\n"); exit(1); }
if (!$owner) {
    $taken = $db->prepare('SELECT 1 FROM users WHERE email = ?');
    $taken->execute([$email]);
    if ($taken->fetchColumn()) { $db->rollBack(); fwrite(STDERR, "That email already belongs to a non-owner account. Refusing.\n"); exit(1); }
    $db->prepare("INSERT INTO users (email, is_owner, permissions, status, created_at) VALUES (?, 1, '[]', 'pending', ?)")->execute([$email, time()]);
    $owner = ['id' => (int)$db->lastInsertId(), 'email' => $email];
}
$token = adminIssueToken((int)$owner['id'], 'setup', 'sent', null);
$db->commit();
adminAudit(null, 'owner.setup_link_issued', ['email' => $email]);
if (!adminSendLink(['email' => $email], $token, 'setup')) { fwrite(STDERR, "Owner created, but the email could not be sent. Re-run to try again.\n"); exit(1); }
echo "Setup link emailed to $email. It expires in 48 hours.\n";
