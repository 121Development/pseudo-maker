# Deploying mutable-cosmos on an internal server

Intended profile: **small team (≤5 concurrent users), Windows 11 laptops hitting
an internal Docker host over the LAN, no authentication — network boundary is
the access control.**

Users open a browser at `http://<server-host>:8765` and drive the tool from there. No client install on the laptops.

---

## 1. Prerequisites on the server

- Docker 24+ and `docker compose` (v2).
- At least 4 GB RAM available to the container (spaCy + model are memory-heavy).
- Outbound internet during **build only** (pulls Python base image and downloads the Swedish spaCy model). Runtime needs no internet.
- ~1.5 GB free disk for the image.

## 2. Build and start

From the project directory:

```sh
docker compose build     # ~5–10 minutes first time (model download dominates)
docker compose up -d
docker compose logs -f   # verify "mutable-cosmos UI running at http://0.0.0.0:8765"
```

Verify reachability from the server:

```sh
curl -f http://127.0.0.1:8765/api/health
```

From a laptop on the same network, open:

```
http://<server-ip-or-hostname>:8765
```

## 3. Restrict access to the LAN

The app has no authentication. Exposure equals reachability.

Options, pick one that matches your environment:

### 3a. Bind to an internal interface only

If the server has multiple NICs, edit `docker-compose.yml`:

```yaml
    ports:
      - "192.168.10.5:8765:8765"   # replace with your internal IP
```

Then `docker compose up -d`. External interfaces cannot reach the port.

### 3b. Host firewall rule (ufw example)

```sh
sudo ufw allow from 192.168.10.0/24 to any port 8765 proto tcp
sudo ufw deny 8765
```

Adjust the CIDR to your internal subnet.

### 3c. Reverse proxy with an allowlist

If you already run an internal nginx / traefik, front the container with it and restrict by source IP there. Example nginx snippet:

```nginx
location / {
    allow 192.168.10.0/24;
    deny all;
    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    # Large enough for the 25 MB upload cap:
    client_max_body_size 30m;
}
```

## 4. What's persisted

Nothing on disk. All session data lives in tmpfs (RAM-backed `/tmp` inside the container) and is wiped in three layers:
1. UI calls `/api/session/.../close` when the user clicks *Start over / Clean another / Restore another* or closes the tab.
2. Server-side TTL reaps any session older than **5 minutes** on the next `/api/health` hit.
3. Container restart throws away `/tmp` entirely.

Container logs (to Docker's json-file driver) contain request lines with session IDs. These rotate at 10 MB × 5 files. If you want logs gone too, add `logging: { driver: none }` in the compose file.

## 5. Updating

```sh
cd <project-dir>
git pull                      # or however you pull new code
docker compose build
docker compose up -d           # picks up the new image, rolls the container
```

## 6. Troubleshooting

- **Healthcheck failing** — `docker compose logs mutable-cosmos`. First start takes 15–20 s because spaCy loads the model into memory.
- **413 on upload** — file exceeds 25 MB. Edit `MAX_UPLOAD_BYTES` in `src/mutable_cosmos/server/app.py` and rebuild, or raise your reverse-proxy body limit.
- **Slow detection on large docs** — spaCy is CPU-bound. For docs >50 pages, allocate more CPU (`cpus: "2.0"` in the compose `deploy` section).
- **Model download fails during build** — the `python -m spacy download sv_core_news_lg` layer needs outbound HTTPS to github.com and PyPI. If you build behind a proxy, set `HTTP_PROXY`/`HTTPS_PROXY` build args.

## 7. What this deployment does **not** include

- **Authentication** — anyone on the LAN who can reach the port can use the tool. If you need per-user accountability, put oauth2-proxy / Authelia / Microsoft Entra in front (see §3c pattern + their docs).
- **TLS** — traffic is plain HTTP inside the LAN. If your LAN is untrusted or you carry PII across subnets, add a reverse proxy with a cert.
- **Audit trail retention** — the per-restore `_AUDIT.json` file is given to the user; the server keeps no copy. If compliance needs one, wire a log shipper to capture the `/api/restore` response bodies.

## 8. Windows-laptop considerations

Nothing to install. Any modern browser (Edge, Chrome, Firefox) on Windows 11 connects to the server URL. File drag-and-drop works from Explorer. Downloads land in the default Downloads folder.

If some laptops need to work **offline** (travel, site visits), ship them the standalone Windows binary instead — see the repo `README.md` for PyInstaller build instructions (note: must build on Windows).
