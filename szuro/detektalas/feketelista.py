# --- 4/a. Feketelistás keresés (pontos és közelítő) ---

from difflib import SequenceMatcher
from .. import config


def load_blacklist(fajl=config.FEKETELISTA_FAJL):
    """
    Beolvassa a tiltott kifejezéseket a szövegfájlból.
    Soronként egy kifejezés, az üres és a '#'-kal kezdődő sorokat kihagyjuk.
    """
    lista = []
    with open(fajl, encoding='utf-8') as f:
        for sor in f:
            sor = sor.strip().lower()
            if sor and not sor.startswith('#'):
                lista.append(sor)
    return lista


# Egyszer olvassuk be, amikor a modult importáljuk
BLACKLIST = load_blacklist()
GYENGE_LISTA = load_blacklist(config.GYENGE_KIFEJEZESEK_FAJL)


def exact_match(text, lista=BLACKLIST):
    """Visszaadja az első tiltott kifejezést, ami szó szerint benne van a szövegben."""
    for phrase in lista:
        if phrase in text:
            return phrase
    return None


def weak_matches(text):
    """Az összes gyenge kifejezés, ami benne van a szövegben (egyet csak egyszer számolunk)."""
    return [phrase for phrase in GYENGE_LISTA if phrase in text]


def fuzzy_search(text, phrase, kuszob=config.FUZZY_KUSZOB):
    """
    Közelítő keresés: a szövegen végigcsúsztatunk egy ugyanannyi szóból álló ablakot,
    és megnézzük, mennyire hasonlít a tiltott kifejezésre.
    Így az OCR-elírások ('ignore prevlous instructlons') is fennakadnak.
    (difflib-et használunk, hogy ne kelljen plusz csomagot telepíteni)
    """
    szavak = text.split()
    n = len(phrase.split())
    for i in range(len(szavak) - n + 1):
        ablak = ' '.join(szavak[i:i + n])
        if SequenceMatcher(None, ablak, phrase).ratio() >= kuszob:
            return ablak
    return None


def fuzzy_match(text):
    """
    Végignézi az egész feketelistát közelítő kereséssel.
    Visszatérés: (talált szövegrész, tiltott kifejezés) vagy None
    """
    for phrase in BLACKLIST:
        talalat = fuzzy_search(text, phrase)
        if talalat:
            return talalat, phrase
    return None
