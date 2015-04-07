from defcon import Font
import glob

fonts = []

for path in glob.glob('*.ufo'):
    fonts.append(Font(path))

for font in fonts:
    font.newGlyph('B')
    font.save()