# Monzero ecosystem website development plan

Updated: 2026-10-19. Status: repository analysis and Release 1 preparation.
Active priority: website expansion; DEX work is deferred. Local mining and builds
remain stopped by owner request. No automatic payouts, new wallet custody, chain
changes or production browser wallet are authorized by this plan.

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
  explicit. Browser wallet is a researched architecture document only.
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
