import React from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const StatisticsPage = () => {
  const { t } = useTranslation();

  const bookingsData = [
    { month: 'Jan', bookings: 45 },
    { month: 'Feb', bookings: 52 },
    { month: 'Mar', bookings: 38 },
    { month: 'Apr', bookings: 65 },
    { month: 'May', bookings: 73 },
    { month: 'Jun', bookings: 58 },
  ];

  const programsData = [
    { program: 'Program A', count: 125 },
    { program: 'Program B', count: 98 },
    { program: 'Program C', count: 67 },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('statistics.title')}</h1>

        <Card className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-6">{t('statistics.bookingsOverTime')}</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={bookingsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="bookings" fill="#84A98C" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-6">{t('statistics.popularPrograms')}</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={programsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="program" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#E9C46A" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </AdminLayout>
  );
};
