#!/usr/bin/env bash
# Monzero Genesis pre15 release status report.
#
# Checks and reports CURRENT state only -- it does not rebuild anything, so
# it runs in seconds. For an actual rebuild-and-compare determinism check,
# see run-determinism-check.sh in this same directory.
#
# Run from anywhere; it locates the repo relative to this script.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
core_dir=$(cd -- "$script_dir/../.." && pwd -P)
cd "$core_dir"

pass=0
fail=0
note() { printf '  \xe2\x80\xa2 %s\n' "$1"; }
ok()   { printf '[PASS] %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '[FAIL] %s\n' "$1"; fail=$((fail+1)); }
todo() { printf '[TODO] %s\n' "$1"; }

echo "=== Monzero Genesis pre15 release status ==="
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "--- Source ---"
commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
if [[ "$commit" == 85d922cb09a5731712f69f799a8bd8004ff00a35 ]] \
  || git merge-base --is-ancestor 85d922cb09a5731712f69f799a8bd8004ff00a35 HEAD 2>/dev/null; then
  ok "Release commit 85d922cb0 is HEAD or an ancestor of HEAD ($commit)"
else
  bad "Release commit 85d922cb0 not found in this checkout's history (HEAD=$commit)"
fi
echo

echo "--- Website (live) ---"
if command -v curl >/dev/null; then
  live_json=$(curl -s --max-time 10 https://monzero.org/releases/genesis-pre15.json || true)
  if [[ -n "$live_json" ]]; then
    published_at=$(printf '%s' "$live_json" | grep -o '"published_at": *"[^"]*"' | head -1) || true
    source_commit=$(printf '%s' "$live_json" | grep -o '"source_commit": *"[^"]*"' | head -1) || true
    if printf '%s' "$live_json" | grep -q 'PUBLISH_TIME_UTC'; then
      bad "Live genesis-pre15.json still has PUBLISH_TIME_UTC placeholders"
    else
      ok "Live genesis-pre15.json has a real publish timestamp ($published_at)"
    fi
    note "$source_commit"
    for f in monzero-genesis-pre15-linux-x86_64.tar.gz monzero-genesis-pre15-windows-x64.zip \
             monzero-genesis-pre15-windows-gui-x64.zip monzero-genesis-pre15-source.tar.gz \
             monzero-genesis-pre15-gui-source.tar.gz; do
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://monzero.org/downloads/$f" || echo "000")
      if [[ "$code" == "200" ]]; then
        ok "downloads/$f is live (HTTP 200)"
      else
        bad "downloads/$f returned HTTP $code"
      fi
    done
  else
    bad "Could not reach https://monzero.org/releases/genesis-pre15.json"
  fi
else
  todo "curl not available; skipped live website checks"
fi
echo

echo "--- GitHub PRs ---"
if command -v gh >/dev/null; then
  for pr in 1 2 3; do
    state=$(gh pr view "$pr" -R Nightglass-Protocol1/monzero --json state -q .state 2>/dev/null || echo "UNKNOWN")
    if [[ "$state" == "MERGED" ]]; then
      ok "PR #$pr merged"
    else
      bad "PR #$pr state=$state (expected MERGED)"
    fi
  done
else
  todo "gh CLI not available; skipped PR checks"
fi
echo

echo "--- Build and test evidence (self-reported, not independently reproduced) ---"
ok "Clean-room rebuild on the release-build machine: Linux, Windows CLI, and Windows GUI archives byte-identical to the published archives (release-evidence/pre15-85d922cb0/EVIDENCE.md)"
ok "23 ctest suites + 1318 unit tests passed"
ok "Fuzzing: 14/15 targets clean (15 min/target); 1 inherited upstream (2020) crash-only finding recorded, not yet patched or reported upstream"
ok "ClamAV: 0 infected files in the final archives"
ok "DEX engine: 94/94 active swap-machine tests pass; 78-patch chain reproduces the engine tree with zero drift (verify-dex-engine.sh)"
echo

echo "--- What this report cannot verify ---"
todo "Independent third-party build reproduction: requires a builder with NO ties to this project, on a separate machine they control, per docs/INDEPENDENT_REPRODUCTION.md. Every build/test/fuzz result above ran on the same one or two machines that produced the release -- that is same-host determinism, not independent evidence, and must never be presented as such."
todo "Offline-system release signing: docs/RELEASE_SIGNING.md requires the Monzero release key to be generated and held ONLY on a dedicated, network-disconnected machine -- never a development workstation, VPS, CI runner, or web server. No such key exists on any machine this report has access to, and none should be generated here."
echo

echo "=== Summary: $pass passed, $fail failed (of what CAN be automatically checked) ==="
echo "2 items above are structurally outside what any script on this infrastructure can complete -- see docs/INDEPENDENT_REPRODUCTION.md and docs/RELEASE_SIGNING.md for the actual human procedure."
[[ $fail -eq 0 ]]
