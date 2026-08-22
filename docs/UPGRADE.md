# Monzero upgrade and rollback guide

Monzero Genesis prereleases are experimental. Back up wallet files, mnemonic
seeds, and the node data directory before replacing any binary. Never enter a
Monero seed into Monzero or a Monzero seed into Monero.

## Supported migration path

This candidate supports upgrades from an earlier Monzero Genesis prerelease
that uses the same protected network identifiers and genesis block. It does
not support migrating Monero mainnet data, wallets, or keys. Asset hard fork
17 is not scheduled on any public network; `--regtest-asset-hard-fork` is only
for disposable local testing.

1. Stop the GUI, wallet RPC, wallet CLI, miners, and daemon cleanly.
2. Copy wallet files and the `.monzero` data directory to offline backup
   storage. Keep the previous verified binaries and their checksums.
3. Verify the new archive SHA-256 and its internal `SHA256SUMS` before use.
4. Extract into a new directory rather than overwriting the previous release.
5. Start `monzerod`, confirm the expected Monzero version, network, height, and
   peer state, then open the wallet and allow it to synchronize.
6. Confirm the primary address and balances before sending funds.

No database migration is intentionally introduced by the Genesis candidate.
An existing database may still be upgraded by inherited database code and
must therefore be treated as non-downgradable without restoring its backup.

## Rollback

Stop all Monzero processes before rollback. Restore both the previous binaries
and the matching pre-upgrade data-directory backup. Do not run an older binary
against a database that a newer binary has opened. If no database backup is
available, move the current data directory aside and synchronize an empty one
with the previous verified daemon. Wallet restoration must use only the
original Monzero seed and a trusted restore height.

Report suspected security issues through the published private security
contact once that release prerequisite is established. Do not disclose wallet
seeds, private keys, or sensitive logs in public reports.
