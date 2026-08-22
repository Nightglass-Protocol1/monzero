# Monzero release status

Status: not ready for production release
Assessment date: 2026-08-22
Candidate line: Genesis prerelease

This file records evidence for the current release assessment. It complements
`RELEASE_CHECKLIST.md`; unchecked requirements remain release blockers even
when they are outside the source repository.

## Verified in the current working tree

- The complete CMake build succeeds with the configured local toolchain.
- All 1,298 unit tests pass in one run with workspace-backed temporary storage,
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
  burn, restoration from seed, and reorganisation rollback. It also splits a
  fungible holding into two one-unit outputs and spends both in one burn,
  proving activated multi-input wallet selection. The opt-in fixture does not
  modify any public-network hard-fork schedule.
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
  rules. A verified multi-input primitive now constructs confidential asset
  transfers and explicit burns, pads the successor anonymity pool, proves
  amount/mask conservation, and emits one stable-key-image CLSAG ownership
  proof per selected input.
- The full software wallet can construct activation-gated multi-input asset
  transfers and irreversible burns after authenticating every real ring member.
  Selection is deterministic, scoped to the requested account/subaddresses,
  and bounded by the existing 64-input consensus limit.
  `asset_transfer`, `asset_burn`, and `asset_list` expose submission and raw
  confirmed-balance workflows in the CLI; spend-restoration material is stored
  in the versioned encrypted wallet cache.
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
- A native Linux GUI build succeeds against pinned core commit `8afa04b46`,
  its bundled daemon links successfully,
  and the headless QML suite exits successfully without QML type/reference
  errors. The startup banner reports `0.18.5.1-release` and logs under
  `.monzero`. Upstream update and development-submodule modes fail closed.
  Desktop metadata is renamed and validated, payment dispatch uses only the
  `monzero:` scheme, and the unsafe inherited Windows installer is removed.
- Two development Linux packages built from the same binaries are byte-for-
  byte identical and pass the normal package verifier. Strict verification
  correctly rejects them when their manifests are dirty or reproducibility is
  not independently verified.
- The packager includes README, release status, checklist, and explicit
  migration/rollback guidance. It refuses mixed daemon/wallet versions and the
  verifier binds their identical reported version into the build manifest,
  screens unsafe archive paths before extraction, and requires the release
  documents. A deliberately mixed historical binary set is rejected.
  Packaged ELF binaries are deterministically stripped; strict verification
  permits only minimal glibc-family dynamic dependencies and rejects the
  broader host-library set produced outside the pinned depends environment.
- A clean static Release configuration at source commit `be2fb8313` produced
  version-consistent daemon, CLI, and wallet RPC binaries. Two Genesis pre3
  archives created from that binary set are byte-for-byte identical with
  SHA-256 `c0ee269628b4d05729bdf3a4db4eb7e11ae74159858a0fca74cfbdb6a9b65aa0`;
  normal verification passes and the manifest records a clean tree, stripped
  binaries, inactive public asset consensus, and unverified reproducibility.
  Strict verification rejects the host build at `libgssapi_krb5.so.2`, proving
  that a pinned depends build and independent reproduction are still required.
  A crafted `../` archive entry is rejected before extraction.
- The pinned Linux depends environment now builds completely on GCC 15 and
  glibc 2.34+ without host-package leakage. It bootstraps gperf, pins legacy C
  sources to C17 where required, carries the established Boost thread fix, and
  disables ZeroMQ transports that are absent from the pinned dependency set.
  A clean build at source commit `4c5cd3353` produced version-consistent daemon,
  CLI, and wallet RPC binaries whose only ELF dependencies are `libm.so.6`,
  `libc.so.6`, and `ld-linux-x86-64.so.2`. Two Genesis pre4 archives are
  byte-for-byte identical with SHA-256
  `0bbc3571db4530076ab863d1f6f6ca291322dd6fe1bda977ecf4453be229a433`.
  Normal verification passes. Strict verification checks all three binaries,
  accepts their stripped/minimal runtime surface, and stops only because the
  required independent binary reproduction remains honestly `unverified`.
- The pinned Windows dependency environment now builds the daemon, CLI wallet,
  and wallet RPC with mandatory Trezor support using the same source baseline
  as Linux. The PE32+ executables import only allowlisted Windows system DLLs,
  carry one identical source revision, and are deterministically stripped.
  Two Genesis pre5 Windows archives produced from the same binaries are byte-
  for-byte identical with SHA-256
  `b37f991b6d59b2a1ae0ea85da06146b07051fc81593e51fbfb571cf37a18af23`.
  Normal verification passes; strict verification stops at the required
  independent reproduction attestation. Execution testing on a clean Windows
  system and the separately pinned GUI package remain outstanding.
- Linux was rebuilt at the same pre5 source baseline. Two packages are byte-
  for-byte identical with SHA-256
  `03b90084297a1fdbd92adca5b395af765f83da327c638f6e43a830d0849ffbcf`.
  Normal verification passes, the three binaries retain only the permitted
  glibc-family dependencies, and strict verification stops only at independent
  reproduction. The website candidate links now identify both packages as
  unsigned, unaudited prereleases rather than production releases.

Live DNSSEC validity is an integration check because it depends on the build
host exposing signatures and a usable trust anchor. Run the unit suite with
`MONZERO_TEST_LIVE_DNSSEC=1` on the release validation host.

## Known package limitations

Genesis pre2 is a private prerelease, not a production candidate. Its Linux
archive predates `BUILD-MANIFEST.txt`, so the current package verifier rejects
it. Genesis pre3 is a clean, deterministic local packaging candidate, but its
host-built binaries have non-permitted runtime dependencies and have not been
independently reproduced or signed. Genesis pre4 replaces that host-built
candidate with pinned-dependency binaries and passes every local strict check,
but still lacks independent reproduction and signing. Genesis pre5 aligns the
pinned Linux and Windows command-line packages at source commit `10ec39009`;
both pass normal verification and deterministic same-machine packaging, but
neither has been independently reproduced, signed, or tested on a clean
Windows system. None of these archives is a production release or may be
promoted without satisfying the remaining strict and external release gates.

## Repository work still required

- Audit remaining translations and secondary build utilities for user-facing
  inherited branding while preserving protocol identifiers and upstream
  technical attribution.
- Complete parser fuzzing and reproduce the passing core, GUI, functional, and
  website/explorer tests in CI and on clean supported systems.
- Add the asset creation/inspection workflow to the desktop GUI. The CLI can export and
  validate canonical signed fungible, NFT, collection, and edition artifacts,
  and its direct issuance command becomes usable only after HF17 activation.
- Complete authenticated metadata retrieval and richer ownership workflows for
  fungible tokens, NFTs, collections, and
  editions. Direct fixed-supply creation, confirmed owned-output discovery,
  multi-input spending, burns, cache round trips, seed restoration, and reorg
  handling are wired and covered, but the broader asset wallet is not yet
  complete.
- Finalize supported-platform, migration, rollback, upgrade, and known-
  limitation documentation for the chosen release candidate.
- Independently reproduce the strict-verifier-compatible Linux candidate and
  produce an equivalent verified Windows candidate from a pinned environment.

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
