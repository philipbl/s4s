# Science for Solutions website

Jekyll site served at <https://aq.byu.edu>. Run `make help` to list every command.
`make` alone previews the site at <http://localhost:4000>.

## Deploying

- Pushing to `main` builds and deploys automatically (`.github/workflows/deploy.yml`).
- `make deploy` does the same from this computer. Run `make deploy_dry_run` first
  to see what would change.

Deploys `rsync --delete` the built `_site/` into the web root, so anything else
put in that folder on the server gets deleted on the next deploy.

GitHub Actions logs in with its own SSH key, stored as the `DEPLOY_SSH_KEY`
repo secret. On the server, that key's line in `~/.ssh/authorized_keys`
(comment `s4s-github-actions-deploy`) starts with
`command="/usr/bin/rrsync -wo /home/philipbl/aq.byu.edu",restrict`. That means
the key can only upload into the web root: no shell, no downloads, no other
folders. Paths are relative to the web root, which is why the workflow deploys
to `philipbl@aq.byu.edu:`.

To replace the key:

1. Generate a new one with
   `ssh-keygen -t ed25519 -N "" -C s4s-github-actions-deploy -f s4s_deploy`.
2. Swap the public key into that `authorized_keys` line, keeping the prefix.
3. Run `gh secret set DEPLOY_SSH_KEY < s4s_deploy`.
4. Delete both local files.

## Server (`ssh aq.byu.edu`)

Ubuntu 22.04. Nothing below is in this repo: it all lives on the server, and
changing it needs `sudo`.

| What | Where |
|---|---|
| Web root (deploy target) | `/home/philipbl/aq.byu.edu/` |
| GitHub Actions deploy key (restricted) | `/home/philipbl/.ssh/authorized_keys` |
| nginx site config (all server blocks) | `/etc/nginx/conf.d/aq.byu.edu.conf` |
| nginx main config (stock, don't edit) | `/etc/nginx/nginx.conf` |
| nginx logs | `/var/log/nginx/` |
| TLS certificate (Let's Encrypt) | `/etc/letsencrypt/live/aq.byu.edu/` |
| certbot renewal settings (nginx plugin) | `/etc/letsencrypt/renewal/aq.byu.edu.conf` |
| nginx apt repo and pin | `/etc/apt/sources.list.d/nginx.list`, `/etc/apt/preferences.d/99nginx` |
| Automatic nginx updates | `/etc/apt/apt.conf.d/51unattended-upgrades-nginx` |

After editing the nginx config:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### What `aq.byu.edu.conf` serves

`aq.byu.edu.conf` serves only this site. Port 80 redirects everything to
HTTPS, and port 443 serves the web root.

### nginx comes from nginx.org, not Ubuntu

nginx is installed from nginx.org's stable repo, not Ubuntu's package. This
layout keeps upgrades working:

- **Don't edit `/etc/nginx/nginx.conf`.** It's the package's own file, and
  editing it makes upgrades stop to ask about it. It loads
  `/etc/nginx/conf.d/*.conf`, so site settings go in `conf.d/aq.byu.edu.conf`.
- `conf.d/default.conf.disabled` is the package's "Welcome to nginx!" page,
  turned off on purpose.
- `sites-available/` and `sites-enabled/` are left over from Ubuntu's layout.
  nginx no longer reads them.
- **Never purge `nginx-common`.** It's a leftover Ubuntu package, and its purge
  script runs `rm -rf /etc/nginx /var/log/nginx /var/lib/nginx`. Purging can
  happen through `apt purge nginx-common`, `apt purge '~c'`, or any
  "remove leftover config files" cleanup.
- unattended-upgrades installs nginx updates. On upgrade, the package swaps in
  the new binary without restarting. The stable branch moves to a new version
  about once a year, so run `sudo nginx -t` afterwards to catch config that
  newer nginx rejects.

Back up the nginx config before big changes:

```bash
sudo tar czf /root/etc-nginx-$(date +%F).tgz -C /etc nginx
```

### History

- **2026-11-20:** Upgraded from Ubuntu's nginx 1.18 to nginx.org's 1.30. The
  new package's `nginx.conf` doesn't read `sites-enabled/`, so the site config
  moved from `sites-available/default` to `conf.d/aq.byu.edu.conf`. Also
  removed deprecated directives (`listen ... http2` became `http2 on;`, and
  OCSP stapling went, since Let's Encrypt certs no longer support it) and
  enabled automatic nginx updates.
- **2026-11-20:** Removed the old reverse proxies from the nginx config:
  `/grafana/` (→ `localhost:3000`), `/location_verification/`
  (→ `localhost:5000`), ports 32420 and 32421 (→ `localhost:5001` and `5002`),
  and the Capstone 2022-23 ports 58090, 58087 and 58089 (Grafana, InfluxDB and
  Flask → `localhost:8090`, `8087` and `8089`).
