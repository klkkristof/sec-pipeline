# --- 1/b. Előfeldolgozott változatok ---

from PIL import Image, ImageOps
from .. import config

# A config-ban szövegesen megadott módszerek -> Pillow konstansok
RESAMPLING = {
    'nearest': Image.NEAREST,
    'bilinear': Image.BILINEAR,
    'bicubic': Image.BICUBIC,
    'lanczos': Image.LANCZOS,
}


def upscale(img):
    """
    Kicsi szövegnél sokat segít a nagyítás
    (a Tesseract 30px körüli betűmérettel szeret dolgozni).
    """
    if img.width < 1500:
        szorzo = 2 if img.width > 600 else 3
        img = img.resize((img.width * szorzo, img.height * szorzo), Image.LANCZOS)
    return img


def make_variants(img):
    """
    Több előfeldolgozott változatot készítünk ugyanabból a képből.
    Az egyszerű kontrasztnövelés nem elég: a 254-es szürke 255-ös fehéren
    úgy is láthatatlan marad, ezért hisztogram-kiegyenlítést is használunk.
    Visszatérés: {változat neve: kép}
    """
    eredeti_meretu = img  # a lekicsinyítést az eredeti méretből kell csinálni
    img = upscale(img)
    gray = img.convert('L')

    valtozatok = {
        'eredeti': gray,
        'autocontrast': ImageOps.autocontrast(gray, cutoff=1),
        'equalize': ImageOps.equalize(gray),       # halvány szöveg kiemelése
        'invertalt': ImageOps.invert(gray),         # világos szöveg sötét háttéren
    }

    # Csatornánkénti vizsgálat: ha a szöveg csak pl. a kék csatornában tér el,
    # a szürkeárnyalatos képen eltűnhet
    if config.CSATORNANKENTI_VIZSGALAT:
        r, g, b = img.split()
        for nev, csatorna in (('piros', r), ('zold', g), ('kek', b)):
            valtozatok[f'{nev}_csatorna'] = ImageOps.equalize(csatorna)

    if config.LEKICSINYITES_VIZSGALAT:
        valtozatok.update(make_downscaled_variants(eredeti_meretu))

    return valtozatok


def make_downscaled_variants(img):
    """
    Downscale-aliasing elleni védelem: a képet lekicsinyítjük a tipikus
    modellbemeneti méretekre, többféle resampling módszerrel, ahogy egy
    multimodális modell előfeldolgozása is tenné.
    Ha a támadó egy adott módszerre (pl. nearest) tervezte a képet,
    akkor annál a változatnál előjön a rejtett szöveg.
    Visszatérés: {'le_<méret>_<módszer>': kép}
    """
    valtozatok = {}
    hosszabb_oldal = max(img.size)

    for meret in config.CELMERETEK:
        # ha a kép eleve nem sokkal nagyobb, nincs mit kicsinyíteni
        if hosszabb_oldal < meret * 1.5:
            continue
        arany = meret / hosszabb_oldal
        uj_meret = (max(1, round(img.width * arany)), max(1, round(img.height * arany)))

        for nev in config.RESAMPLING_MODSZEREK:
            kicsi = img.resize(uj_meret, RESAMPLING[nev])
            # az OCR-hez vissza kell nagyítani, különben túl kicsik a betűk
            nagy = kicsi.resize((uj_meret[0] * 3, uj_meret[1] * 3), Image.LANCZOS)
            valtozatok[f'le_{meret}_{nev}'] = ImageOps.autocontrast(nagy.convert('L'), cutoff=1)

    return valtozatok


def prepare_alpha(alfa):
    """Az alfa csatornából OCR-ezhető, kontrasztos szürke képet csinál."""
    return ImageOps.autocontrast(upscale(alfa).convert('L'))
