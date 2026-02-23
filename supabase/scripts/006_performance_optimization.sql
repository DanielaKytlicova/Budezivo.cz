-- ============================================================
-- PERFORMANCE OPTIMIZATION QUERIES
-- Budeživo.cz - Database Performance Tuning
-- ============================================================

-- ============================================================
-- ANALYZE TABLE STATISTICS
-- Run after bulk data operations
-- ============================================================

ANALYZE public.institutions;
ANALYZE public.users;
ANALYZE public.programs;
ANALYZE public.reservations;
ANALYZE public.payments;
ANALYZE public.schools;
ANALYZE public.audit_log;

-- ============================================================
-- PARTIAL INDEXES FOR COMMON QUERIES
-- ============================================================

-- Active programs only (most common query)
CREATE INDEX IF NOT EXISTS idx_programs_active 
ON public.programs(institution_id, name_cs) 
WHERE status = 'active' AND deleted_at IS NULL AND is_published = TRUE;

-- Pending reservations (dashboard query)
CREATE INDEX IF NOT EXISTS idx_reservations_pending 
ON public.reservations(institution_id, date) 
WHERE status = 'pending' AND deleted_at IS NULL;

-- Upcoming reservations (next 30 days)
CREATE INDEX IF NOT EXISTS idx_reservations_upcoming 
ON public.reservations(institution_id, date, time_block) 
WHERE status IN ('pending', 'confirmed') AND deleted_at IS NULL;

-- Unpaid payments
CREATE INDEX IF NOT EXISTS idx_payments_unpaid 
ON public.payments(institution_id, created_at) 
WHERE status = 'pending';

-- ============================================================
-- COMPOSITE INDEXES FOR JOIN QUERIES
-- ============================================================

-- Reservation with program lookup
CREATE INDEX IF NOT EXISTS idx_reservations_program_date 
ON public.reservations(program_id, date, status);

-- User role checks (for RLS)
CREATE INDEX IF NOT EXISTS idx_users_auth 
ON public.users(id, institution_id, role) 
WHERE deleted_at IS NULL;

-- ============================================================
-- FUNCTION INDEXES FOR COMMON FILTERS
-- ============================================================

-- Month-based reservation queries
CREATE INDEX IF NOT EXISTS idx_reservations_month 
ON public.reservations(institution_id, date_trunc('month', date::timestamp));

-- ============================================================
-- QUERY OPTIMIZATION VIEWS
-- Materialized views for complex statistics
-- ============================================================

-- Institution statistics (refresh daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_institution_stats AS
SELECT 
    i.id as institution_id,
    i.name as institution_name,
    i.plan,
    (SELECT COUNT(*) FROM public.users u WHERE u.institution_id = i.id AND u.deleted_at IS NULL) as user_count,
    (SELECT COUNT(*) FROM public.programs p WHERE p.institution_id = i.id AND p.deleted_at IS NULL) as program_count,
    (SELECT COUNT(*) FROM public.reservations r WHERE r.institution_id = i.id AND r.deleted_at IS NULL) as total_reservations,
    (SELECT COUNT(*) FROM public.reservations r 
     WHERE r.institution_id = i.id 
     AND r.status = 'confirmed' 
     AND r.date >= CURRENT_DATE) as upcoming_reservations,
    (SELECT COALESCE(SUM(p.amount), 0) FROM public.payments p 
     WHERE p.institution_id = i.id 
     AND p.status = 'paid') as total_revenue
FROM public.institutions i
WHERE i.deleted_at IS NULL;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_institution_stats_id 
ON public.mv_institution_stats(institution_id);

-- Refresh function (call via cron or Edge Function)
CREATE OR REPLACE FUNCTION refresh_institution_stats()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_institution_stats;
END;
$$;

-- ============================================================
-- RESERVATION CALENDAR VIEW
-- Optimized for calendar queries
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_calendar_availability AS
SELECT 
    r.institution_id,
    r.program_id,
    r.date,
    r.time_block,
    COUNT(*) as booking_count,
    CASE 
        WHEN COUNT(*) >= p.max_capacity THEN 'full'
        WHEN COUNT(*) > 0 THEN 'partial'
        ELSE 'available'
    END as availability_status
FROM public.reservations r
JOIN public.programs p ON r.program_id = p.id
WHERE r.status IN ('pending', 'confirmed')
AND r.date >= CURRENT_DATE
AND r.date <= CURRENT_DATE + INTERVAL '90 days'
GROUP BY r.institution_id, r.program_id, r.date, r.time_block, p.max_capacity;

CREATE INDEX IF NOT EXISTS idx_mv_calendar_lookup 
ON public.mv_calendar_availability(institution_id, program_id, date);

-- ============================================================
-- COMMON QUERY PATTERNS OPTIMIZATION
-- ============================================================

-- Dashboard stats function (cached)
CREATE OR REPLACE FUNCTION get_dashboard_stats(p_institution_id UUID)
RETURNS TABLE (
    today_bookings BIGINT,
    upcoming_groups BIGINT,
    capacity_usage NUMERIC,
    bookings_used BIGINT,
    bookings_limit INTEGER
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_limit INTEGER;
BEGIN
    -- Get institution limit
    SELECT bookings_monthly_limit INTO v_limit
    FROM public.institutions
    WHERE id = p_institution_id;
    
    RETURN QUERY
    SELECT 
        -- Today's bookings
        (SELECT COUNT(*) FROM public.reservations 
         WHERE institution_id = p_institution_id 
         AND date = CURRENT_DATE 
         AND status != 'cancelled')::BIGINT,
        
        -- Upcoming groups (next 7 days)
        (SELECT COUNT(*) FROM public.reservations 
         WHERE institution_id = p_institution_id 
         AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
         AND status IN ('pending', 'confirmed'))::BIGINT,
        
        -- Capacity usage percentage
        LEAST(100.0, (
            (SELECT COUNT(*) FROM public.reservations 
             WHERE institution_id = p_institution_id 
             AND date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE))::NUMERIC 
            / NULLIF(v_limit, 0) * 100
        ))::NUMERIC,
        
        -- Bookings used this month
        (SELECT COUNT(*) FROM public.reservations 
         WHERE institution_id = p_institution_id 
         AND date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE))::BIGINT,
        
        -- Bookings limit
        v_limit;
END;
$$;

-- ============================================================
-- INDEX MAINTENANCE
-- ============================================================

-- Reindex for performance (run during maintenance window)
/*
REINDEX TABLE CONCURRENTLY public.reservations;
REINDEX TABLE CONCURRENTLY public.programs;
REINDEX TABLE CONCURRENTLY public.audit_log;
*/

-- Vacuum and analyze (automatic in Supabase, but can be manual)
/*
VACUUM ANALYZE public.reservations;
VACUUM ANALYZE public.programs;
*/

-- ============================================================
-- QUERY PERFORMANCE MONITORING
-- ============================================================

-- Enable pg_stat_statements (usually enabled in Supabase)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
CREATE OR REPLACE VIEW public.slow_queries AS
SELECT 
    calls,
    mean_exec_time::numeric(10,2) as avg_ms,
    total_exec_time::numeric(10,2) as total_ms,
    rows,
    query
FROM pg_stat_statements
WHERE calls > 10
ORDER BY mean_exec_time DESC
LIMIT 20;

-- ============================================================
-- CONNECTION POOL OPTIMIZATION
-- ============================================================

-- Recommended connection pool settings for production:
-- - Pool Mode: Transaction (for serverless)
-- - Pool Size: Based on plan (Free: 15, Pro: 60, Team: 120)
-- - Statement Timeout: 30s for web, 300s for background jobs
-- - Idle Timeout: 60s

-- Set statement timeout for current session
-- SET statement_timeout = '30s';

-- ============================================================
-- PARTITIONING FOR LARGE TABLES (Future)
-- Consider if reservations exceed 1M rows
-- ============================================================

/*
-- Example: Partition reservations by month
CREATE TABLE public.reservations_partitioned (
    LIKE public.reservations INCLUDING ALL
) PARTITION BY RANGE (date);

-- Create partitions
CREATE TABLE public.reservations_2025_01 
    PARTITION OF public.reservations_partitioned 
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
    
CREATE TABLE public.reservations_2025_02 
    PARTITION OF public.reservations_partitioned 
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... etc
*/
