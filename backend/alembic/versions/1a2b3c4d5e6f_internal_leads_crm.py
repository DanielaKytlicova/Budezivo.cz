"""Add isolated internal CRM tables. Rollback keeps CRM data for recovery."""
from alembic import op

revision = '1a2b3c4d5e6f'
down_revision = '0f9e8d7c6b5a'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("\nCREATE TABLE IF NOT EXISTS lead_accounts (\n\tid VARCHAR(36) NOT NULL, \n\tusername VARCHAR(80) NOT NULL, \n\tfirst_name VARCHAR(100) NOT NULL, \n\tlast_name VARCHAR(100) NOT NULL, \n\tpassword_hash TEXT NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\trole VARCHAR(30) NOT NULL, \n\tcreated_by VARCHAR(80) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlast_login_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_lead_account_role CHECK (role = 'lead_collaborator'), \n\tUNIQUE (username)\n)\n\n")
    op.execute('ALTER TABLE lead_accounts ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE lead_accounts FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON lead_accounts FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON lead_accounts FROM authenticated; END IF; END $$")
    op.execute('\nCREATE TABLE IF NOT EXISTS lead_sessions (\n\tid VARCHAR(36) NOT NULL, \n\taccount_id VARCHAR(36) NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(account_id) REFERENCES lead_accounts (id), \n\tUNIQUE (token_hash)\n)\n\n')
    op.execute('CREATE INDEX IF NOT EXISTS ix_lead_sessions_account_id ON lead_sessions (account_id)')
    op.execute('ALTER TABLE lead_sessions ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE lead_sessions FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON lead_sessions FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON lead_sessions FROM authenticated; END IF; END $$")
    op.execute('\nCREATE TABLE IF NOT EXISTS leads (\n\tid VARCHAR(36) NOT NULL, \n\tlegacy_id VARCHAR(100), \n\tname VARCHAR(300) NOT NULL, \n\ttype VARCHAR(80) NOT NULL, \n\ttype_label VARCHAR(150) NOT NULL, \n\tcity VARCHAR(150) NOT NULL, \n\tregion VARCHAR(150) NOT NULL, \n\taddress VARCHAR(300) NOT NULL, \n\tcountry VARCHAR(80) NOT NULL, \n\tpostal_code VARCHAR(20) NOT NULL, \n\tdistrict VARCHAR(150) NOT NULL, \n\tlat FLOAT, \n\tlng FLOAT, \n\tlocation_accuracy VARCHAR(300) NOT NULL, \n\tcluster VARCHAR(150) NOT NULL, \n\tplan VARCHAR(80) NOT NULL, \n\tprograms VARCHAR(150) NOT NULL, \n\tcatalog_programs INTEGER NOT NULL, \n\tbooking VARCHAR(500) NOT NULL, \n\tonline VARCHAR(150) NOT NULL, \n\tonline_completion VARCHAR(150) NOT NULL, \n\tactivity VARCHAR(150) NOT NULL, \n\trelationship VARCHAR(150) NOT NULL, \n\tregularity VARCHAR(300) NOT NULL, \n\tscore INTEGER NOT NULL, \n\twhy TEXT NOT NULL, \n\tcatalog VARCHAR(150) NOT NULL, \n\tcatalog_role VARCHAR(300) NOT NULL, \n\twebsite_url VARCHAR(2000) NOT NULL, \n\tprogram_url VARCHAR(2000) NOT NULL, \n\tstage VARCHAR(100) NOT NULL, \n\tresult_reason TEXT NOT NULL, \n\tnext_action TEXT NOT NULL, \n\tnext_action_date DATE, \n\tlast_contact DATE, \n\tinternal_note TEXT NOT NULL, \n\tassignee_id VARCHAR(36), \n\tarchived BOOLEAN NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_by VARCHAR(80) NOT NULL, \n\tlegacy_snapshot JSON, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_lead_score CHECK (score BETWEEN 0 AND 100), \n\tCONSTRAINT ck_lead_program_count CHECK (catalog_programs >= 0), \n\tCONSTRAINT ck_lead_lat CHECK (lat BETWEEN -90 AND 90), \n\tCONSTRAINT ck_lead_lng CHECK (lng BETWEEN -180 AND 180), \n\tUNIQUE (legacy_id), \n\tFOREIGN KEY(assignee_id) REFERENCES lead_accounts (id)\n)\n\n')
    op.execute('CREATE INDEX IF NOT EXISTS ix_leads_assignee_id ON leads (assignee_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_leads_next_action_date ON leads (next_action_date)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_leads_stage ON leads (stage)')
    op.execute('ALTER TABLE leads ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE leads FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON leads FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON leads FROM authenticated; END IF; END $$")
    op.execute('\nCREATE TABLE IF NOT EXISTS lead_contacts (\n\tid VARCHAR(36) NOT NULL, \n\tlead_id VARCHAR(36) NOT NULL, \n\tfirst_name VARCHAR(100) NOT NULL, \n\tlast_name VARCHAR(150) NOT NULL, \n\tposition VARCHAR(300) NOT NULL, \n\temail VARCHAR(254) NOT NULL, \n\tphone VARCHAR(80) NOT NULL, \n\tnote TEXT NOT NULL, \n\t"primary" BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n)\n\n')
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_lead_primary_contact ON lead_contacts (lead_id) WHERE "primary" IS true')
    op.execute('CREATE INDEX IF NOT EXISTS ix_lead_contacts_lead_id ON lead_contacts (lead_id)')
    op.execute('ALTER TABLE lead_contacts ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE lead_contacts FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON lead_contacts FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON lead_contacts FROM authenticated; END IF; END $$")
    op.execute('\nCREATE TABLE IF NOT EXISTS lead_activities (\n\tid VARCHAR(36) NOT NULL, \n\tlead_id VARCHAR(36) NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\tsubject VARCHAR(300) NOT NULL, \n\tbody TEXT NOT NULL, \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tactor_id VARCHAR(80) NOT NULL, \n\tactor_name VARCHAR(220) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n)\n\n')
    op.execute('CREATE INDEX IF NOT EXISTS ix_lead_activities_lead_id ON lead_activities (lead_id)')
    op.execute('ALTER TABLE lead_activities ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE lead_activities FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON lead_activities FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON lead_activities FROM authenticated; END IF; END $$")
    op.execute('\nCREATE TABLE IF NOT EXISTS lead_audit (\n\tid VARCHAR(36) NOT NULL, \n\tlead_id VARCHAR(36), \n\tentity VARCHAR(30) NOT NULL, \n\tentity_id VARCHAR(100) NOT NULL, \n\tactor_id VARCHAR(80) NOT NULL, \n\tactor_name VARCHAR(220) NOT NULL, \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\taction VARCHAR(30) NOT NULL, \n\tfield VARCHAR(80) NOT NULL, \n\told_value JSON, \n\tnew_value JSON, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n)\n\n')
    op.execute('CREATE INDEX IF NOT EXISTS ix_lead_audit_lead_id ON lead_audit (lead_id)')
    op.execute('ALTER TABLE lead_audit ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE lead_audit FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON lead_audit FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON lead_audit FROM authenticated; END IF; END $$")
    op.execute('\nCREATE TABLE IF NOT EXISTS lead_goals (\n\tid VARCHAR(36) NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tmetric VARCHAR(30) NOT NULL, \n\ttarget INTEGER NOT NULL, \n\tdeadline DATE NOT NULL, \n\tcluster VARCHAR(150), \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_lead_goal_target CHECK (target > 0)\n)\n\n')
    op.execute('ALTER TABLE lead_goals ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE lead_goals FROM PUBLIC')
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON lead_goals FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON lead_goals FROM authenticated; END IF; END $$")
    op.execute("""INSERT INTO lead_goals (id, name, metric, target, deadline, cluster) VALUES
        ('default-active', 'Aktivní instituce', 'connected', 15, '2027-01-31', NULL),
        ('default-paying', 'Platící instituce', 'paying', 5, '2027-01-31', NULL),
        ('default-cluster', 'Instituce v hlavním klastru', 'connected', 12, '2027-01-31', 'Liberec–Jablonec–Turnov'),
        ('default-programs', 'Programy v katalogu', 'programs', 50, '2027-01-31', NULL)
        ON CONFLICT (id) DO NOTHING""")


def downgrade():
    # Intentionally retain private CRM tables and audit. Roll back application code,
    # not customer data. Re-upgrade is idempotent; no tenant schema was changed.
    pass
