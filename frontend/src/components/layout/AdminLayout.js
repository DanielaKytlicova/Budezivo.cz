import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AuthContext } from '../../context/AuthContext';
import { LayoutDashboard, Calendar, BookOpen, School, BarChart3, Settings, Users, LogOut, MessageSquare, Clock, FileText } from 'lucide-react';

// Logo Budeživo.cz - oficiální SVG
const BudezivoLogo = ({ showText = true }) => (
  <div className="flex items-center">
    {showText ? (
      <svg 
        viewBox="0 0 265.42 73.09" 
        className="h-10 w-auto"
        aria-label="Budeživo.cz"
      >
        <defs>
          <style>{`.admin-logo-blue{fill:#5a7aae;}.admin-logo-gold{fill:#c5ac87;}`}</style>
        </defs>
        <path className="admin-logo-blue" d="M41.23,40.83a5.17,5.17,0,0,0-2.42-.69V39.9a5.64,5.64,0,0,0,2.1-.88,4.54,4.54,0,0,0,1.43-1.62,4.61,4.61,0,0,0,.52-2.22A5,5,0,0,0,42,32.29a5.43,5.43,0,0,0-2.48-1.94,10.42,10.42,0,0,0-4.09-.7h-9V51.48h9.73a9.64,9.64,0,0,0,4.12-.8,6,6,0,0,0,2.57-2.16,5.69,5.69,0,0,0,.88-3.14A5.26,5.26,0,0,0,43,42.64,5,5,0,0,0,41.23,40.83Zm-9.65-7h3.09a3.28,3.28,0,0,1,2.13.64,2.13,2.13,0,0,1,.79,1.75,2.28,2.28,0,0,1-.39,1.34,2.58,2.58,0,0,1-1.07.84,4,4,0,0,1-1.54.29h-3Zm5.91,12.85a4,4,0,0,1-2.57.67H31.58V42H35a4.12,4.12,0,0,1,1.76.34,2.67,2.67,0,0,1,1.14,1,2.75,2.75,0,0,1,.39,1.48A2.22,2.22,0,0,1,37.49,46.63Z"/>
        <path className="admin-logo-blue" d="M56.91,44.44a3.48,3.48,0,0,1-.35,1.64,2.5,2.5,0,0,1-1,1,2.91,2.91,0,0,1-1.47.36,2.51,2.51,0,0,1-2-.79,3.06,3.06,0,0,1-.71-2.16V35.1H46.34V45.53a7.09,7.09,0,0,0,.7,3.24,5.21,5.21,0,0,0,2,2.15,5.77,5.77,0,0,0,3,.76,4.82,4.82,0,0,0,3.43-1.19,6.67,6.67,0,0,0,1.69-2.59l.08,3.58H62V35.1H56.91Z"/>
        <path className="admin-logo-blue" d="M76.05,37.91h-.12a5.3,5.3,0,0,0-.9-1.44,4.65,4.65,0,0,0-1.52-1.13,5,5,0,0,0-2.22-.45,6.08,6.08,0,0,0-3.21.9,6.46,6.46,0,0,0-2.4,2.77,10.8,10.8,0,0,0-.91,4.74A10.81,10.81,0,0,0,65.65,48,6.4,6.4,0,0,0,68,50.77a6,6,0,0,0,3.31.94,5.07,5.07,0,0,0,2.16-.42A4.79,4.79,0,0,0,75,50.22a5.33,5.33,0,0,0,.93-1.4h.18v2.66h5V29.65h-5.1Zm-.25,7.72a3.54,3.54,0,0,1-1.06,1.55,2.66,2.66,0,0,1-1.67.55,2.59,2.59,0,0,1-1.66-.55,3.4,3.4,0,0,1-1-1.56A6.86,6.86,0,0,1,70,43.3,6.78,6.78,0,0,1,70.38,41a3.38,3.38,0,0,1,1-1.54,2.54,2.54,0,0,1,1.66-.55,2.65,2.65,0,0,1,1.67.54A3.33,3.33,0,0,1,75.8,41a7.78,7.78,0,0,1,0,4.68Z"/>
        <path className="admin-logo-blue" d="M97.65,37a6.9,6.9,0,0,0-2.51-1.61A9,9,0,0,0,92,34.89,8.44,8.44,0,0,0,87.69,36a7.23,7.23,0,0,0-2.8,3,9.44,9.44,0,0,0-1,4.42,9.63,9.63,0,0,0,1,4.52,6.9,6.9,0,0,0,2.85,2.91,9.16,9.16,0,0,0,4.42,1,10.13,10.13,0,0,0,3.53-.57,6.65,6.65,0,0,0,2.53-1.62,5.8,5.8,0,0,0,1.41-2.45l-4.55-.75a2.55,2.55,0,0,1-.61.93,2.68,2.68,0,0,1-1,.57,4,4,0,0,1-1.25.19,3.5,3.5,0,0,1-1.74-.42,2.87,2.87,0,0,1-1.17-1.26A4.54,4.54,0,0,1,89,44.53H99.87V43.24a10.16,10.16,0,0,0-.58-3.59A7.26,7.26,0,0,0,97.65,37ZM89,41.56a4.46,4.46,0,0,1,.3-1.27,2.87,2.87,0,0,1,1-1.25A3.1,3.1,0,0,1,92,38.6a3,3,0,0,1,1.67.44,2.74,2.74,0,0,1,1,1.26A4.67,4.67,0,0,1,95,41.56Z"/>
        <path className="admin-logo-blue" d="M200.58,46.32a2.71,2.71,0,0,0-2,.78,2.78,2.78,0,0,0,0,3.9,2.88,2.88,0,0,0,3.94,0,2.78,2.78,0,0,0,0-3.9A2.71,2.71,0,0,0,200.58,46.32Z"/>
        <path className="admin-logo-blue" d="M217.66,46.27a3.33,3.33,0,0,1-.6.88,2.44,2.44,0,0,1-.82.54,2.73,2.73,0,0,1-1,.18,2.56,2.56,0,0,1-1.67-.55,3.35,3.35,0,0,1-1.05-1.57,7.4,7.4,0,0,1-.36-2.43,7.32,7.32,0,0,1,.36-2.43,3.24,3.24,0,0,1,1.05-1.55,2.61,2.61,0,0,1,1.67-.54,2.8,2.8,0,0,1,1,.18,2.24,2.24,0,0,1,.8.53,3,3,0,0,1,.59.85A4.49,4.49,0,0,1,218,41.5l4.71-.79a6.6,6.6,0,0,0-.8-2.41,5.82,5.82,0,0,0-1.59-1.83A7.23,7.23,0,0,0,218,35.3a9.66,9.66,0,0,0-2.87-.41A8.78,8.78,0,0,0,210.75,36a7.23,7.23,0,0,0-2.84,3,10.38,10.38,0,0,0,0,8.85,7.17,7.17,0,0,0,2.84,3,8.67,8.67,0,0,0,4.41,1.06,9.46,9.46,0,0,0,2.88-.41,7.1,7.1,0,0,0,2.29-1.18,6.36,6.36,0,0,0,1.59-1.87,7.18,7.18,0,0,0,.8-2.47L218,45.09A4.53,4.53,0,0,1,217.66,46.27Z"/>
        <polygon className="admin-logo-blue" points="231.66 47.48 231.66 47.37 238.73 38.33 238.73 35.1 225.25 35.1 225.25 39.1 232.64 39.1 232.64 39.2 225 48.53 225 51.48 239.01 51.48 239.01 47.48 231.66 47.48"/>
        <path className="admin-logo-blue" d="M181.38,19.53h-35.8l-4.43,5h40.23A4.26,4.26,0,0,1,185.43,29v23.9a4.26,4.26,0,0,1-4.05,4.44H116a4.26,4.26,0,0,1-4-4.44V29a4.26,4.26,0,0,1,4-4.44h11.55l3.61-5H116A9.26,9.26,0,0,0,107,29v23.9a9.27,9.27,0,0,0,9,9.44h65.38a9.27,9.27,0,0,0,9.05-9.44V29A9.26,9.26,0,0,0,181.38,19.53Z"/>
        <polygon className="admin-logo-gold" points="119.77 48.53 119.77 51.48 133.78 51.48 133.78 47.48 126.42 47.48 126.42 47.37 133.5 38.33 133.5 35.1 120.02 35.1 120.02 39.1 127.41 39.1 127.41 39.2 119.77 48.53"/>
        <path className="admin-logo-gold" d="M141.6,29a2.66,2.66,0,0,0-1.87-.72,2.61,2.61,0,0,0-1.86.72,2.33,2.33,0,0,0,0,3.48,2.58,2.58,0,0,0,1.86.73,2.66,2.66,0,0,0,1.87-.72,2.28,2.28,0,0,0,.78-1.73A2.31,2.31,0,0,0,141.6,29Z"/>
        <rect className="admin-logo-gold" x="137.18" y="35.1" width="5.11" height="16.38"/>
        <path className="admin-logo-gold" d="M162.13,35.1h-5.34l-2.4,8c-.32,1.08-.6,2.19-.84,3.3-.09.41-.18.84-.26,1.27-.09-.43-.19-.86-.28-1.27-.24-1.13-.53-2.23-.86-3.3l-2.45-8h-5.39l5.94,16.38h5.91Z"/>
        <path className="admin-logo-gold" d="M166.74,50.72a9.7,9.7,0,0,0,8.82,0,7.08,7.08,0,0,0,2.83-3,10.48,10.48,0,0,0,0-8.85,7.14,7.14,0,0,0-2.83-3,9.7,9.7,0,0,0-8.82,0,7.21,7.21,0,0,0-2.83,3,10.38,10.38,0,0,0,0,8.85A7.15,7.15,0,0,0,166.74,50.72Zm1.74-9.79a3.41,3.41,0,0,1,1-1.57,2.73,2.73,0,0,1,3.31,0,3.41,3.41,0,0,1,1,1.57,8.54,8.54,0,0,1,0,4.77,3.46,3.46,0,0,1-1,1.6,2.69,2.69,0,0,1-3.31,0,3.46,3.46,0,0,1-1-1.6,8.3,8.3,0,0,1,0-4.77Z"/>
        <polygon className="admin-logo-gold" points="126.8 30.85 124.7 28.39 120.38 28.39 120.38 28.39 120.38 28.48 120.38 28.48 124.94 32.99 128.64 32.99 133.2 28.48 136.69 24.53 141.12 19.53 148.87 10.78 141.58 10.78 135.27 19.53 131.66 24.53 128.88 28.39 126.8 30.85"/>
      </svg>
    ) : (
      <svg 
        viewBox="0 0 73.42 73.09" 
        className="h-10 w-10"
        aria-label="Budeživo.cz"
      >
        <defs>
          <style>{`.admin-icon-blue{fill:#5a7aae;}.admin-icon-gold{fill:#c5ac87;}`}</style>
        </defs>
        <path className="admin-icon-blue" d="M46.9,55A1.87,1.87,0,0,1,45,56.84H14.88A1.87,1.87,0,0,1,13,55V24.83A1.87,1.87,0,0,1,14.88,23H37.74l6.43-8.91H14.88A10.79,10.79,0,0,0,4.11,24.83V55A10.78,10.78,0,0,0,14.88,65.74H45A10.78,10.78,0,0,0,55.8,55V31.55L46.9,41.6Z"/>
        <polygon className="admin-icon-gold" points="30.01 43.07 26.28 38.69 18.58 38.69 18.58 38.85 26.7 46.88 33.3 46.88 41.41 38.85 46.9 32.65 55.6 22.83 69.31 7.35 56.32 7.35 50.41 15.55 45.06 22.96 33.71 38.69 30.01 43.07"/>
      </svg>
    )}
  </div>
);

export const AdminLayout = ({ children }) => {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = React.useContext(AuthContext);

  // Role-based navigation - nové role podle wireframu
  const getNavItems = () => {
    const baseItems = [
      { path: '/admin', icon: LayoutDashboard, label: 'Přehled', testId: 'nav-dashboard', roles: ['admin', 'spravce', 'edukator', 'lektor', 'pokladni', 'staff', 'viewer'] },
      { path: '/admin/programs', icon: Calendar, label: 'Programy', testId: 'nav-programs', roles: ['admin', 'spravce', 'edukator', 'staff', 'viewer'] },
      { path: '/admin/bookings', icon: BookOpen, label: 'Rezervace', testId: 'nav-bookings', roles: ['admin', 'spravce', 'edukator', 'lektor', 'pokladni', 'staff', 'viewer'] },
      { path: '/admin/schools', icon: School, label: 'Školy', testId: 'nav-schools', roles: ['admin', 'spravce', 'edukator', 'staff'] },
      { path: '/admin/feedback', icon: MessageSquare, label: 'Zpětná vazba', testId: 'nav-feedback', roles: ['admin', 'spravce', 'edukator', 'staff'] },
      { path: '/admin/availability', icon: Clock, label: 'Dostupnost', testId: 'nav-availability', roles: ['admin', 'spravce', 'edukator', 'lektor'] },
      { path: '/admin/statistics', icon: BarChart3, label: 'Statistiky', testId: 'nav-statistics', roles: ['admin', 'spravce', 'edukator', 'staff'] },
      { path: '/admin/team', icon: Users, label: 'Tým', testId: 'nav-team', roles: ['admin', 'spravce'] },
      { path: '/admin/settings', icon: Settings, label: 'Nastavení', testId: 'nav-settings', roles: ['admin', 'spravce'] },
    ];

    const userRole = user?.role || 'viewer';
    return baseItems.filter(item => item.roles.includes(userRole));
  };

  const navItems = getNavItems();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Role badge color - nové role
  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': 
      case 'spravce': return 'bg-[#2B3E50] text-white';
      case 'edukator':
      case 'staff': return 'bg-[#4A6FA5] text-white';
      case 'lektor': return 'bg-[#84A98C] text-white';
      case 'pokladni': return 'bg-[#C4AB86] text-white';
      case 'viewer': return 'bg-gray-200 text-gray-700';
      default: return 'bg-gray-200 text-gray-700';
    }
  };

  const getRoleLabel = (role) => {
    switch (role) {
      case 'admin': 
      case 'spravce': return 'Správce';
      case 'edukator':
      case 'staff': return 'Edukator';
      case 'lektor': return 'Externí lektor';
      case 'pokladni': return 'Pokladní';
      case 'viewer': return 'Návštěvník';
      default: return 'Uživatel';
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      {/* Desktop Sidebar */}
      <aside className="hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col">
        <div className="flex flex-col flex-grow border-r border-border bg-white overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-6 py-6 border-b border-border">
            <Link to="/">
              <BudezivoLogo />
            </Link>
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
              <p className="text-xs text-muted-foreground">{user?.name || user?.email}</p>
              <span className={`inline-block mt-2 px-2 py-0.5 text-xs rounded-full ${getRoleBadgeColor(user?.role)}`}>
                {getRoleLabel(user?.role)}
              </span>
            </div>
            <button
              data-testid="admin-logout-button"
              onClick={handleLogout}
              className="w-full flex items-center px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
            >
              <LogOut className="mr-3 h-5 w-5" />
              Odhlásit se
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 bg-white border-b border-border z-50 px-4 h-14 flex items-center justify-between">
        <Link to="/">
          <BudezivoLogo showText={false} />
        </Link>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 text-xs rounded-full ${getRoleBadgeColor(user?.role)}`}>
            {getRoleLabel(user?.role)}
          </span>
          <button
            onClick={handleLogout}
            className="p-2 text-slate-600 hover:text-slate-800"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-border z-50">
        {(() => {
          const userRole = user?.role || 'viewer';
          const isAdmin = ['admin', 'spravce'].includes(userRole);
          const settingsItem = navItems.find(item => item.path === '/admin/settings');
          const mobileItems = isAdmin && settingsItem
            ? [...navItems.slice(0, 4), settingsItem]
            : navItems.slice(0, 4);
          return (
            <div className={`grid gap-1 p-2 ${mobileItems.length === 5 ? 'grid-cols-5' : 'grid-cols-4'}`}>
              {mobileItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path || 
                  (item.path === '/admin/settings' && location.pathname.startsWith('/admin/settings'));
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
                    <span className="text-xs mt-1">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          );
        })()}
      </nav>

      {/* Main Content */}
      <div className="md:pl-64 pt-14 md:pt-0">
        <main className="py-6 px-4 md:px-8 pb-20 md:pb-6">
          {children}
        </main>
      </div>
    </div>
  );
};
