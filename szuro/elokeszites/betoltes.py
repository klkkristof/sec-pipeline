# --- 1/a. Kép betöltése ---

from PIL import Image


def load_image(image_path):
    """
    Kép betöltése. Ha van alfa csatorna (átlátszóság), akkor fehér ÉS fekete
    háttérre is ráhelyezzük, mert az átlátszó rétegben elrejtett szöveg
    csak az egyiken látszik.
    Visszatérés: (képek listája, alfa csatorna vagy None)
    """
    img = Image.open(image_path)
    img.load()  # itt derül ki, ha sérült vagy túl nagy a kép

    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGBA')
        hatterek = []
        for szin in ('white', 'black'):
            hatter = Image.new('RGBA', img.size, szin)
            hatter.alpha_composite(img)
            hatterek.append(hatter.convert('RGB'))
        # Az alfa csatornát külön is megnézzük, mert abba is lehet szöveget "rajzolni"
        alfa = img.getchannel('A').convert('RGB')
        return hatterek, alfa

    return [img.convert('RGB')], None
