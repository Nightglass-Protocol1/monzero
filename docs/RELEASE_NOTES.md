# Monzero Genesis pre9 release notes

Genesis pre9 is an experimental, unsigned, unaudited, and deliberately
untested prerelease. It is not a production release. The exact source commit and
artifact digests are recorded in each package manifest and the matching
machine-readable release metadata published at `https://monzero.org`.

## Packaged platforms

| Package | Compatibility scope |
| --- | --- |
| Linux x86-64 CLI | glibc 2.31 or newer |
| Windows x64 CLI | 64-bit Windows command-line environment |
| Windows x64 GUI | 64-bit Windows graphical environment |
| Complete source | Pinned repository commit and recursive submodule contents |

The binary archives contain `monzerod`, the command-line wallet, and wallet
RPC. The Linux archive includes shell launchers and systemd examples; the
Windows CLI archive includes batch launchers. The GUI is distributed in a
separate archive with matching command-line tools.
macOS, Linux ARM, Windows ARM, mobile platforms, and 32-bit systems are not
qualified by this candidate.

## Changes since Genesis pre8

- Defined cryptographic carry normalization without signed left-shift behavior.
- Corrected wallet enum-varint conversion while retaining its wire encoding.
- Added modern view-tagged mined-reward ownership coverage to the source tree.
- New GUI wallets default to `Monzero/wallets`; the wallet picker also scans
  the legacy `Monero/wallets` directory without moving or deleting files.
- Updated the whitepaper and release evidence for these changes.

## Verification performed

At the publisher's direction, no test suite, package verifier, platform smoke
test, or native wallet lifecycle test was run to qualify the exact Genesis
pre9 artifacts. Successful compilation and checksum generation are packaging
steps, not test evidence. Earlier pre8 results do not qualify pre9.

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
