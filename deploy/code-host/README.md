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

`nginx-app.monzero.org.conf` separately serves the static Studio beta from
`/var/www/monzero-app` and exposes only the daemon's restricted `get_info`
method through a same-origin status endpoint. Token, NFT, collection, and swap
submission controls remain disabled until reviewed consensus and wallet RPC
support exists.
