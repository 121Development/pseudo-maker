# mutable-cosmos

Anonymize Swedish PII in documents so you can safely share them with public LLMs, then restore the originals on the way back.

Upload a Word document (or plain text / Markdown). The tool detects person names, company names, Swedish personnummer and organisationsnummer, addresses, phone numbers, emails, bank details and more. Each detection gets replaced by a realistic Swedish-locale substitute — personnummer with a valid checksum, `Anna Andersson` → `Karin Berg`, `Volvo AB` → `Åkesson AB`. You get a cleaned file plus a mapping file. Paste the cleaned text into ChatGPT (or similar), save the response, then restore to get the originals back — with a per-session audit log of what was substituted.

## Workflow

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ your_doc.docx    │──▶──▶│ your_doc_        │──▶──▶│  Public LLM      │
│   (sensitive)    │ clean│   CLEANED.docx   │ copy │  (ChatGPT, etc.) │
└──────────────────┘      │ your_doc_        │      └───────┬──────────┘
                          │   MAPPING.json   │              │ LLM reply
                          └──────────────────┘              ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ your_doc_        │◀──◀──│ your_doc_        │◀──◀──│  llm_reply.docx  │
│   RESTORED.docx  │ rest.│   AUDIT.json     │      │                  │
│ your_doc_        │      └──────────────────┘      └──────────────────┘
│   AUDIT.json     │
└──────────────────┘
```

The mapping file contains your real sensitive values — **keep it local**. The cleaned file is safe to share with an LLM because every identifier has been replaced with a realistic fake.

## What it detects

| Category | Examples |
|---|---|
| Personal | Person names, Swedish personnummer (Luhn-validated), phone, email, home address |
| Organisations | Company names, Swedish organisationsnummer (Luhn), VAT |
| Financial | IBAN, bankgiro, plusgiro, credit card |
| Geographic | Swedish cities and streets (kept separately), postal codes |
| Other identifiers | Swedish license plates, passport numbers, IP addresses, URLs |
| Quasi-identifiers | Dates, ages |

Detection combines two techniques:
- **Regex + checksum validators** for deterministic formats (personnummer, orgnr, IBAN, credit card, …). Skips `ISO 27001`-style standard numbers, country names, role words (`OWNER/FOUNDER`), and a built-in blocklist of common false positives (`site`, `turnover`, `Java` the language, `barbell`, …).
- **Swedish spaCy NER** (`sv_core_news_lg`) for people, companies, and locations.

## Substitution

Realistic Swedish-locale fakes via `Faker(sv_SE)`:
- **PERSON** / **COMPANY** — Swedish names, preserving form (first-only vs first+last, `AB`/`HB`/`KB` suffix).
- **CITY** vs **STREET** — split automatically so cities get city-style fakes and streets get street-style fakes.
- **PERSONNUMMER / ORGNR / BANKGIRO / IBAN / CREDIT_CARD** — random but checksum-valid.
- **PHONE / EMAIL / POSTAL_CODE / DATE / AGE** — preserve format / shape.

The same input value always maps to the same fake within one document. `Anna Andersson` and a later bare `Anna` coalesce to the same mapping entry automatically.

## Getting started

Three ways to run. Pick one.

### Option 1 — Docker (recommended for teams)

Best for deploying to an internal server that laptops hit over the browser.

```sh
git clone <this-repo>
cd mutable-cosmos
docker compose build       # ~5–10 min first time (bakes spaCy Swedish model into the image)
docker compose up -d
curl -f http://127.0.0.1:8765/api/health
```

Open `http://<docker-host>:8765` in any browser. See [`DEPLOY.md`](DEPLOY.md) for LAN hardening, and [`docker_plan.md`](docker_plan.md) for the planned subdomain + reverse-proxy setup.

### Option 2 — Standalone binary (single file, no dependencies)

Best for a single laptop, including offline use.

```sh
# Use a pre-built binary from dist/ (if available), or build your own:
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m spacy download sv_core_news_lg
pyinstaller --onefile \
  --collect-all spacy --collect-all sv_core_news_lg --collect-all thinc \
  --collect-all faker --collect-all docx \
  --collect-all fastapi --collect-all uvicorn --collect-all starlette --collect-all multipart \
  --add-data "src/mutable_cosmos/server/static:mutable_cosmos/server/static" \
  --paths src --name mutable-cosmos entrypoint.py
```

The result is `dist/mutable-cosmos` (~263 MB, includes Python + spaCy + the Swedish model). It runs on macOS / Linux / Windows as a single file — no Python needed on the target machine. Build on the OS you want to run on (PyInstaller doesn't cross-compile cleanly).

```sh
./dist/mutable-cosmos serve        # opens the UI at http://127.0.0.1:8765
./dist/mutable-cosmos clean my.docx
./dist/mutable-cosmos restore reply.docx --mapping my_MAPPING.json
```

### Option 3 — Development install

For running tests, extending detection rules, or contributing.

```sh
git clone <this-repo>
cd mutable-cosmos
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m spacy download sv_core_news_lg
pytest                           # full test suite (~40 tests, <5s)
mutable-cosmos serve             # start the web UI
```

## Usage

### Web UI

Start the server (any of the three options above) and open `http://127.0.0.1:8765`.

**Clean tab** — drag in a `.docx` / `.txt` / `.md` file. The tool detects entities and shows a preview table. For each row you can:
- Untick **Replace** to leave the original in place.
- Click the **Will become** cell to edit the fake manually (useful if the auto-pick collides with the real surname, or if the format needs tweaking). Client-side validation warns on empty / duplicate / invalid-Luhn entries but still accepts your value.

Click **Finalize** and you get two downloads: `<name>_CLEANED.<ext>` and `<name>_MAPPING.json`.

**Restore tab** — drop the LLM's response file and the mapping JSON. You get back `<name>_RESTORED.<ext>` plus a visible report of what was restored exactly, what matched fuzzily (when the LLM lightly rewrote a fake), and what was missing. A `<name>_AUDIT.json` download gives you the machine-readable version of the same report.

### CLI

```sh
# Detect and write a cleaned doc + mapping + suggested LLM system prompt
mutable-cosmos clean client.docx
# → client_CLEANED.docx, client_MAPPING.json, client_PROMPT.txt

# Restore the LLM output
mutable-cosmos restore reply.docx --mapping client_MAPPING.json
# → reply_RESTORED.docx, reply_AUDIT.json

# Dry-run: list detected entities without writing anything
mutable-cosmos detect client.docx

# Start the web UI
mutable-cosmos serve [--host 0.0.0.0] [--port 8765] [--no-browser]
```

Run `mutable-cosmos <cmd> --help` for the full option set (seed, NER toggle, fuzzy threshold, audit path, …).

## Project layout

```
mutable-cosmos/
├── src/mutable_cosmos/
│   ├── cli.py                   # Typer CLI: clean / restore / detect / serve
│   ├── orchestrate.py           # Preview + finalize + restore + audit-log helpers
│   ├── detect/                  # Detection pipeline
│   │   ├── pipeline.py            # Combines regex + NER, resolves overlaps
│   │   ├── ner_swedish.py         # spaCy sv_core_news_lg wrapper with filters
│   │   ├── blocklist.py           # False-positive blocklists / country list
│   │   └── recognizers/           # Per-type regex + checksum recognizers
│   ├── substitute/              # Fake generation + mapping
│   │   ├── fakes.py               # Faker + per-type generators
│   │   ├── valid_format.py        # Luhn-valid personnummer / orgnr / etc.
│   │   └── mapper.py              # Stable input→fake dedup + alias coalescing + override
│   ├── restore/                 # LLM-output → original restoration
│   ├── mapping/                 # mapping.json schema
│   ├── io/                      # .docx (python-docx) + text/markdown I/O
│   └── server/                  # FastAPI app + static UI
│       ├── app.py                 # HTTP endpoints + session store
│       └── static/                # index.html + app.js + style.css
├── tests/                       # pytest — 39 tests covering recognizers, mapper, restore, audit, filters
├── Dockerfile, docker-compose.yml, .dockerignore
├── DEPLOY.md                    # How to run on an internal server
├── docker_plan.md               # Future subdomain + reverse-proxy proposal
└── pyproject.toml
```

## Testing

```sh
pytest                 # all tests
pytest -v              # verbose
pytest tests/test_filters.py   # just the false-positive filters
```

Round-trip tests verify that `clean → restore` produces byte-identical output to the original (when nothing else changes between). No-leak tests confirm the cleaned document contains zero occurrences of any original sensitive value.

## Privacy model

- **Your files never leave the machine running the tool.** The web UI talks to a local process only. The Docker image binds to its own network namespace; IT decides what the LAN can reach.
- Uploaded files are kept in an **in-memory tmpfs** while being processed, reaped after **5 minutes** or when the browser tab closes (whichever is first). The Docker container additionally mounts `/tmp` as tmpfs so restart wipes everything.
- The mapping file contains your real sensitive values. The tool writes it once and hands it to you; don't share it with the LLM.
- No telemetry. No outbound calls at runtime. The only network activity during `docker compose build` is pulling the base image and downloading the spaCy model.

## Limitations / known issues

- The Swedish spaCy NER model occasionally splits compound names (e.g. `Uppsala Universitet` → `Uppsala` as city + `Universitet` as company). Uncheck one of the rows in the preview table if you want to avoid the split. A post-processor to merge adjacent CITY+ORG spans is a likely future improvement.
- Documents with complex .docx formatting (nested tables, text boxes, images with embedded text) may lose some formatting when a single sensitive value spans multiple runs. Plain paragraphs and simple tables are preserved reliably.
- The tool is tuned for Swedish text. English and other Nordic languages partially work because spaCy's Swedish model and Faker's `sv_SE` locale handle some overlap, but recall drops for non-Swedish names and addresses.

## License

Your choice — add a `LICENSE` file. No license declared yet.
