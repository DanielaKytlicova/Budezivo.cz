import React from 'react';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Card } from '../../components/ui/card';
import { CreditCard, Truck, Receipt, ShieldCheck } from 'lucide-react';

export const PaymentTermsPage = () => {
  return (
    <div className="min-h-screen bg-[#F8F9FA]" data-testid="payment-terms-page">
      <Header />

      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
        <div className="text-center mb-10">
          <div className="w-14 h-14 bg-[#4A6FA5] rounded-full flex items-center justify-center mx-auto mb-5">
            <CreditCard className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-[#2B3E50] mb-3">
            Platební a dodací podmínky
          </h1>
          <p className="text-gray-600">
            Informace o způsobech platby a dodání rezervovaných služeb
          </p>
        </div>

        <Card className="p-6 md:p-8 bg-white space-y-6">
          {/* Provozovatel */}
          <section data-testid="payment-provider">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">1. Provozovatel</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              Daniela Kytlicová, IČO 07407971, se sídlem Mlýnská 538, není plátce DPH.
              E-mail: <a href="mailto:info@budezivo.cz" className="text-[#4A6FA5] hover:underline">info@budezivo.cz</a>.
            </p>
            <p className="text-sm text-gray-700 leading-relaxed mt-2">
              Provozovatel poskytuje rezervační platformu Budeživo.cz, která zprostředkovává rezervace mezi kulturními institucemi a jejich zákazníky. Provozovatel <strong>není</strong> poskytovatelem rezervovaných programů ani příjemcem plateb za ně.
            </p>
          </section>

          {/* Předmět plnění */}
          <section data-testid="payment-subject">
            <div className="flex items-center gap-2 mb-2">
              <Truck className="w-5 h-5 text-[#4A6FA5]" />
              <h2 className="text-lg font-semibold text-[#2B3E50]">2. Předmět plnění (dodání)</h2>
            </div>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>Dodáním se rozumí <strong>rezervace termínu programu</strong> v kulturní instituci a její potvrzení e-mailem.</li>
              <li>U placených akcí je dodáním <strong>závazná přihláška na akci</strong> a obdržení potvrzení s případným vstupenkovým údajem (variabilní symbol, QR kód).</li>
              <li>Potvrzovací e-mail je odesílán automaticky obratem po úspěšném vytvoření rezervace nebo přihlášky.</li>
              <li>Samotná realizace programu/akce probíhá v termínu zvoleném při rezervaci v provozovně pořádající instituce.</li>
            </ul>
          </section>

          {/* Způsoby platby */}
          <section data-testid="payment-methods">
            <div className="flex items-center gap-2 mb-2">
              <Receipt className="w-5 h-5 text-[#4A6FA5]" />
              <h2 className="text-lg font-semibold text-[#2B3E50]">3. Způsoby platby</h2>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed mb-3">
              Konkrétní způsob platby závisí na nastavení pořádající instituce a typu programu:
            </p>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li><strong>Platba na místě</strong> — při školních programech rezervovaných školou; platba probíhá přímo v instituci v hotovosti nebo platební kartou dle možností pořadatele.</li>
              <li><strong>Bankovní převod / QR platba</strong> — u placených akcí může pořadatel zaslat platební údaje s variabilním symbolem a QR kódem v potvrzovacím e-mailu.</li>
              <li><strong>Online platba kartou</strong> — pokud pořádající instituce má aktivní platební bránu (např. Comgate), zákazník platí online přímo v rezervačním procesu. Platba je zpracována zabezpečenou bránou třetí strany.</li>
            </ul>
          </section>

          {/* Bezpečnost a brána */}
          <section data-testid="payment-security">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-5 h-5 text-[#4A6FA5]" />
              <h2 className="text-lg font-semibold text-[#2B3E50]">4. Poskytovatel platební brány a bezpečnost online plateb</h2>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed mb-3">
              Online platby na této platformě jsou zpracovávány platební bránou{' '}
              <a
                href="https://www.comgate.eu/cs/platebni-brana"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#4A6FA5] hover:underline font-semibold"
                data-testid="comgate-gateway-link"
              >
                Comgate
              </a>
              {' '}— poskytovatelem je společnost <strong>Comgate, a.s.</strong>, IČO 27924505,
              v souladu s mezinárodními bezpečnostními standardy <strong>PCI-DSS</strong>.
            </p>

            <div className="bg-[#EEF2F9] rounded-lg p-4 my-3 space-y-2 text-sm" data-testid="payment-methods-explainer">
              <p className="font-semibold text-[#2B3E50]">Podporované způsoby online platby:</p>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                <li>
                  <strong>Platba kartou (Visa, Mastercard)</strong> — zákazník zadá údaje své platební karty na zabezpečené stránce Comgate;
                  v případě potřeby je vyzván k autentizaci v aplikaci své banky (3-D Secure). Po úspěšné platbě je obratem přesměrován zpět na potvrzovací stránku rezervace.{' '}
                  <a
                    href="https://help.comgate.cz/v1/docs/cs/platby-kartou"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#4A6FA5] hover:underline"
                    data-testid="comgate-card-help-link"
                  >
                    Podrobnosti o platbě kartou
                  </a>
                </li>
                <li>
                  <strong>Platební tlačítka bank (online bankovní převod)</strong> — zákazník je přesměrován do internetového bankovnictví své banky,
                  kde předvyplněnou platbu pouze potvrdí. Platba je zaúčtována během několika minut.{' '}
                  <a
                    href="https://help.comgate.cz/docs/bankovni-prevody"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#4A6FA5] hover:underline"
                    data-testid="comgate-transfer-help-link"
                  >
                    Podrobnosti o bankovních převodech
                  </a>
                </li>
              </ul>
            </div>

            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>Údaje o platební kartě nejsou zpracovávány ani ukládány provozovatelem platformy ani pořádající institucí — kompletní zpracování probíhá výhradně na zabezpečené infrastruktuře Comgate.</li>
              <li>Po úspěšné platbě je zákazník automaticky přesměrován zpět na potvrzovací stránku rezervace.</li>
              <li>Příjemcem online platby je <strong>pořádající instituce</strong>, ne provozovatel platformy.</li>
            </ul>

            {/* Comgate contact card */}
            <div
              className="mt-4 border border-[#D9E1F0] rounded-lg p-4 bg-white"
              data-testid="comgate-contact-card"
            >
              <p className="text-sm font-semibold text-[#2B3E50] mb-2">Kontakt na poskytovatele platební brány</p>
              <div className="text-sm text-gray-700 space-y-0.5 leading-relaxed">
                <p className="font-medium">Comgate, a.s.</p>
                <p>Gočárova třída 1754/48b, 500 02 Hradec Králové</p>
                <p>
                  E-mail:{' '}
                  <a href="mailto:podpora@comgate.cz" className="text-[#4A6FA5] hover:underline">
                    podpora@comgate.cz
                  </a>
                </p>
                <p>
                  Telefon:{' '}
                  <a href="tel:+420228224267" className="text-[#4A6FA5] hover:underline">
                    +420 228 224 267
                  </a>
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  Reklamace a dotazy ke konkrétním platbám (např. neproběhlá nebo dvojitě stržená platba) prosím směřujte přímo na podporu Comgate uvedenou výše.
                </p>
              </div>
            </div>
          </section>

          {/* Cena a měna */}
          <section data-testid="payment-price">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">5. Cena a měna</h2>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 leading-relaxed">
              <li>Veškeré ceny jsou uváděny v českých korunách (CZK) a jsou konečné.</li>
              <li>Provozovatel platformy není plátcem DPH; pořádající instituce může být plátcem DPH dle svých daňových povinností.</li>
              <li>U školních programů je cena uvedena v detailu programu (např. „60 Kč / dítě, pedagog zdarma") a je orientační — závazná cena vychází z provozních pravidel instituce.</li>
              <li>U placených akcí je cena uvedena v detailu konkrétní akce před přihlášením.</li>
            </ul>
          </section>

          {/* Doklad */}
          <section data-testid="payment-receipt">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">6. Doklad o platbě</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              Doklad o platbě (potvrzení o přijetí, případně daňový doklad) vystavuje pořádající instituce.
              Po dokončení platby online bránou obdrží zákazník potvrzení e-mailem; v případě potřeby formálního dokladu lze pořadatele kontaktovat na e-mailu uvedeném v potvrzení rezervace.
            </p>
          </section>

          {/* Storno a reklamace odkaz */}
          <section data-testid="payment-cancel-link" className="pt-4 border-t border-gray-100">
            <h2 className="text-lg font-semibold text-[#2B3E50] mb-2">7. Storno, vrácení a reklamace</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              Podmínky pro zrušení rezervace, vrácení platby a reklamaci jsou popsány v dokumentu{' '}
              <a href="/reklamace" className="text-[#4A6FA5] hover:underline font-semibold">Reklamační a stornovací podmínky</a>.
            </p>
          </section>

          <p className="text-xs text-gray-400 pt-2">Verze: v1 · Účinnost: 27. 4. 2026</p>
        </Card>
      </div>

      <Footer />
    </div>
  );
};

export default PaymentTermsPage;
