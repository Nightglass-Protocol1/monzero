# Monzero Genesis pre14 release notes

Release label: genesis-pre14

Genesis pre14 is the next experimental prerelease candidate. It is not a
production release. Exact-artifact qualification is recorded separately from
these source-tree notes; final artifact digests and exact source commits must
be recorded in the package manifests and matching machine-readable release
metadata. Packaging alone does not authorize publication or deployment.

## Packaged platforms

| Package | Intended compatibility scope |
| --- | --- |
| Linux x86-64 CLI | glibc 2.31 or newer |
| Windows x64 CLI | 64-bit Windows command-line environment |
| Windows x64 GUI | 64-bit Windows graphical environment |
| Complete source | Exact repository commit and recursive pinned submodules |

The binary archives are intended to contain `monzerod`, the command-line
wallet, and wallet RPC. The GUI is distributed separately with matching core
tools. macOS, Linux ARM, Windows ARM, mobile platforms, and 32-bit systems are
not qualified by this candidate.

## Changes since Genesis pre13

- Added isolated, fixture-only DEX-lab preparation tooling (`utils/dex-lab/`)
  for a separate, air-gapped-from-production VM: preflight checks,
  Bitcoin-regtest/Monzero-fakechain health validation, disposable settlement
  and lock-PSBT fixture construction with crash-safe recovery metadata, and a
  bounded/authenticated live-lab RPC checker. It ships no live adapters, no
  atomic settlement, and no funds verification, and is not wired into any
  release package or public network path.
- Recorded that the `Nightglass-Protocol1/monzero` GitHub mirror has not yet
  passed this project's own MFA/two-owner, branch-protection, signed-tag, and
  clean-clone checklist for a canonical forge, so the gap is a documented,
  deliberate decision rather than a silent one.
- Updated the website to state plainly that the DEX research GUI under local
  testing is not part of any published download, that real-money DEX trading,
  cross-chain settlement, refunds, and fee enforcement remain unimplemented,
  and to warn against sending funds or disclosing seeds to test it.
- Corrected `RELEASE_STATUS.md` to name the revised (revision 2) pre13 GUI
  commit and its Windows GUI archive and GUI source digests, which had still
  named the superseded revision 1 identifiers.
- Closed a release-verification gap where a Windows GUI archive could ship
  binaries built against a different core commit than the one its manifest
  declared: `verify-windows-gui-package.sh` now checks that
  `GUI_BUILD_MANIFEST.txt`'s declared core version matches its declared core
  source commit, and that every packaged executable embeds that exact version
  string. `tests/phase0/test-gui-package-version.py` exercises both new
  failure modes against a real, otherwise-valid archive.
- Added `.gitignore` patterns for wallet key and backup files (`*.keys`,
  `/Wallet*`) as a backstop against an accidental commit of wallet material
  alongside the public mirror.
- Triggered a CI workflow run to verify the GitHub organization's Actions
  policy; no source, build, or release-script change resulted.
- No mainnet consensus identity, genesis block, address prefix, port, monetary
  policy, or public hard-fork schedule changed. Monzero Assets remain inactive
  on every public network. No file under `src/` changed since Genesis pre13.

## Source-tree verification performed

- All 1,305 unit tests pass on the local Linux build (160 test cases; full
  `ctest` run 2026-09-17, 3,599 seconds total).
- All 20 `ctest` suites pass (100%), including `core_tests` (full consensus
  replay), `unit_tests`, `cnv4-jit`, `cncrypto`, `wallet-crypto-bench`,
  `block_weight`, `difficulty`/`wide_difficulty`, and the RandomX/hash-family
  suites.
- `monzerod`, `monzero-wallet-cli`, and `monzero-wallet-rpc` were rebuilt from
  this exact commit and report matching version strings.
- The RPC functional-test suite (`functional_tests_rpc`) could not run on this
  build host: the `monotonic`, `zmq`, and `deepdiff` Python modules are not
  installed. This is an environment gap, not a code regression; it was also
  skipped, for the same reason, in this build.

These are source-tree results. They do not qualify a particular binary archive
without matching artifact evidence, and they are not an independent security review.

## Known limitations and safety notices

- Each pre14 artifact must complete the full clean qualification cycle before
  publication; consult its exact-hash evidence rather than assuming these
  source-tree test results apply to it.
- This candidate's Linux CLI archive (`monzerod`, `monzero-wallet-cli`,
  `monzero-wallet-rpc`) was built with the ordinary system toolchain on the
  release workstation, not the pinned reproducible-build/depends environment
  used for prior published candidates; it has not passed strict package
  verification (`RELEASE_STRICT=1`) or the digest-pinned container smoke test.
- A Windows x64 CLI archive (`monzerod.exe`, `monzero-wallet-cli.exe`,
  `monzero-wallet-rpc.exe`) was produced for this candidate using this
  project's pinned `contrib/depends` cross-toolchain (`x86_64-w64-mingw32`,
  posix threading variant), matching this exact source commit
  (`0.18.5.1-14cf088a4`). SHA-256:
  `1050e444c24e8e5a19c26e2c710080d17a2c5a08990e8b5818b4c39ec4ed6bcf`. It has
  not been run on a native Windows host; the checks in
  `WINDOWS_NATIVE_TEST.md` (native version, daemon startup, offline RPC,
  clean shutdown) remain outstanding before this archive can be trusted.
- No Windows GUI archive was produced for this candidate.
- The Linux GUI archive for this candidate reuses the exact Genesis pre13 GUI
  binary and its pinned core commit (`bddd92e435d66cef92478618b35c3812dfc34328`)
  unchanged, because no commit since pre13 touched `monzero-gui/` or its
  pinned core submodule. Its embedded core version therefore does not match
  the pre14 CLI/daemon packages' embedded version, even though no relevant
  core source differs between them.
- Packages and release metadata will remain unsigned until the offline release
  signing process is completed.
- A separately trusted operator has not reproduced and signed the binaries.
- Consensus, cryptography, and the broader implementation have not completed
  an independent audit.
- Native Windows CLI execution testing remains required for the Windows x64
  CLI archive produced for this candidate; it has not yet been run. No
  Windows GUI archive exists for this candidate, so GUI execution testing
  does not yet apply.
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
