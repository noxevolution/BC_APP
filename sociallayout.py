#!/usr/bin/env python

import sys
import time
import PySide
import math

from PySide.QtCore import *
import PySide.QtCore as QtCore
from PySide.QtGui import *
from PySide.QtUiTools import *

from tools import *
from monitor import ConciseMonitor

import universe as universeNamespace

class Leaf ():
    def __init__ (self, root, parentLeaf, nodeIndex, hierarchicalLevel):
        self.root = root
        self.parent = parentLeaf
        self.children = []
        self.index = nodeIndex
        self.hierarchicalLevel = hierarchicalLevel
        self.label = self.root.nodes [nodeIndex].labelText
        self.FULL_TURN = math.pi * 2.0
        self.coefficient = 99
    def addChild (self, index, coefficient):
        _child = Leaf (self.root, self, index, self.hierarchicalLevel + 1)
        _child.coefficient = coefficient
        self.children.append (_child)
        return _child
    def showLeaf (self, parent = None):
        print ' ' * self.hierarchicalLevel * 2, '%d:%s (%d leaves, total %d) [%.2f]' % (self.hierarchicalLevel, self.label, self.count, self.totalCount, self.coefficient)

        for _child in self.children:
            _child.showLeaf (self)
    def countLeaves (self, level):
        self.count = len (self.children)
        self.totalCount = self.count
        _newLevel = level

        if self.count:
            for _leaf in self.children:
                _childLevel = _leaf.countLeaves (level + 1)

                if _childLevel > _newLevel:
                    _newLevel = _childLevel

                self.totalCount += _leaf.totalCount
                self.root.social.view.visibleNodeDetails.addIndex (_leaf.index)
        else:
            self.root.social.view.terminals += 1

        return _newLevel
    def createLinks (self, parentLink = None):
        if self.parent:
            self.root.nodes [self.index].socialLinks.append (parentLink)

        _maxCoefficient = 1.0 if self.root.cm.maxabscoeff () == 0.0 else self.root.cm.maxabscoeff ()

        for _leaf in self.children:
            _link = self.root.social.view.addLink (self.index, _leaf.index, _leaf.coefficient, _maxCoefficient)
            self.root.nodes [self.index].socialLinks.append (_link)
            _link.state = universeNamespace.LinkDrawState.RESET
            _link.zValue = 4
            _leaf.createLinks (_link)
    def makeListOfVisibleNodes (self, list):
        list.append (self.index)

        for _child in self.children:
            _child.makeListOfVisibleNodes (list)
    def positionNode (self, span, previousNodes):
        TO_DEGREES = 180.0 / math.pi

        if self.hierarchicalLevel == 0:
            _x = 0.0
            _y = 0.0

            try:
                self.root.social.view.spacing = self.FULL_TURN / self.root.social.view.terminals
            except:
                self.root.social.view.spacing = self.FULL_TURN

            for _child in self.children:
                _child.positionNode (span, previousNodes)
        else:
            if self.count:
                _startAngle = self.root.social.view.angle

                for _child in self.children:
                    _child.positionNode (span, previousNodes)

                self.alpha = (_startAngle + self.root.social.view.angle - self.root.social.view.spacing) / 2.0
            else:
                self.alpha = self.root.social.view.angle
                self.root.social.view.angle += self.root.social.view.spacing

            _intensity = span * self.hierarchicalLevel
            _x = _intensity * math.sin (self.alpha)
            _y = _intensity * math.cos (self.alpha)

        # ANDY self.root.nodes [self.index].social.view.pos = QPointF (_x, _y)
        self.root.social.view.visibleNodeDetails.setPosition (self.index, QPointF (_x, _y))

        if self.index not in previousNodes:
            self.root.nodes [self.index].social.previousEndpoint = QPointF (_x * 10.0, _y * 10.0)

class SocialNetworkLayoutThread (QThread):
    def __init__ (self, root):
        QThread.__init__ (self)
        self.root = root
        self.interruptRequest = False
        self.iAmWorking = False
        done = QtCore.Signal ()
        self.suspend = False
        QtCore.QObject.connect (self, QtCore.SIGNAL ('done ()'), self.root.social.view.mainThread.display)
    def interrupt (self):
        if self.iAmWorking:
            self.interruptRequest = True
    def working (self):
        return self.iAmWorking
    def interruptRequested (self):
        return self.interruptRequest
    def createBranch (self, parent, inflow, cutoff, visibleNodeIndexList, level):
        _newChildren = []
        _sparse = self.root.cm.sparse
        _cutoffValue = self.root.cm.maxabscoeff ()

        for _childIndex in visibleNodeIndexList [:]:
            if inflow:
                _row = self.root.cm.coeffs [parent.index]
                _coefficient = 0 if _sparse and _childIndex not in _row else _row [_childIndex]
            else:
                _row = self.root.cm.coeffs [_childIndex]
                _coefficient = 0 if _sparse and parent.index not in _row else _row [parent.index]

            if abs (_coefficient / _cutoffValue) >= cutoff:
                _child = parent.addChild (_childIndex, _coefficient)
                visibleNodeIndexList.remove (_childIndex)
                _newChildren.append (_child)
            #    print '1 %d: cutoff:%.2f, maxCoeff:%.2f, Coeff:%.2f, Norm:%.2f' % (level, cutoff, _cutoffValue, _coefficient, _coefficient / _cutoffValue)
            #else:
            #    print '0 %d: cutoff:%.2f, maxCoeff:%.2f, Coeff:%.2f, Norm:%.2f' % (level, cutoff, _cutoffValue, _coefficient, _coefficient / _cutoffValue)

        for _child in _newChildren:
            self.createBranch (_child, inflow, cutoff, visibleNodeIndexList, level + 1)
    def suspendRedraw (self, state):
        self.suspend = state
    def run (self):
        resource_usage = ConciseMonitor ()
        self.iAmWorking = True

        if not self.suspend and self.root.nodes:
            for _node in self.root.nodes:
                _node.linksIn = []
                _node.linksOut = []

            self.root.social.view.links = []
            self.root.limitRangeOfCenterNode ()
            self.root.social.view.visibleNodeDetails.setPosition (self.root.centerNode (), QPointF (0, 0))
            _previousNodes = self.root.social.view.visibleNodeDetails.nodeList ()
            self.root.social.view.visibleNodeDetails.setNodeList ([self.root.centerNode ()])

            # Make a simple list of visible nodes
            _visibleNodeIndexList = []

            for _nodeIndex in range (self.root.N):
                _node = self.root.nodes [_nodeIndex]

                if not _node.hiding:
                    _visibleNodeIndexList.append (_nodeIndex)

            if self.root.centerNode () not in _visibleNodeIndexList:
                _visibleNodeIndexList.append (self.root.centerNode ())

            # Make a tree of relevant nodes
            self.root.social.view.rootLeaf = Leaf (self.root, None, self.root.centerNode (), 0)
            _cutoff = self.root.social.view.cutoffSlider.slider.value () / 255.0
            _visibleNodeIndexList.remove (self.root.centerNode ())
            _inflow = (self.root.inflowCheckbox.checkState () == Qt.Checked)
            self.createBranch (self.root.social.view.rootLeaf, _inflow, _cutoff, _visibleNodeIndexList, 0)

            # Note details about the number of hierarchical levels, etc.
            self.root.social.view.terminals = 0
            self.root.social.view.levels = self.root.social.view.rootLeaf.countLeaves (0)

            if self.root.social.view.levels == 0:
                self.root.social.view.levelSpan = self.root.TOTAL_SCALING
            else:
                self.root.social.view.levelSpan = self.root.TOTAL_SCALING / self.root.social.view.levels

            # Clear any old link definitions
            for _node in self.root.nodes:
                _node.socialLinks = []

            self.root.social.view.rootLeaf.createLinks ()
        
            # Make a list of nodes that makes up this tree
            self.root.lsNodeIndexList = []
            self.root.social.view.visibleNodeDetails.resetNodeList ()

            _nodeList = []
            self.root.social.view.rootLeaf.makeListOfVisibleNodes (_nodeList)

            if len (_nodeList):
                self.root.social.view.visibleNodeDetails.setNodeList (_nodeList)
                self.root.social.view.angle = -20.0
                self.root.social.view.rootLeaf.positionNode (self.root.social.view.levelSpan, _previousNodes)
                self.done.emit ()
                self.root.message [self.root.SOCIAL].hide ()
            else:
                self.root.message [self.root.SOCIAL].display ('No nodes to display')

        #resource_usage.report ('Social: Finished')
        self.iAmWorking = False

class SocialLayout ():
    def __init__ (self, root):
        self.root = root
        self.circles = []
    def layout (self):
        if self.root.socialLayoutThread.working ():
            self.root.socialLayoutThread.interrupt ()

        self.root.socialLayoutThread.wait ()
        self.root.setUpdatesEnabled (False)
        self.root.socialLayoutThread.start ()
        self.root.setUpdatesEnabled (True)
    def display (self):
        _savedSelectionList = self.root.selectionList [:]
        self.root.setUpdatesEnabled (False)
        self.root.social.view.xf.setup (0, 0, 0, self.root.social.view.rotation.y (), self.root.social.view.rotation.x (), 0)
        self.root.social.view.removeAllGraphicsItemsFromScene ()
        self.circles = []

        # Display the hierarchical circles
        for _level in range (1, self.root.social.view.levels + 1):
            _oldDiameter = _level * self.root.social.view.previousLevelSpan * 2.0
            _newDiameter = _level * self.root.social.view.levelSpan * 2.0
            _colorIntensity = 255.0 / _level
            _circle = self.root.social.view.makeCircle (self.root, 0, 0, QColor (_colorIntensity, _colorIntensity, _colorIntensity), _oldDiameter, 0)
            _circle.setOpacity (self.root.onionRingOpacitySlider.slider.value ())
            _circle.adjust (_oldDiameter, _newDiameter)
            self.circles.append ([_circle, _colorIntensity])

        self.root.social.view.previousLevels = self.root.social.view.levels
        self.root.social.view.previousLevelSpan = self.root.social.view.levelSpan

        self.root.nodes [self.root.centerNode ()].hiding = False

        for _node in self.root.nodes:
            _node.visible = (_node.index in self.root.social.view.visibleNodeDetails.nodeList ())

        self.root.social.view.realizeNodes (self.root.social.view.visibleNodeDetails.nodeList (), _savedSelectionList)

        if self.root.linksCheckbox.checkState () == Qt.Checked:
            if len (self.root.social.view.links) <= 1000:
                self.root.social.view.realizeLinks (self.root.cosmeticLinksCheckbox.checkState () == Qt.Checked)

                for _link in self.root.social.view.links:
                    _link.graphic.setVisible (True)
                    _link.graphic.toArrowhead.setVisible (True)
                    _link.graphic.fromArrowhead.setVisible (False)

        self.root.social.view.showNodes ()

        # Call this method explicitly as it doesn't get called automatically for the central node
        try:
            self.root.nodes [self.root.centralNodeIndex].social.graphic.itemChange (QGraphicsItem.ItemPositionHasChanged, 0)
        except:
            None

        #self.root.social.view.redrawAllArrowheads ()
        self.root.social.updateStatus ()
        self.root.setUpdatesEnabled (True)
