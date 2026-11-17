# ⛳ Golf Flipper

Krijg een melding op je gsm zodra er golfmateriaal te goedkoop te koop komt:
- op **2dehands** rond Londerzeel of langs je route naar Gierle (⛳ in de melding)
- op **Vinted**, in heel België, met verzending (👕 in de melding)

## Hoe het werkt
1. Elke 15 minuten zoekt het script de nieuwste advertenties in 6 zones, telkens met een straal van 10 km:
   Londerzeel → Boom/Willebroek → Antwerpen → Wommelgem/Ranst → Zoersel → Gierle (route A12 – R1 – E34).
2. Alleen golfadvertenties blijven over (categorie Golf, of het woord "golf" in Sport). VW Golfs en zo worden eruit gefilterd.
3. Voor elke nieuwe advertentie bepaalt het script **wat** het is (driver, ijzers, set, trolley, …), het **merk** en waar mogelijk het **model** (Stealth, G425, M2, …).
4. Daarna zoekt het in **heel België** naar dezelfde spullen en neemt de **mediaan van de vraagprijzen** als marktprijs.
5. **Melding** als: prijs ≤ 65% van de marktprijs **én** je verwachte winst ≥ €40.
   Verwachte winst = marktprijs × 0,9 (je verkoopt iets onder de gemiddelde vraagprijs) − aankoopprijs − €5 kosten.
   Gratis golfspullen en prijzen onder je "spotprijs" geven ook een melding.

De melding toont de prijs, de plaats, de marktprijs, je geschatte winst en een knop om de advertentie meteen te openen.

## Vinted
- Het programma leest de gewone Vinted-zoekpagina voor elke zoekterm in `config.json` → `vinted.zoektermen`, nieuwste eerst.
- Vinted toont geen afstand: alles wordt verzonden. Daarom rekent het programma met wat je **echt betaalt**: prijs + Vinted-servicekost + verzending (instelbaar per soort in `vinted.verzendkosten`).
- Losse accessoires (headcovers, grips, ballen, kledij) en gewone sporthorloges worden overgeslagen. De merkenlijst geldt ook hier.
- Vinted heeft een strenge botbescherming. Weigert Vinted de vragen van GitHub, dan krijg je daar **max. 1 melding per dag** over, en 2dehands blijft gewoon werken. Vinted uitzetten: `"aan": false` in `config.json`.

## Doorverkopen op 2dehands én Vinted
- Voor elk mogelijk koopje bepaalt het programma de marktprijs op **beide** platformen (mediaan van de vraagprijzen) en kiest het het platform waar je het **meeste** voor krijgt. De melding toont beide, bv. `Markt: 2dehands ±€250 · vinted ±€300` en `Verkoop op vinted ±€270`.
- Vinted rekent verkopers geen kosten aan en de koper betaalt de verzending, dus de Vinted-prijs is wat je ontvangt.
- Trolleys en complete sets verzend je niet makkelijk. Die worden daarom alleen op 2dehands gewaardeerd (`vinted.niet_verkopen_op_vinted`).
- Alleen op 2dehands verkopen: zet `"verkoop_op": ["2dehands"]`. Is Vinted onbereikbaar, dan valt het programma vanzelf terug op 2dehands.

## Installatie (±15 minuten, gratis)

### 1. App op je gsm
- Installeer **ntfy** (gratis, Android én iPhone).
- Tik op **+** en abonneer je op een topic met een **zelfverzonnen, moeilijk te raden naam**, bv. `golfflip-arne-8k3j2q`.
  Iedereen die de naam kent, kan je meldingen lezen. Houd hem dus geheim.

### 2. Laten draaien op GitHub (gratis, ook als je pc uit staat)
1. Maak een account op github.com en een **nieuwe publieke repository** (bv. `golf-flipper`).
   Publieke repo's krijgen onbeperkt gratis rekentijd. Je ntfy-naam staat er niet in, want die zit in een geheim.
2. Upload alle bestanden uit deze map, **ook de map `.github`** (sleep de uitgepakte map in "Add file → Upload files").
3. Ga naar **Settings → Secrets and variables → Actions → New repository secret**:
   naam `NTFY_TOPIC`, waarde = de naam van je topic uit stap 1.
4. Ga naar **Actions → Golf Flipper → Run workflow**.
   De eerste run onthoudt alleen alle bestaande advertenties (geen 200 meldingen ineens).
   Vanaf dan krijg je alleen meldingen voor nieuwe advertenties.

Opmerking: GitHub start geplande taken soms 5 à 15 minuten later dan gepland.

### Alternatief: op je eigen pc
Python 3 installeren (python.org) en dan:
```
python golf_flipper.py --test     # testmelding naar je gsm
python golf_flipper.py            # één zoekronde
```
Zet dat laatste in Windows Taakplanner (elke 15 min). Zet dan wel je topic in `config.json` bij `ntfy_topic`.

## Instellen (`config.json`)
| Instelling | Betekenis |
|---|---|
| `zones` | postcodes + straal. Voeg gerust zones toe of verwijder er. |
| `alleen_merken` | alleen deze merken geven een melding, omdat ze vlot doorverkopen. Een advertentie zonder herkend merk wordt ook overgeslagen. Maak de lijst leeg (`[]`) om alle merken toe te laten. |
| `min_winst_euro` | minimale verwachte winst voor een melding (standaard 40) |
| `max_prijs_vs_markt` | 0.65 = melding als de prijs maximaal 65% van de marktprijs is |
| `verkoop_korting` | 0.9 = je verwacht te verkopen aan 90% van de gemiddelde vraagprijs |
| `kosten_per_aankoop_euro` | benzine/tijd per aankoop |
| `meld_ook_bieden` | `true` = ook melding bij advertenties zonder prijs ("Bieden") |
| `vaste_marktprijzen` | jouw eigen kennis, bv. `"driver\|taylormade\|stealth": 200`. Gaat voor op de berekende mediaan. |
| `absolute_koopjes` | spotprijzen: altijd melding als bv. een trolley onder €80 of een Garmin-golfhorloge onder €60 staat |

Handig om te testen: `python golf_flipper.py --droog --alles` toont welke huidige advertenties een melding zouden geven, zonder iets te versturen.

## Goed om te weten
- De marktprijs is gebaseerd op **vraagprijzen**, niet op echte verkoopprijzen. Kijk altijd even zelf naar staat, shaft (flex), links- of rechtshandig en dames/heren.
- Modellen die het script niet kent, worden vergeleken op merk + soort. Dat is ruwer. Voeg je favoriete modellen toe aan `MODELLEN` in het script.
- Het script gebruikt dezelfde zoekfunctie als de 2dehands-website, met rustige pauzes tussen de vragen. Als 2dehands die functie verandert, moet het script misschien aangepast worden.
