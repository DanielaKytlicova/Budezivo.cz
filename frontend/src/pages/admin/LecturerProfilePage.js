/**
 * LecturerProfilePage — combined UI of Availability calendar + My Profile sections.
 *
 * IMPORTANT: This page is a thin UI composition; it MUST NOT change any backend
 * logic, endpoints, payloads, feature flags or DB schema. It only re-uses the
 * two existing pages as render-only sub-trees.
 *
 *   ┌──────────────────────────────────────────┐
 *   │  Calendar (UnifiedAvailabilityPage)      │
 *   ├──────────────────────────────────────────┤
 *   │  Profile sections (MyProfilePage)        │
 *   │   • Co mohu vést                         │
 *   │   • Co se chci naučit (náslech)          │
 *   │   • Preferované věkové skupiny           │
 *   │   • Základní údaje                       │
 *   │   • Poznámka od správce                  │
 *   └──────────────────────────────────────────┘
 *
 * Both child pages already wrap themselves in <AdminLayout>, so we render them
 * directly. This avoids duplicating their state/effects logic.
 */
import React from 'react';
import { UnifiedAvailabilityPage } from './UnifiedAvailabilityPage';
import { MyProfilePage } from './MyProfilePage';

export const LecturerProfilePage = () => (
  <div data-testid="lecturer-profile-page">
    {/* 1) Availability calendar — full existing logic (blocked days, time slots, capacities) */}
    <UnifiedAvailabilityPage />

    {/* 2) Profile sections — full existing logic (supported / learning programs, age groups, name, admin note).
        MyProfilePage handles its own save flow via PATCH /api/team/{user_id}/lecturer-profile. */}
    <MyProfilePage />
  </div>
);

export default LecturerProfilePage;
