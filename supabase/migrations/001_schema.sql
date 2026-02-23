-- ============================================================
-- BUDEŽIVO.CZ - PRODUCTION DATABASE SCHEMA
-- Multi-tenant SaaS for Cultural Institutions
-- ============================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- HELPER FUNCTIONS FOR RLS
-- ============================================================

-- Function to get current user's ID from JWT
CREATE OR REPLACE FUNCTION auth.user_id() 
RETURNS uuid 
LANGUAGE sql STABLE 
AS $$
  SELECT auth.uid()
$$;

-- Function to get current user's institution_id from JWT claims
CREATE OR REPLACE FUNCTION auth.institution_id() 
RETURNS uuid 
LANGUAGE sql STABLE 
AS $$
  SELECT COALESCE(
    (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'institution_id')::uuid,
    NULL
  )
$$;

-- Function to get current user's role from JWT claims
CREATE OR REPLACE FUNCTION auth.user_role() 
RETURNS text 
LANGUAGE sql STABLE 
AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'role',
    'viewer'
  )
$$;

-- Function to check if user is admin of their institution
CREATE OR REPLACE FUNCTION auth.is_admin() 
RETURNS boolean 
LANGUAGE sql STABLE 
AS $$
  SELECT auth.user_role() IN ('admin', 'spravce')
$$;

-- Function to check if user is educator
CREATE OR REPLACE FUNCTION auth.is_educator() 
RETURNS boolean 
LANGUAGE sql STABLE 
AS $$
  SELECT auth.user_role() IN ('admin', 'spravce', 'edukator')
$$;

-- Function to check if user is external lecturer
CREATE OR REPLACE FUNCTION auth.is_lecturer() 
RETURNS boolean 
LANGUAGE sql STABLE 
AS $$
  SELECT auth.user_role() IN ('admin', 'spravce', 'edukator', 'lektor')
$$;

-- Function to check if user is cashier
CREATE OR REPLACE FUNCTION auth.is_cashier() 
RETURNS boolean 
LANGUAGE sql STABLE 
AS $$
  SELECT auth.user_role() IN ('admin', 'spravce', 'pokladni')
$$;

-- ============================================================
-- INSTITUTIONS TABLE
-- ============================================================

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
    
    -- Plan & Limits
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'standard', 'premium')),
    programs_limit INTEGER NOT NULL DEFAULT 3,
    bookings_monthly_limit INTEGER NOT NULL DEFAULT 50,
    
    -- Default Operating Settings
    default_available_days TEXT[] DEFAULT ARRAY['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    default_time_blocks JSONB DEFAULT '[{"start": "09:00", "end": "10:00"}]',
    operating_start_date DATE,
    operating_end_date DATE,
    
    -- Default Program Settings
    default_program_duration INTEGER DEFAULT 60,
    default_program_capacity INTEGER DEFAULT 30,
    default_target_group TEXT DEFAULT 'schools',
    
    -- Settings
    notification_settings JSONB DEFAULT '{"new_reservation": true, "confirmation": true, "cancellation": true, "sms_enabled": false}',
    locale_settings JSONB DEFAULT '{"language": "cs", "timezone": "Europe/Prague", "date_format": "dd.mm.yyyy", "time_format": "24h"}',
    gdpr_settings JSONB DEFAULT '{"data_retention": "never", "anonymize": false}',
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- USERS TABLE (extends auth.users)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'spravce', 'edukator', 'lektor', 'pokladni', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
    invited_by UUID REFERENCES public.users(id),
    
    -- GDPR
    gdpr_consent BOOLEAN DEFAULT FALSE,
    gdpr_consent_date TIMESTAMPTZ,
    
    -- Metadata
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- PROGRAMS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    
    -- Basic Info (multilingual)
    name_cs TEXT NOT NULL,
    name_en TEXT,
    description_cs TEXT NOT NULL,
    description_en TEXT,
    
    -- Program Details
    duration INTEGER NOT NULL DEFAULT 60, -- minutes
    age_group TEXT NOT NULL CHECK (age_group IN ('ms_3_6', 'zs1_7_12', 'zs2_12_15', 'ss_14_18', 'gym_14_18', 'adults', 'all')),
    min_capacity INTEGER NOT NULL DEFAULT 5,
    max_capacity INTEGER NOT NULL DEFAULT 30,
    target_group TEXT NOT NULL DEFAULT 'schools' CHECK (target_group IN ('schools', 'public', 'both')),
    price DECIMAL(10,2) DEFAULT 0.00,
    
    -- Status & Publishing
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'concept', 'archived')),
    is_published BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT FALSE,
    send_email_notification BOOLEAN DEFAULT TRUE,
    
    -- Schedule Settings
    available_days TEXT[] DEFAULT ARRAY['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    time_blocks JSONB DEFAULT '["09:00-10:30"]',
    start_date DATE,
    end_date DATE,
    
    -- Booking Parameters
    min_days_before_booking INTEGER DEFAULT 14,
    max_days_before_booking INTEGER DEFAULT 90,
    preparation_time INTEGER DEFAULT 10, -- minutes
    cleanup_time INTEGER DEFAULT 30, -- minutes
    
    -- Assigned Lecturer (for external lecturers)
    assigned_lecturer_id UUID REFERENCES public.users(id),
    
    -- Metadata
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- RESERVATIONS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    program_id UUID NOT NULL REFERENCES public.programs(id) ON DELETE CASCADE,
    
    -- Booking Details
    date DATE NOT NULL,
    time_block TEXT NOT NULL,
    
    -- School/Group Info
    school_name TEXT NOT NULL,
    group_type TEXT NOT NULL CHECK (group_type IN ('ms_3_6', 'zs1_7_12', 'zs2_12_15', 'ss_14_18', 'gym_14_18', 'adults', 'other')),
    age_or_class TEXT,
    num_students INTEGER NOT NULL,
    special_requirements TEXT,
    
    -- Contact Info
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    
    -- Status & Workflow
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),
    confirmed_by UUID REFERENCES public.users(id),
    confirmed_at TIMESTAMPTZ,
    cancelled_by UUID REFERENCES public.users(id),
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    
    -- GDPR
    gdpr_consent BOOLEAN DEFAULT FALSE,
    gdpr_consent_date TIMESTAMPTZ,
    
    -- For external lecturers
    assigned_lecturer_id UUID REFERENCES public.users(id),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- PAYMENTS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    reservation_id UUID REFERENCES public.reservations(id) ON DELETE SET NULL,
    
    -- Payment Details
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'CZK',
    payment_method TEXT CHECK (payment_method IN ('card', 'bank_transfer', 'cash', 'invoice')),
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
    
    -- Stripe Integration
    stripe_session_id TEXT,
    stripe_payment_intent_id TEXT,
    
    -- Invoice
    invoice_number TEXT,
    invoice_issued_at TIMESTAMPTZ,
    
    -- Package Purchase (for plan upgrades)
    package TEXT CHECK (package IN ('basic', 'standard', 'premium')),
    billing_cycle TEXT CHECK (billing_cycle IN ('monthly', 'yearly')),
    
    -- Metadata
    paid_at TIMESTAMPTZ,
    created_by UUID REFERENCES public.users(id),
    updated_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SCHOOLS TABLE (CRM for repeat visitors)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    
    -- School Info
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    
    -- Contact
    contact_person TEXT,
    email TEXT,
    phone TEXT,
    
    -- Statistics
    booking_count INTEGER DEFAULT 0,
    last_booking_date DATE,
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- THEME SETTINGS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.theme_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL UNIQUE REFERENCES public.institutions(id) ON DELETE CASCADE,
    
    -- Colors
    primary_color TEXT DEFAULT '#1E293B',
    secondary_color TEXT DEFAULT '#84A98C',
    accent_color TEXT DEFAULT '#E9C46A',
    
    -- Branding
    logo_url TEXT,
    header_style TEXT DEFAULT 'light' CHECK (header_style IN ('light', 'dark')),
    footer_text TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- CONTACT MESSAGES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.contact_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Sender Info
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    institution TEXT,
    
    -- Message
    subject TEXT DEFAULT 'general',
    message TEXT NOT NULL,
    
    -- Status
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'read', 'replied', 'archived')),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    replied_at TIMESTAMPTZ
);

-- ============================================================
-- AUDIT LOG TABLE (for compliance)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID REFERENCES public.institutions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    -- Action Details
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Institutions
CREATE INDEX IF NOT EXISTS idx_institutions_plan ON public.institutions(plan);
CREATE INDEX IF NOT EXISTS idx_institutions_deleted ON public.institutions(deleted_at) WHERE deleted_at IS NULL;

-- Users
CREATE INDEX IF NOT EXISTS idx_users_institution ON public.users(institution_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_institution_role ON public.users(institution_id, role);

-- Programs
CREATE INDEX IF NOT EXISTS idx_programs_institution ON public.programs(institution_id);
CREATE INDEX IF NOT EXISTS idx_programs_status ON public.programs(status);
CREATE INDEX IF NOT EXISTS idx_programs_institution_status ON public.programs(institution_id, status);
CREATE INDEX IF NOT EXISTS idx_programs_assigned_lecturer ON public.programs(assigned_lecturer_id);
CREATE INDEX IF NOT EXISTS idx_programs_deleted ON public.programs(deleted_at) WHERE deleted_at IS NULL;

-- Reservations
CREATE INDEX IF NOT EXISTS idx_reservations_institution ON public.reservations(institution_id);
CREATE INDEX IF NOT EXISTS idx_reservations_program ON public.reservations(program_id);
CREATE INDEX IF NOT EXISTS idx_reservations_date ON public.reservations(date);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON public.reservations(status);
CREATE INDEX IF NOT EXISTS idx_reservations_institution_date ON public.reservations(institution_id, date);
CREATE INDEX IF NOT EXISTS idx_reservations_assigned_lecturer ON public.reservations(assigned_lecturer_id);
CREATE INDEX IF NOT EXISTS idx_reservations_contact_email ON public.reservations(contact_email);

-- Payments
CREATE INDEX IF NOT EXISTS idx_payments_institution ON public.payments(institution_id);
CREATE INDEX IF NOT EXISTS idx_payments_reservation ON public.payments(reservation_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_session ON public.payments(stripe_session_id);

-- Schools
CREATE INDEX IF NOT EXISTS idx_schools_institution ON public.schools(institution_id);
CREATE INDEX IF NOT EXISTS idx_schools_email ON public.schools(email);

-- Theme Settings
CREATE INDEX IF NOT EXISTS idx_theme_institution ON public.theme_settings(institution_id);

-- Audit Log
CREATE INDEX IF NOT EXISTS idx_audit_institution ON public.audit_log(institution_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON public.audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON public.audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON public.audit_log(table_name, record_id);

-- ============================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_institutions_updated_at
    BEFORE UPDATE ON public.institutions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_programs_updated_at
    BEFORE UPDATE ON public.programs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reservations_updated_at
    BEFORE UPDATE ON public.reservations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at
    BEFORE UPDATE ON public.payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schools_updated_at
    BEFORE UPDATE ON public.schools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_theme_updated_at
    BEFORE UPDATE ON public.theme_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
