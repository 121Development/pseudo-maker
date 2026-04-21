"""Per-entity fake-value generators."""
from __future__ import annotations

import random
import re
from datetime import datetime, timedelta

from faker import Faker

from . import valid_format as vf

# Faker is seeded per-mapper; this module is stateless.
_fake_se = Faker("sv_SE")
_fake_en = Faker("en_US")


def _preserve_company_suffix(original: str, generated: str) -> str:
    """Match common Swedish company suffixes (AB, HB, KB) on the generated name."""
    for suffix in (" AB", " HB", " KB"):
        if original.upper().endswith(suffix):
            if not generated.upper().endswith(suffix):
                generated = re.sub(r"\s+(AB|HB|KB)$", "", generated, flags=re.IGNORECASE)
                generated = f"{generated}{suffix}"
            return generated
    return generated


def fake_person(original: str, rng: random.Random) -> str:
    Faker.seed(rng.randint(0, 2**31))
    full = _fake_se.name()
    # If original looks like a single token, return only the first name.
    if " " not in original.strip():
        return full.split()[0]
    return full


def fake_company(original: str, rng: random.Random) -> str:
    Faker.seed(rng.randint(0, 2**31))
    name = _fake_se.company()
    return _preserve_company_suffix(original, name)


def fake_address(original: str, rng: random.Random) -> str:
    """Street or mixed-address. Used for STREET and the legacy ADDRESS type."""
    Faker.seed(rng.randint(0, 2**31))
    if "\n" in original or "," in original:
        return _fake_se.address().replace("\n", ", ")
    return _fake_se.street_address()


def fake_city(original: str, rng: random.Random) -> str:
    """Swedish city name. Used for single-token LOC matches."""
    Faker.seed(rng.randint(0, 2**31))
    return _fake_se.city()


def fake_phone(original: str, rng: random.Random) -> str:
    Faker.seed(rng.randint(0, 2**31))
    return _fake_se.phone_number()


def fake_email(original: str, rng: random.Random) -> str:
    Faker.seed(rng.randint(0, 2**31))
    return _fake_se.email()


def fake_url(original: str, rng: random.Random) -> str:
    Faker.seed(rng.randint(0, 2**31))
    # Preserve scheme and any path
    m = re.match(r"^(https?://)([^/]+)(.*)$", original, re.IGNORECASE)
    if not m:
        return _fake_en.url()
    scheme, _host, path = m.groups()
    return f"{scheme}{_fake_en.domain_name()}{path}"


def fake_ip(original: str, rng: random.Random) -> str:
    Faker.seed(rng.randint(0, 2**31))
    if ":" in original:
        return _fake_en.ipv6()
    return _fake_en.ipv4_private()


def fake_vat(original: str, rng: random.Random) -> str:
    cc = original[:2].upper() if original[:2].isalpha() else "SE"
    return f"{cc}{rng.randint(100000000, 999999999)}01"


def fake_date(original: str, rng: random.Random) -> str:
    """Shift the date by ±90 days, preserving the input format if recognizable."""
    fmts = [
        "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d.%m.%Y",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(original, fmt)
            shifted = dt + timedelta(days=rng.randint(-90, 90))
            return shifted.strftime(fmt)
        except ValueError:
            continue
    # Long form fallback: return a random date
    Faker.seed(rng.randint(0, 2**31))
    return _fake_se.date()


def fake_age(original: str, rng: random.Random) -> str:
    m = re.match(r"\s*(\d+)", original)
    if not m:
        return original
    n = int(m.group(1))
    new_n = max(0, n + rng.randint(-2, 2))
    return original.replace(m.group(1), str(new_n), 1)


def fake_postal_code(original: str, rng: random.Random) -> str:
    return vf.fake_postal_code(rng)


def fake_personnummer(original: str, rng: random.Random) -> str:
    return vf.fake_personnummer(original, rng)


def fake_orgnr(original: str, rng: random.Random) -> str:
    return vf.fake_orgnr(original, rng)


def fake_bankgiro(original: str, rng: random.Random) -> str:
    return vf.fake_bankgiro(original, rng)


def fake_plusgiro(original: str, rng: random.Random) -> str:
    return vf.fake_bankgiro(original, rng)


def fake_credit_card(original: str, rng: random.Random) -> str:
    return vf.fake_credit_card(rng)


def fake_iban(original: str, rng: random.Random) -> str:
    return vf.fake_iban_se(rng)


def fake_license_plate(original: str, rng: random.Random) -> str:
    return vf.fake_license_plate(rng, original)


def fake_passport(original: str, rng: random.Random) -> str:
    return vf.fake_passport(rng)


# Dispatch table — one entry per entity type
GENERATORS = {
    "PERSON": fake_person,
    "COMPANY": fake_company,
    "STREET": fake_address,
    "CITY": fake_city,
    "ADDRESS": fake_address,  # backward-compat alias
    "POSTAL_CODE": fake_postal_code,
    "PHONE": fake_phone,
    "EMAIL": fake_email,
    "URL": fake_url,
    "IP": fake_ip,
    "PERSONNUMMER": fake_personnummer,
    "ORGNR": fake_orgnr,
    "BANKGIRO": fake_bankgiro,
    "PLUSGIRO": fake_plusgiro,
    "CREDIT_CARD": fake_credit_card,
    "IBAN": fake_iban,
    "VAT": fake_vat,
    "LICENSE_PLATE": fake_license_plate,
    "PASSPORT": fake_passport,
    "DATE": fake_date,
    "AGE": fake_age,
}


def generate_fake(entity_type: str, original: str, rng: random.Random) -> str:
    gen = GENERATORS.get(entity_type)
    if gen is None:
        # Unknown type: opaque token fallback
        return f"[{entity_type}_{rng.randint(1000, 9999)}]"
    return gen(original, rng)
