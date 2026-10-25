import re
from difflib import SequenceMatcher
from .. import config


def words(szoveg):
    #A szöveg szavai írásjelek nélkül, csak a 3 betűnél hosszabbak
    return {szo for szo in re.findall(r'\w+', szoveg) if len(szo) > 3}


def is_similar_to_any(szo, szavak, kuszob=0.7):
    #Igaz, ha a szó hasonlít valamelyikre (pl. 'hetk6znap' ~ 'hetkoznap' = OCR-elírás
    return any(SequenceMatcher(None, szo, masik).ratio() >= kuszob for masik in szavak)


def has_hidden_text(szovegek):

    eredeti_szavak = words(szovegek.get('0_eredeti', ''))
    uj_szavak = set()

    for kulcs, szoveg in szovegek.items():
        if '_le_' in kulcs:
            continue
        for szo in words(szoveg):
            if szo not in uj_szavak and not is_similar_to_any(szo, eredeti_szavak):
                uj_szavak.add(szo)

    return len(uj_szavak) >= config.REJTETT_SZAVAK_MIN
