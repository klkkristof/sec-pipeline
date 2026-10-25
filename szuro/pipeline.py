# --- FŐ FOLYAMAT (Pipeline összekötése) ---
# Ez a fájl köti össze a lépéseket:
#   előszűrés -> [külön folyamatban: kép -> változatok -> OCR -> normalizálás] -> detektálás -> döntés

import os

from . import config
from .elokeszites.betoltes import load_image
from .elokeszites.valtozatok import make_variants, prepare_alpha
from .ocr.tesseract import extract_text_from_image
from .szoveg.normalizalas import normalize_text
from .detektalas.rejtett_szoveg import has_hidden_text
from .detektalas.pontozas import detect_prompt_injection
from .sandbox import check_file, run_isolated

# A három lehetséges döntés
ENGEDELYEZVE = 'ENGEDÉLYEZVE'
KARANTEN = 'KARANTÉN'
BLOKKOLVA = 'BLOKKOLVA'


def ocr_all_variants(image_path, normalizalas=True):
    
    #Betölti a képet, elkészíti az összes változatot és mindegyiken lefuttatja az OCR-t.
    #normalizalas=False esetén a nyers OCR-szöveget adja vissza (a kiértékelés így tudja
    #normalizálással és anélkül is kiértékelni ugyanazt az OCR-eredményt).
    
    tisztit = normalize_text if normalizalas else (lambda szoveg: szoveg)
    kepek, alfa = load_image(image_path)

    szovegek = {}
    for k_index, kep in enumerate(kepek):
        for nev, valtozat in make_variants(kep).items():
            szovegek[f'{k_index}_{nev}'] = tisztit(extract_text_from_image(valtozat))

    if alfa is not None:
        szovegek['alfa_csatorna'] = tisztit(extract_text_from_image(prepare_alpha(alfa)))

    return szovegek


def merge_texts(szovegek):
    #Összefűzi a különböző változatokból kinyert, egyedi szövegeket.
    egyedi = []
    for s in szovegek.values():
        if s and s not in egyedi:
            egyedi.append(s)
    return ' '.join(egyedi)


def make_decision(pont):
    #Pontszámból döntés (a küszöbök a config.py-ban vannak)
    if pont >= config.BLOKKOLASI_KUSZOB:
        return BLOKKOLVA
    if pont >= config.KARANTEN_KUSZOB:
        return KARANTEN
    return ENGEDELYEZVE


def decide_from_texts(szovegek, kikapcsolt=()):
    
    #A már kinyert szövegekből meghozza a döntést.
    #Külön függvény, mert a kiértékelés (ertekeles/) is ezt használja:
    #az OCR-t elég egyszer lefuttatni, a döntést pedig többféle beállítással újra lehet számolni.
    # Visszatérés: (döntés, pontszám, okok, összefűzött szöveg)
    
    osszes_szoveg = merge_texts(szovegek)
    rejtett = has_hidden_text(szovegek)
    pont, okok = detect_prompt_injection(osszes_szoveg, rejtett, kikapcsolt)
    return make_decision(pont), pont, okok, osszes_szoveg


def analyze_image_security(image_path, kiir=True):
    
    def log(szoveg):
        if kiir:
            print(szoveg)

    log(f"\n--- [ FÁJL ELEMZÉSE: {os.path.basename(image_path)} ] ---")
    try:
        # 0. Sandbox: előszűrés a kép megnyitása előtt (méret, valódi formátum)
        check_file(image_path)

        # 1-3. Kép betöltése, változatok, OCR, normalizálás - külön folyamatban, korlátokkal
        szovegek = run_isolated(ocr_all_variants, image_path)

        # 4. Detektálás és döntés
        dontes, pont, okok, osszes_szoveg = decide_from_texts(szovegek)

        log(f"Kinyert, normalizált szöveg:\n{osszes_szoveg if osszes_szoveg else '<ÜRES>'}\n")
        jel = {ENGEDELYEZVE: '+', KARANTEN: '?', BLOKKOLVA: '!'}[dontes]
        log(f"[{jel}] EREDMÉNY: {dontes}, pontszám: {pont}")
        if dontes == KARANTEN:
            log(f"[{jel}] A kép csak korlátozott módban mehet a modellhez (sandbox.quarantine_request)")
        for ok in okok:
            log(f"[{jel}] OK: {ok}")

        return dontes, okok, osszes_szoveg

    except Exception as e:
        # Fail: ha bármi hiba van (időtúllépés, hamis formátum, ...), blokkolunk
        log(f"[-] Hiba történt a fájl feldolgozása során: {e}")
        log(f"[!] EREDMÉNY: {BLOKKOLVA}")
        return BLOKKOLVA, [f"Hiba: {e}"], ""
