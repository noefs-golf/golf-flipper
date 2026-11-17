#!/usr/bin/env python3
"""
Golf Flipper - zoekt op 2dehands.be naar golfspullen die te goedkoop staan
en stuurt een pushmelding naar je gsm (via de gratis app ntfy).

Alleen standaard-Python nodig (3.8+), niks te installeren.

Gebruik:
    python golf_flipper.py            # één keer zoeken (zet dit op een schema)
    python golf_flipper.py --test     # stuurt een testmelding naar je gsm
    python golf_flipper.py --droog    # zoeken, maar alleen printen (geen meldingen)
    python golf_flipper.py --alles    # meld ook advertenties die al gezien zijn
"""
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
CONFIG_PAD = os.path.join(HIER, "config.json")
GEZIEN_PAD = os.path.join(HIER, "data", "gezien.json")
MARKT_PAD = os.path.join(HIER, "data", "marktprijzen.json")

BASIS = "https://www.2dehands.be"
API = BASIS + "/lrp/api/search"
SPORT_CAT = 784   # Sport en Fitness
GOLF_CAT = 794    # Golf

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "nl-BE,nl;q=0.9",
}

# ---------------------------------------------------------------- herkenning
TYPES = [  # volgorde = prioriteit
    ("trolley", ["elektrische trolley", "golftrolley", "trolley", "golfkar", "caddy kar",
                 "motocaddy", "powakaddy", "stewart", "jucad", "push cart", "duwkar", "trekkar",
                 "chariot"]),
    ("horloge", ["golfhorloge", "golf horloge", "gps horloge", "horloge", "smartwatch", "watch",
                 "approach s", "montre"]),
    ("afstandsmeter", ["afstandsmeter", "rangefinder", "laser", "approach z", "approach g", "télémètre",
                       "telemetre"]),
    ("set", ["complete set", "golfset", "volledige set", "halve set", "half set", "starterset",
             "set golfclubs", "golfclubs set", "golf set", "complete golf", "clubs + tas",
             "clubs met tas", "set + tas", "set met tas", "set complet", "série complète",
             "ensemble de golf", "kit de golf"]),
    ("ijzers", ["ijzers", "ijzerset", "irons", "iron set", "ijzer set", "set ijzers", "4-pw", "5-pw", "6-pw",
                "série de fers", "serie de fers", "set de fers", " fers "]),
    ("putter", ["putter"]),
    ("wedge", ["wedge", "sand wedge", "lob wedge", "sw ", " gap "]),
    ("hybride", ["hybride", "hybrid", "rescue", "utility"]),
    ("fairway", ["fairway", "wood 3", "hout 3", "3 wood", "3-wood", "5 wood", "5-wood", "houten 3", "fw ",
                 "bois de parcours", "bois 3", "bois 5"]),
    ("driver", ["driver"]),
    ("tas", ["golftas", "standbag", "stand bag", "cartbag", "cart bag", "tourbag", "sac de golf", "tas"]),
]

MERKEN = ["scotty cameron", "taylormade", "taylor made", "callaway", "titleist", "ping", "cobra",
          "mizuno", "srixon", "cleveland", "odyssey", "wilson", "pxg", "honma", "xxio", "benross",
          "tour edge", "motocaddy", "powakaddy", "big max", "bigmax", "clicgear", "jucad", "stewart",
          "bushnell", "garmin", "nikon", "sun mountain", "ogio", "macgregor", "inesis", "adams",
          "yonex", "lynx", "mkids", "us kids", "spalding", "dunlop", "nike"]

MODELLEN = [  # model maakt veel uit voor de prijs; lijst mag je zelf aanvullen
    "qi35", "qi10", "stealth 2", "stealth2", "stealth", "sim2", "sim max", "sim", "m6", "m5", "m4",
    "m3", "m2", "m1", "p790", "p770", "p7mc", "spider", "rbz", "burner", "r11", "r15", "sldr",
    "elyte", "ai smoke", "paradym", "rogue", "epic", "mavrik", "big bertha", "apex", "x-20", "x20",
    "x2 hot", "xr", "g440", "g430", "g425", "g410", "g400", "g30", "i230", "i525", "i59", "blueprint",
    "tsr3", "tsr2", "tsi3", "tsi2", "ts3", "ts2", "t100", "t150", "t200", "t300", "t350", "917", "915",
    "darkspeed", "aerojet", "ltdx", "radspeed", "speedzone", "king", "jpx", "zx5", "zx7", "zx",
    "launcher", "newport", "phantom", "special select", "white hot", "tri-hot", "jailbird",
    "m5 gps", "m7", "m1 gps", "fusion", "fusion 2", "tour v6", "tour v5", "tour v4", "pro x3",
    "pro xe", "approach z82", "approach z30", "s70", "s62", "s60", "s44", "s42", "s40", "s20",
    "s12", "s10", "ct10",
]

GOLF_WOORDEN = ["golf", "driver", "putter", "ijzers", "irons", "wedge", "hybride", "fairway",
                "trolley", "golftas", "standbag", "cartbag"] + MERKEN
NIET_GOLF = ["volkswagen", "vw golf", "golf 7", "golf 6", "golf 5", "golf 8", "golf gti", "tdi",
             "minigolf", "golfplaten", "golfplaat", "golfkarton", "golfbreker", "golfslag"]


def tekst(l):
    return (" " + (l.get("title") or "") + " " + (l.get("description") or "") + " ").lower()


def ext_attr(l, key):
    for a in (l.get("extendedAttributes") or []) + (l.get("attributes") or []):
        if a.get("key") == key:
            return (a.get("value") or "").lower()
    return ""


def is_golf(l):
    if l.get("categoryId") == GOLF_CAT:
        return True
    t = tekst(l)
    if any(w in t for w in NIET_GOLF):
        return False
    if "garmin" in t and ("approach" in t or "golf" in t):  # golfhorloges staan vaak bij Horloges/Telecom
        return True
    return "/golf/" in (l.get("vipUrl") or "") or ("golf" in t and l.get("l1CategoryId") == SPORT_CAT)


ACCESSOIRES = ["cover", "hoes", "housse", "couvre", "grip", " tee", "ballen", "balls", "balles",
               "handschoen", "gant", "polo", " pet ", "casquette", "schoenen", "chaussures", "shoes",
               "paraplu", "parapluie", "umbrella", "regenhoes", "sticker", "boek", "livre", "poster"]


def soort(l):
    titel = " " + (l.get("title") or "").lower() + " "
    if any(w in titel for w in ACCESSOIRES):
        return None  # losse accessoires: headcovers, grips, ballen, kledij...
    for naam, woorden in TYPES:  # eerst enkel de titel
        if any(w in titel for w in woorden):
            return naam
    attr = ext_attr(l, "type")
    mapping = {"set": "set", "tas": "tas", "trolley": "trolley", "driver": "driver",
               "putter": "putter", "ijzers": "ijzers", "wedge": "wedge", "hybride": "hybride",
               "fairway": "fairway", "afstandsmeter": "afstandsmeter"}
    for k, v in mapping.items():
        if k in attr:
            return v
    t = tekst(l)
    for naam, woorden in TYPES:
        if naam != "tas" and any(w in t for w in woorden):
            return naam
    return None


def merk(l):
    t = tekst(l)
    for m in MERKEN:
        if re.search(r"(?<![a-z])" + re.escape(m) + r"(?![a-z])", t):
            return {"taylor made": "taylormade", "bigmax": "big max"}.get(m, m)
    b = ext_attr(l, "brand")
    if b and "overige" not in b:
        return b
    return None


def model(l):
    titel = " " + (l.get("title") or "").lower() + " "
    for m in MODELLEN:
        if re.search(r"(?<![a-z0-9])" + re.escape(m) + r"(?![a-z0-9])", titel):
            return m.replace(" ", "")
    return None


def prijs(l):
    """Geeft (prijs_in_euro of None, prijstype)."""
    pi = l.get("priceInfo") or {}
    typ = pi.get("priceType", "")
    cents = pi.get("priceCents") or 0
    if typ == "FREE":
        return 0.0, typ
    if typ in ("FIXED", "MIN_BID") and cents > 0:
        return cents / 100.0, typ
    return None, typ


# ---------------------------------------------------------------- netwerk
def haal(params, pogingen=3):
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(pogingen):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa
            print(f"  ! fout bij ophalen ({e}), poging {i + 1}/{pogingen}")
            time.sleep(3 * (i + 1))
    return {"listings": []}


def zoek_zone(zone, zoektermen):
    """Nieuwste golfadvertenties binnen de straal van een postcode."""
    gevonden = {}
    basis = {"l1CategoryId": SPORT_CAT, "postcode": zone["postcode"],
             "distanceMeters": int(zone.get("straal_km", 10) * 1000),
             "limit": 100, "offset": 0, "sortBy": "SORT_INDEX", "sortOrder": "DECREASING",
             "viewOptions": "list-view"}
    # 1) alle nieuwste sportadvertenties, gefilterd op golf
    for l in haal(basis).get("listings", []):
        if is_golf(l):
            gevonden[l["itemId"]] = l
    time.sleep(1)
    # 2) extra zoektermen (vangt ook verkeerd gecategoriseerde advertenties)
    for term in zoektermen:
        p = dict(basis, query=term)
        p.pop("l1CategoryId")
        for l in haal(p).get("listings", []):
            if is_golf(l):
                gevonden[l["itemId"]] = l
        time.sleep(1)
    return gevonden


# ---------------------------------------------------------------- Vinted
VINTED = "https://www.vinted.be"


def haal_html(url):
    """Normale zoekpagina ophalen. Geeft (html, status). Geen omzeiling van botbescherming."""
    try:
        req = urllib.request.Request(url, headers={**HEADERS, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8", "ignore"), r.status
    except urllib.error.HTTPError as e:
        return "", e.code
    except Exception as e:  # noqa
        print(f"  ! Vinted fout: {e}")
        return "", 0


def _veld(chunk, patroon):
    m = re.search(patroon, chunk)
    return m.group(1) if m else None


def vinted_parse(html):
    """Haalt de advertenties uit de zoekpagina (zitten als JSON in de pagina)."""
    t = html.replace('\\"', '"').replace("\\\\", "\\")
    items = []
    for chunk in t.split('"productItem":')[1:]:
        chunk = chunk[:6000]
        iid = _veld(chunk, r'^\{"id":(\d+)')
        titel = _veld(chunk, r'"title":"((?:[^"\\]|\\.)*)"')
        url = _veld(chunk, r'"url":"(/items/[^"]+)"')
        prijs_ = _veld(chunk, r'"price":\{"amount":"([\d.]+)"')
        totaal = _veld(chunk, r'"totalItemPrice":\{"amount":"([\d.]+)"')
        if not (iid and titel and url and prijs_):
            continue
        try:
            titel = json.loads('"' + titel + '"')
        except Exception:  # noqa
            pass
        items.append({
            "id": iid, "title": titel, "url": VINTED + url, "prijs": float(prijs_),
            "totaal": float(totaal or prijs_),
            "merk": _veld(chunk, r'"firstLine":"((?:[^"\\]|\\.)*)"') or "",
            "staat": _veld(chunk, r'"secondLine":"((?:[^"\\]|\\.)*)"') or "",
            "zakelijk": '"isBusiness":true' in chunk,
        })
    return items


def vinted_naar_listing(v):
    """Zet een Vinted-item om naar dezelfde vorm als een 2dehands-advertentie."""
    return {
        "itemId": "v" + v["id"], "title": v["title"], "description": "",
        "priceInfo": {"priceCents": int(round(v["prijs"] * 100)), "priceType": "FIXED"},
        "location": {"cityName": "Vinted (verzending)"}, "vipUrl": v["url"],
        "extendedAttributes": [{"key": "brand", "value": v["merk"]}],
        "attributes": [{"key": "condition", "value": v["staat"]}],
        "_bron": "vinted", "_totaal": v["totaal"],
    }


def vinted_is_golf(l):
    s = soort(l)
    if not s:
        return False
    t = tekst(l) + " " + ext_attr(l, "brand")
    if any(w in t for w in NIET_GOLF):
        return False
    if s == "horloge" and not ("approach" in t or "golf" in t):
        return False  # gewone sporthorloges overslaan
    return "golf" in t or merk(l) in MERKEN


def zoek_vinted(cfg):
    """Nieuwste Vinted-advertenties per zoekterm. Geeft (dict, geblokkeerd)."""
    vc = cfg.get("vinted") or {}
    gevonden, blok, ok = {}, 0, 0
    for term in vc.get("zoektermen", []):
        url = VINTED + "/catalog?" + urllib.parse.urlencode({"search_text": term, "order": "newest_first"})
        html, status = haal_html(url)
        if status in (403, 429) or (html and "captcha-delivery" in html):
            blok += 1
            print(f"  ! Vinted blokkeert de vraag ({status}) voor '{term}'")
            if blok >= 2 and ok == 0:
                break  # niet blijven aandringen
        elif html:
            ok += 1
            for v in vinted_parse(html):
                l = vinted_naar_listing(v)
                if vinted_is_golf(l):
                    gevonden[l["itemId"]] = l
        time.sleep(vc.get("pauze_sec", 3))
    return gevonden, (blok > 0 and ok == 0)


def vinted_marktprijs(soort_, merk_, model_, cfg, cache):
    """Mediaan van de Vinted-vraagprijzen (wat de verkoper ontvangt; Vinted rekent verkopers niets aan)."""
    if not merk_:
        return None, "geen merk", 0
    kandidaten = []
    if model_:
        kandidaten.append((f"vinted|{soort_}|{merk_}|{model_}", f"{merk_} {model_} {zoekwoord(soort_)}"))
    kandidaten.append((f"vinted|{soort_}|{merk_}", f"{merk_} {zoekwoord(soort_)}"))
    nu = time.time()
    max_leeftijd = cfg.get("markt_cache_dagen", 3) * 86400
    for sleutel, query in kandidaten:
        c = cache.get(sleutel)
        if not c or nu - c["ts"] > max_leeftijd:
            html, status = haal_html(VINTED + "/catalog?" + urllib.parse.urlencode({"search_text": query}))
            time.sleep((cfg.get("vinted") or {}).get("pauze_sec", 3))
            if not html:
                return None, f"Vinted niet bereikbaar ({status})", 0  # niet cachen, later opnieuw
            prijzen = []
            for v in vinted_parse(html):
                l = vinted_naar_listing(v)
                if not vinted_is_golf(l) or soort(l) != soort_ or merk(l) != merk_:
                    continue
                if len(sleutel.split("|")) == 4 and model(l) != model_:
                    continue
                if v["prijs"] >= 5:
                    prijzen.append(v["prijs"])
            c = {"ts": nu, "n": len(prijzen), "mediaan": statistics.median(prijzen) if prijzen else None}
            cache[sleutel] = c
        if c["mediaan"] and c["n"] >= cfg.get("min_vergelijkbare", 5):
            return c["mediaan"], f"mediaan van {c['n']} Vinted-advertenties", c["n"]
    return None, "te weinig vergelijkbare op Vinted", 0


def marktprijs(soort_, merk_, model_, cfg, cache):
    """Mediaan van de vraagprijzen in heel België voor hetzelfde soort/merk(/model)."""
    vast = cfg.get("vaste_marktprijzen", {})
    for sleutel in ([f"{soort_}|{merk_}|{model_}"] if model_ else []) + [f"{soort_}|{merk_}", f"{soort_}"]:
        if sleutel in vast:
            return float(vast[sleutel]), f"vaste prijs ({sleutel})", 0

    kandidaten = []
    if merk_ and model_:
        kandidaten.append((f"{soort_}|{merk_}|{model_}", f"{merk_} {model_} {zoekwoord(soort_)}"))
    if merk_:
        kandidaten.append((f"{soort_}|{merk_}", f"{merk_} {zoekwoord(soort_)}"))

    nu = time.time()
    max_leeftijd = cfg.get("markt_cache_dagen", 3) * 86400
    for sleutel, query in kandidaten:
        c = cache.get(sleutel)
        if not c or nu - c["ts"] > max_leeftijd:
            prijzen = []
            for offset in (0, 100):
                params = {"query": query, "l1CategoryId": SPORT_CAT, "limit": 100,
                          "offset": offset, "viewOptions": "list-view"}
                if soort_ == "horloge":  # horloges staan vaak buiten Sport en Fitness
                    params.pop("l1CategoryId")
                data = haal(params)
                lst = data.get("listings", [])
                for l in lst:
                    if not is_golf(l) or soort(l) != soort_:
                        continue
                    if merk(l) != merk_ or (len(sleutel.split("|")) == 3 and model(l) != model_):
                        continue
                    p, _ = prijs(l)
                    if p and p >= 5:
                        prijzen.append(p)
                time.sleep(1)
                if len(lst) < 100:
                    break
            c = {"ts": nu, "n": len(prijzen),
                 "mediaan": statistics.median(prijzen) if prijzen else None}
            cache[sleutel] = c
        if c["mediaan"] and c["n"] >= cfg.get("min_vergelijkbare", 5):
            return c["mediaan"], f"mediaan van {c['n']} advertenties ({sleutel})", c["n"]
    return None, "te weinig vergelijkbare advertenties", 0


def zoekwoord(s):
    return {"set": "golfset", "ijzers": "ijzers", "tas": "golftas", "trolley": "trolley",
            "afstandsmeter": "afstandsmeter", "hybride": "hybrid",
            "horloge": "approach"}.get(s, s)


# ---------------------------------------------------------------- beoordeling
def beoordeel(l, cfg, cache):
    p, typ = prijs(l)
    s, m, mo = soort(l), merk(l), model(l)
    info = {"soort": s, "merk": m, "model": mo, "prijs": p, "prijstype": typ}

    toegelaten = [x.lower() for x in cfg.get("alleen_merken") or []]
    if toegelaten and m not in toegelaten:
        info.update(koopje=False, reden=f"merk niet in je lijst ({m or 'onbekend'})")
        return info

    if p is None:
        info["reden"] = "geen vaste prijs (bieden/zie omschrijving)"
        info["koopje"] = bool(cfg.get("meld_ook_bieden")) and typ == "FAST_BID"
        return info
    if typ == "FREE":
        info.update(koopje=True, reden="GRATIS")
        return info
    if s is None:
        info.update(koopje=False, reden="soort niet herkend")
        return info

    absoluut = cfg.get("absolute_koopjes", {}).get(s)
    kanalen = cfg.get("verkoop_op", ["2dehands"])
    markten = {}
    if "2dehands" in kanalen:
        mp, bron, _ = marktprijs(s, m, mo, cfg, cache) if (m or s in cfg.get("vaste_marktprijzen", {})) else (None, "geen merk", 0)
        if mp:
            markten["2dehands"] = mp
    vc = cfg.get("vinted") or {}
    if "vinted" in kanalen and vc.get("aan") and s not in vc.get("niet_verkopen_op_vinted", []):
        mp, _, _ = vinted_marktprijs(s, m, mo, cfg, cache)
        if mp:
            markten["vinted"] = mp
    info["markten"] = {k: round(v) for k, v in markten.items()}
    kanaal = max(markten, key=markten.get) if markten else None
    markt = markten.get(kanaal)
    info.update(markt=markt, kanaal=kanaal)

    # wat het je echt kost: bij Vinted servicekost + verzending, bij 2dehands je rit
    if l.get("_bron") == "vinted":
        vk = (cfg.get("vinted") or {}).get("verzendkosten", {})
        verzend = vk.get(s, vk.get("standaard", 7))
        kost = l.get("_totaal", p) + verzend
        info.update(kosten_extra=round(kost - p, 2), verzend=verzend)
    else:
        kost = p + cfg.get("kosten_per_aankoop_euro", 5)
    info["kost"] = round(kost, 2)

    if markt:
        verkoop = markt * cfg.get("verkoop_korting", 0.9)
        winst = verkoop - kost
        info.update(verkoop=round(verkoop), winst=round(winst))
        if kost <= markt * cfg.get("max_prijs_vs_markt", 0.65) and winst >= cfg.get("min_winst_euro", 40):
            info.update(koopje=True, reden=f"{round(100 * kost / markt)}% van marktprijs (incl. kosten)")
            return info
    if absoluut is not None and p <= absoluut and p >= 5:
        info.update(koopje=True, reden=f"onder je spotprijs voor {s} (€{absoluut})")
        return info
    info.update(koopje=False, reden="niet goedkoop genoeg")
    return info


# ---------------------------------------------------------------- melding
def stuur(cfg, titel, bericht, url=None, prio="high", tags="golf,moneybag"):
    topic = cfg.get("ntfy_topic", "")
    if not topic or topic.startswith("VERANDER"):
        print("  ! ntfy_topic staat nog niet ingesteld in config.json - melding niet verstuurd")
        return
    payload = {"topic": topic, "title": titel, "message": bericht, "tags": tags.split(","),
               "priority": {"min": 1, "low": 2, "default": 3, "high": 4, "max": 5}.get(prio, 3)}
    if url:
        payload["click"] = url
        payload["actions"] = [{"action": "view", "label": "Open advertentie", "url": url}]
    req = urllib.request.Request(cfg.get("ntfy_server", "https://ntfy.sh").rstrip("/"),
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:  # noqa
        print(f"  ! melding mislukt: {e}")


def melding_tekst(l, info, zone):
    loc = l.get("location") or {}
    if l.get("_bron") == "vinted":
        regels = [f"€{info['prijs']:.0f} op Vinted + ±€{info.get('kosten_extra', 0):.0f} servicekost/verzending"
                  f" = ±€{info.get('kost', info['prijs']):.0f}"]
    else:
        regels = [f"€{info['prijs']:.0f}" + (" (bieden vanaf)" if info["prijstype"] == "MIN_BID" else "")
                  + f" · {loc.get('cityName', '?')} ({zone})"]
    if info.get("markt"):
        markten = " · ".join(f"{k} ±€{v}" for k, v in info.get("markten", {}).items())
        regels.append(f"Markt: {markten}")
        regels.append(f"Verkoop op {info['kanaal']} ±€{info['verkoop']} → winst ±€{info['winst']}")
    regels.append(f"Waarom: {info['reden']}")
    regels.append(" · ".join(x for x in [info.get("soort"), info.get("merk"), info.get("model")] if x))
    return "\n".join(regels)


# ---------------------------------------------------------------- opslag
def laad(pad, standaard):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa
        return standaard


def bewaar(pad, data):
    os.makedirs(os.path.dirname(pad), exist_ok=True)
    tmp = pad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, pad)


# ---------------------------------------------------------------- hoofdlus
def main(argv):
    cfg = laad(CONFIG_PAD, None)
    if cfg is None:
        sys.exit("config.json niet gevonden of ongeldig")
    if os.environ.get("NTFY_TOPIC"):  # geheim topic via GitHub Secrets
        cfg["ntfy_topic"] = os.environ["NTFY_TOPIC"]

    if "--test" in argv:
        stuur(cfg, "Golf Flipper werkt!", "Je ontvangt meldingen voor golfkoopjes.",
              url=BASIS + "/l/sport-en-fitness/golf/", prio="default", tags="white_check_mark")
        print("Testmelding verstuurd.")
        return

    droog, alles = "--droog" in argv, "--alles" in argv
    gezien = laad(GEZIEN_PAD, {})
    cache = laad(MARKT_PAD, {})

    def bron_van(iid):
        return "vinted" if iid.startswith("v") else "2dehands"
    nieuw_bron = {b for b in ("2dehands", "vinted") if not any(bron_van(k) == b for k in gezien if not k.startswith("_"))}

    alle = {}
    for zone in cfg["zones"]:
        print(f"Zone {zone['naam']} ({zone['postcode']}, {zone.get('straal_km', 10)} km)...")
        for iid, l in zoek_zone(zone, cfg.get("zoektermen", [])).items():
            alle.setdefault(iid, (l, zone["naam"]))
    print(f"{len(alle)} golfadvertenties in je zones.")

    if (cfg.get("vinted") or {}).get("aan"):
        print("Vinted...")
        vinted, geblokkeerd = zoek_vinted(cfg)
        print(f"{len(vinted)} golfadvertenties op Vinted.")
        for iid, l in vinted.items():
            alle.setdefault(iid, (l, "Vinted"))
        vandaag = datetime.now().strftime("%Y-%m-%d")
        if geblokkeerd and gezien.get("_vinted_blok_melding") != vandaag and not droog:
            stuur(cfg, "Vinted blokkeert de spotter",
                  "Vinted weigert vandaag de zoekvragen van de server (botbescherming). "
                  "2dehands blijft gewoon werken. Je krijgt hier max. 1 melding per dag over.",
                  prio="low", tags="warning")
            gezien["_vinted_blok_melding"] = vandaag

    nieuw = {k: v for k, v in alle.items() if alles or k not in gezien}
    for b in sorted(nieuw_bron):
        if not alles:
            print(f"Eerste run voor {b}: alles wordt als 'gezien' gemarkeerd zonder meldingen.")
    meldingen = 0
    for iid, (l, zone) in nieuw.items():
        stil = bron_van(iid) in nieuw_bron and not alles
        info = {"koopje": False} if stil else beoordeel(l, cfg, cache)
        gezien[iid] = int(time.time())
        if not info.get("koopje"):
            continue
        vip = l.get("vipUrl") or ""
        url = vip if vip.startswith("http") else BASIS + vip
        icoon = "👕" if l.get("_bron") == "vinted" else "⛳"
        print(f"  KOOPJE: {l.get('title')} | {melding_tekst(l, info, zone)!r} | {url}")
        if not droog:
            stuur(cfg, f"{icoon} {l.get('title', '')[:80]}", melding_tekst(l, info, zone), url=url)
            meldingen += 1

    grens = time.time() - 60 * 86400  # vergeet advertenties ouder dan 60 dagen
    gezien = {k: v for k, v in gezien.items() if k.startswith("_") or v > grens}
    if not droog:
        bewaar(GEZIEN_PAD, gezien)
    bewaar(MARKT_PAD, cache)
    print(f"Klaar om {datetime.now(timezone.utc).astimezone():%H:%M}: {len(nieuw)} nieuw, {meldingen} melding(en).")


if __name__ == "__main__":
    main(sys.argv[1:])
