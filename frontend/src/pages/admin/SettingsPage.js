import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const SettingsPage = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    primary_color: '#1E293B',
    secondary_color: '#84A98C',
    accent_color: '#E9C46A',
    header_style: 'light',
    footer_text: '',
    logo_url: '',
  });

  useEffect(() => {
    fetchThemeSettings();
  }, []);

  const fetchThemeSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings/theme`);
      setFormData(response.data);
    } catch (error) {
      console.error('Error fetching theme settings:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.put(`${API}/settings/theme`, formData);
      toast.success(t('common.success'));
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('settings.title')}</h1>

        <Card className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-6">{t('settings.theme')}</h2>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="settings-form">
            <div>
              <Label htmlFor="logo_url">{t('settings.logo')}</Label>
              <div className="mt-2 space-y-2">
                <Input
                  id="logo_url"
                  type="url"
                  data-testid="logo-url-input"
                  value={formData.logo_url}
                  onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
                  placeholder="https://example.com/logo.png"
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Zadejte URL adresu vašeho loga (doporučená velikost: 200x60px)
                </p>
                {formData.logo_url && (
                  <div className="mt-4 p-4 border border-border rounded-md bg-muted">
                    <p className="text-sm font-medium mb-2">Náhled:</p>
                    <img
                      src={formData.logo_url}
                      alt="Logo preview"
                      className="max-h-16 object-contain"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentElement.innerHTML += '<p class="text-sm text-red-600">Nepodařilo se načíst obrázek</p>';
                      }}
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <Label htmlFor="primary_color">{t('settings.primaryColor')}</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    id="primary_color"
                    type="color"
                    data-testid="primary-color-input"
                    value={formData.primary_color}
                    onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                    className="w-20 h-10"
                  />
                  <Input
                    value={formData.primary_color}
                    onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                    className="flex-1"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="secondary_color">{t('settings.secondaryColor')}</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    id="secondary_color"
                    type="color"
                    data-testid="secondary-color-input"
                    value={formData.secondary_color}
                    onChange={(e) => setFormData({ ...formData, secondary_color: e.target.value })}
                    className="w-20 h-10"
                  />
                  <Input
                    value={formData.secondary_color}
                    onChange={(e) => setFormData({ ...formData, secondary_color: e.target.value })}
                    className="flex-1"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="accent_color">{t('settings.accentColor')}</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    id="accent_color"
                    type="color"
                    data-testid="accent-color-input"
                    value={formData.accent_color}
                    onChange={(e) => setFormData({ ...formData, accent_color: e.target.value })}
                    className="w-20 h-10"
                  />
                  <Input
                    value={formData.accent_color}
                    onChange={(e) => setFormData({ ...formData, accent_color: e.target.value })}
                    className="flex-1"
                  />
                </div>
              </div>
            </div>

            <div>
              <Label htmlFor="header_style">{t('settings.headerStyle')}</Label>
              <Select
                value={formData.header_style}
                onValueChange={(value) => setFormData({ ...formData, header_style: value })}
              >
                <SelectTrigger className="mt-2" data-testid="header-style-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">{t('settings.headerStyles.light')}</SelectItem>
                  <SelectItem value="dark">{t('settings.headerStyles.dark')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              type="submit"
              data-testid="settings-submit-button"
              className="bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90"
              disabled={loading}
            >
              {loading ? t('common.loading') : t('settings.save')}
            </Button>
          </form>
        </Card>
      </div>
    </AdminLayout>
  );
};
