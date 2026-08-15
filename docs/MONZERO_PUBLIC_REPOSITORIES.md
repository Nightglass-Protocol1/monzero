# Monzero public repository setup

Three Monzero-owned, read-only public repositories are deployed at
`https://code.monzero.org`:

| Repository | Purpose | Initial local source |
| --- | --- | --- |
| `monzero-core` | Node, wallet CLI, consensus code and release tooling | `/home/pinhead/Projects/Monero-Fork-backups/git-remotes/monzero-core.git` |
| `monzero-gui` | Desktop GUI | `/home/pinhead/Projects/Monzero-Fork-backups/git-remotes/monzero-gui.git` |
| `monzero-gitian-sigs` | Independent reproducible-build assertions and builder public keys | `/home/pinhead/Projects/Monzero-Fork-backups/git-remotes/monzero-gitian-sigs.git` |

Public clone URLs:

- `https://code.monzero.org/monzero-core.git`
- `https://code.monzero.org/monzero-gui.git`
- `https://code.monzero.org/monzero-gitian-sigs.git`

The VPS publishes source browsing through Cgit and cloning through Git smart
HTTP. HTTP redirects to HTTPS, certificate renewal is enabled and tested, and
HTTP write routes are deliberately absent. The repositories retain local
backup `origin` remotes and use `public` for this read-only deployment.

Do not publish these under an individual contributor's account if a Monzero
organization is intended. Create the organization first, enable multifactor
authentication for owners, and retain at least two organization owners.

## Repository controls

Protect `main` in all three repositories:

- disallow force pushes and branch deletion;
- require pull requests and at least one independent approval;
- require passing test/build checks;
- require conversation resolution;
- restrict direct pushes to release administrators;
- enable secret scanning and dependency alerts where the host supports them.

Core release tags should be annotated and signed. Do not allow an automated
workflow to possess a human builder's private Gitian signing key.

## Publishing updates

The public service is intentionally read-only. Commit and push to each local
backup `origin`, then deploy its bare mirror to `/srv/git` over the restricted
administrator SSH connection. Do not expose `git-receive-pack` through Nginx.

The following is retained as the future migration pattern if the projects move
to a hosted forge with protected write access:

```bash
git remote set-url origin https://HOST/MONZERO_ORG/monzero-core.git
git push origin fork/main:main
git push origin monzero-phase0-assets-prototype-20260815

git -C monzero-gui remote set-url origin https://HOST/MONZERO_ORG/monzero-gui.git
git -C monzero-gui push origin main
git -C monzero-gui push origin monzero-gui-phase0-20260815-r1

git -C /home/pinhead/Projects/monzero-gitian-sigs remote set-url origin \
  https://HOST/MONZERO_ORG/monzero-gitian-sigs.git
git -C /home/pinhead/Projects/monzero-gitian-sigs push origin main
```

Before changing the local `origin` URLs, retain the local bare remotes as a
separate `backup` remote. Never change or push to the repositories named
`upstream`; they are retained solely for attribution and controlled upstream
comparison.

Update `monzero-gui/.gitmodules` to the final public core URL (or a correct
relative sibling URL), commit that change, and verify a clean recursive clone.

## Signing bootstrap

Each independent builder creates their own signing key on a trusted machine,
publishes only the public key in `monzero-gitian-sigs/gitian-pubkeys/`, and has
its complete fingerprint verified out of band by another maintainer. At least
two independently administered builders must reproduce Linux and Windows
artifacts before those artifacts are marked verified.

The Gitian command requires an explicit source repository:

```bash
MONZERO_GITIAN_SIGS_URL=https://code.monzero.org/monzero-gitian-sigs.git \
  contrib/gitian/gitian-build.py --setup --docker \
  --url https://code.monzero.org/monzero-core.git BUILDER RELEASE
```

Asset/NFT consensus functionality remains inactive throughout repository and
release setup. Its activation requires the separate review and public-testnet
gates in `MONZERO_PHASE0_STABILIZATION.md`.
