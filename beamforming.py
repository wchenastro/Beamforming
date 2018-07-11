import numpy as np
import datetime

import katpoint
import coordinate as coord
from interferometer import InterferometryObservation
from tile import ellipseCompact, ellipseGrid
from plot import plotPackedBeam, plotBeamContour, plot_beam_shape, plot_interferometry, plot_overlap
from beamshape import calculateBeamOverlaps
from utilities import normInverse


class psfsim(object):
    """
    Class for simulation of beam shape.

    arguments:
    antenna -- a list of antenna coordinates whose element is
        in the order of latitude(deg), longitude(deg), altitude(meter)
    frequencies -- the central frequency of the observation in Hz

    """

    arrayRefereceGEODET = (-30.71106, 21.44389, 1035)
    '''speed Of Light'''
    sol = 299792458
    # self.waveLengths = sol/frequencies

    def __init__(self, antennas, frequencies):
        """
        constructor of the psfsim class.

        """

        self.pixels = 400
        self.boreSight = (21.44389, -30.71106)
        self.observation = None
        self.antennas = []

        waveLengths = float(self.sol)/np.array(frequencies)
        if waveLengths.shape == (1,): waveLengths = waveLengths[0]

        observation = InterferometryObservation(self.arrayRefereceGEODET,
                            None, waveLengths)
        observation.setBoreSight(self.boreSight)
        observation.setBeamSizeFactor(1)
        observation.setBeamNumber(self.pixels)
        observation.setInterpolating(True)
        observation.setAutoZoom(True)
        observation.setInputType(InterferometryObservation.equatorialInput)


        self.observation = observation
        self.antennas = self.checkAntenna(antennas)

    def setBeamPixelNum(self, num):
        """
        set the number of pixels of the image, default is 400,
        that will generate a image with a dimension of 20x20

        arguments:
        num -- the number of pixels of the image

        """

        self.observation.setBeamNumber(num)

    def checkAntenna(self, antennas):
        """
        check the type of the inputs. if they are katpoint objects,
        then extract the latitude, longitude, elevation information

        arguments:
        antennas -- either can be a list of katpoint antenna objects or
                    a list of [latitude, longitude, elevation]


        return:
        a list of antenna geographic coordinates in the order of
        [latitude, longitude, elevation]

        """

        antennas = np.array(antennas)
        if isinstance(antennas[0], np.ndarray):
            return antennas
        elif isinstance(antennas[0], katpoint.Antenna):
            antennaList = []
            for antenna in antennas:
                antennaList.append([np.rad2deg(antenna.observer.lat),
                                    np.rad2deg(antenna.observer.lon),
                                    antenna.observer.elev])

            return np.array(antennaList)

    def checkSource(self, source):
        """
        check the type of the inputs. if it is a katpoint object,
        then extract the RA, DEC information

        arguments:
        source -- either can be a katpoint target object or [RA, DEC]


        return:
        a coordinate as [RA, DEC]

        """

        source = np.array(source)
        if isinstance(source, np.ndarray):
            return source
        elif isinstance(source, katpoint.Target):
            ra = source.body._ra
            dec = source.body._dec

            return np.rad2deg([ra, dec])

    def getBeamShape(self, source, time):
        """
        return the beamshape of current oservation parameters
        assuming the beam is roughly a ellipse.

        arguments:
        source -- the boresight location or telescope pointing
            in the order of RA(deg), DEC(deg)
        time -- the observation time in datatime object or epoch seconds


        return:
        a beamshape object contain properties of semi-major axis,
            semi-mino axis and orientation all in degree
        """

        self.observation.setBoreSight(self.checkSource(source))
        self.observation.setObserveTime(time)

        self.observation.createContour(self.antennas)
        axisH, axisV, angle = self.observation.getBeamAxis()
        beamShapeObj = beamShape(axisH, axisV, angle)
        beamShapeObj.setHorizon(np.rad2deg(self.observation.getHorizontal()))
        beamShapeObj.setAntennas(self.antennas, self.arrayRefereceGEODET)
        beamShapeObj.setPointSourceFunction(
                self.observation.getPointSourceFunction())

        return beamShapeObj


class beamShape(object):
    """
    Class of  the beamShape object contain properties of the beamshape

    arguments:
    axisH -- length of the semi-major axis in degree
    axisV -- length of the semi-minor axis in degree
    angle -- orientation of the angle in degree

    """


    def __init__(self, axisH, axisV, angle):
        """
        constructor of the beamShape class.

        """
        self.axisH = axisH
        self.axisV = axisV
        self.angle = angle

    def setHorizon(self, horizon):
        self.horizon = horizon

    def setPointSourceFunction(self, psf):
        self.psf = psf

    def setAntennas(self, antennas, reference=None):
        self.antennas = antennas
        self.reference = reference

    def widthAtOverlap(self, overlap):
        """
        return the half widths of the ellipse in major axis and
        minor axis direction given a overlap level.

        the relationship between one sigma and the full width maximal can be
        found in this link

        https://en.wikipedia.org/wiki/Full_width_at_half_maximum
        2.*np.sqrt(2.*np.log(2)) = 2.3548200450309493
        """
        sigmaH = self.axisH * (2./2.3548200450309493)
        sigmaV = self.axisV * (2./2.3548200450309493)

        widthH = normInverse(overlap, 0, sigmaH)
        widthV = normInverse(overlap, 0, sigmaV)

        return widthH, widthV

    def plotPSF(self, fileName, shapeOverlay = False):
        """
        plot the point source function

        arguments:
        fileName --  name and directory of the plot
        shapeOverlay -- whether to add the shape overlay on the psf

        """

        if shapeOverlay == False:
            plotBeamContour(self.psf.image, self.psf.bore_sight, self.psf.width,
                    fileName, interpolation = True)
        else:
            imageWidth = self.psf.image.shape[0]
            step=self.psf.width*1.0/imageWidth
            ellipseCenter = [self.psf.bore_sight[0] + step/2.,
                             self.psf.bore_sight[1] - step/2.]

            plot_beam_shape(self.psf.image, self.psf.bore_sight, self.psf.width,
                ellipseCenter, self.axisH, self.axisV, self.angle, fileName,
                interpolation = True)


    def plot_interferometry(self, fileName):
        """
        plot the interferometry overview, including the antennas, the source

        arguments:
        fileName --  name and directory of the plot

        """

        plot_interferometry(self.antennas, self.reference, self.horizon, fileName)

class Overlap(object):
    """
    """
    def __init__(self, metrics, mode):
        self.metrics  = metrics
        self.mode = mode


    def plot(self, fileName):
        plot_overlap(self.metrics, self.mode, fileName)

    def calculateFractions(self):

        if self.mode == "heater":
            return (0, 0, 0)

        overlapCounter = self.metrics
        overlapGrid = np.count_nonzero(overlapCounter > 1)
        nonOverlapGrid = np.count_nonzero(overlapCounter == 1)
        emptyGrid = np.count_nonzero(overlapCounter == 0)
        pointNum = overlapGrid+nonOverlapGrid+emptyGrid
        normalizedCounts = np.array([overlapGrid, nonOverlapGrid,
                emptyGrid])/float(pointNum)

        return normalizedCounts


class tiling(object):
    """
    Class of tiling object contain a tiling result

    arguments:
    coordinates -- tiling coordinates as a list of [RA, DEC] in degree
    beamShape -- beamShape object
    raidus -- the raidus of the entire tiling
    overlap -- how much overlap between two beams, range in (0, 1)

    """


    def __init__(self, coordinates, beamShape, radius, overlap):
        """
        constructor of the tiling class.

        """

        self.coordinates = coordinates
        self.beamShape = beamShape
        self.tilingRadius = radius
        self.beamNum = len(coordinates)
        self.overlap = overlap

    def plotTiling(self, fileName):
        """
        plot the tiling pattern with specified file name.

        arguments:
        filename --  filename of the plot, the format and directory can be
        specified in the file name such as  "plot/pattern.png" or "pattern.pdf"

        """

        widthH, widthV = beamShape.widthAtOverlap(self.overlap)
        plotPackedBeam(self.coordinates,
                self.beamShape.angle, widthH, widthV,
                self.tilingRadius, fileName=fileName)


    def plotSkyPattern(self, fileName):

        heats = self.calculateOverlap("heater", newBeamShape = None)
        plot_overlap(heats.metrics, "heater", fileName)

    def calculateOverlap(self, mode, newBeamShape = None):
        """
        calculate overlap of the tiling pattern.

        arguments:
        mode -- mode of the calculation,
                "heater" will calculate the tiling pattern as sky temperature,
                "counter" will calculate the counts of the overlap regions,
                          non-overlap regions and empty regions.
                "both" will calculate both sky temperature and counter
        filename --  filename of the plot, the format and directory can be
                specified in the file name such as  "plot/pattern.png"

        return:
        overlapCounter -- counter when choose "counter" mode
        overlapHeater -- heater when choose "heater" mode
        overlapCounter, overlap heater -- both result will returenwhen choose
                       "both" mode


        """
        if newBeamShape == None:
            beamShape = self.beamShape
        else:
            beamShape = newBeamShape

        overlapCounter = calculateBeamOverlaps(
                self.coordinates, self.tilingRadius,
                beamShape.axisH, beamShape.axisV,
                beamShape.angle, self.overlap, mode)

        overlap = Overlap(overlapCounter, mode)

        return overlap



class tilegen(object):
    """
    Class for generation of tiling

    """


    def __init__(self):
        pass

        """
        constructor of the tilesim class.

        """


    def getTiling(self, beamShape, beamNum, overlap = 0.5):
        """
        generate and return the tiling.

        arguments:
        beamShape -- beamShape object
        beamNum -- number of beams to tile
        overlap -- how much overlap between two beams, range in (0, 1)


        return:
        tiling -- tiling coordinates in a list of [RA, DEC] pairs in degree

        """

        widthH, widthV = beamShape.widthAtOverlap(overlap)

        tilingCoordinates, tilingRadius = ellipseCompact(
                beamNum, widthH, widthV, beamShape.angle, 10)


        tilingObj = tiling(tilingCoordinates, beamShape, tilingRadius, overlap)

        return tilingObj

    def getTilingWithinRadius(self, beamShape, tilingRadius, overlap = 0.5):
        """
        return the tiling inside a specified region

        arguments:
        beamShape -- beamShape object
        tilingRadius -- the radius of the region to tile
        overlap -- how much overlap between two beams, range in (0, 1)

        return:
        tiling -- tiling coordinates in a list of [RA, DEC] pairs in degree

        """

        widthH, widthV = beamShape.widthAtOverlap(overlap)

        tilingCoordinates = ellipseGrid(
                tilingRadius, widthH, widthV, beamShape.angle)

        tilingObj = tiling(tilingCoordinates.T, beamShape, tilingRadius, overlap)

        return tilingObj



class DelayPolynomial(object):

    """
    Class for generation of  delay polynomial

    arguments:
    antennas -- a list of antenna objects or coordinate in csv format
    timestamp -- the observation time in datatime object or epoch seconds
    targets -- a list of beam location in equatorial coordinates
    duration -- the duration in which the polynomial is calcuated
    frequencies -- a list of frequencies on which the polynomail is calculated in Hz
    reference -- the reference antenna for delay calculation

    """


    def __init__(self, antennas, targets,
            timestamp, duration, reference):

        """
        constructor of the Delay Polynomial class.

        """

        self.antennas = antennas
        self.timestamp = self.checkTime(timestamp)
        self.targets = targets
        self.frequency = 1.4e9
        self.reference = reference
        self.duration = duration

    def checkTargets(self, targets):
        """
        check the target data type, the arguments will be converted to katpoint
            object if they are not.

        arguments:
        targets -- a list of target objets in the format of
            katpoint target object or set of [longitude, latitude, altitude]

        return:
            targets in katpoint object

        """

        if isinstance(targets[0], katpoint.Target):
            return targets
        else:
            return makeKapointTarget(targets)


    def setAntennas(self, antennas):
        """
        set the antennas geographical localtion

        arguments:
        antennas -- a list of antenna objects or coordinate in csv format


        """
        self.antennas = antennas

    def setTimestamp(self, timestamp):
        """
        set the timestamp for the observation, it will be as the starting
            point of the duration for the polynomial

        arguments:
        timestamp -- the time in datatime object or epoch seconds


        """

        self.timestamp = self.checkTime(timestamp)

    def setTimeDuration(self, duration):
        """
        set the duration in which the polynomial is calcuated

        arguments:
        duration -- the amount of time in seconds


        """

        self.duration = duration

    def setTargets(self, targets):
        """
        set the beam location in equatorial coordinates

        arguments:
        targets -- a list of beam location in katpoint targets

        """

        self.targets = targets

    def setReference(self, reference):
        """
        set the reference for the delay calculation

        arguments:
        reference -- reference in katpoint antenna object

        """

        self.reference = reference

    def checkTime(self, time):
        """
        check the the data type of the time value. If the values are datetime
            objects, they will be converted to seconds

        arguments:
        time -- epoch seconds or datetime objects

        return:
        time in epoch seconds

        """

        if type(time) != int and type(time) != float:
            return coord.datetimeToEpoch(time)
        else:
            return time

    def dictToOrderList(self, dictObj):
        orderList = []
        for key in sorted(dictObj.iterkeys()):
            orderList.append(dictObj[key])

        return orderList

    @staticmethod
    def makeKapointTarget(sources):
        targets = []
        for source in sources:
            targetString = ",".join(['radec',
                            coord.angleToHour(source[0]),
                            coord.angleToDEC(source[1])])
            targets.append(katpoint.Target(targetString))

        return targets

    @staticmethod
    def makeAntenna(antennaString):
        antennaKat = []

        for antenna in antennaString:
            antkat = katpoint.Antenna(antenna)
            antennaKat.append(antkat)

        return antennaKat



    def getPolynomial(self):

        """
        calculate and return the polynomials


        return:
        polynomials in the order of beam, antenna, (delay, rate)

        """

        antennaObjectList = self.antennas
        targets = self.targets
        ref = self.reference
        timestamp = (self.timestamp, self.timestamp + self.duration)
        freq = self.frequency

        targetArray = []
        for target in targets:
            dc = katpoint.DelayCorrection(antennaObjectList , ref, freq)
            delay, phase = dc.corrections(target, timestamp)
            # phaseArray = np.array(self.dictToOrderList(phase))
            delayArray = np.array(self.dictToOrderList(delay))
            """
            [::2]: only take the one polarization
            [:, 0, :]: only take first rate output
            """
            targetArray.append(delayArray[::2][:,0,:])
        targetArray = np.array(targetArray)
        """
        subtract the boresight beam form the offset beams
        """
        targetArray = targetArray - targetArray[0, :, :]


        # beam, antenna, (delay, rate)

        return targetArray
