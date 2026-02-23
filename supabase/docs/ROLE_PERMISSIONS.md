# ============================================================
# ROLE PERMISSIONS QUICK REFERENCE
# Budeživo.cz - Cultural Institution Booking System
# ============================================================

## Role Hierarchy

```
admin/spravce (Správce)
    └── edukator (Edukátor)
        └── lektor (Externí lektor)
    └── pokladni (Pokladní)
        └── viewer (Prohlížeč)
```

## Permission Matrix

| Resource | Action | admin | edukator | lektor | pokladni | viewer |
|----------|--------|-------|----------|--------|----------|--------|
| **Institutions** |
| | View Settings | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Edit Settings | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Delete | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Users/Team** |
| | View Members | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Invite | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Change Role | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Remove | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Edit Self | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Programs** |
| | View All | ✅ | ✅ | ❌ | ✅ | ✅ |
| | View Assigned | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Create | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Edit | ✅ | ✅ | ⚠️¹ | ❌ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Assign Lecturer | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Reservations** |
| | View All | ✅ | ✅ | ❌ | ✅ | ✅ |
| | View Assigned | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Confirm | ✅ | ✅ | ⚠️¹ | ❌ | ❌ |
| | Cancel | ✅ | ✅ | ⚠️¹ | ❌ | ❌ |
| | Edit Details | ✅ | ✅ | ⚠️¹ | ❌ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Payments** |
| | View | ✅ | ❌ | ❌ | ✅ | ❌ |
| | Create | ✅ | ❌ | ❌ | ✅ | ❌ |
| | Update Status | ✅ | ❌ | ❌ | ✅ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Schools (CRM)** |
| | View | ✅ | ✅ | ❌ | ❌ | ✅ |
| | Edit | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Theme Settings** |
| | View | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Edit | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Audit Logs** |
| | View | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Statistics** |
| | View Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| | View Reports | ✅ | ✅ | ❌ | ❌ | ❌ |

**Legend:**
- ✅ Full access
- ⚠️¹ Only for assigned items
- ❌ No access

## Role Descriptions

### Správce (admin)
Full administrative access within the institution. Can manage all settings, users, programs, and data. The only role that can invite new users and delete records.

**Typical user:** Institution director, IT administrator

### Edukátor (edukator)
Can manage educational programs and reservations. Cannot modify institution settings or manage team members.

**Typical user:** Education coordinator, program manager

### Externí lektor (lektor)
Limited access to only programs and reservations assigned to them. Cannot see other institution data.

**Typical user:** External lecturer, guest speaker, contractor

### Pokladní (pokladni)
Focused on payment processing. Can view reservations but cannot modify booking details. Full access to payment records.

**Typical user:** Cashier, accountant, finance staff

### Prohlížeč (viewer)
Read-only access to programs, reservations, and schools. Cannot modify any data.

**Typical user:** Intern, temporary staff, auditor

## Implementation Notes

### RLS Policy Structure
```sql
-- Check user role
auth.user_role() IN ('admin', 'spravce')

-- Check institution membership
institution_id = auth.institution_id()

-- Check assignment (for lecturers)
assigned_lecturer_id = auth.user_id()
```

### Role Hierarchy Functions
```sql
-- Is admin or higher
auth.is_admin() → admin, spravce

-- Is educator or higher
auth.is_educator() → admin, spravce, edukator

-- Is lecturer or higher
auth.is_lecturer() → admin, spravce, edukator, lektor

-- Is cashier or higher
auth.is_cashier() → admin, spravce, pokladni
```

## Security Considerations

1. **Role Assignment**: Only admins can change roles
2. **Self-Protection**: Users cannot demote themselves
3. **Tenant Isolation**: All access is scoped to institution_id
4. **Audit Trail**: All role changes are logged
5. **Soft Delete**: Records are never hard-deleted

---

*Version: 1.0.0*
*Last Updated: December 2025*
