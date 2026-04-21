# docker_plan.md — subdomain routing for mutable-cosmos

## Context

Today's Docker image (`Dockerfile` + `docker-compose.yml` in the repo root) runs `mutable-cosmos serve` on port 8765 inside the container. Users reach it at `http://<server-ip>:8765`.

The next step is to expose it at a nicer internal URL like `clean.company.se`. The current image stays untouched — this document is the proposal IT can act on later, after the standalone image is validated in a pilot.

**Goal:** route `https://clean.company.se` (or `http://`) on the Docker host to the existing `mutable-cosmos` container, without modifying that container.

## What has to be true

Three separate moving parts have to line up. Any one of them can be skipped in a simpler setup.

1. **DNS.** `clean.company.se` must resolve to the Docker host's IP.
   - *Internal-only zone* — add an A/CNAME in the internal DNS resolver. Laptops inside the network resolve it; the outside world does not.
   - *Public zone* — add the A record in the public zone registrar. Anyone on the internet can resolve it; access is gated purely by reachability (firewall).

2. **Reverse proxy** on the Docker host. Listens on 80/443 for the hostname `clean.company.se`, forwards to `127.0.0.1:8765` (or to the `mutable-cosmos` service over Docker's internal network). Options:
   - **Caddy** — simplest, config is 3 lines, automatic TLS including an internal CA mode.
   - **nginx** — ubiquitous, you drop in an existing cert + key.
   - **Traefik** — discovers services via Docker labels; good if you expect to add more services later.

3. **TLS certificate** for `clean.company.se`. The choice depends on whether the name is internal-only and whether the laptops have a way to trust a non-public CA.
   - **Caddy `tls internal`** — Caddy generates its own CA and mints a cert automatically. Laptops must trust Caddy's root CA once (push via Intune/MDM or manually). Zero ongoing ops.
   - **Company internal CA** — IT issues a cert for `clean.company.se` from the existing internal CA; you drop the cert + key into nginx/Caddy config. Matches existing corporate trust chain.
   - **Let's Encrypt via DNS-01** — viable even for an internal-IP-only host, if you have DNS-provider API access. Public trust, free, auto-renews.
   - **No TLS** — plain HTTP. Fine for a small trusted LAN; browsers won't flag anything because there's no auth or cookies that matter.

## Recommended path (smallest diff, easiest to maintain)

**Add a Caddy sidecar to the existing `docker-compose.yml`.** The mutable-cosmos service stays exactly as it is today; Caddy becomes the only port exposed to the LAN.

Sketch:

```yaml
services:
  mutable-cosmos:
    # unchanged — the image you're about to pilot-test
    # remove `ports:` mapping; Caddy reaches it over the internal Docker network
    expose:
      - "8765"

  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data      # holds Caddy's internal CA + certs
      - caddy_config:/config
    depends_on:
      - mutable-cosmos

volumes:
  caddy_data:
  caddy_config:
```

Caddyfile (three lines):

```
clean.company.se {
    tls internal
    reverse_proxy mutable-cosmos:8765
}
```

That's the whole change for the "HTTPS with Caddy's internal CA" variant.

For the "plain HTTP, no cert" variant the Caddyfile becomes:

```
http://clean.company.se {
    reverse_proxy mutable-cosmos:8765
}
```

For the "company internal CA with your own cert" variant you'd drop the cert + key in a volume and replace `tls internal` with `tls /path/to/cert.pem /path/to/key.pem`.

## What doesn't change

- The `mutable-cosmos` container image.
- The `mutable-cosmos` configuration (still listens on 0.0.0.0:8765 inside its own network namespace).
- The app's behavior — session TTL, upload cap, cleanup, audit log.

## What this proposal doesn't include (deliberately)

- **Authentication.** A subdomain + TLS doesn't gate who can use the tool. If the pilot shows non-team users reaching the URL, revisit this — the right place to add it is at the Caddy/nginx layer (Authelia, oauth2-proxy, or a corporate SSO forward-auth).
- **Horizontal scaling.** Single container instance, single uvicorn worker, single Caddy. Fine for the stated 1–5 user profile.
- **External access.** The proposal assumes the server and laptops share a network. Publishing to the public internet needs at minimum: a public DNS record, a public-trust cert, and — almost certainly — auth.

## Decisions still open (what IT needs to confirm)

1. **`clean.company.se` — internal-only or publicly resolvable?** Drives whether DNS is done in the internal resolver or at the registrar, and whether TLS can use `tls internal` or needs DNS-01 / a company cert.
2. **Laptop root-CA management.** If going with `tls internal`, is there a way to push Caddy's root CA to the Windows 11 laptops (Intune, GPO, manual install)? If not, use a company-issued cert or skip TLS.
3. **Will anything else live on ports 80/443 of this host?** If yes, Caddy/nginx has to share; if no, Caddy having them to itself is simplest.

## Next steps (after standalone pilot succeeds)

1. IT answers the three decisions above.
2. Pick a Caddy variant (internal-CA / company-cert / no-TLS).
3. Add the Caddy service + Caddyfile to `docker-compose.yml`; remove the `ports: 8765:8765` mapping from `mutable-cosmos` (expose stays).
4. Redeploy: `docker compose up -d`.
5. From a laptop, open `https://clean.company.se` — expect the same UI you saw at `http://<server-ip>:8765`.

## Verification after the proxy is in place

- `docker compose ps` shows both services `healthy`.
- `curl -fk https://clean.company.se/api/health` on the Docker host returns `{"ok": true, ...}`.
- From a laptop: DNS resolves to the host IP; browser shows the UI; clean + restore round-trip still byte-identical on a test document.
- Cert chain: if using `tls internal`, the browser should trust the cert after the CA has been pushed to the laptop; otherwise the usual corporate cert chain.
