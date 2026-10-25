# --- KIÉRTÉKELÉS FUTTATÁSA ---
# Futtatás a projekt gyökeréből:
#   python -m ertekeles.futtatas           -> teljes mérés
#   python -m ertekeles.futtatas --gyors   -> kisebb adathalmaz, gyors kipróbáláshoz
#
# Lépések:
#   1. tesztadathalmaz generálása
#   2. OCR minden képen (párhuzamosan, képenként egyszer, nyers szöveggel)
#   3. alapmérés: konfúziós mátrix, precision/recall/F1, FP/FN arány, karantén arány, futásidő
#   4. OCR-konfigurációk összehasonlítása (dolgozat 4.4)
#   5. abláció: mi történik, ha egy-egy modult kikapcsolunk (dolgozat 4.5)
#   6. robusztusság: JPEG, zaj, elmosás, átméretezés hatása (dolgozat 4.6)
#   7. eredmények mentése (CSV, összesítő szöveg, grafikonok, táblázatok Excelben)
#
# Az OCR-t csak egyszer futtatjuk, és a NYERS szöveget tároljuk el. A normalizálást és a
# döntést utána a különböző beállításokkal újra kiszámoljuk (ez gyors, nem kell újra OCR).

import os
import sys
import csv
import time
import shutil
import statistics
from multiprocessing import Pool

from PIL import Image

from szuro.pipeline import ocr_all_variants, decide_from_texts, BLOKKOLVA, KARANTEN
from szuro.szoveg.normalizalas import normalize_text
from .adathalmaz import create_dataset, load_dataset
from .zaj import PERTURBACIOK
from .metrikak import confusion_matrix, metrics

ADAT_MAPPA = 'ertekeles_adatok'
EREDMENY_MAPPA = 'eredmenyek'
SAJAT_KEPEK_MAPPA = os.path.join('adatok', 'sajat_kepek')

GYORS = '--gyors' in sys.argv

# Adathalmaz mérete
TAMADAS_PER_TIPUS = 4 if GYORS else 16
ARTALMATLAN_DB = 10 if GYORS else 30
CSAPDA_DB = 8 if GYORS else 16

# A robusztussági mérés sok OCR-t igényel, ezért csak egy részhalmazon fut
ROBUSZTUSSAG_TAMADAS_PER_TIPUS = 1 if GYORS else 4
ROBUSZTUSSAG_ARTALMATLAN_DB = 4 if GYORS else 10

# A változatok neveinek végződései (lásd szuro/elokeszites/valtozatok.py)
KONTRASZT = ('_autocontrast', '_equalize', '_invertalt')
CSATORNAK = ('_csatorna',)


def csak_kisbetu(szoveg):
    """'Normalizálás nélküli' változat: csak kisbetűsítünk (Unicode és szóköz kezelése nélkül)."""
    return szoveg.lower()


# --- Beállítások az összehasonlításokhoz ---
# Mindegyik: (melyik OCR-változatok számítanak, milyen normalizálás, mely szabályok vannak kikapcsolva)

# 4.4: OCR-konfigurációk
OCR_KONFIGURACIOK = {
    'Alapértelmezett OCR (csak az eredeti kép)':
        (lambda k: k == '0_eredeti', normalize_text, ()),
    'OCR kontrasztjavítás után':
        (lambda k: k == '0_eredeti' or (k.startswith('0_') and k.endswith(KONTRASZT)), normalize_text, ()),
    'Több beállítás kombinálva (összes változat)':
        (lambda k: True, normalize_text, ()),
}

# 4.5: modulok ablációja
ABLACIOS_BEALLITASOK = {
    'Teljes rendszer':
        (lambda k: True, normalize_text, ()),
    'Képi előfeldolgozás nélkül':
        (lambda k: k == '0_eredeti', normalize_text, ()),
    'Kontrasztjavítás és színcsatornák nélkül':
        (lambda k: not k.endswith(KONTRASZT + CSATORNAK), normalize_text, ()),
    'Alfa csatorna vizsgálata nélkül':
        (lambda k: k.startswith('0_'), normalize_text, ()),
    'Lekicsinyítés nélkül':
        (lambda k: '_le_' not in k, normalize_text, ()),
    'Unicode-normalizálás nélkül':
        (lambda k: True, csak_kisbetu, ()),
    'Közelítő (fuzzy) keresés nélkül':
        (lambda k: True, normalize_text, ('fuzzy',)),
    'Gyenge kifejezések nélkül':
        (lambda k: True, normalize_text, ('gyenge',)),
    'Rejtett szöveg jelzés nélkül':
        (lambda k: True, normalize_text, ('rejtett',)),
    'Anomália-vizsgálat nélkül':
        (lambda k: True, normalize_text, ('anomalia',)),
}
TELJES = ABLACIOS_BEALLITASOK['Teljes rendszer']


# --- OCR futtatása ---

def ocr_worker(ut):
    """Egy kép összes változatának nyers OCR-je + az eltelt idő. (külön folyamatban fut)"""
    kezdes = time.perf_counter()
    try:
        szovegek = ocr_all_variants(ut, normalizalas=False)
    except Exception as e:
        print(f"[-] Hiba: {ut}: {e}")
        szovegek = None  # fail-closed: a döntésnél blokkoljuk
    return ut, szovegek, time.perf_counter() - kezdes


def run_ocr(utak, leiras):
    """Az összes képen lefuttatja az OCR-t, a processzormagok számának megfelelő párhuzamossággal."""
    print(f"\n[*] OCR: {leiras} ({len(utak)} kép)")
    eredmeny = {}
    with Pool() as pool:
        for i, (ut, szovegek, ido) in enumerate(pool.imap_unordered(ocr_worker, utak), 1):
            eredmeny[ut] = (szovegek, ido)
            if i % 20 == 0 or i == len(utak):
                print(f"    {i}/{len(utak)} kész")
    return eredmeny


# --- Döntés és mérőszámok ---

def evaluate(adatok, ocr_eredmeny, beallitas=TELJES):
    """
    Minden képre meghozza a döntést a megadott beállítással.
    Visszatérés: az adatok sorai kiegészítve: dontes, blokkolva, karanten, pont, ido_mp, okok
    """
    kulcs_szuro, normalizalo, kikapcsolt = beallitas
    sorok = []
    for adat in adatok:
        szovegek, ido = ocr_eredmeny[adat['ut']]
        if szovegek is None:
            dontes, pont, okok = BLOKKOLVA, 0, ['Hiba a feldolgozás során']
        else:
            szurt = {k: normalizalo(v) for k, v in szovegek.items() if kulcs_szuro(k)}
            dontes, pont, okok, _ = decide_from_texts(szurt, kikapcsolt)
        sorok.append({**adat, 'dontes': dontes,
                      'blokkolva': int(dontes == BLOKKOLVA), 'karanten': int(dontes == KARANTEN),
                      'pont': pont, 'ido_mp': round(ido, 3), 'okok': ' | '.join(okok)})
    return sorok


def summarize(sorok, karantennal=False):
    """
    Konfúziós mátrix és mérőszámok egy eredménylistából.
    karantennal=False: csak a BLOKKOLVA számít detektálásnak (szigorú)
    karantennal=True:  a KARANTÉN is detektálásnak számít
    """
    josolt = [1 if (s['blokkolva'] or (karantennal and s['karanten'])) else 0 for s in sorok]
    tp, fp, tn, fn = confusion_matrix([s['cimke'] for s in sorok], josolt)
    return (tp, fp, tn, fn), metrics(tp, fp, tn, fn)


def block_rate(sorok):
    """A blokkolt képek aránya egy csoportban."""
    return sum(s['blokkolva'] for s in sorok) / len(sorok) if sorok else 0.0


def quarantine_rate(sorok):
    """A karanténba került képek aránya egy csoportban."""
    return sum(s['karanten'] for s in sorok) / len(sorok) if sorok else 0.0


def group_by_type(sorok):
    """Típusonként csoportosít, a bejövő sorrendet megtartva."""
    csoportok = {}
    for s in sorok:
        csoportok.setdefault(s['tipus'], []).append(s)
    return csoportok


def compare_settings(adatok, ocr, beallitasok):
    """Lista: (név, szigorú metrikák, karanténos metrikák) minden beállításra."""
    eredmeny = []
    for nev, beallitas in beallitasok.items():
        sorok = evaluate(adatok, ocr, beallitas)
        eredmeny.append((nev, summarize(sorok)[1], summarize(sorok, karantennal=True)[1]))
    return eredmeny


# --- Robusztusság ---

def robustness_subset(adatok):
    """Részhalmaz a robusztussági méréshez: típusonként néhány támadás + néhány ártalmatlan kép."""
    reszhalmaz = []
    for tipus, csoport in group_by_type(adatok).items():
        db = ROBUSZTUSSAG_TAMADAS_PER_TIPUS if csoport[0]['cimke'] == 1 else ROBUSZTUSSAG_ARTALMATLAN_DB // 2
        reszhalmaz.extend(csoport[:db])
    return reszhalmaz


def run_robustness(reszhalmaz, alap_ocr):
    """
    Minden torzításra és szintre: torzított képek mentése, OCR, döntés.
    Visszatérés: {torzítás neve: [(szint, recall, recall karanténnal, fp_arany), ...]},
    az első pont a torzítás nélküli.
    """
    def meres(sorok, szint):
        szigoru = summarize(sorok)[1]
        return (szint, szigoru['recall'], summarize(sorok, karantennal=True)[1]['recall'], szigoru['fp_arany'])

    alap = meres(evaluate(reszhalmaz, alap_ocr), 'nincs')
    eredmeny = {}

    for nev, (fuggveny, szintek) in PERTURBACIOK.items():
        eredmeny[nev] = [alap]
        for szint in szintek:
            mappa = os.path.join(ADAT_MAPPA, 'robusztussag', f'{nev}_{szint}')
            os.makedirs(mappa, exist_ok=True)
            torzitott = []
            for adat in reszhalmaz:
                ut = os.path.join(mappa, os.path.splitext(adat['fajl'])[0] + '.png')
                fuggveny(Image.open(adat['ut']), szint).save(ut)
                torzitott.append({**adat, 'ut': ut})

            ocr = run_ocr([a['ut'] for a in torzitott], f'robusztusság: {nev}, szint = {szint}')
            eredmeny[nev].append(meres(evaluate(torzitott, ocr), szint))

    return eredmeny


# --- Adathalmaz jellemzői (dolgozat 4.1) ---

def dataset_stats(adatok):
    """Típusonként: képek száma, ebből átfogalmazott, átlagos felbontás, formátum."""
    statisztika = []
    for tipus, csoport in group_by_type(adatok).items():
        szelessegek, magassagok, modok = [], [], set()
        for a in csoport:
            with Image.open(a['ut']) as img:
                szelessegek.append(img.width)
                magassagok.append(img.height)
                modok.add(f"{img.format} ({img.mode})")
        statisztika.append({
            'tipus': tipus, 'cimke': csoport[0]['cimke'], 'db': len(csoport),
            'atfogalmazott': sum(a['atfogalmazott'] for a in csoport),
            'atlag_szelesseg': round(statistics.mean(szelessegek)),
            'atlag_magassag': round(statistics.mean(magassagok)),
            'formatum': ', '.join(sorted(modok)),
        })
    return statisztika


# --- Mentés ---

def save_csv(fajl, sorok, mezok):
    with open(fajl, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=mezok, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(sorok)


def szazalek(x):
    return f'{x * 100:5.1f}%'


def main():
    kezdes = time.time()
    os.makedirs(EREDMENY_MAPPA, exist_ok=True)

    # 1. Adathalmaz (mindig újragenerálunk, hogy a beállítások biztosan érvényesek legyenek)
    if os.path.isdir(ADAT_MAPPA):
        shutil.rmtree(ADAT_MAPPA)
    print("[*] Adathalmaz generálása...")
    create_dataset(ADAT_MAPPA, TAMADAS_PER_TIPUS, ARTALMATLAN_DB, CSAPDA_DB)
    adatok = load_dataset(ADAT_MAPPA, SAJAT_KEPEK_MAPPA)
    print(f"    {sum(a['cimke'] for a in adatok)} támadó és "
          f"{sum(1 - a['cimke'] for a in adatok)} ártalmatlan kép")

    # 2. OCR (nyers szöveg)
    alap_ocr = run_ocr([a['ut'] for a in adatok], 'teljes adathalmaz')

    # 3. Alapmérés
    sorok = evaluate(adatok, alap_ocr)
    (tp, fp, tn, fn), m = summarize(sorok)
    (ktp, kfp, ktn, kfn), km = summarize(sorok, karantennal=True)
    idok = [s['ido_mp'] for s in sorok]
    tamado = [s for s in sorok if s['cimke'] == 1]
    csoportok = group_by_type(sorok)
    tipusok = [(t, block_rate(cs), cs[0]['cimke'] == 1, quarantine_rate(cs)) for t, cs in csoportok.items()]

    # 4-5. OCR-konfigurációk és abláció (csak a döntést számoljuk újra)
    ocr_konfig = compare_settings(adatok, alap_ocr, OCR_KONFIGURACIOK)
    ablacio = compare_settings(adatok, alap_ocr, ABLACIOS_BEALLITASOK)

    # 6. Robusztusság
    reszhalmaz = robustness_subset(adatok)
    robusztussag = run_robustness(reszhalmaz, alap_ocr)

    # 7. Mentés
    save_csv(os.path.join(EREDMENY_MAPPA, 'reszletes.csv'), sorok,
             ['fajl', 'cimke', 'tipus', 'valtozat', 'atfogalmazott', 'dontes', 'pont', 'ido_mp', 'szoveg', 'okok'])
    save_csv(os.path.join(EREDMENY_MAPPA, 'ablacio.csv'),
             [{'beallitas': nev, 'recall': round(sz['recall'], 4), 'fp_arany': round(sz['fp_arany'], 4),
               'f1': round(sz['f1'], 4), 'f1_karantennal': round(k['f1'], 4)} for nev, sz, k in ablacio],
             ['beallitas', 'recall', 'fp_arany', 'f1', 'f1_karantennal'])
    save_csv(os.path.join(EREDMENY_MAPPA, 'ocr_konfiguraciok.csv'),
             [{'konfiguracio': nev, 'recall': round(sz['recall'], 4), 'recall_karantennal': round(k['recall'], 4),
               'fp_arany': round(sz['fp_arany'], 4), 'f1': round(sz['f1'], 4)} for nev, sz, k in ocr_konfig],
             ['konfiguracio', 'recall', 'recall_karantennal', 'fp_arany', 'f1'])
    save_csv(os.path.join(EREDMENY_MAPPA, 'robusztussag.csv'),
             [{'torzitas': nev, 'szint': s[0], 'recall': round(s[1], 4), 'recall_karantennal': round(s[2], 4),
               'fp_arany': round(s[3], 4)} for nev, lista in robusztussag.items() for s in lista],
             ['torzitas', 'szint', 'recall', 'recall_karantennal', 'fp_arany'])

    # Összesítő szöveg (a konzolra és fájlba is)
    sor = []
    sor.append("=== ALAPMÉRÉS ===")
    sor.append(f"Képek: {len(sorok)} ({len(tamado)} támadó, {len(sorok) - len(tamado)} ártalmatlan)")
    sor.append(f"Konfúziós mátrix (szigorú):     TP={tp}  FN={fn}  FP={fp}  TN={tn}")
    sor.append(f"Konfúziós mátrix (karanténnal): TP={ktp}  FN={kfn}  FP={kfp}  TN={ktn}")
    sor.append(f"  {'':<32} {'szigorú':>9} {'karanténnal':>12}")
    for kulcs, nev in (('pontossag', 'Pontosság (accuracy)'), ('precision', 'Precision'),
                       ('recall', 'Recall (detektálási arány)'), ('f1', 'F1'),
                       ('fp_arany', 'FP arány (téves riasztás)'), ('fn_arany', 'FN arány (átengedett támadás)')):
        sor.append(f"  {nev:<32} {szazalek(m[kulcs]):>9} {szazalek(km[kulcs]):>12}")
    feketelistas = [s for s in tamado if not s['atfogalmazott']]
    atfogalmazott = [s for s in tamado if s['atfogalmazott']]
    sor.append(f"  Recall feketelistás szövegre       {szazalek(block_rate(feketelistas))}")
    sor.append(f"  Recall átfogalmazott szövegre      {szazalek(block_rate(atfogalmazott))}")
    sor.append(f"Futásidő képenként: átlag {statistics.mean(idok):.2f} s, "
               f"medián {statistics.median(idok):.2f} s, max {max(idok):.2f} s")

    sor.append("\n=== TÍPUSONKÉNT ===")
    sor.append(f"  {'típus':<20} {'blokkolva':>9} {'karantén':>9}")
    for t, arany, tamado_e, karanten in tipusok:
        sor.append(f"  {t:<20} {szazalek(arany):>9} {szazalek(karanten):>9}   ({'támadó' if tamado_e else 'ártalmatlan'})")

    for cim, lista in (("OCR-KONFIGURÁCIÓK", ocr_konfig), ("ABLÁCIÓ", ablacio)):
        sor.append(f"\n=== {cim} ===")
        sor.append(f"  {'beállítás':<44} {'recall':>7} {'FP arány':>9} {'F1':>7}")
        for nev, sz, _ in lista:
            sor.append(f"  {nev:<44} {szazalek(sz['recall']):>7} {szazalek(sz['fp_arany']):>9} {szazalek(sz['f1']):>7}")

    sor.append(f"\n=== ROBUSZTUSSÁG ({len(reszhalmaz)} képes részhalmazon) ===")
    for nev, lista in robusztussag.items():
        sor.append(f"  {nev}: " + ', '.join(f"{s[0]} -> recall {szazalek(s[1]).strip()}, FP {szazalek(s[3]).strip()}"
                                            for s in lista))

    sor.append(f"\nTeljes futásidő: {(time.time() - kezdes) / 60:.1f} perc")
    osszesites = '\n'.join(sor)
    print('\n' + osszesites)
    with open(os.path.join(EREDMENY_MAPPA, 'osszesites.txt'), 'w', encoding='utf-8') as f:
        f.write(osszesites + '\n')

    # Táblázatok a dolgozathoz (Excel)
    try:
        from . import tablazatok
        tablazatok.save_tables(os.path.join(EREDMENY_MAPPA, 'tablazatok.xlsx'), {
            'adathalmaz': dataset_stats(adatok),
            'szigoru': ((tp, fp, tn, fn), m), 'karantennal': ((ktp, kfp, ktn, kfn), km),
            'idok': idok, 'csoportok': csoportok,
            'ocr_konfig': ocr_konfig, 'ablacio': ablacio,
            'robusztussag': robusztussag, 'reszhalmaz_db': len(reszhalmaz),
            'sorok': sorok,
        })
        print(f"[+] Táblázatok mentve: {EREDMENY_MAPPA}/tablazatok.xlsx")
    except ImportError:
        print("[!] Nincs telepítve az openpyxl, a táblázatok kimaradnak (pip install openpyxl)")

    # Grafikonok (ha nincs matplotlib, csak kihagyjuk)
    try:
        from . import grafikonok
        grafikonok.confusion_matrix_plot(tp, fp, tn, fn, os.path.join(EREDMENY_MAPPA, 'konfuzios_matrix.png'))
        grafikonok.tipus_bar(tipusok, os.path.join(EREDMENY_MAPPA, 'tipusonkent.png'))
        grafikonok.ablacio_bar([(nev, sz['recall'], sz['fp_arany']) for nev, sz, _ in ablacio],
                               os.path.join(EREDMENY_MAPPA, 'ablacio.png'))
        grafikonok.robusztussag_plot({nev: [(s[0], s[1], s[3]) for s in lista] for nev, lista in robusztussag.items()},
                                     os.path.join(EREDMENY_MAPPA, 'robusztussag.png'))
        grafikonok.futasido_hist(idok, os.path.join(EREDMENY_MAPPA, 'futasido.png'))
        print(f"[+] Grafikonok mentve: {EREDMENY_MAPPA}/")
    except ImportError:
        print("[!] Nincs telepítve a matplotlib, a grafikonok kimaradnak (pip install matplotlib)")


if __name__ == '__main__':
    main()
