# --- GRAFIKONOK A DOLGOZATHOZ ---
# matplotlib kell hozzá (pip install matplotlib). Minden grafikon PNG-be kerül.

import matplotlib
matplotlib.use('Agg')  # ablak nélküli mód, csak fájlba rajzolunk
import matplotlib.pyplot as plt

SZIN_TAMADO = '#c0392b'
SZIN_ARTALMATLAN = '#2e86c1'


def confusion_matrix_plot(tp, fp, tn, fn, fajl):
    """Konfúziós mátrix 2x2-es táblázatként."""
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ertekek = [[tp, fn], [fp, tn]]
    ax.imshow(ertekek, cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(ertekek[i][j]), ha='center', va='center', fontsize=16)
    ax.set_xticks([0, 1], ['Blokkolva', 'Átengedve'])
    ax.set_yticks([0, 1], ['Támadó', 'Ártalmatlan'])
    ax.set_xlabel('A szűrő döntése')
    ax.set_ylabel('Valódi címke')
    ax.set_title('Konfúziós mátrix')
    fig.tight_layout()
    fig.savefig(fajl, dpi=150)
    plt.close(fig)


def tipus_bar(tipusok, fajl):
    """
    Típusonkénti blokkolási és karantén arány (egymásra rakott oszlopok).
    tipusok: lista (név, blokkolási arány, támadó-e, karantén arány)
    """
    fig, ax = plt.subplots(figsize=(9, 4.5))
    nevek = [t[0] for t in tipusok]
    blokk = [t[1] * 100 for t in tipusok]
    karanten = [t[3] * 100 for t in tipusok]
    szinek = [SZIN_TAMADO if t[2] else SZIN_ARTALMATLAN for t in tipusok]
    ax.bar(nevek, blokk, color=szinek, label='Blokkolva')
    ax.bar(nevek, karanten, bottom=blokk, color=szinek, alpha=0.35, hatch='//', label='Karantén')
    for i, (b, k) in enumerate(zip(blokk, karanten)):
        ax.text(i, b + k + 1.5, f'{b:.0f}%' + (f' +{k:.0f}%' if k else ''), ha='center', fontsize=8)
    ax.set_ylabel('Képek aránya (%)')
    ax.set_ylim(0, 115)
    ax.set_title('Döntések képtípusonként (piros: támadó, kék: ártalmatlan; csíkos: karantén)')
    plt.xticks(rotation=35, ha='right')
    fig.tight_layout()
    fig.savefig(fajl, dpi=150)
    plt.close(fig)


def ablacio_bar(ablacio, fajl):
    """
    Ablációs vizsgálat: mennyit ront, ha egy-egy modult kikapcsolunk.
    ablacio: lista (beállítás neve, recall, fp_arany)
    """
    fig, ax = plt.subplots(figsize=(9, 4.5))
    nevek = [a[0] for a in ablacio]
    x = range(len(nevek))
    ax.bar([i - 0.2 for i in x], [a[1] * 100 for a in ablacio], width=0.4,
           color=SZIN_TAMADO, label='Detektálási arány (recall)')
    ax.bar([i + 0.2 for i in x], [a[2] * 100 for a in ablacio], width=0.4,
           color=SZIN_ARTALMATLAN, label='Téves riasztás (FP arány)')
    ax.set_xticks(list(x), nevek, rotation=25, ha='right')
    ax.set_ylabel('%')
    ax.set_ylim(0, 105)
    ax.set_title('Abláció: az egyes modulok hozzájárulása')
    ax.legend()
    fig.tight_layout()
    fig.savefig(fajl, dpi=150)
    plt.close(fig)


def robusztussag_plot(robusztussag, fajl):
    """
    Detektálási arány a torzítás erősségének függvényében, torzításonként egy kis ábra.
    robusztussag: {torzítás neve: [(szint, recall, fp_arany), ...]}
    """
    fig, axok = plt.subplots(1, len(robusztussag), figsize=(4 * len(robusztussag), 3.8))
    for ax, (nev, sorok) in zip(axok, robusztussag.items()):
        szintek = [str(s[0]) for s in sorok]
        ax.plot(szintek, [s[1] * 100 for s in sorok], 'o-', color=SZIN_TAMADO, label='Recall')
        ax.plot(szintek, [s[2] * 100 for s in sorok], 's--', color=SZIN_ARTALMATLAN, label='FP arány')
        ax.set_title(nev)
        ax.set_ylim(-5, 105)
        ax.set_xlabel('szint')
    axok[0].set_ylabel('%')
    axok[0].legend()
    fig.suptitle('Robusztusság különböző torzításokkal (első pont: torzítás nélkül)')
    fig.tight_layout()
    fig.savefig(fajl, dpi=150)
    plt.close(fig)


def futasido_hist(idok, fajl):
    """A képenkénti feldolgozási idő eloszlása."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(idok, bins=20, color='#7f8c8d')
    ax.set_xlabel('Feldolgozási idő képenként (s)')
    ax.set_ylabel('Képek száma')
    ax.set_title('Futásidő eloszlása')
    fig.tight_layout()
    fig.savefig(fajl, dpi=150)
    plt.close(fig)
