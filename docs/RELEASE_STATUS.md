# Monzero release status

Status: not ready for production release
Assessment date: 2026-08-23
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
  for-byte identical; the outer digest is published in the adjacent checksum
  file and on the website rather than embedded recursively in the archive.
  Normal verification passes; strict verification stops at the required
  independent reproduction attestation. Execution testing on a clean Windows
  system and the separately pinned GUI package remain outstanding.
- Linux was rebuilt at the same pre5 source baseline. Two packages are byte-
  for-byte identical, with the outer digest published separately.
  Normal verification passes, the three binaries retain only the permitted
  glibc-family dependencies, and strict verification stops only at independent
  reproduction. The website candidate links now identify both packages as
  unsigned, unaudited prereleases rather than production releases.
- Genesis pre5 is deployed on `https://monzero.org` as an explicitly unsigned,
  unaudited prerelease. A post-deployment HTTPS download of each complete
  archive matched its published SHA-256 digest: Linux
  `99e4be1dda90dad94ca624fb19f734f8a5faf9ad6c8cbcb3391da7269c507675`
  and Windows
  `7870ed552f4c1d4b92260d8cfbd25260b1c983edc36c5136965e555162cdcc42`.
  The explorer remained reachable and the node-info endpoint returned status
  `OK` after deployment, but the node reported `synchronized: false` at height
  1023. The prior homepage is retained server-side in the timestamped rollback
  directory `Monzero-backup-20260822T194244Z-pre5`.
- A subsequent public verification downloaded both complete archives over
  HTTPS and reproduced the same published digests. HTTP metadata reports the
  expected `application/gzip` and `application/zip` MIME types and exact sizes
  of 28,530,347 and 25,739,082 bytes. Both normal package verifiers pass;
  strict verification rejects both packages solely because independent binary
  reproduction remains `unverified`. The public explorer RPC still responds,
  but its latest block is height 1022 with timestamp 1786833652 and the node
  reports zero peers and `synchronized: false`; public-network freshness and
  independent-node synchronization therefore remain unproven.
- The prerelease homepage now publishes the exact packaged source commit and
  links `/releases/genesis-pre5.json`. The live JSON is byte-for-byte identical
  to the repository copy and binds both artifact names, sizes, SHA-256 hashes,
  signing state, audit state, and reproducibility state. The prior homepage is
  retained server-side as `index.html.before-release-metadata-20260822`, in
  addition to the full pre5 rollback directory. Post-deployment checks confirm
  that the explorer still returns valid JSON and both artifact endpoints retain
  their expected MIME types and byte sizes.
- The homepage node indicator now distinguishes RPC reachability from network
  readiness: `status: OK` with `synchronized: false` is displayed as “Node
  unsynchronized” with the offline warning state, rather than “Node online”.
  The updated JavaScript and cache-busted homepage are deployed and match the
  committed files byte-for-byte. Server-side pre-change copies are retained as
  `index.html.before-node-state-20260822` and
  `app.js.before-node-state-20260822`.
- The public VPS was rebuilt from a fresh Ubuntu 26.04 image after its former
  SSH host key material was exposed. Its new ED25519 host key was verified
  through the provider console before deployment. Password and direct-root SSH
  authentication are disabled, a dedicated unprivileged administrator key is
  in use, and the host firewall permits only SSH plus Monzero P2P and restricted
  RPC ports. The systemd service runs as the unprivileged `monzero` account.
  The deployed daemon came from the published Genesis pre5 Linux archive; the
  archive and every packaged file passed SHA-256 verification on the VPS, and
  the daemon reports source revision `ab143bbaf`.
- The recovered public node and an operator node both report height 1023, top
  block hash `995a7d95b7c3ca12acacd6fd6dbadd00c0920d917d3bf67dd0f1464d021c530f`,
  `synchronized: true`, and one P2P connection between them. Public P2P and
  restricted RPC are reachable through `node.monzero.org`. The production
  network-readiness gate still fails: it requires at least two peers and a tip
  no more than 900 seconds old, while the restored network has one peer and its
  latest block is approximately seven days old. This recovery establishes
  service availability, not production network readiness.
- The final Genesis pre5 Windows archive was extracted read-only in a disposable
  Ubuntu 20.04 container with Wine 5. The daemon, CLI wallet, and wallet RPC
  executables each loaded, reported the manifest-bound `ab143bbaf` version, and
  exited successfully for `--version`. A full daemon smoke under Wine could not
  initialize LMDB on either the container overlay filesystem or tmpfs, returning
  an I/O error before RPC startup. This is useful PE loader coverage but does
  not satisfy the clean Windows system test requirement.
- The website node-status API now obtains the latest block header and applies
  the same 900-second tip-age and 300-second future-skew thresholds as the
  release-readiness gate. Local PHP and JavaScript syntax checks pass, and a
  live proxy smoke reports the current synchronized daemon as
  `network_ready: false` and `tip_fresh: false`. The homepage and explorer are
  deployed with the cache-busted “Network tip stale” state instead of implying
  that a synchronized process necessarily means a ready network.
- The VPS now separates its RPC surfaces: restricted public RPC remains on
  `0.0.0.0:6175`, while unrestricted operator RPC is bound only to
  `127.0.0.1:6177`. The on-host readiness gate confirms the local endpoint is
  unrestricted and the public endpoint is restricted. A hardened systemd
  timer runs that gate every five minutes and records failures in the journal;
  its first deployed run reported exactly the known one-peer and stale-tip
  failures. Port 6177 is not permitted through the host firewall.
- Independent reproduction now has a fail-closed evidence path. The package
  comparator verifies all four reference/reproduced Linux and Windows inputs,
  requires byte-for-byte equality and one clean source commit, and emits a
  canonical attestation for the second builder to sign. Production publication
  additionally requires that attestation to bind the exact metadata artifacts,
  verifies it against an explicitly trusted reproducer fingerprint, and rejects
  reuse of the release-signing key. Positive matching, valid mismatch,
  missing-identity, overwrite-refusal, and throwaway two-key integration tests
  pass. The integration test reaches and correctly stops at pre5's honest
  `binary_build_reproducibility=unverified` manifest; same-host candidate pairs
  remain determinism evidence only, not independent reproduction.
- A deterministic Genesis pre5 source package now supplies the otherwise
  unavailable public commit plus all six pinned recursive submodule revisions.
  Two packaging runs are byte-for-byte identical at SHA-256
  `a958217d92418d35f59fedb2734dbb1162562876ef0896f74a7d42e94789beca`;
  the source verifier passes over 4,703 archive entries and the release
  publication verifier binds its exact 21,182,274-byte size, digest, and source
  commit alongside the two binary artifacts. The source package, checksum,
  download surface, and byte-identical pre5 JSON are deployed publicly.
- The homepage no longer hard-codes “Public node online” in its hero
  banner. It uses a static experimental-prerelease label and delegates live
  readiness claims exclusively to the stale-tip-aware status panel.
- The 2026-08-23 webspace deployment was performed from a hash-verified staging
  directory, with HTML entry points replaced last. Public HTTPS checks confirm
  the cache-busted homepage and explorer scripts, truthful stale-tip API state,
  exact metadata equality, and the expected MIME types and byte sizes for all
  three downloads. Complete public downloads reproduce the published Linux,
  Windows, and source SHA-256 hashes, and the downloaded source package passes
  full verification. The six replaced live files are retained at
  `/home/www/Monzero-backup-20260823T094426Z-source-status` for rollback.
- Webspace deployment access now uses a dedicated ED25519 key with fingerprint
  `SHA256:zBU44whbE/eHScuAlbue/zcFufKRL5kTmqGrT/IMeFQ`. It was appended without
  replacing the existing operator key, and fresh key-only SSH and SFTP sessions
  both succeed. The password disclosed during deployment is no longer required
  and must be rotated.
- A locally mined block advanced the public network to height 1,024, removing
  the stale-tip failure while preserving one-thread battery-aware background
  mining. The local daemon and public node reported the same top hash,
  `c621d3172dbbe1e941674a28df47f6ebb10b05dfe6381774c3cee3a3533e894e`.
  The remaining live readiness failure is the single connected peer. The public
  API, homepage, and explorer now apply the same minimum of two peers as the
  server release gate: at height 1,024 the verified HTTPS response reported
  `tip_fresh=true`, `peer_ready=false`, and `network_ready=false`, and both UIs
  label the condition “Network under-peered”. The five replaced files can be
  rolled back from
  `/home/www/Monzero-backup-20260823T095331Z-peer-readiness`.
- Clean-system testing of the exact published pre5 Linux archive found that all
  three executables require `GLIBC_2.42`; they fail at process loading on the
  digest-pinned Ubuntu 24.04 image before `--version` can run. The strict Linux
  verifier now enforces a default maximum requirement of `GLIBC_2.35`, and a
  repeatable test runs the final archive in a network-isolated, read-only
  container. Both gates correctly reject pre5. The public homepage and release
  JSON disclose the `GLIBC 2.42+` limitation and Ubuntu 24.04 incompatibility;
  the prior files are retained at
  `/home/www/Monzero-backup-20260823T100042Z-linux-compatibility`. The rebuild
  audit also found that the Linux depends set relied on an undeclared host zlib
  development package. zlib 1.3.2 is now pinned by its official SHA-256 in the
  depends graph. The first clean relink then exposed the same undeclared-host
  dependency for zstd; zstd 1.5.7 is now pinned as well. A new Linux candidate
  must be built and pass both gates before replacing pre5.
- The Genesis pre6 candidate closes that Linux portability regression. Two
  clean pinned-dependency Linux builds produced byte-identical daemon, wallet
  CLI, and wallet RPC executables. Their packages are byte-identical, require
  no non-system shared libraries, require at most `GLIBC_2.29`, pass strict
  package verification, and start successfully from the exact final archive
  in the digest-pinned, network-isolated, read-only Ubuntu 24.04 smoke-test
  container.
- Two clean MinGW builds of the matching Genesis pre6 commit produced
  byte-identical daemon, wallet CLI, and wallet RPC executables and
  byte-identical Windows ZIP archives. The final ZIP passes strict PE format,
  embedded-version, manifest, checksum, and imported-DLL verification. Trezor
  support and its pinned HIDAPI and libusb dependencies were enabled during
  configuration. Native execution on a clean Windows host, independent
  reproduction by a separately trusted person, code signing, and an external
  security audit remain outstanding; pre6 therefore remains an explicitly
  unsigned and unaudited prerelease.
- Genesis pre6 is published at `https://monzero.org` from source commit
  `d4cac36271387af2b6589208bf2be74e10e5a01f`. The public Linux, Windows,
  and recursively complete source archives have SHA-256 digests
  `77b7299a7532093eec94411a59f6663451566a6964feecb742a17029eaa0ebaa`,
  `9d6fb20055a1e1e89625f8565af13be6f9140275de943c5a41a886d8aea87405`,
  and `9ebdf1bf68357fc784d6c92370eff94bc9b104ed1e668ae0110de5fcedf48104`
  respectively. Full HTTPS downloads reproduce those hashes, the publication
  verifier accepts the downloaded metadata and artifacts, and the server
  returns the expected gzip and ZIP media types and exact byte sizes. The
  pre6 website rollback is retained at
  `/home/www/Monzero-backup-20260823T124259Z-pre6`.
- Genesis pre6 is deployed on the VPS from the exact published Linux archive.
  The archive hash and every internal package checksum were verified on-host
  before installation. The prior binary, configuration, systemd unit,
  operator-local RPC evidence, and a complete stopped-state chain database are
  retained at `/var/backups/monzero-pre6-20260823T141935Z`, together with
  tested rollback instructions. The deployed binary reports
  `0.18.5.1-d4cac3627`, reopened the existing chain, synchronized at height
  1,036, and remained enabled, active, correctly versioned, and synchronized
  after a second systemd restart. Operator-local RPC, restricted public RPC,
  and the website API agreed on top hash
  `0d6fea8274daa1b6a14c91211bdbeb3bf08c0417e75fe7a0c744099f92195cbf`.
  The deployment key uses key-only root SSH; password root SSH remains
  disabled. The production readiness gate still fails solely on the live
  network side because the public node has one peer rather than the required
  minimum of two.
- A second, isolated Genesis pre6 daemon was started locally from the published
  Linux build on alternate P2P, RPC, and ZMQ ports. It successfully handshook
  with the existing node, synchronized from genesis through all 1,025 blocks,
  reported version `0.18.5.1-d4cac3627`, and matched the canonical top hash
  `e4baa0aadf87c555f169ca9377b5a0e261a3963a88bfd8b6dd01d64dfe167f1c`.
  This supplies live-chain startup, handshake, import, and synchronization
  evidence for the exact pre6 code in addition to the offline clean-system
  smoke test. It does not satisfy the independent-public-peer gate because both
  local daemons share one public network origin.
- One-thread mining temporarily ran in active mode to resolve the stale-tip
  gate, found block 1,024, and propagated the new top hash to the existing
  local node, the isolated pre6 node, the VPS, and the website API. The miner
  was then restored to its prior battery-aware background mode. The website
  now reports `tip_fresh=true`; the exact pre6 readiness check fails solely
  because its single local peer is below the required minimum of two.
- A second public Genesis pre6 node was deployed from a fresh Ubuntu 26.04
  installation in the IONOS US region at `node2.monzero.org` (`67.217.247.219`).
  It runs as the unprivileged `monzero` user under the same hardened systemd
  unit as the European node, accepts key-only SSH administration, exposes only
  P2P port 6174, and keeps unrestricted RPC on loopback port 6177. Its daemon
  SHA-256 is
  `5b9646fa17a94650d8898783f255ef5d4c7ea28d96b50ffe134edcca1ca50156`,
  identical to the verified pre6 daemon deployed in Europe. Both nodes maintain
  priority connections to each other, and public DNS resolution plus inbound
  P2P reachability were verified through the new hostname. The repository's
  hardened five-minute readiness timer is enabled on both VPSs; its first US
  run completed successfully at height 1,040 with three peers and a 249-second
  tip age.
- After block 1,039 was mined with one temporary local CPU thread, the exact
  repository readiness gate passed independently against each VPS's
  operator-local RPC: both reported height 1,040, three P2P connections, and
  tip ages of 34 and 36 seconds. The local miner was immediately returned to
  its prior battery-aware background mode. The live website API then reported
  `network_ready=true`, `peer_ready=true`, `tip_fresh=true`, height 1,040, and
  three connections. This closes the two-public-peer operational gate; it does
  not satisfy the stronger production requirement for three independently
  administered seed nodes across at least two providers.
- The dedicated `security@monzero.org` mailbox was authenticated successfully
  over TLS against both the IONOS IMAP and SMTP services without sending a
  message. `SECURITY.md` and the website now publish the private reporting
  address, scope, prohibited secret material, acknowledgement targets, and
  coordinated-disclosure process. Email is explicitly identified as lacking
  end-to-end encryption until a dedicated security OpenPGP key is published.
  A TLS-authenticated self-delivery test succeeded; the received message was
  signed with IONOS DKIM selector `s1-ionos` for `monzero.org`, and its
  authentication results reported DKIM, SPF, and DMARC alignment passing. The
  domain's DMARC policy remains monitoring-only (`p=none`); enforcement must
  not be raised until normal mail flow is observed and the remaining
  IONOS-recommended DKIM selector is published.
- The production publication verifier now resolves a valid signing-subkey
  signature to its trusted primary OpenPGP fingerprint instead of incorrectly
  requiring the rotating subkey fingerprint as the release identity. A real
  disposable GnuPG integration test creates a certification-only Ed25519
  primary key plus a distinct Ed25519 signing subkey, signs a payload, proves
  the parser returns the primary fingerprint, and rejects missing or ambiguous
  `VALIDSIG` evidence. `RELEASE_SIGNING.md` documents the matching offline key
  ceremony, backups, revocation, multi-channel fingerprint publication,
  metadata signing, verification, rotation, and compromise response. No
  production key has been generated on this development machine.
- The webspace now redirects every plain-HTTP path and query to the same
  canonical `https://monzero.org` URL with a permanent redirect. A conservative
  one-day HSTS trial, same-origin Content Security Policy, restrictive browser
  permissions policy, frame denial, MIME sniffing protection, and referrer
  policy are active on pages, APIs, and release downloads. Post-deployment
  checks followed the redirect without a loop, retained the release archive's
  exact gzip type and size, loaded homepage/explorer assets, and received valid
  node-status JSON. The prior `.htaccess` is retained server-side as
  `.htaccess.before-https-20260823` for rollback.
- A checksum-pinned PowerShell harness completed the native Windows pre6
  command-line smoke test without weakening it into Wine or cross-build evidence. It
  verifies the exact public ZIP and every inner package hash, launches all
  three executables, creates a fresh offline daemon on random loopback ports,
  validates local RPC and mainnet identity, requests clean shutdown, and emits
  machine-readable host and result evidence. On 2026-08-23, the exact published
  archive passed on native 64-bit Windows 11 build 26200 under Windows
  PowerShell 5.1: all three executables reported source revision `d4cac3627`,
  the fresh offline mainnet daemon returned RPC status `OK` at height 1, and it
  shut down cleanly through RPC. The retained evidence SHA-256 is
  `8deaefa9e82be79e9dc5be7d77839708e6d47d384c29c16da169ff3bfc5de5e9`.
  This closes the exact archive's native command-line launch/RPC gate, but does
  not cover mining scripts, GUI behavior, wallet recovery, synchronization, or
  independent reproduction.
- Genesis pre7 fixes the packaged Windows mining launcher pipeline at source
  commit `38914bf1347781dc6e0ead4a786e3607cc8ebeac`. Two packages from each
  platform were byte-for-byte identical: Linux SHA-256
  `83476fd3e57a6953003874cac2409916ca1cfaa9677144418de6e535561b789e`,
  Windows SHA-256
  `049b4db553d52f592e0a0b05956fbafbec1e37c2672de50d0cde2bfbdffce284`,
  and complete source SHA-256
  `a60c776a70087a997e4c0501638f21fd193d53cb8d56f4704b122e1b1c9f62e6`.
  The Linux binaries were rebuilt in the pinned dependency environment on a
  controlled Ubuntu 20.04 userspace, require no glibc symbol newer than 2.29,
  expose only the minimal glibc-family runtime dependencies, pass normal
  package verification, and pass the digest-pinned isolated Ubuntu 24.04
  launch smoke test. Strict verification stops only at the required external
  independent-reproduction attestation.
- The exact pre7 Windows ZIP passed a native Windows 11 build 26200 network
  and launcher test under Windows PowerShell 5.1. All outer and inner hashes
  matched; all three executables reported revision `38914bf13`; a fresh data
  directory synchronized from height 1 to 1040 with canonical top hash
  `44029426d863f954745a73322dafdae3370299772e2990abd9721ea0b88067af`;
  the exact `start-mining.bat` and `stop-mining.bat` activated and stopped one
  RandomX thread; and the exact node launcher shut down cleanly through its
  console. The retained JSON evidence has SHA-256
  `c89c3dbcd41bc5632d3a5a96c24b5f38718d7e0dcd63e901caf93cb43796d6a1`.
  This remains operator evidence, not independent reproduction or audit.
- A second native Windows harness exercised the exact pre7 wallet RPC from the
  same published archive. It created a new deterministic software wallet,
  exported its recovery seed only in process memory, closed it, restored a
  second wallet from that seed, reproduced the identical Monzero address,
  refreshed 1,039 blocks through the restricted public node, stored both
  wallet states, and shut down the RPC cleanly. The successful harness removes
  its temporary keys and diagnostic directory; the retained seed-free evidence
  has SHA-256
  `96efaa1f1091d3a529ff67b0c805f4496b45663e469fdce90456d092245528fb`.
  This closes native creation and deterministic-restoration coverage for the
  command-line package, but does not establish funded transfer history, GUI,
  hardware-wallet, multisig, or offline-signing coverage on Windows. The live
  homepage and byte-identical release metadata now identify this additional
  test without changing the artifact digest or overstating production status;
  their preceding versions are retained at
  `/home/www/Monzero-backup-20260823T1830Z-wallet-evidence`.
- Genesis pre7 is deployed on `https://monzero.org` as an explicitly unsigned,
  unaudited prerelease. The live metadata names source commit
  `38914bf1347781dc6e0ead4a786e3607cc8ebeac`, and complete HTTPS downloads of
  the Linux, Windows, and source archives reproduce the published SHA-256
  digests and expected byte sizes. The public Windows network-smoke harness is
  byte-identical to the tested script. HTTP security headers, download MIME
  types, the homepage, explorer, and both POST-only status APIs were verified
  after deployment. The preceding webspace state is retained at
  `/home/www/Monzero-backup-20260823T1812Z-pre7` for rollback.
- Both IONOS public nodes now run the exact pre7 Linux daemon from the published
  archive and report `0.18.5.1-38914bf13`. The European deployment can be
  rolled back from `/var/backups/monzero-pre7-20260823T1814Z`; the US deployment
  can be rolled back from `/var/backups/monzero-pre7-20260823T1815Z`. Each
  systemd service is active and synchronized at height 1,040 with canonical
  top hash
  `44029426d863f954745a73322dafdae3370299772e2990abd9721ea0b88067af`,
  and the nodes maintain their bidirectional P2P relationship. Operator-local
  readiness checks and the public website API agree that synchronization and
  peer-count requirements pass but the latest block is more than three hours
  old, so the freshness gate correctly fails and the website reports
  `network_ready=false`. This is a live mining/network condition rather than a
  daemon deployment failure.
- One temporarily active local RandomX thread mined blocks 1,040 and 1,041,
  after which the miner was restored to its prior one-thread, battery-aware
  background policy. The local node and both pre7 public nodes converged at
  height 1,042 with top hash
  `76cbc51636b282da330878300504aa45ea90e28ab16245e430307521aabe1199`.
  The exact packaged readiness gate then passed independently on both VPSs
  with three peers and tip ages of 36 and 37 seconds. The public HTTPS API
  independently reported `status=OK`, `synchronized=true`,
  `peer_ready=true`, `tip_fresh=true`, and `network_ready=true`. This proves
  the deployed pre7 topology can propagate a fresh tip; it is not evidence of
  sustained independent mining, and freshness will lapse again without
  continuing hash power. The next timer-driven readiness cycles also passed on
  US and EU at height 1,042 with three peers and tip ages of 300 and 319
  seconds, proving the scheduled checks recovered from their earlier truthful
  stale-tip failures without manual service intervention.
- Both pre7 VPSs now run a second hardened five-minute systemd timer for
  operational health, separate from consensus/network readiness. It checks the
  service main process, loopback operator RPC identity and synchronization,
  height and top-hash shape, resident memory, data-volume usage, and recent
  daemon error-log visibility. Initial sandboxed runs passed at height 1,042:
  EU used 287 MiB RSS and 3% disk; US used 285 MiB RSS and 3% disk, with no
  error-level lines in either retained 200-line log window. A forced 1 MiB RSS
  ceiling produced the required nonzero failure and diagnostic. These journal
  checks improve host monitoring but do not provide an external alert receiver
  or close the required 24-hour and seven-day observation periods.

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
pinned Linux and Windows command-line packages at the manifest source commit;
both pass normal verification and deterministic same-machine packaging, but
neither has been independently reproduced, signed, or tested on a clean
Windows system. Genesis pre6 replaces pre5's compatibility-limited Linux
archive with matching pinned Linux and Windows builds that are reproducible
across clean local build directories and pass the strict package gates. It is
still not a production release because separately trusted reproduction,
signing, a security audit, broader independent clean-system testing, and the remaining
network-readiness requirements have not been completed. None of these archives
may be promoted as stable without satisfying the remaining external release
gates. Genesis pre7 supersedes pre6 because the exact pre6 mining launcher had
an invalid PowerShell pipeline escape. Pre7 corrects that launcher and passes
the exact native network, mining, and shutdown workflow, but remains an
unsigned, unaudited prerelease with the same external production gates.

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
- Independently reproduce both strict-verifier-compatible pinned Linux and
  Windows candidates on separate clean systems.

## External evidence required before production release

- Release version/codename, supported platforms, and final source commit.
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
