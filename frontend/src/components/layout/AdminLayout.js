import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AuthContext } from '../../context/AuthContext';
import { LayoutDashboard, Calendar, BookOpen, School, BarChart3, Settings, Users, LogOut } from 'lucide-react';

// Minimalistické logo Budeživo.cz
const BudezivoLogo = ({ showText = true }) => (
  <div className="flex items-center gap-2">
    <div className="w-8 h-8 rounded-lg bg-[#4A6FA5] flex items-center justify-center">
      <svg 
        width="18" 
        height="18" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="white" 
        strokeWidth="2.5" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </div>
    {showText && (
      <span className="font-bold text-[#4A6FA5] text-xl tracking-tight">
        Budeživo<span className="text-[#C4AB86]">.cz</span>
      </span>
    )}
  </div>
);

export const AdminLayout = ({ children }) => {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = React.useContext(AuthContext);

  // Role-based navigation
  const getNavItems = () => {
    const baseItems = [
      { path: '/admin', icon: LayoutDashboard, label: 'Přehled', testId: 'nav-dashboard', roles: ['admin', 'staff', 'viewer'] },
      { path: '/admin/programs', icon: Calendar, label: 'Programy', testId: 'nav-programs', roles: ['admin', 'staff', 'viewer'] },
      { path: '/admin/bookings', icon: BookOpen, label: 'Rezervace', testId: 'nav-bookings', roles: ['admin', 'staff', 'viewer'] },
      { path: '/admin/schools', icon: School, label: 'Školy', testId: 'nav-schools', roles: ['admin', 'staff'] },
      { path: '/admin/statistics', icon: BarChart3, label: 'Statistiky', testId: 'nav-statistics', roles: ['admin', 'staff'] },
      { path: '/admin/team', icon: Users, label: 'Tým', testId: 'nav-team', roles: ['admin'] },
      { path: '/admin/settings', icon: Settings, label: 'Nastavení', testId: 'nav-settings', roles: ['admin'] },
    ];

    const userRole = user?.role || 'viewer';
    return baseItems.filter(item => item.roles.includes(userRole));
  };

  const navItems = getNavItems();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Role badge color
  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': return 'bg-[#4A6FA5] text-white';
      case 'staff': return 'bg-[#84A98C] text-white';
      case 'viewer': return 'bg-gray-200 text-gray-700';
      default: return 'bg-gray-200 text-gray-700';
    }
  };

  const getRoleLabel = (role) => {
    switch (role) {
      case 'admin': return 'Administrátor';
      case 'staff': return 'Zaměstnanec';
      case 'viewer': return 'Návštěvník';
      default: return 'Uživatel';
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
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
              <p className="text-xs text-muted-foreground">{user?.email}</p>
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
                <span className="text-xs mt-1">{item.label}</span>
              </Link>
            );
          })}
        </div>
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
