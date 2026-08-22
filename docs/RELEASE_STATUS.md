# Monzero release status

Status: not ready for production release
Assessment date: 2026-08-22
Candidate line: Genesis prerelease

This file records evidence for the current release assessment. It complements
`RELEASE_CHECKLIST.md`; unchecked requirements remain release blockers even
when they are outside the source repository.

## Verified in the current working tree

- The complete CMake build succeeds with the configured local toolchain.
- All 1,297 unit tests pass in one run with workspace-backed temporary storage,
  including protected Monzero consensus vectors and
  the inactive asset, recipient-restoration, and persistent-state tests.
- All 18 default RPC functional tests pass in one clean run. This covers wallet
  creation/restoration, transfers, mining, txpool/ZMQ, multisig, cold signing,
  P2P propagation and reorganisation, RPC payment, URI handling, and restart-
  sensitive wallet operations. The harness now launches Monzero executables,
  uses Monzero network address fixtures, and applies XMZ precision and genesis
  expectations.
- A separate regtest-only HF17 scenario passes the complete live NFT lifecycle:
  wallet RPC issuance, confirmed discovery, confidential transfer, explicit
  burn, restoration from seed, and reorganisation rollback. The opt-in fixture
  does not modify any public-network hard-fork schedule.
- A dedicated asset-wire fuzz target directly exercises arbitrary payload
  decoding, successful encode/decode round trips, and activated native asset
  envelope parsing. It builds and completes local smoke inputs; a sustained
  sanitizer-backed fuzz campaign is still required for the release gate.
- A disposable stagenet software wallet successfully creates and re-opens both
  fungible-token and NFT issuance artifacts through `monzero-wallet-cli`.
  Inspection rejects a tampered declared asset ID, and creation rejects an NFT
  without its required metadata hash. These artifacts remain offline-only.
- The inactive v2 asset wire constructor now creates a signed fixed-supply
  issuance whose output is both commitment-conserving and recipient-decodable.
  It can attach the envelope to a native transaction prefix before native
  signing while preserving the non-circular carrier commitment. Obsolete v1
  payloads are rejected instead of being reinterpreted.
- The software-wallet transaction path can now attach a fungible or NFT
  issuance after native inputs, outputs, and public keys are finalized but
  before RingCT signs the prefix. `asset_issue` exposes this as a confirmation-
  gated CLI workflow and reparses the completed envelope before returning it.
  It fails closed while HF17 is inactive and on light, watch-only, background,
  multisig, hardware, and cross-network wallets.
- Wallet payment URIs use `monzero:` consistently in the core and functional
  tests; inherited `monero:` payment links are no longer accepted as Monzero
  links.
- Update discovery and URL generation fail closed instead of contacting Monero
  infrastructure. A regression test protects this behavior.
- The CLI donation command cannot transfer funds and does not advertise an
  inherited Monero donation address.
- The root README identifies Monzero as an independent, experimental network,
  warns against cross-fork seed reuse, and describes the inactive status of
  hard-fork version 17 assets.
- Website and explorer JavaScript and PHP pass syntax checks. Local homepage
  and explorer smoke tests pass, and the node-status API returns a successful
  response from the configured public node.
- The explorer includes asset registry and detail routes backed by the bounded
  asset RPCs, exact fixed-supply formatting, confidential-output summaries,
  inactive-network warnings, and distinct issuer, collection-controller, and
  external-metadata trust labels. It degrades cleanly while the public node is
  still running a pre-asset RPC build.
- Full and view wallets now discover confirmed owned asset outputs across
  derived subaddresses by decoding recipient data and verifying its
  commitment. The versioned encrypted cache persists output IDs, openings,
  heights, and subaddress indices; rescans deduplicate them, pool-only outputs
  are excluded, and reorg/cache reset paths remove stale records.
- Issuance seeds a complete 16-member same-asset anonymity set, preventing a
  singleton NFT from becoming unspendable under the fixed-ring ownership
  rules. A verified single-input primitive now constructs confidential asset
  transfers and explicit burns, pads the successor anonymity pool, proves
  amount/mask conservation, and emits a stable-key-image CLSAG ownership proof.
- The full software wallet can construct activation-gated single-input asset
  transfers and irreversible burns after authenticating the real ring member.
  `asset_transfer`, `asset_burn`, and `asset_list` expose submission and raw
  confirmed-balance workflows in the CLI; spend-restoration material is stored
  in the versioned encrypted wallet cache. Multi-input asset coin selection
  remains unfinished.
- A fresh software wallet reconstructed from the same account keys rediscovers
  the identical asset opening and ownership key image from confirmed chain
  data. The restoration test spends that output into confidential change with
  an explicit burn, then verifies reorg rollback removes the detached change
  and restores the original output to unspent. The dedicated activated-daemon
  scenario additionally proves the RPC, relay, mining, seed-restoration, and
  competing-tip rollback path.
- Wallet RPC applications can now create fungible tokens, NFTs, collections,
  and editions, enumerate confirmed holdings, and construct transfers or burns
  through `create_asset`, `get_assets`, and `transfer_asset`. Mutating calls
  reject restricted mode, integrated destinations, unsupported wallet modes,
  and inactive HF17; non-relay raw transaction export is supported. The live
  wallet functional test covers holdings and the inactive activation gate.
- Website copies of the Genesis pre2 Linux and Windows archives are byte-for-
  byte identical to `dist/`; their outer SHA-256 files verify and all website
  download links resolve locally.
- Linux release, packaged launcher, and utility shell scripts pass `bash -n`.
- A native Linux GUI build succeeds against pinned core commit `488946b35`,
  its bundled daemon links successfully,
  and the headless QML suite exits successfully without QML type/reference
  errors. The startup banner reports `0.18.5.1-release` and logs under
  `.monzero`. Upstream update and development-submodule modes fail closed.
  Desktop metadata is renamed and validated, payment dispatch uses only the
  `monzero:` scheme, and the unsafe inherited Windows installer is removed.
- Two development Linux packages built from the same binaries are byte-for-
  byte identical and pass the normal package verifier. Strict verification
  correctly rejects them because they are dirty, dynamic, unstripped, and not
  independently reproducible.

Live DNSSEC validity is an integration check because it depends on the build
host exposing signatures and a usable trust anchor. Run the unit suite with
`MONZERO_TEST_LIVE_DNSSEC=1` on the release validation host.

## Known package limitations

Genesis pre2 is a private prerelease, not a production candidate. Its Linux
archive predates `BUILD-MANIFEST.txt`, so the current package verifier rejects
it. The existing developer binaries are not established as static, stripped,
or independently reproducible, and the archives do not have a Monzero release
signature. A new package version must be produced rather than relabelling
pre2.

## Repository work still required

- Audit remaining translations and secondary build utilities for user-facing
  inherited branding while preserving protocol identifiers and upstream
  technical attribution.
- Complete parser fuzzing and reproduce the passing core, GUI, functional, and
  website/explorer tests in CI and on clean supported systems.
- Add the asset creation/inspection workflow to the desktop GUI. The CLI can export and
  validate canonical signed fungible, NFT, collection, and edition artifacts,
  and its direct issuance command becomes usable only after HF17 activation.
- Complete multi-input asset coin selection, authenticated metadata retrieval,
  and richer ownership workflows for fungible tokens, NFTs, collections, and
  editions. Direct fixed-supply creation, confirmed owned-output discovery,
  single-input spending, burns, cache round trips, seed restoration, and reorg
  handling are wired and covered, but the broader asset wallet is not yet
  complete.
- Finalize supported-platform, migration, rollback, upgrade, and known-
  limitation documentation for the chosen release candidate.
- Produce a strict-verifier-compatible Linux candidate and an equivalent
  verified Windows candidate from pinned build environments.

## External evidence required before production release

- Release version/codename, supported platforms, and final source commit.
- A working private security-reporting contact and published disclosure policy.
- An offline release-signing key with a publicly verified fingerprint.
- At least one independent reviewer and a second reproducible-build operator.
- Three independently administered seed nodes across at least two providers
  and regions, followed by empty-directory synchronization and failover tests.
- Public bootstrap height/allocation disclosure and team-controlled-address or
  equivalent accountability disclosure.
- Clean-system Windows and Linux package tests and post-deployment monitoring.
- Independent consensus/implementation review. Asset activation additionally
  requires the cryptographic review, isolated network, public testnet, audit,
  and coordinated hard-fork gates in `MONZERO_ASSETS_V1_SPEC.md`.

None of the evidence in this document authorizes asset activation or a
production release.
