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
