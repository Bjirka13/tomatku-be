from __future__ import annotations

from typing import Any
from uuid import uuid4

from database.connection import DatabaseConnection


class DetectionRepository:
    def __init__(self, connection: DatabaseConnection | None = None) -> None:
        self.connection = connection or DatabaseConnection()

    def create_scan(self, detection_mode: str, stream_id: str | None) -> str:
        query = """
            INSERT INTO scans (started_at, ended_at, detection_mode, stream_id)
            VALUES (NOW(), NOW(), %s, %s)
            RETURNING id;
        """
        result = self.connection.execute(
            query,
            params=(detection_mode, stream_id),
            fetch=True,
        )
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

    def try_claim_realtime_capture(
        self,
        stream_id: str,
        cooldown_seconds: float,
    ) -> str | None:
        """Atomically allow one capture per stream during the cooldown window."""
        claim_token = uuid4().hex
        query = """
            INSERT INTO realtime_capture_state (stream_id, last_saved_at, claim_token)
            VALUES (%s, NOW(), %s)
            ON CONFLICT (stream_id) DO UPDATE
            SET last_saved_at = EXCLUDED.last_saved_at,
                claim_token = EXCLUDED.claim_token
            WHERE realtime_capture_state.last_saved_at
                <= NOW() - (%s * INTERVAL '1 second')
            RETURNING claim_token;
        """
        result = self.connection.execute(
            query,
            params=(stream_id, claim_token, cooldown_seconds),
            fetch=True,
        )
        return str(result[0]["claim_token"]) if result else None

    def release_realtime_capture(self, stream_id: str, claim_token: str) -> None:
        """Release a cooldown claim when its image or detection could not be saved."""
        query = """
            DELETE FROM realtime_capture_state
            WHERE stream_id = %s AND claim_token = %s;
        """
        self.connection.execute(query, params=(stream_id, claim_token))

    def get_scan_history(self) -> list[dict[str, Any]]:
        """Keep scans without detections in history, with their detection fields empty."""
        query = """
            SELECT s.id AS scan_id,
                   d.id AS detection_id,
                   d.classification,
                   d.confidence_pct,
                   d.image_path,
                   d.severity_level,
                   d.severity_pct,
                   s.detection_mode,
                   s.stream_id,
                   d.detected_at
            FROM scans s
            LEFT JOIN detection_logs d ON d.scan_id = s.id
            ORDER BY d.detected_at DESC NULLS LAST;
        """
        return self.connection.execute(query, fetch=True) or []
