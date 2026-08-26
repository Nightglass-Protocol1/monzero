# Monzero: An Independent Privacy-Preserving Digital Currency

**Protocol paper, draft 1.1 — August 2026**

## Abstract

Monzero is an independent proof-of-work digital-currency network derived from
the Monero codebase. Its native currency, XMZ, is designed for private,
permissionless electronic payments: one-time destination keys obscure the
recipient, ring signatures make the spent output ambiguous, confidential
commitments hide transferred amounts, and key images prevent double spending.
RandomX proof of work orders transactions and secures the ledger without a
premine or stake allocation.

Monzero has a distinct genesis block, network identifiers, address prefixes,
ports, monetary policy, and chain history. It targets 100 million XMZ through a
smooth primary-emission curve and then maintains a permanent subsidy of 3.26
XMZ per two-minute block. This paper describes the protocol represented by the
current source tree, its security assumptions, and its limitations. Monzero is
experimental, unaudited software; this document is not an investment
prospectus or a claim that the system is production-ready.

## 1. Motivation and design goals

A public ledger is useful for independent verification, but a transparent
transaction graph exposes balances and commercial relationships. Monzero aims
to preserve public verification of the rules without making every payment
publicly traceable.

The protocol has five primary goals:

1. **Transaction privacy.** Avoid directly publishing the sender, recipient,
   or amount of an ordinary payment.
2. **Permissionless verification.** Allow any participant to run a node and
   independently validate the entire chain.
3. **Permissionless issuance.** Distribute new XMZ through proof of work, with
   no hard-coded premine.
4. **Fungibility.** Minimize transaction-history information that could cause
   otherwise equal units to be treated differently.
5. **Sustainable security.** Continue paying a block subsidy after primary
   emission approaches its target.

Privacy is not binary. Network observations, wallet compromise, user behavior,
small anonymity sets, malicious peers, and external information can all weaken
it. The protocol reduces information exposed by the ledger; it does not make
operational security unnecessary.

## 2. System model

Monzero uses an unspent-output ledger. Wallets construct transactions that
consume prior outputs and create new ones. Full nodes independently check each
transaction, maintain the set of spent key images, validate proof of work, and
select the valid chain with the greatest cumulative difficulty.

The principal participants are:

- **wallets**, which hold private keys, discover owned outputs, construct
  transactions, and sign spends;
- **full nodes**, which relay and validate transactions and blocks;
- **miners**, which assemble valid candidate blocks and search for RandomX
  proofs of work; and
- **light or remote-wallet users**, who delegate some chain access to a node
  and consequently adopt additional privacy and availability assumptions.

No central party assigns accounts or approves payments. Consensus is defined
by deterministic validation in the node software. Human-readable documents
explain that implementation but do not override it.

## 3. Transaction privacy

Monzero inherits the mature CryptoNote and Monero transaction model. The
mechanisms below provide complementary protections; none should be evaluated
in isolation.

### 3.1 One-time destination keys

A standard address contains public spend and view keys. For each payment, the
sender derives a unique one-time output key using an ephemeral transaction
secret and the recipient's public keys. The recipient uses the private view
key to scan the chain and the private spend key to authorize spending.

Consequently, outputs sent to the same published address do not contain that
address or a reusable destination key on chain. Subaddresses let a wallet
present unlinkable receiving identities for different contexts. Integrated
addresses additionally carry a short payment identifier, but subaddresses are
generally the safer separation mechanism for new integrations.

### 3.2 Ring signatures and key images

To spend an output, a wallet forms a ring containing the real output and
decoys selected from the chain. A Concise Linkable Spontaneous Anonymous Group
(CLSAG) signature proves that one member is authorized without identifying
which one. At the active protocol version, a normal ring contains 16 members:
one real input and 15 decoys.

Each real output deterministically produces a key image. The image does not
reveal which ring member was spent, but a second use of the same output
produces the same image. Nodes reject repeated key images, providing
double-spend detection without revealing the consumed member.

Ring signatures provide plausible ambiguity, not a guarantee that all members
are equally likely. Decoy-selection quality, output age, unusual spending
patterns, chain forks, and information learned elsewhere can reduce the
effective anonymity set.

### 3.3 Confidential amounts

Ring Confidential Transactions encode amounts in Pedersen commitments. A
commitment to amount \(a\) with mask \(x\) has the form

\[
C = xG + aH,
\]

where \(G\) and \(H\) are independent curve points. Commitments are additive,
so nodes can verify that inputs equal outputs plus the public transaction fee
without learning the hidden values.

Bulletproofs+ range proofs demonstrate that each committed output amount lies
in the permitted range. This prevents creating value through negative or
overflowing amounts while keeping the amounts confidential. Encrypted amount
data lets the intended recipient recover the value and commitment mask.

### 3.4 Transaction propagation

The peer-to-peer layer includes Dandelion++ stem-and-fluff relay behavior and
optional Tor/I2P connectivity. These measures seek to make source-IP inference
harder, but they are not an anonymity proof. A remote RPC operator can observe
requests, timing, and IP metadata; users with stronger threat models should run
their own node and use an appropriate anonymity network.

## 4. Consensus and proof of work

### 4.1 Blocks and chain selection

Miners gather valid transactions, construct a coinbase transaction paying the
block subsidy and fees, and search for a header hash below the current target.
Nodes accept only blocks whose transactions, timestamps, size, reward, and
proof of work satisfy consensus. Among competing valid histories, nodes follow
the chain with the greatest cumulative difficulty.

The target interval is 120 seconds. Difficulty adjusts from recent block
history to keep the long-run interval near that target despite changing hash
rate. Short-term block times remain stochastic.

### 4.2 RandomX

Protocol version 16 uses RandomX, a proof-of-work function optimized for
general-purpose 64-bit CPUs. RandomX combines randomized code execution and
memory-hard techniques to narrow, rather than eliminate, the efficiency gap
between commodity processors and specialized hardware.

Proof of work gives the chain an objective accumulated-work ordering and makes
history replacement costly in proportion to the honest network hash rate. It
does not protect a small network from an attacker able to obtain majority hash
power. Hash-rate concentration and the availability of independent miners are
therefore material security considerations.

### 4.3 Adaptive block weight and fees

Monzero inherits an adaptive block-weight mechanism. The full-reward zone at
the active protocol is 300,000 bytes, and recent block weights influence the
permitted weight and reward penalty. Blocks can grow when demand persists, but
miners incur a subsidy penalty for blocks above the effective median. Dynamic
per-byte fees discourage spam and compensate miners for including
transactions. If ordinary reward calculation fails while estimating a fee,
the implementation conservatively derives its fallback upper bound from the
maximum base subsidy permitted by the monetary parameters. This bound is tied
at compile time to the 120-second block target so a target change cannot
silently retain the old assumption.

## 5. Monetary policy

One XMZ is divided into \(10^{11}\) atomic units. Eleven decimal places are the
maximum precision compatible with the 100,000,000-XMZ primary-emission target
and the unsigned 64-bit amount representation used by this implementation.

Let \(M = 10^{19}\) atomic units be the primary-emission target and \(A_n\) the
cumulative generated amount before block \(n\). With a two-minute target, the
base subsidy is

\[
R_n = \max\left(\left\lfloor\frac{M-A_n}{2^{19}}\right\rfloor,
326{,}000{,}000{,}000\right)
\]

atomic units, before any block-weight penalty. The second term is 3.26 XMZ.
The first subsidy is approximately 190.73486328125 XMZ and declines smoothly
with issuance. The permanent floor eventually replaces the declining term.

At the target interval, tail emission is approximately 856,728 XMZ per
365-day year. Because the denominator (circulating supply) continues to grow,
the percentage issuance rate trends toward zero, while the absolute subsidy
continues funding proof-of-work security. Transaction fees are paid in XMZ and
are added to the miner reward.

There is no hard-coded premine. Coins produced during any private bootstrap or
test period are nevertheless real chain issuance. The project commits to
publishing the public-launch height and time, team-controlled addresses and
balances, total privately mined amount and intended use before representing
the network as publicly launched.

## 6. Network identity and parameters

Monzero is not a Monero test network and does not share Monero's ledger.

| Parameter | Mainnet value |
| --- | --- |
| Currency / ticker | Monzero / XMZ |
| Target block interval | 120 seconds |
| Atomic units per XMZ | 100,000,000,000 |
| Primary-emission target | 100,000,000 XMZ |
| Tail subsidy | 3.26 XMZ per block |
| Proof of work | RandomX at protocol v16 |
| Transaction version | 2 |
| Ring size | 16 at the active protocol |
| Coinbase unlock | 60 blocks (about 120 minutes) |
| Normal output spendable age | 10 blocks (about 20 minutes) |
| Address prefixes | 86 / 87 / 88 |
| P2P / RPC / ZMQ ports | 6174 / 6175 / 6176 |
| Network UUID | `94834264-d0b2-41dd-b0f2-0ada675c7710` |
| Genesis nonce | 2271206363 |
| Genesis block hash | `84f9ebdac8924806f037482ec16fd59b271e954d3e00363dd6c7e4ce9dd659e4` |

Separate testnet and stagenet identities are defined in the machine-readable
consensus manifest. Wallet seeds and private keys should never be reused
between Monzero, Monero, or any other CryptoNote-derived chain. Cross-chain key
reuse can turn activity on one ledger into information about another.

## 7. Protocol activation and upgrades

The inherited protocol revisions are scheduled at heights 1 through 16, one
version per block. This compressed bootstrap schedule means that the intended
steady-state public protocol is version 16 rather than a replay of Monero's
historical activation timeline. Public mining should begin only after those
bootstrap revisions have activated.

Consensus upgrades require a new rule version, implementation review, tests,
release coordination, and broad operator adoption. Nodes that enforce
incompatible rules can split into separate networks. The source code and
`config/monzero-consensus.json` are authoritative for exact validation
parameters; changes to this paper alone do not alter consensus.

## 8. Monzero Assets research

The repository contains an inactive prototype for fixed-supply private assets.
Its intended model would make an asset identifier, issuance, and maximum
supply public while seeking to hide owners, recipients, balances, and transfer
amounts. XMZ would remain the only currency for fees and mining rewards.

This feature is **not active**. Asset transactions are not serialized or
accepted by current public consensus, wallets do not provide active asset
support, transaction version remains 2, and proposed hard-fork version 17 has
no activation height. Descriptor, authorization, conservation, registry, and
ownership-proof code exists only as a reviewable research scaffold.

Activation must not occur without Phase 0 stabilization, an independently
reviewed cryptographic construction, complete consensus and wallet
integration, adversarial testing, an isolated development network, and an
extended public testnet. Thinly traded assets would also have smaller
practical anonymity sets than XMZ; cryptography cannot manufacture unrelated
activity.

## 9. Security assumptions and limitations

Monzero's safety depends on more than correct cryptographic primitives:

- **Consensus majority.** An attacker controlling sufficient hash power can
  reorganize recent history, censor transactions, or double spend its own
  payments.
- **Implementation correctness.** Consensus, cryptography, wallet, database,
  and networking bugs may cause loss of funds, privacy failures, or chain
  splits. The Monzero-specific changes have not received an independent audit.
- **Endpoint security.** Malware, exposed seeds, weak backups, compromised
  build systems, and malicious remote nodes can defeat protocol protections.
- **Metadata.** Timing, IP observations, exchange records, payment context, and
  repeated user behavior can correlate otherwise private transactions.
- **Anonymity-set quality.** Ring membership is not equivalent to a uniform
  posterior probability. Statistical and temporal information may distinguish
  candidates.
- **Finality.** Proof-of-work settlement is probabilistic. Applications must
  choose confirmation requirements according to value, observed hash rate,
  and reorganization risk.
- **Supply auditing.** Confidential amounts make ordinary transaction values
  private; supply integrity relies on sound commitment and range-proof
  cryptography plus correct verification software.
- **Network maturity.** A small peer and miner population provides weaker
  resilience, censorship resistance, and practical privacy than a large,
  diverse network.

Users should verify release hashes and signatures when available, keep seeds
offline, use a newly generated Monzero-only wallet, and run a full node where
their threat model warrants it. No protocol can recover a disclosed spend key
or seed.

Binary distribution is a separate security boundary. The release verifier
pre-inspects tar and ZIP members before extraction, rejects links, special
files, path traversal, duplicate paths, excessive entry counts, and oversized
payloads, and only then checks the packaged manifest. These controls reduce
archive-extraction risk; they do not replace authenticated hashes,
maintainer signatures, reproducible builds, or independent review of the
binary itself.

## 10. Governance and development

Monzero has no on-chain governance mechanism. Protocol evolution occurs
through public source changes, review, release artifacts, and voluntary
adoption by node operators, miners, services, and users. This makes social
coordination explicit: maintainers can publish software, but cannot force
independent participants to run it.

Consensus-critical changes should include protected vectors, deterministic
tests, multi-node and reorganization coverage, reproducible packages, and a
documented migration path. Cryptographic changes require specialist review.
Network parameters and release claims should be verifiable from source and
signed artifacts rather than trusted from a website alone.

Release qualification regenerates and replays consensus fixtures against
Monzero's own money supply, decimal precision, block target, and resulting
coinbase denominations. The suite covers emission, integer-overflow rejection,
RingCT, Bulletproofs, Bulletproofs+, CLSAG, pruning races, transaction
propagation, node restart, and longer-chain reorganization. Passing these
tests is evidence about the tested implementation and platform, not a proof of
correctness or a substitute for independent cryptographic review.

Current correctness work also protects two implementation boundaries that are
easy to overlook during toolchain upgrades. Ref10 carry normalization uses
defined integer multiplication rather than signed left shifts, preserving the
same powers-of-two arithmetic without relying on compiler-specific behavior.
Binary wallet serialization converts enumeration values through their explicit
underlying unsigned type while retaining the established varint encoding. A
mined-reward regression constructs a modern view-tagged coinbase output and
proves that the destination wallet recognizes its full amount. These checks
improve portability and reward-accounting confidence; they do not replace an
independent cryptographic review or validate any particular live wallet cache.

The desktop GUI now uses a Monzero-specific `Monzero/wallets` directory for
new wallets. To avoid locking out users upgrading from earlier prereleases,
its wallet picker also discovers wallets in the legacy `Monero/wallets`
directory, and previously saved absolute wallet paths continue to open in
place. The application does not automatically move, rename, or delete wallet
files. This compatibility behavior is especially important when rebuilding a
wallet cache after a reorganization: the keys file must be preserved, and a
new wallet is not required merely because the default directory changed.

The development GUI resource bundle now uses Monzero-specific application,
title-bar, mining-status, and mined-transfer artwork on Linux, Windows, and
macOS packaging paths. Required upstream copyright notices, research names,
and compatibility identifiers remain unchanged because branding does not
erase provenance. These changes postdate Genesis pre9 and are not present in
its published binaries.

## 11. Status and roadmap

The current project is an unsigned, unaudited prerelease. Genesis pre9 is an
explicitly untested distribution: compilation and checksum generation do not
qualify it as production-ready, and earlier pre8 test evidence does not apply
to the exact pre9 binaries. Its immediate work is
operational rather than promotional:

1. obtain independent consensus, cryptography, and implementation review;
2. complete independent binary reproduction and platform testing;
3. establish a diverse, synchronized public peer and mining network;
4. disclose bootstrap issuance and launch conditions; and
5. keep experimental asset work isolated until its separate activation gates
   are satisfied.

A fresh mainnet genesis identity is present in the development source. Its new
genesis nonce produces the block hash recorded in Section 6, and its new peer-
network UUID prevents nodes on the superseded chain from joining it. This is
not a wallet recovery seed and does not modify wallet keys. Genesis pre9 and
the live nodes still use the superseded identity until new binaries are
qualified and deployed through an explicit rollback-safe migration. Balances
and transaction history from the superseded chain will not carry into the new
genesis history; wallets must rescan the fresh chain from height zero.

No roadmap item is a promise of delivery or authorization to weaken a release
gate.

## 12. References and provenance

Monzero is based on Monero and CryptoNote research and implementation work. In
particular, the design draws on:

1. Nicolas van Saberhagen, *CryptoNote v2.0* (2013).
2. Shen Noether, Adam Mackenzie, and the Monero Research Lab, *Ring
   Confidential Transactions* (2016).
3. Sarang Noether and Brandon Goodell, *Concise Linkable Ring Signatures and
   Forgery Against Adversarial Keys* (2019).
4. Benedikt Bünz et al., *Bulletproofs: Short Proofs for Confidential
   Transactions and More* (2018), and the subsequent Bulletproofs+
   construction used by the inherited implementation.
5. tevador et al., *RandomX: A Proof of Work Algorithm Based on Random Code
   Execution* (2019).
6. Giulia Fanti et al., *Dandelion++: Lightweight Cryptocurrency Networking
   with Formal Anonymity Guarantees* (2018).

Exact Monzero parameters are recorded in
[`MONZERO_CHAIN_SPEC.md`](MONZERO_CHAIN_SPEC.md) and
[`config/monzero-consensus.json`](config/monzero-consensus.json). The asset
research boundary is specified in
[`docs/MONZERO_ASSETS_V1_SPEC.md`](docs/MONZERO_ASSETS_V1_SPEC.md), while
current release evidence and unmet gates are tracked in
[`docs/RELEASE_STATUS.md`](docs/RELEASE_STATUS.md).

Monzero is not affiliated with or endorsed by the Monero Project. Copyright
belongs to the respective CryptoNote, Monero, and Monzero contributors. Source
licensing is described in [`LICENSE`](LICENSE).
