import React, { useEffect, useState, useContext } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { AuthContext } from '../../context/AuthContext';
import axios from 'axios';
import { Calendar, Users, TrendingUp, AlertCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const DashboardPage = () => {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{t('dashboard.welcome')}</h1>
          <p className="text-muted-foreground mt-1">{user?.institution_name}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="p-6" data-testid="dashboard-today-bookings">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.todayBookings')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats?.today_bookings || 0}</p>
              </div>
              <div className="w-12 h-12 bg-[#84A98C] rounded-full flex items-center justify-center">
                <Calendar className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="p-6" data-testid="dashboard-upcoming-groups">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.upcomingGroups')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats?.upcoming_groups || 0}</p>
              </div>
              <div className="w-12 h-12 bg-[#E9C46A] rounded-full flex items-center justify-center">
                <Users className="w-6 h-6 text-slate-900" />
              </div>
            </div>
          </Card>

          <Card className="p-6" data-testid="dashboard-capacity-usage">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.capacityUsage')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats?.capacity_usage?.toFixed(0) || 0}%</p>
              </div>
              <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="p-6" data-testid="dashboard-booking-limit">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.bookingLimit')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">
                  {stats?.bookings_used || 0}/{stats?.bookings_limit || 50}
                </p>
              </div>
              <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>
        </div>

        <Card className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">{t('nav.bookings')}</h2>
          <p className="text-muted-foreground">{t('common.noResults')}</p>
        </Card>
      </div>
    </AdminLayout>
  );
};
