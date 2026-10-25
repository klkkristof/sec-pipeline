# --- TORZÍTÁSOK A ROBUSZTUSSÁG MÉRÉSÉHEZ ---
# Minden torzítás egy függvény: (kép, szint) -> új kép.
# A szint jelentése torzításonként más (JPEG minőség, zaj szórása, stb.).
#
# FIGYELEM: a torzítás a támadást is elronthatja (pl. a JPEG tömörítés eltünteti
# a 254-es szürke szöveget, vagy az átlátszóságot). Ilyenkor a "támadás" valójában
# már nincs a képen, ezt az eredmények értelmezésénél figyelembe kell venni.

import io
import numpy as np
from PIL import Image, ImageFilter

ZAJ_SEED = 42  # fix seed, így a zajos mérés is megismételhető


def jpeg(img, minoseg):
    """JPEG tömörítés a megadott minőséggel (100 = legjobb). Az alfa csatorna elveszik."""
    buffer = io.BytesIO()
    img.convert('RGB').save(buffer, format='JPEG', quality=minoseg)
    buffer.seek(0)
    return Image.open(buffer).convert('RGB')


def gauss_zaj(img, szoras):
    """
    Gauss-zaj hozzáadása (szórás pixelértékben, 0-255 skálán), csatornánként külön.
    Fix seeddel generáljuk, így minden futtatásnál ugyanaz a zaj kerül a képre.
    """
    tomb = np.asarray(img.convert('RGB'), dtype=np.float32)
    rng = np.random.default_rng(ZAJ_SEED)
    zajos = tomb + rng.normal(0, szoras, tomb.shape)
    return Image.fromarray(np.clip(zajos, 0, 255).astype(np.uint8))


def elmosas(img, sugar):
    """Gauss-elmosás a megadott sugárral (pixel)."""
    return img.convert('RGB').filter(ImageFilter.GaussianBlur(sugar))


def atmeretezes(img, arany):
    """A kép lekicsinyítése (pl. 0.5 = fele akkora), mintha kis felbontásban küldték volna."""
    img = img.convert('RGB')
    uj = (max(1, int(img.width * arany)), max(1, int(img.height * arany)))
    return img.resize(uj, Image.BILINEAR)


# torzítás neve -> (függvény, vizsgált szintek)
PERTURBACIOK = {
    'jpeg': (jpeg, [90, 70, 50, 30]),
    'zaj': (gauss_zaj, [5, 10, 20, 30]),
    'elmosas': (elmosas, [0.5, 1.0, 1.5, 2.0]),
    'atmeretezes': (atmeretezes, [0.9, 0.75, 0.5, 0.35]),
}
