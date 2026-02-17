import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AuthContext } from '../../context/AuthContext';
import { LayoutDashboard, Calendar, BookOpen, School, BarChart3, Settings, CreditCard, LogOut } from 'lucide-react';

export const AdminLayout = ({ children }) => {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = React.useContext(AuthContext);

  const navItems = [
    { path: '/admin', icon: LayoutDashboard, label: t('nav.dashboard'), testId: 'nav-dashboard' },
    { path: '/admin/programs', icon: Calendar, label: t('nav.programs'), testId: 'nav-programs' },
    { path: '/admin/bookings', icon: BookOpen, label: t('nav.bookings'), testId: 'nav-bookings' },
    { path: '/admin/schools', icon: School, label: t('nav.schools'), testId: 'nav-schools' },
    { path: '/admin/statistics', icon: BarChart3, label: t('nav.statistics'), testId: 'nav-statistics' },
    { path: '/admin/settings', icon: Settings, label: t('nav.settings'), testId: 'nav-settings' },
    { path: '/admin/plan', icon: CreditCard, label: t('nav.plan'), testId: 'nav-plan' },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      {/* Desktop Sidebar */}
      <aside className="hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col">
        <div className="flex flex-col flex-grow border-r border-border bg-white overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-6 py-6 border-b border-border">
            <h1 className="text-2xl font-bold text-primary">KulturaBooking</h1>
          </div>

          <div className="flex-1 flex flex-col px-4 py-6 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={item.testId}
                  className={`flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <Icon className="mr-3 h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          <div className="p-4 border-t border-border">
            <div className="px-4 py-3 bg-muted rounded-md mb-3">
              <p className="text-sm font-medium text-foreground">{user?.institution_name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <button
              data-testid="admin-logout-button"
              onClick={handleLogout}
              className="w-full flex items-center px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
            >
              <LogOut className="mr-3 h-5 w-5" />
              {t('nav.logout')}
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-border z-50">
        <div className="grid grid-cols-4 gap-1 p-2">
          {navItems.slice(0, 4).map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`mobile-${item.testId}`}
                className={`flex flex-col items-center py-2 px-1 rounded-md ${
                  isActive ? 'bg-slate-800 text-white' : 'text-slate-700'
                }`}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs mt-1">{item.label.split(' ')[0]}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main Content */}
      <div className="md:pl-64">
        <main className="py-6 px-4 md:px-8 pb-20 md:pb-6">
          {children}
        </main>
      </div>
    </div>
  );
};
