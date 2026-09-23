# Monzero Genesis pre15 release notes

Release label: genesis-pre15

Genesis pre15 is the next experimental prerelease candidate. It is not a
production release. Exact-artifact qualification is recorded separately from
these source-tree notes; final artifact digests and exact source commits must
be recorded in the package manifests and matching machine-readable release
metadata. Packaging alone does not authorize publication or deployment.

## Packaged platforms

| Package | Intended compatibility scope |
| --- | --- |
| Linux x86-64 CLI | glibc 2.35 or newer (verified on Ubuntu 24.04) |
| Windows x64 CLI | 64-bit Windows command-line environment |
| Windows x64 GUI | 64-bit Windows graphical environment |
| Complete source | Exact repository commit and recursive pinned submodules |

The binary archives are intended to contain `monzerod`, the command-line
wallet, and wallet RPC. The GUI is distributed separately with matching core
tools. macOS, Linux ARM, Windows ARM, mobile platforms, and 32-bit systems are
not qualified by this candidate.

## Changes since Genesis pre14

- **Wallets only open Monzero wallet files.** Keys files now carry a Monzero
  marker. Monero and other CryptoNote wallet files are refused with "this
  wallet file was not created by Monzero and cannot be opened". Wallets
  created by earlier Genesis prereleases open normally and receive the
  marker the first time they are opened. A wrong password is still reported
  as a wrong password, and a refused file is not modified.
- **Amounts are always XMZ with 11 decimal places.** A wallet file could
  previously switch amount parsing to Monero's 12 decimals, so that entering
  `1` sent 10 XMZ while the confirmation showed `1`. The CLI's mXMZ, uXMZ,
  nXMZ, and atomic-XMZ display units are removed; `set unit` accepts only
  `XMZ`. A prerelease wallet that had selected mXMZ, uXMZ, or nXMZ opens and
  is reset to XMZ.
- The wallet RPC now rejects `relay_tx` when the transaction's pending inputs
  no longer match the open wallet.
- `stop-mining.bat` and `stop-monzero-miner.sh` wait up to 120 seconds for the
  daemon. The first stop after startup waits for RandomX initialisation
  (measured at about 11 seconds) and previously reported failure even though
  mining stopped.
- `monzero-wallet-rpc` writes `monzero` rather than `monero` as the username
  in its generated `.login` file.
- The Linux CLI binaries are built in the pinned `contrib/depends`
  environment inside an Ubuntu 22.04 container and depend only on the system
  C library. The pre14 Linux archive linked the build host's Boost, libsodium,
  ZeroMQ, unbound, and hidapi libraries, required glibc 2.38, and did not
  start on Ubuntu 24.04.
- Test fixes: the amount-parsing test uses 11 decimals, the Python RPC test
  framework covers `get_assets` and `get_asset_outputs`, and wallet storage
  tests use Monzero wallet fixtures.
- No mainnet consensus identity, genesis block, address prefix, port, monetary
  policy, or public hard-fork schedule changed. Monzero Assets remain inactive
  on every public network.

## Source-tree verification performed

- All 23 `ctest` suites pass (100%) at source commit `e2af2cdbc` on the Linux
  release workstation, run serially on 2026-09-23 (2,469 seconds total). This
  includes `core_tests` (full consensus replay, 1,411 seconds),
  `functional_tests_rpc`, `functional_tests_assets` (activated-regtest assets
  on regtest only), `check_missing_rpc_methods`, `unit_tests`, and the
  RandomX, hash-family, difficulty, and block-weight suites.
- `unit_tests` reports 1,315 passing tests, including 8 new wallet-origin and
  decimal-point tests; 2 hardware-dependent `is_hdd` tests are skipped.
- The functional suites must run one at a time; parallel `ctest -j` runs make
  them collide on local ports. `node_server.race_condition` can abort
  intermittently when run immediately after them; it passes on rerun.
- Linux and Windows binaries built from this commit in the pinned environment
  report version `0.18.5.1-e2af2cdbc`. On a clean Ubuntu 24.04 VM the Linux
  daemon synchronized from the public nodes and the CLI created a wallet. On a
  clean Windows 11 VM, `start-node.bat` synchronized, `start-mining.bat` and
  `stop-mining.bat` succeeded, a wallet was created, and a Monero wallet file
  was refused.

These are source-tree results. They do not qualify a particular binary archive
without matching artifact evidence, and they are not an independent security review.

## Known limitations and safety notices

- Each pre15 artifact must complete the full clean qualification cycle before
  publication; consult its exact-hash evidence rather than assuming these
  source-tree test results apply to it.
- **A prerelease wallet that had selected the atomic-XMZ display unit cannot
  be opened**, because that setting was also used by Monero wallets and does
  not prove the file was created by Monzero. Restore it from its recovery
  seed. No other prerelease wallet is affected.
- The wallet file check cannot detect a Monero seed or private keys typed
  into Monzero's restore options. Never reuse them.
- The Windows GUI archive is built from GUI commit `0018a58f`, the newest GUI
  commit compatible with this core's wallet API; unmerged asset transfer/burn
  and DEX work on the GUI development tip is not included.
- Packages and release metadata will remain unsigned until the offline release
  signing process is completed.
- A separately trusted operator has not reproduced and signed the binaries.
- Consensus, cryptography, and the broader implementation have not completed
  an independent audit.
- The public network has limited independent infrastructure and hash power.
- Windows SmartScreen may warn until the executables are code-signed.
- Never reuse a Monero or other CryptoNote-derived seed, keys, wallet file, or
  data directory with Monzero.

## Upgrade and rollback

Read `UPGRADE.md` before replacing binaries. Stop wallets, miners, and the
daemon cleanly; back up wallet files, seeds, node configuration, and the data
directory; verify the archive and its internal manifest; and extract into a
new directory. Keep the previous verified binaries and matching data backup
until the upgraded node has synchronized and remained healthy.

## Verification and reporting

Compare downloads with the SHA-256 values in the final published JSON metadata
and adjacent `.sha256` files. Review `BUILD-MANIFEST.txt` or
`SOURCE-MANIFEST.txt` inside the archive before use. Current evidence and
unresolved gates are recorded in `RELEASE_STATUS.md` and
`RELEASE_CHECKLIST.md`. Report security issues privately to
`security@monzero.org`; never include wallet seeds or private keys.
