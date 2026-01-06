# poți salva aici în memorie sau în DB (tabel name_aliases)
ALIASES = {
  # "u cluj": "Universitatea Cluj",
}

def alias_lookup(entity_type: str, raw: str) -> str | None:
    key = raw.strip().lower()
    return ALIASES.get(key)
