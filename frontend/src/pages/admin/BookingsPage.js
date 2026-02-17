import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import { format } from 'date-fns';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const BookingsPage = () => {
  const { t } = useTranslation();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    try {
      const response = await axios.get(`${API}/bookings`);
      setBookings(response.data);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await axios.patch(`${API}/bookings/${id}/status?status=${status}`);
      toast.success(t('common.success'));
      fetchBookings();
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
    };
    return (
      <Badge className={variants[status] || 'bg-gray-100 text-gray-800'}>
        {t(`bookings.statuses.${status}`)}
      </Badge>
    );
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('bookings.title')}</h1>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          </div>
        ) : bookings.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-muted-foreground">{t('common.noResults')}</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {bookings.map((booking) => (
              <Card key={booking.id} className="p-6" data-testid={`booking-card-${booking.id}`}>
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-slate-900">{booking.school_name}</h3>
                      {getStatusBadge(booking.status)}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground block">{t('bookings.date')}:</span>
                        <span className="font-medium">{booking.date}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">{t('bookings.program')}:</span>
                        <span className="font-medium">{booking.program_id}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">{t('bookings.numStudents')}:</span>
                        <span className="font-medium">{booking.num_students}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">{t('schools.contactPerson')}:</span>
                        <span className="font-medium">{booking.contact_name}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {booking.status === 'pending' && (
                      <>
                        <Button
                          size="sm"
                          data-testid={`confirm-booking-${booking.id}`}
                          onClick={() => updateStatus(booking.id, 'confirmed')}
                          className="bg-[#84A98C] hover:bg-[#84A98C]/90"
                        >
                          {t('bookings.confirm')}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          data-testid={`cancel-booking-${booking.id}`}
                          onClick={() => updateStatus(booking.id, 'cancelled')}
                          className="text-red-600 hover:text-red-700"
                        >
                          {t('bookings.cancel')}
                        </Button>
                      </>
                    )}
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
