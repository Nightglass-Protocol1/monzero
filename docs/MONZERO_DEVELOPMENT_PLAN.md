# Monzero ecosystem website development plan

Updated: 2026-10-19. Status: Release 1 implementation and local acceptance;
production deployment remains pending.
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


### CPU benchmark catalog — implementation in testing

`/mining/benchmarks/` now has a versioned static catalog, strict runtime validation,
search across CPU/system/miner fields, manufacturer and verification filters,
hashrate/date/efficiency sorting, 50-row incremental presentation, and up to three
selected comparisons retained across filtering. Comparison controls restore keyboard
focus after rerender. Production `records` is empty: no measured records have been
provided or independently reproduced. Synthetic values exist only in test fixtures.

Efficiency ranking accepts wall measurements only; package and unknown power do
not produce a comparable H/s-per-watt score. All records require source evidence,
method/date and environment. A verified record additionally requires a reviewer
identifier and separate reproduction link. Publication review is via repository
pull requests/issues, documented in `submission.md`; accepting a community record
must not imply reproduction. General website admin remains a later requirement.

Five module tests passed: production schema/test-data exclusion, verification
requirements, malformed/duplicate input rejection, power-basis comparisons and
filter/sort behavior. Chromium checks at 1440px and 390px passed empty state,
filtering, comparison persistence/removal, three-item cap, keyboard focus and no
horizontal overflow/runtime errors. Full website check runner is underway;
Claude's read-only implementation review is running under
`monzero-claude-benchmarks-review-20261019.service`, output
`core/build/claude-benchmarks-review-20261019.txt`. Neither result is assumed
complete until observed terminal. Nothing deployed; no mining or builds started.

The homepage pool terms now identify their 19 Oct verification date and advise
checking current pool terms/status; existing downloads remain unchanged.


Benchmark review follow-up: Claude completed source review (unit exited 0).
Its initial missing-runner, focus and homepage-link findings described an earlier
snapshot; those had already been corrected and tested. Subsequently fixed strict
record/root field allowlists (avoid publishing incidental private fields), power
basis/null consistency, threads/core consistency, control/bidi text rejection,
distinct verification URL requirement, original source plus reproduction links,
CPU-specific link labels and row headers. Added a served HTML submission guide,
explicit selection-limit explanation and clearer unavailable-power wording.
Independent reproduction remains a human evidence-review requirement; URL/schema
checks alone cannot prove it. A separate full JSON Schema, CI wiring, duplicate
measurement review automation, shared navigation and full accessibility audit
remain open. No sourced measurements were invented to populate the catalog.

The full website runner completed successfully before the final benchmark review
fixes (`core/build/website-checks-20261019.log`); final focused verification then
passed six module tests and Chromium checks at 1440/390px including verified
source/reproduction display, comparison cap and restored focus. Diff/syntax checks
passed. No deployment or native build/mining occurred. Web wallet remains excluded.

### Shared navigation verification — 2026-10-19

The twelve existing website pages now share a static, keyboard-accessible menu,
maintained by `utils/website/sync_navigation.py`. Downloads, Assets & NFTs and
all three mining tools are directly reachable. No web-wallet feature, research
or specification is included; public opt-in wallet disclosures remain a separate
existing feature.

Claude reviewed the navigation sources and identified missing Download and
Assets & NFTs routes; both are now included in the shared menu. The earlier
focus handling issue was corrected with `FocusEvent.relatedTarget`. The full
website checks passed before these two link additions; focused navigation checks
cover all twelve pages at desktop/mobile widths and mobile without JavaScript.
The source consistency check is part of the website test runner. Changes remain
local and are not a production deployment. Production hosting validation and
the remaining Release 1 items listed above are still outstanding. Mining and
native builds remain paused as requested.

The calculator, pool dashboard and benchmark headers now use the existing
transparent teal coin asset. Mobile rendering and successful image loading were
checked in Chromium; all 36 shared navigation checks passed after the change.
A local PHP preview is available at http://127.0.0.1:8765/ without a build step.

### Navigation preference — 2026-10-19

At the owner's request, restored the previous page-specific navigation and
its desktop links/mobile Menu layout. This supersedes the unified disclosure
menu described above. Retained the new mining pages, their transparent teal
logos and homepage links. Removed the navigation generator so it cannot
reapply the rejected design. Updated navigation checks to cover the restored
layout rather than require the rejected menu.

Follow-up mobile verification found that shared responsive styles hid the short
mining-page navigation without a toggle. Scoped mining-header styles now keep
those links visible at every width, preserving the owner's preferred existing
navigation elsewhere. All 36 navigation checks passed, including mining-link
visibility at 390px with and without JavaScript. No production deployment.

### Benchmark contributor validation — 2026-10-19

Added a downloadable Draft 2020-12 JSON Schema for editor assistance and a Node
CLI that invokes the same authoritative catalog validator as the browser. The
schema documents cross-field checks that require the runtime validator. Updated
HTML and Markdown submission guidance with the commands and review boundaries.
A scoped GitHub Actions workflow runs catalog validation and its regression tests
on relevant pushes and pull requests; it has read-only repository permissions.
The workflow has not yet run on GitHub and does not publish submissions.

Verified locally: schema validity and empty production catalog; six runtime
regression tests; CLI failure for invalid dates and missing files; benchmark
browser checks at 1440px and 390px. Catalog remains empty pending sourced,
reviewed measurements. Human evidence and duplicate-measurement review remain
required. Claude source review is pending in
`core/build/claude-benchmark-publication-review-20261019.txt` outside this worktree.

Claude review completed. Fixed raw URL normalization/length/control-character
gaps, equivalent evidence-URL comparisons, invisible descriptive text and
non-finite efficiency calculations. The CLI rejects future catalog dates;
checkout no longer persists its credential. Eight runtime regression tests pass,
including the new cases. The full website suite passed before these focused
validator fixes; subsequent benchmark browser checks cover the changed module.
Branch-protection/reviewer configuration is not established by a local workflow;
no invented maintainer allowlist or automatic verification claims were added.
Numeric plausibility and independence of evidence remain human review duties.

### Nginx hosting parity — 2026-10-19

The example config now routes PHP directory indexes through the website adapter,
so `/api/node-info/` retains the same freshness/readiness contract as the local
preview. Removed the raw daemon bypass. Static cache rules use `expires` without
location-level `add_header`, preserving inherited security headers. Hidden-file
denial now precedes PHP regex matching, including hidden `.php` names.

Verified against Nginx 1.30.5 and PHP CGI on isolated loopback ports: syntax;
real adapter GET rejection; POST preservation through index resolution; static
and error security headers; checksum/module MIME; static cache policy; hidden
PHP denial. The four actual node-observation PHP tests also pass. No service
configuration, live server, mining or build process was changed. Production TLS,
PHP-FPM permissions, Apache hosting and public header validation remain pending.
A dedicated reproducible check is in `tests/website/check_nginx.py`; its required
executables and limitations are documented in `website/README.md`.

Claude's hosting review is complete. Added relative directory redirects and a
308 node-status slash redirect, and verified both through Nginx. Hardened the
test's process cleanup, disabled PHP opcode caching for its rewritten fixture,
and tested the image fixture. Trusted proxy/client-IP configuration remains a
required deployment-specific step documented in the README; no arbitrary proxy
addresses are trusted by this patch. The expanded Nginx regression check passes.

The preview roadmap now includes a dated website-progress section with links to
the three mining tools, distinguishing local verification from production release
acceptance. It preserves historical DEX entries and explicitly excludes the web
wallet. All 36 navigation checks passed; the new roadmap section was visually
inspected at mobile width with no horizontal overflow.

### Shared node observation cache — 2026-10-19

The homepage/calculator endpoint now shares public observations for 15 seconds,
with one nonblocking refresh lock and a five-second failure cooldown. Expired
observations are never returned as fallback after a failed refresh. Public
observation timestamps and response age are exposed; tip freshness is recalculated
on every response, and readiness explicitly requires mainnet. Calculator expiry
accounts for the server observation age; homepage/calculator display source time.

Cache files live outside the webroot in a deployment-specific mode-0700 temporary
directory, mode 0600, without client IDs or request bodies. Both cURL and stream
HTTP paths cap responses at 256 KiB and disable redirects. Storage errors return
503. The existing node HTTP transport remains a deployment limitation.

Eleven PHP adapter tests pass for each transport path, covering shared reads,
expiry, outage cooldown/no stale fallback, cached freshness, lock contention,
malformed storage, private permissions, response caps, redirect refusal and
non-mainnet readiness. The full website regression suite passed after the cache
change. Broader endpoint caching/edge rate limits and production hosting remain
open; this does not complete Release 1. Claude source review is pending.

Claude review completed. Fresh readers now share a read lock; only refreshes
hold an exclusive lock. Header-fetch failures and mismatched tip observations
use the short cooldown. Stream fallback reads have a total deadline, cache JSON
encoding is bounded, and private-directory ownership is checked where supported.
Calculator expiry checks both elapsed and wall-clock time to cover suspend/resume.
Fifteen adapter cases passed per transport, including a slow-trickle upstream
that reaches the total deadline; focused calculator browser checks also passed
after these fixes. Requests arriving
while an expired observation refreshes still receive explicit retryable 503; stale
results are not presented as current. Edge abuse controls remain deployment work.

### Homepage ecosystem and development discovery — 2026-10-19

Added homepage ecosystem cards linking to existing explorer/network charts,
mining tools, pool, public opt-in disclosures, source documentation and community.
A development section links existing release notes/checksums, GitHub commit and
issue pages, and the evidence-based website/DEX roadmap. The live GitHub feed is
explicitly unavailable; payment/merchant tools and the developer portal remain
planned. No web-wallet feature is offered. New sections retain the dark/teal
palette and require no JavaScript or new dependencies.

Verified discovery layout and local link destinations at 1440px, 768px and 390px,
with no horizontal overflow; inspected desktop rendering. Homepage network tests
passed at desktop/mobile sizes. The existing header/navigation and entire download
section are byte-for-byte unchanged. Claude's source/content review completed. Mining cards now explicitly say preview,
wallet privacy wording identifies signed publication, and headings use relative
font sizing. The unchanged navigation/download comparison was also verified.

### Supply metric provenance audit — 2026-10-19

The existing supply endpoint extrapolates a saved 10,000-block emission anchor
with unpenalized rewards; it does not measure circulating availability or later
reward penalties. Native constants confirm the emission parameters, but the
public node rejected `get_coinbase_tx_sum` with method-not-found, so this audit
could not reverify the anchor. The homepage now explicitly marks estimated
circulating supply unavailable instead of presenting that estimate as verified.

Preserved legacy endpoint numbers/field names and arithmetic for existing
consumers; added JSON estimate/method/anchor-verification metadata and corrected
the explanatory note. PHP syntax and homepage desktop/mobile tests passed.
A synthetic amount fixture verified unchanged legacy JSON fields and new metadata;
source comparison verified unchanged arithmetic. Local PHP lacks GMP, so no
claim is made that the emission calculation was executed in this check. Anchor
verification and production extension validation remain open.

Claude confirmed the PHP estimate wording and native emission constants. The
legacy endpoint exception is now explicitly documented and marked by an HTTP
status-description header, including for plain-text consumers. Preserving its
existing numeric contract is intentional; `max_supply` was already null and is
unchanged. Homepage wording does not imply independent verification is underway.
No local node, miner or build was started to resolve the missing anchor evidence.

### Pool session observation charts — 2026-10-19

Added opt-in, memory-only hashrate and pending-reward charts. The public pool
provides no historical samples, so the charts collect only successful lookups
after the visitor opts in, capped at 120 observations. They cause no additional
requests and never use browser persistence. Opt-out, address edits and clear
remove samples. Duplicate/backward timestamps are rejected; failed lookups,
missing metrics and intervals above 90 seconds break lines. Pending rewards are
not described as earned income; approximate chart values have an exact-amount
accessible table. Earlier pool history and persistent worker labels remain open.

Three model tests passed, covering bounds, timestamps, exact amount retention,
gaps, zero and unavailable samples. Desktop/mobile browser checks passed for
opt-in/no extra lookup, rendering, exact amounts, opt-out, address-change erasure,
clear, outage and no localStorage. Mobile rendering was inspected. Claude review
is pending; this remains local preview work.

Claude's chart review found no privacy/address-mixing defects. Addressed its
presentation findings: failed lookups immediately annotate retained samples,
sub-XMZ amounts use an appropriate vertical scale, duplicate/earlier timestamps
are explained, retrieval labels include dates and identify the website clock,
and overlapping ten-minute averages are disclosed. Four model tests now pass,
including pending-unit conversion and time-coordinate checks. Opt-out and address
edit browser checks were added during review (they were absent from Claude's
initial snapshot). Historical pool data is still unavailable; session observations
do not replace it.

### Asset cache and hosting acceptance — 2026-10-19

Read-only public probes returned HTTPS 200 on the homepage with CSP, HSTS,
nosniff, frame, referrer and permissions headers. The live node endpoint rejected
HEAD with 405/Allow POST/no-store and returned mainnet data on POST. It still uses
the previous observation format: the new website/API changes are not deployed.
These spot checks do not establish every production route or PHP dependency.

Versioned the modified homepage classic script and shared mining stylesheet to
avoid mixing new markup with seven-day cached files. Stable module URLs now
require revalidation in both Apache and the Nginx example; benchmark catalog
requests also revalidate. Isolated Apache 2.4.69 and Nginx 1.30.5 checks passed,
including JavaScript module MIME, no-cache on 200/304, inherited security headers,
checksum MIME, ordinary CSS caching and redirects. The Apache test separates
static policy from HTTPS rewriting and does not claim production PHP/TLS coverage.
Claude source review and full Release 1 regression are in progress.

Claude review completed. Added explicit inherited-expiry suppression in Apache
and a single revalidation header, tested under server-wide seven-day expiry.
Catalog JSON now revalidates in both server configurations as well as its fetch
request. Both server checks passed after those fixes, including conditional 304
responses. The full interpreted website regression suite completed successfully.
No new production deployment or native build was performed. Release acceptance
still requires a concrete staged deployment/rollback, real pool integration and
remaining feature/support decisions; local test success does not close those gates.

### Real pool integration acceptance — 2026-10-19

A bounded read-only lookup through the local production PHP adapter used the
already published founder address from `website/founder/index.html`. HTTPS pool
integration returned HTTP 200/no-store, ten pool-reported sent payments, exact
string amounts, zero connected workers, no echoed address and no historical data.
Worker-name masking and null confirmation fields matched the presentation contract.
This is source integration evidence, not independent on-chain payout verification.

A Chromium pass then used the same public address through the real dashboard:
payments rendered, both opt-in session charts appeared, local/session storage
remained empty, and Clear erased the address and observations. No private wallet,
seed, credentials, mining, transaction submission or production mutation was used.
This closes the basic live-pool transport/response/browser integration check;
outage, limits and malformed responses retain their separate synthetic evidence.

### Optional worker labels — 2026-10-19

Implemented address-scoped keyed worker identifiers without exposing raw login
names. The private HMAC key is supplied through persistent service configuration,
separate from temporary rate state; key loss/rotation invalidates old associations. Duplicate logins share
labels and are documented as such, not falsely identified as separate machines.
Browser labels stay in memory by default; explicit opt-in saves only bounded
opaque-ID/label pairs locally. Clear, opt-out and Forget remove saved data, with
honest errors if browser storage is unavailable. Raw addresses/activity are not
stored with labels. Refresh pauses while editing a label.

PHP contract/API tests passed for stable identifiers, address separation, key
rotation and hidden raw names. Three JS tests passed for label validation,
malformed storage, text safety and capacity. Claude reviewed the feature; fixes
cover persistent key configuration, cross-tab deletion, restored checkbox state
and removal of labels for disconnected workers. Chromium checks passed at 1440
and 390 pixels for explicit saving, cross-tab forgetting, individual removal,
blocked writes/deletions, chart regression, outage and clearing; no-JavaScript
controls remain disabled. Four chart-model cases and syntax/whitespace checks
also passed. No production deployment.

### Windows mining report follow-up — 2026-10-19

The new user report records repeated wallet-to-daemon connection failures after
GUI mining start. It does not include daemon mining status or a daemon crash log,
so the cause and actual CLI hashrate remain unverified. No reward transactions
alone does not establish mining failure: solo rewards require finding a block.
The published manifest identifies GUI `4b0cc9e16` and unchanged core `c4165784d`;
source inspection confirms asynchronous loopback mining commands and an existing
launcher RPC-ban safeguard. Earlier Wine mining evidence used a native Linux
daemon and does not close native Windows daemon acceptance. Keep this issue open;
no mining, builds, release replacement or claim of a reproduced fix was made.

Claude's bounded source review completed. It confirmed that the supplied log
cannot identify the mining failure, and identified two follow-up improvements:
clear stale mining status text on disconnect and retain useful, sanitized mining
command failure diagnostics. These are findings, not implemented or reproduced
Windows fixes. Review: `core/build/claude-mining-report-review-20261019.txt`.

### Benchmark submission intake — 2026-10-19

Added a structured GitHub issue form for CPU/system details, measured hashrate,
power basis, methodology, date and sanitized evidence. Public visibility and
review requirements are explicit. The template remains local until merged to the
repository default branch; the site explains the blank-issue fallback. Submission
does not add a record to the catalog or qualify it as reproduced. No real records
were invented, no issue was sent, and no automatic publishing path was added.
Claude reviewed the form and page; wording now distinguishes public issues from
catalog acceptance, and evidence accepts attachments in a textarea. The page uses
semantic headings/lists, site typography and the transparent coin. No-JavaScript
390/1440px layout, logo and keyboard skip-link checks passed. YAML parsing, field
uniqueness and required-field checks passed locally; GitHub hosting acceptance is
still pending. Full website regression suite passed (log:
`core/build/website-release1-intake-regression-20261019.log`). No deployment.

### GUI mining source follow-up — 2026-10-19

Source changes in `gui-wt-usability` clear disconnected readings, promptly refresh
after reconnect, ignore replies for a changed wallet/node, default to one mining
thread and report fixed mining-command failure categories. Claude reviewed them.
Twenty mining and thirteen startup QML results passed using the existing Linux
test executable and current source QML with mocked replies. These do not validate
the changed C++ binary or reproduce the Windows daemon disconnect. Builds and
mining remain stopped; no release replacement. Details in the GUI worktree's
`docs/WINDOWS_MINING_FOLLOWUP_20261019.md`. Original root cause remains open.

### Session mining alerts — 2026-10-19

Implemented opt-in monitoring of pool-reported hashrate drops, worker-count
thresholds and repeated lookup failures, with separate browser-notification
consent. No extra API requests or browser persistence; generic notification text
contains no address, label or amount. Bounded memory history, consecutive-sample
checks, per-condition deduplication and cooldowns apply. Pauses, unknown metrics,
shared worker identities and lack of background monitoring are disclosed.

Claude reviewed the code. Fixes cover rapid healthy readings, observations from
requests begun before enabling, server-time gaps and notification-permission
races. Eight model tests passed. Chromium at 390/1440px passed opt-in, thresholds,
deduplication, no-extra-request counts, failed lookups, clear/address changes,
permission denial and late permission resolution. Existing dashboard label/chart
regressions also passed; mobile controls were visually inspected. Browser delivery
was mocked for privacy and deterministic tests, not verified across real OS
notification centers. No deployment, mining or builds. Payout/difficulty alerts
and wider network/community work remain open.

### Pool-reported payment alerts — 2026-10-19

Added a separate payout-monitoring opt-in to the session dashboard. The first
valid list is a baseline with no alert; subsequent newly observed pool-sent
transaction IDs are deduplicated and grouped under a ten-minute rate limit.
Notifications remain generic and omit transaction IDs, addresses and amounts.
No confirmations or actual send times are inferred. Incomplete initial history
can produce an alert for an older payment appearing later; this is disclosed.
Invalid lists are skipped. At 1,000 distinct IDs, payment monitoring and queued
alerts pause visibly rather than evicting IDs and potentially re-alerting.
Stop, Clear and address changes reset the payout opt-in and monitor.

Claude reviewed the implementation. Thirteen alert-model tests passed, including
malformed/oversized lists, first-history exclusion, cooldown grouping, memory
bounds and backfilled history semantics. Chromium at 390/1440px passed payment
opt-in, baseline exclusion, deduplication, grouped alerts, generic notification
content/tag, request counts and clearing; delivery uses a mock Notification API.
Existing dashboard labels/charts also passed after initial integration. Syntax
and whitespace checks passed. No production deployment or native builds/mining.
Network-difficulty alerts remain unfinished.

### Statistics endpoint validation and cache — 2026-10-19

Replaced permissive chart-data casts with strict source consistency checks for
complete, linked windows matching the reported mainnet tip. Numeric data must be
nonnegative safe integers (positive difficulty); unsupported wide difficulty and
bootstrap-marked responses are rejected. Retained the existing route and chart
response fields, adding schema `monzero-chain-charts-v2`.

Private deployment-scoped cache permissions, shared-reader locks, nonblocking
refresh, bounded transport, failure cooldown and remaining browser cache lifetime
are implemented. Failed refreshes do not return stale success. Claude reviewed
the changes; shared-reader concurrency and cache-write/age findings were addressed.
Contract tests cover malformed/partial/reordered headers, link/tip mismatches,
720-header boundaries, bootstrap flags and numeric limits. Eight integration
tests passed with cURL and eight with the forced PHP stream fallback, covering
cache reuse/expiry, permissions, busy/shared locks, corruption/future dates,
negative caching, upstream failure, redirects, oversized responses and methods.

Read-only mainnet sampling validated 720 headers at height 12,524. The local PHP
endpoint returned HTTP 200 with the v2 schema and 720 blocks; the existing mobile
stats page rendered this live-source response without JavaScript errors. This
is not independent consensus validation or a production deployment. Upstream
HTTP trust, archival storage and broader rate controls remain open. No local
mining or builds ran.

### Persistent network observations foundation — 2026-10-19

Added a Python/SQLite collector because the current PHP runtime has no PDO
database drivers. It retains one dated tip observation per minute from the v2
statistics adapter, with strict shape/time checks, fixed sources, bounded child
transport and no source mixing. This is sampled observation history, not a
canonical chain index. It does not yet collect emission, supply, node versions,
node counts or block-interval distributions.

Private storage (0700 directory/0600 database), immediate migration/insert
transactions, consistent export snapshots and atomic per-file JSON publishing
are implemented. All six requested ranges export at most 721 buckets; gaps stay
empty. Exact difficulty extrema, approximate per-observation means, sample/sync
counts and tip-age bounds retain important data limitations. Export-only mode
requires an existing database and opens it read-only, with no source request.

Claude reviewed the foundation and concurrency follow-up. Eighteen tests passed
covering initialization/reopen, backup round trip, overlapping collectors,
source/clock conflicts, minute cadence, malformed inputs, range bounds, exact
extrema, permission/symlink/schema rejection, atomic export, wrong-path protection
and bounded HTTP errors/redirects/oversize/timeout. Two real mainnet observations
were collected through the local preview and exported to
`core/build/network-history-public-20261019`. No continuous collector or production
deployment was enabled. The `/network/` consumer, staleness presentation and
additional analytics metrics remain next work. Operational notes are in
`utils/website/NETWORK_HISTORY.md`. No builds or mining ran.

### Network history browser contract — 2026-10-19

Added the browser-side history contract for all six requested ranges. It checks
source/schema, timestamps, aggregation bucket boundaries, numeric bounds,
exact difficulty extrema, estimated hashrate consistency and synchronization
counts before chart rendering. Missing buckets remain missing and decreasing
heights are permitted. Freshness distinguishes old observations, empty archives
and a browser clock behind the export clock.

Seven focused test groups passed; all six existing real mainnet archive exports
also passed the contract. The test is included in the website runner. Claude's
read-only review is in progress. The visible network page, ongoing collection
and production deployment remain unfinished. No native builds or mining ran.

### Network history page — local preview, 2026-10-19

Implemented `/network/` with six time ranges, individual difficulty/hashrate
points, UTC archive coverage and accessible bucket tables. Missing observations
are not connected. Unsynchronized, stale-tip and future-timestamp observations
are qualified visually and exposed numerically in the table. Unsupported metrics
remain explicitly unavailable. The homepage links to the page without changing
its preferred navigation. Runtime JSON exports remain untracked and the private
archive remains outside the document root.

Claude's browser-contract review identified archive/point freshness mismatches
and floating-point mean edge cases; both were addressed. Eight contract tests
pass. Local Chromium checks passed all six ranges at 390/1440px, overflow checks,
failed-refresh clearing and JavaScript-disabled controls. These browser checks
use existing local exports, not a production deployment. Added hosting cache
revalidation configuration; hosting acceptance and broader malformed/empty/race
browser coverage remain pending. Continuous collection is still not enabled.
No native builds or mining ran.

### Network page acceptance follow-up — 2026-10-19

Apache and Nginx isolated hosting checks now include history JSON revalidation
and pass. Browser acceptance uses temporary databases and exports from the real
collector, with no dependency on a running preview or its archive. Six ranges,
390/1440px layouts, malformed/empty/oversized/outage responses and recovery,
no-JavaScript controls and header clearance pass. The suite is in the runner.

Claude's page review prompted render-error state clearing, calendar bounds,
streamed response-size enforcement, readable horizontally scrollable charts,
explicit highest-bucket-mean values/units, quality text in the table, distinct
outlined quality markers, accessible table/scroll regions and unchanged-status
announcement suppression. Visual inspection caught and fixed inherited header
overlap. Conservative clock mismatch reporting is retained: a clock behind the
export cannot verify freshness. Nine contract tests pass. Fast-switch/timeout
browser scenarios and continuous collection remain open; no production deployment.

### Local network collection timer — 2026-10-19

Added preview-specific systemd user service/timer examples and installed them
locally. Collection runs 60 seconds after completion, with a 60-second service
deadline, private umask and lower CPU scheduling priority. The timer does not
start mining, build code, enable lingering or automatically start the preview.
The archive remains outside the document root with mode 0600. Operations and
stop commands are documented in `utils/website/NETWORK_HISTORY.md`.

The first explicit service invocation and the following scheduled invocation
both exited successfully; the real archive increased from two to four mainnet
observations. The browser displayed recent observations. The public roadmap now
links to network history with local-only status. Browser fixture checks now also
pass pending-range cancellation and timeout/recovery, without waiting on upstream
services. Claude's timer review found no blockers. Added isolated Python startup, more timeout headroom and ignored interrupted-publish temporary files. Worktree removal requires stopping/reconfiguring the timer; this is documented. The preview unit's presence was confirmed with systemctl, contrary to the review's missing-unit concern. Production collection/deployment
and additional network metrics remain unfinished. No builds or mining ran.

### Recent block analytics — implementation under review, 2026-10-19

Added an independent recent-block panel to `/network/`: current chain height,
observed height/time window, timestamp-derived production rate and five interval
distribution bins. The panel explicitly covers up to 720 recent blocks rather
than pretending the historical range selector has complete block archives.
Backwards timestamp intervals are counted/excluded and suppress the rate;
single-block and zero-span windows have no rate. Unknown data remains unavailable.

Four calculation/contract test groups passed, including bin boundaries, malformed
metadata, incomplete windows, backwards clocks and zero spans. Isolated browser
checks passed at 390/1440px with a known 30-block/hour fixture and outage recovery.
A real mainnet preview returned 720 blocks at chain height 12,558, with 719 valid
intervals, without mobile overflow. Claude's read-only review is still running.
Historical block distribution/production archives, emission and node metrics
remain unfinished. No production deployment, builds or mining ran.

### Recent block analytics review and verification — 2026-10-19

Claude's review is complete. The production rate now explicitly uses the first
and last timestamps; internal backwards steps are counted separately rather than
silently preventing an endpoint estimate. Zero/nonpositive spans remain
unavailable. The page explains that miner-set timestamps and excluded backwards
steps can bias the distribution; syncing-node and future-tip warnings appear
beside the figures. Unused mean/maximum calculations were removed.

Added the interval histogram with exact counts/percentages in its accompanying
accessible table. Six calculation tests pass, including the complete 720-block
window above genesis and calendar/type boundaries. Desktop/mobile browser checks
pass known histogram values, syncing/future-tip warnings and outage/recovery.
The real mainnet histogram was visually inspected. The public roadmap records
this recent-window scope, not historical block analytics completion. No native
builds, mining or production deployment ran.

### Community hub — local implementation, 2026-10-19

Added `/community/` with the owner-supplied Telegram group, existing official
repository, roadmap/source-update links, contribution routes, security disclosure
instructions and mining/network resources. The homepage links to the hub without
changing its navigation. Unknown Bitcointalk/social URLs are explicitly absent;
no independent announcements feed or funded bounty claims were invented. Voting,
bounties and badges remain planned, with submissions closed pending their controls.

The static page needs no JavaScript. Desktop/mobile checks verify layout, header
clearance and keyboard access; local resource links are checked against the preview.
Claude's read-only review is pending. This page does not complete the community
platform or publish anything to production. No builds or mining ran.

### Community hub review follow-up — 2026-10-19

Claude reviewed the hub and confirmed the listed Telegram/repository URLs match
the established homepage links and contribution/security guidance. Changed the
future-feature heading to Planned, stated moderation/authentication/abuse-control
prerequisites, removed an unsupported translation-process implication, and added
current-page navigation. The hub and network stylesheet links are absolute and
versioned for cache refresh. Other review suggestions were stylistic; no new
external official accounts or release claims were inferred.

Visual inspection exposed inherited mobile navigation positioning over content
on both the hub and network pages. Scoped static navigation fixes now pass at
390/1440px; network browser acceptance explicitly checks navigation clearance.
The hub passes no-JavaScript layout, keyboard skip-link and eleven local-route
checks. The public roadmap records the hub's local-only implementation scope.
Production publishing and the interactive community platform remain unfinished.

### Integrated website regression — 2026-10-19

The complete `tests/website/run.sh` finished with exit 0 after the network and
community integration. Evidence is in
`core/build/website-network-community-regression-20261019.log`. Coverage includes
calculator/browser cases; node observation contracts with both PHP transports;
pool adapter, worker labels, session charts and alerts; benchmark contracts and
browser behavior; statistics contracts/cache and historical collector tests;
network history and recent-block calculations/browser error recovery.

Shared navigation acceptance now includes `/community/` and `/network/`, checks
their logo and navigation clearance, and passes all fourteen routes at desktop,
mobile, and mobile with JavaScript disabled. This protects against the inherited
mobile-positioning regression found during visual inspection. These results do
not establish production hosting/deployment or completeness of later releases.
No native builds or mining ran.

### Network difficulty session alerts — implementation under test, 2026-10-19

Added an opt-in difficulty monitor to the network page. It compares fresh,
synchronized tip difficulty with the first qualifying observation after enabling.
Two spaced observations confirm a threshold crossing; duplicates, backwards
clocks, stale/future observations and syncing nodes cannot confirm a change.
The fixed baseline and event list are memory-only. Alerts latch while a condition
persists, rearm after recovery and have a ten-minute cooldown. Stop clears state.
While enabled, the visible page refreshes recent blocks once per minute; there
are no background or operating-system notifications.

Six focused model tests pass and existing recent-block model tests still pass.
Browser opt-in/confirmation/clear acceptance passed at 390/1440px, including a known 20% increase and the minute refresh timer. The fixture clock is installed before page load so existing timers are controlled. Claude's review remains in progress.
This work is not yet claimed as a completed public roadmap milestone. No builds,
mining or production deployment ran.

### Difficulty alert review follow-up — 2026-10-19

Claude reviewed the model and browser integration. Added spacing checks against
both source observation time and browser monotonic time; rapid opposite-direction
samples now break pending confirmation. Rejected observations explain clock skew,
stale tips, syncing and lookup failures. Strict clock checking is retained with
an explicit reason. The wording distinguishes repeated observations of one tip
from new-block confirmations and explains delays during normal long block gaps.

The threshold is locked while enabled and displayed in the active status. Enable
during an older request schedules a fresh request after that request completes;
old epochs still cannot seed a monitor. Automatic refresh avoids clearing the
previous display or announcing Loading on every poll. Unchanged alert status is
not rewritten. Nine focused model tests and the desktop/mobile browser suite
pass, including opt-in, threshold locking, confirmation and clearing. Dedicated
pending-request/visibility alert scenarios remain additional acceptance work.
The public roadmap records local session-alert scope, not background delivery or
production deployment. No builds or mining ran.

### Difficulty alert request/visibility acceptance — 2026-10-19

Extended the network browser suite with held-response scenarios at 390/1440px.
Enable during an existing request waits for a new request before establishing
a baseline. Stop/re-enable excludes the prior session's response; Stop during a
request leaves monitoring off when it completes. Tests use distinct difficulty
values to prove that the correct response establishes each baseline.

A simulated document visibility signal verifies that automatic timers issue no
requests while hidden and resume while visible. This is deterministic browser
logic coverage, not operating-system background lifecycle testing. All scenarios
passed alongside the existing range, outage, timeout and alert checks. No product
changes were needed. No builds, mining or production deployment ran.

### Bounty board contract — implementation started, 2026-10-19

Added the bounty catalog model with required category, task description,
difficulty, acceptance criteria, submission/discussion instructions, maintainer,
reviewer and status fields. Rewards use exact decimal-string XMZ atomic units.
Funded/paid claims require dated funding evidence; completed tasks require
completion evidence and paid tasks additionally require payment evidence.
These checks validate record consistency, not independent proof of custody or
payment. Maintainer review remains necessary and no automated payouts exist.

The real catalog is empty: no tasks, rewards or funding claims were fabricated.
Five focused test groups pass, including missing evidence, conflicting statuses,
invalid dates/URLs, duplicate IDs and maximum atomic-amount precision. Tests are
included in the website runner. Claude's contract review is pending. The board
UI and authenticated moderation/publication workflow remain unfinished; no public
roadmap completion claim is made. No builds, mining or deployment ran.

### Bounty board interface — local draft, 2026-10-19

Implemented the read-only board at `/community/bounties/` with category/status/
funding filters, search, twenty-record pagination, exact XMZ reward display and
separate funding/completion/payment evidence links. All record text uses DOM text
nodes, not HTML interpolation. The bounded catalog fetch clears failed data and
distinguishes unavailable from an empty catalog. The real catalog remains empty.

Local desktop/mobile checks passed empty and outage states, navigation clearance,
no horizontal page overflow and disabled controls without JavaScript. Populated
fixture/filter/pagination browser acceptance is still pending. Claude's contract
review completed without blockers but identified evidence-date/status and input
coverage improvements to address before publishing reviewed listings. Authenticated
moderation and public submissions remain unfinished. No deployment, builds or
mining ran; no public-roadmap completion claim is made.

### Bounty contract review fixes — 2026-10-19

Added required completion/payment check dates, future-date rejection, exact field
allowlists, surrogate/line-separator rejection and multiline prose support.
Cancelled tasks cannot retain a funded label. Evidence dates are displayed beside
the links. The actual empty catalog is validated by tests and fixture records
are rejected in that production-catalog check. Seven test groups pass.

Retained uint64 atomic precision rather than treating MONEY_SUPPLY as a proven
lifetime cap: the core reward code also applies FINAL_SUBSIDY_PER_MINUTE. A URL
or reviewer name remains evidence to inspect, not automated proof of funding or
separate-person review. Arbitrary HTTPS evidence hosts are still allowed for
reviewed records; no automated fetching occurs. Further status/URL branch tests,
populated browser acceptance and authenticated moderation remain outstanding.
No builds, mining or deployment ran.

### Bounty populated-browser acceptance — 2026-10-19

Added an isolated browser fixture suite without modifying the real empty catalog.
At 390/1440px it verifies twenty-item pagination, category/status/funding/search
filters, exact atomic rewards, evidence links, literal rendering of HTML-like
text, empty/malformed/outage states and recovery, navigation clearance and
no-JavaScript disabled controls. The suite passes and is in the website runner.

Nginx now explicitly revalidates the bounty catalog; the existing Apache catalog
rule already covers its filename. Nginx and Apache hosting checks pass. Claude's
UI review is running. No reviewed tasks or funded rewards have been published;
authenticated moderation and submission workflows remain unfinished. No native
builds, mining or production deployment ran.

### Bounty board additional validation — 2026-10-19

Eight contract test groups now pass, including remaining conflicting status/
evidence combinations, invalid discussion links, currency/date mismatches and
catalog bounds. The community hub links to the local read-only board while
explicitly stating that its catalog is empty and submissions are closed. Mobile
visual inspection confirmed usable filters and clear empty/funding wording.
The board has been added to shared navigation acceptance; that run and Claude's
UI review are still in progress. No deployment, native builds or mining ran.

### Bounty UI review fixes — 2026-10-19

Claude's UI review completed. Fixed long-token mobile overflow and pagination
focus: the first newly revealed task receives focus. Refresh now uses aria-disabled
with the existing busy guard so the focused control is not removed from keyboard
navigation. Browser fixtures include long titles/criteria and pagination focus;
checks pass at both widths. All fifteen shared-navigation routes also passed.

Future catalog dates now produce a specific clock/catalog-date explanation
rather than an outage claim; strict date validation remains. Evidence checked-at
dates are review dates, not payment/completion event dates, so a chronological
ordering rule was not inferred from them. Eight contract groups pass. Additional
paid/completed rendering and transport/focus edge coverage remain pending.
No production deployment, builds or mining ran.

### Read-only bounty board verification checkpoint — 2026-10-19

Completed the remaining focused browser cases: completed/paid fixture listings
render distinct dated evidence links; oversized responses and timed-out requests
clear listings; refresh retains keyboard focus while pending and after timeout;
a subsequent successful refresh recovers. Desktop and mobile runs pass. The
fixtures remain isolated from the real empty catalog.

The read-only board, contract and tests are ready as a local implementation
checkpoint. The public roadmap explicitly distinguishes this from authenticated
moderation, submissions and payout operations, which are not enabled. Eight
contract groups, populated browser acceptance, fifteen-page navigation and
Apache/Nginx hosting checks have passed. Claude's contract and UI reviews were
reconciled as recorded above. No production deployment, native builds or mining.

### Developer portal — initial local documentation, 2026-10-19

Added `/developers/` with source/protocol links and implementation-derived recent
block/history contracts, local curl example, caching/freshness/error handling and
source limitations. The homepage links to the portal. Proposed versioned API,
explorer/pool API support and wallet/payment examples are explicitly unfinished;
no browser wallet or unverified network endpoints were introduced.

Desktop/mobile no-JavaScript layout and navigation clearance checks passed.
Claude's factual review against the adapter/collector sources is pending. This
is an initial portal, not completion of the developer platform or a deployed API.
No native builds, mining or production deployment ran.

### Pool adapter developer documentation — 2026-10-19

Expanded the portal from the actual pool adapter/normalizer source: POST shape,
2 KiB limit, same-origin browser boundary, lexical-only address checks, exact
11-decimal XMZ atomic strings, nullable observations, connection-label semantics,
pool-sent versus confirmed payments, privacy implications and current throttling/
error responses. The example requires a caller-supplied public mining address
and is not executed by the page. The documentation distinguishes the existing
site adapter from a versioned supported API.

Desktop/mobile no-JavaScript checks pass after the addition. Claude's initial
network-contract review remains in progress. Explorer/RPC and wallet/payment
integration examples, versioned APIs and production deployment remain unfinished.
No builds, mining or external messages ran.

### Developer portal review and explorer reference — 2026-10-19

Claude's network-contract review completed; corrected synchronization semantics,
the history sources array and sampled-tip wording, and made preview-to-public-node
requests explicit. Verified the transaction-count field uses blk.tx_hashes.size()
in the core RPC source, excluding the miner transaction.

Added the existing explorer action reference directly from its switch/validation
logic, including newest-first headers, bounded asset search and ambiguous
unsupported/outage fallback. The portal explicitly distinguishes this legacy
presentation adapter from a hardened versioned API. Pool contract details were
checked against its adapter and normalizer; neither example runs automatically.
All sixteen shared-navigation routes pass desktop/mobile/no-JavaScript checks.
The public roadmap records the initial portal scope. Full RPC documentation,
wallet/payment examples, versioned APIs and production deployment remain open.
No builds, mining or production changes ran.

### Explorer asset outage semantics — implementation under review, 2026-10-19

Removed the catch-all successful empty/unsupported fallback from the asset-list
adapter. RPC errors and malformed registry envelopes now return unavailable;
valid empty registries still succeed. The frontend refuses legacy ambiguous
responses instead of inferring activation state or zero assets. Updated the
portal to describe the local behavior.

Isolated actual-PHP checks pass method-not-found, upstream failure, missing fields,
invalid activation type and a valid empty registry. PHP/JS syntax passes; the
checks are included in the website runner. Claude's review and browser-level
outage wording acceptance remain pending. This does not complete general
explorer transport/input hardening or the versioned API. No native builds,
mining or production deployment ran.

### Explorer asset-list review follow-up — 2026-10-19

Claude confirmed the outage fallback was removed and identified remaining
consumer certainty issues. The explorer now titles registry failures unavailable,
not Nothing found, and makes successful empty/inactive messages node-reported.
Studio resets activation to Unknown after lookup failure. Script cache versions
were bumped. The isolated upstream test asserts URL replacement before execution
so it cannot silently reach the public node after a source URL change.

Desktop/mobile browser checks distinguish HTTP failures, legacy ambiguous 200
responses and valid empty registries; no page errors or horizontal overflow.
Actual-PHP fixture checks pass and assert failure responses contain none of the
supported/active/count/list fields. General input/transport hardening, individual
record validation, single-asset/hash-search failure semantics and dedicated Studio
browser acceptance remain follow-up work. No builds, mining or deployment ran.

### Single-asset lookup failure semantics — 2026-10-19

The single-asset action now validates both registry and output pages with the
same envelope rules as the list (status, activation type, bounded total, exact
page length, 64-hex record identities) and requires consistent activation
observations. A miss inside a truncated 1000-record window returns 503 (existence
unknown) instead of a false 404. Field names and the page-length rule were checked
against `COMMAND_RPC_GET_ASSETS`/`COMMAND_RPC_GET_ASSET_OUTPUTS` and
`on_get_assets` in the core source. Actual-PHP fixture checks cover malformed,
busy, inconsistent-activation and valid empty output pages; full website runner
passes. No builds, mining or deployment ran.

### Payment request tool and merchant guide — 2026-10-19 (Claude)

Owner asked Claude to continue the plan (web wallet still excluded). Added
`/payments/request/`: in-browser address validation mirroring
`get_account_address_from_str` (Monero-style base58, original Keccak-256 checksum,
mainnet/testnet/stagenet standard/integrated/subaddress prefixes 86–88/111–113/
131–133, exact key length, canonical ed25519 `check_key` decompression), amounts
per `parse_amount`/`print_money` (11 decimals, uint64 bound), and `monzero:` URIs
per `make_uri`. Text fields escape every reserved byte because the wallet's own
encoder leaves `=`/`?` unescaped and its parser then rejects them. Payment IDs
appear only inside integrated addresses; name/description are labelled as
payer-wallet notes, not on-chain references. Self-contained QR encoder (byte mode,
level M, v1–40) with SVG/PNG download, copy and Web Share. No network requests,
storage, keys or signing.

Verification: Keccak vectors match pycryptodome; wallet-generated vectors from a
throwaway offline `monzero-wallet-cli` (release-v1 host build) for primary,
subaddress and integrated addresses; generated URIs (including `= ? / + %`, UTF-8
and the uint64 maximum) were parsed exactly by offline `monzero-wallet-rpc`
`parse_uri`, and `make_uri` output matched byte-for-byte. QR output decodes with
zbarimg at every version 1–40; the browser test scans the on-page QR and the
downloaded PNG. Desktop/mobile/no-JS and 18-route navigation pass.

Added `/developers/payments/`: view-only wallet, loopback wallet RPC with digest
login, per-invoice `create_address`, `make_uri`, `get_transfers` confirmation
tracking (pool vs in, double_spend_seen, 10-block spendable age, reorg recheck),
expiry/late payments and HMAC callback verification. Flags/methods checked in
source; create_address/make_uri/digest-401 exercised offline. `get_transfers`
needs a daemon and was verified from source only. Homepage, portal and roadmap
link both pages. No builds, mining or deployment ran.

### Exchange directory, listing tracker and markets — 2026-10-19 (Claude)

Added `/exchanges/` backed by a reviewed `catalog.json` (`monzero-exchanges-v1`)
and a fail-closed validator. Statuses follow the brief (planned, application
submitted, under review, approved, live, suspended). Venue fields (pair, official
HTTPS URL, deposit/withdrawal/trading state, last-verified date, verification
link) are required for live/suspended and forbidden before; applications need
dates; a listing fee needs a source link; no price or volume fields exist.
Production data: one record, Biconomy, Planned, no application date, fee not
published, $15,000 target linked to live `/fund/` progress. Sources: the
published fund page goal and `outreach/listing/README.md` (application not
submitted). No live venue is claimed. Updates are maintainer-reviewed catalog
edits until the authenticated admin system exists.

`/markets/` shows an explicit unavailable state: no verified venue, so no
price, change, volume, depth or spread; no synthetic data. Unit tests cover the
production catalog and the status, venue, fee, link and duplicate rules. A
browser test covers the real tracker, a fixture live venue (literal text,
noopener), and invalid/outage clearing at 390/1440px. Navigation passes on 20
routes. No deployment.

### Ecosystem directory — 2026-10-19 (Claude)

Added `/ecosystem/` from a reviewed `catalog.json` (`monzero-ecosystem-v1`):
search, category (the brief's eight) and operator filters. Every entry is
labelled project-operated or third-party; third-party entries must use external
HTTPS URLs, and exchanges are rejected here because they belong to the dated
exchange tracker. Ten entries come only from links the site already publishes:
pool, wallets, explorer, network history, source, merchant guide, whitepaper,
mining guide, Telegram and the third-party Chainquiry listing. Submissions go
through GitHub issues with maintainer review until authenticated moderation
exists. Unit and browser tests (filters, labels, noopener, outage clearing,
390/1440px) pass. Linked from the homepage. No deployment.

### Read-only API v1 — 2026-10-19 (Claude)

Added `/api/v1/` as directory `index.php` endpoints (same hosting pattern as
`/api/node-info/`, so no rewrite rules are needed): network stats/hashrate/
difficulty, blocks/latest (count 1–30), blocks?height=N, mining/pools,
mining/benchmarks, exchanges, ecosystem. `lib.php` refuses direct requests and
provides: a fixed method allowlist (get_info, get_last_block_header,
get_block_header_by_height, get_block_headers_range) against the configured
public node with 1 MiB bounds, 2s/5s timeouts and no redirects; strict
GET/HEAD/OPTIONS handling; rejection of unknown or array query parameters; one
JSON envelope and error shape; CORS `*` without credentials; nosniff; 15-second
private file caches under fixed names. Rate limit: 60 per client and 1200 total
per minute, keyed by HMAC with a per-window salt so no IP is stored. Headers are
normalised (amounts and difficulty as strings; nonce/pow hash dropped). The
observation is refused unless the network is mainnet and the tip matches; latest
windows must be contiguous, prev-hash linked and end at the tip; deep blocks
cache longer. Roadmap and transaction endpoints are not included; the docs say so.

Tests use the actual PHP against a fixture node (the URL replacement is asserted
first, so the public node is never reached): envelope, cache reuse, ranges,
400/404/405, testnet/outage/broken-link refusal (502, no partial data, no-store),
429 with Retry-After, no stored IPs. Docs at `/developers/api/`; portal, homepage
and roadmap updated. All new pages were checked under the production `.htaccess`
CSP with zero violations. 22-route navigation and the full runner pass. No
deployment.

### Opt-in mining leaderboard — 2026-10-19 (Claude)

Added `/mining/leaderboard/` over the existing `/api/miner-stats/` GET (no
backend change). It ranks opted-in miners active in the last 3 minutes by
reported hashrate and by reported blocks, top 50 each, under the service's
existing HMAC pseudonyms; responses with any non-pseudonym name are refused.
Blocks come from each reporter's local log count (`utils/monzero-miner-reporter.py`)
and are labelled as possibly including orphans and resetting with the log.
Uptime and weekly/monthly boards are shown as unavailable: the service keeps
only each miner's latest record (deleted after 7 days), so building them needs
an opt-in history design that changes the ingest service, which is an owner
decision. Opt-out is explained. Unit and browser tests cover rankings, the cap,
zero-block exclusion, and empty/invalid/outage states. Navigation passes. No
deployment.

### Faucet architecture and marketplace specification — 2026-10-19 (Claude)

Added `docs/FAUCET_ARCHITECTURE.md`: claim endpoint, private claims store,
payout worker under a separate OS user, and a loopback hot wallet. It covers
anti-bot checks, per-address/client/day limits, treasury float and reserve,
an append-only log, a pause flag read by both parts, configuration outside the
document root (default disabled) and an activation checklist (owner approval,
tests, a week on testnet, security review, a small float). Implemented only a
`/faucet/` page (Status: paused, no form) and `GET /api/faucet/`, which can
only return paused. It reads no config, has no wallet access and refuses POST.
Not implemented on purpose: the claim endpoint, payout worker, wallet and
anti-bot provider; these need owner approval and funding.

Added `docs/MARKETPLACE_SPEC.md`: a non-custodial catalog and order
bookkeeping. Merchants receive payment directly via per-order subaddresses from
their own view-only wallet; "paid" is reported by the merchant through a signed
callback; disputes affect only reputation and listing; no escrow or custody.
Legal, moderation and fraud risks plus dependencies are listed. Tests: faucet
status contract and page checks; 24-route navigation. No deployment.

### Invite-only administration — 2026-10-21 (Claude)

Owner request: `security@monzero.org` is the owner; the owner approves other
admins and the rights they may pass on; everyone else joins by invite only.
Added `/admin/` (PHP + SQLite outside the document root at
`~/monzero-private/admin.sqlite`; the production host has PHP 8.3, pdo_sqlite and
sodium). Owner created only by the CLI `admin/bootstrap.php`, which refuses a
second owner and emails a one-time 48-hour setup link. No password is ever
emailed; the owner sets it. Owner invites are emailed immediately. Invites
from admins holding "Invite admins" wait for owner approval and may grant
only a subset of the inviter's permissions. The owner can change permissions,
disable or enable, revoke and resend; the owner row cannot be changed from the
web. Security: Argon2id; 12-character minimum; per-account (5) and per-client
(20) failure throttling per 15 minutes; a dummy-hash verify for unknown
accounts; `__Host-` Secure HttpOnly SameSite=Strict cookies over HTTPS; hashed
session tokens with 30 min idle / 8 h maximum; per-session CSRF plus an Origin
check; single-use hashed link tokens; optional TOTP (RFC 6238, QR rendered
locally); no-store, no-referrer and noindex headers; an append-only audit table
enforced by triggers; lib/bootstrap return 404 over HTTP; email links use a
fixed base URL, never the Host header.

Tests (`tests/website/test_admin.py`, run on PHP 8.3 in the local php:8.3-cli
image because host PHP lacks pdo_sqlite; `run.sh` reports SKIPPED when it is
missing) cover the whole flow including throttling, TOTP, disable/logout,
audit immutability and that no password appears in mail. Pages showed zero CSP
violations. Content-editing modules are not built yet; the overview says so.

### Country-level node map — 2026-10-20 (Claude)

Owner rule: nodes are shown by country only, never by region, city or location.
`utils/nodemap/node_census.py` runs on monzero-eu next to the node. It reads the
node's own `get_peer_list` (white list, last seen within 24 hours = accepting
connections) and `get_connections` over the private loopback RPC, drops
non-global addresses (private, CGNAT, loopback, link-local, documentation, Tor/I2P
hosts), maps each IP to a country with the offline DB-IP "IP to Country Lite"
database (CC BY 4.0, refreshed monthly, about 38 MB peak memory) and sends only
per-country `observed` / `reachable` / `connected` counts. IPs are never written to
disk and never leave the node. The website ingest `/api/node-census/` takes an
HMAC-signed request (timestamp ±300 s, single-use nonce), refuses extra keys,
wrong sums, lowercase codes and censuses older than the stored one, and keeps the
latest snapshot plus one per UTC day (400 days) in `~/monzero-private/node-census/`.
Read API `/api/v1/network/nodes/` (optional `?history=daily`); page
`/network/nodes/` shades a Natural Earth 1:110m country map (built once with
`utils/nodemap/build_world_svg.py`; small countries appear in the table only) and
lists every country, with one-vantage-point and lookup-accuracy caveats. Software
versions are not exposed by the peer list and are not shown. Tests:
`tests/website/test_node_census.py` (aggregation, filtering, signature, replay,
ordering, API, no stored IPs, browser under the production CSP at 390/1440 px).
Deployment: upload the website files, then `bash utils/nodemap/deploy-eu.sh`.

### Navigation submenus — 2026-10-20 (Claude)

Owner request: make every new page reachable from the header, with submenus on
hover. The owner's twelve top-level links stay exactly as they were; six of them
gain a submenu (Explorer: explorer, network history, node map; Stats: stats,
markets, exchanges; Public wallets: wallets, payment request; Roadmap: roadmap,
community, bounties, ecosystem; Whitepaper: whitepaper, developers, API, Accept
XMZ; Mining: how to mine, calculator, your mining, benchmarks, leaderboard,
faucet). Desktop: hover, keyboard focus or the ▾ button opens a group; Escape
closes it. Mobile Menu: ▾ expands a group in place; without JavaScript the groups
are expanded. The Menu-button breakpoint moved from 1100 px to 1340 px because the
▾ buttons widen the row. `utils/website/nav_submenus.py` adds the submenus to the
existing anchors (idempotent, `--check` in the runner) and writes
`lib/site-nav-submenus.json`, which the faucet's PHP header reads. Navigation
checks: 26 pages at 1440/1300/390 px with and without JavaScript, every route
reachable from every page, hover/click/Escape/keyboard/mobile expand.

### Service status and owner alerts — 2026-10-20 (Claude)

`/status/` and `GET /api/status/` show seven checks: public node (tip under 30 min,
synchronized), mining pool (answers, same height), faucet (worker heartbeat within
10 min, not halted, at least two days of funds at the daily cap), node map census,
network history, and check-ins from the EU and US nodes. The faucet worker now
sends a signed `heartbeat` every cycle with its balance (and when it halts).
`utils/website/status_ping.py` runs every 10 minutes on both nodes
(`deploy-status-ping.sh`); each signed check-in re-evaluates the checks and emails
the owner (`~/monzero-private/status-config.php`, default security@monzero.org)
only when a check changes state or stays bad for a day. Public output has no
secrets, addresses or member data. Tests: `tests/website/test_status.py`.
