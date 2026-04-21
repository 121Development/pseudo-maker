# mutable-cosmos

Anonymize Swedish PII in Word documents so they can be safely shared with public LLMs, then restore the originals afterwards.

## Workflow

```
mutable-cosmos clean   client_brief.docx
   → cleaned.docx, mapping.json, prompt.txt

(paste cleaned.docx contents into ChatGPT, save reply as llm_reply.docx)

mutable-cosmos restore llm_reply.docx --mapping mapping.json
   → restored.docx
```

## What it detects

- Swedish personnummer and organisationsnummer (Luhn-validated)
- Person names, company names, locations (spaCy `sv_core_news_lg`)
- Phone, email, postal codes, addresses
- IBAN, bankgiro, plusgiro, credit card, VAT
- Swedish license plates, IP addresses, URLs
- Dates and ages

## Substitution

Realistic Swedish-locale fakes (Faker `sv_SE`). Numeric IDs get fresh values with a valid checksum. The same input value always maps to the same fake within a document.

## Install

```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
python -m spacy download sv_core_news_lg
```

## Build standalone binary

```
pyinstaller --onefile --collect-all spacy --collect-all sv_core_news_lg \
  --name mutable-cosmos src/mutable_cosmos/cli.py
```
