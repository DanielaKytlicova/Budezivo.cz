# Produkcni smoke test pilotni instituce

Tento checklist slouzi pro rychle overeni, ze konkretni pilotni instituce muze v produkci bezpecne projit hlavnim provoznim tokem.

Spousti se az po nasazeni poslednich predpilotnich zmen a idealne zvlast pro kazdou pilotni instituci.

## Pravidla

- Testuj jen na uctu dane instituce.
- Nevytvarej ani nemaz realna historicka data, pokud to neni domluvene.
- Pouzivej jasne testovaci nazvy, napriklad `TEST PILOT - neodesilat`.
- Pokud narazis na chybu, zastav se a zapis presny krok, cas a screenshot.
- Pokud je potreba seedovani, mazani nebo hromadny datovy test, nepokracuj na produkci. Pouzij izolovanou testovaci databazi.

## Vysledek zapisuj takto

- `OK` - funguje podle ocekavani.
- `POZOR` - funguje, ale je tam UX nejasnost nebo drobnost.
- `CHYBA` - blokuje praci nebo uklada spatna data.
- `NEOVERENO` - nebylo mozne otestovat.

## 1. Prihlaseni a zakladni nacteni

1. Prihlas se jako admin/spravce pilotni instituce.
2. Obnov stranku prohlizece.
3. Otevri hlavni zalozky: Prehled, Programy, Rezervace, Akce, Propagace, Sprava/Skoly, Kontakty, Nastaveni.

Spravne:

- Ucet zustane prihlaseny.
- Zalozky se nactou bez bile obrazovky.
- Konzole nema opakovane `401`, `CORS`, nebo fatal React chyby.

## 2. Programy

1. Otevri existujici program.
2. Zkus ulozit bez povinneho pole.
3. Dopln chybejici pole a uloz.
4. Zkontroluj nastaveni terminove rezervace a zpetne vazby, pokud je pro instituci zapnute.

Spravne:

- Chybna povinna pole maji cerveny obrys a cerveny text pod polem.
- Dobrovolna pole nejsou zbytecne vyzadovana.
- Program jde po oprave ulozit.

## 3. Akce a uzaverky

1. Vytvor nebo uprav testovaci akci.
2. Pridej termin se zacatkem a koncem.
3. Nastav uzaverku prihlasek pred zacatkem terminu.
4. Zkus ulozit nespravny konec pred zacatkem.
5. Oprav hodnoty a uloz.

Spravne:

- Uzaverka muze byt pred terminem akce.
- Konec terminu musi byt az po zacatku terminu.
- Pri chybe se zvyrazni konkretni spatne pole.
- Po oprave se akce ulozi.

## 4. Rezervace

1. Otevri seznam rezervaci.
2. Prepni seznam/kalendar.
3. Otevri detail rezervace.
4. Pokud existuje rezervace pro pokladni, over zobrazeni poctu realne prichozich.

Spravne:

- Prepínani seznam/kalendar funguje.
- Kalendar se nacte a nezakryva ovladaci prvky.
- Detail rezervace ukazuje skolu, program, cas a stav.

## 5. Skoly a kontakty

1. Otevri Skoly.
2. Rozbal kontakty u skoly.
3. Pridej testovaci kontakt, pokud je to pro instituci vhodne.
4. Zkus chybejici povinna pole.
5. Oprav a uloz.

Spravne:

- Kontakt jde pridat pres radek skoly.
- Povinna chybna pole jsou zvyraznena jednotnym stylem.
- Neplatne kontakty a archivovane kontakty se chovaji predvidatelne podle filtru.

## 6. Propagace a mailing

1. Vytvor koncept kampane.
2. Vyber program a prijemce.
3. Zkus prejit dal bez povinneho pole.
4. Odesli testovaci e-mail na vlastni adresu.
5. Pokud je to domluvene, odesli malou testovaci kampan na bezpecne interni adresy.

Spravne:

- Povinna pole jsou zvyraznena jednotnym stylem.
- Testovaci e-mail obsahuje stejne programove karty jako ostry e-mail.
- Odkazy v e-mailu vedou na vyber terminu.
- Domena projde SPF/DKIM/DMARC.

## 7. Nastaveni

1. Otevri Sprava instituce.
2. Over ulozeni nazvu instituce.
3. Otevri zmenu hesla a zkus chybejici povinna pole.
4. Pokud ma instituce platby, over platebni nastaveni v uctu, kde je tato funkce dostupna.

Spravne:

- Povinna pole maji jednotne cervene zvyrazneni.
- Dobrovolna pole, napriklad nepovinne kontakty, se nevynucuji.
- Platebni nastaveni se zobrazuje jen tam, kde ma instituce platebni funkce.

## 8. Verejne odkazy

1. Otevri verejnou rezervacni stranku instituce.
2. Otevri verejny detail programu.
3. Otestuj verejny formular, ale neodesilej realne citlive udaje.
4. Pokud existuje ICS odkaz, over jeho nacteni.

Spravne:

- Verejne stranky se nactou bez prihlaseni.
- Formulare ukazuji chyby primo u poli.
- Stare ICS odkazy zustavaji funkcni.

## 9. Role

Pokud ma instituce vice roli, over zvlast:

- admin/spravce vidi kompletni spravu instituce,
- edukator/lektor vidi jen casti, ktere potrebuje,
- pokladni vidi prehled a rezervace, ne lektorsky profil,
- uzivatel nevidi data cizi instituce.

## Zaver testu

Vypln kratky zaznam:

```text
Instituce:
Datum a cas:
Testoval/a:
Vysledek: OK / POZOR / CHYBA / NEOVERENO

Poznamky:
- 

Blokery pred pilotem:
- 
```
