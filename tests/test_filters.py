"""Tests for the feedback-driven false-positive filters."""
from pseudo_maker.detect.blocklist import (
    is_blocklisted_person,
    is_country_or_continent,
)
from pseudo_maker.detect.ner_swedish import (
    _classify_location,
    _should_reject_company,
    _should_reject_person,
)
from pseudo_maker.detect.recognizers.postal_code_se import PostalCodeSeRecognizer


def _pc_values(text):
    return [s.value for s in PostalCodeSeRecognizer().find(text)]


def test_postal_code_requires_space():
    # Both NNNNN compact forms should be rejected.
    assert _pc_values("ISO 27001 är en standard") == []
    assert _pc_values("ISO 18788:2015 hanterar säkerhetstjänster") == []
    # The normal NNN NN with a space still matches.
    assert _pc_values("Adress: Storgatan 5, 411 23 Göteborg") == ["411 23"]


def test_postal_code_skips_standards_prefix():
    # Even if the numbers happen to be formatted with a space, skip when preceded
    # by a standards prefix.
    assert _pc_values("RFC 411 23 är fiktiv") == []
    assert _pc_values("ISO 411 23 är också fiktiv") == []


def test_person_blocklist_core_terms():
    assert is_blocklisted_person("site")
    assert is_blocklisted_person("turnover")
    assert is_blocklisted_person("Java")
    assert is_blocklisted_person("OWNER")
    assert is_blocklisted_person("owner/")
    assert is_blocklisted_person("VD")
    # Real names pass through.
    assert not is_blocklisted_person("Anna")
    assert not is_blocklisted_person("Erik Svensson")


def test_country_whitelist():
    assert is_country_or_continent("Somalia")
    assert is_country_or_continent("Irak")
    assert is_country_or_continent("Sverige")
    assert is_country_or_continent("Europe")
    # Cities should not be in the country list.
    assert not is_country_or_continent("Stockholm")
    assert not is_country_or_continent("Göteborg")


def test_reject_person_rules():
    # Lowercase single token → reject.
    assert _should_reject_person("site")
    assert _should_reject_person("turnover")
    # Slash inside → reject.
    assert _should_reject_person("OWNER/FOUNDER")
    assert _should_reject_person("Anna/Erik")
    # All-caps short token → reject (role fragment).
    assert _should_reject_person("CEO")
    assert _should_reject_person("FOUNDER")
    # Real names kept.
    assert not _should_reject_person("Anna")
    assert not _should_reject_person("Anna Andersson")
    assert not _should_reject_person("Erik Svensson")


def test_reject_company_with_slash():
    assert _should_reject_company("OWNER/FOUNDER")
    assert not _should_reject_company("Volvo AB")


def test_classify_location_city_vs_street():
    assert _classify_location("Stockholm") == "CITY"
    assert _classify_location("Göteborg") == "CITY"
    assert _classify_location("Luleå") == "CITY"
    # Multiword / with numbers / with commas → street.
    assert _classify_location("Storgatan 5") == "STREET"
    assert _classify_location("Storgatan 5, 411 23 Göteborg") == "STREET"
    # Lowercase or oddly-formatted → street (conservative).
    assert _classify_location("stockholm") == "STREET"
    # Street suffix wins over single-token-city detection.
    assert _classify_location("Slåttervallsgatan") == "STREET"
    assert _classify_location("Storgatan") == "STREET"
    assert _classify_location("Kungsvägen") == "STREET"
    assert _classify_location("Odengatan") == "STREET"


def test_strip_leading_noise():
    from pseudo_maker.detect.ner_swedish import _strip_leading_noise
    assert _strip_leading_noise("mainly Irak") == ("Irak", 7)
    assert _strip_leading_noise("huvudsakligen Stockholm") == ("Stockholm", 14)
    assert _strip_leading_noise("Stockholm") == ("Stockholm", 0)


def test_fake_city_generator_produces_city():
    import random
    from pseudo_maker.substitute.fakes import generate_fake
    fake = generate_fake("CITY", "Stockholm", random.Random(0))
    # Cities are single-token, no digits.
    assert " " not in fake or fake.count(" ") <= 2
    assert not any(c.isdigit() for c in fake)
