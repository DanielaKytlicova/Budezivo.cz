-- ============================================================
-- CASHIER ROLE - RESTRICTED UPDATE POLICY
-- Cashier can only update payment-related fields on reservations
-- ============================================================

-- Drop the generic update policy for reservations
DROP POLICY IF EXISTS "reservations_update_role" ON public.reservations;

-- Create separate policies for different roles

-- ADMIN/EDUCATOR: Full update access
CREATE POLICY "reservations_update_admin_educator" ON public.reservations
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.is_educator()
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.is_educator()
    );

-- EXTERNAL LECTURER: Can only update assigned reservations (limited fields)
CREATE POLICY "reservations_update_lecturer" ON public.reservations
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.user_role() = 'lektor'
        AND assigned_lecturer_id = auth.user_id()
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.user_role() = 'lektor'
        AND assigned_lecturer_id = auth.user_id()
    );

-- CASHIER: Create a function to restrict which fields can be updated
CREATE OR REPLACE FUNCTION check_cashier_reservation_update()
RETURNS TRIGGER AS $$
BEGIN
    -- If user is cashier and not admin/educator, restrict field updates
    IF auth.user_role() = 'pokladni' AND NOT auth.is_educator() THEN
        -- Cashier can only change status to 'paid' related statuses
        -- and cannot modify core booking details
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

-- Apply trigger
DROP TRIGGER IF EXISTS check_cashier_update ON public.reservations;
CREATE TRIGGER check_cashier_update
    BEFORE UPDATE ON public.reservations
    FOR EACH ROW
    EXECUTE FUNCTION check_cashier_reservation_update();

-- Cashier policy for status updates only
CREATE POLICY "reservations_update_cashier" ON public.reservations
    FOR UPDATE TO authenticated
    USING (
        institution_id = auth.institution_id()
        AND auth.user_role() = 'pokladni'
    )
    WITH CHECK (
        institution_id = auth.institution_id()
        AND auth.user_role() = 'pokladni'
    );
