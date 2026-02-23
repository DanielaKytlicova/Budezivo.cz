-- ============================================================
-- BACKUP AND RECOVERY SCRIPTS
-- Budeživo.cz - Production Database
-- ============================================================

-- ============================================================
-- PRE-MIGRATION BACKUP PROCEDURE
-- Run before any schema changes
-- ============================================================

-- Create a backup schema for rollback
CREATE SCHEMA IF NOT EXISTS backup_$(date +%Y%m%d);

-- Copy critical tables
CREATE TABLE backup_$(date +%Y%m%d).institutions AS SELECT * FROM public.institutions;
CREATE TABLE backup_$(date +%Y%m%d).users AS SELECT * FROM public.users;
CREATE TABLE backup_$(date +%Y%m%d).programs AS SELECT * FROM public.programs;
CREATE TABLE backup_$(date +%Y%m%d).reservations AS SELECT * FROM public.reservations;
CREATE TABLE backup_$(date +%Y%m%d).payments AS SELECT * FROM public.payments;

-- ============================================================
-- ROLLBACK PROCEDURE
-- Use if migration fails
-- ============================================================

-- Example rollback (replace date)
/*
BEGIN;

-- Drop current tables
DROP TABLE IF EXISTS public.institutions CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.programs CASCADE;
DROP TABLE IF EXISTS public.reservations CASCADE;
DROP TABLE IF EXISTS public.payments CASCADE;

-- Restore from backup
CREATE TABLE public.institutions AS SELECT * FROM backup_20250615.institutions;
CREATE TABLE public.users AS SELECT * FROM backup_20250615.users;
CREATE TABLE public.programs AS SELECT * FROM backup_20250615.programs;
CREATE TABLE public.reservations AS SELECT * FROM backup_20250615.reservations;
CREATE TABLE public.payments AS SELECT * FROM backup_20250615.payments;

-- Restore primary keys
ALTER TABLE public.institutions ADD PRIMARY KEY (id);
ALTER TABLE public.users ADD PRIMARY KEY (id);
ALTER TABLE public.programs ADD PRIMARY KEY (id);
ALTER TABLE public.reservations ADD PRIMARY KEY (id);
ALTER TABLE public.payments ADD PRIMARY KEY (id);

-- Re-enable RLS
ALTER TABLE public.institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

COMMIT;
*/

-- ============================================================
-- DATA EXPORT FOR OFFLINE BACKUP
-- ============================================================

-- Export to CSV (run via psql)
/*
\copy (SELECT * FROM public.institutions WHERE deleted_at IS NULL) TO '/tmp/institutions_backup.csv' WITH CSV HEADER;
\copy (SELECT id, institution_id, email, name, role, status, created_at FROM public.users WHERE deleted_at IS NULL) TO '/tmp/users_backup.csv' WITH CSV HEADER;
\copy (SELECT * FROM public.programs WHERE deleted_at IS NULL) TO '/tmp/programs_backup.csv' WITH CSV HEADER;
\copy (SELECT * FROM public.reservations WHERE deleted_at IS NULL) TO '/tmp/reservations_backup.csv' WITH CSV HEADER;
\copy (SELECT * FROM public.payments) TO '/tmp/payments_backup.csv' WITH CSV HEADER;
*/

-- ============================================================
-- GDPR DATA EXPORT FOR USER
-- Export all data for a specific user
-- ============================================================

CREATE OR REPLACE FUNCTION export_user_data(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
    v_user RECORD;
    v_institution_id UUID;
BEGIN
    -- Get user and their institution
    SELECT * INTO v_user FROM public.users WHERE id = p_user_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'User not found');
    END IF;
    
    v_institution_id := v_user.institution_id;
    
    -- Build export
    v_result := jsonb_build_object(
        'export_date', NOW(),
        'user', jsonb_build_object(
            'id', v_user.id,
            'email', v_user.email,
            'name', v_user.name,
            'role', v_user.role,
            'created_at', v_user.created_at,
            'gdpr_consent', v_user.gdpr_consent,
            'gdpr_consent_date', v_user.gdpr_consent_date
        ),
        'institution', (
            SELECT to_jsonb(i.*) - 'id' 
            FROM public.institutions i 
            WHERE id = v_institution_id
        ),
        'programs_created', (
            SELECT COALESCE(jsonb_agg(to_jsonb(p.*) - 'institution_id'), '[]')
            FROM public.programs p
            WHERE p.created_by = p_user_id
        ),
        'reservations_confirmed', (
            SELECT COALESCE(jsonb_agg(to_jsonb(r.*) - 'institution_id'), '[]')
            FROM public.reservations r
            WHERE r.confirmed_by = p_user_id OR r.cancelled_by = p_user_id
        ),
        'audit_log', (
            SELECT COALESCE(jsonb_agg(to_jsonb(a.*) - 'institution_id'), '[]')
            FROM public.audit_log a
            WHERE a.user_id = p_user_id
            ORDER BY a.created_at DESC
            LIMIT 100
        )
    );
    
    RETURN v_result;
END;
$$;

-- ============================================================
-- GDPR DATA DELETION (Right to be Forgotten)
-- Anonymize user data while preserving statistical integrity
-- ============================================================

CREATE OR REPLACE FUNCTION anonymize_user(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Anonymize user record
    UPDATE public.users
    SET 
        email = 'anonymized_' || id::text || '@deleted.local',
        name = 'Anonymized User',
        deleted_at = NOW()
    WHERE id = p_user_id;
    
    -- Clear personal data from audit logs but keep action history
    UPDATE public.audit_log
    SET 
        old_values = old_values - ARRAY['email', 'name', 'contact_name', 'contact_email', 'contact_phone'],
        new_values = new_values - ARRAY['email', 'name', 'contact_name', 'contact_email', 'contact_phone']
    WHERE user_id = p_user_id;
    
    -- Log the anonymization
    INSERT INTO public.audit_log (
        user_id,
        action,
        table_name,
        record_id,
        new_values
    ) VALUES (
        p_user_id,
        'GDPR_ANONYMIZE',
        'users',
        p_user_id,
        jsonb_build_object('anonymized_at', NOW())
    );
    
    RETURN TRUE;
END;
$$;

-- ============================================================
-- CLEANUP OLD BACKUPS
-- Run periodically to remove old backup schemas
-- ============================================================

/*
-- List backup schemas older than 30 days
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name LIKE 'backup_%'
AND schema_name < 'backup_' || to_char(NOW() - INTERVAL '30 days', 'YYYYMMDD');

-- Drop old backup schema (replace with actual name)
DROP SCHEMA backup_20250515 CASCADE;
*/

-- ============================================================
-- STATISTICS FOR MONITORING
-- ============================================================

CREATE OR REPLACE VIEW public.database_stats AS
SELECT
    (SELECT COUNT(*) FROM public.institutions WHERE deleted_at IS NULL) as total_institutions,
    (SELECT COUNT(*) FROM public.users WHERE deleted_at IS NULL) as total_users,
    (SELECT COUNT(*) FROM public.programs WHERE deleted_at IS NULL) as total_programs,
    (SELECT COUNT(*) FROM public.reservations WHERE deleted_at IS NULL) as total_reservations,
    (SELECT COUNT(*) FROM public.reservations WHERE status = 'pending') as pending_reservations,
    (SELECT COUNT(*) FROM public.reservations WHERE status = 'confirmed') as confirmed_reservations,
    (SELECT COUNT(*) FROM public.payments WHERE status = 'paid') as completed_payments,
    (SELECT pg_size_pretty(pg_database_size(current_database()))) as database_size;

-- Grant access to admins
-- GRANT SELECT ON public.database_stats TO authenticated;
