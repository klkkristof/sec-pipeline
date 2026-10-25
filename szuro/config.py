# --- BEÁLLÍTÁSOK ---
# Minden állítható érték itt van egy helyen, hogy ne kelljen a kódban keresgélni.

import os
import warnings
from PIL import Image
import pytesseract

# A projekt gyökérmappája (ahol a README.md is van)
PROJEKT_MAPPA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A tiltott kifejezések listája külön szövegfájlban van, kód nélkül szerkeszthető
FEKETELISTA_FAJL = os.path.join(PROJEKT_MAPPA, 'adatok', 'feketelista.txt')
# Gyenge kifejezések: ártalmatlan szövegben is előfordulnak, ezért csak részpontot érnek
GYENGE_KIFEJEZESEK_FAJL = os.path.join(PROJEKT_MAPPA, 'adatok', 'gyenge_kifejezesek.txt')

# Windows alatt meg kell adni a Tesseract útvonalát, Linuxon/macOS-en a PATH-ból megtalálja
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = os.environ.get(
        'TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    )

# OCR nyelvek (a magyarhoz kell a 'hun' nyelvi csomag is!)
OCR_NYELVEK = 'eng+hun'

# Decompression bomb elleni védelem: túl nagy képet nem nyitunk meg
Image.MAX_IMAGE_PIXELS = 40_000_000  # kb. 40 megapixel
warnings.simplefilter('error', Image.DecompressionBombWarning)  # a figyelmeztetésből hiba lesz

# Döntési szintek a pontszám alapján:
#   0 .. KARANTEN_KUSZOB-1          -> ENGEDÉLYEZVE
#   KARANTEN_KUSZOB .. BLOKKOLASI-1 -> KARANTÉN (mehet a modellhez, de korlátozott módban)
#   BLOKKOLASI_KUSZOB felett        -> BLOKKOLVA
KARANTEN_KUSZOB = 30
BLOKKOLASI_KUSZOB = 50

# Pontszámok az egyes jelzésekhez (detektalas/pontozas.py használja)
PONT_PONTOS_EGYEZES = 100
PONT_GYENGE_EGYEZES = 40   # gyenge kifejezés (pl. "bypass"): egyedül csak karantén, kettő már blokk
PONT_FUZZY_EGYEZES = 60
PONT_REJTETT_SZOVEG = 30
PONT_SPECIALIS_KARAKTER = 20

# Küszöbök
FUZZY_KUSZOB = 0.85             # 0-1 közötti hasonlóság (difflib)
SPECIALIS_ARANY_KUSZOB = 0.3    # 30% fölött gyanús
REJTETT_SZAVAK_MIN = 3          # ennyi "új" szó kell a rejtett szöveg jelzéshez

# Ha True, a piros/zöld/kék csatornát is külön megvizsgáljuk (lassabb, de alaposabb)
CSATORNANKENTI_VIZSGALAT = True

# --- Downscale-aliasing elleni védelem ---
# A multimodális modellek a képet bemenet előtt lekicsinyítik. Egy erre tervezett kép
# teljes méretben ártalmatlan, kicsinyítés után viszont előjön rajta egy rejtett szöveg.
# Ezért a képet mi is lekicsinyítjük a tipikus modellbemeneti méretekre, és azt is OCR-ezzük.
LEKICSINYITES_VIZSGALAT = True
CELMERETEK = [224, 384, 512, 768]   # a kép hosszabbik oldala kicsinyítés után (pixel)
RESAMPLING_MODSZEREK = ['nearest', 'bilinear', 'bicubic']

# --- Sandbox (sandbox.py) ---
MAX_FAJLMERET_MB = 20        # ennél nagyobb fájlt meg se nyitunk
OCR_IDOKORLAT_MP = 60        # ha egy kép feldolgozása tovább tart, leállítjuk
MEMORIA_KORLAT_MB = 2048     # a feldolgozó folyamat memóriakorlátja (csak Linux/macOS)
