# --- 3. Szöveg normalizálás ---

import re
import unicodedata

# Gyakori "leet" helyettesítések (pl. 1gn0re -> ignore)
LEET_TABLA = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't',
    '@': 'a', '$': 's', '!': 'i', '|': 'i',
})


def normalize_text(text):
    """
    Unicode normalizálás és kisbetűsítés.
    FONTOS: régen ASCII-ra kényszerítettük ('ignore'), de az a cirill 'о'-t nem
    'o'-ra cserélte, hanem kidobta, így az 'ignоre' -> 'ignre' lett és átment a szűrőn.
    Most csak az ékezeteket (kombináló jeleket) vesszük le, minden más marad.
    """
    decomposed = unicodedata.normalize('NFKD', text)
    ekezet_nelkul = ''.join(c for c in decomposed if not unicodedata.combining(c))
    # A sortöréseket és több szóközt egy szóközzé alakítjuk, különben
    # a két sorba tört "ignore previous / instructions" nem akad fenn
    return re.sub(r'\s+', ' ', ekezet_nelkul.lower()).strip()


def leet_normalize(text):
    """Leet karakterek visszafejtése, csak a feketelistás kereséshez használjuk."""
    return text.translate(LEET_TABLA)
