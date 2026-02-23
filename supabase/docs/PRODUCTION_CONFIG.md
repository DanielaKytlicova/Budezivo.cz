# Budeživo.cz - Supabase Production Configuration Guide

## Quick Links
- [Environment Setup](#environment-setup)
- [Security Checklist](#security-checklist)
- [RLS Policy Reference](#rls-policy-reference)
- [Role Permissions Matrix](#role-permissions-matrix)
- [Backup Strategy](#backup-strategy)
- [Monitoring](#monitoring)

---

## Environment Setup

### Required Environment Variables

```bash
# ===========================================
# PRODUCTION ENVIRONMENT (.env.production)
# ===========================================

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Public/Publishable key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # SECRET - Server only!
SUPABASE_JWT_SECRET=your-jwt-secret  # From Supabase Dashboard > Settings > API

# Database Direct Connection (for migrations only)
DATABASE_URL=postgresql://postgres:[password]@db.your-project.supabase.co:5432/postgres

# Application
NODE_ENV=production
NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}

# ===========================================
# DEVELOPMENT ENVIRONMENT (.env.development)
# ===========================================

# Use different Supabase project for development
SUPABASE_URL=https://your-dev-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

NODE_ENV=development
```

### Key Security Rules

| Key Type | Usage | Exposed to Client? |
|----------|-------|-------------------|
| `SUPABASE_ANON_KEY` | Client-side API calls | ✅ Yes (safe with RLS) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side only (bypasses RLS) | ❌ NEVER |
| `SUPABASE_JWT_SECRET` | JWT verification | ❌ NEVER |
| `DATABASE_URL` | Direct DB access | ❌ NEVER |

---

## Security Checklist

### Pre-Production Checklist

- [ ] **RLS Enabled** on ALL tables
- [ ] **Service Role Key** stored server-side only
- [ ] **MFA Enabled** on Supabase Dashboard account
- [ ] **Email Confirmations** enabled in Auth settings
- [ ] **Network Restrictions** configured (IP allowlist)
- [ ] **SSL Enforced** for all connections
- [ ] **API Rate Limits** reviewed
- [ ] **Audit Logging** enabled
- [ ] **Backup Schedule** configured (daily)
- [ ] **Point-in-Time Recovery** enabled (Pro plan)

### Post-Deployment Verification

```sql
-- Verify RLS is enabled on all tables
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public';

-- All should show rowsecurity = true
```

### Security Advisor Check

Navigate to: **Supabase Dashboard > Reports > Security Advisor**

Ensure all items are green:
- ✅ RLS enabled on all tables
- ✅ No public access to sensitive tables
- ✅ Service role key not exposed
- ✅ Auth settings configured

---

## RLS Policy Reference

### Policy Naming Convention

```
{table}_{operation}_{role/scope}
```

Examples:
- `programs_select_institution` - SELECT for institution users
- `reservations_insert_public` - INSERT for public (booking form)
- `payments_update_cashier` - UPDATE for cashier role

### Institutions Table

| Operation | Policy | Who Can Access |
|-----------|--------|----------------|
| SELECT | `institutions_select_own` | Own institution only |
| UPDATE | `institutions_update_admin` | Admin/Správce only |
| INSERT | Service role only | Registration process |
| DELETE | Not allowed | Administrative action |

### Users Table

| Operation | Policy | Who Can Access |
|-----------|--------|----------------|
| SELECT | `users_select_institution` | All institution members |
| INSERT | `users_insert_admin` | Admin/Správce only |
| UPDATE | `users_update_own_or_admin` | Self or Admin |
| DELETE | `users_delete_admin` | Admin (not self) |

### Programs Table

| Operation | Policy | Who Can Access |
|-----------|--------|----------------|
| SELECT (auth) | `programs_select_institution` | Based on role |
| SELECT (anon) | `programs_select_public` | Published programs only |
| INSERT | `programs_insert_educator` | Admin, Správce, Edukátor |
| UPDATE | `programs_update_role` | Admin, Správce, Edukátor, assigned Lektor |
| DELETE | `programs_delete_admin` | Admin only |

### Reservations Table

| Operation | Policy | Who Can Access |
|-----------|--------|----------------|
| SELECT | `reservations_select_institution` | Based on role |
| INSERT (anon) | `reservations_insert_public` | Public booking |
| INSERT (auth) | `reservations_insert_auth` | Institution users |
| UPDATE | Multiple policies | Role-dependent |
| DELETE | `reservations_delete_admin` | Admin only |

### Payments Table

| Operation | Policy | Who Can Access |
|-----------|--------|----------------|
| SELECT | `payments_select_role` | Admin, Správce, Pokladní |
| INSERT | `payments_insert_role` | Admin, Správce, Pokladní |
| UPDATE | `payments_update_cashier` | Pokladní (cashier) |
| DELETE | `payments_delete_admin` | Admin only |

---

## Role Permissions Matrix

### Role Definitions

| Role | Czech Name | Description |
|------|------------|-------------|
| `admin` | Správce | Full access within institution |
| `spravce` | Správce | Alias for admin |
| `edukator` | Edukátor | Manage programs & reservations |
| `lektor` | Externí lektor | View/manage assigned items only |
| `pokladni` | Pokladní | Payment processing only |
| `viewer` | Prohlížeč | Read-only access |

### Detailed Permissions

| Feature | Admin | Edukátor | Lektor | Pokladní | Viewer |
|---------|-------|----------|--------|----------|--------|
| **Institution Settings** |
| View | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Team Management** |
| View members | ✅ | ✅ | ❌ | ❌ | ❌ |
| Invite users | ✅ | ❌ | ❌ | ❌ | ❌ |
| Change roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| Remove users | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Programs** |
| View all | ✅ | ✅ | ❌ | ✅ | ✅ |
| View assigned | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit | ✅ | ✅ | ⚠️* | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Reservations** |
| View all | ✅ | ✅ | ❌ | ✅ | ✅ |
| View assigned | ✅ | ✅ | ✅ | ✅ | ✅ |
| Confirm/Cancel | ✅ | ✅ | ⚠️* | ❌ | ❌ |
| Edit details | ✅ | ✅ | ⚠️* | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Payments** |
| View | ✅ | ❌ | ❌ | ✅ | ❌ |
| Process | ✅ | ❌ | ❌ | ✅ | ❌ |
| Edit | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Schools (CRM)** |
| View | ✅ | ✅ | ❌ | ❌ | ✅ |
| Edit | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Audit Logs** |
| View | ✅ | ❌ | ❌ | ❌ | ❌ |

*⚠️ = Only for assigned items

---

## Backup Strategy

### Automated Backups (Supabase Built-in)

| Plan | Backup Frequency | Retention | PITR |
|------|------------------|-----------|------|
| Free | Daily | 7 days | ❌ |
| Pro | Daily | 7 days | ✅ (7 days) |
| Team | Daily | 14 days | ✅ (14 days) |
| Enterprise | Customizable | Custom | ✅ (30+ days) |

### Manual Backup Commands

```bash
# Export full database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Export specific tables
pg_dump $DATABASE_URL -t institutions -t users -t programs -t reservations > data_backup.sql

# Export with compression
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Recommended Backup Schedule

1. **Daily**: Automated Supabase backup
2. **Weekly**: Manual export stored offsite (S3, GCS)
3. **Before Deployments**: Always backup before schema changes
4. **Monthly**: Test restore procedure

### Recovery Procedures

```bash
# Restore from backup
psql $DATABASE_URL < backup_20250615.sql

# Point-in-time recovery (Pro plan)
# Use Supabase Dashboard > Database > Backups > Restore to Point in Time
```

---

## Index Recommendations

### Primary Indexes (Created in Schema)

```sql
-- High-priority indexes for common queries

-- User lookups
CREATE INDEX idx_users_institution_role ON users(institution_id, role);
CREATE INDEX idx_users_email ON users(email);

-- Reservation queries
CREATE INDEX idx_reservations_institution_date ON reservations(institution_id, date);
CREATE INDEX idx_reservations_assigned_lecturer ON reservations(assigned_lecturer_id);

-- Program filtering
CREATE INDEX idx_programs_institution_status ON programs(institution_id, status);
CREATE INDEX idx_programs_assigned_lecturer ON programs(assigned_lecturer_id);

-- Payment lookups
CREATE INDEX idx_payments_stripe_session ON payments(stripe_session_id);
```

### Query Performance Tips

1. **Always filter by `institution_id`** - This is your tenant isolation column
2. **Use date ranges** instead of exact matches where possible
3. **Avoid `SELECT *`** - Only fetch needed columns
4. **Use pagination** for large result sets

### Monitor Query Performance

```sql
-- Enable query logging (development only)
ALTER DATABASE postgres SET log_statement = 'all';

-- Find slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

---

## Monitoring Recommendations

### Key Metrics to Track

1. **Database Performance**
   - Query latency (p50, p95, p99)
   - Connection pool usage
   - Active connections

2. **API Performance**
   - Request rate per endpoint
   - Error rate (4xx, 5xx)
   - Response times

3. **Security Events**
   - Failed auth attempts
   - RLS policy violations
   - Unusual access patterns

### Supabase Dashboard Monitoring

- **Realtime Inspector**: Monitor live queries
- **API Logs**: Track all API calls
- **Database Metrics**: CPU, Memory, Storage
- **Auth Logs**: Login attempts, token issues

### External Monitoring Setup

```javascript
// Example: Track query performance
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

// Wrap queries with timing
async function trackedQuery(queryFn, queryName) {
  const start = Date.now();
  try {
    const result = await queryFn();
    const duration = Date.now() - start;
    console.log(`Query ${queryName}: ${duration}ms`);
    // Send to monitoring service (Datadog, etc.)
    return result;
  } catch (error) {
    console.error(`Query ${queryName} failed:`, error);
    throw error;
  }
}
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Query latency (p95) | > 500ms | > 2000ms |
| Error rate | > 1% | > 5% |
| Connection usage | > 70% | > 90% |
| Failed auth attempts | > 10/min | > 50/min |
| Storage usage | > 80% | > 95% |

---

## Environment Separation

### Project Structure

```
Production: budezivo-prod.supabase.co
├── Full RLS enforcement
├── Limited service role access
├── Production data only
└── Monitoring enabled

Staging: budezivo-staging.supabase.co
├── Clone of production schema
├── Test data
├── Same RLS policies
└── Used for pre-deployment testing

Development: budezivo-dev.supabase.co
├── Development data
├── May have relaxed RLS for testing
├── Local development connections
└── Schema experimentation
```

### Migration Workflow

```bash
# 1. Test migration on development
supabase db push --db-url=$DEV_DATABASE_URL

# 2. Review changes on staging
supabase db push --db-url=$STAGING_DATABASE_URL

# 3. Deploy to production
supabase db push --db-url=$PROD_DATABASE_URL

# Always backup before production migrations!
```

---

## Security Audit Checklist

### Weekly Checks

- [ ] Review failed authentication attempts
- [ ] Check for unusual API patterns
- [ ] Verify no new public table access
- [ ] Review recent team member changes

### Monthly Checks

- [ ] Run Supabase Security Advisor
- [ ] Review and rotate API keys if needed
- [ ] Audit RLS policies for gaps
- [ ] Test backup restoration
- [ ] Review user roles and permissions

### Quarterly Checks

- [ ] Full security audit
- [ ] Penetration testing
- [ ] GDPR compliance review
- [ ] Update security documentation

---

## Quick Commands Reference

```sql
-- Check RLS status on all tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';

-- List all policies
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- Test policy as specific role
SET ROLE authenticated;
SET request.jwt.claims = '{"app_metadata": {"institution_id": "uuid-here", "role": "edukator"}}';
SELECT * FROM programs; -- Should only return allowed rows
RESET ROLE;

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Find missing indexes
SELECT schemaname, tablename, attname, null_frac, avg_width, n_distinct
FROM pg_stats
WHERE schemaname = 'public' AND tablename IN ('reservations', 'programs');
```

---

## Support & Resources

- **Supabase Documentation**: https://supabase.com/docs
- **RLS Deep Dive**: https://supabase.com/docs/guides/auth/row-level-security
- **Production Checklist**: https://supabase.com/docs/guides/platform/going-into-prod
- **Security Best Practices**: https://supabase.com/docs/guides/auth/managing-user-data

---

*Last Updated: December 2025*
*Version: 1.0.0*
