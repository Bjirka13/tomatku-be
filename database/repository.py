from __future__ import annotations

from typing import Any

from database.connection import DatabaseConnection


class DetectionRepository:
    def __init__(self, connection: DatabaseConnection | None = None) -> None:
        self.connection = connection or DatabaseConnection()

    def create_scan(self) -> str:
        query = "INSERT INTO scans (started_at, ended_at) VALUES (NOW(), NOW()) RETURNING id;"
        result = self.connection.execute(query, fetch=True)
        return str(result[0]["id"])

    def insert_detection_log(
        self,
        scan_id: str,
        classification: str,
        confidence_pct: float,
        image_path: str | None,
        severity_level: str | None,
        severity_pct: float | None,
    ) -> str:
        query = """
            INSERT INTO detection_logs (
                scan_id,
                classification,
                confidence_pct,
                image_path,
                severity_level,
                severity_pct,
                detected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW()) RETURNING id;
        """
        result = self.connection.execute(
            query,
            params=(
                scan_id,
                classification,
                confidence_pct,
                image_path,
                severity_level,
                severity_pct,
            ),
            fetch=True,
        )
        return str(result[0]["id"])

    def get_scan_history(self) -> list[dict[str, Any]]:
        query = """
            SELECT s.id AS scan_id,
                   d.id AS detection_id,
                   d.classification,
                   d.confidence_pct,
                   d.image_path,
                   d.severity_level,
                   d.severity_pct,
                   d.detected_at
            FROM scans s
            LEFT JOIN detection_logs d ON d.scan_id = s.id
            ORDER BY d.detected_at DESC NULLS LAST;
        """
        return self.connection.execute(query, fetch=True) or []
