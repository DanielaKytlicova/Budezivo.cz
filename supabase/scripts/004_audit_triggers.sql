-- ============================================================
-- AUDIT LOGGING TRIGGERS
-- Automatically log all data changes for compliance
-- ============================================================

-- Function to log changes
CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    v_institution_id UUID;
    v_old_values JSONB;
    v_new_values JSONB;
BEGIN
    -- Get institution_id from the record
    IF TG_OP = 'DELETE' THEN
        v_institution_id := OLD.institution_id;
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_institution_id := NEW.institution_id;
        v_old_values := NULL;
        v_new_values := to_jsonb(NEW);
    ELSE -- UPDATE
        v_institution_id := COALESCE(NEW.institution_id, OLD.institution_id);
        v_old_values := to_jsonb(OLD);
        v_new_values := to_jsonb(NEW);
    END IF;

    -- Insert audit log entry
    INSERT INTO public.audit_log (
        institution_id,
        user_id,
        action,
        table_name,
        record_id,
        old_values,
        new_values
    ) VALUES (
        v_institution_id,
        auth.uid(),
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        v_old_values,
        v_new_values
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers to critical tables

-- Programs audit
DROP TRIGGER IF EXISTS audit_programs ON public.programs;
CREATE TRIGGER audit_programs
    AFTER INSERT OR UPDATE OR DELETE ON public.programs
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- Reservations audit
DROP TRIGGER IF EXISTS audit_reservations ON public.reservations;
CREATE TRIGGER audit_reservations
    AFTER INSERT OR UPDATE OR DELETE ON public.reservations
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- Payments audit
DROP TRIGGER IF EXISTS audit_payments ON public.payments;
CREATE TRIGGER audit_payments
    AFTER INSERT OR UPDATE OR DELETE ON public.payments
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- Users audit
DROP TRIGGER IF EXISTS audit_users ON public.users;
CREATE TRIGGER audit_users
    AFTER INSERT OR UPDATE OR DELETE ON public.users
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- ============================================================
-- SOFT DELETE TRIGGER
-- Prevent hard deletes, use soft delete instead
-- ============================================================

CREATE OR REPLACE FUNCTION soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- Instead of deleting, set deleted_at
    UPDATE public.programs 
    SET deleted_at = NOW() 
    WHERE id = OLD.id AND TG_TABLE_NAME = 'programs';
    
    UPDATE public.reservations 
    SET deleted_at = NOW() 
    WHERE id = OLD.id AND TG_TABLE_NAME = 'reservations';
    
    UPDATE public.users 
    SET deleted_at = NOW() 
    WHERE id = OLD.id AND TG_TABLE_NAME = 'users';
    
    UPDATE public.schools 
    SET deleted_at = NOW() 
    WHERE id = OLD.id AND TG_TABLE_NAME = 'schools';
    
    UPDATE public.institutions 
    SET deleted_at = NOW() 
    WHERE id = OLD.id AND TG_TABLE_NAME = 'institutions';
    
    RETURN NULL; -- Prevent actual deletion
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Note: Soft delete triggers can be applied if needed
-- For now, we use RLS to control deletions
