# --- TÁBLÁZATOK A DOLGOZATHOZ ---
# A mérés eredményeiből elkészíti a 4. fejezet táblázatait egy Excel-fájlba (lapanként egy táblázat).
# Wordbe úgy a legegyszerűbb átvinni, hogy Excelben kijelölöd a táblázatot, és beilleszted.
# openpyxl kell hozzá (pip install openpyxl).

import statistics
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Belső típusnevek -> a dolgozatban használt nevek
TIPUS_NEVEK = {
    'rejtett_szoveg': 'Rejtett szöveg',
    'homoglif': 'Homoglif manipuláció (cirill betűk)',
    'kontraszt': 'Kontraszt-alapú támadás',
    'lekicsinyites': 'Downscale-aliasing',
    'steganografia': 'Steganográfia (LSB)',
    'artalmatlan': 'Normál (ártalmatlan) kép',
    'csapda': 'Csapda kép (ártalmatlan, gyanús szavakkal)',
}

# Torzítás neve -> (megjelenített név, a szint leírása)
TORZITAS_NEVEK = {
    'jpeg': ('JPEG-tömörítés', lambda s: f'minőség {s}'),
    'zaj': ('Gauss-zaj', lambda s: f'szórás {s}'),
    'elmosas': ('Elmosás', lambda s: f'sugár {str(s).replace(".", ",")} px'),
    'atmeretezes': ('Átméretezés', lambda s: f'{int(round(s * 100))}%-os méret'),
}

BETU = 'Arial'
VEKONY = Side(style='thin', color='A0A0A0')
KERET = Border(left=VEKONY, right=VEKONY, top=VEKONY, bottom=VEKONY)
FEJLEC_SZIN = PatternFill('solid', fgColor='1A3C4D')
OSSZESEN_SZIN = PatternFill('solid', fgColor='E8EEF1')


def nev(tipus):
    return TIPUS_NEVEK.get(tipus, tipus)


def write_table(ws, cim, fejlec, sorok, szelessegek, megjegyzes=None, kezdo_sor=1, szam_formatum=None):
    """
    Egy táblázat kiírása: cím, fejléc, sorok, alatta megjegyzés.
    szam_formatum: {oszlop index (0-tól): Excel formátum}, pl. {2: '0.00'}
    Visszatérés: a következő szabad sor száma.
    """
    ws.cell(row=kezdo_sor, column=1, value=cim).font = Font(name=BETU, bold=True, size=12)
    fejlec_sor = kezdo_sor + 2
    for i, h in enumerate(fejlec, 1):
        c = ws.cell(row=fejlec_sor, column=i, value=h)
        c.font = Font(name=BETU, bold=True, color='FFFFFF')
        c.fill = FEJLEC_SZIN
        c.alignment = Alignment(wrap_text=True, vertical='center')
        c.border = KERET

    for r, sor in enumerate(sorok, start=fejlec_sor + 1):
        osszesen = str(sor[0]).startswith('Összesen')
        for i, ertek in enumerate(sor):
            c = ws.cell(row=r, column=i + 1, value=ertek)
            c.font = Font(name=BETU, bold=osszesen)
            c.border = KERET
            c.alignment = Alignment(wrap_text=True, vertical='center')
            if osszesen:
                c.fill = OSSZESEN_SZIN
            if szam_formatum and i in szam_formatum and isinstance(ertek, float):
                c.number_format = szam_formatum[i]

    vege = fejlec_sor + len(sorok) + 1
    if megjegyzes:
        c = ws.cell(row=vege, column=1, value=megjegyzes)
        c.font = Font(name=BETU, size=9, italic=True)
        c.alignment = Alignment(wrap_text=True, vertical='top')
        ws.merge_cells(start_row=vege, start_column=1, end_row=vege, end_column=len(fejlec))
        ws.row_dimensions[vege].height = 45
        vege += 1

    for i, sz in enumerate(szelessegek):
        betu = chr(ord('A') + i)
        ws.column_dimensions[betu].width = max(ws.column_dimensions[betu].width or 0, sz)
    return vege + 1


def rate(sorok, kulcs):
    return sum(s[kulcs] for s in sorok) / len(sorok) if sorok else 0.0


def save_tables(fajl, adat):
    wb = Workbook()
    wb.remove(wb.active)

    # --- 4.1 Adathalmaz ---
    ws = wb.create_sheet('4.1 Adathalmaz')
    sorok = []
    for s in adat['adathalmaz']:
        sorok.append([nev(s['tipus']), 'támadó' if s['cimke'] == 1 else 'ártalmatlan', s['db'],
                      s['atfogalmazott'] if s['cimke'] == 1 else '–',
                      f"{s['atlag_szelesseg']} × {s['atlag_magassag']}", s['formatum']])
    tamado_db = sum(s['db'] for s in adat['adathalmaz'] if s['cimke'] == 1)
    osszes_db = sum(s['db'] for s in adat['adathalmaz'])
    sorok.append(['Összesen', f'{tamado_db} támadó, {osszes_db - tamado_db} ártalmatlan', osszes_db,
                  sum(s['atfogalmazott'] for s in adat['adathalmaz']), '', ''])
    write_table(ws, 'A tesztadatkészlet összetétele',
                ['Kategória', 'Csoport', 'Képek száma', 'Ebből átfogalmazott', 'Átlagos felbontás (px)', 'Formátum'],
                sorok, [40, 22, 12, 14, 20, 16],
                'Átfogalmazott: a támadó szöveg nem tartalmaz feketelistás kifejezést. '
                'A képeket a kiértékelő generátor állítja elő rögzített véletlenszám-maggal (seed = 42).')

    # --- 4.2 Általános teljesítmény ---
    ws = wb.create_sheet('4.2 Általános')
    (tp, fp, tn, fn), m = adat['szigoru']
    (ktp, kfp, ktn, kfn), km = adat['karantennal']
    sorok = [
        ['Valós pozitív (TP)', tp, ktp], ['Hamis pozitív (FP)', fp, kfp],
        ['Valós negatív (TN)', tn, ktn], ['Hamis negatív (FN)', fn, kfn],
        ['Pontosság (accuracy)', m['pontossag'], km['pontossag']],
        ['Precision', m['precision'], km['precision']],
        ['Recall (detektálási arány)', m['recall'], km['recall']],
        ['F1-score', m['f1'], km['f1']],
        ['Téves riasztási arány (FPR)', m['fp_arany'], km['fp_arany']],
        ['Átengedett támadások aránya (FNR)', m['fn_arany'], km['fn_arany']],
    ]
    idok = adat['idok']
    vege = write_table(ws, 'A detektáló rendszer általános teljesítménye',
                       ['Mérőszám', 'Csak blokkolás', 'Blokkolás vagy karantén'],
                       sorok, [36, 16, 22],
                       '„Csak blokkolás”: csak a BLOKKOLVA döntés számít detektálásnak. '
                       '„Blokkolás vagy karantén”: a KARANTÉN döntés is (a kép csak korlátozott módban jut a modellhez).',
                       szam_formatum={1: '0.00', 2: '0.00'})
    write_table(ws, 'Feldolgozási idő képenként',
                ['Mérőszám', 'Érték (s)'],
                [['Átlag', round(statistics.mean(idok), 2)], ['Medián', round(statistics.median(idok), 2)],
                 ['Maximum', round(max(idok), 2)]],
                [36, 16], kezdo_sor=vege, szam_formatum={1: '0.00'})

    # --- 4.3 Típusonként ---
    ws = wb.create_sheet('4.3 Típusonként')
    tamado_sorok, artalmatlan_sorok = [], []
    for tipus, cs in adat['csoportok'].items():
        blokk, karanten = rate(cs, 'blokkolva'), rate(cs, 'karanten')
        if cs[0]['cimke'] == 1:
            feketelistas = [s for s in cs if not s['atfogalmazott']]
            tamado_sorok.append([nev(tipus), len(cs), blokk, karanten, 1 - blokk - karanten, blokk, blokk + karanten,
                                 rate(feketelistas, 'blokkolva')])
        else:
            artalmatlan_sorok.append([nev(tipus), len(cs), blokk, karanten, 1 - blokk - karanten])
    szazalek = {i: '0.0%' for i in range(2, 8)}
    vege = write_table(ws, 'Eredmények támadástípusonként',
                       ['Támadástípus', 'Képek száma', 'Blokkolva', 'Karantén', 'Átengedve',
                        'Recall (csak blokkolás)', 'Recall (blokkolás vagy karantén)',
                        'Recall feketelistás szövegre (csak blokkolás)'],
                       tamado_sorok, [40, 10, 11, 11, 11, 14, 18, 20],
                       'Típusonként a támadások negyede átfogalmazott szöveg (feketelistás kifejezés nélkül), '
                       'ezek jellemzően átjutnak a szabályalapú szűrőn. Az utolsó oszlop csak a feketelistás '
                       'kifejezést tartalmazó támadásokra vonatkozik.', szam_formatum=szazalek)
    write_table(ws, 'Ártalmatlan képek döntései (téves riasztások)',
                ['Kategória', 'Képek száma', 'Blokkolva (FP)', 'Karantén', 'Engedélyezve'],
                artalmatlan_sorok, [40, 10, 11, 11, 11], kezdo_sor=vege, szam_formatum=szazalek)

    # --- 4.4 OCR-konfigurációk ---
    ws = wb.create_sheet('4.4 OCR')
    sorok = [[n, sz['recall'], k['recall'], sz['fp_arany'], sz['f1']] for n, sz, k in adat['ocr_konfig']]
    write_table(ws, 'Detektálás különböző OCR-konfigurációk mellett',
                ['OCR-konfiguráció', 'Recall (csak blokkolás)', 'Recall (blokkolás vagy karantén)',
                 'Téves riasztás (FPR)', 'F1-score'],
                sorok, [44, 14, 18, 14, 10],
                'Mindhárom konfiguráció ugyanazt az OCR-motort (Tesseract) használja; a különbség az, hogy '
                'hány előfeldolgozott képváltozaton fut le az OCR. A kombinált beállítás a színcsatornákat, '
                'az alfa csatornát és a lekicsinyített változatokat is tartalmazza.',
                szam_formatum={1: '0.00', 2: '0.00', 3: '0.00', 4: '0.00'})

    # --- 4.5 Abláció ---
    ws = wb.create_sheet('4.5 Abláció')
    teljes_f1 = adat['ablacio'][0][1]['f1']
    sorok = [[n, sz['f1'], sz['f1'] - teljes_f1, sz['recall'], sz['fp_arany'], k['f1']]
             for n, sz, k in adat['ablacio']]
    write_table(ws, 'A védelmi modulok hozzájárulása (abláció)',
                ['Konfiguráció', 'F1-score (csak blokkolás)', 'Változás a teljes rendszerhez képest',
                 'Recall', 'Téves riasztás (FPR)', 'F1-score (blokkolás vagy karantén)'],
                sorok, [40, 14, 16, 10, 14, 18],
                'Minden sorban pontosan egy modul van kikapcsolva. „Unicode-normalizálás nélkül”: a szöveget csak '
                'kisbetűsítjük, ékezet-eltávolítás és szóköz-összevonás nélkül.',
                szam_formatum={1: '0.00', 2: '+0.00;-0.00;0.00', 3: '0.00', 4: '0.00', 5: '0.00'})

    # --- 4.6 Robusztusság ---
    ws = wb.create_sheet('4.6 Robusztusság')
    sorok = []
    for tnev, lista in adat['robusztussag'].items():
        megjelenitett, szint_leiras = TORZITAS_NEVEK.get(tnev, (tnev, str))
        for szint, recall, k_recall, fpr in lista:
            sorok.append([megjelenitett, 'torzítás nélkül' if szint == 'nincs' else szint_leiras(szint),
                          recall, k_recall, fpr])
    write_table(ws, 'Robusztusság különböző képtorzítások mellett',
                ['Torzítás', 'Erősség', 'Recall (csak blokkolás)', 'Recall (blokkolás vagy karantén)',
                 'Téves riasztás (FPR)'],
                sorok, [18, 18, 14, 18, 14],
                f"A mérés egy {adat['reszhalmaz_db']} képből álló részhalmazon készült (típusonként 4 támadó, "
                '5 normál és 5 csapda kép). A torzítás a támadást is gyengítheti (pl. a JPEG-tömörítés '
                'eltünteti a közel fehér szöveget), ezt az értelmezésnél figyelembe kell venni.',
                szam_formatum={2: '0.00', 3: '0.00', 4: '0.00'})

    # --- 4.7 Hibák ---
    ws = wb.create_sheet('4.7 Hibák')
    hibak = []
    for s in adat['sorok']:
        if s['cimke'] == 1 and s['dontes'] != 'BLOKKOLVA':
            hibak.append(['Hamis negatív' if s['dontes'] == 'ENGEDÉLYEZVE' else 'Karantén (támadás)',
                          nev(s['tipus']), 'igen' if s['atfogalmazott'] else 'nem', s['szoveg'], s['okok']])
    for s in adat['sorok']:
        if s['cimke'] == 0 and s['dontes'] != 'ENGEDÉLYEZVE':
            hibak.append(['Hamis pozitív' if s['dontes'] == 'BLOKKOLVA' else 'Karantén (ártalmatlan)',
                          nev(s['tipus']), '–', s['szoveg'], s['okok']])
    write_table(ws, 'Hibás vagy bizonytalan döntések listája',
                ['Hiba típusa', 'Kategória', 'Átfogalmazott', 'A képen lévő szöveg', 'A szűrő indoklása'],
                hibak, [22, 34, 13, 52, 60])

    wb.save(fajl)
