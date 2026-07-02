"""Sync database URL helpers (trainer, classifier)."""


def sync_database_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def resolved_database_url(*urls: str) -> str:
    for url in urls:
        if url and url.strip():
            return url.strip()
    return ""
