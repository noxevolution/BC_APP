#!/usr/bin/env python

import sys
import time
import PySide
import math
import graph
import tools

from PySide.QtCore import *
import PySide.QtCore as QtCore
from PySide.QtGui import *
from PySide.QtUiTools import *

from bc import *
from tools import *

import universe as universeNamespace

CLUSTER_MARKER_DIAMETER = 20

class Cluster ():
    def __init__ (self, index):
        self._index = index
        self._nodes = []
    def index (self):
        return self._index
    def addNode (self, nodeIndex):
        self._nodes.append (nodeIndex)
    def nodes (self):
        return self._nodes
    def __len__ (self):
        return len (self._nodes)

class ClusterLayoutThread (QThread):
    def __init__ (self, root):
        QThread.__init__ (self)
        self.root = root
        self.interruptRequest = False
        self.iAmWorking = False
        done = QtCore.Signal ()
        self.suspend = False
        QtCore.QObject.connect (self, QtCore.SIGNAL ('done ()'), self.root.cluster.view.mainThread.display)
        self.secondaryScaling = CLUSTER_MARKER_DIAMETER
    def setup (self, nodes, cm):
        self.nodes = nodes
        self.cm = cm
    def interrupt (self):
        if self.iAmWorking:
            self.interruptRequest = True
    def working (self):
        return self.iAmWorking
    def suspendRedraw (self, state):
        self.suspend = state
    def interruptRequested (self):
        return self.interruptRequest
    def computeInterClusterCoefficients (self):
        _x = ConciseMonitor ()
        # Create an empty list
        self.interClusterCoefficients = []

        # make a list of visible nodes:
        _visibleNodeList = []

        for _nodeIndex, _node in enumerate (self.nodes):
            if not _node.hiding:
                _visibleNodeList.append (_nodeIndex)

        _x.report ('  Cluster: visibleNodeList')
        # make an empty coefficient list
        for _sourceCluster in self.clusters:
            _list = []
            self.interClusterCoefficients.append (_list)
        
            for _targetCluster in self.clusters:
                _list.append (0.0)

        _x.report ('  Cluster: empty coefficient list')
        # Calculate the inter-cluster coefficients
        _sparse = self.cm.sparse

        for _sourceNodeIndex in _visibleNodeList:
            if self.interruptRequested (): break

            if _sourceNodeIndex not in self.clusterMembership:
                continue

            _coefficients = self.cm.norm [_sourceNodeIndex]

            for _targetNodeIndex in _visibleNodeList:
                if _targetNodeIndex not in self.clusterMembership:
                    continue

                if _sourceNodeIndex == _targetNodeIndex:
                    continue

                if _targetNodeIndex in _coefficients:
                    self.interClusterCoefficients [self.clusterMembership [_sourceNodeIndex].index ()] \
                                                  [self.clusterMembership [_targetNodeIndex].index ()] += _coefficients [_targetNodeIndex]

        _x.report ('  Cluster: compute coefficients')
        # Calculate the cluster strength
        for _cluster in self.clusters:
            _members = _cluster.nodes ()
            _sum = 0

            for i in _members:
                for j in _members:
                    if j in self.cm.norm [i]:
                        _sum += self.cm.norm [i] [j]

            _length = len (_members)

            if _length > 0:
                self.interClusterCoefficients [_cluster.index ()] [_cluster.index ()] = _sum / (_length * _length)
            else:
                self.interClusterCoefficients [_cluster.index ()] [_cluster.index ()] = 0

        _x.report ('  Cluster: calculate cluster strengths')
        # Find the maximum value of all coefficients
        _maxCoefficient = 0.0

        for _sourceClusterIndex, _sourceCluster in enumerate (self.clusters):
            for _targetClusterIndex, _targetCluster in enumerate (self.clusters):
                if _targetClusterIndex != _sourceClusterIndex:
                    if self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex] > _maxCoefficient:
                        _maxCoefficient = self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex]

        if _maxCoefficient == 0.0:
            _maxCoefficient = 1.0

        _x.report ('  Cluster: find max')
        # Normalise the coefficients
        self.allCoefficients = []

        if _maxCoefficient > 0.0:
            for _sourceClusterIndex, _sourceCluster in enumerate (self.clusters):
                _allCoefficients = dict ()

                for _targetClusterIndex, _targetCluster in enumerate (self.clusters):
                    if _targetClusterIndex != _sourceClusterIndex:
                        _coeff = self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex]
                        self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex] /= _maxCoefficient
                        _allCoefficients [_targetClusterIndex] = abs (_coeff * 0.8 / _maxCoefficient)

                self.allCoefficients.append (_allCoefficients)

        _x.report ('  Cluster: normalise')
    def graphClustering (self):
        self.root.cluster.view.visibleNodeDetails.resetNodeList ()
        self.root.cluster.view.visibleNodeDetails.resetPositions ()
        _totalClusters = len (self.clusters)

        if _totalClusters == 0:
            return

        _primaryScaling = (self.root.SCALING + self.root.OFFSET) * 0.9
        _radius = self.root.clusterLayoutThread.secondaryScaling
        self.root.cluster.view.circles = []

        for _clusterNumber, _cluster in enumerate (self.clusters):
            if self.interruptRequested ():
                break

            _totalNodes = len (_cluster)

            if _totalNodes:
                _xCluster = self._coordinates [_clusterNumber].x ()
                _yCluster = self._coordinates [_clusterNumber].y ()
                self.root.cluster.view.circles.append (CircleDescriptor (_xCluster, _yCluster, _radius))

                _graph = graph.Spiral (len (_cluster.nodes ()), scaling = CLUSTER_MARKER_DIAMETER * 0.7, cutoff = 20)
                _coordinates = _graph.coordinates ()

                for _nodeNumber, _node in enumerate (_cluster.nodes ()):
                    _x = _xCluster + _coordinates [_nodeNumber].x ()
                    _y = _yCluster + _coordinates [_nodeNumber].y ()
                    self.root.cluster.view.visibleNodeDetails.setPosition (_node, QPointF (_x, _y))
                    self.root.cluster.view.visibleNodeDetails.addIndex (_node)
    def doClustering (self):
        resource_usage = ConciseMonitor ()
        self.root.cluster.view.links = []
        _cutoff = self.root.cluster.view.cutoffSlider.slider.value () / 255.0
        self.nodeList = []
        self.clusters = []
        self.clusterCount = 0

        # Make a list of visible nodes
        for _index, _node in enumerate (self.nodes):
            if not self.nodes [_index].hiding:
                self.nodeList.append (_index)
                _node.cluster.linksIn = []
                _node.cluster.linksOut = []

        self.unallocatedNodes = self.nodeList [:]
        resource_usage.report ('Cluster: Visible nodes')

        # Calculate link strengths
        _sparse = self.cm.sparse
        _strengths = []

        for i, data in enumerate (self.cm.norm):
            if i in self.nodeList:
                for j in data:
                    if j < i:
                        if j in self.nodeList:
                            _coeff = data [j]

                            if _coeff > 0.005:
                                _strengths.append ([_coeff, i, j])

        self.strengths = sorted (_strengths, key = lambda _strength: _strength [0])
        resource_usage.report ('Cluster: Link strengths')

        # Create the links
        _maxCoefficient = 1.0 if self.root.cm.maxabscoeff () == 0.0 else self.root.cm.maxabscoeff ()

        for _link in self.strengths:
            _coeff, i, j = _link

            if _coeff > _cutoff:
                _linkObject = self.root.cluster.view.addLink (i, j, _coeff, _maxCoefficient)
                _linkObject.state = universeNamespace.LinkDrawState.RESET
                _linkObject.zValue = 1
                self.root.cluster.view.links.append (_linkObject)

        resource_usage.report ('Cluster: Create links')

        # Do the clustering
        self.clusterMembership = dict ()
        _strengths = self.strengths [:]
        _clusterCount = -1

        while len (_strengths):
            if self.interruptRequested (): break
            _coeff, _i, _j = _strengths.pop ()

            if _i in self.clusterMembership:
                if _j not in self.clusterMembership:
                    self.clusterMembership [_j] = self.clusterMembership [_i]
                    self.clusters [self.clusterMembership [_i].index ()].addNode (_j)
                    self.unallocatedNodes.remove (_j)
            else:
                if _j in self.clusterMembership:
                    self.clusterMembership [_i] = self.clusterMembership [_j]
                    self.clusters [self.clusterMembership [_j].index ()].addNode (_i)
                    self.unallocatedNodes.remove (_i)
                else:
                    _clusterCount += 1
                    _cluster = Cluster (_clusterCount)
                    self.clusters.append (_cluster)
                    self.clusterMembership [_i] = _cluster
                    self.clusterMembership [_j] = _cluster
                    _cluster.addNode (_i)
                    _cluster.addNode (_j)
                    self.unallocatedNodes.remove (_i)
                    self.unallocatedNodes.remove (_j)

        resource_usage.report ('Cluster: Clustering')

        if self.interruptRequested ():
            return

        self.computeInterClusterCoefficients ()
        resource_usage.report ('Cluster: Intercluster coefficients')

        # Do a force layout for the collection of clusters
        _maximumCoefficient = 0.0
        _coeffs = []

        if len (self.clusters) > 0:
            _fruchtTime = ConciseMonitor ()
            self.root.message [self.root.CLUSTER].display ('Starting layout')
            _initialPositions = []

            for i in range (len (self.allCoefficients)):
                _angle = 2.0 * math.pi * i / len (self.allCoefficients)
                _position = QPointF (math.cos (_angle), math.sin (_angle))
                _initialPositions.append (_position)

            _graph = graph.FruchtermanReingold (self.root.application, self.root.cluster.view, self.allCoefficients, _initialPositions, \
                                                checkInterruptFunction = self.interruptRequested, \
                                                messageItem = self.root.message [self.root.CLUSTER], minimumKineticEnergy = 0.001)
            _fruchtTime.report ('    Cluster: RuchtermanFreingold')
                    
            if _graph.wasInterrupted ():
                self._coordinates = []

            self._coordinates = _graph.result ()

            for i, dummy in enumerate (self._coordinates):
                self._coordinates [i] *= self.root.TOTAL_SCALING

            # Draw the graph
            _graphTime = ConciseMonitor ()
            self.graphClustering ()

            if _graph.wasInterrupted ():
                self.root.cluster.view.update ()
                self.root.application.processEvents ()

            _graphTime.report ('    Cluster: graphClustering')
        else:
            self.root.cluster.view.visibleNodeDetails.resetNodeList ()
            self.root.cluster.view.visibleNodeDetails.resetPositions ()
            self.root.message [self.root.CLUSTER].display ('No clusters')
            self.root.cluster.view.update ()
            self.root.application.processEvents ()
            resource_usage.report ('Cluster: Layout (Empty)')
            return True

        resource_usage.report ('Cluster: Layout')
        return False
    def run (self):
        self.iAmWorking = True
        self.root.cluster.view.circles = []

        if not self.suspend:
            _leaveMessage = self.doClustering ()

            try:
                if not _graph.wasInterrupted ():
                    self.done.emit ()
            except:
                if len (self.clusters) > 0:
                    self.done.emit ()

            if not _leaveMessage: self.root.message [self.root.CLUSTER].hide ()

        self.interruptRequest = False
        self.iAmWorking = False

class ClusterCircle (QGraphicsEllipseItem):
    def __init__ (self, root, x, y, width, height, nodeList):
        QGraphicsEllipseItem.__init__ (self)
        self.root = root
        self.nodeList = nodeList
        self.setRect (QRectF (x, y, width, height))
        self.setAcceptHoverEvents (True)
    def hoverEnterEvent (self, event):
        try:
            for _nodeIndex in self.nodeList:
                _node = self.root.nodes [_nodeIndex].cluster.graphic
                _node.realPen = _node.pen ()
                _bodyColor = self.root.nodes [_nodeIndex].bodyColor
                _bodyIsBright = (_bodyColor.red () > 190) + (_bodyColor.green () > 190) + (_bodyColor.blue () > 190)

                if _bodyIsBright >= 4:
                    _node.setPen (QPen (QColor ('red'), 3))
                else:
                    _node.setPen (QPen (QColor ('white'), 3))
        except:
            pass
    def hoverLeaveEvent (self, event):
        try:
            for _nodeIndex in self.nodeList:
                _node = self.root.nodes [_nodeIndex].cluster.graphic
                _node.setPen (_node.realPen)
        except:
            pass
    def mouseDoubleClickEvent (self, event):
        self.root.hideNodes (list (set (self.root.cluster.view.visibleNodeDetails.nodeList ()) - set (self.nodeList)))
        self.root.setLayoutType ('Centrifuge')
        self.root.updateSelectionsAndHideButtons ()

class ClusterLayout ():
    def __init__ (self, root):
        self.root = root
    def layout (self):
        if self.root.clusterLayoutThread.working ():
            self.root.clusterLayoutThread.interrupt ()

        self.root.clusterLayoutThread.wait ()
        #self.root.setUpdatesEnabled (False)
        self.root.clusterLayoutThread.setup (self.root.nodes [:], self.root.clusterCm)
        self.root.clusterLayoutThread.start ()
        #self.root.setUpdatesEnabled (True)
    def display (self):
        _savedSelectionList = self.root.selectionList [:]
        self.root.setUpdatesEnabled (False)
        self.root.cluster.view.xf.setup (0, 0, 0, self.root.cluster.view.rotation.y (), self.root.cluster.view.rotation.x (), 0)
        self.root.cluster.view.removeAllGraphicsItemsFromScene ()
        self.root.cluster.view.realizeNodes (self.root.cluster.view.visibleNodeDetails.nodeList (), _savedSelectionList)

        if self.root.linksCheckbox.checkState () == Qt.Checked:
            self.root.cluster.view.realizeLinks (self.root.cosmeticLinksCheckbox.checkState () == Qt.Checked)

        # Get the cluster marker colour
        _color = self.root.constants.clusterMarkerColor

        # Display cluster markers
        for _clusterIndex, _cluster in enumerate (self.root.cluster.view.circles):
            _radius = _cluster.radius ()
            _diameter = 2.0 * _radius
            _x, _y, _z = self.root.cluster.view.xf.transform (_cluster.x (), _cluster.y (), 0)
            _rx, _ry, _rz = self.root.cluster.view.xf.transform (_radius, _radius, 0)
            _c = ClusterCircle (self.root, _x - _radius, _y - _radius, _diameter, _diameter, self.root.clusterLayoutThread.clusters [_clusterIndex].nodes ())
            _cluster.setGraphic (_c)
            _c.setPen (Qt.NoPen)
            _coeff = self.root.clusterLayoutThread.interClusterCoefficients [_clusterIndex] [_clusterIndex] * 255
            _markerColor = QColor (_color.red (), _color.green (), _color.blue (), _coeff)
            _c.setBrush (_markerColor)
            _c.setZValue (0)
            self.root.cluster.view.scene.addItem (_c)

        # Show intercluster coefficients
        #for _sourceClusterIndex, _sourceCluster in enumerate (self.root.cluster.view.circles):
        #    for _targetClusterIndex, _targetCluster in enumerate (self.root.cluster.view.circles):
        #        if _targetClusterIndex < _sourceClusterIndex:
        #            _xS, _yS, _zS = self.root.cluster.view.xf.transform (_sourceCluster.x (), _sourceCluster.y (), 0)
        #            _xT, _yT, _zT = self.root.cluster.view.xf.transform (_targetCluster.x (), _targetCluster.y (), 0)
        #            _coeff = self.root.clusterLayoutThread.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex] * 255
        #            _line = QGraphicsLineItem (_xS, _yS, _xT, _yT)
        #            _line.setPen (QColor (0, 0, 255, _coeff))
        #            self.root.cluster.view.scene.addItem (_line)

        self.root.cluster.view.showNodes ()

        if self.root.linksCheckbox.checkState () == Qt.Checked:
            _showLinks = True

            for _link in self.root.cluster.view.links:
                _link.graphic.setZValue (_link.zValue)
                _link.graphic.setVisible (_showLinks)

        self.root.cluster.updateStatus ()
        self.root.setUpdatesEnabled (True)
        self.root.cluster.view.update ()
        self.root.application.processEvents ()
