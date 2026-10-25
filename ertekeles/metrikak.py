# --- METRIKÁK ---
# Pozitív = támadó kép (cimke 1), "pozitív döntés" = a szűrő blokkolta.
#   TP: támadás, blokkolva          (jó)
#   FN: támadás, átengedve          (rossz - a támadás átjutott)
#   FP: ártalmatlan, blokkolva      (rossz - téves riasztás)
#   TN: ártalmatlan, átengedve      (jó)


def confusion_matrix(valodi, josolt):
    """
    valodi: címkék listája (1 = támadó, 0 = ártalmatlan)
    josolt: döntések listája (1 = blokkolva, 0 = átengedve)
    Visszatérés: (tp, fp, tn, fn)
    """
    tp = fp = tn = fn = 0
    for v, j in zip(valodi, josolt):
        if v == 1 and j == 1:
            tp += 1
        elif v == 0 and j == 1:
            fp += 1
        elif v == 0 and j == 0:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def osztas(a, b):
    """Nullával osztás helyett 0-t ad vissza."""
    return a / b if b else 0.0


def metrics(tp, fp, tn, fn):
    """A szokásos mérőszámok a konfúziós mátrixból."""
    precision = osztas(tp, tp + fp)   # a blokkolt képek hány %-a volt tényleg támadás
    recall = osztas(tp, tp + fn)      # a támadások hány %-át fogtuk meg (detektálási arány)
    return {
        'pontossag': osztas(tp + tn, tp + fp + tn + fn),  # accuracy
        'precision': precision,
        'recall': recall,
        'f1': osztas(2 * precision * recall, precision + recall),
        'fp_arany': osztas(fp, fp + tn),  # téves riasztási arány (FPR)
        'fn_arany': osztas(fn, fn + tp),  # átengedett támadások aránya (FNR)
    }
