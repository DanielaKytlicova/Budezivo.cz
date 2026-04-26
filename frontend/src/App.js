import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from './components/ui/sonner';
import { LanguageProvider } from './context/LanguageContext';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';

// Public pages
import { HomePage } from './pages/public/HomePage';
import { LoginPage } from './pages/public/LoginPage';
import { RegisterPage } from './pages/public/RegisterPage';
import { ForgotPasswordPage } from './pages/public/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/public/ResetPasswordPage';
import { BookingPage } from './pages/public/BookingPage';
import { GDPRPage } from './pages/public/GDPRPage';
import { ContactPage } from './pages/public/ContactPage';
import FeedbackPage from './pages/public/FeedbackPage';
import AcceptInvitePage from './pages/public/AcceptInvitePage';
import TermsPage from './pages/public/TermsPage';
import { VopPage } from './pages/public/VopPage';

// Admin pages
import { DashboardPage } from './pages/admin/DashboardPage';
import { ProgramsPage } from './pages/admin/ProgramsPage';
import { BookingsPage } from './pages/admin/BookingsPage';
import { SchoolsPage } from './pages/admin/SchoolsPage';
import { StatisticsPage } from './pages/admin/StatisticsPage';
import { SettingsPage } from './pages/admin/SettingsPage';
import { PlanPage } from './pages/admin/PlanPage';
import { TeamPage } from './pages/admin/TeamPage';
import { MyProfilePage } from './pages/admin/MyProfilePage';
import FeedbackAdminPage from './pages/admin/FeedbackAdminPage';
import { UnifiedAvailabilityPage } from './pages/admin/UnifiedAvailabilityPage';
import { ArchivePage } from './pages/admin/ArchivePage';
import { AuditLogPage } from './pages/admin/AuditLogPage';
import { EventsPage } from './pages/admin/EventsPage';
import { WaitlistPage } from './pages/admin/WaitlistPage';
import { MailingsPage } from './pages/admin/MailingsPage';
import { SuperadminPage } from './pages/admin/SuperadminPage';
import PublicEventsPage from './pages/public/PublicEventsPage';
import PaymentReturnPage from './pages/public/PaymentReturnPage';
import PaymentMockPage from './pages/public/PaymentMockPage';
import CatalogPage from './pages/public/CatalogPage';
import CatalogDetailPage from './pages/public/CatalogDetailPage';

import './App.css';

// Component to handle dynamic page title
function TitleUpdater() {
  const location = useLocation();
  
  useEffect(() => {
    const isAdminRoute = location.pathname.startsWith('/admin');
    document.title = isAdminRoute ? 'Dashboard Bude živo' : 'Bude živo';
  }, [location]);
  
  return null;
}

function App() {
  return (
    <BrowserRouter>
      <TitleUpdater />
      <LanguageProvider>
        <AuthProvider>
          <ThemeProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
              <Route path="/booking/:institutionId" element={<BookingPage />} />
              <Route path="/gdpr" element={<GDPRPage />} />
              <Route path="/kontakt" element={<ContactPage />} />
              <Route path="/feedback/:token" element={<FeedbackPage />} />
              <Route path="/accept-invite" element={<AcceptInvitePage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/obchodni-podminky" element={<VopPage />} />
              <Route path="/events/:institutionId" element={<PublicEventsPage />} />
              <Route path="/payment/return" element={<PaymentReturnPage />} />
              <Route path="/payment/mock" element={<PaymentMockPage />} />

              {/* B2B catalog "Programy pro školy" — hidden from main nav, accessible by URL only */}
              <Route path="/programy-pro-skoly" element={<CatalogPage />} />
              <Route path="/programy-pro-skoly/p/:id" element={<CatalogDetailPage />} />
              <Route path="/programy-pro-skoly/:slug" element={<CatalogPage />} />

              {/* Admin routes */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/programs"
                element={
                  <ProtectedRoute>
                    <ProgramsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/bookings"
                element={
                  <ProtectedRoute>
                    <BookingsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/schools"
                element={
                  <ProtectedRoute>
                    <SchoolsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/statistics"
                element={
                  <ProtectedRoute>
                    <StatisticsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/settings"
                element={
                  <ProtectedRoute>
                    <SettingsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/plan"
                element={
                  <ProtectedRoute>
                    <PlanPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/team"
                element={
                  <ProtectedRoute>
                    <TeamPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/my-profile"
                element={
                  <ProtectedRoute>
                    <MyProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/feedback"
                element={
                  <ProtectedRoute>
                    <FeedbackAdminPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/availability"
                element={
                  <ProtectedRoute>
                    <UnifiedAvailabilityPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/archive"
                element={
                  <ProtectedRoute>
                    <ArchivePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/audit-log"
                element={
                  <ProtectedRoute>
                    <AuditLogPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/events"
                element={
                  <ProtectedRoute>
                    <EventsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/waitlist"
                element={
                  <ProtectedRoute>
                    <WaitlistPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/mailings"
                element={
                  <ProtectedRoute>
                    <MailingsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/superadmin"
                element={
                  <ProtectedRoute>
                    <SuperadminPage />
                  </ProtectedRoute>
                }
              />

              {/* Catch all */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            <Toaster position="top-right" />
          </ThemeProvider>
        </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}

export default App;
