# Ez a fájl hívja a többi szabályt és összeadja a pontokat.
# Új szabályhoz: új fájl a detektalas/ mappába, majd itt egy új "Ellenőrzés" blokk.

from .. import config
from ..szoveg.normalizalas import leet_normalize
from .feketelista import exact_match, weak_matches, fuzzy_match
from .anomalia import special_char_ratio


# A kikapcsolható szabályok nevei (csak a méréshez kell, élesben minden be van kapcsolva)
SZABALYOK = ('leet', 'gyenge', 'fuzzy', 'rejtett', 'anomalia')


def detect_prompt_injection(text, rejtett_szoveg=False, kikapcsolt=()):
    """
    Nem egyetlen szabály dönt, hanem összeadjuk a jelzéseket:
      - pontos feketelistás egyezés = azonnal 100 pont
      - gyenge kifejezés           = +40 pont kifejezésenként (egy = karantén, kettő = blokk)
      - közelítő (fuzzy) egyezés   = +60 pont
      - rejtett szöveg             = +30 pont (olyan szöveg, ami csak előfeldolgozás után látszik)
      - sok speciális karakter     = +20 pont (gyenge jel, kódos screenshotnál is előfordul)
    """
    if not text:
        return 0, ["Nincs értékelhető szöveg a képen."]

    pont = 0
    okok = []
    leet_text = leet_normalize(text) if 'leet' not in kikapcsolt else text

    # 1. Ellenőrzés: pontos egyezés (sima és leet-visszafejtett szövegben is)
    talalat = exact_match(text) or exact_match(leet_text)
    if talalat:
        return config.PONT_PONTOS_EGYEZES, [f"Kritikus parancs detektálva: '{talalat}'"]

    # 1/b. Ellenőrzés: gyenge kifejezések (ezek ártalmatlan szövegben is előfordulnak)
    if 'gyenge' not in kikapcsolt:
        for phrase in set(weak_matches(text) + weak_matches(leet_text)):
            pont += config.PONT_GYENGE_EGYEZES
            okok.append(f"Gyanús kifejezés: '{phrase}'")

    # 2. Ellenőrzés: közelítő egyezés (csak az erős listára)
    fuzzy = fuzzy_match(leet_text) if 'fuzzy' not in kikapcsolt else None
    if fuzzy:
        pont += config.PONT_FUZZY_EGYEZES
        okok.append(f"Hasonló kifejezés: '{fuzzy[0]}' ~ '{fuzzy[1]}'")

    # 3. Ellenőrzés: rejtett szöveg
    if rejtett_szoveg and 'rejtett' not in kikapcsolt:
        pont += config.PONT_REJTETT_SZOVEG
        okok.append("Rejtett szöveg: csak előfeldolgozás után olvasható (emberi szemmel nem látszik).")

    # 4. Ellenőrzés: anomália (obfuszkáció gyanú)
    arany = special_char_ratio(text)
    if arany > config.SPECIALIS_ARANY_KUSZOB and 'anomalia' not in kikapcsolt:
        pont += config.PONT_SPECIALIS_KARAKTER
        okok.append(f"Magas speciális karakter arány: {arany:.0%} (obfuszkáció gyanú).")

    if not okok:
        okok.append("Nem találtunk gyanús mintát.")
    return pont, okok
