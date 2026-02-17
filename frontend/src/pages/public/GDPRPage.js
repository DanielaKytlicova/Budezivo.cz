import React from 'react';
import { Header } from '../../components/layout/Header';
import { Card } from '../../components/ui/card';
import { Shield, Lock, Eye, FileText, Trash2, Download, Mail, Building } from 'lucide-react';

export const GDPRPage = () => {
  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      <Header />
      <div className="max-w-4xl mx-auto px-4 py-8 md:py-16">
        <div className="text-center mb-12">
          <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
            Ochrana osobních údajů (GDPR)
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Informace o zpracování osobních údajů v souladu s Nařízením Evropského parlamentu 
            a Rady (EU) 2016/679 (GDPR) a zákonem č. 110/2019 Sb., o zpracování osobních údajů.
          </p>
        </div>

        <div className="space-y-8">
          {/* Správce údajů */}
          <Card className="p-6 md:p-8" data-testid="gdpr-controller">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Building className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">1. Správce osobních údajů</h2>
                <p className="text-gray-600 mb-4">
                  Správcem osobních údajů je provozovatel služby Bubeživo.cz. Každá kulturní instituce, 
                  která službu využívá, je samostatným správcem údajů svých návštěvníků a škol.
                </p>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600">
                    <strong>Kontakt na správce:</strong><br />
                    E-mail: gdpr@bubezivo.cz<br />
                    Datová schránka: [ID datové schránky]
                  </p>
                </div>
              </div>
            </div>
          </Card>

          {/* Účel zpracování */}
          <Card className="p-6 md:p-8" data-testid="gdpr-purpose">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">2. Účely zpracování</h2>
                <p className="text-gray-600 mb-4">Vaše osobní údaje zpracováváme pro následující účely:</p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <span className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 text-green-600 text-sm font-medium">a</span>
                    <div>
                      <strong className="text-slate-900">Správa rezervací</strong>
                      <p className="text-sm text-gray-600">Zpracování a potvrzení rezervací vzdělávacích programů, komunikace ohledně rezervací.</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 text-green-600 text-sm font-medium">b</span>
                    <div>
                      <strong className="text-slate-900">Provoz platformy</strong>
                      <p className="text-sm text-gray-600">Registrace a správa uživatelských účtů institucí, poskytování služeb platformy.</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 text-green-600 text-sm font-medium">c</span>
                    <div>
                      <strong className="text-slate-900">Statistiky a reporting</strong>
                      <p className="text-sm text-gray-600">Anonymizované statistiky návštěvnosti pro instituce (bez identifikace jednotlivců).</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 text-green-600 text-sm font-medium">d</span>
                    <div>
                      <strong className="text-slate-900">Plnění právních povinností</strong>
                      <p className="text-sm text-gray-600">Fakturace, účetnictví a archivace dle zákona č. 563/1991 Sb., o účetnictví.</p>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </Card>

          {/* Právní základ */}
          <Card className="p-6 md:p-8" data-testid="gdpr-legal-basis">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Lock className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">3. Právní základ zpracování</h2>
                <p className="text-gray-600 mb-4">Osobní údaje zpracováváme na základě:</p>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-900 mb-2">Čl. 6 odst. 1 písm. b) GDPR</h4>
                    <p className="text-sm text-gray-600">Plnění smlouvy - zpracování rezervací a poskytování služeb.</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-900 mb-2">Čl. 6 odst. 1 písm. a) GDPR</h4>
                    <p className="text-sm text-gray-600">Souhlas subjektu údajů - marketing a zasílání novinek (pokud byl udělen).</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-900 mb-2">Čl. 6 odst. 1 písm. c) GDPR</h4>
                    <p className="text-sm text-gray-600">Plnění právní povinnosti - účetnictví, archivace dokumentů.</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-900 mb-2">Čl. 6 odst. 1 písm. f) GDPR</h4>
                    <p className="text-sm text-gray-600">Oprávněný zájem - zabezpečení a provoz platformy.</p>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Rozsah údajů */}
          <Card className="p-6 md:p-8" data-testid="gdpr-data-scope">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Eye className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">4. Rozsah zpracovávaných údajů</h2>
                
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-slate-900 mb-2">Pro rezervace (pedagogové, vedoucí skupin):</h4>
                    <ul className="text-sm text-gray-600 space-y-1 ml-4 list-disc">
                      <li>Jméno a příjmení kontaktní osoby</li>
                      <li>E-mailová adresa</li>
                      <li>Telefonní číslo</li>
                      <li>Název školy nebo organizace</li>
                      <li>Počet účastníků skupiny</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h4 className="font-medium text-slate-900 mb-2">Pro účty institucí:</h4>
                    <ul className="text-sm text-gray-600 space-y-1 ml-4 list-disc">
                      <li>Název a adresa instituce</li>
                      <li>IČO/DIČ</li>
                      <li>Kontaktní údaje administrátorů (jméno, e-mail)</li>
                      <li>Přihlašovací údaje (e-mail, heslo v šifrované podobě)</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Doba uchování */}
          <Card className="p-6 md:p-8" data-testid="gdpr-retention">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">5. Doba uchování údajů</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 pr-4 font-medium text-slate-900">Typ údajů</th>
                        <th className="text-left py-2 font-medium text-slate-900">Doba uchování</th>
                      </tr>
                    </thead>
                    <tbody className="text-gray-600">
                      <tr className="border-b">
                        <td className="py-3 pr-4">Údaje o rezervacích</td>
                        <td className="py-3">3 roky od uskutečnění rezervace</td>
                      </tr>
                      <tr className="border-b">
                        <td className="py-3 pr-4">Účetní doklady</td>
                        <td className="py-3">10 let dle zákona o účetnictví</td>
                      </tr>
                      <tr className="border-b">
                        <td className="py-3 pr-4">Uživatelské účty institucí</td>
                        <td className="py-3">Po dobu trvání smluvního vztahu + 3 roky</td>
                      </tr>
                      <tr>
                        <td className="py-3 pr-4">Marketingové souhlasy</td>
                        <td className="py-3">Do odvolání souhlasu</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Card>

          {/* Práva subjektu */}
          <Card className="p-6 md:p-8" data-testid="gdpr-rights">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Shield className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">6. Vaše práva</h2>
                <p className="text-gray-600 mb-4">V souvislosti se zpracováním osobních údajů máte následující práva:</p>
                
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <Eye className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-900 text-sm">Právo na přístup</strong>
                      <p className="text-xs text-gray-600">Získat informace o zpracování vašich údajů</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <FileText className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-900 text-sm">Právo na opravu</strong>
                      <p className="text-xs text-gray-600">Požadovat opravu nepřesných údajů</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <Trash2 className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-900 text-sm">Právo na výmaz</strong>
                      <p className="text-xs text-gray-600">Požadovat smazání údajů ("právo být zapomenut")</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <Download className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-900 text-sm">Právo na přenositelnost</strong>
                      <p className="text-xs text-gray-600">Získat údaje ve strojově čitelném formátu</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <Lock className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-900 text-sm">Právo na omezení</strong>
                      <p className="text-xs text-gray-600">Omezit zpracování za určitých podmínek</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <Mail className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-900 text-sm">Právo vznést námitku</strong>
                      <p className="text-xs text-gray-600">Vznést námitku proti zpracování</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Kontakt a stížnosti */}
          <Card className="p-6 md:p-8" data-testid="gdpr-contact">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Mail className="w-6 h-6 text-slate-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">7. Kontakt a podání stížnosti</h2>
                <p className="text-gray-600 mb-4">
                  Pro uplatnění svých práv nebo dotazy ohledně zpracování osobních údajů nás kontaktujte:
                </p>
                
                <div className="bg-slate-50 rounded-lg p-4 mb-4">
                  <p className="text-sm text-gray-600">
                    <strong>E-mail:</strong> gdpr@bubezivo.cz<br />
                    <strong>Písemně:</strong> Bubeživo.cz, [Adresa], [PSČ] [Město]
                  </p>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h4 className="font-medium text-slate-900 mb-2">Právo podat stížnost</h4>
                  <p className="text-sm text-gray-600">
                    Máte právo podat stížnost u dozorového úřadu:
                  </p>
                  <p className="text-sm text-gray-600 mt-2">
                    <strong>Úřad pro ochranu osobních údajů</strong><br />
                    Pplk. Sochora 27, 170 00 Praha 7<br />
                    Web: <a href="https://www.uoou.cz" className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">www.uoou.cz</a><br />
                    E-mail: posta@uoou.cz
                  </p>
                </div>
              </div>
            </div>
          </Card>

          {/* Zabezpečení */}
          <Card className="p-6 md:p-8" data-testid="gdpr-security">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Lock className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">8. Zabezpečení údajů</h2>
                <p className="text-gray-600 mb-4">
                  Vaše osobní údaje chráníme pomocí moderních technických a organizačních opatření:
                </p>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    Šifrovaný přenos dat (HTTPS/TLS)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    Hesla ukládána v šifrované podobě (bcrypt)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    Data uložena na serverech v EU
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    Pravidelné bezpečnostní zálohy
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    Přístup pouze pro autorizované osoby
                  </li>
                </ul>
              </div>
            </div>
          </Card>

          {/* Cookies */}
          <Card className="p-6 md:p-8" data-testid="gdpr-cookies">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-3">9. Používání cookies</h2>
                <p className="text-gray-600 mb-4">
                  Naše webová stránka používá pouze nezbytné technické cookies pro zajištění funkčnosti:
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 pr-4 font-medium text-slate-900">Název</th>
                        <th className="text-left py-2 pr-4 font-medium text-slate-900">Účel</th>
                        <th className="text-left py-2 font-medium text-slate-900">Expirace</th>
                      </tr>
                    </thead>
                    <tbody className="text-gray-600">
                      <tr className="border-b">
                        <td className="py-3 pr-4">session_token</td>
                        <td className="py-3 pr-4">Přihlášení uživatele</td>
                        <td className="py-3">30 dní</td>
                      </tr>
                      <tr>
                        <td className="py-3 pr-4">lang</td>
                        <td className="py-3 pr-4">Preference jazyka</td>
                        <td className="py-3">1 rok</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Card>

          {/* Aktualizace */}
          <Card className="p-6 md:p-8 bg-gray-50" data-testid="gdpr-updates">
            <p className="text-sm text-gray-600 text-center">
              Tyto zásady ochrany osobních údajů jsou platné od <strong>1. ledna 2026</strong>.<br />
              O případných změnách vás budeme informovat na této stránce.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
};
