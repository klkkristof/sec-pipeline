# Végponttól végpontig tesztek a generált tesztképekkel
# EZEKHEZ KELL A TESSERACT! Ha nincs telepítve, a tesztek kimaradnak (skip).
# Futtatás a projekt gyökeréből: pytest tests/

import os
import shutil
import pytest

from szuro import analyze_image_security
from szuro.pipeline import BLOKKOLVA
from tesztkepek import create_test_images, ELVART_EREDMENYEK

nincs_tesseract = shutil.which('tesseract') is None and os.name != 'nt'


@pytest.fixture(scope='module')
def kepek_mappa(tmp_path_factory):
    """A tesztképeket egy ideiglenes mappába generáljuk (egyszer, az összes teszthez)."""
    mappa = tmp_path_factory.mktemp('tesztkepek')
    return create_test_images(str(mappa))


@pytest.mark.skipif(nincs_tesseract, reason="Nincs telepítve a Tesseract")
@pytest.mark.parametrize('fajlnev, elvart', ELVART_EREDMENYEK.items())
def test_tesztkep(kepek_mappa, fajlnev, elvart):
    dontes, okok, _ = analyze_image_security(os.path.join(kepek_mappa, fajlnev), kiir=False)
    assert dontes == elvart, f"{fajlnev}: {okok}"


def test_nem_letezo_fajl_blokkolva():
    # fail-closed: hibánál blokkolunk
    dontes, _, _ = analyze_image_security('nincs_ilyen_kep.png', kiir=False)
    assert dontes == BLOKKOLVA
