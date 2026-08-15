# Monzero public repository setup

Three Monzero-owned repositories are required before public reproducible builds:

| Repository | Purpose | Initial local source |
| --- | --- | --- |
| `monzero-core` | Node, wallet CLI, consensus code and release tooling | `/home/pinhead/Projects/Monero-Fork-backups/git-remotes/monzero-core.git` |
| `monzero-gui` | Desktop GUI | `/home/pinhead/Projects/Monzero-Fork-backups/git-remotes/monzero-gui.git` |
| `monzero-gitian-sigs` | Independent reproducible-build assertions and builder public keys | `/home/pinhead/Projects/Monzero-Fork-backups/git-remotes/monzero-gitian-sigs.git` |

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

## Publishing the prepared repositories

After creating empty public repositories, replace the example URLs and push:

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
MONZERO_GITIAN_SIGS_URL=https://HOST/MONZERO_ORG/monzero-gitian-sigs.git \
  contrib/gitian/gitian-build.py --setup --docker \
  --url https://HOST/MONZERO_ORG/monzero-core.git BUILDER RELEASE
```

Asset/NFT consensus functionality remains inactive throughout repository and
release setup. Its activation requires the separate review and public-testnet
gates in `MONZERO_PHASE0_STABILIZATION.md`.

