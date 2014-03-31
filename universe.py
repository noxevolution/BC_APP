#!/usr/bin/env python

import sys
import time
import PySide
import sqlite3
from datetime import date
import re

from PySide.QtCore import *
import PySide.QtCore as QtCore
from PySide.QtGui import *
from PySide.QtUiTools import *
from PySide.QtWebKit import *
import math

from universeprofile import *
from coefficientsprofile import *
from coefficientslist import *
from casualcheck import *
from sociallayout import *
from galaxylayout import *
from clusterlayout import *
from tools import *

class LinkDrawState ():
    # Links are redrawn several times by Qt during an animation. Redrawing of a link is prompted
    # by movement of the node it's connected to. This means that links will be drawn twice if
    # we're not careful. So, what we do is draw the link only when the second-connected node is
    # moved. This will ensure that links are not left 'dangling' (as would be the case if we
    # did the redraw in the opposite order).
    RESET = 1
    FIRST_VISIT = 2
    DONE = 2

class VisibleNodeDetails ():
    def __init__ (self):
        self.mutex = QMutex ()
        self.indexes = []
        self.pos = dict ()
    def nodeList (self):
        #print "visible"
        return self.indexes [:]
    def nodeListLength (self):
        return len (self.indexes)
    def setNodeList (self, nodeList):
        self.mutex.lock ()
        self.indexes = nodeList [:]
        self.mutex.unlock ()
    def resetNodeList (self):
        self.mutex.lock ()
        self.indexes = []
        self.mutex.unlock ()
    def addIndex (self, index):
        self.mutex.lock ()
        self.indexes.append (index)
        self.mutex.unlock ()
    def positions (self):
        return self.pos.copy ()
    def setPosition (self, index, value):
        self.mutex.lock ()
        self.pos [index] = value
        self.mutex.unlock ()
    def changePosition (self, index, value):
        self.mutex.lock ()
        del self.pos [index]
        self.pos [index] = value
        self.mutex.unlock ()
    def position (self, index):
        self.mutex.lock ()
        _position = self.pos [index]
        self.mutex.unlock ()
        return QPointF (_position)
    def resetPositions (self):
        self.mutex.lock ()
        self.pos = dict ()
        self.mutex.unlock ()

class Arrowhead (QGraphicsPolygonItem):
    def __init__ (self, root, parent, position, angle):
        QGraphicsPolygonItem.__init__ (self, QPolygonF ([QPointF (0, 0), QPointF (12, -5), QPointF (10, 0), QPointF (12, 5), QPointF (0, 0)]))
        self.root = root
        self.position = position
        self.angle = angle
        self.setFlags (QGraphicsItem.ItemIgnoresTransformations)
        self.setParentItem (parent)
    def turnOff (self):
        self.hide ()
    def setVector (self, inflow, netZoom, sourceRadius, targetRadius, sourceGraphic, targetGraphic):
        _arrowCutoff = self.root.constants.shortestLineWithArrowheads
        x0 = sourceGraphic.pos.x ()
        y0 = sourceGraphic.pos.y ()
        x1 = targetGraphic.pos.x ()
        y1 = targetGraphic.pos.y ()
        _lineLength = math.sqrt ((y0 - y1) * (y0 - y1) + (x0 - x1) * (x0 - x1)) * netZoom
        
        if _lineLength < _arrowCutoff: # No point in calculating all this stuff for really short lines
            self.setPolygon (QPolygonF ())
            return

        try:
            _angle = math.atan ((y0 - y1) / (x0 - x1))
        except:
            if y0 > y1:
                _angle = math.pi / 2.0
            else:
                _angle = -math.pi / 2.0

        if inflow:
            if x1 < x0:
                _angle += math.pi
        else:
            if x0 < x1:
                _angle += math.pi

        _angleInDegrees = _angle * 180.0 / math.pi

        if inflow:
            _xSourceOffset = sourceRadius * math.cos (_angle) / netZoom
            _ySourceOffset = sourceRadius * math.sin (_angle) / netZoom
            _xSource = x0 + _xSourceOffset
            _ySource = y0 + _ySourceOffset
            _xTargetOffset = targetRadius * math.cos (_angle) / netZoom
            _yTargetOffset = targetRadius * math.sin (_angle) / netZoom
            _xTarget = x1 - _xTargetOffset
            _yTarget = y1 - _yTargetOffset
            self.setPos (QPointF (_xSource, _ySource))
        else:
            _xTargetOffset = targetRadius * math.cos (_angle) / netZoom
            _yTargetOffset = targetRadius * math.sin (_angle) / netZoom
            _xTarget = x1 + _xTargetOffset
            _yTarget = y1 + _yTargetOffset
            _xSourceOffset = sourceRadius * math.cos (_angle) / netZoom
            _ySourceOffset = sourceRadius * math.sin (_angle) / netZoom
            _xSource = x0 - _xSourceOffset
            _ySource = y0 - _ySourceOffset
            self.setPos (QPointF (_xTarget, _yTarget))

        _visibleLineSegmentLength = math.sqrt ((_ySource - _yTarget) * (_ySource - _yTarget) + (_xSource - _xTarget) * (_xSource - _xTarget)) * netZoom

        if _visibleLineSegmentLength < _arrowCutoff:
            self.setPolygon (QPolygonF ())
        else:
            self.setPolygon (QPolygonF ([QPointF (0, 0), QPointF (12, -5), QPointF (10, 0), QPointF (12, 5), QPointF (0, 0)]))

        self.setRotation (_angleInDegrees)
    def setColor (self, color, opacity):
        self.setBrush (color)
        _pen = QPen (QColor (0, 0, 0, opacity))
        self.setPen (_pen)

class Link ():
    def __init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, scaledCoefficient, maxCoefficient, secondaryCoefficient = 0.0):
        self.root = root
        self.sourceNodeIndex = sourceNodeIndex
        self.targetNodeIndex = targetNodeIndex
        self.coefficient = coefficient
        self.scaledCoefficient = scaledCoefficient
        self.secondaryCoefficient = secondaryCoefficient
        self.maxCoefficient = maxCoefficient
        self.zValue = 4

class GalaxyLink (Link):
    def __init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, secondaryCoefficient, maxCoefficient, zValue = 1):
        Link.__init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, coefficient, maxCoefficient, secondaryCoefficient)
        self.root = root
        self.root.nodes [sourceNodeIndex].galaxy.linksOut.append (self)
        self.root.nodes [targetNodeIndex].galaxy.linksIn.append (self)
        self.state = LinkDrawState.RESET
        self.zValue = zValue

class ClusterLink (Link):
    def __init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, scaledCoefficient, maxCoefficient):
        Link.__init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, scaledCoefficient, maxCoefficient)
        self.root = root
        self.root.nodes [sourceNodeIndex].cluster.linksOut.append (self)
        self.root.nodes [targetNodeIndex].cluster.linksIn.append (self)

class SocialLink (Link):
    def __init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, scaledCoefficient, maxCoefficient):
        Link.__init__ (self, root, sourceNodeIndex, targetNodeIndex, coefficient, scaledCoefficient, maxCoefficient)
        self.root = root
        self.root.nodes [sourceNodeIndex].social.linksOut.append (self)
        self.root.nodes [targetNodeIndex].social.linksIn.append (self)

class LinkGraphic (QGraphicsLineItem, QObject):
    def __init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks, toArrowheadOn = False, fromArrowheadOn = False):
        QGraphicsLineItem.__init__ (self)
        QObject.__init__ (self)

        self.root = root
        #self.setCacheMode (QtGui.QGraphicsItem.ItemCoordinateCache) # (Yuk! Makes the lines go all blocky)
        self.myScene = layoutWidget.scene
        self.toArrowheadOn = toArrowheadOn
        self.fromArrowheadOn = fromArrowheadOn
        self.toArrowhead = Arrowhead (self.root, self, 0, 0)
        self.fromArrowhead = Arrowhead (self.root, self, 0, 0)
        self.setZValue (4)
        self.setCursor (Qt.CrossCursor)
        self.myScene.addItem (self)
        LinkGraphic.setup (self, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks, toArrowheadOn)
    def setup (self, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks, arrowheadsOn):
        self.toArrowheadOn = arrowheadsOn
        self.fromArrowheadOn = arrowheadsOn
        self.coefficient = coefficient
        self.maxCoefficient = maxCoefficient
        self.changed = True
        self.state = LinkDrawState.RESET
        self.sourceNode = sourceNode
        self.targetNode = targetNode
        self.setLinkAppearance (cosmeticLinks)
        self.toArrowhead.setParentItem (self)
        self.fromArrowhead.setParentItem (self)
        self.toArrowhead.setVisible (self.toArrowheadOn)
        self.fromArrowhead.setVisible (self.fromArrowheadOn)
        self.show ()
    def redraw (self, sourceNode, targetNode):
        
        self.setLine (sourceNode.pos.x (), sourceNode.pos.y (), targetNode.pos.x (), targetNode.pos.y ())
        self.redrawArrowheads ()
    def setLinkAppearance (self, cosmetic):
        if cosmetic:
            self.thickness = 0.0
        else:
            _normalisedCoefficient = self.coefficient / self.maxCoefficient
            self.thickness = 1.0 + abs (_normalisedCoefficient) * 2.0

            if self.thickness > 3.0:
                self.thickness = 3.0

        if self.coefficient < 0:
            self.color = QColor (self.root.constants.linkNegativeColor)
        else:
            self.color = QColor (self.root.constants.linkPositiveColor)
    def reshade (self, opacity):
        try:
            _overallOpacity = self.root.layoutType ().view.linkOpacitySlider.slider.value () * (0.1 + 0.9 * abs (self.coefficient))

            if _overallOpacity > 255:
                _overallOpacity = 255
        except:
            _overallOpacity = self.root.layoutType ().view.linkOpacitySlider.slider.value () * 0.1

        self.color.setAlpha (_overallOpacity)
        _pen = QPen (self.color, self.thickness, Qt.SolidLine, Qt.RoundCap)
        self.setPen (_pen)
        self.toArrowhead.setColor (self.color, _overallOpacity)
        self.fromArrowhead.setColor (self.color, _overallOpacity)

class GalaxyLinkGraphic (LinkGraphic):
    def __init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, secondaryCoefficient, maxCoefficient, cosmeticLinks, arrowheadsOn = True):
        self.secondaryCoefficient = secondaryCoefficient
        LinkGraphic.__init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks, toArrowheadOn = arrowheadsOn, fromArrowheadOn = arrowheadsOn)
    def setup (self, sourceNode, targetNode, coefficient, secondaryCoefficient, maxCoefficient, cosmeticLinks, arrowheadsOn = True):
        LinkGraphic.setup (self, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks, arrowheadsOn)
        self.secondaryCoefficient = secondaryCoefficient
    def redraw (self):
        LinkGraphic.redraw (self, self.sourceNode.galaxy.graphic, self.targetNode.galaxy.graphic)
    def redrawArrowheads (self):
        _coeff1 = int (self.coefficient * 10000)
        _coeff2 = int (self.secondaryCoefficient * 10000)
        _sourceNode = self.sourceNode.galaxy.graphic
        _targetNode = self.targetNode.galaxy.graphic

        if self.toArrowheadOn:
            self.toArrowhead.setVector (True, self.root.galaxy.view.netZoom, _sourceNode.scaleSize (), _targetNode.scaleSize (), _sourceNode, _targetNode) 
            self.toArrowhead.show ()
        else:
            self.toArrowhead.hide ()

        if (_coeff1 == _coeff2) and self.fromArrowheadOn:
            self.fromArrowhead.setVector (False, self.root.galaxy.view.netZoom, _sourceNode.scaleSize (), _targetNode.scaleSize (), _sourceNode, _targetNode) 
            self.fromArrowhead.show ()
        else:
            self.fromArrowhead.hide ()

class ClusterLinkGraphic (LinkGraphic):
    def __init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks):
        LinkGraphic.__init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks)
    def redraw (self):
        LinkGraphic.redraw (self, self.sourceNode.cluster.graphic, self.targetNode.cluster.graphic)
    def redrawArrowheads (self):
        None

class SocialLinkGraphic (LinkGraphic):
    def __init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks):
        LinkGraphic.__init__ (self, root, layoutWidget, sourceNode, targetNode, coefficient, maxCoefficient, cosmeticLinks, toArrowheadOn = True, fromArrowheadOn = False)
    def redraw (self):
        LinkGraphic.redraw (self, self.sourceNode.social.graphic, self.targetNode.social.graphic)
    def redrawArrowheads (self):
        _sourceNode = self.sourceNode.social.graphic
        _targetNode = self.targetNode.social.graphic
        self.toArrowhead.setVector (self.root.inflowCheckbox.checkState () == Qt.Checked, self.root.social.view.netZoom,
                        _sourceNode.scaleSize (), _targetNode.scaleSize (), _sourceNode, _targetNode) 

class NodeLabel (QGraphicsSimpleTextItem):
    def __init__ (self, root, parent):
        QGraphicsSimpleTextItem.__init__ (self)
        self.root = root

        self.setZValue (7)
        self.backwash = QGraphicsRectItem (self)
        self.backwash.setZValue (6)
        self.backwash.setBrush (self.root.constants.backwashColor)
        self.backwash.setPen (self.root.constants.backwashColor)
        self.setBrush (self.root.constants.nodeTextColor)
        self.setText (parent.node.labelText)
    def setup (self, size, parent):
        self.setParentItem (parent)
        self.backwash.setParentItem (parent)

        if parent.node.special:
            self.setSize (self.root.nodeHighlightFontSize)
        else:
            self.setSize (self.root.nodeFontSize)
    def setSize (self, size):
        _font = QFont ('lucida', size)
        self.setFont (_font)
        self.backwash.setRect (self.boundingRect ())

class Circle (QGraphicsEllipseItem, QObject):
    
    def __init__ (self, root, layoutWidget, x, y, color, diameter, thickness):
        QObject.__init__ (self)
        QGraphicsEllipseItem.__init__ (self)
        self.root = root
        self.setZValue (3)
        self.myScene = layoutWidget.scene
        self.setup (x, y, color, diameter, thickness)
        self.color = color
    def setup (self, x, y, color, diameter, thickness):
        _radius = diameter / 2.0
        self.color = color
        self.setRect (QRectF (x - _radius, y - _radius, diameter, diameter))
        _pen = QPen (color, thickness, Qt.SolidLine)
        self.setPen (_pen)
        self.myScene.addItem (self)
    def adjust (self, oldDiameter, newDiameter):
        self.animPos = QPropertyAnimation (self, 'diameter')
        self.animPos.setDuration (self.root.constants.moveTime)
        self.animPos.setEasingCurve (self.root.animationTypeCombo.type)
        self.animPos.setStartValue (oldDiameter)
        self.animPos.setEndValue (newDiameter)
        self.animPos.start ()
    def setOpacity (self, opacity):
        _pen = QPen (QColor (self.color.red (), self.color.green (), self.color.blue (), opacity))
        self.setPen (_pen)

    ##########################################
    # Setter/getter for "diameter"
    ##########################################
    def getDiameter (self):
        _rect = QGraphicsEllipseItem.rect (self)
        return _rect.height ()
    def setDiameter (self, diameter):
        _radius = diameter / 2.0
        QGraphicsEllipseItem.setRect (self, QRectF (-_radius, -_radius, diameter, diameter))

    diameter = Property (float, getDiameter, setDiameter)
    ##########################################

class LayoutSpecificNodeDetails ():
    def __init__ (self):
        self.pos = QPointF (0, 0)
        self.previousEndpoint = QPointF (0, 0)
        self.linksIn = []
        self.linksOut = []

class Node ():
    def __init__ (self, root, index, outlineColor, bodyColor, textColor, labelText, font, tipText, radius, infoText):
        self.root = root
        self.galaxy = LayoutSpecificNodeDetails ()
        self.cluster = LayoutSpecificNodeDetails ()
        self.social = LayoutSpecificNodeDetails ()
        self.hiding = False
        self.special = False
        self.selectorTreeNode = None
        self.outlineColor = outlineColor
        self.bodyColor = bodyColor
        self.textColor = textColor
        self.labelText = labelText
        self.font = font
        self.tipText = tipText
        self.radius = radius * 5 + 1
        self.infoText = infoText
        self.selected = False
        self.brush = QBrush (QColor (255, 0, 0))
        self.visible = False
        self.labelVisible = True

        # Save the index of Rick's original data tables as he's using this to index his data
        self.index = index

        # Alas, the item won't get smaller and fade into the mist as we increase its
        # "z" component but this does define it's order in the pile of items.
        # The stacking order of graphics items is:
        #   0: Background items
        #   1: Transverse edges
        #   2: Central blanking disk
        #   3: Bullseye
        #   4: Edges connected to the central node
        #   5: Nodes
        #   6: Label backwash
        #   7: Labels
        self.zValue = 5

        # Add the labels, etc.
        self.labelText = labelText
        self.infoText = infoText
    def hideNode (self):
        # If a display task is running, interrupt it and wait for it to stop
        self.root.interruptLayoutsAndWaitForCompletion ()

        self.selectorTreeNode.checked = Qt.Unchecked
        self.root.newSelector.model.dataChanged.emit (QModelIndex (), QModelIndex ())
        self.root.newSelector.model.propagateToggleStateUp (Qt.Unchecked, self.selectorTreeNode)
        self.hiding = True
        self.selected = False
    def unhideNode (self):
        # If a display task is running, interrupt it and wait for it to stop
        self.root.interruptLayoutsAndWaitForCompletion ()

        self.selectorTreeNode.checked = Qt.Checked
        self.root.newSelector.model.dataChanged.emit (QModelIndex (), QModelIndex ())
        self.root.newSelector.model.propagateToggleStateUp (Qt.Checked, self.selectorTreeNode)
        self.hiding = False
        self.selected = False

class OpaqueDisk (QGraphicsEllipseItem):
    def __init__ (self, root, universe, radius, alpha):
        QGraphicsEllipseItem.__init__ (self)

        self.root = root
        self.radius = radius
        self.alpha = alpha
        self.setRect (-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        self.setPen (self.root.constants.opaqueDiskBorderColor)
        self.setBrush (QColor (0, 0 , 0, self.alpha))
        self.setZValue (2)
        universe.scene.addItem (self)
        self.setAcceptHoverEvents (True)
        self.TOLERANCE = 5
        self.readyToMove = False
        self.opacityAction = False
        #self.setToolTip ('Left click resizes the opaque disk; right-click (then move the mouse up and down) changes its opacity.')
    def size (self):
        return self.radius
    def setSize (self, radius):
        self.radius = radius
        self.setRect (-self.radius, -self.radius, self.radius * 2, self.radius * 2)
    def setOpacity (self, value):
        self.alpha = value
        self.setBrush (QColor (0, 0 , 0, self.alpha))
        self.root.galaxy.view.diskOpacitySlider.slider.setValue (value)
    def opacity (self):
        return self.alpha
    def mouseMoveEvent (self, event):
        if self.opacityAction:
            if self.readyToMove:
                _delta = event.pos ().y () - self.opacityStartPosition.y ()
                self.opacityStartPosition = event.pos ()
                self.workingOpacity += _delta

                if self.workingOpacity > 255:
                    self.workingOpacity = 255
                    self.opacityStartPosition = event.pos ()
                elif self.workingOpacity < 0:
                    self.workingOpacity = 0
                    self.opacityStartPosition = event.pos ()

                self.setOpacity (int (self.workingOpacity))
        else:
            if self.readyToMove:
                _pos = event.pos ()
                _distance = math.sqrt (_pos.x () * _pos.x () + _pos.y () * _pos.y ())

                if _distance < (self.root.TOTAL_SCALING - 25) and _distance > 50:
                    self.radius = _distance
                    _diameter = self.radius * 2.0
                    self.setRect (-self.radius, -self.radius, _diameter, _diameter)

        QGraphicsItem.mouseMoveEvent (self, event)
    def hoverMoveEvent (self, event):
        _pos = event.pos ()
        _distance = math.sqrt (_pos.x () * _pos.x () + _pos.y () * _pos.y ())

        if _distance > (self.radius - self.TOLERANCE / self.root.galaxy.view.netZoom):
            self.setCursor (Qt.SizeHorCursor)
            self.readyToMove = True
        else:
            self.unsetCursor ()
            self.readyToMove = False

            QGraphicsItem.hoverEnterEvent (self, event)
    def hoverEnterEvent (self, event):
        self.setCursor (Qt.SizeHorCursor)
        self.readyToMove = True
        QGraphicsItem.hoverEnterEvent (self, event)
    def hoverLeaveEvent (self, event):
        self.unsetCursor ()
        self.readyToMove = False
        QGraphicsItem.hoverLeaveEvent (self, event)
    def mousePressEvent (self, event):
        if event.button () == Qt.LeftButton:
            if self.readyToMove:
                self.opacityAction = False
                self.grabMouse ()
            else:
                QGraphicsItem.mousePressEvent (self, event)
        elif event.button () == Qt.RightButton:
            self.opacityStartPosition = event.pos ()
            self.opacityAction = True
            self.grabMouse ()
            self.workingOpacity = self.opacity ()
    def mouseReleaseEvent (self, event):
        self.ungrabMouse ()

class SmallBlueCircleItem (QGraphicsEllipseItem):
    def __init__ (self, root, universe, radius, color, thickness):
        QGraphicsEllipseItem.__init__ (self)

        self.root = root
        self.radius = radius
        self.setPen (QPen (color, thickness))
        self.setPos (QPointF (0, 0))
        self.setRect (-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        self.setZValue (3)
        self.setAcceptHoverEvents (True)
        self.readyToMove = False
        #self.setToolTip ('Left click allows resizing')
        universe.scene.addItem (self)
        self.TOLERANCE = 5
    def size (self):
        return self.radius
    def setSize (self, value):
        self.radius = value
        _diameter = value * 2.0
        self.setRect (-self.radius, -self.radius, _diameter, _diameter)
    def mouseMoveEvent (self, event):
        if self.readyToMove:
            _pos = event.pos ()
            self.radius = math.sqrt (_pos.x () * _pos.x () + _pos.y () * _pos.y ())

            if self.radius > self.limit:
                self.radius = self.limit

            if self.radius < 10:
                self.radius = 10

            _diameter = self.radius * 2.0
            self.setRect (-self.radius, -self.radius, _diameter, _diameter)

            if event.pos () != self.OLD_POS:
                self.root.OFFSET = self.radius
                self.root.SCALING = self.root.TOTAL_SCALING - self.root.OFFSET
                self.root.MAX_CROSSLINK_LENGTH = 2.0 * (self.root.SCALING + self.root.OFFSET)
                self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_computeOptimalDistancesSignal)
    def mousePressEvent (self, event):
        if self.readyToMove:
            self.OLD_OFFSET = self.root.OFFSET
            self.OLD_POS = event.pos ()
            self.limit = (self.root.SCALING + self.OLD_OFFSET) * 0.95
            self.grabMouse ()
        else:
            QGraphicsItem.mousePressEvent (self, event)
    def mouseReleaseEvent (self, event):
        self.ungrabMouse ()
        QGraphicsItem.mouseReleaseEvent (self, event)
    def hoverMoveEvent (self, event):
        _pos = event.pos ()
        _distance = math.sqrt (_pos.x () * _pos.x () + _pos.y () * _pos.y ())

        if _distance > (self.radius - self.TOLERANCE / self.root.galaxy.view.netZoom):
            self.setCursor (Qt.SizeHorCursor)
            self.readyToMove = True
        else:
            self.unsetCursor ()
            self.readyToMove = False
            QGraphicsItem.hoverMoveEvent (self, event)
            self.root.galaxy.view.opaqueDisk.hoverMoveEvent (event)

class Ellipse (QObject, QGraphicsEllipseItem):
    def __init__ (self, layoutObject, root, index):
        QObject.__init__ (self)
        QGraphicsEllipseItem.__init__ (self)

        self.root = root
        self.setCacheMode (QtGui.QGraphicsItem.ItemCoordinateCache)
        self.node = self.root.nodes [index]

        self.index = index
        self.scene = layoutObject.scene
        self.layoutObject = layoutObject

        # The mouse pointer will change to this when it passes over the node
        self.setCursor (Qt.CrossCursor)

        # We want Qt to generate events whenever this item is repositioned
        # either by us or by Qt (during an animation). So we need to set
        # this magic semaphore.
        self.setFlags (QGraphicsItem.ItemSendsGeometryChanges | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIgnoresTransformations)

        self.setAcceptHoverEvents (True)
        self.iconPixmap = QPixmap (':/images/Resources/add32x32.png')
        self.label = NodeLabel (self.root, self)
        self.myChange = False
        self.setup (index)
        self.currentSelected = False
        self.scene.addItem (self)
        self.mouseLeftIsPressed = False
    def setup (self, index):
        try:
            self.node = self.root.nodes [index]
        except:
            return True

        self.index = index
        _labelVisible = (self.root.labelsCheckbox.checkState () == Qt.Checked) or self.node.special
        self.label.setText (self.node.labelText)
        self.label.setVisible (_labelVisible)
        self.label.backwash.setVisible (_labelVisible)

        if self.node.special:
            self.label.setup (self.root.nodeHighlightFontSize, self)
            self.setZValue (6)
        else:
            self.label.setup (self.root.nodeFontSize, self)
            self.setZValue (5)

        self.setNodeSize ()
        self.show ()

        if self.root.tooltipsCheckbox.checkState () == Qt.Checked:
            self.setToolTip (self.node.tipText)
        else:
            self.setToolTip ('')

        return False
    def hideSelectedNodesIncludingThisOne (self):
        self.root.hideNodes (self.root.selectionList + [self.index])
        self.root.updateSelectionsAndHideButtons ()
    def mousePressEvent (self, event):
        if event.button () == Qt.LeftButton:
            self.mouseLeftIsPressed = True
            self.dragStartTime = time.clock ()
            self.dragStartPosition = event.pos ()
            _alt = QApplication.keyboardModifiers () == Qt.AltModifier

            if _alt:
                self.currentSelected = False
                self.root.hideNodes ([self.index])
                self.root.updateSelectionsAndHideButtons ()
    def setNodeSize (self):
        _radius = self.scaleSize ()
        _diameter = _radius * 2.0
        self.setRect (-_radius, -_radius, _diameter, _diameter)
        _gradient = QRadialGradient (0, 0, _radius, -_radius, -_radius);
        #_gradient = QRadialGradient (0, 0, 0.5, -0.5, -0.5)
        _gradient.setColorAt (0, self.node.bodyColor.lighter ().lighter ())
        _gradient.setColorAt (0.5, self.node.bodyColor)
        _gradient.setColorAt (1, self.node.bodyColor.darker ().darker ())
        #_gradient.setCoordinateMode (QGradient.StretchToDeviceMode)
        self.setBrush (QBrush (_gradient))
    def setColor (self):
        self.root.setNodeColors (self.index)
        self.root.layoutType ().view.mainThread.layout ()
    def specialToggled (self):
        self.node.special = self.specialAction.isChecked ()

        if self.node.special:
            self.setZValue (6)
            self.label.show ()
            self.label.backwash.setVisible (True)
            self.label.setSize (self.root.nodeHighlightFontSize)
        else:
            _visible = self.root.labelsCheckbox.checkState () == Qt.Checked
            self.setZValue (5)
            self.label.setVisible (_visible)
            self.label.backwash.setVisible (_visible)
            self.label.setSize (self.root.nodeFontSize)
    def profileSelected (self):
        
        _profile = UniverseProfile (self.root.tss, self)
        _profile.exec_ ()
    def normalisedProfileSelected (self):
        _profile = UniverseProfile (self.root.tss, self, normalised = True)
        _profile.exec_ ()
    def forecastSelected (self):
        self.root.analysisPlot.presetForecast (self.index)
    def softCasualCheckActionSelected(self):
        _profile = CasualCheckActionSelected (self,self.index,self.root,self.root.tss, self.root.centerNode (), self.root.nodes [self.root.centerNode ()])
        _profile.exec_ ()   
    def coefficientsListSelected (self):
        _profile = CoefficientsList (self.root.tss, self.root.centerNode (), self.root.nodes [self.root.centerNode ()])
        _profile.exec_ ()
    def coefficientsProfileSelected (self):
        _profile = CoefficientsProfile (self.root.tss, self)
        _profile.exec_ ()
    def scaleSize (self):
        return self.node.radius * self.layoutObject.nodeSizeSlider.slider.value () / 255.0 
    def delete (self):
        self.layoutObject.scene.removeItem (self)
    def mouseReleaseEvent (self, event):
        self.mouseLeftIsPressed = False
        QGraphicsItem.mouseReleaseEvent (self, event)
    def mouseMoveEvent (self, event):
        if self.mouseLeftIsPressed:
            try:
                if abs ((event.pos ().x () - self.dragStartPosition.x ()) + (event.pos ().y () - self.dragStartPosition.y ())) > QApplication.startDragDistance ():
                    drag = QDrag (self.layoutObject)
                    mimeData = QMimeData ()
          
                    _specialList = self.root.selectionList [:]
        
                    if self.index in _specialList:
                        _specialList.remove (self.index)
         
                    mimeData.setText (self.root.numberListToCommaSeparatedString (_specialList + [self.index]))
            
                    drag.setMimeData (mimeData)
                    drag.setPixmap (self.iconPixmap)
                    dropAction = drag.exec_ (Qt.CopyAction)
            except:
                None
    def contextMenuEvent (self, event): # Display a contextual popup
        _menu = QMenu ()
        self.currentSelected = self.isSelected ()

        if len (self.root.selectionList) == 1:
            _title = 'Node: %s (1 node selected)' % self.node.infoText
        else:
            _title = 'Node: %s (%d nodes selected)' % (self.node.infoText, len (self.root.selectionList))

        if self.currentSelected:
            _totalSelected = len (self.root.selectionList)
        else:
            _totalSelected = len (self.root.selectionList) + 1

        _noteAction = _menu.addAction (_title)
        _menu.addSeparator ()
        
        # 'Soft Casual Check' item
        self.softCasualCheckAction = _menu.addAction ('Operator Expertise')
        QtCore.QObject.connect (self.softCasualCheckAction, QtCore.SIGNAL ('triggered ()'), self.softCasualCheckActionSelected)
        
        # 'Special' toggle
        self.specialAction = _menu.addAction ('Special')
        self.specialAction.setCheckable (True)
        self.specialAction.setChecked (self.node.special)
        QtCore.QObject.connect (self.specialAction, QtCore.SIGNAL ('triggered ()'), self.specialToggled)
        
        
        
        # 'Set color' option
        self.colorAction = _menu.addAction ('Set color')
        QtCore.QObject.connect (self.colorAction, QtCore.SIGNAL ('triggered ()'), self.setColor)

        # 'Hide' option
        self.hideAction = _menu.addAction ('Hide')
        QtCore.QObject.connect (self.hideAction, QtCore.SIGNAL ('triggered ()'), self.hideSelectedNodesIncludingThisOne)

        # 'Profile' item
        self.profileAction = _menu.addAction ('Profile')
        QtCore.QObject.connect (self.profileAction, QtCore.SIGNAL ('triggered ()'), self.profileSelected)

        # Normalised 'Profile' item
        self.normalisedProfileAction = _menu.addAction ('Normalised Profile')
        QtCore.QObject.connect (self.normalisedProfileAction, QtCore.SIGNAL ('triggered ()'), self.normalisedProfileSelected)

        # 'Coefficients Profile' item
        self.coefficientsProfileAction = _menu.addAction ('Coefficient Profile')
        QtCore.QObject.connect (self.coefficientsProfileAction, QtCore.SIGNAL ('triggered ()'), self.coefficientsProfileSelected)

        # 'Coefficients List' item
        self.coefficientsListAction = _menu.addAction ('Coefficient List')
        QtCore.QObject.connect (self.coefficientsListAction, QtCore.SIGNAL ('triggered ()'), self.coefficientsListSelected)

        # 'Forecast' item
        self.forecastAction = _menu.addAction ('Forecast')
        QtCore.QObject.connect (self.forecastAction, QtCore.SIGNAL ('triggered ()'), self.forecastSelected)
        
        

        _selectedAction = _menu.exec_ (event.screenPos ())
    def hoverEnterEvent (self, event):
        self.setZValue (7) # Temporarily raise it in front of its neighbours
        self.label.setSize (self.root.nodeHighlightFontSize)
        self.label.show ()
        self.label.backwash.setVisible (True)
        self.label.backwash.setBrush (self.root.constants.backwashHighlightColor)
        self.label.setBrush (self.root.constants.nodeTextHighlightColor)

        if self.node.index == self.root.centerNode ():
            self.realBrush = self.brush ()
            self.setBrush (self.root.constants.centerNodeHighlightColor)
    def hoverLeaveEvent (self, event):
        if self.node.special:
            self.setZValue (6)
            self.label.setSize (self.root.nodeHighlightFontSize)
        else:
            self.setZValue (5)
            self.label.setSize (self.root.nodeFontSize)

        self.label.setBrush (self.root.constants.nodeTextColor)
        self.label.backwash.setBrush (self.root.constants.backwashColor)

        if self.root.labelsCheckbox.checkState () == Qt.Unchecked:
            if not self.node.special:
                self.label.hide ()
                self.label.backwash.setVisible (False)

        try:
            if self.node.index == self.root.centerNode ():
                self.setBrush (self.realBrush)
        except:
            None
    def setSpecial (self, state):
        self.node.special = state

        if state:
            self.label.setSize (self.root.nodeHighlightFontSize)
    def itemChange (self, change, value):
        if (change == QGraphicsItem.ItemPositionChange):
            if self.myChange:
                self.myChange = False
                return self.jabberwocky
            else:
                return QGraphicsItem.itemChange (self, change, value)
        elif (change == QGraphicsItem.ItemSelectedHasChanged):
            if self.node.selectorTreeNode:
                _changesMade = False

                if self.isSelected ():
                    if self.index not in self.root.selectionList:
                        self.root.selectionList.append (self.index)
                        self.node.selectorTreeNode.setSelected (True)
                        self.root.newSelector.model.dataChanged.emit (QModelIndex (), QModelIndex ())
                        _changesMade = True
                else:
                    if self.index in self.root.selectionList:
                        self.root.selectionList.remove (self.index)
                        self.node.selectorTreeNode.setSelected (False)
                        _changesMade = True

                if _changesMade:
                    self.root.updateSelectionsAndHideButtons ()
                    self.root.layoutType ().updateStatus ()

        return QGraphicsItem.itemChange (self, change, value)
    def raiseLinks (self, links, state):
        for _link in links:
            try:
                _graphic = _link.graphic
            except:
                None
            else:
                if state:
                    _link.realPen = _graphic.pen ()
                    _link.realZ = _graphic.zValue ()
                    _graphic.setZValue (4)

                    if _graphic.coefficient < 0:
                        _color = self.root.constants.linkNegativeHighlightColor
                    else:
                        _color = self.root.constants.linkPositiveHighlightColor
                    
                    _graphic.setPen (_color)
                else:
                    try:
                        _graphic.setZValue (_link.realZ)
                        _graphic.setPen (_link.realPen)
                    except:
                        None

class RadialPosition (QObject):
    def __init__ (self, val):
        _x = val.x ()
        _y = val.y ()

        try:
            self._angle = math.atan (_y / _x)
        except:
            self._angle = math.pi / 2.0

        if _x < 0.0:
            self._angle -= math.pi

        self._intensity = math.sqrt (_x * _x + _y * _y)
    def __repr__ (self):
        return 'RadialPosition (angle = %.2f, intensity = %.1f)' % (self._angle, self._intensity)

class GalaxyEllipse (Ellipse):
    def __init__ (self, layoutObject, root, index):
        Ellipse.__init__ (self, layoutObject, root, index)

        self.root = root
        #self.radialPosition = RadialPosition (0, 0)
    def mouseDoubleClickEvent (self, event):
        # Unhighlight all nodes connected to the current center node
        self.raiseLinkedNodes (self.node.galaxy.linksIn + self.node.galaxy.linksOut, False)

        self.root.undoBuffer.push (UndoableAction (UndoableAction.CENTER, [self.root.centerNode (), self.index]))
        self.root.setCenterNode (self.index)
        self.layoutObject.rotation = QPointF (0, 0)
        self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
    def setColor (self):
        self.root.setNodeColors (self.index)
        self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_noLongerWorkingSignal)
    def rotateTo (self, to):
        self.animPos = QPropertyAnimation (self, "radialPosition")
        self.animPos.setDuration (self.root.constants.moveTime)
        self.animPos.setEasingCurve (self.root.animationTypeCombo.type)
        self.animPos.setStartValue (RadialPosition (self.node.galaxy.previousEndpoint))
        self.thisEndpoint = to
        self.animPos.setEndValue (RadialPosition (to))
        self.node.galaxy.previousEndpoint = to
        self.animPos.start ()
    def moveTo (self, to):
        self.animPos = QPropertyAnimation (self, "pos")
        self.animPos.setDuration (self.root.constants.moveTime)
        self.animPos.setEasingCurve (self.root.animationTypeCombo.type)
        self.animPos.setStartValue (self.node.galaxy.previousEndpoint)
        self.thisEndpoint = to
        self.animPos.setEndValue (to)
        self.node.galaxy.previousEndpoint = to
        self.animPos.start ()
    def itemChange (self, change, value):
        if (change == QGraphicsItem.ItemPositionHasChanged):
            for thisLink in self.node.galaxy.linksOut + self.node.galaxy.linksIn:
                thisLink.state = LinkDrawState.FIRST_VISIT # Force redraw on each call
                if thisLink.state == LinkDrawState.RESET:
                    thisLink.state = LinkDrawState.FIRST_VISIT
                elif thisLink.state == LinkDrawState.FIRST_VISIT:
                    try:
                        thisLink.graphic.redraw ()
                    except:
                        None

                    thisLink.state = LinkDrawState.RESET

            return QGraphicsItem.itemChange (self, change, value)
        else:
            return Ellipse.itemChange (self, change, value)
            #return QGraphicsItem.itemChange (self, change, value)
    def raiseLinkedNodes (self, links, state):
        for _link in links:
            if _link.sourceNodeIndex == self.index:
                _target = _link.targetNodeIndex
            else:
                _target = _link.sourceNodeIndex

            try:
                if state:
                    Ellipse.hoverEnterEvent (self.root.nodes [_target].galaxy.graphic, 0)
                else:
                    Ellipse.hoverLeaveEvent (self.root.nodes [_target].galaxy.graphic, 0)
            except:
                None
    def hoverEnterEvent (self, event):
        Ellipse.hoverEnterEvent (self, event)
        Ellipse.raiseLinks (self, self.node.galaxy.linksIn + self.node.galaxy.linksOut, True)

        if self.root.hoverLabelsCheckbox.checkState () == Qt.Checked:
            self.raiseLinkedNodes (self.node.galaxy.linksIn + self.node.galaxy.linksOut, True)
    def hoverLeaveEvent (self, event):
        Ellipse.hoverLeaveEvent (self, event)
        Ellipse.raiseLinks (self, self.node.galaxy.linksIn + self.node.galaxy.linksOut, False)

        if self.root.hoverLabelsCheckbox.checkState () == Qt.Checked:
            self.raiseLinkedNodes (self.node.galaxy.linksIn + self.node.galaxy.linksOut, False)

    ##########################################
    # Setter/getter for "RadialPosition"
    ##########################################
    def getRadialPosition (self):
        #print 'GET:', QGraphicsPixmapItem.pos (self)
        return RadialPosition (QGraphicsPixmapItem.pos (self))
    def setRadialPosition (self, val):
        #print 'PUT:', QPointF (val.intensity () * math.cos (val.alpha ()), val.intensity () * math.sin (val.alpha ()))
        QGraphicsPixmapItem.setPos (self, QPointF (val.intensity () * math.cos (val.alpha ()), val.intensity () * math.sin (val.alpha ())))

    radialPosition = Property (RadialPosition, getRadialPosition, setRadialPosition)
        
    ##########################################
    # Setter/getter for "pos"
    ##########################################
    def getPos (self):
        return QGraphicsPixmapItem.pos (self)
    def setPos (self, val):
        QGraphicsPixmapItem.setPos (self, val)

    pos = Property (QPointF, getPos, setPos)
    ##########################################

class ClusterEllipse (Ellipse):
    def __init__ (self, layoutObject, root, index):
        Ellipse.__init__ (self, layoutObject, root, index)

        self.root = root
    def mouseDoubleClickEvent (self, event):
        # Unhighlight all nodes connected to the current center node
        self.raiseLinkedNodes (self.node.cluster.linksIn + self.node.cluster.linksOut, False)

        self.root.undoBuffer.push (UndoableAction (UndoableAction.CENTER, [self.root.centerNode (), self.index]))
        self.root.setCenterNode (self.index)
        self.layoutObject.rotation = QPointF (0, 0)
        self.layoutObject.layout ()
        self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
    def moveTo (self, to):
        self.animPos = QPropertyAnimation (self, "pos")
        self.animPos.setDuration (self.root.constants.moveTime)
        self.animPos.setEasingCurve (self.root.animationTypeCombo.type)
        self.animPos.setStartValue (self.node.cluster.previousEndpoint)
        self.animPos.setEndValue (to)
        self.node.cluster.previousEndpoint = to
        self.animPos.start ()
    def itemChange (self, change, value):
        if (change == QGraphicsItem.ItemPositionHasChanged):
            for thisLink in self.node.cluster.linksOut + self.node.cluster.linksIn:
                if thisLink.state == LinkDrawState.RESET:
                    thisLink.state = LinkDrawState.FIRST_VISIT
                elif thisLink.state == LinkDrawState.FIRST_VISIT:
                    try:
                        thisLink.graphic.redraw ()
                    except:
                        None

                    thisLink.state = LinkDrawState.RESET

            return QGraphicsItem.itemChange (self, change, value)
        else:
            return Ellipse.itemChange (self, change, value)
    def raiseLinkedNodes (self, links, state):
        for _link in links:
            if _link.sourceNodeIndex == self.index:
                _target = _link.targetNodeIndex
            else:
                _target = _link.sourceNodeIndex

            try:
                if state:
                    Ellipse.hoverEnterEvent (self.root.nodes [_target].cluster.graphic, 0)
                else:
                    Ellipse.hoverLeaveEvent (self.root.nodes [_target].cluster.graphic, 0)
            except:
                None
    def hoverEnterEvent (self, event):
        Ellipse.hoverEnterEvent (self, event)
        Ellipse.raiseLinks (self, self.node.cluster.linksIn + self.node.cluster.linksOut, True)

        if self.root.hoverLabelsCheckbox.checkState () == Qt.Checked:
            self.raiseLinkedNodes (self.node.cluster.linksIn + self.node.cluster.linksOut, True)
    def hoverLeaveEvent (self, event):
        Ellipse.hoverLeaveEvent (self, event)
        Ellipse.raiseLinks (self, self.node.cluster.linksIn + self.node.cluster.linksOut, False)

        if self.root.hoverLabelsCheckbox.checkState () == Qt.Checked:
            self.raiseLinkedNodes (self.node.cluster.linksIn + self.node.cluster.linksOut, False)

    ##########################################
    # Setter/getter for "pos"
    ##########################################
    def getPos (self):
        return QGraphicsPixmapItem.pos (self)
    def setPos (self, val):
        QGraphicsPixmapItem.setPos (self, val)

    pos = Property (QPointF, getPos, setPos)
    ##########################################

class SocialEllipse (Ellipse):
    def __init__ (self, layoutObject, root, index):
        Ellipse.__init__ (self, layoutObject, root, index)

        self.root = root
    def mouseDoubleClickEvent (self, event):
        # Unhighlight all nodes connected to the current center node
        self.raiseLinkedNodes (self.node.social.linksIn + self.node.social.linksOut, False)

        self.root.undoBuffer.push (UndoableAction (UndoableAction.CENTER, [self.root.centerNode (), self.index]))
        self.root.setCenterNode (self.index)
        self.layoutObject.rotation = QPointF (0, 0)
        self.layoutObject.layout ()
        self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
    def moveTo (self, to, directMove = False):
        if directMove:
            self.setPos (to)
        else:
            self.animPos = QPropertyAnimation (self, "pos")
            self.animPos.setDuration (self.root.constants.moveTime)
            self.animPos.setEasingCurve (self.root.animationTypeCombo.type)
            self.animPos.setStartValue (self.node.social.previousEndpoint)
            self.animPos.setEndValue (to)
            self.animPos.start ()

        self.node.social.previousEndpoint = to
    def itemChange (self, change, value):
        if (change == QGraphicsItem.ItemPositionHasChanged):
            for thisLink in self.node.social.linksOut + self.node.social.linksIn:
                if thisLink.state == LinkDrawState.RESET:
                    thisLink.state = LinkDrawState.FIRST_VISIT
                elif thisLink.state == LinkDrawState.FIRST_VISIT:
                    try:
                        thisLink.graphic.redraw ()
                    except:
                        None

                    thisLink.state = LinkDrawState.RESET

            return QGraphicsItem.itemChange (self, change, value)
        else:
            return Ellipse.itemChange (self, change, value)
    def raiseLinkedNodes (self, links, state):
        for _link in links:
            try:
                if state:
                    Ellipse.hoverEnterEvent (self.root.nodes [_link.index].social.graphic, 0)
                else:
                    Ellipse.hoverLeaveEvent (self.root.nodes [_link.index].social.graphic, 0)
            except:
                None
    def hoverEnterEvent (self, event):
        Ellipse.hoverEnterEvent (self, event)
        Ellipse.raiseLinks (self, self.root.nodes [self.index].socialLinks, True)

        if self.root.hoverLabelsCheckbox.checkState () == Qt.Checked:
            self.raiseLinkedNodes (self.root.nodes [self.index].socialLinks, True)
    def hoverLeaveEvent (self, event):
        Ellipse.hoverLeaveEvent (self, event)
        Ellipse.raiseLinks (self, self.root.nodes [self.index].socialLinks, False)

        if self.root.hoverLabelsCheckbox.checkState () == Qt.Checked:
            self.raiseLinkedNodes (self.root.nodes [self.index].socialLinks, False)

    ##########################################
    # Setter/getter for "pos"
    ##########################################
    def getPos (self):
        return QGraphicsPixmapItem.pos (self)
    def setPos (self, val):
        QGraphicsPixmapItem.setPos (self, val)

    pos = Property (QPointF, getPos, setPos)
    ##########################################

class Universe (QGraphicsView):
    def __init__ (self, root):
        QGraphicsView.__init__(self)
        #self.setViewportUpdateMode (QGraphicsView.FullViewportUpdate)
        self.setCacheMode (QGraphicsView.CacheBackground)
        self.setObjectName ('universe')
        self.root = root
        self.scene = QGraphicsScene ()
        self.setScene (self.scene)
        self.setVerticalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
        self.setDragMode (QGraphicsView.ScrollHandDrag)
        self.zoomFactor = 1.2
        self.numScheduledScalings = 0 # Used for mousewheel zoom
        self.setRenderHints (QPainter.Antialiasing)
        self.netZoom = 1.0
        self.previousLevels = 0
        self.previousLevelSpan = self.root.TOTAL_SCALING
        _size = self.root.TOTAL_SCALING * 2 + 200
        _halfSize = _size / 2
        self.setSceneRect (-_halfSize, -_halfSize, _size, _size)
        #self.centerOn (0, 0)
        self.setResizeAnchor (QGraphicsView.AnchorUnderMouse)
        self.animationCount = 0
        self.terminals = 0
        self.angle = 0 # scratchpad for use by Leaf.positionNode
        self.spacing = 0 # scratchpad for use by Leaf.positionNode

        # 3D transformation
        self.rotating = False
        self.rotation = QPointF (0, 0)
        self.rotationEnabled = getArgv ('enable_rotation')
        #self.COUNT = 0
    #def viewportEvent (self, event):
    #    if event.type () == QEvent.Paint:
    #        print '%4d Paint' % (self.COUNT)
    #        self.COUNT += 1
    #        event.accept ()
    #    return QGraphicsView.viewportEvent (self, event)
    def adjustLinkCutoff (self, value):
        self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinks)
    def transform (self, x, y):
        _xRotation = x
        _yRotation = y
        _zRotation = 0
        _transform = self.root.layoutType ().view.xf
        _transform.setup (0, 0, 0, _xRotation, _yRotation, _zRotation)

        for _circle in self.root.layoutType ().view.circles:
            _radius = _circle.radius ()
            _diameter = _radius * 2.0
            _x, _y, _z = _transform.transform (_circle.x (), _circle.y (), 0)
            _rx, _ry, _rz = _transform.transform (_radius, _radius, 0)
            _circle.graphic ().setRect (_x - _radius, _y - _radius, _diameter, _diameter)

        return _transform
    def mousePressEvent (self, event):
        _alt = (QApplication.keyboardModifiers () == Qt.AltModifier) and (event.button () == Qt.LeftButton)
        
        if self.rotationEnabled and _alt:
            self.rotating = True
            self.rotationOrigin = event.posF ()

        QGraphicsView.mousePressEvent (self, event)
    def mouseReleaseEvent (self, event):
        if self.rotating:
            self.rotating = False
        else:
            QGraphicsView.mouseReleaseEvent (self, event)
    def mouseMoveEvent (self, event):
        if self.rotating:
            self.rotation += (event.posF () - self.rotationOrigin) / 100.0
            self.rotationOrigin = event.posF ()
            self.transform (self.rotation.y (), self.rotation.x ())
        else:
            QGraphicsView.mouseMoveEvent (self, event)
    def removeAllGraphicsItemsFromScene (self):
        _scene = self.scene

        for _el in _scene.items ():
            _scene.removeItem (_el)

            if isinstance (_el, Ellipse):
                # Ensure the node is not selected when we throw it away. Because there's a callback attached to the
                # changing of the selected state that screws up our selections and it will rear its ugly head when
                # the node graphic is recycled.
                if _el.isSelected ():
                    _save = self.selectionList [:]
                    _el.setSelected (False)
                    self.selectionList = _save
            elif isinstance (_el, LinkGraphic):
                None
            elif isinstance (_el, Arrowhead):
                None
            elif isinstance (_el, Circle):
                self.root.circleStore.append (_el)
            elif isinstance (_el, QGraphicsRectItem):
                None
            elif isinstance (_el, NodeLabel):
                None
            elif isinstance (_el, OpaqueDisk):
                None
            elif isinstance (_el, SmallBlueCircleItem):
                None
            elif isinstance (_el, ClusterCircle):
                pass
            elif isinstance (_el, QGraphicsSimpleTextItem): # This should be WaitMessage but isinstance doesn't seem to work.
                #_el.hide ()
                _scene.addItem (_el)
            else:
                None
    def busyCursor (self, state):
        if state:
            self.viewport ().setCursor (Qt.WaitCursor)
            self.setCursor (Qt.WaitCursor)
            self.update ()
        else:
            self.viewport ().unsetCursor ()
            self.unsetCursor ()
            self.update ()
    def wheelEvent (self, event):
        self.numDegrees = event.delta () / 5000.0
        self.numSteps = self.numDegrees / 15.0 # see QWheelEvent documentation
        self.numScheduledScalings += self.numSteps

        # if user moves the wheel in another direction, we must reset previously scheduled scalings
        if (self.numScheduledScalings * self.numSteps) < 0:
            self.numScheduledScalings = self.numSteps

        self.anim = QTimeLine (350, self)
        self.anim.setUpdateInterval (20)
        QObject.connect (self.anim, SIGNAL ('valueChanged (qreal)'), self.scalingTime)
        self.anim.start ()
    def scalingTime (self):
        self.factor = 1.0 + self.numScheduledScalings
        self.scale (self.factor, self.factor)
        _netZoomAfter = self.netZoom * self.factor
        #self.centerOn (self.mousePosition * (1 - _netZoomAfter/self.netZoom))
        self.netZoom = _netZoomAfter
    def mouseMoveEvent (self, event):
        self.mousePosition = self.mapToScene (event.pos ())
        QGraphicsView.mouseMoveEvent (self, event)
    def setBackgroundPixmap (self, path):
        self.setBackgroundBrush (QBrush (QPixmap (path)))

class BusyIndicator (QGraphicsRectItem):
    def __init__ (self, root, parent):
        QGraphicsRectItem.__init__ (self, root.TOTAL_SCALING, -root.TOTAL_SCALING, -20.0, 20.0)
        self.root = root
        self.parent = parent
        self.setBrush (self.root.constants.busyIndicatorBrush)
        self.setPen (self.root.constants.busyIndicatorPen)
        self.hide ()
        parent.scene.addItem (self)
    def setState (self, state):
        self.setVisible (state)
        self.parent.update ()
        self.root.application.processEvents ()

class LargeBlueCircle (Circle):
    def __init__ (self, root, layoutWidget, color, diameter, thickness):
        Circle.__init__ (self, root, layoutWidget, 0, 0, color, diameter, thickness)
        self.setAcceptHoverEvents (True)
        self.setZValue (0)
        self.readyToMove = False
        self.radius = diameter / 2.0
        self.alpha = 0.0
        self.alphaOffset = 0.0
        self.rotating = False
        self.rotation = 0.0
    def mousePressEvent (self, event):
        if self.readyToMove:
            self.rotating = True

            _pos = event.pos ()
            _x = _pos.x ()
            _y = _pos.y ()

            try:
                self.alphaOffset = math.atan (_y / _x)
            except: 
                self.alphaOffset = math.pi / 2.0

            if _x < 0.0:
                self.alphaOffset -= math.pi
        else:
            Circle.mousePressEvent (self, event)
    def mouseReleaseEvent (self, event):
        if self.rotating:
            self.rotating = False
            self.rotation += self.alpha - self.alphaOffset
        else:
            Circle.mouseReleaseEvent (self, event)
    def mouseMoveEvent (self, event):
        if self.rotating:
            _pos = event.pos ()
            _x = _pos.x ()
            _y = _pos.y ()

            try:
                self.alpha = math.atan (_y / _x)
            except: 
                self.alpha = math.pi / 2.0

            if _x < 0.0:
                self.alpha -= math.pi

            self.root.galaxy.view.simpleRotate (self.rotation + (self.alpha - self.alphaOffset))
        else:
            Circle.mouseMoveEvent (self, event)
    def hoverMoveEvent (self, event):
        _pos = event.pos ()
        _distance = math.sqrt (_pos.x () * _pos.x () + _pos.y () * _pos.y ())

        if _distance > (self.radius * .95):
            self.setCursor (Qt.SizeVerCursor)
            self.readyToMove = True
        else:
            self.unsetCursor ()
            self.readyToMove = False
            Circle.hoverMoveEvent (self, event)

class GalaxyUniverse (Universe):
    def __init__(self, root):
        Universe.__init__ (self, root)

        self.smallBlueCircle = SmallBlueCircleItem (self.root, self, self.root.OFFSET, self.root.constants.galaxyBlueCircleColor, 2)
        self.largeBlueCircle = LargeBlueCircle (self.root, self, self.root.constants.galaxyBlueCircleColor, 2.0 * self.root.TOTAL_SCALING, 2)
        self.opaqueDisk = OpaqueDisk (self.root, self, self.root.OFFSET + self.root.SCALING / 2, 255)
        self.busyIndicator = BusyIndicator (self.root, self)

        self.rotation = QPointF (0, 0)
        self.links = []
        self.circles = []
        self.xf = Transform ()
        self.visibleNodeDetails = VisibleNodeDetails ()
        display = QtCore.Signal ()
        QtCore.QObject.connect (self, QtCore.SIGNAL ('display ()'), self.doDisplay)

        self.mainThread = GalaxyLayout (self.root)
        self.lastTimeIWasCalled = time.time ()
        self.lastTimeDisplayed = time.time ()
    def adjustCentrifuge (self, value):
        self.doLayout (self.root.galaxyLayoutThread.task_makeLinksSignal)
    def adjustCentralLinkCutoff (self, value):
        self.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
    def adjustOuterLinkCutoff (self, value):
        self.doLayout (self.root.galaxyLayoutThread.task_cutoffOuterLinksSignal)    
    def adjustCrosslinkCutoff (self, value):
        self.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
    def doDisplay (self):
        if self.root.galaxyLayoutThread.phase == self.root.galaxyLayoutThread.task_end:
            self.root.galaxy.view.mainThread.display ()
            self.showNodes ()
            self.busyIndicator.setState (False)
            self.root.updateSelectionsAndHideButtons ()
            return

        _elapsed = time.time () - self.lastTimeDisplayed
        self.root.galaxyLayoutThread.step.emit ()
        self.lastTimeIWasCalled = time.time ()
        _phaseIndex = self.root.galaxyLayoutThread.phases.index (self.root.galaxyLayoutThread.phase)
        _minimumDisplayablePhaseIndex = self.root.galaxyLayoutThread.phases.index (self.root.galaxyLayoutThread.task_setupAdjustAllNodes)

        if getArgv ('display_only_when_complete'):
            if _phaseIndex == (len (self.root.galaxyLayoutThread.phases) - 1):
                #print 'Time since last display:', _elapsed, '=> displaying'
                self.root.galaxy.view.mainThread.display ()
                self.lastTimeDisplayed = time.time ()
                self.showNodes ()
                self.root.application.processEvents ()
        else:
            if (_elapsed > 5.0) and (_phaseIndex >= _minimumDisplayablePhaseIndex):
                #print 'Time since last display:', _elapsed, '=> displaying'
                self.root.galaxy.view.mainThread.display ()
                self.lastTimeDisplayed = time.time ()
                self.showNodes ()
                self.root.application.processEvents ()
    def redrawAllArrowheads (self):
        for _link in self.links:
            try:
                _link.graphic.redrawArrowheads ()
            except:
                None
    def adjustNodeSize (self, value):
        for _nodeIndex in self.visibleNodeDetails.nodeList ():
            try:
                self.root.nodes [_nodeIndex].galaxy.graphic.setNodeSize ()
            except:
                None

        self.redrawAllArrowheads ()
    def doLayout (self, signal):
        if self.root.db:
            self.root.galaxyLayoutThread.interruptRequested = True
            self.busyIndicator.setState (True)
            self.root.galaxy.view.largeBlueCircle.rotation = 0.0
            signal.emit ()
    def toggleNodeTooltips (self, state):
        for _node in self.root.nodes:
            try:
                _graphic =_node.galaxy.graphic

                if state:
                    _graphic.setToolTip (_node.tipText)
                else:
                    _graphic.setToolTip ('')
            except:
                continue
    def toggleLinkTooltips (self, state):
        for _link in self.root.galaxy.view.links:
            try:
                _graphic =_link.graphic

                if state:
                    _graphic.setToolTip ('%s:%s: coefficient => %.2f (%.2f)' % (_graphic.sourceNode.labelText, _graphic.targetNode.labelText,
                                    _graphic.coefficient, _graphic.secondaryCoefficient))
                else:
                    _graphic.setToolTip ('')
            except:
                continue
    def simpleRotate (self, z):
        _xRotation = 0
        _yRotation = 0
        _zRotation = -z
        _transform = self.root.layoutType ().view.xf
        _transform.setup (0, 0, 0, _xRotation, _yRotation, _zRotation)

        for _index in self.visibleNodeDetails.nodeList ():
            _p = self.visibleNodeDetails.position (_index)
            _x, _y, _z = _transform.transform (_p.x (), _p.y (), 0)
            _node = self.root.nodes [_index]
            _point = QPointF (_x, _y)
            _node.galaxy.graphic.setPos (_point)
            _node.galaxy.previousEndpoint = _point
    def transform (self, x, y):
        _transform = Universe.transform (self, x, y)

        for _index in self.visibleNodeDetails.nodeList ():
            _p = self.visibleNodeDetails.position (_index)
            _x, _y, _z = _transform.transform (_p.x (), _p.y (), 0)
            _node = self.root.nodes [_index]
            _point = QPointF (_x, _y)
            _node.galaxy.graphic.setPos (_point)
            _node.galaxy.previousEndpoint = _point
    def showNodes (self):
        for _nodeIndex in self.visibleNodeDetails.nodeList ():
            _node = self.root.nodes [_nodeIndex]

            if not _node.hiding:
                _pos = self.visibleNodeDetails.position (_nodeIndex)
                _x, _y, _z = self.xf.transform (_pos.x (), _pos.y (), 0)

                try:
                    _node.galaxy.graphic.show ()
                    _node.galaxy.graphic.moveTo (QPointF (_x, _y))
                except:
                    None
    def scalingTime (self):
        Universe.scalingTime (self)
        self.redrawAllArrowheads ()
    def setLinkStackingOrder (self):
        # set the stacking order of all edges to 1 (they will be hidden behind the central disk)
        for _link in self.galaxy.links:
            _link.setZValue (1)
            _link.toArrowhead.setZValue (1)
            _link.fromArrowhead.setZValue (1)

        # Every link that connects to the central node should have a stacking order of 4
        _node = self.nodes [self.centerNode ()]

        for _link in _node.linksOut + _node.linksIn:
            _link.setZValue (4)
            _link.toArrowhead.setZValue (4)
            _link.fromArrowhead.setZValue (4)
    def makeCircle (self, root, x, y, color, diameter, thickness):
        if len (self.root.circleStore):
            _graphic = self.root.circleStore.pop ()
            _graphic.setup (x, y, color, diameter, thickness)
        else:
            _graphic = Circle (root, self, x, y, color, diameter, thickness)

        return _graphic

class ClusterUniverse (Universe):
    def __init__(self, root):
        Universe.__init__ (self, root)

        self.links = []
        self.circles = []
        self.rotation = QPointF (0, 0)
        self.xf = Transform ()
        self.visibleNodeDetails = VisibleNodeDetails ()
        self.mainThread = ClusterLayout (self.root)
        self.selectionList = []
        
    def adjustNodeSize (self, value):
        for _nodeIndex in self.visibleNodeDetails.nodeList ():
            try:
                self.root.nodes [_nodeIndex].cluster.graphic.setNodeSize ()
            except:
                None
    def toggleNodeTooltips (self, state):
        for _node in self.root.nodes:
            try:
                _graphic =_node.cluster.graphic

                if state:
                    _graphic.setToolTip (_node.tipText)
                else:
                    _graphic.setToolTip ('')
            except:
                continue
    def toggleLinkTooltips (self, state):
        for _link in self.root.cluster.view.links:
            try:
                _graphic =_link.graphic

                if state:
                    _graphic.setToolTip ('%s:%s: coefficient => %.2f' % (_graphic.sourceNode.labelText, _graphic.targetNode.labelText, _graphic.coefficient))
                else:
                    _graphic.setToolTip ('')
            except:
                continue
    def realizeLinks (self, cosmetic):
        for _link in self.links:
            _link.graphic = self.makeLink (self.root.nodes [_link.sourceNodeIndex], self.root.nodes [_link.targetNodeIndex], _link.coefficient, _link.maxCoefficient, cosmetic)
            _link.graphic.setZValue (_link.zValue)

        self.root.adjustOpacity (self.root.layoutType ().view.linkOpacitySlider.slider.value ())
    def transform (self, x, y):
        _transform = Universe.transform (self, x, y)

        for _index in self.visibleNodeDetails.nodeList ():
            _p = self.visibleNodeDetails.position (_index)
            _x, _y, _z = _transform.transform (_p.x (), _p.y (), 0)
            _node = self.root.nodes [_index]
            _point = QPointF (_x, _y)
            _node.cluster.graphic.setPos (_point)
            _node.cluster.previousEndpoint = _point
    def makeLink (self, sourceNode, targetNode, coefficient, maxCoefficient, cosmetic):
        if len (self.root.linkStore):
            _graphic = self.root.linkStore.pop ()
            _graphic.setup (sourceNode, targetNode, coefficient, maxCoefficient, cosmetic)
        else:
            _graphic = ClusterLinkGraphic (self.root, self, sourceNode, targetNode, coefficient, maxCoefficient, cosmetic)

        if self.root.tooltipsCheckbox.checkState () == Qt.Checked:
            _graphic.setToolTip ('%s:%s: coefficientt => %.2f' % (sourceNode.labelText, targetNode.labelText, coefficient))
        else:
            _graphic.setToolTip ('')

        return _graphic
    def addLink (self, sourceNodeIndex, targetNodeIndex, coefficient, maxCoefficient):
        _link = ClusterLink (self.root, sourceNodeIndex, targetNodeIndex, coefficient, coefficient, maxCoefficient)
        self.links.append (_link)
        return _link
    def realizeNodes (self, visibleNodeList, savedSelectionList):
        for _nodeIndex in visibleNodeList:
            _node = self.root.nodes [_nodeIndex]

            if len (self.root.nodeStore):
                _node.cluster.graphic = self.root.nodeStore.pop ()
                _node.cluster.graphic.setup (_nodeIndex)
            else:
                _node.cluster.graphic = ClusterEllipse (self, self.root, _nodeIndex)
                _node.cluster.graphic.setSelected (_node.index in savedSelectionList)

            if _nodeIndex in self.root.selectionList:
                _node.cluster.graphic.setSelected (True)
    def layout (self):
        self.busyCursor (True)

        # Ensure the layout thread is stopped before we kick off another
        self.root.clusterLayoutThread.interrupt ()
        self.root.clusterLayoutThread.wait ()

        self.root.cluster.view.mainThread.layout ()
        self.busyCursor (False)
    def showNodes (self):
        for _nodeIndex in self.visibleNodeDetails.nodeList ():
            _node = self.root.nodes [_nodeIndex]

            if not _node.hiding:
                try:
                    _node.cluster.graphic.show ()
                    _pos = self.visibleNodeDetails.position (_nodeIndex)
                    _x, _y, _z = self.xf.transform (_pos.x (), _pos.y (), 0)
                    _node.cluster.graphic.moveTo (QPointF (_x, _y))
                except:
                    None
    def scalingTime (self):
        Universe.scalingTime (self)
    def makeCircle (self, root, x, y, color, diameter, thickness):
        if len (self.root.circleStore):
            _graphic = self.root.circleStore.pop ()
            _graphic.setup (x, y, color, diameter, thickness)
        else:
            _graphic = Circle (root, self, x, y, color, diameter, thickness)

        return _graphic
    def newfun(self):
        print 'hii' 

class SocialUniverse (Universe):
    def __init__(self, root):
        Universe.__init__ (self, root)

        self.rotation = QPointF (0, 0)
        self.links = []
        self.circles = []
        self.xf = Transform ()
        self.visibleNodeDetails = VisibleNodeDetails ()
        self.mainThread = SocialLayout (self.root)
        self.selectionList = []
    def redrawAllArrowheads (self):
        for _link in self.links:
            try:
                _link.graphic.redrawArrowheads ()
            except:
                None
    def adjustNodeSize (self, value):
        for _nodeIndex in self.visibleNodeDetails.nodeList ():
            try:
                self.root.nodes [_nodeIndex].social.graphic.setNodeSize ()
            except:
                None

        self.redrawAllArrowheads ()
    def toggleNodeTooltips (self, state):
        for _node in self.root.nodes:
            try:
                _graphic =_node.social.graphic

                if state:
                    _graphic.setToolTip (_node.tipText)
                else:
                    _graphic.setToolTip ('')
            except:
                continue
    def toggleLinkTooltips (self, state):
        for _link in self.root.social.view.links:
            try:
                _graphic =_link.graphic

                if state:
                    _graphic.setToolTip ('%s->%s: coefficientty => %.2f' % (_graphic.sourceNode.labelText, _graphic.targetNode.labelText, _graphic.coefficient))
                else:
                    _graphic.setToolTip ('')
            except:
                continue
    def realizeLinks (self, cosmetic):
        for _link in self.links:
            _link.graphic = self.makeLink (self.root.nodes [_link.sourceNodeIndex], self.root.nodes [_link.targetNodeIndex], _link.coefficient, _link.maxCoefficient, cosmetic)
            _link.graphic.setZValue (_link.zValue)

        self.root.adjustOpacity (self.root.layoutType ().view.linkOpacitySlider.slider.value ())
    def transform (self, x, y):
        _transform = Universe.transform (self, x, y)

        for _index in self.visibleNodeDetails.nodeList ():
            _p = self.visibleNodeDetails.position (_index)
            _x, _y, _z = _transform.transform (_p.x (), _p.y (), 0)
            _node = self.root.nodes [_index]
            _point = QPointF (_x, _y)
            _node.social.graphic.setPos (_point)
            _node.social.previousEndpoint = _point
    def makeLink (self, sourceNode, targetNode, coefficient, maxCoefficient, cosmetic):
        if len (self.root.linkStore):
            _graphic = self.root.linkStore.pop ()
            _graphic.setup (sourceNode, targetNode, coefficient, maxCoefficient, cosmetic)
        else:
            _graphic = SocialLinkGraphic (self.root, self, sourceNode, targetNode, coefficient, maxCoefficient, cosmetic)

        if self.root.tooltipsCheckbox.checkState () == Qt.Checked:
            _graphic.setToolTip ('%s:%s: coefficient => %.2f' % (sourceNode.labelText, targetNode.labelText, coefficient))
        else:
            _graphic.setToolTip ('')

        return _graphic
    def addLink (self, sourceNodeIndex, targetNodeIndex, coefficient, maxCoefficient):
        _link = SocialLink (self.root, sourceNodeIndex, targetNodeIndex, coefficient, coefficient, maxCoefficient)
        self.links.append (_link)
        return _link
    def realizeNodes (self, visibleNodeList, savedSelectionList):
        for _nodeIndex in visibleNodeList:
            _node = self.root.nodes [_nodeIndex]

            if len (self.root.nodeStore):
                _node.social.graphic = self.root.nodeStore.pop ()
                _node.social.graphic.setup (_nodeIndex)
            else:
                _node.social.graphic = SocialEllipse (self, self.root, _nodeIndex)
                _node.social.graphic.setSelected (_node.index in savedSelectionList)

            if _nodeIndex in self.root.selectionList:
                _node.social.graphic.setSelected (True)
    def layout (self):
        self.busyCursor (True)

        # Ensure the layout thread is stopped before we kick off another
        self.root.socialLayoutThread.interrupt ()
        self.root.socialLayoutThread.wait ()

        self.root.social.view.mainThread.layout ()
        self.busyCursor (False)
    def showNodes (self):
        _directMove = len (self.visibleNodeDetails.nodeList ()) > 400

        for _nodeIndex in self.visibleNodeDetails.nodeList ():
            _node = self.root.nodes [_nodeIndex]

            if not _node.hiding:
                try:
                    _node.social.graphic.show ()
                    _pos = self.visibleNodeDetails.position (_nodeIndex)
                    _x, _y, _z = self.xf.transform (_pos.x (), _pos.y (), 0)
                    _node.social.graphic.moveTo (QPointF (_x, _y), _directMove)
                    _node.social.graphic.itemChange (QGraphicsItem.ItemPositionHasChanged, 0)
                except:
                    pass
    def scalingTime (self):
        Universe.scalingTime (self)
        self.redrawAllArrowheads ()
    def makeCircle (self, root, x, y, color, diameter, thickness):
        if len (self.root.circleStore):
            _graphic = self.root.circleStore.pop ()
            _graphic.setup (x, y, color, diameter, thickness)
        else:
            _graphic = Circle (root, self, x, y, color, diameter, thickness)

        return _graphic

class ViewLayout (QVBoxLayout):
    def __init__ (self, root):
        QVBoxLayout.__init__ (self)
        self.root = root

        self.ancestor = root

        # Add the status line
        self.statusLine = QLabel ('No data...')
        self.statusLine.setMinimumWidth (100) # Otherwise it forces the Universe view to be large
        self.addWidget (self.statusLine)
        self.statusLine.setSizePolicy (QSizePolicy.Preferred, QSizePolicy.Preferred)
        
class Galaxy (QWidget):
    def __init__ (self, root):
        QWidget.__init__ (self)
        self.root = root

        self.panel = ViewLayout (self.root)
        self.setLayout (self.panel)
        self.view = GalaxyUniverse (self.root)
        self.panel.insertWidget (0, self.view)
        _hbox = QHBoxLayout ()
        self.panel.insertLayout (1, _hbox)
        _dumpAllButton = QPushButton ('Print All Nodes')
        _hbox.addWidget (_dumpAllButton)
        QtCore.QObject.connect (_dumpAllButton, QtCore.SIGNAL ('clicked ()'), self.dumpAll)
        _dumpVisibleButton = QPushButton ('Print Visible Nodes')
        _hbox.addWidget (_dumpVisibleButton)
        QtCore.QObject.connect (_dumpVisibleButton, QtCore.SIGNAL ('clicked ()'), self.dumpVisible)
        self.updateStatus ()
    def dumpVisible (self):
        self.dump (visibleOnly = True)
    def dumpAll (self):
        self.dump (visibleOnly = False)
    def dump (self, visibleOnly):
        _textHeight = 200
        _table = self.makeTableForDump (self.root.centerNode (), visibleOnly)
        _table = sorted (_table, key = lambda _row: _row [1], reverse = True)

        self.root.galaxy.view.setUpdatesEnabled (False)
        self.view.setBackgroundBrush (QBrush (QColor ('white')))
        self.root.galaxy.view.setUpdatesEnabled (True)
        self.view.opaqueDisk.setBrush (QColor (255, 255, 255, self.view.opaqueDisk.alpha))
        self.root.application.processEvents ()
        _pixmap = QPixmap.grabWindow (self.view.winId ())
        _printer = QPrinter (QPrinter.HighResolution)
        #_printer.setOutputFileName ("/home/andy/Desktop/centrifuge.pdf")

        _xscale = 1.0 * _printer.pageRect ().width () / _pixmap.width ()
        _yscale = 1.0 * _printer.pageRect ().height () / _pixmap.height ()
        _scale = min (_xscale, _yscale)

        _dialog = QPrintDialog (_printer)
        _dialog.setWindowTitle ("Print Centrifuge State")

        self.root.galaxy.view.setUpdatesEnabled (False)
        self.view.setBackgroundBrush (QBrush (QColor ('black')))
        self.root.galaxy.view.setUpdatesEnabled (True)
        self.view.opaqueDisk.setBrush (QColor (0, 0 , 0, self.view.opaqueDisk.alpha))
        self.root.application.processEvents ()

        if _dialog.exec_ () != QDialog.Accepted:
            return

        _painter = QPainter ()
        _painter.begin (_printer)
        _painter.scale (_scale, _scale)
        _painter.drawPixmap (0, 0, _pixmap)
        _painter.setPen (Qt.black)
        _painter.setFont (QFont ("Courier", 12))
        _painter.scale (1 / _scale, 1 / _scale)
        _offset = 200 + _pixmap.height () * _scale

        _text = '%50.50s  (Centre Node)' % (_table [0] [4])
        _painter.drawText (QPointF (0, _offset), _text)
        _offset += _textHeight

        _text = '' # '                                         Node Name  Coefficients'
        _painter.drawText (QPointF (0, _offset), _text)
        _offset += _textHeight

        for _row in _table [1:]:
            _text = '%50.50s  ' % (_row [4])

            try:
                _text += '%+.2f ' % (_row [2])
            except:
                _text += '      '

            try:
                _text += '%+.2f' % (_row [3])
            except:
                pass

            _painter.drawText (QPointF (0, _offset), _text)
            _offset += _textHeight

            if _offset >  _printer.pageRect ().height ():
                _offset = 0
                _printer.newPage ()

        _painter.end ()
    def makeTableForDump (self, centralNodeId, visibleOnly = True):
        #_columns = ['Index', 'Absolute Large Coefficient', 'Large Coefficient', 'Small Coefficient']
        _centralNode = self.root.nodes [centralNodeId]
        _coefficientMatrix = self.root.cm.coeffs
        _visibleCount = 0
        _table = []

        for i, _node in enumerate (self.root.nodes):
            if not visibleOnly or not _node.hiding:
                _c1 = None if centralNodeId not in _coefficientMatrix [i] else _coefficientMatrix [i] [centralNodeId]
                _c2 = None if i not in _coefficientMatrix [centralNodeId] else _coefficientMatrix [centralNodeId] [i]
                _table.append (self.makeVectorForDump (i, centralNodeId, _c1, _c2, _node.labelText))
                _visibleCount += 1

        return _table
    def makeVectorForDump (self, i, centralNodeId, c1, c2, label):
        if i == centralNodeId:
            return [i, 1e99, None, None, label]
        elif c1 == None and c2 == None:
            return [i, None, None, None, label]
        elif c1 == None:
            return [i, abs (c2), c2, None, label]
        elif c2 == None:
            return [i, abs (c1), c1, None, label]
        else:
            if abs (c1) > abs (c2):
                return [i, abs (c1), c1, c2, label]
            else:
                return [i, abs (c2), c2, c1, label]
    def updateStatus (self):
        try:
            if self.root.linksCheckbox.checkState () == QtCore.Qt.Checked:
                _numberOfLinks = len (self.root.galaxy.view.links)
            else:
                _numberOfLinks = 0

            self.panel.statusLine.setText (
                '%s (%s): %d of %d nodes selected, %d visible. %d link%s potentially visible' \
                 % (self.root.bcFiles.databaseFilename, self.root.tss.details (), len (self.root.selectionList), self.root.N,
                self.root.galaxy.view.visibleNodeDetails.nodeListLength (), _numberOfLinks, '' if _numberOfLinks == 1 else 's'))
        except AttributeError:
            self.panel.statusLine.setText ('No data...')

class Cluster (QWidget):
    def __init__ (self, root):
        QWidget.__init__ (self)
        self.root = root

        self.panel = ViewLayout (self.root)
        self.setLayout (self.panel)
        self.view = ClusterUniverse (self.root)
        self.panel.insertWidget (0, self.view)
        self.updateStatus ()
    def updateStatus (self):
        try:
            self.panel.statusLine.setText (
                '%s (%s): %d of %d nodes selected, %d visible.' \
                 % (self.root.bcFiles.databaseFilename, self.root.tss.details (), len (self.root.selectionList), self.root.N,
                self.root.cluster.view.visibleNodeDetails.nodeListLength ()))
        except AttributeError:
            self.panel.statusLine.setText ('No data...')

class Social (QWidget):
    def __init__ (self, root):
        QWidget.__init__ (self)
        self.root = root

        self.panel = ViewLayout (self.root)
        self.setLayout (self.panel)
        self.view = SocialUniverse (self.root)
        self.panel.insertWidget (0, self.view)
        self.updateStatus ()
    def updateStatus (self):
        try:
            self.panel.statusLine.setText (
                '%s (%s): %d of %d nodes selected, %d visible.' \
                 % (self.root.bcFiles.databaseFilename, self.root.tss.details (), len (self.root.selectionList), self.root.N,
                self.root.social.view.visibleNodeDetails.nodeListLength ()))
        except AttributeError:
            self.panel.statusLine.setText ('No data...')

class XYPlot (QWidget):
    def __init__ (self, root):
        QWidget.__init__ (self)
        self.root = root

        self.panel = ViewLayout (self.root)
        self.setLayout (self.panel)
        self.view = XYPlotUniverse (self.root)
        #self.panel.insertLayout (0, self.view)
        self.panel.statusLine.setParent (None)
    def updateStatus (self):
        None

class XYForecastPlot (QWidget):
    def __init__ (self, root):
        QWidget.__init__ (self)
        self.root = root

        self.panel = ViewLayout (self.root)
        self.view = self.root.xyPlot.view
        self.horizontalLayout = QtGui.QHBoxLayout ()
        self.setLayout (self.horizontalLayout)

        _dummyLeft = QLabel ()
        _dummyLeft.setPixmap (QPixmap (':/images/Resources/ForcastexampleLeft.png'))
        _dummyLeft.setFixedSize (150, 400)
        _dummyLeft.setScaledContents (True)
        self.horizontalLayout.addWidget (_dummyLeft)

        self.horizontalLayout.addLayout (self.panel)

        _dummyRight = QLabel ()
        _dummyRight.setPixmap (QPixmap (':/images/Resources/ForcastexampleRight.png'))
        _dummyRight.setFixedSize (150, 400)
        _dummyRight.setScaledContents (True)
        self.horizontalLayout.addWidget (_dummyRight)
        
        self.panel.insertLayout (0, self.view)
        self.panel.statusLine.setParent (None)
    def updateStatus (self):
        None
