import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import { BookingPage } from './pages/public/BookingPage';
import { GDPRPage } from './pages/public/GDPRPage';
import { ContactPage } from './pages/public/ContactPage';

// Admin pages
import { DashboardPage } from './pages/admin/DashboardPage';
import { ProgramsPage } from './pages/admin/ProgramsPage';
import { BookingsPage } from './pages/admin/BookingsPage';
import { SchoolsPage } from './pages/admin/SchoolsPage';
import { StatisticsPage } from './pages/admin/StatisticsPage';
import { SettingsPage } from './pages/admin/SettingsPage';
import { PlanPage } from './pages/admin/PlanPage';
import { TeamPage } from './pages/admin/TeamPage';

import './App.css';

function App() {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>
          <ThemeProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/booking/:institutionId" element={<BookingPage />} />
              <Route path="/gdpr" element={<GDPRPage />} />

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
