CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    CONSTRAINT scans_ended_at_after_started_at
        CHECK (ended_at IS NULL OR ended_at >= started_at)
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

CREATE INDEX IF NOT EXISTS detection_logs_detected_at_idx
    ON detection_logs (detected_at);

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