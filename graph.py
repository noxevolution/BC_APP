#!/usr/bin/env python

####################################################################################
#
#        Graph (linkValueTriangle, width, height)
#
#        N = number of nodes
#        NLINKS = number of links
#
#        A Node is a QPointF. Fetch a node using Graph.getNode(i), i = 0..N-1
#
####################################################################################

import math
import igraph
import time
from PySide.QtCore import QPointF
from monitor import ConciseMonitor

class FruchtermanReingold ():
    def __init__ (self, application, view, coefficients, initialPositions, checkInterruptFunction = None, messageItem = None, \
                    recenter = True, maximumIterations = 100, minimumKineticEnergy = 0.01, damping = 0.9, forceFactor = 0.25):
        _sizeError = Exception ('The sizes of the two arguments do not match')
        _emptyError = Exception ('The coefficients matrix is empty')
        _nodeCount = len (coefficients)
        self.coefficients = coefficients
        _origin = QPointF (0, 0)
        _iteration = 0
        _velocities = [_origin] * _nodeCount
        self.interimPositions = []
        self.finalPositions = []
        self.maximumValue = -1
        self.interrupted = False

        if _nodeCount != len (initialPositions):
            raise _sizeError
        elif _nodeCount == 0:
            raise _emptyError

        _forceFactorMultiplier = forceFactor / _nodeCount

        try:
            _interruptFunction = checkInterruptFunction
        except:
            _interruptFunction = dummyCheckInterruptFunction

        for i in range (_nodeCount):
            self.interimPositions.append (QPointF (initialPositions [i]))
            self.finalPositions.append (QPointF (self.interimPositions [i]))

        _firstIteration = True
        _displayProgress = False
        _maxPercentageComplete = 0.0

        while True:
            if _interruptFunction ():
                self.interrupted = True
                return

            _loopStartTime = time.time ()
            _totalKineticEnergy = 0.0
            _iteration += 1

            for _node1Index, _vector in enumerate (self.interimPositions):
                if _interruptFunction ():
                    self.interrupted = True
                    return

                _netForce = QPointF (0, 0)

                for _node2Index, _node in enumerate (self.interimPositions):
                    if _node1Index != _node2Index:
                        _netForce += self.hooke (_node1Index, _node2Index)

                _velocities [_node1Index] = (_velocities [_node1Index] + _netForce * _forceFactorMultiplier) * damping
                v = _velocities [_node1Index]
                vx = v.x ()
                vy = v.y ()
                _totalKineticEnergy += vx * vx + vy * vy
                self.finalPositions [_node1Index] -= v

            self.interimPositions = self.finalPositions [:]

            if _totalKineticEnergy < minimumKineticEnergy:
                self.totalIterations = _iteration
                self.totalFinalKineticEnergy =  _totalKineticEnergy
                break

            if _iteration >= maximumIterations:
                self.totalIterations = _iteration
                self.totalFinalKineticEnergy =  _totalKineticEnergy
                break

            if messageItem:
                _percentageComplete = min (100, 100.0 * math.sqrt (minimumKineticEnergy / _totalKineticEnergy))
                _maxPercentageComplete = max (_maxPercentageComplete, _percentageComplete)

                if _firstIteration:
                    _firstIteration = False

                    if (time.time () - _loopStartTime ) > .001:
                        _displayProgress = True

                if _displayProgress:
                    if _percentageComplete > 99.9:
                        messageItem.display ('Complete')
                    else:
                        messageItem.display ('%d%% done' % (_maxPercentageComplete + 0.5))

                    view.update ()
                    application.processEvents ()

        if recenter:
            self.recenter (self.finalPositions)
    def wasInterrupted (self):
        return self.interrupted
    def dummyCheckInterruptFunction (self):
        return False
    def pretty (self, pos):
        return '(%.2f, %.2f)' % (pos.x (), pos.y ())
    def recenter (self, positions):
        _middle = QPointF (0, 0)
        _nodeCount = len (positions)

        for _position in positions:
            _middle += _position

        _middle /= _nodeCount

        for _position in positions:
            _position -= _middle
    def iterations (self):
        try:
            return self.totalIterations
        except:
            return None
    def finalKineticEnergy (self):
        try:
            return self.totalFinalKineticEnergy
        except:
            return None
    def result (self):
        return self.finalPositions
    def hooke (self, index1, index2):
        _delta = self.interimPositions [index2] - self.interimPositions [index1]

        try:
            _angle = math.atan (_delta.y () / _delta.x ())
        except:
            _angle = math.pi / 2.0 if _delta.y () > 0 else -math.pi / 2.0

        if _delta.x () < 0:
            _angle += math.pi

        _coefficientVector = self.coefficients [index1]
        _coefficientMagnitude = 1.0 - (0.0 if index2 not in _coefficientVector else abs (_coefficientVector [index2]))
        _coeffX = _coefficientMagnitude * math.cos (_angle)
        _coeffY = _coefficientMagnitude * math.sin (_angle)
        _coeff = QPointF (_coeffX, _coeffY)
        return _coeff - _delta

# Lays out the coeffs list in a spiral
class Spiral ():
    def __init__ (self, nodeCount, scaling = 1.0, cutoff = 1):
        self.nodes = []

        if nodeCount == 1:
            self.nodes.append (QPointF (0, 0))
        elif nodeCount < cutoff:
            _angularIncrement = 2.0 * math.pi / nodeCount
            _angle = _angularIncrement

            for i in range (nodeCount):
                self.nodes.append (QPointF (math.cos (_angle) * scaling, math.sin (_angle) * scaling))
                _angle += _angularIncrement
        else:
            _angularIncrement = math.pi / 7.3
            _magnitudeIncrement = 1.0 * scaling / nodeCount
            _angle = _angularIncrement
            _magnitude = _magnitudeIncrement

            for i in range (nodeCount):
                self.nodes.append (QPointF (math.cos (_angle) * _magnitude, math.sin (_angle) * _magnitude))
                _angle += _angularIncrement
                _magnitude += _magnitudeIncrement
    def coordinates (self):
        return self.nodes

class FruchtermanReingoldIgraph ():
    def __init__(self, links, scaling = 1):
        resource_usage = ConciseMonitor()
        self._scaling = scaling
        self._size = len (links)
        self._links = links

        # initialise the igraph.Graph
        _ig = igraph.Graph (self._size)
        _weights = []

        for i in range (self._size):
            for j in range (i):
                _ig.add_edges ((i, j))
                _corr = self.getLink (i, j)
                _w = int (1000 * _corr)
                _weights.append (_w)

        resource_usage.report ('      FruchtermanReingold: weights')
        x = []
        for i in range (self._size):
            _alpha = i * math.pi * 2 / self._size
            x.append (10 * [math.cos (_alpha), 10 * math.sin (_alpha)])

        resource_usage.report ('      FruchtermanReingold: initial positions')
        _coordinates = self.recentre (_ig.layout_fruchterman_reingold (seed = x, weights = _weights, repulserad = 10))
        resource_usage.report ('      FruchtermanReingold: recentre')
        _maxValue = 0.0

        """
        for i in range (len (_coordinates)):
            if abs (_coordinates [i] [0]) > _maxValue:
                _maxValue = abs (_coordinates [i] [0])

            if abs (_coordinates [i] [1]) > _maxValue:
                _maxValue = abs (_coordinates [i] [0])

        """
        self._nodes = []
        _maxValue = 0

        if _maxValue == 0:
            for i in range (len (_coordinates)):
                _p = QPointF (_coordinates [i] [0] * scaling, _coordinates [i] [1] * scaling)
                self._nodes.append (_p)
        else:
            for i in range (len (_coordinates)):
                _p = QPointF (_coordinates [i] [0] * scaling / _maxValue, _coordinates [i] [1] * scaling / _maxValue)
                self._nodes.append (_p)

        resource_usage.report ('      FruchtermanReingold on %d nodes complete' % (self._size))
    def getLink (self, i, j):
        if i > j:
            return self._links [i] [j]
        elif i < j:
            return self._links [j] [i]
    def coordinates (self):
        return self._nodes
    def recentre (self, nodes):
        _minX = +1e50
        _maxX = -1e50
        _minY = +1e50
        _maxY = -1e50

        for _node in nodes:
            _minX = (min (_minX, _node [0]))
            _minY = (min (_minY, _node [1]))
            _maxX = (max (_maxX, _node [0]))
            _maxY = (max (_maxY, _node [1]))

        _centreX = (_minX + _maxX) / 2.0
        _centreY = (_minY + _maxY) / 2.0

        for _node in nodes:
            _node [0] -= _centreX
            _node [1] -= _centreY

        return nodes
