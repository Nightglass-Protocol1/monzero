# Monzero Genesis pre13 release notes

Release label: genesis-pre13

Genesis pre13 is the next experimental prerelease candidate. It is not a
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

## Changes since Genesis pre12

- Removed undefined behavior from circular `Blockchain` and transaction-pool
  initialization. Pool-to-chain binding is now explicit and checked, and the
  affected utilities and tests preserve valid destruction order.
- Prevented a command-line wallet crash when wallet creation is cancelled
  before a wallet object is returned.
- Added a package gate that rejects missing or stale release notes when their
  declared release label does not match the archive.
- Added pre-extraction archive safety checks to the Linux package and wallet
  smoke tests, including regression coverage for correctly hashed unsafe archives.
- Disabled host ICU auto-detection in the depends Boost build, preventing
  undeclared build-machine libraries from leaking into release dependencies.
- Fixed a peer synchronization stall after competing forks by keeping inbound
  block-serving activity separate from the timer for our own outstanding
  requests. The regression test and two three-node reorganisation, transfer,
  and wallet-restoration simulations pass with the original sync deadline.
- Hardened CI to run release archive, notes, signing-subkey, and branding
  regressions; use Monzero's deterministic source packager and verifier; and
  collect correctly named Monzero cross-build artifacts.
- No mainnet consensus identity, genesis block, address prefix, port, monetary
  policy, or public hard-fork schedule changed. Monzero Assets remain inactive
  on every public network.

## Source-tree verification performed

- All 1,304 unit tests pass on the local Linux build.
- The core-test, block-weight, wallet CLI, and seven affected blockchain
  utility targets build successfully.
- The focused transaction-pool binding, long-term block-weight, fee-scaling,
  and output-distribution suite passes all 20 tests.
- The branding, hostile-archive, signing-subkey, and release-notes binding
  regression gates pass locally.
- All 16 adversarial core tests pass, including transaction-pool and
  double-spend scenarios involving alternative chains.
- A local simulation of the CI source-package path produced a recursively
  complete archive that passed the source-package verifier.

These are source-tree results. They do not qualify a particular binary archive
without matching artifact evidence, and they are not an independent security review.

## Known limitations and safety notices

- Each pre13 artifact must complete the full clean qualification cycle before
  publication; consult its exact-hash evidence rather than assuming these
  source-tree test results apply to it.
- Packages and release metadata will remain unsigned until the offline release
  signing process is completed.
- A separately trusted operator has not reproduced and signed the binaries.
- Consensus, cryptography, and the broader implementation have not completed
  an independent audit.
- Native Windows CLI and GUI execution testing remains required for the exact
  candidate archives.
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
