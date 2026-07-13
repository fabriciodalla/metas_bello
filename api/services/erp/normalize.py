import unicodedata


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    text = " ".join(name.strip().split())
    text = text.upper()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))
