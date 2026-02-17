import React, { useState } from 'react';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import { Mail, Phone, MapPin, Clock, Send } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ContactPage = () => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    institution: '',
    subject: 'general',
    message: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.post(`${API}/contact`, formData);
      toast.success('Zpráva byla odeslána. Brzy se vám ozveme!');
      setFormData({
        name: '',
        email: '',
        institution: '',
        subject: 'general',
        message: '',
      });
    } catch (error) {
      toast.error('Nepodařilo se odeslat zprávu. Zkuste to prosím znovu.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Header />

      {/* Hero */}
      <section className="bg-gradient-to-br from-[#4A6FA5] via-[#5979ad] to-[#6889bb] text-white py-16 md:py-20">
        <div className="max-w-7xl mx-auto px-6 md:px-8 text-center">
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            Kontaktujte nás
          </h1>
          <p className="text-lg md:text-xl text-white/90 max-w-2xl mx-auto">
            Máte dotaz nebo potřebujete pomoc? Jsme tu pro vás.
          </p>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 md:px-8 py-12 md:py-16">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Contact Info */}
          <div className="space-y-6">
            <Card className="p-6" data-testid="contact-info-email">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Mail className="w-6 h-6 text-[#4A6FA5]" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">E-mail</h3>
                  <a href="mailto:info@budezivo.cz" className="text-[#4A6FA5] hover:underline">
                    info@budezivo.cz
                  </a>
                  <p className="text-sm text-gray-500 mt-1">Pro obecné dotazy</p>
                </div>
              </div>
            </Card>

            <Card className="p-6" data-testid="contact-info-phone">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Phone className="w-6 h-6 text-[#4A6FA5]" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">Telefon</h3>
                  <a href="tel:+420123456789" className="text-[#4A6FA5] hover:underline">
                    +420 123 456 789
                  </a>
                  <p className="text-sm text-gray-500 mt-1">Po-Pá 9:00 - 17:00</p>
                </div>
              </div>
            </Card>

            <Card className="p-6" data-testid="contact-info-address">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-6 h-6 text-[#4A6FA5]" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">Adresa</h3>
                  <p className="text-gray-600">
                    Budeživo.cz<br />
                    Příkladová 123<br />
                    110 00 Praha 1
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6" data-testid="contact-info-hours">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Clock className="w-6 h-6 text-[#4A6FA5]" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">Provozní doba</h3>
                  <p className="text-gray-600">
                    Pondělí - Pátek<br />
                    9:00 - 17:00
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Contact Form */}
          <div className="md:col-span-2">
            <Card className="p-6 md:p-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-6">Napište nám</h2>
              
              <form onSubmit={handleSubmit} className="space-y-6" data-testid="contact-form">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="name">Jméno a příjmení</Label>
                    <Input
                      id="name"
                      data-testid="contact-name-input"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="Jan Novák"
                      required
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label htmlFor="email">E-mail</Label>
                    <Input
                      id="email"
                      type="email"
                      data-testid="contact-email-input"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="jan.novak@muzeum.cz"
                      required
                      className="mt-2"
                    />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="institution">Instituce (volitelné)</Label>
                    <Input
                      id="institution"
                      data-testid="contact-institution-input"
                      value={formData.institution}
                      onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
                      placeholder="Městské muzeum"
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label htmlFor="subject">Předmět</Label>
                    <Select
                      value={formData.subject}
                      onValueChange={(value) => setFormData({ ...formData, subject: value })}
                    >
                      <SelectTrigger className="mt-2" data-testid="contact-subject-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">Obecný dotaz</SelectItem>
                        <SelectItem value="demo">Zájem o ukázku</SelectItem>
                        <SelectItem value="pricing">Dotaz na tarify</SelectItem>
                        <SelectItem value="support">Technická podpora</SelectItem>
                        <SelectItem value="partnership">Spolupráce</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label htmlFor="message">Zpráva</Label>
                  <Textarea
                    id="message"
                    data-testid="contact-message-input"
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    placeholder="Napište nám svůj dotaz nebo zprávu..."
                    required
                    className="mt-2"
                    rows={6}
                  />
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full md:w-auto bg-[#C4AB86] text-white hover:bg-[#b39975] h-12 px-8"
                  data-testid="contact-submit-button"
                >
                  {loading ? (
                    'Odesílání...'
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Odeslat zprávu
                    </>
                  )}
                </Button>
              </form>
            </Card>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};
