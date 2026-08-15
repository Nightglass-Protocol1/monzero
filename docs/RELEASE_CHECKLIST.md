# Monzero release checklist

This checklist applies to every Monzero node, CLI wallet, GUI wallet, miner
control, website download, and consensus release. Native amounts use XMZ.

## Scope and source

- [ ] Release version, codename, source commit, and supported platforms agreed
- [ ] Working tree clean or every included patch documented
- [ ] Submodules pinned and verified
- [ ] Consensus-affecting changes identified explicitly
- [ ] Database or wallet migration requirements documented
- [ ] User-visible changes and known limitations written
- [ ] Independent reviewer approves the release scope

## Consensus and network safety

- [ ] Genesis and protected consensus-vector tests pass
- [ ] Block reward, precision, fees, and amount parsing tests pass
- [ ] Valid and invalid transaction tests pass
- [ ] Synchronization from an empty data directory succeeds
- [ ] Reorganisation and restart tests pass
- [ ] Node interoperates with the currently deployed release
- [ ] Seed list contains no node configured to connect to itself
- [ ] Mainnet, testnet, and stagenet identifiers remain isolated
- [ ] Hard-fork activation height and operator notice reviewed, if applicable

## Wallet safety

- [ ] New wallet creation tested in CLI and GUI
- [ ] Seed restoration reproduces addresses and balances
- [ ] Incoming and outgoing transfers confirmed
- [ ] Pending, failed, pool, and confirmed history tested
- [ ] Coinbase and normal output unlock behaviour tested
- [ ] Wallet shutdown and unclean-restart recovery tested
- [ ] View-only, multisig, hardware, and offline signing marked tested or unsupported
- [ ] No workflow requests a recovery seed except an explicit recovery operation

## Branding and configuration

- [ ] Product name is Monzero and native ticker is XMZ
- [ ] Executable names, titles, prompts, logs, and default paths are correct
- [ ] Ports, address prefixes, network UUIDs, DNS seeds, and website are correct
- [ ] Required upstream attribution and copyright notices are preserved
- [ ] User-facing inherited Monero service links are removed or clearly contextual
- [ ] Warnings prohibit cross-fork key and seed reuse

## Automated testing

- [ ] Unit tests pass from a clean build
- [ ] Core and functional tests pass
- [ ] RPC compatibility tests pass
- [ ] Parser and consensus fuzzing has no unresolved regressions
- [ ] Website and explorer API smoke tests pass
- [ ] Linux launch, mining, wallet, and uninstall scripts pass shell validation
- [ ] Windows launch and mining scripts pass on a clean Windows system

## Build and package

- [ ] Linux build produced by the pinned build environment
- [ ] Windows build produced by the pinned cross-build environment
- [ ] A second builder checks reproducibility
- [ ] Executable formats and required runtime libraries inspected
- [ ] Archives contain only intended files
- [ ] README and upgrade instructions included
- [ ] SHA-256 manifest generated and verified
- [ ] Release manifest signed with the Monzero release key
- [ ] Packages scanned and tested after extraction from their final archives

The Linux archive layer is generated with `utils/release/package-linux.sh`.
It refuses a dirty tree unless `ALLOW_DIRTY=1` is explicitly supplied, in
which case the filename and embedded manifest are marked development/dirty.
`utils/release/verify-package.sh` verifies archive shape, inner checksums,
executable presence, formats, and reported versions. This makes packaging
deterministic; it does not by itself make locally compiled binaries
reproducible. `RELEASE_STRICT=1` additionally rejects dirty manifests,
unverified build reproducibility, dynamically linked binaries, debug
information, and unstripped executables.

## Deployment

- [ ] Public node binaries backed up before replacement
- [ ] Public node database backup or recovery procedure confirmed
- [ ] New node starts, binds expected ports, and reports correct version
- [ ] Peer counts, height, difficulty, synchronization, and RPC checked
- [ ] At least one independent node successfully handshakes and synchronizes
- [ ] Explorer and website display current chain data
- [ ] Download files, sizes, MIME types, checksums, and links verified publicly
- [ ] Rollback binary and rollback instructions remain available

## Publication and monitoring

- [ ] Release notes identify experimental and unaudited components
- [ ] Source commit and signed hashes published
- [ ] Node, miner, wallet, and service operators receive upgrade instructions
- [ ] Security contact and disclosure process published
- [ ] Height, fork divergence, peers, RPC, CPU, memory, disk, and logs monitored
- [ ] Post-release review performed after 24 hours and seven days

## Assets-specific gate

For any future Monzero Assets release:

- [ ] Phase 0 stabilization gates are complete
- [ ] Consensus and cryptographic specifications are public
- [ ] Independent cryptographic and implementation audits are resolved
- [ ] Inflation and cross-asset conversion tests pass
- [ ] Asset wallet restoration tests pass
- [ ] Extended public testnet has completed a planned upgrade
- [ ] Mainnet activation height has advance operator coordination
