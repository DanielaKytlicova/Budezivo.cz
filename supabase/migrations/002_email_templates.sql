-- Migration: Add email templates and logs tables
-- Created: 2025-12-XX

-- Table for program-specific email templates
CREATE TABLE IF NOT EXISTS program_email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    
    -- Template content
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    
    -- Metadata
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure one template per program
    CONSTRAINT unique_program_template UNIQUE (program_id)
);

-- Indexes for email templates
CREATE INDEX IF NOT EXISTS idx_email_templates_program ON program_email_templates(program_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_institution ON program_email_templates(institution_id);

-- Table for email sending logs
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    program_id UUID REFERENCES programs(id) ON DELETE SET NULL,
    reservation_id UUID REFERENCES reservations(id) ON DELETE SET NULL,
    
    -- Email details
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_snapshot TEXT,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending', -- pending, sent, failed
    error_message TEXT,
    email_id TEXT, -- External ID from email provider
    
    -- Timestamps
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for email logs
CREATE INDEX IF NOT EXISTS idx_email_logs_institution ON email_logs(institution_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_reservation ON email_logs(reservation_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
CREATE INDEX IF NOT EXISTS idx_email_logs_created ON email_logs(created_at);

-- RLS Policies (if using Supabase RLS)
-- Enable RLS
ALTER TABLE program_email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- Policies for email templates
CREATE POLICY "Users can view their institution's email templates"
    ON program_email_templates FOR SELECT
    USING (institution_id IN (
        SELECT institution_id FROM users WHERE id = auth.uid()
    ));

CREATE POLICY "Users can manage their institution's email templates"
    ON program_email_templates FOR ALL
    USING (institution_id IN (
        SELECT institution_id FROM users WHERE id = auth.uid()
    ));

-- Policies for email logs
CREATE POLICY "Users can view their institution's email logs"
    ON email_logs FOR SELECT
    USING (institution_id IN (
        SELECT institution_id FROM users WHERE id = auth.uid()
    ));

CREATE POLICY "System can insert email logs"
    ON email_logs FOR INSERT
    WITH CHECK (true);

-- Comment for documentation
COMMENT ON TABLE program_email_templates IS 'Custom email templates for booking confirmations per program';
COMMENT ON TABLE email_logs IS 'Audit log of all sent emails for tracking and debugging';
