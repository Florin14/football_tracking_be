from typing import Optional


def apply_search(query, field, search: Optional[str]):
    if search:
        return query.filter(field.ilike(f"%{search}%"))
    return query
