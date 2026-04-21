"""Generators that produce valid-checksum fakes preserving the input shape."""
from __future__ import annotations

import random
import re
import string

from ..detect.recognizers.base import luhn_checksum


def fake_personnummer(original: str, rng: random.Random) -> str:
    """Return a fake personnummer with the same shape and a valid Luhn checksum.

    Preserves: 12-digit vs 10-digit form, presence/absence of dash/+ separator.
    Generates a random valid date and a random 3-digit serial.
    """
    digits_only = re.sub(r"[-+]", "", original)
    twelve_digit = len(digits_only) == 12
    has_sep = "-" in original or "+" in original
    sep = "-" if "-" in original else ("+" if "+" in original else "")

    year = rng.randint(1940, 2010)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    serial = f"{rng.randint(1, 999):03d}"
    yymmdd = f"{year % 100:02d}{month:02d}{day:02d}"
    body9 = yymmdd + serial
    check = luhn_checksum(body9)
    last4 = serial + str(check)

    if twelve_digit:
        head = f"{year:04d}{month:02d}{day:02d}"
        return f"{head}{sep}{last4}" if has_sep else f"{head}{last4}"
    return f"{yymmdd}{sep}{last4}" if has_sep else f"{yymmdd}{last4}"


def fake_orgnr(original: str, rng: random.Random) -> str:
    """Random valid Swedish org number, preserving dash if present."""
    has_dash = "-" in original
    # Third digit must be >= 2
    digits = [str(rng.randint(0, 9)) for _ in range(9)]
    digits[2] = str(rng.randint(2, 9))
    body = "".join(digits)
    full = body + str(luhn_checksum(body))
    return f"{full[:6]}-{full[6:]}" if has_dash else full


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


def fake_credit_card(rng: random.Random) -> str:
    """Test-range Visa-style number with valid Luhn (4 + 14 random + check)."""
    body = "4" + "".join(str(rng.randint(0, 9)) for _ in range(14))
    return body + str(luhn_checksum(body))


def fake_iban_se(rng: random.Random) -> str:
    """Generate a valid Swedish IBAN."""
    # SE kk BBBB CCCCCCCCCCCCCCCCC (24 chars total)
    bban = "".join(str(rng.randint(0, 9)) for _ in range(20))
    # Compute IBAN check digits
    rearranged = bban + "282500"  # SE = 2825, 00 placeholder
    check = 98 - (int(rearranged) % 97)
    return f"SE{check:02d}{bban}"


def fake_postal_code(rng: random.Random) -> str:
    return f"{rng.randint(100, 989)} {rng.randint(0, 99):02d}"


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


def fake_passport(rng: random.Random) -> str:
    return "".join(rng.choices(string.digits, k=8))
