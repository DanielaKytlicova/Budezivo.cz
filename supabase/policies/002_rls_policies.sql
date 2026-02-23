-- ============================================================
-- BUDEŽIVO.CZ - ROW LEVEL SECURITY POLICIES
-- Multi-tenant SaaS Security Configuration
-- ============================================================

-- ============================================================
-- ENABLE RLS ON ALL TABLES
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
-- REVOKE PUBLIC ACCESS (Defense in depth)
-- ============================================================

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;

-- Grant specific permissions after RLS is enabled
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- ============================================================
-- INSTITUTIONS POLICIES
-- Only users can see their own institution
-- Only admins can modify institution settings
-- ============================================================

-- SELECT: Users can only see their own institution
CREATE POLICY "institutions_select_own" ON public.institutions
    FOR SELECT TO authenticated
    USING (id = auth.institution_id());

-- UPDATE: Only admins can update institution
CREATE POLICY "institutions_update_admin" ON public.institutions
    FOR UPDATE TO authenticated
    USING (id = auth.institution_id() AND auth.is_admin())
    WITH CHECK (id = auth.institution_id() AND auth.is_admin());

-- INSERT: Handled via service role during registration (no direct user insert)
-- DELETE: Not allowed via RLS (handled administratively)

-- ============================================================
-- USERS POLICIES
-- Multi-tenant isolation with role-based access
-- ============================================================

-- SELECT: Users can see team members in their institution
CREATE POLICY "users_select_institution" ON public.users
    FOR SELECT TO authenticated
    USING (institution_id = auth.institution_id());

-- INSERT: Only admins can invite new users
CREATE POLICY "users_insert_admin" ON public.users
    FOR INSERT TO authenticated
    WITH CHECK (
        institution_id = auth.institution_id() 
        AND auth.is_admin()
    );

-- UPDATE: Admins can update any user, users can update themselves
CREATE POLICY "users_update_own_or_admin" ON public.users
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id() 
        AND (id = auth.user_id() OR auth.is_admin())
    )
    WITH CHECK (
        institution_id = auth.institution_id() 
        AND (id = auth.user_id() OR auth.is_admin())
    );

-- DELETE: Only admins can remove users (not themselves)
CREATE POLICY "users_delete_admin" ON public.users
    FOR DELETE TO authenticated
    USING (
        institution_id = auth.institution_id() 
        AND auth.is_admin() 
        AND id != auth.user_id()
    );

-- ============================================================
-- PROGRAMS POLICIES
-- Role-based CRUD access
-- ============================================================

-- SELECT: All authenticated users in institution can view programs
-- External lecturers can only see programs assigned to them
CREATE POLICY "programs_select_institution" ON public.programs
    FOR SELECT TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND (
            auth.user_role() IN ('admin', 'spravce', 'edukator', 'pokladni')
            OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())
        )
    );

-- SELECT: Public can view published active programs (for booking page)
CREATE POLICY "programs_select_public" ON public.programs
    FOR SELECT TO anon
    USING (
        is_published = TRUE 
        AND status = 'active' 
        AND deleted_at IS NULL
    );

-- Allow anon to read programs
GRANT SELECT ON public.programs TO anon;

-- INSERT: Only admins and educators can create programs
CREATE POLICY "programs_insert_educator" ON public.programs
    FOR INSERT TO authenticated
    WITH CHECK (
        institution_id = auth.institution_id() 
        AND auth.is_educator()
    );

-- UPDATE: Admins, educators can update; lecturers can update assigned programs
CREATE POLICY "programs_update_role" ON public.programs
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND (
            auth.is_educator()
            OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())
        )
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND (
            auth.is_educator()
            OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())
        )
    );

-- DELETE: Only admins can delete programs
CREATE POLICY "programs_delete_admin" ON public.programs
    FOR DELETE TO authenticated
    USING (
        institution_id = auth.institution_id() 
        AND auth.is_admin()
    );

-- ============================================================
-- RESERVATIONS POLICIES
-- Complex role-based access
-- ============================================================

-- SELECT: Institution users can view reservations based on role
CREATE POLICY "reservations_select_institution" ON public.reservations
    FOR SELECT TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND (
            auth.user_role() IN ('admin', 'spravce', 'edukator', 'pokladni')
            OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())
        )
    );

-- INSERT: Public can create reservations (booking form)
CREATE POLICY "reservations_insert_public" ON public.reservations
    FOR INSERT TO anon
    WITH CHECK (TRUE);

-- Allow anon to insert reservations
GRANT INSERT ON public.reservations TO anon;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon;

-- INSERT: Authenticated users can also create reservations
CREATE POLICY "reservations_insert_auth" ON public.reservations
    FOR INSERT TO authenticated
    WITH CHECK (institution_id = auth.institution_id());

-- UPDATE: Role-based update permissions
-- Admin/Educator: Full update
-- Cashier: Only payment-related fields
-- External Lecturer: Only assigned reservations
CREATE POLICY "reservations_update_role" ON public.reservations
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND (
            auth.is_educator()
            OR auth.is_cashier()
            OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())
        )
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND (
            auth.is_educator()
            OR auth.is_cashier()
            OR (auth.user_role() = 'lektor' AND assigned_lecturer_id = auth.user_id())
        )
    );

-- DELETE: Only admins can delete reservations
CREATE POLICY "reservations_delete_admin" ON public.reservations
    FOR DELETE TO authenticated
    USING (
        institution_id = auth.institution_id() 
        AND auth.is_admin()
    );

-- ============================================================
-- PAYMENTS POLICIES
-- Restricted to admin and cashier roles
-- ============================================================

-- SELECT: Admin and cashier can view payments
CREATE POLICY "payments_select_role" ON public.payments
    FOR SELECT TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_cashier()
    );

-- INSERT: Admin and cashier can create payments
CREATE POLICY "payments_insert_role" ON public.payments
    FOR INSERT TO authenticated
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.is_cashier()
    );

-- UPDATE: Only cashier can update payment data
CREATE POLICY "payments_update_cashier" ON public.payments
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_cashier()
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.is_cashier()
    );

-- DELETE: Only admin can delete payments
CREATE POLICY "payments_delete_admin" ON public.payments
    FOR DELETE TO authenticated
    USING (
        institution_id = auth.institution_id() 
        AND auth.is_admin()
    );

-- ============================================================
-- SCHOOLS POLICIES
-- CRM access for educators and above
-- ============================================================

-- SELECT: Educators and above can view schools
CREATE POLICY "schools_select_educator" ON public.schools
    FOR SELECT TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_educator()
    );

-- INSERT: Educators and above can add schools
CREATE POLICY "schools_insert_educator" ON public.schools
    FOR INSERT TO authenticated
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.is_educator()
    );

-- UPDATE: Educators and above can update schools
CREATE POLICY "schools_update_educator" ON public.schools
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_educator()
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.is_educator()
    );

-- DELETE: Only admin can delete schools
CREATE POLICY "schools_delete_admin" ON public.schools
    FOR DELETE TO authenticated
    USING (
        institution_id = auth.institution_id() 
        AND auth.is_admin()
    );

-- ============================================================
-- THEME SETTINGS POLICIES
-- ============================================================

-- SELECT: Public can view theme settings (for booking page styling)
CREATE POLICY "theme_select_public" ON public.theme_settings
    FOR SELECT TO anon
    USING (TRUE);

GRANT SELECT ON public.theme_settings TO anon;

-- SELECT: Authenticated users can view their institution theme
CREATE POLICY "theme_select_institution" ON public.theme_settings
    FOR SELECT TO authenticated
    USING (institution_id = auth.institution_id());

-- INSERT/UPDATE: Only admins can modify theme
CREATE POLICY "theme_modify_admin" ON public.theme_settings
    FOR ALL TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_admin()
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.is_admin()
    );

-- ============================================================
-- CONTACT MESSAGES POLICIES
-- ============================================================

-- INSERT: Anyone can submit contact form (public)
CREATE POLICY "contact_insert_public" ON public.contact_messages
    FOR INSERT TO anon
    WITH CHECK (TRUE);

GRANT INSERT ON public.contact_messages TO anon;

-- SELECT: Only system admins (via service role)
-- No authenticated user access

-- ============================================================
-- AUDIT LOG POLICIES
-- ============================================================

-- SELECT: Only admins can view audit logs for their institution
CREATE POLICY "audit_select_admin" ON public.audit_log
    FOR SELECT TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_admin()
    );

-- INSERT: System only (via triggers/service role)
-- No direct user insert
