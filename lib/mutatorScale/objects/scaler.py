#coding=utf-8
from __future__ import division

from robofab.world import RGlyph
from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator

import sys
sys.path.insert(0, u'/Users/loicsander/Documents/100 CodeLibs/MutatorScale/lib')
import mutatorScale

from mutatorScale.objects.fonts import MutatorScaleFont
from mutatorScale.objects.glyphs import errorGlyph
from mutatorScale.utilities.fontUtils import makeListFontName
from mutatorScale.utilities.numbersUtils import mapValue

class MutatorScaleEngine:
    """
    This object is built to handle the interpolated scaling of glyphs using MutatorMath.
    It requires a list of fonts (at least two) from which it determines which kind of interpolation it can achieve.
    Maybe I should state the obvious: the whole process is based on the assumption that the provided fonts are compatible for interpolation.
    With existing masters, the object is then set to certain parameters that allow for specific glyph scaling operations,
    while scaling, a MutatorScaleEngine attempts to obtain specified weight and contrast for the scaled glyph
    by interpolating accordingly and to the best possible result with available masters.

    Each master in a MutatorScaleEngine is an instance of a MutatorScaleFont for which stem values are defined.
    If not specifically provided, these stem values are measured on capital letters I and H for vertical and horizontal stems respectively.
    The stem values obtained are only meant to be reference value and do not reflect the stem values of all glyphs but only of I and H.
    While scaling, if you ask for a scaled glyph with stem values (80, 60), you’re effectively asking for a scaledGlyph interpolated
    as to have the vertical stem of a I equal to 80 and the horizontal stem of a H equal to 60. It is not akin to ask that these stem values
    are applied to the exact glyph you asked for, that’s not how interpolation works.

    When a MutatorScaleEngine is asked for a scaled glyph with specific horizontal and vertical stem values,
    here’s what happens:
    – it collects glyphs corresponding to the glyphName passed to .getScaledGlyph() in the available masters;
    – it scales all the master glyphs to the proportions to which the MutatorScaleEngine is set;
    – it then builds a MutatorMath space in which masters are placed according to their horizontal and vertical stem values scaled down;
    – finally, it returns a scaled down (as all masters are) interpolated glyph with the asked for stem values.

    #####

    Here’s how it goes:

    >>> scaler = MutatorScaleEngine(ListOfFonts)
    >>> scaler.set({
        'scale': (1.03, 0.85)
        })
    >>> scaler.getScaledGlyph('a', ())
    """

    errorGlyph = errorGlyph()

    def __init__(self, masterFonts=[], stemsWithSlantedSection=False):
        self.masters = {}
        self._currentScale = None
        self._canUseTwoAxes = False
        self.stemsWithSlantedSection = stemsWithSlantedSection
        self._availableGlyphs = []
        for font in masterFonts:
            self.addMaster(font)
        self.mutatorErrors = []

    def __repr__(self):
        return 'MutatorScaleEngine # {0} masters\n- {1}\n'.format(len(self.masters), '\n- '.join([str(master) for master in self.masters]))

    def __getitem__(self, key):
        if key in self.masters.keys():
            return self.masters[key]
        else:
            raise KeyError(key)

    def __iter__(self):
        for master in self.masters.values():
            yield master

    def __len__(self):
        return len(self.masters)

    def __contains__(self, fontName):
        return fontName in self.masters

    def hasGlyph(self, glyphName):
        return glyphName in self._availableGlyphs

    def getReferenceGlyphs(self):
        masters = self.masters.values()
        glyphs = reduce(lambda a, b: list(set(a) & set(b)), [master.get_notEmpty_glyphs_names() for master in masters])
        return glyphs

    def set(self, scalingParameters):
        """Define scaling parameters.

        Collect relevant data in the various forms it can be input,
        produce a scale definition relevant to a ScaleFont object.
        """
        scale = (1, 1)

        if scalingParameters.has_key('width'):
            width = scalingParameters['width']
            scale = (width, 1)
        else:
            width = 1

        if scalingParameters.has_key('scale'):
            scale = scalingParameters['scale']
            if isinstance(scale, (float, int)):
                scale = (scale, scale)

        elif  scalingParameters.has_key('targetHeight') and scalingParameters.has_key('referenceHeight'):
            targetHeight = scalingParameters['targetHeight']
            referenceHeight = scalingParameters['referenceHeight']
            scale = (width, targetHeight, referenceHeight)

        for master in self.masters.values():
            master.setScale(scale)

        self._currentScale = scale

    def _makeMaster(self, font, stems=None):
        """Return a MutatorScaleFont."""
        name = makeListFontName(font)
        master = MutatorScaleFont(font, stems=stems, stemsWithSlantedSection=self.stemsWithSlantedSection)
        return name, master

    def addMaster(self, font, stems=None):
        """Add a MutatorScaleFont to masters."""
        name, master = self._makeMaster(font, stems)
        if self._currentScale is not None:
            master.setScale(self._currentScale)
        self.masters[name] = master
        self._canUseTwoAxes = self.checkForTwoAxes()
        if not len(self._availableGlyphs):
            self._availableGlyphs = master.keys()
        elif len(self._availableGlyphs):
            self._availableGlyphs = list(set(self._availableGlyphs) & set(master.keys()))

    def removeMaster(self, font):
        """Remove a MutatorScaleFont from masters."""
        name = makeListFontName(font)
        if self.masters.has_key(name):
            self.masters.pop(name, 0)
        self._canUseTwoAxes = self.checkForTwoAxes()

    def getScaledGlyph(self, glyphName, stemTarget, slantCorrection=True):
        """Return an interpolated & scaled glyph according to set parameters and given masters."""
        masters = self.masters.values()
        twoAxes = self._canUseTwoAxes
        mutatorMasters = []
        yScales = []
        angles = []

        """
        Gather master glyphs for interpolation:
        each master glyph is scaled down according to set parameter,
        it is then inserted in a mutator design space with scaled down stem values.
        Asking for the initial stem values of a scaled down glyphName
        will result in an scaled glyph which will retain specified stem widths.
        """

        if len(masters) > 1:

            medianYscale = 1
            medianAngle = 0

            for master in masters:

                xScale, yScale = master.getScale()
                yScales.append(yScale)

                if glyphName in master:
                    masterGlyph = master[glyphName]

                    if twoAxes == True:
                        axis = {
                            'vstem': master.vstem * xScale,
                            'hstem': master.hstem * yScale
                            }
                    else:

                        if slantCorrection == True:
                            # if interpolation is an/isotropic
                            # skew master glyphs to upright angle to minimize deformations
                            angle = master.italicAngle

                            if angle:
                                masterGlyph.skewX(angle)
                                angles.append(angle)

                        axis = {
                            'stem': master.vstem * xScale
                        }

                    mutatorMasters.append((Location(**axis), masterGlyph))

            if len(angles) and slantCorrection == True:
                # calculate a median slant angle
                # in case there are variations among masters
                # shouldn’t happen, most of the time
                medianAngle = sum(angles) / len(angles)

            medianYscale = sum(yScales) / len(yScales)


            targetLocation = self._getTargetLocation(stemTarget, masters, twoAxes, (xScale, medianYscale))
            instanceGlyph = self._getInstanceGlyph(targetLocation, mutatorMasters)

            if instanceGlyph.name == '_error_':
                if self.hasGlyph(glyphName):
                    instanceGlyph.unicodes = masters[0][glyphName].unicodes
                self.mutatorErrors[-1]['glyph'] = glyphName
                self.mutatorErrors[-1]['masters'] = mutatorMasters

            if medianAngle and slantCorrection == True:
                # if masters were skewed to upright position
                # skew instance back to probable slant angle
                instanceGlyph.skew(-medianAngle)

            instanceGlyph.round()

            return instanceGlyph
        return

    def _getInstanceGlyph(self, location, masters):
        I = self._getInstance(location, masters)
        if I is not None:
            return I.extractGlyph(RGlyph())
        else:
            return self.errorGlyph

    def _getInstance(self, location, masters):
        try:
            b, m = buildMutator(masters)
            if m is not None:
                instance = m.makeInstance(location)
                return instance
        except Exception as e:
            self.mutatorErrors.append({'error':e.message})
            return None

    def _getTargetLocation(self, stemTarget, masters, twoAxes, (xScale, yScale)):
        """
        Return a proper Location object for a scaled glyph instance,
        the essential part lies in the conversion of stem values,
        so that in anisotropic mode, a MutatorScaleEngine can attempt to produce
        a glyph with proper stem widths without requiring two-axes interpolation.
        """

        targetVstem, targetHstem = None, None

        try: targetVstem, targetHstem = stemTarget
        except: targetVstem = stemTarget

        if targetHstem is not None:

            if twoAxes == False:
                vStems = [master.vstem * xScale for master in masters]
                hStems = [master.hstem * yScale for master in masters]
                (minVStem, minStemIndex), (maxVStem, maxStemIndex) = self._getExtremes(vStems)
                vStemSpan = (minVStem, maxVStem)
                hStemSpan = hStems[minStemIndex], hStems[maxStemIndex]
                newHstem = mapValue(targetHstem, hStemSpan, vStemSpan)
                return Location(stem=(targetVstem, newHstem))

            elif twoAxes == True:
                return Location(vstem=targetVstem, hstem=targetHstem)

        else:

            return Location(stem=targetVstem)

    def _getExtremes(self, values):
        """
        Return the minimum and maximum in a list of values with indices,
        this implementation was necessary to distinguish indices when min and max value happen to be equal (without being the same value per se).
        """
        if len(values) > 1:
            baseValue = (values[0], 0)
            smallest, largest = baseValue, baseValue
            for i, value in enumerate(values[1:]):
                if value >= largest[0]:
                    largest = (value, (i+1))
                elif value < smallest[0]:
                    smallest = (value, (i+1))
            return smallest, largest
        return

    def checkForTwoAxes(self, masters=None):
        """
        Check conditions are met for two-axis interpolation in MutatorMath:
        1. At least two identical values (to bind a new axis to the first axis)
        2. At least one value different from the others (to be able to have a differential on second axis)
        """
        if masters is None:
            masters = self.masters.values()

        if len(masters) > 2:
            values = [master.hstem for master in masters]

            length = len(values)
            if length:
                identicalValues = 0
                differentValues = 0
                for i, value in enumerate(values):
                    if i < length-1:
                        nextValue = values[i+1]
                        if nextValue == value: identicalValues += 1
                        if nextValue != value: differentValues += 1
                return bool(identicalValues) and bool(differentValues)
        return False

    def getMutatorReport(self):
        return self.mutatorErrors


if __name__ == '__main__':

    import os
    import unittest
    import glob
    from defcon import Font

    class MutatorScaleEngineTest(unittest.TestCase):

        def setUp(self):
            libFolder = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
            libFolder = os.path.join(libFolder, 'testFonts/')
            self.scalers = []
            self.loadedFonts = []
            self.glyphNames = ['H','I']
            for fontsFolder in ['two-axes','isotropic-anisotropic']:
                fonts = []
                fontsPath = os.path.join(libFolder, fontsFolder)
                os.chdir(fontsPath)
                for singleFontPath in glob.glob('*.ufo'):
                    font = Font(singleFontPath)
                    if 'Italic' not in font.info.styleName:
                        fonts.append(font)
                        self.loadedFonts.append(font)
                scaler = MutatorScaleEngine(fonts)
                self.scalers.append(scaler)

        def test_if_scalingEngine_has_glyph(self):
            """Checking if glyph is present among all scaling masters."""
            for scaler in self.scalers:
                for glyphName in self.glyphNames:
                    hasGlyph = scaler.hasGlyph(glyphName)
                    self.assertTrue(hasGlyph)

        def test_get_list_of_non_empty_glyph(self):
            """Checking if glyph is present among all scaling masters."""
            for scaler in self.scalers:


        def test_setting_up_simple_scale(self):
            """Test setting up simple scale on a MutatorScaleEngine."""
            for scaler in self.scalers:
                scaler.set({'scale':(0.5, 0.4)})
                for glyphName in self.glyphNames:
                    scaler.getScaledGlyph(glyphName, (100, 40))

        def test_setting_up_width(self):
            """Test setting up width scaling on a MutatorScaleEngine."""
            for scaler in self.scalers:
                scaler.set({'width':0.75})
                for glyphName in self.glyphNames:
                    scaler.getScaledGlyph(glyphName, (100, 40))

        def test_setting_up_scale_by_reference(self):
            """Test setting up scale on a MutatorScaleEngine."""
            for scaler in self.scalers:
                scaler.set({
                    'targetHeight': 490,
                    'referenceHeight': 'capHeight'
                    })
                for glyphName in self.glyphNames:
                    scaler.getScaledGlyph(glyphName, (100, 40))

        def test_adding_master(self):
            libFolder = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
            libFolder = os.path.join(libFolder, 'testFonts/')
            newFontPath = os.path.join(libFolder, 'isotropic-anisotropic/bold-mid-contrast.ufo')
            newFont = Font(newFontPath)
            scaler = self.scalers[0]
            scaler.addMaster(newFont)
            self.assertEqual(len(scaler), 5)

        def test_removing_master(self):
            scaler = self.scalers[0]
            fontToRemove = self.loadedFonts[0]
            scaler.removeMaster(fontToRemove)
            self.assertEqual(len(scaler), 3)

    unittest.main()