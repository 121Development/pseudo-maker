"""Generators that produce valid-checksum fakes preserving the input shape."""
from __future__ import annotations

import random
import re
import string

from .. import swedish as sv
from ..detect.recognizers.base import luhn_checksum


def fake_personnummer(original: str, rng: random.Random) -> str:
    """Return a fake personnummer with the same shape and a valid Luhn checksum.

    Preserves: 12- vs 10-digit form, the separator ('-', '+' or none), the
    legal gender digit (odd = man, even = woman), samordningsnummer (day+60),
    and the approximate age (birth year within ±3 years). The date and serial
    are otherwise random.
    """
    from datetime import date

    digits_only = re.sub(r"[-+]", "", original)
    twelve_digit = len(digits_only) == 12
    sep = "-" if "-" in original else ("+" if "+" in original else "")

    # Recover original birth year to keep the person's age roughly intact.
    orig_year = None
    if twelve_digit:
        orig_year = int(digits_only[:4])
    elif len(digits_only) == 10:
        yy = int(digits_only[:2])
        this_year = date.today().year
        # 10-digit: '+' means 100+ years old, otherwise most recent matching year.
        base = this_year - (100 if sep == "+" else 0)
        orig_year = base - ((base - yy) % 100)
    year = (orig_year + rng.randint(-3, 3)) if orig_year else rng.randint(1940, 2005)
    year = min(year, date.today().year - 1)

    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    coordination = len(digits_only) >= 10 and int(digits_only[-6:-4]) > 60
    day_field = day + 60 if coordination else day

    serial2 = f"{rng.randint(0, 99):02d}"
    gender_digit = rng.randint(0, 9)
    if len(digits_only) >= 10:
        orig_gender_odd = int(digits_only[-2]) % 2
        if gender_digit % 2 != orig_gender_odd:
            gender_digit = (gender_digit + 1) % 10
    serial = serial2 + str(gender_digit)
    if serial == "000":
        serial = "002"

    yymmdd = f"{year % 100:02d}{month:02d}{day_field:02d}"
    check = luhn_checksum(yymmdd + serial)
    last4 = serial + str(check)

    head = f"{year:04d}{month:02d}{day_field:02d}" if twelve_digit else yymmdd
    return f"{head}{sep}{last4}"


def fake_orgnr(original: str, rng: random.Random) -> str:
    """Random valid Swedish org number in the original's format.

    Keeps the first digit (the legal-form group: 5 = aktiebolag, 9 = HB/KB,
    8 = ideell förening, 7 = ek. förening, 2 = myndighet ...) since that is
    not identifying, and the optional '16' prefix / dash.
    """
    digits = re.sub(r"\D", "", original)
    prefix16 = len(digits) == 12 and digits.startswith("16")
    if prefix16:
        digits = digits[2:]
    first = digits[0] if digits and digits[0] in "256789" else "5"
    body = [first] + [str(rng.randint(0, 9)) for _ in range(8)]
    body[2] = str(rng.randint(2, 9))
    body_s = "".join(body)
    full = body_s + str(luhn_checksum(body_s))
    if prefix16:
        full = "16" + full
    return sv.reshape_digits(original, full) if len(re.sub(r"\D", "", original)) == len(full) else full


def fake_bankgiro(original: str, rng: random.Random) -> str:
    """7- or 8-digit bankgiro with valid Luhn, preserving the dash position."""
    m = re.match(r"(\d{3,4})-(\d{4})", original)
    if not m:
        return original
    head_len = len(m.group(1))
    digits = [str(rng.randint(1, 9))] + [str(rng.randint(0, 9)) for _ in range(head_len + 4 - 2)]
    body = "".join(digits)
    full = body + str(luhn_checksum(body))
    return f"{full[:head_len]}-{full[head_len:]}"


def fake_plusgiro(original: str, rng: random.Random) -> str:
    """Plusgiro with valid Luhn, same digit count and grouping ('12 34 56-7')."""
    n = len(re.sub(r"\D", "", original))
    body = str(rng.randint(1, 9)) + sv.random_digits(n - 2, rng)
    return sv.reshape_digits(original, body + str(luhn_checksum(body)))


def fake_credit_card(rng: random.Random, original: str = "") -> str:
    """Visa-style number with valid Luhn, keeping the original's grouping."""
    n = len(re.sub(r"\D", "", original)) or 16
    body = "4" + sv.random_digits(n - 2, rng)
    full = body + str(luhn_checksum(body))
    return sv.reshape_digits(original, full) if original else full


def fake_iban_se(rng: random.Random, original: str = "") -> str:
    """Generate a valid Swedish IBAN, grouped in 4s if the original was."""
    # SE kk BBB C... (24 chars). Bank code 3 digits; use common Swedish ranges.
    bank = rng.choice(["500", "600", "800", "300", "120", "950"])
    bban = bank + sv.random_digits(17, rng)
    rearranged = bban + "281400"  # letters → numbers: S=28, E=14; check digits "00"
    check = 98 - (int(rearranged) % 97)
    value = f"SE{check:02d}{bban}"
    if " " in original:
        value = " ".join(value[i:i + 4] for i in range(0, len(value), 4))
    return value


def fake_postal_code(rng: random.Random, original: str = "") -> str:
    """Same format as the original ('SE-' prefix, space or not)."""
    digits = f"{rng.randint(100, 989)}{rng.randint(0, 99):02d}"
    return sv.reshape_digits(original, digits) if original else f"{digits[:3]} {digits[3:]}"


def fake_license_plate(rng: random.Random, original: str) -> str:
    """Match new format if original ends in letter, classic if all digits."""
    letters = "ABCDEFGHJKLMNOPRSTUWXYZ"
    new_format = bool(re.search(r"[A-Z]\s?\d{2}[A-Z]$", original.upper()))
    head = "".join(rng.choice(letters) for _ in range(3))
    if new_format:
        tail = f"{rng.randint(0, 99):02d}{rng.choice(letters)}"
    else:
        tail = f"{rng.randint(0, 999):03d}"
    sep = " " if " " in original else ""
    return f"{head}{sep}{tail}"


def fake_passport(rng: random.Random, original: str = "") -> str:
    """Keep the letter/digit pattern of the original (Swedish passports: 8 digits)."""
    if not original:
        return "".join(rng.choices(string.digits, k=8))
    return "".join(
        rng.choice(string.ascii_uppercase) if c.isalpha() else rng.choice(string.digits) if c.isdigit() else c
        for c in original
    )
