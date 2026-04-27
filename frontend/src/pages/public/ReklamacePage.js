import React from 'react';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Card } from '../../components/ui/card';
import { ShieldAlert, Clock, RefreshCcw, XCircle, Mail } from 'lucide-react';

export const ReklamacePage = () => {
  return (
    <div className="min-h-screen bg-[#F8F9FA]" data-testid="reklamace-page">
      <Header />

      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
        <div className="text-center mb-10">
          <div className="w-14 h-14 bg-[#4A6FA5] rounded-full flex items-center justify-center mx-auto mb-5">
            <ShieldAlert className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-[#2B3E50] mb-3">
            Reklamační a stornovací podmínky
          </h1>
          <p className="text-gray-600">
            Podmínky pro storno rezervace, vrácení platby a reklamaci služeb
          </p>
        </div>

        <Card className="p-6 md:p-8 bg-white space-y-6">
          {/* Provozovatel */}
          <section data-testid="reklamace-provider">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">1. Provozovatel platformy</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              Daniela Kytlicová, IČO 07407971, se sídlem Mlýnská 538, není plátce DPH.
              Kontaktní e-mail: <a href="mailto:info@budezivo.cz" className="text-[#4A6FA5] hover:underline">info@budezivo.cz</a>.
              Provozovatel je výhradně technickým zprostředkovatelem rezervací; samotnou službu (program, akci) realizuje kulturní instituce uvedená v rezervaci.
            </p>
          </section>

          {/* Storno rezervace */}
          <section data-testid="reklamace-cancel">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-[#4A6FA5]" />
              <h2 className="text-lg font-semibold text-[#2B3E50]">2. Storno rezervace zákazníkem</h2>
            </div>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>Bezplatné storno je možné nejpozději <strong>48 hodin před začátkem programu</strong>.</li>
              <li>Storno se provádí e-mailem na adresu pořádající instituce uvedenou v potvrzovacím e-mailu rezervace.</li>
              <li>Při zrušení později než 48 hodin předem může pořádající instituce požadovat storno poplatek dle vlastních provozních pravidel.</li>
              <li>Pro akce hrazené online bránou platí storno podmínky uvedené u konkrétní akce.</li>
            </ul>
          </section>

          {/* Vrácení peněz */}
          <section data-testid="reklamace-refund">
            <div className="flex items-center gap-2 mb-2">
              <RefreshCcw className="w-5 h-5 text-[#4A6FA5]" />
              <h2 className="text-lg font-semibold text-[#2B3E50]">3. Vrácení platby</h2>
            </div>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>U akcí placených online bránou (např. Comgate) je platba vrácena na původní platební prostředek do <strong>14 dnů</strong> od schválení vrácení.</li>
              <li>Vrácení provádí pořádající instituce, která je příjemcem platby. Provozovatel platformy není stranou platební transakce.</li>
              <li>Při zrušení akce ze strany pořadatele má zákazník nárok na vrácení 100 % uhrazené částky.</li>
              <li>Bankovní poplatky platební brány se nevrací — jsou nákladem pořádající instituce.</li>
            </ul>
          </section>

          {/* Zrušení ze strany pořadatele */}
          <section data-testid="reklamace-organizer-cancel">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-5 h-5 text-[#4A6FA5]" />
              <h2 className="text-lg font-semibold text-[#2B3E50]">4. Zrušení nebo změna ze strany pořadatele</h2>
            </div>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>Pořadatel může z provozních důvodů (nemoc lektora, technická závada, vyšší moc) program zrušit nebo přesunout.</li>
              <li>O zrušení informuje zákazníka neprodleně e-mailem nebo telefonem.</li>
              <li>Při zrušení nabídne pořadatel buď náhradní termín, nebo plné vrácení uhrazené částky.</li>
            </ul>
          </section>

          {/* Reklamace */}
          <section data-testid="reklamace-complaint">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">5. Reklamace služby</h2>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>Reklamaci kvality programu je třeba uplatnit u pořádající instituce <strong>bez zbytečného odkladu</strong>, nejpozději do 14 dnů od konání programu.</li>
              <li>Reklamace se podává e-mailem s popisem vady a požadovaným způsobem vyřízení.</li>
              <li>Pořadatel reklamaci posoudí a sdělí zákazníkovi výsledek do 30 dnů.</li>
              <li>Reklamaci technické funkčnosti rezervačního systému (chyba platformy, nedoručený e-mail) lze podat na <a href="mailto:info@budezivo.cz" className="text-[#4A6FA5] hover:underline">info@budezivo.cz</a>.</li>
            </ul>
          </section>

          {/* Mimosoudní řešení sporů */}
          <section data-testid="reklamace-adr">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">6. Mimosoudní řešení sporů (ADR)</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              Spotřebitel má právo na mimosoudní řešení spotřebitelského sporu. Příslušným orgánem je Česká obchodní inspekce
              (<a href="https://www.coi.cz" target="_blank" rel="noopener noreferrer" className="text-[#4A6FA5] hover:underline">www.coi.cz</a>).
              Lze využít také platformu EU pro online řešení sporů na <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener noreferrer" className="text-[#4A6FA5] hover:underline">ec.europa.eu/consumers/odr</a>.
            </p>
          </section>

          <section className="pt-4 border-t border-gray-100" data-testid="reklamace-contact">
            <div className="flex items-start gap-3 bg-[#EEF2F9] p-4 rounded-lg">
              <Mail className="w-5 h-5 text-[#4A6FA5] flex-shrink-0 mt-0.5" />
              <div className="text-sm text-gray-700">
                <p className="font-semibold text-[#2B3E50] mb-1">Kontakt pro reklamace</p>
                <p>
                  E-mail: <a href="mailto:info@budezivo.cz" className="text-[#4A6FA5] hover:underline">info@budezivo.cz</a><br />
                  Provozovatel platformy reklamaci přepošle pořádající instituci, pokud se týká jejích služeb.
                </p>
              </div>
            </div>
          </section>

          <p className="text-xs text-gray-400 pt-2">Verze: v1 · Účinnost: 27. 4. 2026</p>
        </Card>
      </div>

      <Footer />
    </div>
  );
};

export default ReklamacePage;
