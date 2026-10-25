# Unit tesztek a kiértékelés mérőszámaihoz (nem kell hozzá Tesseract)

from ertekeles.metrikak import confusion_matrix, metrics


def test_konfuzios_matrix():
    valodi = [1, 1, 1, 0, 0, 0]
    josolt = [1, 1, 0, 1, 0, 0]
    assert confusion_matrix(valodi, josolt) == (2, 1, 2, 1)  # tp, fp, tn, fn


def test_metrikak():
    m = metrics(tp=8, fp=2, tn=18, fn=2)
    assert m['precision'] == 0.8
    assert m['recall'] == 0.8
    assert abs(m['f1'] - 0.8) < 1e-9
    assert m['fp_arany'] == 0.1
    assert m['fn_arany'] == 0.2
    assert m['pontossag'] == 26 / 30


def test_nullaval_osztas():
    # ha nincs egyetlen pozitív döntés se, ne szálljon el
    m = metrics(tp=0, fp=0, tn=5, fn=0)
    assert m['precision'] == 0.0
    assert m['recall'] == 0.0
