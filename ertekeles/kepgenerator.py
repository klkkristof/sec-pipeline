# --- KÉPGENERÁTOR ---
# Támadó és ártalmatlan képek előállítása. Minden támadástípus egy külön függvény.
# A tesztek (tests/tesztkepek.py) és a kiértékelés (adathalmaz.py) is ezt használja.

import random
from PIL import Image, ImageDraw, ImageFont, ImageOps


# --- Segédfüggvények ---

def get_font(meret=28):
    """Megpróbálunk egy rendes betűtípust betölteni, ha nincs, marad az alapértelmezett."""
    for nev in ('arial.ttf', 'DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(nev, meret)
        except OSError:
            continue
    return ImageFont.load_default(size=meret)  # Pillow 10.1+ kell hozzá


def text_box(szoveg, font):
    """A szöveg befoglaló téglalapja: (bal, fent, jobb, lent)."""
    rajz = ImageDraw.Draw(Image.new('L', (1, 1)))
    return rajz.multiline_textbbox((0, 0), szoveg, font=font)


def text_image(szoveg, szin=(0, 0, 0), hatter=(255, 255, 255), betumeret=28, margo=30):
    """
    Egyszerű kép: háttérszínen egy szöveg. A kép mérete a szöveghez igazodik.
    Ebből épül a legtöbb támadás, csak a színek és a szöveg változnak.
    """
    font = get_font(betumeret)
    bal, fent, jobb, lent = text_box(szoveg, font)
    img = Image.new('RGB', (jobb - bal + 2 * margo, lent - fent + 2 * margo), hatter)
    ImageDraw.Draw(img).multiline_text((margo - bal, margo - fent), szoveg, fill=szin, font=font)
    return img


# --- Ártalmatlan kép ---

def artalmatlan(szoveg, betumeret=28):
    """Normál, jól olvasható szöveg fehér háttéren."""
    return text_image(szoveg, betumeret=betumeret)


# --- Támadástípusok ---

def nyilt(szoveg, betumeret=28):
    """Nyílt támadás: a parancs simán, feketével rá van írva a képre."""
    return text_image(szoveg, betumeret=betumeret)


def halvany(szoveg, kulonbseg=1, betumeret=28):
    """
    Rejtett szöveg: fehér háttéren majdnem fehér betűk (pl. 254 a 255-ön).
    Emberi szemmel láthatatlan, de a modell (és az előfeldolgozott OCR) kiolvashatja.
    """
    szurke = 255 - kulonbseg
    return text_image(szoveg, szin=(szurke, szurke, szurke), betumeret=betumeret)


def alacsony_kontraszt(szoveg, hatter=(120, 160, 200), kulonbseg=6, betumeret=28):
    """Kontraszt-alapú támadás: színes háttéren alig eltérő színű szöveg."""
    szin = tuple(max(0, c - kulonbseg) for c in hatter)
    return text_image(szoveg, szin=szin, hatter=hatter, betumeret=betumeret)


def atlatszo_reteg(szoveg, betumeret=28):
    """
    Átlátszó rétegben elrejtett szöveg: a betűk helyén a kép teljesen átlátszó.
    Fehér háttéren nem látszik semmi, fekete háttéren (vagy az alfa csatornában) igen.
    """
    maszk = ImageOps.invert(text_image(szoveg, betumeret=betumeret).convert('L'))
    img = Image.new('RGBA', maszk.size, (255, 255, 255, 255))
    img.putalpha(ImageOps.invert(maszk))  # a betűk helyén alfa = 0
    return img


def tobb_soros(szoveg, betumeret=28):
    """A parancs több sorba van tördelve, hogy a sima szövegkeresés ne találja meg."""
    szavak = szoveg.split()
    fele = len(szavak) // 2
    return text_image(' '.join(szavak[:fele]) + '\n' + ' '.join(szavak[fele:]), betumeret=betumeret)


LEET_CSERE = {'o': '0', 'e': '3', 'i': '1', 'a': '4', 's': '5'}


def leet(szoveg, arany=0.5, rnd=None, betumeret=28):
    """Leet karakterek: néhány betű helyett hasonló szám (ignore -> 1gn0re)."""
    rnd = rnd or random.Random()
    uj = ''.join(LEET_CSERE[c] if c in LEET_CSERE and rnd.random() < arany else c for c in szoveg)
    return text_image(uj, betumeret=betumeret)


# Latin betű -> hasonlóan kinéző cirill betű
HOMOGLIF_CSERE = {'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'x': 'х', 'y': 'у', 'i': 'і'}


def homoglif(szoveg, betumeret=28):
    """
    Homoglif támadás: a latin betűk egy része cirill betűre van cserélve.
    Szövegként ez kijátssza a kulcsszavas keresést, képen viszont ugyanúgy néz ki,
    ezért az OCR jellemzően latin betűként olvassa vissza.
    """
    uj = ''.join(HOMOGLIF_CSERE.get(c, c) for c in szoveg)
    return text_image(uj, betumeret=betumeret)


def kis_betu(lathato_szoveg, rejtett_szoveg, betumeret=28, kis_meret=10):
    """
    Egy ártalmatlan képen, a sarokban apró, szürke betűkkel ott a parancs.
    Ránézésre csak egy "zajos" vonal, a modell viszont elolvashatja.
    """
    img = text_image(lathato_szoveg, betumeret=betumeret, margo=40)
    kis_font = get_font(kis_meret)
    bal, fent, jobb, lent = text_box(rejtett_szoveg, kis_font)
    szelesseg = max(img.width, jobb - bal + 20)
    uj = Image.new('RGB', (szelesseg, img.height + 20), (255, 255, 255))
    uj.paste(img, (0, 0))
    ImageDraw.Draw(uj).text((10 - bal, img.height - 5 - fent), rejtett_szoveg, fill=(170, 170, 170), font=kis_font)
    return uj


def steganografia(lathato_szoveg, rejtett_szoveg, betumeret=28):
    """
    Egyszerű LSB-steganográfia: egy ártalmatlan képen a rejtett szöveg bitjei a piros
    csatorna legalsó bitjeibe vannak írva (soronként, balról jobbra).
    A kép szemmel és OCR-rel is teljesen ártalmatlan, a szöveg csak bitszinten olvasható ki
    (lásd steganografia_kiolvasas). A szűrőnek erre nincs külön modulja, ezért ezzel
    a mérés a rendszer korlátját mutatja meg.
    """
    img = text_image(lathato_szoveg, betumeret=betumeret)
    bitek = []
    for bajt in (rejtett_szoveg + '\0').encode('utf-8'):   # a \0 jelzi az üzenet végét
        bitek.extend((bajt >> i) & 1 for i in range(7, -1, -1))

    if len(bitek) > img.width * img.height:
        raise ValueError("A kép túl kicsi az üzenethez")

    px = img.load()
    for i, bit in enumerate(bitek):
        x, y = i % img.width, i // img.width
        r, g, b = px[x, y]
        px[x, y] = ((r & ~1) | bit, g, b)
    return img


def steganografia_kiolvasas(img):
    """A steganografia() által elrejtett szöveg visszafejtése (teszteléshez)."""
    img = img.convert('RGB')
    px = img.load()
    bajtok = bytearray()
    aktualis = 0
    for i in range(img.width * img.height):
        x, y = i % img.width, i // img.width
        aktualis = (aktualis << 1) | (px[x, y][0] & 1)
        if i % 8 == 7:
            if aktualis == 0:
                break
            bajtok.append(aktualis)
            aktualis = 0
    return bajtok.decode('utf-8', errors='replace')


def nearest_sample_positions(nagy_meret, kis_meret):
    """
    Megnézzük, hogy a Pillow NEAREST kicsinyítése a nagy kép melyik pixeleit választja ki.
    Trükk: egy olyan képet kicsinyítünk, amiben minden pixel értéke a saját sorszáma.
    """
    index = Image.new('I', (nagy_meret, 1))
    for x in range(nagy_meret):
        index.putpixel((x, 0), x)
    kicsi = index.resize((kis_meret, 1), Image.NEAREST)
    return [kicsi.getpixel((x, 0)) for x in range(kis_meret)]


def lekicsinyites(lathato_szoveg, rejtett_szoveg, cel_szelesseg=512, szorzo=4, seed=0):
    """
    Downscale-aliasing támadás (egyszerűsített, NEAREST kicsinyítésre tervezve).
    A nagy kép ránézésre egy zajos háttér egy ártalmatlan felirattal. Ha viszont
    pontosan cel_szelesseg szélességre kicsinyítik (nearest módszerrel), akkor
    CSAK a rejtett szöveg marad meg, mert a kicsinyítés pont azokat a pixeleket
    választja ki, amikbe a rejtett szöveget elrejtettük.
    (A valódi támadások bilinear/bicubic kicsinyítésre is működnek, ott optimalizálással
    számolják ki a pixeleket - ez a dolgozat szempontjából a mechanizmus bemutatására elég.)
    """
    rnd = random.Random(seed)

    # 1. A rejtett szöveg a cél méretben (ezt fogja "látni" a modell)
    meret = 30
    while meret > 10 and text_box(rejtett_szoveg, get_font(meret))[2] > cel_szelesseg - 40:
        meret -= 2  # ha nem fér ki, kisebb betűvel próbáljuk
    font = get_font(meret)
    bal, fent, jobb, lent = text_box(rejtett_szoveg, font)
    cel_magassag = lent - fent + 60
    kicsi = Image.new('L', (cel_szelesseg, cel_magassag), 255)
    ImageDraw.Draw(kicsi).text(((cel_szelesseg - (jobb - bal)) // 2 - bal, 30 - fent),
                               rejtett_szoveg, fill=0, font=font)

    # 2. A nagy kép: világos zajos háttér + nagy, ártalmatlan felirat
    nagy_w, nagy_h = cel_szelesseg * szorzo, cel_magassag * szorzo
    nagy = Image.new('L', (nagy_w, nagy_h))
    nagy.putdata([rnd.randint(110, 255) for _ in range(nagy_w * nagy_h)])
    nagy_font = get_font(int(nagy_h * 0.35))
    b2, f2, j2, l2 = text_box(lathato_szoveg, nagy_font)
    ImageDraw.Draw(nagy).text(((nagy_w - (j2 - b2)) // 2 - b2, (nagy_h - (l2 - f2)) // 2 - f2),
                              lathato_szoveg, fill=60, font=nagy_font)

    # 3. A kicsinyítés által kiválasztott pixelekbe beírjuk a rejtett képet
    xek = nearest_sample_positions(nagy_w, cel_szelesseg)
    yok = nearest_sample_positions(nagy_h, cel_magassag)
    nagy_px = nagy.load()
    kicsi_px = kicsi.load()
    for x in range(cel_szelesseg):
        for y in range(cel_magassag):
            nagy_px[xek[x], yok[y]] = 90 if kicsi_px[x, y] < 128 else 255

    return nagy.convert('RGB')
