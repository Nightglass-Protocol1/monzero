# Monzero security policy

## Reporting a vulnerability

Report suspected vulnerabilities privately to
[`security@monzero.org`](mailto:security@monzero.org). Do not open a public
issue until the report has been assessed and a coordinated disclosure date has
been agreed.

Include the affected commit or release, operating system, impact, reproduction
steps, and the smallest safe proof of concept needed to demonstrate the issue.
Do not send wallet seeds, private keys, passwords, personal data, or live funds.
Email is not end-to-end encrypted until a dedicated security OpenPGP key is
published.

The project aims to acknowledge a report within seven calendar days, provide a
status update within fourteen days, and coordinate disclosure after a fix is
available. A 90-day disclosure window is the default target, but urgent active
exploitation or complex consensus changes may require a different schedule
agreed with the reporter. Good-faith reports will be credited unless the
reporter asks to remain anonymous.

## Scope

Reports concerning Monzero consensus, networking, wallets, release packages,
the website, explorer, and official deployment configuration are in scope.
Upstream Monero services, third-party exchanges, mining pools, hosting
providers, and user-operated infrastructure are outside the project's control;
report those issues to their respective operators.

Genesis pre6 is experimental, unsigned, and unaudited. This policy establishes
a private reporting channel; it does not change the release's prerelease status
or imply that remaining production gates have passed.
