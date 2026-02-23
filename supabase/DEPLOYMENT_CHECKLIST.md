# Budeživo.cz - Supabase Production Deployment Checklist

## Pre-Deployment

### 1. Supabase Project Setup
- [ ] Create production project at supabase.com
- [ ] Note down project URL and API keys
- [ ] Enable MFA on dashboard account
- [ ] Set up team members with appropriate roles

### 2. Environment Configuration
- [ ] Copy `.env.example` to `.env.production`
- [ ] Set `SUPABASE_URL` from dashboard
- [ ] Set `SUPABASE_ANON_KEY` from dashboard
- [ ] Set `SUPABASE_SERVICE_ROLE_KEY` (server-only!)
- [ ] Set `DATABASE_URL` for migrations
- [ ] Configure `STRIPE_*` keys for payments

### 3. Run Database Migrations
```bash
# Order of execution:
1. supabase/migrations/001_schema.sql
2. supabase/policies/002_rls_policies.sql
3. supabase/policies/003_rls_cashier_restriction.sql
4. supabase/scripts/004_audit_triggers.sql
5. supabase/scripts/005_backup_recovery.sql (optional)
6. supabase/scripts/006_performance_optimization.sql (optional)
```

### 4. Verify RLS
```sql
-- All should return 'true'
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
```

### 5. Security Settings
- [ ] Enable SSL enforcement
- [ ] Configure Network Restrictions
- [ ] Enable email confirmations
- [ ] Set password requirements
- [ ] Review rate limits

## Post-Deployment

### 6. Testing
- [ ] Test user registration flow
- [ ] Test login with new user
- [ ] Verify tenant isolation (cross-tenant access blocked)
- [ ] Test each role's permissions
- [ ] Test public booking form
- [ ] Test payment flow

### 7. Monitoring Setup
- [ ] Configure error alerting
- [ ] Set up uptime monitoring
- [ ] Enable query performance logging
- [ ] Configure backup notifications

### 8. Documentation
- [ ] Update team documentation
- [ ] Document emergency procedures
- [ ] Create runbook for common issues

---

## Quick Commands

```bash
# Connect to database
psql $DATABASE_URL

# Run migration
psql $DATABASE_URL -f supabase/migrations/001_schema.sql

# Check RLS status
psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# Export backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Test policy
psql $DATABASE_URL -c "SELECT * FROM pg_policies WHERE schemaname = 'public';"
```

## Emergency Contacts

- **Supabase Support**: support@supabase.io
- **Status Page**: status.supabase.com
- **Discord**: discord.supabase.com

---

*Checklist Version: 1.0.0*
*Last Updated: December 2025*
