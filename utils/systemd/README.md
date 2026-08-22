# Monzero systemd service

The unit runs `monzerod` as a dedicated, unprivileged `monzero` account. It
keeps chain state in `/var/lib/monzero`, logs in `/var/log/monzero`, and reads
operator-reviewed settings from `/etc/monzero/monzerod.conf`.

Create the system account and configuration directory before enabling it:

```bash
sudo useradd --system --home-dir /var/lib/monzero --shell /usr/sbin/nologin monzero
sudo install -d -o root -g monzero -m 0750 /etc/monzero
sudo install -o root -g monzero -m 0640 monzerod.conf /etc/monzero/monzerod.conf
sudo install -o root -g root -m 0644 monzerod.service /etc/systemd/system/monzerod.service
sudo systemctl daemon-reload
sudo systemctl enable --now monzerod.service
```

The production configuration must explicitly review P2P/RPC bind addresses,
restricted RPC, authentication, public ports, seed or priority nodes, pruning,
and log retention. Never expose unrestricted wallet or daemon RPC to the
internet. Confirm `status`, `get_info`, peer counts, synchronization, and an
empty-directory sync before promoting a node.
