#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

fail=false

check_absent() {
  local description=$1
  local pattern=$2
  shift 2
  if grep -RInE -- "$pattern" "$@"; then
    echo "User-facing branding gate failed: $description" >&2
    fail=true
  fi
}

for completion in monzerod monzero-wallet-cli monzero-wallet-rpc; do
  file="utils/fish/${completion}.fish"
  [[ -f $file ]] || {
    echo "User-facing branding gate failed: missing $file" >&2
    fail=true
    continue
  }
  grep -Fq "complete -c ${completion}" "$file" || {
    echo "User-facing branding gate failed: $file does not register ${completion}" >&2
    fail=true
  }
done

for obsolete in utils/fish/monerod.fish utils/fish/monero-wallet-cli.fish utils/fish/monero-wallet-rpc.fish; do
  [[ ! -e $obsolete ]] || {
    echo "User-facing branding gate failed: obsolete completion remains: $obsolete" >&2
    fail=true
  }
done

check_absent \
  "Fish completions contain inherited product names, services, or ports" \
  '(^|[^[:alnum:]_])(monerod|monero-wallet-(cli|rpc)|Monero)([^[:alnum:]_]|$)|getmonero\.org|(^|[^0-9])(1808[0-2]|2808[0-2]|3808[0-2])([^0-9]|$)' \
  utils/fish

check_absent \
  "active runtime defaults contain inherited executable or file names" \
  'monero-wallet-(cli|rpc)\.(log|login)|Please run monerod|monerod is now disconnected' \
  src/simplewallet/simplewallet.cpp \
  src/wallet/wallet_rpc_server.cpp \
  src/blockchain_db/lmdb/db_lmdb.cpp \
  src/cryptonote_protocol/cryptonote_protocol_handler.inl

if $fail; then
  exit 1
fi

echo "User-facing branding gate passed"
