# Monzero Genesis pre8 release notes

Genesis pre8 is an experimental, unsigned, and unaudited command-line
prerelease. It is not a production release. The exact source commit and
artifact digests are recorded in each package manifest and the matching
machine-readable release metadata published at `https://monzero.org`.

## Packaged platforms

| Package | Compatibility scope |
| --- | --- |
| Linux x86-64 CLI | glibc 2.29 or newer |
| Windows x64 CLI | 64-bit Windows command-line environment |
| Complete source | Pinned repository commit and recursive submodule contents |

The binary archives contain `monzerod`, the command-line wallet, and wallet
RPC. The Linux archive includes shell launchers and systemd examples; the
Windows archive includes batch launchers. A graphical wallet is not included.
macOS, Linux ARM, Windows ARM, mobile platforms, and 32-bit systems are not
qualified by this candidate.

## Changes since Genesis pre7

- Added the protocol whitepaper to the repository, website, and binary
  packages, with explicit consensus parameters, privacy assumptions, monetary
  policy, inactive asset boundary, and security limitations.
- Corrected packaged node and wallet launchers to resolve sibling binaries,
  use Monzero's mainnet ports and data directory, avoid personal wallet paths,
  and require an explicit valid reward address before mining.
- Removed a fixed priority-node IP and use the maintained node hostname.
- Corrected the fallback transaction-fee reward bound for Monzero's 120-second
  initial emission rate.
- Hardened release verification by rejecting unsafe tar and ZIP members,
  links, special files, duplicate or noncanonical paths, excessive entry
  counts, and oversized archives before extraction.
- Made Linux and Windows packaging fail closed when binary provenance does not
  match the source commit.
- Adapted generated consensus fixtures to Monzero's finite supply, 11-decimal
  precision, 120-second emission, and resulting coinbase denominations. This
  restores meaningful overflow, RingCT, Bulletproof, Bulletproof+, and CLSAG
  coverage instead of relying on inherited Monero monetary literals.
- Moved test databases from the shared system temporary directory into the
  build tree to avoid false LMDB failures caused by unrelated `/tmp` pressure.
- Completed remaining release-facing daemon, wallet, RPC, service, address,
  and ticker branding corrections.

## Verification performed

The release source is gated by unit, adversarial consensus, generated core,
pruning-race, and three-node propagation/restart/reorganization/transfer tests.
Each published archive must also pass its strict outer checksum, safe archive
inspection, inner manifest, source-commit, version, and platform checks.
Platform smoke-test results belong in the published release metadata and
`RELEASE_STATUS.md`; they are evidence for the exact named archives only.

## Known limitations and safety notices

- Packages and release metadata are unsigned; there is no production Monzero
  release-signing identity yet.
- A separately trusted operator has not reproduced and signed the binaries.
- Consensus, cryptography, and the broader implementation have not completed
  independent audit.
- The public network has limited independent infrastructure and hash power.
- Windows SmartScreen may warn because the executables are not code-signed.
- Hardware-wallet, multisig, view-only, offline-signing, GUI, and funded
  transaction lifecycles do not have complete clean-system release evidence.
- The asset prototype remains inactive on every public network. Studio drafts
  are unsigned JSON and cannot be submitted to consensus.
- Never reuse a Monero or other CryptoNote-derived seed, keys, wallet file, or
  data directory with Monzero.

## Upgrade and rollback

Read `UPGRADE.md` before replacing binaries. Stop wallets, miners, and the
daemon cleanly; back up wallet files, seeds, node configuration, and the data
directory; verify the archive and its internal manifest; and extract into a
new directory. Keep the previous verified binaries and matching data backup
until the upgraded node has synchronized and remained healthy.

## Verification and reporting

Compare downloads with the SHA-256 values in the published JSON metadata and
adjacent `.sha256` files. Review `BUILD-MANIFEST.txt` or
`SOURCE-MANIFEST.txt` inside the archive before use. Current evidence and
unresolved gates are recorded in `RELEASE_STATUS.md` and
`RELEASE_CHECKLIST.md`. Report security issues privately to
`security@monzero.org`; never include wallet seeds or private keys.
