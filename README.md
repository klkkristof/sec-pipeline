# Képi prompt injection szűrő

Képeken elrejtett prompt injection támadások szűrése, mielőtt a kép eljutna egy multimodális LLM-hez,
valamint a szűrő hatékonyságának mérése.

## Mappaszerkezet

```
kepi_injection_szuro/
├── main.py                   # belépési pont: képek ellenőrzése parancssorból
├── requirements.txt
├── pytest.ini
│
├── szuro/                    # maga a szűrő, Python csomag
│   ├── __init__.py           # innen importálható: analyze_image_security
│   ├── config.py             # minden beállítás egy helyen
│   ├── pipeline.py           # a lépések összekötése, 3 szintű döntés
│   ├── sandbox.py            # előszűrés, elszigetelt futtatás, karantén
│   ├── elokeszites/          # 1. lépés: kép -> változatok
│   │   ├── betoltes.py       #   kép betöltése, alfa csatorna
│   │   └── valtozatok.py     #   nagyítás, kontraszt, csatornák, lekicsinyítés
│   ├── ocr/                  # 2. lépés
│   │   └── tesseract.py
│   ├── szoveg/               # 3. lépés
│   │   └── normalizalas.py
│   └── detektalas/           # 4. lépés: minden szabály külön fájl
│       ├── pontozas.py       #   összeadja a pontokat, ez dönt
│       ├── feketelista.py    #   pontos + közelítő (fuzzy) egyezés
│       ├── rejtett_szoveg.py #   szemmel nem látható szöveg
│       └── anomalia.py       #   speciális karakterek aránya
│
├── ertekeles/                # a szűrő mérése, az eredmenyfejezethez
│   ├── kepgenerator.py       #   támadástípusok és ártalmatlan képek generálása
│   ├── adathalmaz.py         #   címkézett tesztadathalmaz (szövegek, típusok)
│   ├── zaj.py                #   torzítások: JPEG, zaj, elmosás, átméretezés
│   ├── metrikak.py           #   konfúziós mátrix, precision, recall, F1, FP/FN arány
│   ├── tablazatok.py         #   a dolgozat 4. fejezetének táblázatai (Excel)
│   ├── grafikonok.py         #   ábrák (matplotlib)
│   └── futtatas.py           #   a teljes mérés, ezt kell indítani
│
├── adatok/
│   ├── feketelista.txt       # erős tiltott kifejezések -> azonnali blokk
│   ├── gyenge_kifejezesek.txt# gyenge kifejezések -> részpont (karantén)
│   └── sajat_kepek/          # (opcionális) valódi képek a méréshez, lásd lent
│
└── tests/                    
    ├── tesztkepek.py         # fix tesztképek
    ├── test_normalizalas.py  # unit tesztek (Tesseract nélkül)
    ├── test_detektalas.py    #   -||-
    ├── test_metrikak.py      #   -||-
    ├── test_lekicsinyites.py #   -||-
    ├── test_sandbox.py       #   -||-
    ├── test_ertekeles.py     #   -||-
    └── test_pipeline.py      # végponttól végpontig (Tesseract kell)
```

## A szűrő folyamata

```
kép -> check_file (sandbox előszűrés)
    -> [külön folyamatban, idő- és memóriakorláttal:
        load_image -> make_variants -> OCR (minden változatra) -> normalize_text]
    -> szövegek összefűzése -> detect_prompt_injection
    -> ENGEDÉLYEZVE / KARANTÉN / BLOKKOLVA
```

## Sandbox és döntési szintek

**1. A feldolgozás elszigetelése** (a gép védelme a rosszindulatú fájloktól):
- megnyitás előtt: fájlméret-korlát, valódi formátum ellenőrzése a fájl első bájtjai alapján
  (a kiterjesztésnek nem hiszünk), pixelszám-korlát
- a képfeldolgozás és az OCR külön folyamatban fut, időkorláttal (Linuxon/macOS-en memóriakorláttal is)
- bármilyen hiba vagy időtúllépés esetén blokkolunk (fail-closed)

**2. Karantén** (ha a szűrő bizonytalan):

| Pontszám | Döntés | Jelentés |
|---|---|---|
| 0-29 | ENGEDÉLYEZVE | mehet a modellhez |
| 30-49 | KARANTÉN | mehet, de korlátozott módban: eszközök nélkül, a képről olvasott szöveg megbízhatatlan adatként megjelölve (`sandbox.quarantine_request`) |
| 50+ | BLOKKOLVA | nem jut el a modellig |

A gyenge kifejezések (pl. „bypass”, „you are now”) ártalmatlan szövegben is előfordulnak, ezért csak
részpontot érnek: egy ilyen kifejezés karanténba küldi a képet, kettő vagy más gyanús jellel együtt blokkolja.

## Vizsgált támadástípusok

Az ütemtervben szereplő öt támadástípus:

| Típus | Leírás |
|---|---|
| `rejtett_szoveg` | három változat felváltva: közel fehér szöveg fehéren (`halvany`), apró halványszürke betűk egy ártalmatlan képen (`kis_betu`), átlátszó rétegben elrejtett szöveg (`atlatszo`) |
| `homoglif` | latin betűk helyett hasonló cirill betűk |
| `kontraszt` | színes háttéren alig eltérő színű szöveg |
| `lekicsinyites` | downscale-aliasing: csak kicsinyítés után jelenik meg a szöveg |
| `steganografia` | LSB-steganográfia: a szöveg bitjei a piros csatorna legalsó bitjeiben (a szűrőnek erre nincs modulja) |

Az ártalmatlan képeknek két csoportja van:
- `artalmatlan`: teljesen hétköznapi szövegek.
- `csapda`: ártalmatlan, de gyanús szavakat tartalmaz (pl. „You are now subscribed...”). Ezen mérhető a téves riasztás.

A támadások negyede **átfogalmazott** szöveg, feketelistás kifejezés nélkül. Ez mutatja meg a szabályalapú szűrés korlátját.

## Telepítés

```
git clone a repót

python -m venv .venv

.venv/Scripts/Activate.ps1 (ezek win környezetbe)

pip install -r requirements.txt
```

Ezen kívül kell a Tesseract OCR program, magyar nyelvi csomaggal:
- Windows: a telepítőben pipáld be a "Hungarian" nyelvet
- Linux: `sudo apt install tesseract-ocr tesseract-ocr-hun`

## Futtatás

A projekt gyökérmappájából:

```
python main.py                       # fix tesztképek generálása és ellenőrzése
python main.py kep1.png kep2.jpg     # saját képek ellenőrzése
pytest                               # tesztek futtatása

python -m ertekeles.futtatas --gyors # gyors mérés kisebb adathalmazon (kb. 7 perc)
python -m ertekeles.futtatas         # teljes mérés (kb. 15-20 perc, 2 magon)
```

A mérés eredményei az `eredmenyek/` mappába kerülnek:
- `osszesites.txt`: minden fontos szám egy helyen
- `reszletes.csv`: képenként a döntés, a pontszám, a futásidő és az okok
- `tablazatok.xlsx`: a dolgozat 4.1–4.7 táblázatai, lapanként egy (Excelből bemásolható a Wordbe)
- `ablacio.csv`, `robusztussag.csv`: nyers adatok
- `konfuzios_matrix.png`, `tipusonkent.png`, `ablacio.png`, `robusztussag.png`, `futasido.png`

### Saját (valódi) képek a méréshez

A generált képek mellé érdemes valódi képeket is tenni (screenshotok, fotók, plakátok), mert azokkal
hitelesebb a téves riasztások mérése:

```
adatok/sajat_kepek/tamado/       <- támadó képek
adatok/sajat_kepek/artalmatlan/  <- ártalmatlan képek
```

A `futtatas.py` automatikusan hozzáveszi őket az adathalmazhoz.

## Bővítés

- **Új tiltott kifejezés:** új sor az `adatok/feketelista.txt`-be vagy a `gyenge_kifejezesek.txt`-be (ékezet nélkül, kisbetűvel).
- **Új szabály:** új fájl a `szuro/detektalas/` mappába, majd egy új ellenőrzés a `pontozas.py`-ba.
- **Új támadástípus:** új függvény a `kepgenerator.py`-ba, és egy sor a `TAMADAS_TIPUSOK`-ba (`adathalmaz.py`).
- **Küszöbök, pontszámok, célméretek, sandbox korlátok:** `szuro/config.py`.
