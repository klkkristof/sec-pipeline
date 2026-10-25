# Unit tesztek a normalizáláshoz (nem kell hozzá Tesseract, gyors)
# Futtatás a projekt gyökeréből: pytest tests/

from szuro.szoveg.normalizalas import normalize_text, leet_normalize


def test_kisbetu_es_ekezet():
    assert normalize_text("Hagyd FIGYELMEN Kívül") == "hagyd figyelmen kivul"


def test_sortores_osszevonasa():
    # a két sorba tört kifejezésből egy sor lesz
    assert normalize_text("ignore previous\ninstructions") == "ignore previous instructions"


def test_tobb_szokoz():
    assert normalize_text("  forget    everything  ") == "forget everything"


def test_cirill_betu_nem_tunik_el():
    # régen az ASCII-ra kényszerítés kidobta a cirill 'о'-t -> 'ignre' lett
    eredmeny = normalize_text("ignоre")  # a második 'о' cirill!
    assert len(eredmeny) == 6


def test_leet():
    assert leet_normalize("1gn0r3 pr3v10us") == "ignore previous"
