#!/usr/bin/env python

import sys
import time
import math
import copy
import inspect
import random
import tools
import universe
import PySide.QtCore as QtCore
import PySide.QtGui as QtGui
from monitor import ConciseMonitor

class GalaxyLayoutThread (QtCore.QThread):
    def __init__ (self, root):
        QtCore.QThread.__init__ (self)
        self.root = root
        self.phases = [
            # These don't change no matter what
            self.task_preamble,
            self.task_computeCoefficients,
            self.task_computeOptimalDistances,
            # These depend on what the central node is
            self.task_cutoffOuterLinks,
            self.task_cutoffCentralLinks,
            
            self.task_makeLinks,
            self.task_tupliseNodeLinks,
            self.task_removeUnattachedNodes,
            self.task_findRangeOfCentralLinks,
            self.task_computeSecondaryNodeIndexList,
            self.task_computeAlphae,
            self.task_computeOptimalDistancesToCenterNode,
            self.task_placeNodes,
            self.task_setupAdjust,
            self.task_setupAdjustAllNodes,
            self.task_adjustAllNodes,
            self.task_noLongerWorking,
            self.task_end]

        self.phase = self.phases [0]
        self.phaseIndex = 0
        self.displayPhaseSignal = dict ()
        self.phasesByName = dict ()
        self.maxIndex = -1
        self.entryByStep = False

        for _index, _phase in enumerate (self.phases):
            self.displayPhaseSignal [_phase.__name__] = QtCore.Signal ()
            QtCore.QObject.connect (self, QtCore.SIGNAL (_phase.__name__ + 'Signal ()'), _phase, QtCore.Qt.QueuedConnection)
            self.phasesByName [_phase.__name__] = _index

        step = QtCore.Signal ()
        QtCore.QObject.connect (self, QtCore.SIGNAL ('step ()'), self.doPhase, QtCore.Qt.QueuedConnection)

        displayReset = QtCore.Signal () # Reset - call when new database is loaded
        QtCore.QObject.connect (self, QtCore.SIGNAL ('displayReset ()'), self.reset, QtCore.Qt.QueuedConnection)

        self.quit = QtCore.Signal ()
        QtCore.QObject.connect (self, QtCore.SIGNAL ('quit ()'), self.doQuit)

        self.START = time.time ()
        self.suspend = True
    def task_preamble (self):
        if not self.enterThisFunction (): return
        self.resource_usage = ConciseMonitor()
        self.root.galaxy.view.links = []
        self.root.galaxy.view.visibleNodeDetails.setNodeList ([self.root.centerNode ()])

        try:
            self.root.nodes [self.root.centerNode ()].hiding = False
        except:
            self.root.setCenterNode (0)
            self.root.nodes [0].hiding = False

        self.nextStep ()
    def showSparse (self, matrix, integer = False):
        result = '['

        for i in matrix:
            result += '{'
            added = False

            for j in i:
                if integer:
                    result += '%d:%4d' % (j, i [j]) + ', '
                else:
                    result += '%d:%.2f' % (j, i [j]) + ', '

                added = True

            if added:
                result = result [:-2]

            result += '}'

        result += ']'

        return result
    def task_computeCoefficients (self):
        if not self.enterThisFunction (): return
        self.computeListOfVisibleNodes ()
        
        self.maxCoefficient = self.root.cm.maxabscoeff ()
        self.bestCoefficients = self.root.cm.best
        self.secondaryCoefficients = self.root.cm.secondary
        self.directions = self.root.cm.direction
        self.absNormalizedCoefficients = self.root.cm.norm

        # Create an empty vector that we'll use later
        self.optimalCentralLinkLength = self.makeEmptyRowVector ()
        self.nextStep ()
    def task_computeOptimalDistances (self):
        if not self.enterThisFunction (): return
        self.computeListOfVisibleNodes ()
        self.optimalCrosslinkLength = []

        for i in range (self.root.N):
            _optimalCrosslinkLength = dict ()
            _normalizedCoefficientVector = self.absNormalizedCoefficients [i]

            for j in _normalizedCoefficientVector:
                _distance = int ((1.0 - _normalizedCoefficientVector [j]) * self.root.MAX_CROSSLINK_LENGTH)

                if _distance < self.root.MINIMUM_SEPARATION:
                    _distance = self.root.MINIMUM_SEPARATION

                _optimalCrosslinkLength [j] = _distance

            self.optimalCrosslinkLength.append (_optimalCrosslinkLength)

        self.nextStep ()
    def task_cutoffOuterLinks (self):        
        if not self.enterThisFunction (): return
        self.root.galaxy.view.outerLinkCutoffSlider.slider.value ()
        self.root.displayedLastTime = self.root.galaxy.view.visibleNodeDetails.nodeList ()
        _sliderValue = (255 - self.root.galaxy.view.outerLinkCutoffSlider.slider.value ()) / 255.0
        
        self.computeListOfVisibleNodes ()
        _centerNode = self.root.centerNode () ## Value is 0
        
        _newVisibleNodeIndexList = []
        _sparse = self.root.cm.sparse  ### value is true
       
        _normalizedCoefficients = self.absNormalizedCoefficients [_centerNode]
        
        for i in self.visibleNodeIndexList:
            if i == _centerNode:
                _newVisibleNodeIndexList.append (_centerNode)
            else:
                _normalized = 0 if _sparse and i not in _normalizedCoefficients else _normalizedCoefficients [i]

                if _normalized >= _sliderValue:
                    _newVisibleNodeIndexList.append (i)

        self.visibleNodeIndexList = _newVisibleNodeIndexList ## Takes input of the point value will be plotted in cercle
        #print self.visibleNodeIndexList
        self.nextStep ()    
    def task_cutoffCentralLinks (self):
        _categoryData=[]
        parentData=[]
        if self.root.db:
            _series = self.root.tss.getseries

            for i in range (self.root.N):
                _seriesElement = _series (i)
                if i>0:
                    try :
                        _seriesElement.category ().split(':')[2]
                    except:
                        parentData.append(i)
                _categoryData.append ([_seriesElement.category (), _seriesElement.label (), i])
               
        if not self.enterThisFunction (): return

        self.root.displayedLastTime = self.root.galaxy.view.visibleNodeDetails.nodeList ()
        _sliderValue = (255 - self.root.galaxy.view.centralLinkCutoffSlider.slider.value ()) / 255.0
        
        self.computeListOfVisibleNodes ()
        _centerNode = self.root.centerNode () ## Value is 0
        
        _newVisibleNodeIndexList = []
        _sparse = self.root.cm.sparse  ### value is true
       
        _normalizedCoefficients = self.absNormalizedCoefficients [_centerNode]
        
        for i in self.visibleNodeIndexList:
            if i == _centerNode:
                _newVisibleNodeIndexList.append (_centerNode)
            else:
                _normalized = 0 if _sparse and i not in _normalizedCoefficients else _normalizedCoefficients [i]

                if _normalized >= _sliderValue or i in parentData:
                    _newVisibleNodeIndexList.append (i)

        self.visibleNodeIndexList = _newVisibleNodeIndexList ## Takes input of the point value will be plotted in cercle
        #print self.visibleNodeIndexList
        self.nextStep ()
    def task_makeLinks (self):
        if not self.enterThisFunction (): return
        _sliderValue = (255 - self.root.galaxy.view.cutoffSlider.slider.value ()) / 255.0
        _centerNode = self.root.centerNode ()
        _sparse = self.root.cm.sparse

        for i in self.visibleNodeIndexList:
            _node = self.root.nodes [i].galaxy
            _node.linksOut = []
            _node.linksIn = []

            _normalizedCoefficients = self.absNormalizedCoefficients [i]
            _bestCoefficients = self.bestCoefficients [i]
            _secondaryCoefficients = self.secondaryCoefficients [i]
            _directions = self.directions [i]
            _maxCoefficient = 1.0 if self.root.cm.maxabscoeff () == 0.0 else self.root.cm.maxabscoeff ()

            for j in self.visibleNodeIndexList:
                if j < i:
                    _normalized = 0 if _sparse and j not in _normalizedCoefficients else _normalizedCoefficients [j]

                    if (_normalized >= _sliderValue) or (i == _centerNode) or (j == _centerNode):
                        _best = 0 if _sparse and j not in _bestCoefficients else _bestCoefficients [j]

                        if _best != 0:
                            _secondary = 0 if _sparse and j not in _secondaryCoefficients else _secondaryCoefficients [j]
                            _direction = 0 if _sparse and j not in _directions else _directions [j]

                            if _direction == 2:
                                _link = universe.GalaxyLink (self.root, j, i, _best, _secondary, _maxCoefficient)
                            else:
                                _link = universe.GalaxyLink (self.root, i, j, _best, _secondary, _maxCoefficient)
        
        self.nextStep ()
    def task_tupliseNodeLinks (self):
        if not self.enterThisFunction (): return

        _allLinks = []

        for _nodeIndex in self.visibleNodeIndexList:
            _node = self.root.nodes [_nodeIndex].galaxy

            for _link in _node.linksIn:
                _allLinks.append (_link)

            _node.linksIn = tuple (_node.linksIn)
            _node.linksOut = tuple (_node.linksOut)

        self.root.galaxy.view.links = tuple (_allLinks)
        
        self.nextStep ()
    def task_removeUnattachedNodes (self):
        if not self.enterThisFunction (): return
        _centerNode = self.root.centerNode ()
        _cutoffNonZero = (self.root.galaxy.view.centralLinkCutoffSlider.slider.value () != 255) 

        for _index in self.visibleNodeIndexList [:]:
            _node = self.root.nodes [_index]
            _galaxy = _node.galaxy

            if _index == _centerNode:
                for _link in _galaxy.linksIn:
                    _link.zValue = 4

                for _link in _galaxy.linksOut:
                    _link.zValue = 4
            else:
                if _cutoffNonZero:
                    if len (_galaxy.linksOut):
                        None
                    elif len (_galaxy.linksIn):
                        None
                    else:
                        self.visibleNodeIndexList.remove (_index)

        self.nextStep ()
    def task_removeUnattachedNodes (self):
        if not self.enterThisFunction (): return
        _centerNode = self.root.centerNode ()
        _cutoffNonZero = (self.root.galaxy.view.outerLinkCutoffSlider.slider.value () != 255) 

        for _index in self.visibleNodeIndexList [:]:
            _node = self.root.nodes [_index]
            _galaxy = _node.galaxy

            if _index == _centerNode:
                for _link in _galaxy.linksIn:
                    _link.zValue = 4

                for _link in _galaxy.linksOut:
                    _link.zValue = 4
            else:
                if _cutoffNonZero:
                    if len (_galaxy.linksOut):
                        None
                    elif len (_galaxy.linksIn):
                        None
                    else:
                        self.visibleNodeIndexList.remove (_index)

        self.nextStep ()    
    def task_findRangeOfCentralLinks (self):
        coffList = [];
        if not self.enterThisFunction (): return
        _minCoeff = 1.0E+99
        _maxCoeff = 0.0
        _centerNode = self.root.centerNode ()
        _bestCoefficients = self.bestCoefficients [_centerNode]
        _sparse = self.root.cm.sparse
        newCoeff = 1
        for _nodeIndex in self.visibleNodeIndexList:
            if _nodeIndex != _centerNode:
                _coeff = 0 if _sparse and _nodeIndex not in _bestCoefficients else abs (_bestCoefficients [_nodeIndex])
                _maxCoeff = max (_maxCoeff, _coeff)
                _minCoeff = min (_minCoeff, _coeff)
                coffList.append(_coeff)
                #print _coeff
                #print _nodeIndex 
                if _coeff < newCoeff:
                    newCoeff = _coeff
                    outerNode = _nodeIndex
                ## much anticipated coefficient
                
        # Calculate the scaling values
        #print 'min',newCoeff,"  node",outerNode
        sortedCoffList=sorted(coffList)
        #print sortedCoffList
        #print sortedCoffList
        self.coeffShift = _minCoeff

        try:
            self.coeffMultiplier = 1.0 / (_maxCoeff - _minCoeff)
        except:
            self.coeffMultiplier = 0.0
            self.coeffShift = 0.0

        self.secondaryNodeIndexList = self.visibleNodeIndexList [:]

        # Remove the central node from the list of secondary nodes
        if _centerNode in self.secondaryNodeIndexList:
            self.secondaryNodeIndexList.remove (_centerNode)

        if _centerNode not in self.visibleNodeIndexList:
            print 'The central node appears to be unapparent'

        self.nextStep ()
    def task_computeSecondaryNodeIndexList (self):
        if not self.enterThisFunction (): return
        _list = self.visibleNodeIndexList [:]
        _filteredList = []

        # ANDY 2011-11-04 Added this line
        self.secondaryNodeIndexList = self.visibleNodeIndexList [:]

        """
        for _nodeIndex in _list:
            _node = self.root.nodes [_nodeIndex]

            if (len (_node.galaxy.linksIn) + len (_node.galaxy.linksOut)) > 0:
                _filteredList.append (_nodeIndex)

        self.secondaryNodeIndexList = _filteredList
        """
        
        self.nextStep ()
    def task_computeAlphae (self):
        if not self.enterThisFunction (): return
        self.alpha = dict () # Dictionary of bearings

        if self.root.centerNode () in self.secondaryNodeIndexList:
            self.secondaryNodeIndexList.remove (self.root.centerNode ())

        if len (self.secondaryNodeIndexList):
            for _nodeIndex in self.visibleNodeIndexList:
                self.alpha [_nodeIndex] = self.Talpha (self.root.centerNode (), self.secondaryNodeIndexList [0], _nodeIndex)
                
        self.nextStep ()
    def task_computeOptimalDistancesToCenterNode (self):
        #### Here we are calculating the length which value should be plotted where
        if not self.enterThisFunction (): return

        self.root.galaxy.view.visibleNodeDetails.setNodeList (self.visibleNodeIndexList)
        _power = (1.0 + (self.root.galaxy.view.centrifugeSlider.slider.value ())) / 256.0
        _centerNode = self.root.centerNode ()
        _bestCoefficients = self.bestCoefficients [_centerNode]
        _sparse = self.root.cm.sparse

        for _nodeIndex in self.visibleNodeIndexList:
            if _nodeIndex != _centerNode:
                _best = 0 if _sparse and _nodeIndex not in _bestCoefficients else abs (_bestCoefficients [_nodeIndex])
                _coeff = (_best - self.coeffShift) * self.coeffMultiplier
                _centrifugedCoefficient = 1.0 - math.pow (_coeff, _power)
                self.optimalCentralLinkLength [_nodeIndex] = _centrifugedCoefficient * self.root.SCALING + self.root.OFFSET
                #print self.optimalCentralLinkLength [_nodeIndex]
                length = self.optimalCentralLinkLength [_nodeIndex]
               # print length,"node ",_nodeIndex
                
        
        self.nextStep ()
    def computeListOfVisibleNodes (self):
        self.visibleNodeIndexList = []

        for _nodeIndex, _node in enumerate (self.root.nodes):
            if not _node.hiding:
                self.visibleNodeIndexList.append (_nodeIndex)

        if not self.root.centerNode () in self.visibleNodeIndexList:
            self.visibleNodeIndexList.append (self.root.centerNode ())
           
    def task_placeNodes (self):
        if not self.enterThisFunction (): return

        # Reset the node position information
        self.root.galaxy.view.visibleNodeDetails.resetPositions ()

        # Place the primary node
        self.root.galaxy.view.visibleNodeDetails.setPosition (self.root.centerNode (), QtCore.QPointF (0, 0))

        # Place non-central nodes
        
        if len (self.secondaryNodeIndexList):
            self.secondaryNode = self.secondaryNodeIndexList [0]

            for _nodeIndex in self.secondaryNodeIndexList:
                _currentPosition = self.root.nodes [_nodeIndex].galaxy.previousEndpoint

                try:
                    self.alpha [_nodeIndex] = math.atan (_currentPosition.y () / _currentPosition.x ())

                    if _currentPosition.x () < 0.0:
                        self.alpha [_nodeIndex] -= math.pi
                except:
                    self.alpha [_nodeIndex] = random.uniform (0.0, 2.0 * math.pi) # Start with nodes with random alphae so when crosslink cutoff is max we have some spread

                _intensity = self.distance (_nodeIndex)
                _alpha = self.alpha [_nodeIndex]
                self.root.galaxy.view.visibleNodeDetails.setPosition (_nodeIndex, QtCore.QPointF (_intensity * math.cos (_alpha), _intensity * math.sin (_alpha)))
        #print self.visibleNodeIndexList         
        self.nextStep ()
    def task_setupAdjust (self):
        if not self.enterThisFunction (): return
        self.DEGREES = math.pi / 180.0

        # Usual values
        self.alphaDelta = 130.0 * self.DEGREES
        self.alphaDeltaReductionFactor = 0.7
        self.alphaDeltaSmallest = 5.0 * self.DEGREES

        self.nextStep ()
    def task_setupAdjustAllNodes (self):
        # See how many iterations we need at most - this is just so we can indicate progress
        #self.iterations = int (math.log10 (self.alphaDeltaSmallest / self.alphaDelta) / math.log10 (self.alphaDeltaReductionFactor)) + 1
        self.iteration = 0
        self.thisNode = 1 # This has to start at 1, not zero. We ignore the first value in the list
        self.alphaDelta = 130.0 * self.DEGREES

        if len (self.secondaryNodeIndexList):
            self.lastNode = self.secondaryNodeIndexList [-1]
            self.changesThisIteration = False
            self.nextStep ()
        else:
            # Skip the next step
            self.phase = self.phases [self.phases.index (self.phase) + 1]
            self.nextStep ()
    def task_adjustAllNodes (self):
        if not self.enterThisFunction (): return # Don't want to reset timer
        _startTime = time.time ()
        self.DECLUTTER_THRESHOLD = 400 # This is the square of the repulsion distance
        self.declutterSliderValue = self.root.galaxy.view.declutterSlider.slider.value ()
        self.lsZeroCache = []
        _secondaryNodeIndexList = self.secondaryNodeIndexList
        _alphaDeltaReductionFactor = self.alphaDeltaReductionFactor
        self.lsZeroCache = [-1] * self.root.N

        if len (_secondaryNodeIndexList) > 1:
            _thisNode = _secondaryNodeIndexList [self.thisNode]

            while (time.time () - _startTime) < .01:
                self.changesMade = self.lsIterationOnOneNode (_thisNode, _secondaryNodeIndexList, self.alphaDelta)
                self.changesThisIteration = True

                if self.alphaDelta < self.alphaDeltaSmallest:
                    self.nextStep ()
                    return
                else:
                    if _thisNode == self.lastNode:
                        if self.changesThisIteration:
                            self.thisNode = 1
                            _thisNode = _secondaryNodeIndexList [self.thisNode]
                            self.alphaDelta *= _alphaDeltaReductionFactor
                            self.iteration += 1
                            self.changesThisIteration = False
                        else:
                            self.nextStep ()
                            return
                    else:
                        self.thisNode += 1
                        _thisNode = _secondaryNodeIndexList [self.thisNode]

            self.repeatStep ()
        else:
            self.nextStep ()
    def task_noLongerWorking (self):
        if not self.enterThisFunction (): return
        self.nextStep ()
    def task_end (self):
        if not self.enterThisFunction (): return
    def makeEmptyRowVector (self):
        _vector = []

        for i in range (self.root.N):
            _vector.append (0)

        return _vector
    def makeEmptyTriangularMatrix (self):
        _matrix = []

        for i in range (self.root.N):
            _row = []

            for j in range (i):
                _row.append (0)

            _matrix.append (_row)

        return _matrix
    def distance (self, j):
        return self.optimalCentralLinkLength [j]
    def suspendRedraw (self, state):
        self.suspend = state
    def getOptimalCrosslinkLength (self, nodeIndex1, nodeIndex2):
        _lengths = self.optimalCrosslinkLength

        if nodeIndex2 in _lengths [nodeIndex1]:
            return _lengths [nodeIndex1] [nodeIndex2]
        else:
            return self.root.MAX_CROSSLINK_LENGTH
    def Talpha (self, centralNodeIndex, nodeIndex1, nodeIndex2):
        if nodeIndex1 == nodeIndex2:
            return 3.14
        elif nodeIndex1 == centralNodeIndex:
            return 3.14
        elif nodeIndex2 == centralNodeIndex:
            return 3.14

        _a = self.distance (nodeIndex1)
        _b = self.distance (nodeIndex2)
        _d = self.root.galaxyLayoutThread.getOptimalCrosslinkLength (nodeIndex1, nodeIndex2)
        _a2 = _a * _a
        _b2 = _b * _b
        _d2 = _d * _d

        try:
            result = math.acos ((_a2 + _b2 - _d2) / (2.0 * _a * _b))
        except:
            result = 3.14

        return result
    def placeNode (self, centralNodeIndex, thisNodeIndex):
        _optimalDistance = self.distance (thisNodeIndex)
        _x = _optimalDistance * math.cos (self.alpha [thisNodeIndex])
        _y = _optimalDistance * math.sin (self.alpha [thisNodeIndex])
        self.root.galaxy.view.visibleNodeDetails.setPosition (thisNodeIndex, QtCore.QPointF (_x, _y))
    def sumOfSquares (self, centralNodeIndex, thisNode, _listOfVisibleNodes):
        sum = 0
        _nodeIterationList = _listOfVisibleNodes [:]
        
        if thisNode in _nodeIterationList:
            _nodeIterationList.remove (thisNode)

        posThis = self.root.galaxy.view.visibleNodeDetails.position (thisNode)
        posThisX = posThis.x ()
        posThisY = posThis.y ()
        _sliderValue = (255 - self.root.galaxy.view.cutoffSlider.slider.value ()) / 255.0
        _normalizedCoefficients = self.absNormalizedCoefficients [thisNode]
        _sparse = self.root.cm.sparse

        for nodeIndex in _nodeIterationList:
            _normalized = 0 if _sparse and nodeIndex not in _normalizedCoefficients else _normalizedCoefficients [nodeIndex]

            if _normalized < _sliderValue:
                continue

            posIndex = self.root.galaxy.view.visibleNodeDetails.position (nodeIndex)
            distanceX = posThisX - posIndex.x ()
            distanceY = posThisY - posIndex.y ()

            # Make squares by multiplying numbers by themselves. Don't use math.pow: it's way too slow
            effect = distanceX * distanceX + distanceY * distanceY

            _term = self.getOptimalCrosslinkLength (thisNode, nodeIndex)
            optimal = _term * _term
            _diff = abs (effect - optimal)

            if effect < self.DECLUTTER_THRESHOLD:
                _power = 1.0 + self.declutterSliderValue / 500.0
                _addition = math.pow (_diff * (1 + ((self.declutterSliderValue / 255.0) * (self.DECLUTTER_THRESHOLD - effect) / self.DECLUTTER_THRESHOLD)), _power)
                sum += _addition
            else:
                sum += _diff

        return sum
    def thisFunction (self):
        return inspect.stack () [2] [3]
    def enterThisFunction (self):
        if self.entryByStep:
            self.entryByStep = False
        else:
            self.BIG_START = time.time ()
            self.root.galaxyTime = ConciseMonitor()
            self.START = time.time ()
            self.root.galaxy.view.lastTimeDisplayed = time.time ()

        _requestedFunction = self.thisFunction ()
        _requestedIndex = self.phasesByName [_requestedFunction]
        _currentIndex = self.phasesByName [self.phase.__name__]

        if _currentIndex > self.maxIndex:
            self.maxIndex = _currentIndex

        if _requestedIndex > self.maxIndex:
            return False
        else:
            self.phase = self.phases [_requestedIndex]
            return True
    def makeListOfVisibleNodes (self):
        if not self.enterThisFunction (): return
        self.computeListOfVisibleNodes ()
        self.nextStep ()
    def nextStep (self):
        self.resource_usage.report ('nextStep: %s' % (self.phase.__name__))
        self.resource_usage = ConciseMonitor()
        
        # Report how long the last phase took
        ##print self.phase.__name__
        if self.phase.__name__ == 'task_preamble':
            self.START = time.time ()
            self.BIG_START = self.START

        self.START = self.root.INSTRUMENT_CENTRIFUGE (self.phase.__name__, self.START)
        ##print self.START
        self.iteration = 0

        # prepare for next phase
        self.phase = self.phases [self.phases.index (self.phase) + 1]

        # Tell the GUI thread to move on
        self.root.galaxy.view.display.emit ()
    def repeatStep (self):
        self.root.galaxy.view.display.emit ()
    def reset (self):
        self.phaseIndex = 0
        self.phase = self.phases [0]
        self.iteration = 0
        self.maxIndex = -1
        self.entryByStep = False
    def doPhase (self):
        if not self.suspend:
            if self.iteration == 0:
                self.START = time.time ()

            self.entryByStep = True
            self.phase ()
    def doQuit (self):
        None
    def run (self):
        self.setPriority (QtCore.QThread.LowestPriority)
        self.exec_ () # Wait for events directed to this thread
    def lsIterationOnOneNode (self, nodeIndex, nodeIndexList, alphaDelta):
        if self.lsZeroCache [nodeIndex] == -1:
            lsZero = self.sumOfSquares (self.root.centerNode (), nodeIndex, nodeIndexList)
        else:
            lsZero = self.lsZeroCache [nodeIndex]

        _initialAlpha = self.alpha [nodeIndex]
        self.alpha [nodeIndex] += alphaDelta
        self.placeNode (self.root.centerNode (), nodeIndex)
        lsPlus = self.sumOfSquares (self.root.centerNode (), nodeIndex, nodeIndexList)

        if lsPlus >= lsZero:
            self.alpha [nodeIndex] = _initialAlpha - alphaDelta
            self.placeNode (self.root.centerNode (), nodeIndex)
            lsMinus = self.sumOfSquares (self.root.centerNode (), nodeIndex, nodeIndexList)

            if lsMinus >= lsZero:
                self.alpha [nodeIndex] = _initialAlpha
                self.placeNode (self.root.centerNode (), nodeIndex)
                return False
            else:
                self.lsZeroCache [nodeIndex] = lsMinus
        else:
            self.lsZeroCache [nodeIndex] = lsPlus

        return True

class GalaxyLayout ():
    def __init__ (self, root):
        self.root = root
        self.count = 0
        self.ellipseBank = []
        self.linkBank = []
        self.mappedItems = []
    def layout (self):
        print 'LAYOUT CALLED'
        galaxyLayoutThread.resource_usage = ConciseMonitor()
        self.root.galaxyLayoutThread.task_preambleSignal.emit ()
    def reconstructNodesAndLinks (self, desiredNodeList, selectionList, cosmetic):
        self.LOCAL_START = time.time ()
        self.RECON_START = self.LOCAL_START
        _unconsideredCount = 0
        _scene = self.root.galaxy.view.scene
        _localEllipseBank = []
        _localLinkBank = []

        sceneItems = self.mappedItems
        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('recreate:get items', self.LOCAL_START)
        
        for _el in self.mappedItems:
            if _el.isVisible ():
                if isinstance (_el, universe.Ellipse):
                    _localEllipseBank.append (_el)
                elif isinstance (_el, universe.LinkGraphic):
                    _localLinkBank.append (_el)
                else:
                    print 'Attempt to liberate an unrecognised scene item.'

        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('recreate:scan scene', self.LOCAL_START)
        self.root.galaxy.nodes = []

        for _nodeIndex in desiredNodeList:
            _node = self.root.nodes [_nodeIndex]

            if len (_localEllipseBank):
                _ellipse = _localEllipseBank.pop ()
                _status = _ellipse.setup (_nodeIndex)
            elif len (self.ellipseBank):
                _ellipse = self.ellipseBank.pop ()
                _status = _ellipse.setup (_nodeIndex)
            else:
                _ellipse = universe.GalaxyEllipse (self.root.galaxy.view, self.root, _nodeIndex)
                self.mappedItems.append (_ellipse)
                _status = not _ellipse

            #if _nodeIndex not in self.root.displayedLastTime:
            #    _ellipse.node.galaxy.previousEndpoint = QtCore.QPointF (0, 0)
                
            # If we're trying to display a database that has been closed...
            if _status:
                return True

            self.root.galaxy.nodes.append (_ellipse)

            if _nodeIndex in selectionList:
                _ellipse.setSelected (True)
            else:
                _ellipse.setSelected (False)

            _node.galaxy.graphic = _ellipse

        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('recreate:nodes', self.LOCAL_START)

        if self.root.linksCheckbox.checkState () == QtCore.Qt.Checked:
            try:
                _linkQuantity = int (self.root.linkQuantityTextField.text ())
            except:
                _linkQuantity = 0

            if _linkQuantity > 0:
                _links = list ()

                for _link in self.root.galaxy.view.links:
                    _links.append ((abs (_link.coefficient), _link))

                _links = sorted (_links, reverse = True) [:_linkQuantity]

                for _link in _links:
                    _sourceNode = self.root.nodes [_link [1].sourceNodeIndex]
                    _targetNode = self.root.nodes [_link [1].targetNodeIndex]
                    _arrowheadsOn = self.root.arrowheadsCheckbox.isChecked ()

                    if len (_localLinkBank):
                        _graphic = _localLinkBank.pop ()
                        _graphic.setup (_sourceNode, _targetNode, _link [1].coefficient, _link [1].secondaryCoefficient, _link [1].maxCoefficient, cosmetic, _arrowheadsOn)
                    elif len (self.linkBank):
                        _graphic = self.linkBank.pop ()
                        _graphic.setup (_sourceNode, _targetNode, _link [1].coefficient, _link [1].secondaryCoefficient, _link [1].maxCoefficient, cosmetic, _arrowheadsOn)
                    else:
                        _graphic = universe.GalaxyLinkGraphic (self.root, self.root.galaxy.view, _sourceNode, _targetNode, _link [1].coefficient,
                                        _link [1].secondaryCoefficient, _link [1].maxCoefficient, cosmetic, _arrowheadsOn)

                        self.mappedItems.append (_graphic)

                    _graphic.setZValue (_link [1].zValue)

                    if self.root.tooltipsCheckbox.checkState () == QtCore.Qt.Checked:
                        _graphic.setToolTip ('%s:%s: coefficient => %.2f (%.2f)' % (_sourceNode.labelText, _targetNode.labelText,
                                    _link [1].coefficient, _link [1].secondaryCoefficient))
                    else:
                        _graphic.setToolTip ('')

                    _link [1].graphic = _graphic
                    _graphic.reshade (255) # Value not important here - just need to get colour into it
                    _graphic.redrawArrowheads ()

        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('recreate:links', self.LOCAL_START)

        # Remove from the scene all those items we can't recycle immediately but keep them by for recycling later
        if len (_localEllipseBank):
            for _ellipse in _localEllipseBank:
                _ellipse.hide ()

            self.ellipseBank += _localEllipseBank

        if len (_localLinkBank):
            for _link in _localLinkBank:
                _link.hide ()

            self.linkBank += _localLinkBank
        
        # Ensure all the lines join up properly to their nodes
        for _nodeIndex in desiredNodeList:
            self.root.nodes [_nodeIndex].galaxy.graphic.itemChange (QtGui.QGraphicsItem.ItemPositionHasChanged, self.root.galaxy.view.visibleNodeDetails.position (_nodeIndex))

        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('recreate:housekeeping', self.LOCAL_START)
        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('recreate:TOTAL', self.RECON_START)
        self.LOCAL_START = self.root.INSTRUMENT_CENTRIFUGE ('=' * 40, time.time ())

        return False
    def directDisplay (self):
        self.root.galaxyLayoutThread.BIG_START = time.time ()
        self.root.galaxy.view.busyIndicator.setState (True)
        self.display ()
        self.root.galaxy.view.busyIndicator.setState (False)
    def display (self):
        self.root.galaxy.view.setUpdatesEnabled (False)
        _savedSelectionList = self.root.selectionList [:]
        self.root.galaxy.view.xf.setup (0, 0, 0, self.root.galaxy.view.rotation.y (), self.root.galaxy.view.rotation.x (), 0)

        # Because of the asynchronous nature of galaxy display it is possible to attempt to display a closed database. Detect this and abort if necessary
        if self.reconstructNodesAndLinks (self.root.galaxy.view.visibleNodeDetails.nodeList (), _savedSelectionList, self.root.cosmeticLinksCheckbox.checkState () == QtCore.Qt.Checked):
            return

        self.root.selectionList = _savedSelectionList
        self.root.galaxy.updateStatus ()
        self.root.galaxy.view.setUpdatesEnabled (True)
        self.root.INSTRUMENT_CENTRIFUGE ('TOTAL', self.root.galaxyLayoutThread.BIG_START)
        #self.root.galaxyTime.report ('TOTAL')
