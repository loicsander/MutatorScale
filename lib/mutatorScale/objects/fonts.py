#coding=utf-8
from __future__ import division

from mutatorScale.objects.glyphs import MathGlyph
from mutatorScale.utilities.fontUtils import makeListFontName, getRefStems, getSlantAngle

from fontTools.pens.boundsPen import BoundsPen

class ScaleFont(object):
    """
    A ScaleFont takes a font object (Robofab or Defcon) and a scale setting,
    it is then ready to return any number of scaled glyphs.

    Usage:
        smallFont = ScaleFont(font, 0.5)
        small_Glyph_A = smallFont.getGlyph('A')
    Or:
        smallFont = ScaleFont(font)
        smallFont.setScale((1.05, 490, 'capHeight'))
    """
    def __init__(self, font, scale=None):
        self.glyphs = font
        self.scale = scale
        self.heights = { heightName:getattr(font.info, heightName) for heightName in ['capHeight','ascender','xHeight','descender'] }
        self.name = makeListFontName(font)
        self.italicAngle = -getSlantAngle(font, True)

        if scale is not None:
            self.setScale(scale)

    def __repr__(self):
        return '<{className} {fontName}>'.format(className = self.__class__.__name__, fontName = self.name)

    def __getitem__(self, key):
        return self.getGlyph(key)

    def __contains__(self, glyphName):
        return glyphName in self.glyphs

    def keys(self):
        return self.glyphs.keys()

    def get_notEmpty_glyphs_names(self):
        glyphs = self.glyphs
        glyphNames = [glyph.name for glyph in glyphs if (not glyph.isEmpty() and not 'space' in glyph.name)]
        return glyphNames

    def getXScale(self):
        if self.scale is not None:
            return self.scale[0]
        return

    def getYScale(self):
        if self.scale is not None:
            return self.scale[1]
        return

    def getScale(self):
        return self.scale

    def setScale(self, scale):
        """ Setting scale for the font.

        – Either a simple (x, y) scale tuple;
        – or a tuple in the form (width, targetHeight, referenceHeight).
            – x, y, width should be floats;
            – targetHeight should be an int or float;
            – referenceHeight can be either a string or float/int.
        """
        if len(scale) == 2:
            self.scale = scale

        elif len(scale) == 3:
            x, targetHeight, referenceHeight = scale

            try:
                xy = targetHeight / referenceHeight

            except:

                # try parsing referenceHeight to a numeric value
                if referenceHeight in self.heights:
                    referenceHeightValue = self.heights[referenceHeight]
                elif referenceHeight in self.glyphs:
                    referenceHeightValue = self._getGlyphHeight(referenceHeight)
                    if referenceHeightValue is None:
                        referenceHeightValue = 1
                else:
                    referenceHeightValue = referenceHeight

                # try parsing targetHeight to a numeric value
                if targetHeight in self.heights:
                    targetHeightValue = self.heights[targetHeight]
                elif targetHeight in self.glyphs:
                    targetHeightValue = self._getGlyphHeight(targetHeight)
                    if targetHeightValue is None:
                        targetHeightValue = referenceHeightValue
                else:
                    targetHeightValue = targetHeight

                try:
                    xy = targetHeightValue / referenceHeightValue
                except:
                    xy = 1

            finally:
                self.scale = (x * xy, xy)


    def _getGlyphHeight(self, glyphName):
        glyph = self.glyphs[glyphName]
        if not glyph.isEmpty():
            pen = BoundsPens(self.glyphs)
            glyph.draw(pen)
            return pen.bounds
        return

    def getGlyph(self, glyphName):
        """Return a scaled glyph as a MathGlyph instance."""
        if glyphName in self.glyphs:
            glyph = self.glyphs[glyphName]
            scale = self.scale
            scaledGlyph = self._scaleGlyph(glyph, scale)
            return scaledGlyph
        else:
            return KeyError

    def extractGlyph(self, glyphName, glyph):
        scaledGlyph = self.getGlyph(glyphName)
        pen = glyph.getPen()
        scaledGlyph.draw(pen)

    def _scaleGlyph(self, glyph, scale):
        """
        Return a glyph scaled according to the font’s scale settings,
        if glyph has components, reset scaling on each component but keep scaled offset coordinates.
        """
        glyph = MathGlyph(glyph)
        italicAngle = self.italicAngle
        # Skew to an upright position to prevent the slant angle from changing because of scaling
        if italicAngle:
            glyph.skewX(italicAngle)

        # Do the scaling
        glyph *= scale
        # Cancel scaling effect on components
        for i, component in enumerate(glyph.components):
            baseGlyph, matrix = component
            xx, yx, xy, yy, x, y = matrix
            xx, yx, xy, yy = 1, 0, 0, 1
            glyph.components[i] = (baseGlyph, (xx, yx, xy, yy, x, y))
        # Reverting to initial slant angle
        if italicAngle:
            glyph.skewX(-italicAngle)

        return glyph

class MutatorScaleFont(ScaleFont):
    """ Subclass extending a ScaleFont and adding reference stem values to be used inside a MutatorScaleEngine."""

    def __init__(self, font, scale=(1, 1), stems=None, stemsWithSlantedSection=False):
        super(MutatorScaleFont, self).__init__(font, scale)
        self.stemsWithSlantedSection = stemsWithSlantedSection
        self.processDimensions(font, stems)

    def __repr__(self):
        return '<{className} {fontName}>'.format(className=self.__class__.__name__, fontName=self.name)

    def processDimensions(self, font, stems=None):
        refVstem, refHstem = getRefStems(font, self.stemsWithSlantedSection)
        if stems is None:
            self._refVstem, self._refHstem = refVstem, refHstem
        else:
            vstem, hstem = stems
            self._refVstem = vstem if vstem is not None else refVstem
            self._refHstem = hstem if hstem is not None else refHstem

    def getStems(self):
        return self.vstem, self.hstem

    def setStems(self, stems):
        vstem, hstem = stems
        self.vstem = vstem
        self.hstem = hstem

    @property
    def vstem(self):
        return self._refVstem
    @vstem.setter
    def vstem(self, stem):
        self._refVstem = stem

    @property
    def hstem(self):
        return self._refHstem
    @hstem.setter
    def hstem(self, stem):
        self._refHstem = stem

if __name__ == '__main__':

    import unittest
    import os
    from defcon import Font

    class ScaleFontsTest(unittest.TestCase):

        def setUp(self):
            libFolder = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
            singleFontPath = u'testFonts/two-axes/regular-low-contrast.ufo'
            fontPath = os.path.join(libFolder, singleFontPath)
            font = Font(fontPath)
            self.smallFont = ScaleFont(font, (0.5, 0.4))
            self.stemedSmallFont = MutatorScaleFont(font, (0.5, 0.4))
            self.stemedSmallFont = MutatorScaleFont(font, (0.5, 0.4), stemsWithSlantedSection=True)

        def test_setScale_with_values(self):
            """Test changing scale with x, y values."""
            for testFont in [self.smallFont, self.stemedSmallFont]:
                testFont.setScale((0.85, 0.79))

        def test_setScale_with_references(self):
            """Test changing scale with width, targetHeight, referenceHeight arguments."""
            for testFont in [self.smallFont, self.stemedSmallFont]:
                testFont.setScale((1.02, 450, 'capHeight'))
                testFont.setScale((0.65, 350, 250))

        def test_get_scaled_glyph_as_MathGlyph(self):
            """Test scaled glyph retrieval."""
            for testFont in [self.smallFont, self.stemedSmallFont]:
                for glyphName in ['H', 'Aacute']:
                    scaledGlyph = testFont.getGlyph(glyphName)
                    self.assertIsInstance(scaledGlyph, MathGlyph)
                    scaledGlyph = testFont[glyphName]
                    self.assertIsInstance(scaledGlyph, MathGlyph)

        def test_extract_scaled_glyph_as_Defcon_Glyph(self):
            """Test scaled glyph retrieval as a Defcon glyph."""
            from defcon import Glyph
            for testFont in [self.smallFont, self.stemedSmallFont]:
                scaledGlyph = Glyph()
                for glyphName in ['H', 'Aacute']:
                    testFont.extractGlyph(glyphName, scaledGlyph)
                    self.assertIsInstance(scaledGlyph, Glyph)

        def test_extract_scaled_glyph_as_Robofab_Glyph(self):
            """Test scaled glyph retrieval as a Robofab Glyph."""
            from robofab.world import RGlyph
            for testFont in [self.smallFont, self.stemedSmallFont]:
                scaledGlyph = RGlyph()
                for glyphName in ['H', 'Aacute']:
                    testFont.extractGlyph(glyphName, scaledGlyph)
                    self.assertIsInstance(scaledGlyph, RGlyph)

        def test_set_stems(self):
            """Test setting stems on a MutatorScaleFont."""
            self.stemedSmallFont.setStems((100, 40))

        def test_set_stems_separately(self):
            """Test setting stems separately on a MutatorScaleFont."""
            self.stemedSmallFont.vstem = 120
            self.stemedSmallFont.hstem = 50


    unittest.main()