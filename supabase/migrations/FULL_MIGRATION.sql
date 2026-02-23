-- ============================================================
-- COMBINED MIGRATION SCRIPT
-- Run this single file to set up the entire database
-- Budeživo.cz - Production Database Setup
-- ============================================================

-- ============================================================
-- STEP 1: EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- STEP 2: HELPER FUNCTIONS FOR RLS
-- ============================================================

-- Get current user's ID from JWT
CREATE OR REPLACE FUNCTION auth.user_id() 
RETURNS uuid 
LANGUAGE sql STABLE 
AS $$
  SELECT auth.uid()
$$;

-- Get current user's institution_id from JWT claims
CREATE OR REPLACE FUNCTION auth.institution_id() 
RETURNS uuid 
LANGUAGE sql STABLE 
AS $$
  SELECT COALESCE(
    (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'institution_id')::uuid,
    NULL
  )
$$;

-- Get current user's role from JWT claims
CREATE OR REPLACE FUNCTION auth.user_role() 
RETURNS text 
LANGUAGE sql STABLE 
AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'role',
    'viewer'
  )
$$;

-- Role check functions
CREATE OR REPLACE FUNCTION auth.is_admin() 
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT auth.user_role() IN ('admin', 'spravce')
$$;

CREATE OR REPLACE FUNCTION auth.is_educator() 
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT auth.user_role() IN ('admin', 'spravce', 'edukator')
$$;

CREATE OR REPLACE FUNCTION auth.is_lecturer() 
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT auth.user_role() IN ('admin', 'spravce', 'edukator', 'lektor')
$$;

CREATE OR REPLACE FUNCTION auth.is_cashier() 
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT auth.user_role() IN ('admin', 'spravce', 'pokladni')
$$;

-- ============================================================
-- STEP 3: TABLES
-- ============================================================

-- Institutions
CREATE TABLE IF NOT EXISTS public.institutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('museum', 'gallery', 'library', 'cultural_center', 'other')),
    country TEXT NOT NULL DEFAULT 'CZ',
    address TEXT,
    city TEXT,
    psc TEXT,
    ico_dic TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    logo_url TEXT,
    primary_color TEXT DEFAULT '#1E293B',
    secondary_color TEXT DEFAULT '#84A98C',
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'standard', 'premium')),
    programs_limit INTEGER NOT NULL DEFAULT 3,
    bookings_monthly_limit INTEGER NOT NULL DEFAULT 50,
    default_available_days TEXT[] DEFAULT ARRAY['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    default_time_blocks JSONB DEFAULT '[{"start": "09:00", "end": "10:00"}]',
    operating_start_date DATE,
    operating_end_date DATE,
    default_program_duration INTEGER DEFAULT 60,
    default_program_capacity INTEGER DEFAULT 30,
    default_target_group TEXT DEFAULT 'schools',
    notification_settings JSONB DEFAULT '{"new_reservation": true, "confirmation": true, "cancellation": true, "sms_enabled": false}',
    locale_settings JSONB DEFAULT '{"language": "cs", "timezone": "Europe/Prague", "date_format": "dd.mm.yyyy", "time_format": "24h"}',
    gdpr_settings JSONB DEFAULT '{"data_retention": "never", "anonymize": false}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Users
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'spravce', 'edukator', 'lektor', 'pokladni', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
    invited_by UUID REFERENCES public.users(id),
    gdpr_consent BOOLEAN DEFAULT FALSE,
    gdpr_consent_date TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Programs
CREATE TABLE IF NOT EXISTS public.programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    name_cs TEXT NOT NULL,
    name_en TEXT,
    description_cs TEXT NOT NULL,
    description_en TEXT,
    duration INTEGER NOT NULL DEFAULT 60,
    age_group TEXT NOT NULL CHECK (age_group IN ('ms_3_6', 'zs1_7_12', 'zs2_12_15', 'ss_14_18', 'gym_14_18', 'adults', 'all')),
    min_capacity INTEGER NOT NULL DEFAULT 5,
    max_capacity INTEGER NOT NULL DEFAULT 30,
    target_group TEXT NOT NULL DEFAULT 'schools' CHECK (target_group IN ('schools', 'public', 'both')),
    price DECIMAL(10,2) DEFAULT 0.00,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'concept', 'archived')),
    is_published BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT FALSE,
    send_email_notification BOOLEAN DEFAULT TRUE,
    available_days TEXT[] DEFAULT ARRAY['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    time_blocks JSONB DEFAULT '["09:00-10:30"]',
    start_date DATE,
    end_date DATE,
    min_days_before_booking INTEGER DEFAULT 14,
    max_days_before_booking INTEGER DEFAULT 90,
    preparation_time INTEGER DEFAULT 10,
    cleanup_time INTEGER DEFAULT 30,
    assigned_lecturer_id UUID REFERENCES public.users(id),
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Reservations
CREATE TABLE IF NOT EXISTS public.reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    program_id UUID NOT NULL REFERENCES public.programs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    time_block TEXT NOT NULL,
    school_name TEXT NOT NULL,
    group_type TEXT NOT NULL CHECK (group_type IN ('ms_3_6', 'zs1_7_12', 'zs2_12_15', 'ss_14_18', 'gym_14_18', 'adults', 'other')),
    age_or_class TEXT,
    num_students INTEGER NOT NULL,
    special_requirements TEXT,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),
    confirmed_by UUID REFERENCES public.users(id),
    confirmed_at TIMESTAMPTZ,
    cancelled_by UUID REFERENCES public.users(id),
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    gdpr_consent BOOLEAN DEFAULT FALSE,
    gdpr_consent_date TIMESTAMPTZ,
    assigned_lecturer_id UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Payments
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    reservation_id UUID REFERENCES public.reservations(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'CZK',
    payment_method TEXT CHECK (payment_method IN ('card', 'bank_transfer', 'cash', 'invoice')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
    stripe_session_id TEXT,
    stripe_payment_intent_id TEXT,
    invoice_number TEXT,
    invoice_issued_at TIMESTAMPTZ,
    package TEXT CHECK (package IN ('basic', 'standard', 'premium')),
    billing_cycle TEXT CHECK (billing_cycle IN ('monthly', 'yearly')),
    paid_at TIMESTAMPTZ,
    created_by UUID REFERENCES public.users(id),
    updated_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Schools
CREATE TABLE IF NOT EXISTS public.schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    contact_person TEXT,
    email TEXT,
    phone TEXT,
    booking_count INTEGER DEFAULT 0,
    last_booking_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Theme Settings
CREATE TABLE IF NOT EXISTS public.theme_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL UNIQUE REFERENCES public.institutions(id) ON DELETE CASCADE,
    primary_color TEXT DEFAULT '#1E293B',
    secondary_color TEXT DEFAULT '#84A98C',
    accent_color TEXT DEFAULT '#E9C46A',
    logo_url TEXT,
    header_style TEXT DEFAULT 'light' CHECK (header_style IN ('light', 'dark')),
    footer_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Contact Messages
CREATE TABLE IF NOT EXISTS public.contact_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    institution TEXT,
    subject TEXT DEFAULT 'general',
    message TEXT NOT NULL,
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'read', 'replied', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    replied_at TIMESTAMPTZ
);

-- Audit Log
CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID REFERENCES public.institutions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- STEP 4: INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_institutions_plan ON public.institutions(plan);
CREATE INDEX IF NOT EXISTS idx_users_institution ON public.users(institution_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_institution_role ON public.users(institution_id, role);
CREATE INDEX IF NOT EXISTS idx_programs_institution ON public.programs(institution_id);
CREATE INDEX IF NOT EXISTS idx_programs_status ON public.programs(status);
CREATE INDEX IF NOT EXISTS idx_programs_institution_status ON public.programs(institution_id, status);
CREATE INDEX IF NOT EXISTS idx_programs_assigned_lecturer ON public.programs(assigned_lecturer_id);
CREATE INDEX IF NOT EXISTS idx_reservations_institution ON public.reservations(institution_id);
CREATE INDEX IF NOT EXISTS idx_reservations_program ON public.reservations(program_id);
CREATE INDEX IF NOT EXISTS idx_reservations_date ON public.reservations(date);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON public.reservations(status);
CREATE INDEX IF NOT EXISTS idx_reservations_institution_date ON public.reservations(institution_id, date);
CREATE INDEX IF NOT EXISTS idx_reservations_assigned_lecturer ON public.reservations(assigned_lecturer_id);
CREATE INDEX IF NOT EXISTS idx_payments_institution ON public.payments(institution_id);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_session ON public.payments(stripe_session_id);
CREATE INDEX IF NOT EXISTS idx_schools_institution ON public.schools(institution_id);
CREATE INDEX IF NOT EXISTS idx_audit_institution ON public.audit_log(institution_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON public.audit_log(created_at);

-- ============================================================
-- STEP 5: TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_institutions_updated_at BEFORE UPDATE ON public.institutions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_programs_updated_at BEFORE UPDATE ON public.programs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_reservations_updated_at BEFORE UPDATE ON public.reservations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON public.payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_schools_updated_at BEFORE UPDATE ON public.schools FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_theme_updated_at BEFORE UPDATE ON public.theme_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- STEP 6: ENABLE RLS
-- ============================================================

ALTER TABLE public.institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.theme_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contact_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- STEP 7: RLS POLICIES
-- ============================================================

-- Revoke public access
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;

-- Grant controlled access
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Institutions
CREATE POLICY "institutions_select_own" ON public.institutions FOR SELECT TO authenticated USING (id = auth.institution_id());
CREATE POLICY "institutions_update_admin" ON public.institutions FOR UPDATE TO authenticated USING (id = auth.institution_id() AND auth.is_admin()) WITH CHECK (id = auth.institution_id() AND auth.is_admin());

-- Users
CREATE POLICY "users_select_institution" ON public.users FOR SELECT TO authenticated USING (institution_id = auth.institution_id());
CREATE POLICY "users_insert_admin" ON public.users FOR INSERT TO authenticated WITH CHECK (institution_id = auth.institution_id() AND auth.is_admin());
CREATE POLICY "users_update_own_or_admin" ON public.users FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND (id = auth.user_id() OR auth.is_admin())) WITH CHECK (institution_id = auth.institution_id() AND (id = auth.user_id() OR auth.is_admin()));
CREATE POLICY "users_delete_admin" ON public.users FOR DELETE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin() AND id != auth.user_id());

-- Programs
CREATE POLICY "programs_select_institution" ON public.programs FOR SELECT TO authenticated USING (institution_id = auth.institution_id() AND (auth.user_role() IN ('admin', 'spravce', 'edukator', 'pokladni') OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())));
CREATE POLICY "programs_select_public" ON public.programs FOR SELECT TO anon USING (is_published = TRUE AND status = 'active' AND deleted_at IS NULL);
GRANT SELECT ON public.programs TO anon;
CREATE POLICY "programs_insert_educator" ON public.programs FOR INSERT TO authenticated WITH CHECK (institution_id = auth.institution_id() AND auth.is_educator());
CREATE POLICY "programs_update_role" ON public.programs FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND (auth.is_educator() OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id()))) WITH CHECK (institution_id = auth.institution_id() AND (auth.is_educator() OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())));
CREATE POLICY "programs_delete_admin" ON public.programs FOR DELETE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin());

-- Reservations
CREATE POLICY "reservations_select_institution" ON public.reservations FOR SELECT TO authenticated USING (institution_id = auth.institution_id() AND (auth.user_role() IN ('admin', 'spravce', 'edukator', 'pokladni') OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())));
CREATE POLICY "reservations_insert_public" ON public.reservations FOR INSERT TO anon WITH CHECK (TRUE);
GRANT INSERT ON public.reservations TO anon;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon;
CREATE POLICY "reservations_insert_auth" ON public.reservations FOR INSERT TO authenticated WITH CHECK (institution_id = auth.institution_id());
CREATE POLICY "reservations_update_admin_educator" ON public.reservations FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_educator()) WITH CHECK (institution_id = auth.institution_id() AND auth.is_educator());
CREATE POLICY "reservations_update_lecturer" ON public.reservations FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id()) WITH CHECK (institution_id = auth.institution_id() AND auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id());
CREATE POLICY "reservations_update_cashier" ON public.reservations FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND auth.user_role() = 'pokladni') WITH CHECK (institution_id = auth.institution_id() AND auth.user_role() = 'pokladni');
CREATE POLICY "reservations_delete_admin" ON public.reservations FOR DELETE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin());

-- Payments
CREATE POLICY "payments_select_role" ON public.payments FOR SELECT TO authenticated USING (institution_id = auth.institution_id() AND auth.is_cashier());
CREATE POLICY "payments_insert_role" ON public.payments FOR INSERT TO authenticated WITH CHECK (institution_id = auth.institution_id() AND auth.is_cashier());
CREATE POLICY "payments_update_cashier" ON public.payments FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_cashier()) WITH CHECK (institution_id = auth.institution_id() AND auth.is_cashier());
CREATE POLICY "payments_delete_admin" ON public.payments FOR DELETE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin());

-- Schools
CREATE POLICY "schools_select_educator" ON public.schools FOR SELECT TO authenticated USING (institution_id = auth.institution_id() AND auth.is_educator());
CREATE POLICY "schools_insert_educator" ON public.schools FOR INSERT TO authenticated WITH CHECK (institution_id = auth.institution_id() AND auth.is_educator());
CREATE POLICY "schools_update_educator" ON public.schools FOR UPDATE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_educator()) WITH CHECK (institution_id = auth.institution_id() AND auth.is_educator());
CREATE POLICY "schools_delete_admin" ON public.schools FOR DELETE TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin());

-- Theme Settings
CREATE POLICY "theme_select_public" ON public.theme_settings FOR SELECT TO anon USING (TRUE);
GRANT SELECT ON public.theme_settings TO anon;
CREATE POLICY "theme_select_institution" ON public.theme_settings FOR SELECT TO authenticated USING (institution_id = auth.institution_id());
CREATE POLICY "theme_modify_admin" ON public.theme_settings FOR ALL TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin()) WITH CHECK (institution_id = auth.institution_id() AND auth.is_admin());

-- Contact Messages
CREATE POLICY "contact_insert_public" ON public.contact_messages FOR INSERT TO anon WITH CHECK (TRUE);
GRANT INSERT ON public.contact_messages TO anon;

-- Audit Log
CREATE POLICY "audit_select_admin" ON public.audit_log FOR SELECT TO authenticated USING (institution_id = auth.institution_id() AND auth.is_admin());

-- ============================================================
-- STEP 8: CASHIER FIELD RESTRICTION TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION check_cashier_reservation_update()
RETURNS TRIGGER AS $$
BEGIN
    IF auth.user_role() = 'pokladni' AND NOT auth.is_educator() THEN
        IF NEW.date != OLD.date OR
           NEW.time_block != OLD.time_block OR
           NEW.program_id != OLD.program_id OR
           NEW.school_name != OLD.school_name OR
           NEW.num_students != OLD.num_students OR
           NEW.contact_name != OLD.contact_name OR
           NEW.contact_email != OLD.contact_email OR
           NEW.contact_phone != OLD.contact_phone THEN
            RAISE EXCEPTION 'Cashier role cannot modify booking details';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER check_cashier_update
    BEFORE UPDATE ON public.reservations
    FOR EACH ROW
    EXECUTE FUNCTION check_cashier_reservation_update();

-- ============================================================
-- STEP 9: AUDIT LOGGING TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    v_institution_id UUID;
    v_old_values JSONB;
    v_new_values JSONB;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_institution_id := OLD.institution_id;
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_institution_id := NEW.institution_id;
        v_old_values := NULL;
        v_new_values := to_jsonb(NEW);
    ELSE
        v_institution_id := COALESCE(NEW.institution_id, OLD.institution_id);
        v_old_values := to_jsonb(OLD);
        v_new_values := to_jsonb(NEW);
    END IF;

    INSERT INTO public.audit_log (institution_id, user_id, action, table_name, record_id, old_values, new_values)
    VALUES (v_institution_id, auth.uid(), TG_OP, TG_TABLE_NAME, COALESCE(NEW.id, OLD.id), v_old_values, v_new_values);

    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER audit_programs AFTER INSERT OR UPDATE OR DELETE ON public.programs FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_reservations AFTER INSERT OR UPDATE OR DELETE ON public.reservations FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_payments AFTER INSERT OR UPDATE OR DELETE ON public.payments FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_users AFTER INSERT OR UPDATE OR DELETE ON public.users FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================

-- Verify RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
