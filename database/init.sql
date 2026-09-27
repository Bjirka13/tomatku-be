CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    detection_mode TEXT NOT NULL DEFAULT 'capture',
    stream_id TEXT,
    CONSTRAINT scans_ended_at_after_started_at
        CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT scans_mode_valid
        CHECK (detection_mode IN ('capture', 'realtime')),
    CONSTRAINT scans_stream_valid
        CHECK (
            (detection_mode = 'capture' AND stream_id IS NULL)
            OR (detection_mode = 'realtime' AND stream_id IS NOT NULL AND btrim(stream_id) <> '')
        )
);

ALTER TABLE scans
    ADD COLUMN IF NOT EXISTS detection_mode TEXT NOT NULL DEFAULT 'capture',
    ADD COLUMN IF NOT EXISTS stream_id TEXT;

ALTER TABLE scans
    DROP CONSTRAINT IF EXISTS scans_mode_valid,
    DROP CONSTRAINT IF EXISTS scans_stream_valid;

ALTER TABLE scans
    ADD CONSTRAINT scans_mode_valid
        CHECK (detection_mode IN ('capture', 'realtime')),
    ADD CONSTRAINT scans_stream_valid
        CHECK (
            (detection_mode = 'capture' AND stream_id IS NULL)
            OR (detection_mode = 'realtime' AND stream_id IS NOT NULL AND btrim(stream_id) <> '')
        );

CREATE TABLE IF NOT EXISTS detection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    classification TEXT NOT NULL,
    confidence_pct NUMERIC(5, 2) NOT NULL,
    image_path TEXT,
    severity_level TEXT,
    severity_pct NUMERIC(5, 2),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT detection_logs_classification_valid
        CHECK (classification IN ('healthy', 'early_blight', 'unknown')),
    CONSTRAINT detection_logs_confidence_valid
        CHECK (confidence_pct >= 0 AND confidence_pct <= 100),
    CONSTRAINT detection_logs_severity_level_valid
        CHECK (severity_level IS NULL OR severity_level IN ('ringan', 'sedang', 'parah')),
    CONSTRAINT detection_logs_severity_valid
        CHECK (severity_pct IS NULL OR (severity_pct >= 0 AND severity_pct <= 100))
);

CREATE TABLE IF NOT EXISTS realtime_capture_state (
    stream_id TEXT PRIMARY KEY,
    last_saved_at TIMESTAMPTZ NOT NULL,
    claim_token TEXT NOT NULL
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
                WHERE table_schema = current_schema()
                    AND table_name = 'detection_logs'
                    AND column_name = 'detection_mode'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
                WHERE table_schema = current_schema()
                    AND table_name = 'detection_logs'
                    AND column_name = 'stream_id'
    ) THEN
        UPDATE scans AS s
        SET detection_mode = d.detection_mode,
            stream_id = d.stream_id
        FROM detection_logs AS d
        WHERE d.scan_id = s.id;
    END IF;
END $$;

ALTER TABLE detection_logs
    DROP COLUMN IF EXISTS detection_mode,
    DROP COLUMN IF EXISTS stream_id;

CREATE INDEX IF NOT EXISTS detection_logs_detected_at_idx
    ON detection_logs (detected_at);

CREATE INDEX IF NOT EXISTS scans_stream_started_at_idx
    ON scans (stream_id, started_at DESC);

CREATE INDEX IF NOT EXISTS detection_logs_scan_id_idx
    ON detection_logs (scan_id);

CREATE INDEX IF NOT EXISTS detection_logs_classification_idx
    ON detection_logs (classification);

ALTER TABLE detection_logs
    ADD COLUMN IF NOT EXISTS image_path TEXT;

CREATE INDEX IF NOT EXISTS detection_logs_image_path_idx
    ON detection_logs (image_path);

ALTER TABLE detection_logs
    ALTER COLUMN severity_level DROP NOT NULL,
    ALTER COLUMN severity_pct DROP NOT NULL;

UPDATE detection_logs
SET severity_level = NULL,
    severity_pct = NULL
WHERE classification = 'healthy';

ALTER TABLE detection_logs
    DROP CONSTRAINT IF EXISTS detection_logs_severity_level_valid,
    DROP CONSTRAINT IF EXISTS detection_logs_severity_valid,
    DROP CONSTRAINT IF EXISTS detection_logs_classification_severity_valid;

ALTER TABLE detection_logs
    ADD CONSTRAINT detection_logs_severity_level_valid
        CHECK (
            severity_level IS NULL
            OR severity_level IN ('ringan', 'sedang', 'parah')
        ),
    ADD CONSTRAINT detection_logs_severity_valid
        CHECK (
            severity_pct IS NULL
            OR (severity_pct >= 0 AND severity_pct <= 100)
        ),
    ADD CONSTRAINT detection_logs_classification_severity_valid
        CHECK (
            (classification = 'healthy'
             AND severity_level IS NULL
             AND severity_pct IS NULL)
            OR (classification <> 'healthy'
                AND severity_level IS NOT NULL
                AND severity_pct IS NOT NULL)
        );