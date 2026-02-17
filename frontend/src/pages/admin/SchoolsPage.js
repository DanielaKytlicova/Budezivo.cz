import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const SchoolsPage = () => {
  const { t } = useTranslation();
  const [schools, setSchools] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSchools();
  }, []);

  const fetchSchools = async () => {
    try {
      const response = await axios.get(`${API}/schools`);
      setSchools(response.data);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('schools.title')}</h1>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          </div>
        ) : schools.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-muted-foreground">{t('common.noResults')}</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {schools.map((school) => (
              <Card key={school.id} className="p-6" data-testid={`school-card-${school.id}`}>
                <h3 className="text-lg font-semibold text-slate-900 mb-4">{school.name}</h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">{t('schools.contactPerson')}: </span>
                    <span className="font-medium">{school.contact_person}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('schools.email')}: </span>
                    <span className="font-medium">{school.email}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('schools.phone')}: </span>
                    <span className="font-medium">{school.phone}</span>
                  </div>
                  <div className="mt-4 pt-4 border-t border-border">
                    <span className="text-muted-foreground">{t('schools.bookingHistory')}: </span>
                    <span className="font-semibold text-[#84A98C]">{school.booking_count || 0}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  );
};
