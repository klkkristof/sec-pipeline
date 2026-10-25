# --- 4/c. Anomália: speciális karakterek aránya ---

import re


def special_char_ratio(text):
    """
    Speciális karakterek aránya a NEM szóköz karakterekhez képest.
    A nem latin betűk (pl. cirill) is speciálisnak számítanak, mert a normalizálás
    már nem dobja el őket.
    Rövid szövegnél (20 karakter alatt) nem számolunk, mert ott nincs értelme.
    """
    karakterek = text.replace(' ', '')
    if len(karakterek) < 20:
        return 0.0
    specialis = len(re.findall(r'[^a-z0-9]', karakterek))
    return specialis / len(karakterek)
