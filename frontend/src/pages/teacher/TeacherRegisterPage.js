import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Header } from '../../components/layout/Header';
import { Card } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Button } from '../../components/ui/button';
import { Loader2, GraduationCap } from 'lucide-react';
import { useTeacherAuth } from '../../context/TeacherAuthContext';
import { toast } from 'sonner';

export const TeacherRegisterPage = () => {
  const navigate = useNavigate();
  const { register } = useTeacherAuth();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    school_name: '',
    phone: '',
  });
  const [agree, setAgree] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');

  const onChange = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!agree) { setErr('Musíte odsouhlasit obchodní podmínky a GDPR.'); return; }
    if (form.password.length < 8) { setErr('Heslo musí mít alespoň 8 znaků.'); return; }
    setSubmitting(true);
    setErr('');
    const r = await register({
      ...form,
      email: form.email.trim().toLowerCase(),
      name: form.name.trim(),
      school_name: form.school_name.trim() || undefined,
      phone: form.phone.trim() || undefined,
    });
    setSubmitting(false);
    if (r.ok) {
      toast.success('Účet úspěšně vytvořen.');
      navigate('/ucitel/ucet');
    } else {
      setErr(r.error);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Header />
      <div className="max-w-md mx-auto px-4 py-12">
        <Card className="p-6 md:p-8" data-testid="teacher-register-page">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-[#4A6FA5] flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#2B3E50]">Registrace učitele</h1>
              <p className="text-sm text-gray-500">Účet je zdarma a kdykoliv ho můžete smazat.</p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <Label htmlFor="r-name">Jméno a příjmení *</Label>
              <Input id="r-name" required value={form.name} onChange={onChange('name')} data-testid="teacher-register-name" />
            </div>
            <div>
              <Label htmlFor="r-email">E-mail *</Label>
              <Input id="r-email" type="email" required value={form.email} onChange={onChange('email')} data-testid="teacher-register-email" />
            </div>
            <div>
              <Label htmlFor="r-password">Heslo (min. 8 znaků) *</Label>
              <Input id="r-password" type="password" required minLength={8} value={form.password} onChange={onChange('password')} data-testid="teacher-register-password" />
            </div>
            <div>
              <Label htmlFor="r-school">Škola (volitelné — slouží pro předvyplnění formulářů)</Label>
              <Input id="r-school" value={form.school_name} onChange={onChange('school_name')} data-testid="teacher-register-school" />
            </div>
            <div>
              <Label htmlFor="r-phone">Telefon (volitelné)</Label>
              <Input id="r-phone" value={form.phone} onChange={onChange('phone')} data-testid="teacher-register-phone" />
            </div>

            <label className="flex items-start gap-3 cursor-pointer pt-2">
              <input
                type="checkbox"
                checked={agree}
                onChange={e => setAgree(e.target.checked)}
                required
                className="rounded mt-0.5 w-4 h-4 shrink-0"
                data-testid="teacher-register-terms"
              />
              <span className="text-sm text-gray-700 leading-relaxed">
                Souhlasím s{' '}
                <a href="/obchodni-podminky" target="_blank" rel="noopener noreferrer" className="text-[#4A6FA5] hover:underline">obchodními podmínkami</a>
                {' '}a{' '}
                <a href="/gdpr" target="_blank" rel="noopener noreferrer" className="text-[#4A6FA5] hover:underline">zpracováním osobních údajů</a>.
              </span>
            </label>

            {err && (
              <p className="text-sm text-red-600" data-testid="teacher-register-error">{err}</p>
            )}

            <Button
              type="submit"
              disabled={submitting}
              className="w-full bg-[#4A6FA5] hover:bg-[#3a5f95] h-11"
              data-testid="teacher-register-submit"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Vytvořit účet
            </Button>
          </form>

          <p className="mt-6 text-sm text-center text-gray-600">
            Už máte účet?{' '}
            <Link to="/ucitel/prihlaseni" className="text-[#4A6FA5] hover:underline" data-testid="teacher-login-link">
              Přihlaste se
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
};

export default TeacherRegisterPage;
