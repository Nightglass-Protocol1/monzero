# Monzero ecosystem website development plan

Updated: 2026-10-19. Status: repository analysis and Release 1 preparation.
Active priority: website expansion; DEX work is deferred. Local mining and builds
remain stopped by owner request. No automatic payouts, new wallet custody, chain
changes or browser wallet are authorized by this plan. The owner explicitly excludes all
web-wallet work, including research/specification, from the requested scope.

## Requirements and scope

Implement the owner's attached “MONZERO.ORG — COMPLETE WEBSITE DEVELOPMENT
INSTRUCTIONS FOR CODEX” incrementally. Preserve existing routes, working pages,
release archives/checksums, privacy controls, graphics and integrations. The
attachment ends at “Release 2 — Network and community / Advanced explorer
improvements / Network”; the detailed phases 0–11 remain available. The sequence
below follows their dependencies without inventing additional release promises.

Worktree: `core-wt-website-ecosystem`, branch
`website/ecosystem-expansion-20261019`, based on `ca34e031c`.
Claude is conducting a separate read-only architecture review. Findings will be
reconciled here before implementation acceptance. The conversation goal tool
refused creation because the paused DEX goal is unfinished; this document records
the new working priority without falsely declaring the DEX complete.

## Repository and existing architecture

This is a native cryptocurrency core repository (CMake/C++, native/functional
Python tests) with a self-contained `website/` tree. Website code has no build-time
dependencies or frontend/backend application framework. Do not run core builds
or start mining to develop the site.

- Frontend: static HTML, vanilla JavaScript, per-page CSS, shared `theme.css`,
  `site-nav.css` and `site-nav.js`. Existing dark/teal variables, transparent coin
  assets, keyboard focus and responsive menu should be reused.
- Web backend: PHP endpoints, fixed allowlisted public-node RPC destinations,
  request timeouts and JSON responses. Hosting supports PHP; repository also has
  an Nginx example. Production shared hosting differs from that example: verify
  actual routing before publishing new endpoints.
- Auxiliary backend: `utils/public-wallets/server.py`, loopback Python service,
  SQLite storage, fixed native signature verifier and authenticated PHP proxy.
  This is address-control authentication, not general user/admin login.
- Miner reporting: opt-in heartbeat PHP service, private JSON storage, HMAC
  pseudonyms and server-only ingest credentials. Reported hashrate/blocks are
  self-reported, not consensus-verified or a census of users.
- No general account/session/admin system was found in the website route tree.
  Never repurpose miner ingest credentials or wallet-profile proofs as admin auth.
- CI: `.github/workflows/{build,depends,gitian}.yml` covers native software.
  Website-specific CI and an integrated website test harness need to be added.
  Existing profile backend tests are in `utils/public-wallets/test_server.py`.
- Deployment: `website/README.md`, `website/nginx-monzero.conf`, historical
  deployment documents/scripts. Keep secrets outside document root; inspect
  configuration names and permissions without exposing secret values.

## Existing route and API inventory

| Route | Existing role and dependency |
|---|---|
| `/` | Home, downloads, node information, miner table, mining instructions |
| `/explorer/` | Blocks, transactions and assets via allowlisted `api.php` |
| `/stats/` | Up to 720 mainnet headers, hashrate/difficulty/interval/tx charts |
| `/wallets/` | Opt-in signed wallet disclosures; historical founder record |
| `/app/` | Local unsigned asset drafts; no wallet signing/submission |
| `/founder/` | Founder declarations and transparency |
| `/fund/` | Existing donation/fundraising information |
| `/roadmap/` | Verified progress and unfinished delivery gates |
| `/security/` | Security information |
| `/downloads/`, `/releases/`, `/assets/` | Existing artifacts, metadata and graphics |
| `/api/node-info/index.php` | Fixed-source node info for homepage |
| `/api/supply/index.php` | Existing supply calculation/data endpoint |
| `/api/miner-stats/index.php` | Opt-in reporter ingestion and public aggregates |
| `/api/donations/index.php` | Existing fundraising data |
| `/explorer/api.php` | POST allowlist: info, blocks, block, transaction, assets, asset, pool |
| `/stats/api.php` | GET mainnet header history, serialized 60-second cache |
| `/wallets/api.php` | Fixed HTTPS proxy for signature-authenticated profiles |

`explorer` action `pool` means the transaction mempool, not mining-pool worker
statistics. Never use it as a worker/payout API. Existing pool link is
`https://pool.monzero.org/`; discover and verify its actual supported API before
claiming dashboard integration. Current homepage mining fee/payout statements
must be checked against the pool rather than copied as immutable constants.

## Data correctness and privacy

The public-node source currently configured is `node.monzero.org:6175`.
Read-only network calls must use fixed destinations, bounded inputs/responses,
timeouts and caching. Never expose arbitrary RPC forwarding or user-provided URLs.
Existing HTTP upstream transport is a dependency to review for authenticated TLS;
calling data “verified” must not imply an independent consensus proof.

`src/cryptonote_config.h` defines 11 XMZ decimal places and a 120-second target.
Use decimal strings/BigInt for exact atomic amounts; floating-point estimates are
acceptable only for explicitly approximate mining projections. A header reward
may include fees; do not silently describe it as pure emission or future reward.
Reward and supply methodology must be checked against native RPC/source.

Unknown supply, peers, pool history, market prices, exchange status, benchmark
values and user counts must remain unavailable. Never seed realistic-looking
sample data into production. Node connections are not unique public nodes;
transactions are not users. Public disclosures cannot reveal hidden balances.

## Implementation phases and acceptance

### Release 1 — Core site and mining

1. Finish repository/dependency review with Claude; inventory data contracts,
   caching, existing security and deployment limitations. Review source before
   refactoring; keep routes and artifact hashes unchanged.
2. Extend shared accessible layout and homepage ecosystem links. Preserve current
   downloads and live widgets. Add timestamps, explicit loading/error/empty states,
   keyboard focus, reduced-motion behavior and stable chart dimensions.
3. `/mining/calculator/`: pure calculation module and tested input validation;
   H/s, KH/s, MH/s, watts, electricity cost, fee and hardware cost. Use trusted
   mainnet difficulty/reward observations, show source/time and methodology.
   Price-dependent outputs remain unavailable without a validated price source.
   Test units, zero hashrate, invalid/overflow input, fee bounds, zero revenue,
   negative net return and break-even exclusion. Label variance and changing
   difficulty; no profitability promises.
4. `/mining/dashboard/`: verify supported pool API, then allow public-address
   lookup without identity persistence by default. Show only available worker,
   share, payout and historical data. Optional local labels require opt-in and
   removal controls. No seed/key collection or unsupported “connect account”.
5. `/mining/benchmarks/`: empty searchable catalog until sourced records exist.
   Define provenance/verification status and moderation before accepting writes.
   Tests must distinguish verified records from community estimates.

### Release 2 — Network and community

Extend explorer; add `/network/` and storage-backed historical aggregation.
Expose only collected history for 24h/7d/30d/90d/year/all ranges. Node map requires
lawful public observations, approximate locations and no unnecessary IP display.
Add verified community links, including owner-provided
`https://t.me/MonzeroOfficial`. Voting is non-binding; submissions, bounties and
achievements depend on moderation, auth, abuse controls and auditable provenance.
Alerts require explicit opt-in, threshold validation, rate limiting/deduplication.
Leaderboards use consented data with opt-out and self-report labels.

### Later releases — dependent capabilities

- Payments: verify actual core address checksum/network rules and wallet URI
  specification before QR/address utilities. Merchant documentation remains
  self-hosted/non-custodial; authenticate callbacks and make confirmation state
  explicit. Browser/web wallet implementation and research/specification are excluded by
  the owner. Public-address lookups and payment requests must never generate,
  collect or store keys/seeds or sign transactions.
- Exchanges/markets: sourced directory and dated listing tracker; live price,
  depth and volume only from verified venue APIs. No invented listings.
- Transparency: extend existing fund/founder/roadmap pages with dated evidence,
  distinguish declarations and manual reconciliation from independently checked
  data; no automatic treasury payments or guaranteed release dates.
- Ecosystem directory: review submissions; label third-party services. Faucet
  architecture and paused backend only, with treasury limits, anti-abuse and
  logs; no payout activation without explicit approval and security testing.
  Marketplace is an architecture specification, not escrow/fund management.
- Developer portal: actual RPC examples, pool/explorer contracts, non-custodial
  payments, repositories and clearly separate testnet documentation.
- Versioned read-only API: reuse existing adapters; fixed method allowlists,
  validated inputs, bounded responses, structured errors, caching, rate limits,
  conservative CORS and security headers. Do not publicly proxy unrestricted RPC.
- Administration: require strong authentication, role-based server authorization,
  secure sessions/CSRF defenses, throttling and append-only audit events before
  exposing moderation or publishing operations. No hardcoded admin credentials.

## Database and migration plan

Release 1 calculator/layout needs no database migration. Preserve the existing
wallet-profile SQLite database and miner JSON format; do not mix their secrets
or private records with ecosystem features.

Before accepting submissions introduce a separate private ecosystem database,
using SQLite only if deployment concurrency/storage supports it. Candidate tables:
`schema_migrations`, `benchmarks`, `submissions`, `moderation_events`,
`network_samples`, `network_aggregates`, `proposals`, `votes`, `bounties`,
`exchange_records`, `campaign_updates`, `directory_entries`, `admin_roles`,
`audit_events`, `alert_rules`, `alert_deliveries`. Define retention, consent,
unique constraints, transaction boundaries and indices feature by feature.
Use numbered transactional migrations, backup/restore and upgrade tests. No
migration or production database change is approved merely by listing it here.
General account credentials/auth provider selection remains an architectural
choice requiring verified hosting support and a concrete threat model.

## Verification and publication gates

Run lightweight interpreted unit/syntax checks without compiling or mining.
Verify HTML links, existing download/checksum preservation, PHP/JS contracts,
calculator edge cases, source precision and upstream outages. For interactive
work perform desktop/mobile, keyboard and accessibility inspection. Add API
integration, rate-limit, permission/auth, CSRF and migration tests as features
are introduced. Test external services with bounded read-only requests; no live
mining, transfers or faucet payouts.

Before deployment: review concrete diff, back up replaced files, stage only
reviewed site changes, verify deployment routing/headers and HTTPS responses,
and keep rollback available. Roadmap may claim only verified milestones.
Do not report placeholder/unavailable integrations as completed features.

## Progress log

- 2026-10-19: isolated worktree created; route/source inventory and initial
  phased plan recorded. Claude architecture review running. No site changes
  deployed; no mining or builds restarted.


### Claude review reconciled

Claude completed its source-only review (`core/build/claude-website-analysis-20261019.txt`).
Confirmed the no-build static/PHP architecture and separate profile SQLite service.
Additional findings: `.htaccess` enforces same-origin scripts/connections; Nginx
example lacks index.php routing parity and bypasses readiness fields on one
node-info route. Existing menus differ. These require regression checks, not a
blanket rewrite. Preserve CSP and avoid inline/CDN scripts.

Release 1 benchmarks can use reviewed JSON plus GitHub PR submissions, avoiding
an unauthenticated write endpoint or premature admin/database dependency.
Telegram is explicitly supplied by the owner; no further confirmation is needed.
Pool API support and actual production PHP extensions remain to be verified.
Do not adopt suggested guessed pool fees, address-prefix-only validation, or
unverified market assumptions as verified facts. The calculator leaves market
outputs unavailable and pool fee editable, initially zero and clearly labelled.

Calculator implementation has started as an isolated additive route, reusing the
existing allowlisted explorer endpoint. It refuses wrong-network, unsynchronized,
old or malformed observations; uses the observed reward including fees; expires
observations/results after five minutes; keeps inputs in the current tab only.
Ten pure calculation tests pass, and both module syntax checks pass. Browser,
upstream integration and complete Release 1 acceptance are still pending.
No deployment, mining or build was performed.


- Calculator verification follow-up: Chromium checks passed at 1440px and 390px
  with explicitly synthetic test fixtures, no horizontal overflow or JS errors,
  correct zero-hashrate behavior, invalidation after input changes and clearing
  on upstream failure. Visual inspection found and fixed inherited header overlap.
  Reusable browser check: `tests/website/check_calculator_browser.py` (requires
  installed PHP, Chromium and Python Playwright; does not build or mine).
- A bounded read-only live explorer request confirmed mainnet status, synchronized
  node, matching height/header, 120-second target, numeric difficulty and an exact
  safe-integer atomic reward. This verifies the current input contract, not future
  availability or all browser integration. Calculator remains unpublished.


### Reconfirmed request and homepage progress

The owner resent the website requirements in attachment
`47becf12-eb32-4dea-863a-ddf643c12c68/pasted-text.txt`; detailed requirements
remain the same, with the Release 2 sequence still truncated. Continue this plan.

Homepage additions: explicit XMZ naming, Start mining and owner-supplied Telegram
links, calculator entry point, estimated-hashrate label, target interval, observed
block reward including fees and block time. Missing statistics now show unavailable
instead of fabricated zeroes; failed refreshes clear previous node/header values.
No existing download/release reference was changed. This implements part of the
homepage scope; supply integration, ecosystem directory and development feed remain
open. No deployment or native build/mining performed.

Verification: `tests/website/check_home_network.py` passed at 1440px and 390px,
covering observed fields, absent inputs, failed refresh clearing, required links,
no horizontal overflow and no JavaScript runtime errors. `node --check` and
`git diff --check` passed. This is fixture-backed browser verification, not a
claim that every production service or the entire website is accepted.

### Claude review fixes — 2026-10-19

Actual Claude source review completed successfully; evidence is
`core/build/claude-website-review-20261019.txt`. Addressed the pre-publication
privacy, difficulty-source and freshness findings:

- Calculator controls remain disabled until its module and submit handler load;
  a no-script notice explains why. No default form submission of user inputs.
- Calculator now uses the existing node-readiness PHP endpoint instead of a
  second explorer request. The adapter includes matched tip height/reward;
  mismatched info/header heights or hashes invalidate freshness.
- Next-block difficulty drives expected work, with nonzero high-64-bit difficulty
  rejected. Server readiness supplies the existing 900s age / 300s future-skew
  operational policy; visitor wall-clock accuracy is not a readiness condition.
  Five-minute result expiry uses a monotonic browser clock.
- Module MIME mappings added to both hosting examples; actual production headers
  still require deployment validation. No security-header claim is made for the
  existing Nginx inheritance issue, which remains open.
- Small nonzero results use significant digits; result text is larger. Automatic
  refresh uses silent validity checks. Repeated input notices are deduplicated.
- Homepage reward/block display now requires a synchronized, fresh observation;
  unavailable high-bit difficulty is never presented as low-bit hashrate.

Verification: ten calculation cases, four PHP adapter tests using a synthetic
loopback RPC server, expanded Chromium tests at 1440px and 390px (wrong network,
unsynchronized/stale data, mismatched height, unsafe reward, high-bit difficulty,
result expiry, small nonzero reward, outage, no-JavaScript disabled inputs), plus
homepage stale/unsynchronized rejection checks. All passed. PHP/JS syntax and
whitespace checks passed. Reusable check runner: `tests/website/run.sh`; requires
installed Node, PHP, Chromium, Python Playwright. It performs no native builds or
mining. Hosted CSP/MIME acceptance and a full accessibility audit remain open.

Remaining review items: cache/rate-limit shared public observations; resolve
Nginx example routing/security-header inheritance; unify navigation; verify pool
terms and supported read-only endpoints; benchmark catalog with reviewed source
records. Read-only pool research is already within the authorized scope and does
not need additional owner permission. Keep unknown data unavailable.


### Explicit owner scope correction

The owner excludes the web wallet from the supplied feature list. Phase 5.3
(browser-wallet research/architecture) is removed as well as any implementation.
All other requested website features remain in scope. This is not a request to
remove desktop wallet downloads or public-address/payment-request utilities.


### Pool dashboard implementation — 2026-10-19

Read-only HTTPS checks of the live pool homepage and `/api/stats` confirmed the
published endpoints and config: XMZ, 11 decimals, PPLNS, 1% fee, 1 XMZ threshold,
60 confirmations, payments-enabled flag. These are dated pool reports, not a
promise that payouts cannot be paused. Inspected source:
`/home/tripo/projects/Monzero-App/pool/xmzpool/xmzpool.py` (`stats`, `miner_stats`,
`http`). Claude independently reviewed the contract; output:
`core/build/claude-pool-contract-20261019.txt`.

Additive `/mining/dashboard/` implementation now supports explicit public-address
lookup, ten-minute share-based hashrate, connected worker count, pending/paid
atomic-string amounts, contribution percentage where consistent and up to 50
pool-reported sent payments with explorer links. Unknown-address and real-zero
responses cannot be distinguished by the upstream API. Sent is not chain-confirmed;
timestamps are pool payment record times. Missing share counts, uptime and
historical hashrate remain unavailable. Charts, labels and independently checked
confirmations are still open requirements, not completed by this page.

Security: fixed HTTPS destination/no redirects, bounded bodies/timeouts, POST-only
lookup, shape-only address boundary, response allowlist, no CORS, no-store client
responses, ten requests/client/minute and sixty total/minute, serialized upstream
access. Private operational state holds short-lived hashed client limits and
only public pool aggregate caching; individual miner responses are not cached
on disk. No plain address/IP logs in the adapter. Pool upstream GET query logging
remains possible and is disclosed. Raw worker names are withheld because the
pool may derive them from miner password/login fields; numbered connections are
snapshot-only identifiers. No automatic initial lookup or address persistence.
Refresh is explicitly opt-in and stops while the tab is hidden; Clear cancels
requests and clears the address/results.

Verification: contract checks for exact large amounts, unknown fields, invalid
responses, generic worker labels and inconsistent percentages passed. Two PHP
HTTP adapter tests passed using an explicitly replaced synthetic transport:
method/body/cross-site guards, exact amounts, cache behavior, request limits and
absence of plain address/IP/miner amount from disk state. This does not verify
live TLS transport or production hosting. Chromium checks at 1440/390px passed
explicit lookup, large-amount formatting, payment links, no overflow, error
clearing, clear action and no localStorage persistence; JS-disabled controls
remain disabled. Syntax and whitespace checks passed. Changes are unpublished.

Outstanding: shared navigation, CPU benchmark catalog, historical chart support,
worker-label strategy without sensitive upstream names, public observation cache
hardening, production HTTP/TLS/header validation and full Release 1 regression.
