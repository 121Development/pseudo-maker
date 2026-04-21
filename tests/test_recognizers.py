from mutable_cosmos.detect.recognizers.base import luhn_check, luhn_checksum
from mutable_cosmos.detect.recognizers.bankgiro_plusgiro import BankgiroRecognizer
from mutable_cosmos.detect.recognizers.credit_card import CreditCardRecognizer
from mutable_cosmos.detect.recognizers.date_age import AgeRecognizer, DateRecognizer
from mutable_cosmos.detect.recognizers.email import EmailRecognizer
from mutable_cosmos.detect.recognizers.iban import IbanRecognizer
from mutable_cosmos.detect.recognizers.ip_url import IpRecognizer, UrlRecognizer
from mutable_cosmos.detect.recognizers.license_plate_se import LicensePlateSeRecognizer
from mutable_cosmos.detect.recognizers.orgnr import OrgnrRecognizer, is_valid_orgnr
from mutable_cosmos.detect.recognizers.passport import PassportRecognizer
from mutable_cosmos.detect.recognizers.personnummer import (
    PersonnummerRecognizer,
    is_valid_personnummer,
)
from mutable_cosmos.detect.recognizers.phone_se import PhoneSeRecognizer
from mutable_cosmos.detect.recognizers.postal_code_se import PostalCodeSeRecognizer


def _types(values, recognizer):
    return [s.value for s in recognizer.find(values)]


def test_luhn_basic():
    assert luhn_check("79927398713") is True
    assert luhn_check("79927398710") is False
    assert luhn_checksum("7992739871") == 3


def test_personnummer_valid_and_invalid():
    # 800101-1231 has valid Luhn (body 800101123, check 1)
    assert is_valid_personnummer("198001011231")
    assert is_valid_personnummer("800101-1231")
    assert not is_valid_personnummer("800101-1230")
    assert not is_valid_personnummer("800101-1237")


def test_personnummer_finds_in_text():
    text = "Anna har personnummer 800101-1231 och bor i Stockholm. Annan: 800101-1230 (ogiltig)."
    found = list(PersonnummerRecognizer().find(text))
    values = [s.value for s in found]
    assert "800101-1231" in values
    assert "800101-1230" not in values


def test_orgnr_valid():
    # Volvo AB: 556036-0793
    assert is_valid_orgnr("556036-0793")
    assert is_valid_orgnr("5560360793")
    assert not is_valid_orgnr("556036-0790")
    # third digit must be >= 2 (otherwise it's a personnummer-shape)
    assert not is_valid_orgnr("551036-0793")


def test_orgnr_finds_in_text():
    text = "Volvo AB org.nr 556036-0793 är registrerat."
    found = list(OrgnrRecognizer().find(text))
    assert any(s.value.endswith("556036-0793") for s in found)


def test_phone_finds_se_formats():
    text = "Ring oss på 070-123 45 67 eller +46 8 123 456 78."
    found = [s.value for s in PhoneSeRecognizer().find(text)]
    assert any("070" in v for v in found)
    assert any("+46" in v for v in found)


def test_email():
    text = "Mail: anna.andersson@example.se eller info@bolaget.com"
    found = [s.value for s in EmailRecognizer().find(text)]
    assert "anna.andersson@example.se" in found
    assert "info@bolaget.com" in found


def test_iban():
    text = "IBAN: SE3550000000054910000003 betalas in."
    found = [s.value.replace(" ", "") for s in IbanRecognizer().find(text)]
    assert "SE3550000000054910000003" in found


def test_credit_card():
    # Test Visa
    text = "Kort: 4111 1111 1111 1111"
    found = list(CreditCardRecognizer().find(text))
    assert len(found) == 1


def test_bankgiro():
    # 5402-9707: body 5402970 (7 digits) + check 7. Valid Luhn.
    text = "Bankgiro: 5402-9707"
    found = list(BankgiroRecognizer().find(text))
    assert any("5402-9707" in s.value for s in found)


def test_license_plate():
    text = "Bilen ABC123 stod parkerad bredvid DEF12G."
    found = [s.value for s in LicensePlateSeRecognizer().find("Bilen ABC 123 stod bredvid DEF 12G.")]
    assert any("ABC" in v for v in found)


def test_passport_with_cue_word():
    text = "Passport: AB1234567"
    found = [s.value for s in PassportRecognizer().find(text)]
    assert "AB1234567" in found


def test_ip_url():
    text = "Server 192.168.1.10 reachable at https://internal.example.se/path."
    ips = [s.value for s in IpRecognizer().find(text)]
    urls = [s.value for s in UrlRecognizer().find(text)]
    assert "192.168.1.10" in ips
    assert any("internal.example.se" in u for u in urls)


def test_postal_code():
    text = "Adress: Storgatan 5, 411 23 Göteborg"
    found = [s.value for s in PostalCodeSeRecognizer().find(text)]
    assert any("411" in v for v in found)


def test_date_and_age():
    text = "Mötet hölls 2024-01-15. Klienten är 45 år gammal."
    dates = [s.value for s in DateRecognizer().find(text)]
    ages = [s.value for s in AgeRecognizer().find(text)]
    assert "2024-01-15" in dates
    assert any("45" in a for a in ages)
