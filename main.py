# --- BELÉPÉSI PONT ---
# Használat (a projekt gyökeréből):
#   python main.py                   -> legenerálja és leellenőrzi a tesztképeket
#   python main.py kep1.png kep2.jpg -> a megadott képeket vizsgálja

import os
import sys

from szuro import analyze_image_security
from tests.tesztkepek import create_test_images

KEP_KITERJESZTESEK = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')


def run_folder(mappa):
    """Egy mappa összes képét leellenőrzi."""
    eredmenyek = []
    for fajl in sorted(os.listdir(mappa)):
        if fajl.lower().endswith(KEP_KITERJESZTESEK):
            dontes, _, _ = analyze_image_security(os.path.join(mappa, fajl))
            eredmenyek.append((fajl, dontes))
    return eredmenyek


def print_summary(eredmenyek):
    print("\n=== ÖSSZESÍTÉS ===")
    for fajl, dontes in eredmenyek:
        print(f"{dontes:<13} {fajl}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Saját képek a parancssorból
        eredmenyek = []
        for kep in sys.argv[1:]:
            dontes, _, _ = analyze_image_security(kep)
            eredmenyek.append((os.path.basename(kep), dontes))
    else:
        # Nincs megadott kép -> tesztképek
        mappa = create_test_images()
        print(f"(Tesztképek létrehozva a '{mappa}' mappában.)")
        eredmenyek = run_folder(mappa)

    print_summary(eredmenyek)
