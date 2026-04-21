"""Built-in blocklist of terms that NER sometimes tags as names/locations
but almost never are in a Swedish professional-document context.

Two kinds of rejections here:

1. `PERSON_BLOCKLIST` — lowercase-normalized terms that should never be
   treated as PERSON. Applied to single-token matches and to any match whose
   normalized form exactly matches.

2. `ROLE_WORDS` — job-title fragments that sometimes get pulled into a PERSON
   span by spaCy (e.g. "OWNER/FOUNDER"). If a detected span equals a role word
   (case-insensitive) or is a pure role-word with a trailing slash, drop it.

3. `COUNTRIES_AND_CONTINENTS` — geographic names the Swedish NER tags as LOC
   but that we keep as-is (mentioning "Somalia" in a CV isn't PII; replacing
   it with "Stationsgatan 1" is worse than leaving it).
"""
from __future__ import annotations

# Common English/Swedish nouns that spaCy's Swedish NER occasionally mis-tags
# as PERSON when they appear capitalized in CVs / job descriptions.
PERSON_BLOCKLIST: set[str] = {
    # Business / CV jargon
    "site", "sites", "turnover", "revenue", "profit", "budget", "scope",
    "scale", "scope", "mission", "vision", "agenda", "brief", "scope",
    "owner", "founder", "partner", "client", "customer", "supplier", "vendor",
    "team", "staff", "crew", "board", "executive", "management", "lead",
    "project", "program", "product", "portfolio", "stakeholder",
    # Roles
    "ceo", "cto", "cfo", "coo", "cio", "cmo", "vd", "chef", "grundare",
    "ägare", "direktör", "styrelseordförande", "konsult", "projektledare",
    "manager", "director", "president", "chair", "chairman", "chairwoman",
    "head", "officer", "analyst", "specialist", "engineer", "developer",
    # Tech / things often capitalized in CVs
    "java", "python", "linux", "windows", "macos", "excel", "word",
    "powerpoint", "office", "outlook", "slack", "teams", "docker", "kubernetes",
    "aws", "azure", "gcp", "react", "angular", "vue", "django",
    "cv", "lebenslauf", "resumé", "resume",
    # Sports / hobby terms that sometimes get flagged
    "barbell", "dumbbell", "crossfit", "yoga", "pilates",
    # Misc
    "mainly", "primarily", "ongoing", "recent", "previous", "current",
}


ROLE_WORDS: set[str] = {
    "ceo", "cto", "cfo", "coo", "cio", "cmo", "cpo",
    "owner", "founder", "co-founder", "cofounder", "vd", "chef",
    "grundare", "ägare", "direktör", "president", "vice president",
    "manager", "director", "head", "lead", "chief", "officer",
}


COUNTRIES_AND_CONTINENTS: set[str] = {
    # Swedish names
    "sverige", "norge", "danmark", "finland", "island", "tyskland", "frankrike",
    "spanien", "italien", "storbritannien", "england", "irland", "nederländerna",
    "belgien", "schweiz", "österrike", "portugal", "grekland", "polen",
    "tjeckien", "slovakien", "ungern", "rumänien", "bulgarien", "estland",
    "lettland", "litauen", "ryssland", "ukraina", "vitryssland",
    "usa", "kanada", "mexiko", "brasilien", "argentina", "chile",
    "kina", "japan", "indien", "sydkorea", "nordkorea", "thailand", "vietnam",
    "indonesien", "filippinerna", "malaysia", "singapore",
    "somalia", "etiopien", "kenya", "egypten", "sydafrika", "marocko",
    "irak", "iran", "syrien", "libanon", "israel", "saudiarabien",
    "australien", "nya zeeland",
    "europa", "asien", "afrika", "nordamerika", "sydamerika", "oceanien",
    # English variants we might see in mixed-language CVs
    "sweden", "norway", "denmark", "germany", "france", "spain", "italy",
    "britain", "england", "netherlands", "belgium", "switzerland", "austria",
    "poland", "russia", "ukraine", "canada", "brazil", "china", "japan",
    "india", "korea", "thailand", "indonesia", "philippines", "iraq", "iran",
    "syria", "lebanon", "israel", "europe", "asia", "africa",
    # Notable islands that double as tech / other terms
    "java",
}


def normalize(value: str) -> str:
    return value.strip().lower()


def is_blocklisted_person(value: str) -> bool:
    v = normalize(value)
    if not v:
        return True
    if v in PERSON_BLOCKLIST:
        return True
    if v in ROLE_WORDS:
        return True
    # Strip trailing slashes / punctuation and re-check (handles "OWNER/").
    stripped = v.rstrip(" /-_.,:;")
    if stripped in PERSON_BLOCKLIST or stripped in ROLE_WORDS:
        return True
    return False


def is_country_or_continent(value: str) -> bool:
    v = normalize(value)
    return v in COUNTRIES_AND_CONTINENTS
