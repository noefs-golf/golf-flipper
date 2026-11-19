# ⛳ Golf Flipper

Krijg een melding op je gsm zodra er golfmateriaal te koop komt dat je met **minstens €25 winst** kan doorverkopen:
- op **2dehands** rond Londerzeel en langs je route naar Gierle (⛳)
- op **Vinted**, in heel België, met verzending (👕)

## Hoe het programma rekent
1. **Referentieprijs = Golfbidder.** Elke advertentie wordt gekoppeld aan het juiste model in `golfbidder_prijzen.json` (de EU-site, in euro, prijs van het goedkoopste gebruikte exemplaar).
   - Herkent het programma alleen het hoofdmodel (bv. "G425" zonder MAX/LST/SFT), dan neemt het de **goedkoopste variant**. In de melding staat dan "≈ goedkoopste variant".
   - Staat het model niet bij Golfbidder (trolleys, horloges, complete sets…), dan gebruikt het de mediaan van de 2dehands- en Vinted-vraagprijzen. In de melding staat dan "Geen Golfbidder-prijs".
2. **Verkoopprijs = 5 tot 10% onder Golfbidder.** Er wordt gerekend met de voorzichtige −10%.
3. **Kosten:** op 2dehands €5 voor je rit, op Vinted de servicekost en de verzending.
4. **Melding** als je bij −10% nog **≥ €25 winst** overhoudt. Bij "bieden vanaf"-advertenties krijg je ook een melding als je met een bod tot 20% onder de vraagprijs je winst haalt.

## Wat er in een melding staat
```
Vraagprijs €180 · Londerzeel (Londerzeel)
Golfbidder: €275 (Ping G425 MAX Driver, 2021)
Verkoop aan €247-261 → winst ±€62-76
MAX. BOD: €215 (dan hou je min. €25 over)
Bericht: Hallo, is deze nog beschikbaar? Zou €150 lukken? Ik kan hem snel komen ophalen. Mvg
```
Houd de melding lang ingedrukt om het bericht te kopiëren. Het openingsbod ligt ±15% onder de vraagprijs en nooit boven je max. bod.

## Wat er wordt overgeslagen
- **Trage verkopers:** linkshandig, dames, junior/kinder, en modellen ouder dan 10 jaar (volgens het Golfbidder-bouwjaar). Uitzetten: `"trage_verkopers_overslaan": false`.
- **Accessoires:** hoesjes/headcovers, grips, ballen, kledij, schoenen. Ook **losse koppen en shafts** worden overgeslagen.
- **Merken** die niet in `alleen_merken` staan, en auto's ("VW Golf") die in de categorie Golf staan.
- **Garmin-golfhorloges** (Approach S-reeks) worden wel opgevolgd. Gewone sporthorloges niet.

## Golfbidder-prijslijst vernieuwen
Golfbidder heeft een beveiligingscontrole, dus de prijzen kunnen niet automatisch vanaf GitHub opgehaald worden. Vernieuw de lijst ongeveer één keer per maand: vraag het aan Claude (via Claude in Chrome), en vervang daarna `golfbidder_prijzen.json` op GitHub. De datum van de lijst staat bovenaan in het bestand.

## Instellingen (`config.json`)
| Instelling | Betekenis |
|---|---|
| `min_winst_euro` | minimale winst per transactie (standaard 25) |
| `golfbidder.korting_min` / `korting_max` | je verkoopt 5-10% onder Golfbidder |
| `golfbidder.max_leeftijd_jaar` | oudere modellen overslaan (standaard 10 jaar) |
| `golfbidder.alleen_golfbidder` | `true` = alleen meldingen als er een Golfbidder-prijs is |
| `trage_verkopers_overslaan` | linkshandig, dames, junior en oude modellen overslaan |
| `kosten_per_aankoop_euro` | benzine/tijd per aankoop op 2dehands |
| `zones` | postcodes + straal voor 2dehands |
| `vinted` | zoektermen, verzendkosten, aan/uit |
| `alleen_merken` | alleen deze merken geven meldingen |
| `vaste_marktprijzen` | jouw eigen prijzen voor wat niet bij Golfbidder staat |

## Installatie
1. Installeer **ntfy** op je gsm en abonneer je op een geheime naam.
2. Zet alle bestanden in een publieke GitHub-repository, met de workflow in `.github/workflows/golf-flipper.yml`.
3. Maak bij **Settings → Secrets and variables → Actions** het geheim `NTFY_TOPIC` aan, met je ntfy-naam.
4. Kies bij **Settings → Actions → General → Workflow permissions** voor **Read and write**.
5. Start via **Actions → Golf Flipper → Run workflow**. De eerste run per bron is stil: die onthoudt alleen wat er al te koop staat.

Testen: `python golf_flipper.py --droog --alles` toont welke huidige advertenties een melding zouden geven, zonder iets te versturen.
