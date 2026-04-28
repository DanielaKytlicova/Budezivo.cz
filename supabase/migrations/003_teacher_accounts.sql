-- ============================================================================
-- Migration 003: Teacher accounts (B2C self-registration)
-- ============================================================================
-- Creates parallel auth system for external teachers / parents.
-- Independent of the institutional `users` table.
-- Adds favorites + brute-force tracking.
-- Idempotent — safe to re-run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS teacher_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT,
    name            TEXT NOT NULL,
    school_name     TEXT,
    phone           TEXT,
    auth_provider   TEXT NOT NULL DEFAULT 'password',
    google_sub      TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_teacher_accounts_email      ON teacher_accounts(email);
CREATE INDEX IF NOT EXISTS idx_teacher_accounts_google_sub ON teacher_accounts(google_sub);

CREATE TABLE IF NOT EXISTS teacher_favorites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES teacher_accounts(id) ON DELETE CASCADE,
    program_id      UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    institution_id  UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teacher_favorites_teacher  ON teacher_favorites(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_favorites_program  ON teacher_favorites(program_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_favorites_unique ON teacher_favorites(teacher_id, program_id);

CREATE TABLE IF NOT EXISTS teacher_login_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier      TEXT NOT NULL,
    failed_count    INTEGER NOT NULL DEFAULT 0,
    last_failed_at  TIMESTAMPTZ,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_login_attempts_identifier ON teacher_login_attempts(identifier);
