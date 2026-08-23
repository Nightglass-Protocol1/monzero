# Monzero Genesis pre7 release notes

Genesis pre7 is an experimental, unsigned, and unaudited command-line
prerelease. It is not a production release. These notes describe the exact
artifacts published at `https://monzero.org` and bound by
`website/releases/genesis-pre7.json`.

## Release identity

- Codename: Genesis pre7
- Source commit: `38914bf1347781dc6e0ead4a786e3607cc8ebeac`
- Native currency: XMZ
- Public asset hard fork: inactive; no public-network asset activation is
  scheduled

## Packaged and tested platforms

| Package | Compatibility floor | Exact archive testing |
| --- | --- | --- |
| Linux x86-64 CLI | glibc 2.29 or newer | Digest-pinned Ubuntu 24.04 launch test and native wallet create, restore, and refresh lifecycle passed |
| Windows x64 CLI | Native Windows 11 build 26200 | Node launch, empty-directory synchronization, one-thread mining start/stop, clean shutdown, and wallet create, restore, and refresh lifecycle passed |

The archives contain `monzerod`, the command-line wallet, and wallet RPC. The
Linux archive also contains shell launchers and systemd examples; the Windows
archive contains batch launchers. The graphical wallet is not included.

macOS, Linux ARM, Windows ARM, mobile platforms, and 32-bit systems are not
packaged or supported by this candidate. Other glibc-based Linux distributions
meeting the symbol floor may work but have not been qualified by this release.

## User-visible changes

- Replaced inherited network identity, default ports, address prefixes, URI
  scheme, paths, and user-facing service links with Monzero equivalents.
- Added deterministic Linux, Windows, and recursively complete source packages
  with inner and outer SHA-256 manifests.
- Added safe launch and mining controls for Linux and Windows. Genesis pre7
  supersedes pre6 because the pre6 Windows mining launcher had an invalid
  PowerShell pipeline escape.
- Added stale-tip and peer-count-aware public node status rather than treating
  an RPC response alone as network readiness.
- Added native wallet creation and deterministic seed-restoration coverage on
  Linux and Windows.
- Added an experimental local-draft Studio for token, NFT, collection, and swap
  design. Studio drafts are unsigned JSON and cannot be submitted to the chain.
- Implemented asset consensus and wallet groundwork behind hard-fork version
  17. It remains inactive on every public Monzero network.

## Known limitations and safety notices

- Packages and release metadata are unsigned. There is no production Monzero
  release-signing identity yet.
- Byte-for-byte repeatability has been shown locally, but a separately trusted
  operator has not reproduced and signed the binaries.
- Consensus, cryptographic asset code, and the broader implementation have not
  completed independent audit.
- The public network has limited independent infrastructure and hash power. A
  synchronized daemon may still report a stale tip when no miner finds a block.
- Windows SmartScreen may warn because the executables are not code-signed.
- Hardware-wallet, multisig, view-only, offline-signing, and funded transaction
  lifecycles do not yet have complete clean-system release evidence across both
  packaged platforms.
- Studio does not connect to a wallet, hold keys, sign transactions, create
  live assets, or place exchange orders.
- Direct asset issuance remains activation-gated and must not be enabled on a
  public network without the review, testnet, audit, and coordinated hard-fork
  gates in `MONZERO_ASSETS_V1_SPEC.md`.
- Never reuse a Monero or other CryptoNote-derived seed, keys, wallet file, or
  data directory with Monzero.

## Upgrade and rollback

Read `UPGRADE.md` before replacing binaries. Stop wallets, miners, and the
daemon cleanly; back up wallet files, seeds, and the node data directory; verify
the archive and its internal manifest; and extract into a new directory. Keep
the previous verified binaries and matching data backup for rollback.

## Verification and reporting

Compare downloads against the SHA-256 values in
`website/releases/genesis-pre7.json` and the adjacent `.sha256` files. Current
test evidence and unresolved gates are recorded in `RELEASE_STATUS.md` and
`RELEASE_CHECKLIST.md`. Report security issues privately to
`security@monzero.org`; never include wallet seeds or private keys.
