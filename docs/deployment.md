# Deploying Songbook on your own domain (HTTPS)

This guide puts a self-hosted Songbook on a domain such as
`songs.example.com` with a free, auto-renewing certificate (#22). Caddy uses
Let's Encrypt, with ZeroSSL as its built-in fallback.
It uses [Caddy](https://caddyserver.com/) as the HTTPS reverse proxy through
`docker-compose.tls.yml`.

```
browser ──HTTPS──▶ caddy :443 ──▶ frontend :80 (app + /api proxy) ──▶ backend :8000
```

## 1. Before you start

- A server with Docker and Docker Compose, and ports **80** and **443** open to
  the internet. Let's Encrypt connects to port 80 to issue the certificate.
- A domain you control.
- A working `.env` (copy `.env.example`). Set a strong `SECRET_KEY` and
  `AUTH_PASSWORD`; production mode refuses the defaults.

## 2. Point the domain at the server

At your DNS provider, create an `A` record (and an `AAAA` record if the server
has IPv6) for the name you want:

| Type | Name | Value |
| --- | --- | --- |
| A | `songs` | your server's public IPv4 |
| AAAA | `songs` | your server's public IPv6 (optional) |

Check it before continuing. This should print your server's address:

```bash
dig +short songs.example.com
```

## 3. Start with HTTPS

Add these to `.env`, or export them in the shell:

```bash
DOMAIN=songs.example.com
ACME_EMAIL=you@example.com   # Let's Encrypt expiry notices
```

Then start the stack with the TLS override:

```bash
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.tls.yml logs -f caddy
```

When Caddy logs `certificate obtained successfully`, open
`https://songs.example.com`. Plain HTTP redirects to HTTPS, and the certificate
renews automatically. Caddy keeps it in the `caddy-data` volume, so do not
delete that volume or you may hit Let's Encrypt rate limits.

With the override, the backend (`8000`) and frontend (`8081`) ports are **not**
published on the host. Everything goes through HTTPS on 443. The app calls the
API on its own origin, so no CORS or `VITE_API_URL` change is needed.

Use the same two `-f` files for every later `docker compose` command
(`pull`, `up`, `logs`, `exec`). Without them, Compose starts the stack without
Caddy and with the plain-HTTP ports published.

## 4. Upgrades and backups

Follow "Database migrations" in the README: back up, then
`git pull && docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build`.

The home server's instance upgrades itself on release tags; see §5.

## 5. Releases and auto-deploy (home server)

The home server runs Songbook as its own Compose project from the private
[`home-server`](https://github.com/xbankov/home-server) repository: the app is
the `services/songbook/app` git submodule and the stack is
`services/songbook/compose.yaml`. A self-hosted GitHub Actions runner in that
repository checks for a new release every ten minutes and deploys it.

A **release** is an annotated `v*` tag on `main`:

```bash
git tag -a v2.0.1 -m "Songbook 2.0.1"
git push origin v2.0.1
```

Tag only a commit whose CI is green. Until the first tag exists, the runner
deploys the tip of `main`.

A deploy:
- resets the deployment checkout to `main` and updates the submodule;
- checks out the newest `v*` tag;
- stops the app containers so no write can land after the dump;
- takes a `pg_dump` into `SONGBOOK_DATA_DIR/backups` (the last 10 are kept)
  and keeps the new dump until the health check passes;
- rebuilds and recreates the stack, then waits for `/api/health`;
- on a failed health check after migrations ran, stops the stack, restores
  that pre-deploy dump and starts the previous tag. The dump is never deleted
  before a successful health check.

The only downtime is the dump plus rebuild and health check; the app is not
serving while the backup is taken, so a save cannot be lost by a rollback.

Manual deploy or rollback on the server:

```bash
cd /home/ubuntu/songbook-deploy
git fetch origin main && git reset --hard origin/main
git submodule update --init --recursive
./scripts/songbook-deploy.sh                 # the newest tag
./scripts/songbook-deploy.sh v2.0.0          # a specific tag
SONGBOOK_FORCE=1 ./scripts/songbook-deploy.sh  # rebuild the current tag
```

A release that ran a database migration **cannot** be rolled back by switching
the tag alone. Stop the stack, restore the dump taken immediately before that
deploy, then start the previous tag. The deploy script already stops the app
before taking the dump, so there are no writes to lose. Do not delete that dump
until the release has been healthy (and a fresh backup exists). The home-server
README documents the restore command for its Compose project.

Data lives outside the checkout (`SONGBOOK_DATA_DIR`, set to
`/home/ubuntu/songbook-data` on the home server), so resets and rebuilds never
touch it. The instance is on the LAN at `http://192.168.178.50:8081`; the
runner, secrets and stack are documented in the home-server README.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Caddy logs `challenge failed` / `timeout` | Port 80 is blocked by a firewall, or DNS does not point at this server yet |
| `too many certificates already issued` | The `caddy-data` volume was deleted repeatedly; wait, or test with a different subdomain |
| Browser shows a certificate for `localhost` | `DOMAIN` was empty or `localhost`; Caddy then issues a local, untrusted certificate |
| `DOMAIN is required` when running Compose | Set `DOMAIN` and `ACME_EMAIL` in `.env` or the shell |

## Other reverse proxies

If you already run Traefik, nginx, or a Cloudflare Tunnel, skip the override
and point your proxy at the frontend container (port `8081` on the host, or
`frontend:80` on the `songbook-net` network), and terminate TLS there. The app
uses relative URLs and same-origin API calls, so it needs no forwarded-header
configuration. Note that the frontend's nginx sets `X-Forwarded-Proto` to its
own scheme (`http`) and uvicorn only trusts proxy headers from `127.0.0.1`, so
the backend does not see the original scheme; nothing in the app depends on it
today.
