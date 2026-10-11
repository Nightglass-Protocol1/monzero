# Monzero Genesis pre16 release notes

Release label: genesis-pre16

Genesis pre16 is the next experimental prerelease candidate. It is not a
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

## Changes since Genesis pre15

- **Wallets no longer fail on unmixable early outputs.** Monzero's first three
  blocks paid pre-RingCT coinbase outputs in fixed denominations that exist
  only a few times on chain. Normal coin selection could pick one of them, and
  every transfer from that wallet then failed with "not enough outputs for
  specified ring size = 16". The wallet now asks the node which pre-RingCT
  amounts have enough unlocked outputs for a full ring and leaves the rest
  out, for ordinary transfers and for sweeps. The request lists every standard
  denomination, so it works with restricted public nodes and does not reveal
  which amounts the wallet holds. Wallets without pre-RingCT outputs make no
  extra request.
- **The GUI's Assets & NFT Studio matches monzero.org/app.** Choose NFT,
  edition, collection or token; the GUI fingerprints the artwork locally
  (SHA-256, size, type and dimensions), builds canonical
  `monzero-metadata/1` JSON whose SHA-256 is the asset's metadata hash, shows
  a live preview, checks the descriptor against consensus limits, saves
  `metadata.json`, and copies the matching `asset_create` command. A verify
  panel checks a metadata file and image against their hashes. The metadata
  is byte-identical to what the website produces for the same inputs.
  Issuance stays disabled until hard fork 17 activates.
- All changes listed for Genesis pre15 are included.
- No mainnet consensus identity, genesis block, address prefix, port, monetary
  policy, or public hard-fork schedule changed. Monzero Assets remain inactive
  on every public network.

## Source-tree verification performed

- All 23 `ctest` suites pass (100%) at source commit `5ba344a16` (the
  release commit adds only these notes) on the Linux release workstation,
  run serially on 2026-10-11. This includes `core_tests` (full consensus
  replay, 1,306 seconds), `functional_tests_rpc`, `functional_tests_assets`
  (activated-regtest assets on regtest only), `check_missing_rpc_methods`,
  `unit_tests`, and the RandomX, hash-family, difficulty, and block-weight
  suites.
- `unit_tests` reports 1,318 passing tests; 2 hardware-dependent `is_hdd`
  tests are skipped.
- On mainnet, a wallet holding the 18 pre-RingCT coinbase outputs of blocks
  1–3 could not build any transfer before this fix. With the fix, and with
  none of those outputs frozen, it built and sent single-recipient,
  three-recipient, and six-input transfers through the restricted public
  node, all with 16-member rings, and confirmed in block 5,963. A wallet
  created offline completed a transfer and a sweep.
- The functional suites must run one at a time; parallel `ctest -j` runs make
  them collide on local ports.

These are source-tree results. They do not qualify a particular binary archive
without matching artifact evidence, and they are not an independent security review.

## Known limitations and safety notices

- Each pre16 artifact must complete the full clean qualification cycle before
  publication; consult its exact-hash evidence rather than assuming these
  source-tree test results apply to it.
- **A prerelease wallet that had selected the atomic-XMZ display unit cannot
  be opened**, because that setting was also used by Monero wallets and does
  not prove the file was created by Monzero. Restore it from its recovery
  seed. No other prerelease wallet is affected.
- The wallet file check cannot detect a Monero seed or private keys typed
  into Monzero's restore options. Never reuse them.
- The Windows GUI archive is built from GUI commit `0018a58f` plus the Studio
  rework, the newest GUI code compatible with this core's wallet API; unmerged
  asset transfer/burn and DEX work on the GUI development tip is not included.
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
