import random

from pseudo_maker.detect.recognizers.orgnr import is_valid_orgnr
from pseudo_maker.detect.recognizers.personnummer import is_valid_personnummer
from pseudo_maker.substitute.fakes import generate_fake
from pseudo_maker.substitute.mapper import Mapper
from pseudo_maker.substitute.valid_format import (
    fake_orgnr,
    fake_personnummer,
)


def test_fake_personnummer_is_valid():
    rng = random.Random(0)
    for _ in range(50):
        fake = fake_personnummer("800101-1237", rng)
        assert is_valid_personnummer(fake), fake


def test_fake_personnummer_preserves_shape():
    rng = random.Random(0)
    f1 = fake_personnummer("800101-1237", rng)
    assert "-" in f1
    assert len(f1.replace("-", "")) == 10

    f2 = fake_personnummer("19800101-1237", rng)
    assert "-" in f2
    assert len(f2.replace("-", "")) == 12

    f3 = fake_personnummer("8001011237", rng)
    assert "-" not in f3
    assert len(f3) == 10


def test_fake_orgnr_is_valid():
    rng = random.Random(1)
    for _ in range(50):
        fake = fake_orgnr("556036-0793", rng)
        assert is_valid_orgnr(fake), fake


def test_mapper_stable_within_doc():
    m = Mapper(seed=0)
    e1 = m.map("PERSON", "Anna Andersson")
    e2 = m.map("PERSON", "Anna Andersson")
    assert e1 is e2
    assert e1.occurrences == 2


def test_mapper_alias_coalesces_first_name():
    m = Mapper(seed=0)
    full = m.map("PERSON", "Anna Andersson")
    short = m.map("PERSON", "Anna")
    assert short is full
    assert "Anna" in full.aliases


def test_mapper_unique_fakes_for_different_inputs():
    m = Mapper(seed=0)
    a = m.map("PERSON", "Anna Andersson")
    b = m.map("PERSON", "Erik Svensson")
    assert a.fake != b.fake


def test_company_suffix_preserved():
    rng = random.Random(0)
    fake = generate_fake("COMPANY", "Volvo AB", rng)
    assert fake.upper().endswith(" AB")


def test_override_fake_updates_entry_and_used_fakes():
    import pytest
    m = Mapper(seed=0)
    entry = m.map("PERSON", "Anna Andersson")
    old_fake = entry.fake
    assert old_fake in m._used_fakes

    m.override_fake(entry.id, "Zelda Zorglub")
    assert entry.fake == "Zelda Zorglub"
    assert "Zelda Zorglub" in m._used_fakes
    assert old_fake not in m._used_fakes

    # Unknown id → KeyError
    with pytest.raises(KeyError):
        m.override_fake("ent_9999", "X Y")

    # Empty value → ValueError
    with pytest.raises(ValueError):
        m.override_fake(entry.id, "   ")


def test_override_fake_refreshes_fake_aliases_for_person():
    m = Mapper(seed=0)
    full = m.map("PERSON", "Anna Andersson")
    short = m.map("PERSON", "Anna")  # coalesces, records alias + fake_alias
    assert short is full
    assert "Anna" in full.fake_aliases

    m.override_fake(full.id, "Zelda Zorglub")
    # After override, fake_aliases["Anna"] should be the first token of the new fake.
    assert full.fake_aliases["Anna"] == "Zelda"
