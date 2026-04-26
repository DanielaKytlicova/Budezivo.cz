/**
 * LecturerProfilePage — combined view of Availability + My Profile
 * inside a single AdminLayout shell.
 *
 * Both child pages support an `embedded` prop that returns content WITHOUT
 * the AdminLayout wrapper, so we get exactly one layout (no duplicated
 * sidebar / mobile nav / impersonation banner).
 *
 * NO backend / API / DB / role / feature-flag logic is changed — this is a
 * pure UI composition that re-uses the existing pages' children.
 */
import React from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { UnifiedAvailabilityPage } from './UnifiedAvailabilityPage';
import { MyProfilePage } from './MyProfilePage';

export const LecturerProfilePage = () => (
  <AdminLayout>
    <div className="space-y-10" data-testid="lecturer-profile-page">
      {/* 1) Calendar / availability — full existing logic via embedded mode */}
      <UnifiedAvailabilityPage embedded />

      {/* 2) Profile sections — full existing logic via embedded mode.
          MyProfilePage owns its own save flow → PATCH /api/team/{id}/lecturer-profile */}
      <MyProfilePage embedded />
    </div>
  </AdminLayout>
);

export default LecturerProfilePage;
