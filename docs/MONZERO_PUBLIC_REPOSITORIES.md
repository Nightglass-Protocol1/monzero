# Monzero source distribution

The former Monzero code-host deployment has been retired. There is currently
no canonical public Git clone URL for Monzero Core, Monzero GUI, or the Gitian
signature repository. Do not advertise an unofficial mirror as authoritative.

Until a maintained public forge is selected, prerelease source should be
distributed as a versioned archive together with its checksum and signed
release manifest. Recipients should verify those artifacts before building.
The local bare repositories remain development backups, not public release
channels.

Before publishing a replacement forge:

- establish a project-owned organization with multifactor authentication and
  at least two owners;
- protect the release branch against force pushes and deletion;
- require passing build checks and independent review;
- publish annotated, signed release tags;
- verify a clean recursive clone, including the GUI core submodule; and
- keep human Gitian signing keys outside automated workflows.

At least two independently administered builders should reproduce Linux and
Windows artifacts before they are described as verified. Asset/NFT consensus
activation additionally remains subject to the review and public-testnet gates
in `MONZERO_PHASE0_STABILIZATION.md`.
