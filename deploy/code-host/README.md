# code.monzero.org deployment

This configuration publishes read-only source browsing and Git clones from
`/srv/git` on the Monzero VPS. Administrative pushes remain restricted to SSH.
It does not change the Monzero daemon service or ports.

The deployed repositories are mirrors of the local recovery remotes:

- `monzero-core.git`
- `monzero-gui.git`
- `monzero-gitian-sigs.git`

Nginx exposes only `git-upload-pack`; it intentionally has no
`git-receive-pack` route. After deployment, Certbot upgrades the virtual host
to HTTPS and UFW admits ports 80 and 443.

