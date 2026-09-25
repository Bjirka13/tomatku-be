from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from config import settings


class DatabaseConnection:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or settings.DATABASE_URL

    @contextmanager
    def session(self) -> Iterator[Any]:
        connection = psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)
        try:
            yield connection
        finally:
            connection.close()

    def execute(self, query: str, params: tuple[Any, ...] = (), fetch: bool = False):
        with self.session() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = None
                connection.commit()
                return result


connection = DatabaseConnection()

__all__ = ["DatabaseConnection", "connection"]
