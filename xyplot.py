#!/usr/bin/env python

from PySide import QtCore
from PySide import QtGui
import PySide.QtCore as QtCore
import string
import math
import copy
import cPickle

from application import *
from timeseries import *
from constants import *
from xyprofile import *
from tools import *

MINIMUM_BUBBLE_SIZE = 20

# Qt seems to have some bugs when plotting over a very small area (0..1 square). Fix it by multiplying everything by 1000
FACTOR = 1000.0

# When displaying the graph, leave this amount of space around the plot.
MARGIN = 200

#############################
# Report on garbage recovery
#
class Garbage ():
    def __init__ (self, instrument = False):
        self.instrument = instrument
    def REPORT (self, text):
        if self.instrument:
            print text
#############################

garbage = Garbage (False)

def makef2dIntoString (x):
    try:
        _xString = '%.2f' % x
    except:
        _xString = '?'

    return _xString

def lags (root, association, axis, timeOffset, scaling, normalised, timeStep = None):
    _ts = root.tss.series () [association [0].axis [axis].combo.selectionId]
    _lag = association [0].axis [axis].lagSpinBox.lag ()

    if timeStep:
        _index = timeStep + timeOffset + _lag
    else:
        _index = root.timeSlider.timeIndex () + timeOffset + _lag

    try:
        _flags = _ts.flags () [_index]
    except:
        _flags = 0

    return _flags

def allAxesLumpiness (root, association, timeOffset = 0, timeStep = None):
    _x = axisLumpiness (root, association, 0, timeOffset, timeStep)
    _y = axisLumpiness (root, association, 1, timeOffset, timeStep)
    _z = axisLumpiness (root, association, 2, timeOffset, timeStep)

    try:
        _value = _x * _y * _z
    except:
        _value = 0.0

    return _value

def axisLumpiness (root, association, axis, timeOffset, timeStep = None):
    _ts = root.tss.series () [association [0].axis [axis].combo.selectionId]
    _lag = association [0].axis [axis].lagSpinBox.lag ()

    if timeStep:
        _index = timeStep + timeOffset + _lag
    else:
        _index = root.timeSlider.timeIndex () + timeOffset + _lag

    try:
        _value = _ts.getAllIntensities () [_index]

        if _value == None:
            _value = 0.0
    except:
        _value = 1.0

    return _value

def transform (root, association, timesteps, axis, timeOffset, scaling, normalised, timeStep = None):
    _ts = root.tss.series () [association [0].axis [axis].combo.selectionId]
    _lag = association [0].axis [axis].lagSpinBox.lag ()

    if timeStep == None:
        _index = root.timeSlider.timeIndex () + timeOffset + _lag
    else:
        _index = timeStep + timeOffset + _lag

    _index = _index % timesteps

    if axis == 0 and root.ancestor.vTimeButton.isChecked ():
        _values = root.tss.series () [-2].getAllNormValues ()
        _fullRange = len (_values) - 1
        _endstopRange = (root.timeSlider.finishPosition - root.timeSlider.startPosition)
        _m = float (_fullRange) / _endstopRange
        _value = (_values [_index] - (float (root.timeSlider.startPosition) / (_fullRange))) * _m
    elif normalised:
        try:
            _value = _ts.getAllNormValues () [_index]
        except:
            try:
                _value = _ts._normvalues [_index]
            except:
                _value = None

        if _value != None:
            if association [0].axis [axis].checkbox.checkState ():
                _value = math.log10 ((_value + (1.0 / 9.0)) * 9.0)
            else:
                _value = _value

            _value = _value * scaling
    else:
        try:
            _value = _ts.getAllValues () [_index]
        except:
            try:
                _value = _ts._normvalues [_index]
            except:
                _value = None

    if _value == None:
        return _value
    else:
        return _value * FACTOR

class LagSpinBox (QtGui.QSpinBox):
    def __init__ (self, root, parent, association, axis):
        QtGui.QSpinBox.__init__ (self)
        self.setMinimum (-12)
        self.setMaximum (12)
        self.root = root
        self.parent = parent
        self.axis = axis
        self.lagValue = 0
        self.association = association
        self.setMaximumWidth (50)
        QtCore.QObject.connect (self, QtCore.SIGNAL ('valueChanged (int)'), self.selectionChanged)
    def __del__ (self):
        garbage.REPORT ('LagSpinBox deleted')
    def delete (self):
        None
    def selectionChanged (self, selectionId, logUndo = True):
        self.lagValue = selectionId
        self.association.association [1].associationChanged (self.association.association, 0)
        self.association.association [1].locusChanged ()
    def enterEvent (self, event):
        self.valueOnEntry = self.value ()
    def leaveEvent (self, event):
        _oldValue = self.valueOnEntry
        _newValue = self.value ()

        if _oldValue != _newValue:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.LAG, [self.association.associationId, self.axis, _newValue, _oldValue]))
    def lag (self):
        return self.lagValue

class AssociationComboBox (QtGui.QComboBox):
    def __init__ (self, root, association, axis, labels):
        QtGui.QComboBox.__init__ (self)
        self.root = root
        self.axis = axis
        self.association = association
        self.addItems (labels)
        self.selectionId = 0
        self.setAcceptDrops (True)
        self.setToolTip ('Select one timeseries from the selection tree, galaxy, social network or communities graph and drop it here')
        QtCore.QObject.connect (self, QtCore.SIGNAL ('currentIndexChanged (int)'), self.selectionChanged)
    def __del__ (self):
        garbage.REPORT ('AssociationComboBox deleted')
    def delete (self):
        self.setParent (None)
    def dragEnterEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            event.acceptProposedAction ()
    def dropEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            _labels = event.mimeData ().text ().split (',')
            _value = int (_labels [-1])
            self.preselectFromIndex (_value)
    def selectionChanged (self, selectionId):
        _oldSelectionId = self.selectionId
        self.selectionId = selectionId
        self.association.association [1].associationChanged (self.association.association, 0)
        self.association.association [1].locusChanged ()
        _association = self.association.association [0]

        if not self.root.noLog: # We don't record two undo actions for this; instead we record a single action for axis swap elsewhere
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.TIMESERIES, [_association.associationId, self.axis, selectionId, _oldSelectionId]))
    def preselectFromIndex (self, index):
        if index == -1:
            self.preselect ('LINEAR')
        elif index == -2:
            self.preselect ('CONSTANT')
        else:
            self.setCurrentIndex (index)
    def preselect (self, selection):
        _index = self.findText (selection)
        self.setCurrentIndex (_index)

class AxisLabel (QLabel):
    def __init__ (self, root, parent, association, axis, text):
        QLabel.__init__ (self, text)

        self.root = root
        self.parent = parent
        self.association = association
        self.axis = axis
        self.iconPixmap = QPixmap (':/images/Resources/add32x32.png')
        self.setAcceptDrops (True)
    def mouseMoveEvent (self, event):
        _dragText = '%d' % (self.parent.combo.selectionId)
        self.root.sourceAxis = self.axis
        self.root.sourceAssociation = self.association
        drag = QDrag (self)
        mimeData = QMimeData ()
        mimeData.setText (_dragText)
        drag.setMimeData (mimeData)
        drag.setPixmap (self.iconPixmap)
        dropAction = drag.exec_ (Qt.CopyAction)
    def mouseReleaseEvent (self, event):
        self.root.sourceAxis = -1
    def dragEnterEvent (self, event):
        if self.root.sourceAxis != -1:
            event.acceptProposedAction ()
    def dropEvent (self, event):
        if self.root.sourceAxis != -1:
            # Axis swapping occurs here
            _code = event.mimeData ().text ()
            #_sourceId = self.parent.combo.currentIndex ()
            _sourceId = self.root.sourceAssociation.associationId
            _targetId = self.parent.association.associationId
            _sourceAxis = self.root.sourceAxis
            _targetAxis = self.axis
            _sourceIndex = self.root.sourceAssociation.axis [_sourceAxis].combo.currentIndex ()
            _targetIndex = self.parent.association.axis [_targetAxis].combo.currentIndex ()

            _previousLogState = self.root.noLog
            self.root.noLog = True
            self.parent.association.axis [_targetAxis].combo.setCurrentIndex (_sourceIndex)
            self.root.sourceAssociation.axis [_sourceAxis].combo.setCurrentIndex (_targetIndex)
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.SWAP, [_sourceId, _sourceAxis, _targetId, _targetAxis]))
            self.root.noLog = _previousLogState

        self.root.sourceAxis = -1

class AssociationComboGroup (QtGui.QWidget):
    def __init__ (self, labels, root, axis, association, parentLayout):
        QtGui.QWidget.__init__ (self)
        parentLayout.addWidget (self)
        self.root = root
        self.axis = axis
        self.association = association
        self.layout = QtGui.QHBoxLayout ()
        self.layout.setContentsMargins (0, 0, 0, 0)
        self.setLayout (self.layout)
        _label = AxisLabel (self.root, self, association, axis, ['  x', '  y', '  z'][axis])
        _label.setFrameStyle (QFrame.Box)
        _label.setToolTip ('Drag me to another axis to swap axes')
        _label.setSizePolicy (QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout.addWidget (_label)
        self.combo = AssociationComboBox (root, association, axis, labels)
        self.layout.addWidget (self.combo)
        self.lagSpinBox = LagSpinBox (root, self, association, axis)
        self.layout.addWidget (self.lagSpinBox)

        self.checkbox = QtGui.QCheckBox ('log')
        QtCore.QObject.connect (self.checkbox, QtCore.SIGNAL ('stateChanged (int)'), self.stateChanged)
        self.layout.addWidget (self.checkbox)
    def __del__ (self):
        garbage.REPORT ('AssociationComboGroup deleted')
    def delete (self):
        self.lagSpinBox.delete ()
        self.layout.removeWidget (self.combo)
        self.combo.delete ()
        del self.combo
    def stateChanged (self, state):
        self.association.association [1].associationChanged (self.association.association, self.root.timeSlider.value ())
        self.association.association [1].locusChanged ()

        if not self.root.noLog:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.LOG, [self.association.associationId, self.axis, state]))
    def newState (self, state):
        self.checkbox.setCheckState (state)
        self.association.association [1].associationChanged (self.association.association, self.root.timeSlider.value ())
        self.association.association [1].locusChanged ()

class LocusSegment (QGraphicsLineItem):
    def __init__ (self, x0, y0, x1, y1):
        QGraphicsLineItem.__init__ (self, x0, y0, x1, y1)
        self.setZValue (1)
        self.line = QLineF (x0, y0, x1, y1)
    def __del__ (self):
        garbage.REPORT ('Locus segment deleted')

class DummyItem ():
    def __init__ (self):
        None

class AssociationLabel (QLabel):
    def __init__ (self, index, color, parent):
        QLabel.__init__ (self, '%d' % (index))
        self.parent = parent
        self.setMinimumWidth (30)
        self.setAlignment (QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.setStyleSheet ('background-color: rgb(%d,%d,%d)' % (color.red (), color.green (), color.blue ()))
        self.setAcceptDrops (True)
        self.setFrameStyle (QFrame.Box)
        self.setToolTip ('Select THREE timeseries from the selection tree, galaxy, social network or communities graph and drop them here')
    def dragEnterEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            _labels = event.mimeData ().text ().split (',')

            if len (_labels) == 3:
                event.acceptProposedAction ()
    def dropEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            _labels = event.mimeData ().text ().split (',')
            _values = []

            for _label in _labels:
                _values.append (int (_label))

            self.parent.axis [0].combo.preselectFromIndex (_values [0])
            self.parent.axis [1].combo.preselectFromIndex (_values [1])
            self.parent.axis [2].combo.preselectFromIndex (_values [2])

class AssociationWidget (QWidget):
    def __init__ (self, association):
        QWidget.__init__ (self)
        self.association = association
        self.setAcceptDrops (True)
    def dragEnterEvent (self, event):
        self.association [0].enterEvent (event)

class AssociationNameEditorLabel (QLineEdit):
    def __init__ (self, root, text, parent):
        QLineEdit.__init__ (self, text)
        self.root = root
        self.parent = parent
        self.setTextMargins (0, 0, 0, 0)
        self.setFrame (False)
        self.setStyleSheet ('background-color: transparent')
        QtCore.QObject.connect (self, QtCore.SIGNAL ('textEdited (QString)'), self.change)
        self.setContextMenuPolicy (Qt.NoContextMenu)
    def change (self, text):
        if self.parent.labelChanged:
            _oldText = self.text ()
        else:
            _oldText = None

        self.parent.associationName = text
        self.parent.labelChanged = True
        self.parent.bubble.label.setText (text)
    def revert (self, text):
        self.parent.associationName = text

        if text == None:
            self.parent.labelChanged = False
            _bubbleLabel, _listLabel = self.parent.compoundName ()
            self.setText (_listLabel)
        else:
            self.parent.labelChanged = True
            self.setText (text)

        self.parent.bubble.label.setText (text)
    def enterEvent (self, event):
        self.setCursorPosition (0)
        self.setReadOnly (False)

        if self.parent.labelChanged:
            self.textOnEntry = self.text ()
        else:
            self.textOnEntry = None
    def leaveEvent (self, event):
        self.setCursorPosition (0)
        self.setReadOnly (True)
        self.setBackgroundRole (QPalette.Window)

        _text = self.text ()

        if self.parent.labelChanged and (_text != self.textOnEntry):
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.LABEL, [self.parent.associationId, _text, self.textOnEntry]))

        self.deselect ()

class Association (AssociationWidget):
    def __init__ (self, root, labels, associationId, listItemWidget):
        AssociationWidget.__init__ (self, self)
        assert len (labels) > 0 # Crash out if called incorrectly
        self.root = root
        self.listItemWidget = listItemWidget
        self.associationId = associationId
        self.associationName = ''
        self.labelChanged = False

        self._locus = []
        self.hidden = False

        # Choose the next sequential colour
        self.color = self.root.ancestor.constants.colorPicker [self.associationId % len (self.root.ancestor.constants.colorPicker)]
        self.labels = labels
        self.layout = QtGui.QHBoxLayout (self)
        self.layout.setContentsMargins (2, 2, 2, 2)

        # Add the id
        self.id = AssociationLabel (self.associationId + 1, self.color, self)
        self.layout.addWidget (self.id)

        # Add the combobox groups
        self.comboLayout = QVBoxLayout ()
        self.idLayout = QtGui.QHBoxLayout ()
        self.comboLayout.addItem (self.idLayout)

        # Validity warning
        self.validityWarning = QLabel ('')
        self.validityWarning.setStyleSheet ('color: red')
        self.idLayout.addWidget (self.validityWarning)

        # Association name
        self.associationNameWidget = AssociationNameEditorLabel (self.root, 'Association name', self)
        self.idLayout.addWidget (self.associationNameWidget)
        self.layout.addLayout (self.comboLayout)
        self.association = [self, None, True]

        # Axes
        self.axis = []
        self.axis.append (AssociationComboGroup (self.labels, root, 0, self, self.comboLayout))
        self.axis.append (AssociationComboGroup (self.labels, root, 1, self, self.comboLayout))
        self.axis.append (AssociationComboGroup (self.labels, root, 2, self, self.comboLayout))

        # Bubble
        self.bubble = self.createBubble (self.color, self.listItemWidget)
        self.association [1] = self.bubble
        associationId += 1

        # Add the locus
        self.createLocus ()

        # Add a spacer just in case the window is bigger than the data
        self.layout.addItem (QSpacerItem (0, 0, QSizePolicy.Expanding, QSizePolicy.Maximum))

        QtCore.QObject.connect (self, QtCore.SIGNAL ('event (QEvent *)'), self.event)
    def _del__ (self):
        garbage.REPORT ('Association deleted')
    def markAsDisplayed (self, state):
        if state:
            self.validityWarning.setText ('')
        else:
            self.validityWarning.setText ('Data missing (x, y, z) for this time point')
    def deleteAll (self):
        for _association in self.root.associations:
            if _association [2]:
                _association [0].delete ()
        
        #self.root.associations = []
        #self.root.associationId = 0
        #self.associations = []
        #self.associationId = 0
        
    def delete (self, logUndo = True):
        # swat the locus
        self.deleteLocus ()

        #print self.associationId
        
        self.root.selector.deleteAssociation (self.associationId)

        if self.root.selector.expandedPane == self:
            self.root.selector.expandedPane = None

        self.root.timeSlider.overlapWidget.removeOldOverlaps ()

        if logUndo:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.DELETE, [self.associationId]))
    def hideToggle (self):
        _state = self.hideAction.isChecked ()
        self.setAssociationVisibility (_state)
    def setAssociationVisibility (self, state, logUndo = True):
        self.hidden = state

        if logUndo:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.HIDE, [self.associationId, state]))

        self.bubble.setVisible (self.hidden == Qt.Unchecked)
        self.bubble.associationChanged (self.association, 0)
        self.bubble.locusChanged ()
    def compoundName (self):
        if self.labelChanged:
            return self.associationName, self.associationName
        else:
            _x = self.axis [0].combo.selectionId
            _y = self.axis [1].combo.selectionId
            _z = self.axis [2].combo.selectionId
            _labels = self.labels
            _associationName = '%s v %s v %s' % (_labels [_x], _labels [_y], _labels [_z])
            return '%d' % (self.associationId + 1), _associationName
    def setAssociationNames (self, bold, highlightLabel = False, special = False):
        _bubbleLabel, _listLabel = self.compoundName ()

        if highlightLabel:
            self.bubble.label.setHtml ('<span style="color : ' + self.root.ancestor.constants.xyHighlightedNodeTextColor.name () + '">' + _bubbleLabel + '</span>')
            self.bubble.label.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeHighlightFontSize))
        elif special:
            self.bubble.label.setHtml ('<span style="color : ' + self.root.ancestor.constants.xyNodeTextColor.name () + '">' + _bubbleLabel + '</span>')
            self.bubble.label.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeHighlightFontSize))
        else:
            self.bubble.label.setHtml ('<span style="color : ' + self.root.ancestor.constants.xyNodeTextColor.name () + '">' + _bubbleLabel + '</span>')
            self.bubble.label.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeFontSize))

        self.associationNameWidget.setText (_listLabel)
        self.associationNameWidget.home (True)
        self.associationNameWidget.deselect ()
    def contextMenuEvent (self, event): # Display a contextual help popup
        _menu = QMenu ()

        # 'Hide' toggle
        self.hideAction = _menu.addAction ('hide')
        self.hideAction.setCheckable (True)
        self.hideAction.setChecked (self.hidden)
        QtCore.QObject.connect (self.hideAction, QtCore.SIGNAL ('triggered ()'), self.hideToggle)

        # 'Special' toggle
        self.specialAction = _menu.addAction ('Special')
        self.specialAction.setCheckable (True)
        self.specialAction.setChecked (self.bubble.special)
        QtCore.QObject.connect (self.specialAction, QtCore.SIGNAL ('triggered ()'), self.specialToggled)

        # 'Profile' item
        self.profileAction = _menu.addAction ('Profile')
        QtCore.QObject.connect (self.profileAction, QtCore.SIGNAL ('triggered ()'), self.bubble.profileSelected)

        # Normalised 'Profile' item
        self.normalisedProfileAction = _menu.addAction ('Normalised Profile')
        QtCore.QObject.connect (self.normalisedProfileAction, QtCore.SIGNAL ('triggered ()'), self.bubble.normalisedProfileSelected)

        _menu.addSeparator ()

        # 'Delete'
        self.deleteAction = _menu.addAction ('delete')
        QtCore.QObject.connect (self.deleteAction, QtCore.SIGNAL ('triggered ()'), self.delete)

        # 'Delete All'
        self.deleteAllAction = _menu.addAction ('delete all')
        QtCore.QObject.connect (self.deleteAllAction, QtCore.SIGNAL ('triggered ()'), self.deleteAll)

        # Tree selector
        #self.treeSelectorAction = self.contextMenu.addAction ('Tree')
        #QtCore.QObject.connect (self.treeSelectorAction, QtCore.SIGNAL ('triggered ()'), self.popupTreeSelectorDialog)

        # Set color
        #_setColorAction = _menu.addAction ('Set colour')
        #QtCore.QObject.connect (_setColorAction, QtCore.SIGNAL ('triggered ()'), self.setColorFromTree)

        _selectedAction = _menu.exec_ (QCursor.pos ())
    def specialToggled (self):
        _state = self.specialAction.isChecked ()
        self.setAssociationSpecial (_state)
    def setAssociationSpecial (self, state, logUndo = True):
        if logUndo:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.SPECIAL, [self.associationId, state]))

        self.bubble.special = state
        self.bubble.setBubbleColors (1.0)
        self.bubble.locusChanged ()

        if self.bubble.special:
            self.bubble.label.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeHighlightFontSize))
        else:
            self.bubble.label.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeFontSize))
    def doHideAction (self, hide):
        for _axis in self.axis:
            _axis.setVisible (not hide)

        try:
            _a = self.optimalSize
        except:
            self.optimalSize = self.listItemWidget.sizeHint ()

        if hide:
            self.listItemWidget.setSizeHint (QSize (self.optimalSize.width (), 20))
            self.setAssociationNames (False, False, self.bubble.special)
            self.listItemWidget.setSelected (False)
        else:
            self.listItemWidget.setSizeHint (self.optimalSize)
            self.setAssociationNames (True, True, self.bubble.special)
            self.listItemWidget.setSelected (True)
            self.root.selector.itemList.scrollToItem (self.listItemWidget)
    def enterEvent (self, event):
        if self.root.selector.expandedPane:
            if self.root.selector.expandedPane != self:
                self.root.selector.expandedPane.doHideAction (True)
                self.doHideAction (False)
                self.root.selector.expandedPane = self
            else:
                self.setAssociationNames (True, special = self.bubble.special) # Make sure the name is boldified, though
        else:
            self.doHideAction (False)
            self.root.selector.expandedPane = self

        # Update the overlap panel
        self.root.timeSlider.overlapWidget.setTimeseries (
               [self.axis [0].combo.selectionId,
                self.axis [1].combo.selectionId,
                self.axis [2].combo.selectionId],
                self.color)
    def leaveEvent (self, event):
        None
    def createLocus (self):
        start = self.root.timeSlider.startPosition
        stop = self.root.timeSlider.finishPosition
        self.deleteLocus ()

        if self.root.ancestor.xyPlot.view.showLoci.checkState () == Qt.Checked and not self.hideState ():
            _series = self.root.tss.series ()
            _times = _series [0].getAllTimes ()
            _numberOfTimesteps = len (_times)

            if stop == 0:
                _realStop = len (_times) - 1
            else:
                _realStop = stop
 
            _times = _times [start:_realStop + 1]
            _logX = self.axis [0].checkbox.checkState () 
            _logY = self.axis [1].checkbox.checkState () 
            self._locus = []
            association = self.association [0].association

            # Normalise the y values
            _maxY = 0

            for t in range (start, _realStop + 1):
                y = transform (self.root, association, _numberOfTimesteps, axis = 1, timeOffset = 0, scaling = 1.0, normalised = True, timeStep = t)
                _maxY = max (y, _maxY)
            
            try:
                association [0].scaling = 1000.0 / _maxY
            except:
                association [0].scaling = 1.0

            for t in range (start + 1, _realStop + 1):
                x0 = transform (self.root, association, _numberOfTimesteps, axis = 0, timeOffset = -1, scaling = 1.0, normalised = True, timeStep = t)
                y0 = transform (self.root, association, _numberOfTimesteps, axis = 1, timeOffset = -1, scaling = association [0].scaling, normalised = True, timeStep = t)
                x1 = transform (self.root, association, _numberOfTimesteps, axis = 0, timeOffset = 0, scaling = 1.0, normalised = True, timeStep = t)
                y1 = transform (self.root, association, _numberOfTimesteps, axis = 1, timeOffset = 0, scaling = association [0].scaling, normalised = True, timeStep = t)
                self.lumpyFactor = allAxesLumpiness (self.root, association, timeOffset = 0, timeStep = t)

                if (x0 == None): continue
                if (y0 == None): continue
                if (x1 == None): continue
                if (y1 == None): continue

                # invert the y axis
                y0 = FACTOR - y0
                y1 = FACTOR - y1

                _zeroLengthLine = ((x0 - x1)) == 0.0 and ((y0 - y1) == 0.0)

                if not _zeroLengthLine:
                    _item = DummyItem ()
                    _item.graphic = LocusSegment (x0, y0, x1, y1)
                    _item.graphic.association = self
                    _item.graphic.color = self.color
                    self._locus.append (_item.graphic)

                    if self.association [1].special:
                        _alpha = 255 * self.lumpyFactor
                    else:
                        _alpha = self.root.alpha * self.lumpyFactor

                    _color = QColor (self.color.red (), self.color.green (), self.color.blue (), _alpha)
                    _pen = QPen (_color, 5, QtCore.Qt.SolidLine)
                    _pen.setCapStyle (Qt.RoundCap)
                    _item.graphic.setPen (_pen)
                    self.root.view._scene.addItem (_item.graphic)
    def deleteLocus (self):
        for item in self._locus:
            self.root.view._scene.removeItem (item)
            del item

        self._locus = []
    def createBubble (self, color, listItemWidget):
        self.bubble = Bubble (self.root, color, listItemWidget)
        self.color = color
        self.association [1] = self.bubble
        self.root.associations.append (self.association)
        self.bubble.associationChanged (self.association, 0)
        self.bubble.locusChanged ()

        # Add a tooltip
        self.updateBubbleTooltip (self.association, self.bubble, 0)

        # Bubble always on top of loci
        self.bubble.setZValue (2)

        return self.bubble
    def updateBubbleTooltip (self, association, bubble, time):
        _timesteps = self.root.totalSteps
        x = transform (self.root, association, _timesteps, axis = 0, timeOffset = 0, scaling = 1.0, normalised = False, timeStep = time)
        y = transform (self.root, association, _timesteps, axis = 1, timeOffset = 0, scaling = 1.0, normalised = False, timeStep = time)
        z = transform (self.root, association, _timesteps, axis = 2, timeOffset = 0, scaling = 1.0, normalised = False, timeStep = time)
        _series = self.root.tss.series ()
        _textX = _series [association [0].axis [0].combo.selectionId].label ()
        _textY = _series [association [0].axis [1].combo.selectionId].label ()
        _textZ = _series [association [0].axis [2].combo.selectionId].label ()

        if x == None:
            xString = '?'
        else:
            xString = makef2dIntoString (x / FACTOR)

        if y == None:
            yString = '?'
        else:
            yString = makef2dIntoString (y / FACTOR)

        if z == None:
            zString = '?'
        else:
            zString = makef2dIntoString (z / FACTOR)

        _xLumpiness = axisLumpiness (self.root, association, axis = 0, timeOffset = 0, timeStep = time)
        _yLumpiness = axisLumpiness (self.root, association, axis = 1, timeOffset = 0, timeStep = time)
        _zLumpiness = axisLumpiness (self.root, association, axis = 2, timeOffset = 0, timeStep = time)

        if _xLumpiness < 1.0:
            _xLumpyString = ' (%d%%)' % (100.0 * _xLumpiness)
        else:
            _xLumpyString = ''

        if _yLumpiness < 1.0:
            _yLumpyString = ' (%d%%)' % (100.0 * _yLumpiness)
        else:
            _yLumpyString = ''

        if _zLumpiness < 1.0:
            _zLumpyString = ' (%d%%)' % (100.0 * _zLumpiness)
        else:
            _zLumpyString = ''

        bubble.setToolTip ('<b>Series: %d</b><br/>x:(<b>%s</b>) %s%s<br/>y:(<b>%s</b>) %s%s<br/>z:(<b>%s</b>) %s%s' %
                    (association [0].associationId + 1, xString, _textX, _xLumpyString, yString, _textY, _yLumpyString, zString, _textZ, _zLumpyString))
        bubble.tooltipText = bubble.toolTip ()
    def hideState (self):
        return self.hidden

class BubbleLabel (QtGui.QGraphicsTextItem):
    def __init__ (self, id, root, parent):
        QtGui.QGraphicsTextItem.__init__ (self)
        self.root = root

        self.setText ('%d' % (id + 1))
        self.index = id
        self.setParentItem (parent)
        self.adjustFontSize ()
        self.setTextInteractionFlags (Qt.TextEditorInteraction)
        self.setZValue (3)
        self.setAcceptHoverEvents (True)
    def hoverLeaveEvent (self, event):
        _association = self.parentItem ().listItemWidget.association

        if _association.labelChanged:
            _association.associationName = self.toPlainText ()
            _association.associationNameWidget.setText (self.toPlainText ())
            _association.associationNameWidget.deselect ()
    def adjustFontSize (self):
        _parent = self.parentItem ()

        if _parent.special:
            self.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeHighlightFontSize))
        else:
            self.setFont (QFont ('lucida', self.root.ancestor.constants.xynodeFontSize))
    def keyPressEvent (self, event):
        event.accept ()
        QGraphicsTextItem.keyPressEvent (self, event)
        _association = self.parentItem ().listItemWidget.association

        if '%d' % (self.index) == event.text ():
            _association.labelChanged = False
            _association.associationName = ''
        else:
            _association.labelChanged = True
            _association.associationName = event.text ()
    def setText (self, text):
        self.setPlainText (text)

class Bubble (QtGui.QGraphicsEllipseItem, QtCore.QObject):
    def __init__ (self, root, color, listItemWidget):
        QtGui.QGraphicsEllipseItem.__init__ (self)
        QtCore.QObject.__init__ (self)
        self.root = root

        # Flag that at least one of the series gives an invalid value at some timeslice
        self.invalid = False

        self.listItemWidget = listItemWidget
        self.bubbleSizeScaling = 0.08
        self.previousPointWasInvalid = True
        self.color = color
        self.edgeColor = self.root.ancestor.constants.xyBubbleEdgeColor

        # Marking a bubble as 'special' just means that it's not subject to dimming
        self.special = False

        # Add it to the scene
        self.setRect (QtCore.QRectF (0, 0, 0, 0))
        root.view._scene.addItem (self)

        # Add the user-editable label
        self.label = BubbleLabel (self.root.associationId + 1, self.root, self)
        self.realBubbleText = '?'

        # We want to change the font size when the user passes his mouse over this bubble
        self.setAcceptHoverEvents (True)
    #def itemChange (self, change, value):
    #    self.setBubbleColors (1.0)
    #    return QGraphicsItem.itemChange (self, change, value)
    def __del__ (self):
        garbage.REPORT ('Deletion of bubble')
    def mouseDoubleClickEvent (self, event):
        None
    def hoverEnterEvent (self, event):
        self.label.show ()
        self.listItemWidget.association.enterEvent (True)
        self.association [0].setAssociationNames (True, True, self.special)
    def hoverLeaveEvent (self, event):
        self.association [0].setAssociationNames (False, False, self.special)

        if self.root.ancestor.labelsCheckbox.checkState () == Qt.Unchecked:
            if not self.special:
                self.label.hide ()
    def specialToggled (self):
        _association = self.association [0]
        _state = self.specialAction.isChecked ()
        _association.setAssociationSpecial (_state)
    def normalisedProfileSelected (self):
        _profile = XyProfile (self.root.tss, self.association [0], self.root.timeSlider.value (), normalised = True)
        _profile.exec_ ()
    def profileSelected (self):
        _profile = XyProfile (self.root.tss, self.association [0], self.root.timeSlider.value ())
        _profile.exec_ ()
    def contextMenuEvent (self, event):
        self.contextMenu = QMenu ()

        # 'Delete'
        self.deleteAction = self.contextMenu.addAction ('delete')
        QtCore.QObject.connect (self.deleteAction, QtCore.SIGNAL ('triggered ()'), self.association [0].delete)

        # 'Hide' toggle
        self.hideAction = self.contextMenu.addAction ('hide')
        self.hideAction.setCheckable (True)
        self.hideAction.setChecked (self.association [0].hidden)
        QtCore.QObject.connect (self.hideAction, QtCore.SIGNAL ('triggered ()'), self.hideToggle)

        # 'Special' toggle
        self.specialAction = self.contextMenu.addAction ('Special')
        self.specialAction.setCheckable (True)
        self.specialAction.setChecked (self.special)
        QtCore.QObject.connect (self.specialAction, QtCore.SIGNAL ('triggered ()'), self.specialToggled)

        # 'Profile' item
        self.profileAction = self.contextMenu.addAction ('Profile')
        QtCore.QObject.connect (self.profileAction, QtCore.SIGNAL ('triggered ()'), self.profileSelected)

        # Normalised 'Profile' item
        self.normalisedProfileAction = self.contextMenu.addAction ('Normalised Profile')
        QtCore.QObject.connect (self.normalisedProfileAction, QtCore.SIGNAL ('triggered ()'), self.normalisedProfileSelected)

        _selectedAction = self.contextMenu.exec_ (event.screenPos ())
    def hideToggle (self):
        _association = self.association [0]
        _state = self.hideAction.isChecked ()
        _association.setAssociationVisibility (_state)
    def popupTreeSelectorDialog (self):
        self.root.ancestor.popupTreeSelectorDialog.setShowing (True)
    def locusChanged (self):
        self.association [0].createLocus ()
    def associationChanged (self, association, time):
        _timesteps = self.root.totalSteps

        try:
            _yScaling = association [0].scaling
        except:
            _yScaling = 1.0

        self.bubble = association [1]
        self.association = association
        x = transform (self.root, association, _timesteps, axis = 0, timeOffset = 0, scaling = 1.0, normalised = True)
        y = transform (self.root, association, _timesteps, axis = 1, timeOffset = 0, scaling = _yScaling, normalised = True)
        z = transform (self.root, association, _timesteps, axis = 2, timeOffset = 0, scaling = self.bubbleSizeScaling, normalised = True)

        if z != None:
            z += MINIMUM_BUBBLE_SIZE
            z *= self.root.bubbleScaling

        _lumpyFactor = allAxesLumpiness (self.root, association, timeOffset = 0)

        # Invert the y axis
        if y != None:
            y = FACTOR - y

        if x != None and y != None and z != None:
            if self.bubble.invalid:
                self.bubble.invalid = False
                self.bubble.label.show ()

            self.setBubbleColors (_lumpyFactor)

            # Turn off animation temporarily if the previous timeslice gave an invalid bubble.
            # Otherwise the poor bubble will be flying around all over the shop.
            if self.root.animationOn and not self.previousPointWasInvalid:
                self.anim = QtCore.QPropertyAnimation (self.bubble, "rect")
                self.anim.setDuration (self.root.ancestor.durationControl.slider.value () * 1000.0 / self.root.timeSlider.steps ())
                self.anim.setEasingCurve (QtCore.QEasingCurve.Linear)
                self.anim.setStartValue (self.bubble.getRect ())
                self.target = QtCore.QRectF (x - z / 2.0, y - z / 2.0, z, z)
                self.anim.setEndValue (self.target)
                self.anim.start ()
            else:
                self.bubble.setRect (QtCore.QRectF (x - z / 2.0, y - z / 2.0, z, z))

            self.association [0].updateBubbleTooltip (self.association, self.bubble, time)
            self.association [0].markAsDisplayed (True)
            self.previousPointWasInvalid = False
        else:
            self.bubble.setRect (QtCore.QRectF (0, 0, 0, 0))
            self.bubble.invalid = True
            self.bubble.label.hide ()
            self.association [0].markAsDisplayed (False)

            # We set this so we can switch off animation 'from' a missing value.
            self.previousPointWasInvalid = True
    def setBubbleColors (self, lumpyFactor):
        if self.special:
            _alpha = 255 * lumpyFactor
        else:
            _alpha = self.root.alpha * lumpyFactor
        
        _bubbleColor = QColor (self.color.red (), self.color.green (), self.color.blue (), _alpha)
        _radius = self.getRect ().width () / 2
        _rect = self.getRect ()
        _gradient = QRadialGradient (0, 0, 1, 0, 0)
        _gradient.setColorAt (0, QColor ('white'))
        _gradient.setColorAt (1, _bubbleColor)
        _gradient.setCoordinateMode (QGradient.ObjectBoundingMode)
        self.setBrush (QBrush (_gradient))
        self.setPen (QPen (QColor ('transparent'), 0))
        self.label.setOpacity (_alpha / 255.0)

    ##########################################
    # Setter/getter for "rect"
    ##########################################
    def getRect (self):
        return QGraphicsEllipseItem.rect (self)
    def setRect (self, val):
        QGraphicsEllipseItem.setRect (self, val)

        try:
            self.label.setPos (val.x () + val.width () / 2.0, val.y () + val.height () / 2.0)
        except:
            None

    rect = QtCore.Property (QtCore.QRectF, getRect, setRect)
    ##########################################

class DurationControl (QtGui.QVBoxLayout):
    def __init__ (self, root):
        QtGui.QVBoxLayout.__init__ (self)

        self.root = root
        self.lower = 0
        self.upper = 1
        self.default = 0

        # Make the dial
        self.dial = QDial ()
        self.addWidget (self.dial)

        # Underneath we display its range and its current value
        self.labelLayout = QtGui.QHBoxLayout ()
        self.addLayout (self.labelLayout)

        self.lowerLabel = QtGui.QLabel ()
        self.labelLayout.addWidget (self.lowerLabel)

        self.chosenLabel = QtGui.QLabel ()
        self.chosenLabel.setAlignment (QtCore.Qt.AlignCenter)
        self.labelLayout.addWidget (self.chosenLabel)

        self.upperLabel = QtGui.QLabel ()
        self.upperLabel.setAlignment (QtCore.Qt.AlignRight)
        self.labelLayout.addWidget (self.upperLabel)

        self.setRange (1, 120, 5)

        # Changes to the dial will update its label
        QtCore.QObject.connect (self.dial, QtCore.SIGNAL ('valueChanged (int)'), self.setValue)

        _label = QLabel ('Duration')
        _label.setAlignment (QtCore.Qt.AlignCenter)
        self.addWidget (_label)
    def setValue (self, value):
        self.chosenLabel.setText ('<b>%.1fs</b>' % value)
        self.dial.setSliderPosition (value)
        self.root.rerun ()
    def value (self):
        return self.dial.sliderPosition ()
    def setRange (self, lower, upper, default):
        self.lower = lower
        self.upper = upper
        self.default = default
        self.dial.setRange (self.lower, self.upper)
        self.setValue (self.default)
        self.upperLabel.setText ('%.1fs' % self.upper)
        self.lowerLabel.setText ('%.1fs' % self.lower)

class SelectionListListWidget (QtGui.QListWidget):
    def __init__ (self, root):
        QtGui.QListWidget.__init__ (self)
        self.root = root
        self.iconPixmap = QPixmap (':/images/Resources/add32x32.png')

class ToolButton (QToolButton):
    def __init__ (self, root, pixmapName, tooltip, callback):
        QToolButton.__init__ (self)
        self.root = root
        self.setIcon (QIcon (pixmapName))
        self.setToolTip (tooltip)
        QObject.connect (self, SIGNAL ('clicked ()'), callback)
        self.setAcceptDrops (True)
    def dragEnterEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            if len (event.mimeData ().text ().split (',')) % 3 == 0:
                event.acceptProposedAction ()
    def dropEvent (self, event):
        event.acceptProposedAction ()

        if event.mimeData ().hasFormat ('text/plain'):
            event.acceptProposedAction ()
            _labels = event.mimeData ().text ().split (',')
            _values = []

            for _label in _labels:
                _values.append (int (_label))

            while len (_values) and (len (_values) % 3) == 0:
                self.root.selector.craftAssociationFromIndices (_values [0], _values [1], _values [2], logUndo = True)
                del _values [0:3]

class UndoableAssociationAction ():
    HIDE        = 1 # [associationId, state]                                        Hide or show this associations
    SPECIAL     = 2 # [associationId, state]                                        Make this association special or ordinary
    TIMESERIES  = 3 # [associationId, axis, newTimeseriesId, oldTimeseries]         Set the timeseries for this axis
    SWAP        = 4 # [associationId1, axis1, associationId2, axis2]                Swap the timeseries between these two axes
    CREATE      = 5 # [associationId]                                               Create a new association
    DELETE      = 6 # [associationId]                                               Delete an association
    LABEL       = 7 # [associationId, newText, oldText]                             Change the association's label. None means 'undefined'.
    LAG         = 8 # [associationId, axis, newLag, oldLag]                         Change the axis' lag value
    LOG         = 9 # [associationId, axis, newState]                               Change the axis' log state

    def __init__ (self, action, data):
        self.action = action
        self.data = data

class AssociationUndoBuffer ():
    def __init__ (self, root):
        self.root = root
        self.reset ()
    def reset (self):
        self.undoBuffer = []
        self.redoBuffer = []
        self.root.selector.undoButton.setEnabled (False)
        self.root.selector.redoButton.setEnabled (False)
    def push (self, instruction):
        self.undoBuffer.append (instruction)
        self.redoBuffer = []
        self.root.selector.undoButton.setEnabled (True)
        self.root.selector.redoButton.setEnabled (False)
    def lenUndo (self):
        return len (self.undoBuffer)
    def lenRedo (self):
        return len (self.redoBuffer)
    def pop (self):
        if len (self.undoBuffer):
            _item = self.undoBuffer.pop ()
            self.redoBuffer.append (_item)
            self.root.selector.redoButton.setEnabled (True)

            if len (self.undoBuffer) == 0:
                self.root.selector.undoButton.setEnabled (False)

            return _item
        else:
            return None
    def redo (self):
        if len (self.redoBuffer):
            _item = self.redoBuffer.pop ()
            self.undoBuffer.append (_item)
            self.root.selector.undoButton.setEnabled (True)

            if len (self.redoBuffer) == 0:
                self.root.selector.redoButton.setEnabled (False)

            return _item
        else:
            return None
    def undoable (self):
        return self.undoBuffer
    def redoable (self):
        return self.redoBuffer

class SelectionList (QtGui.QWidget):
    def __init__ (self, root):
        QtGui.QWidget.__init__ (self)
        self.root = root
        _layout = QtGui.QVBoxLayout (self)
        _horizontalLayout = QtGui.QHBoxLayout ()
        _layout.addLayout (_horizontalLayout)
        self.itemList = SelectionListListWidget (self.root)
        self.itemList.setSizePolicy (QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        _layout.addWidget (self.itemList)
        _buttonBox = QtGui.QHBoxLayout ()

        # Undo button
        self.undoButton = QPushButton ('Undo')
        self.undoButton.setIcon (QIcon (':/images/Resources/undoIcon.png'))
        QtCore.QObject.connect (self.undoButton, QtCore.SIGNAL ('clicked ()'), self.root.undo)
        self.undoButton.setEnabled (False)
        _buttonBox.addWidget (self.undoButton)
        # Redo button
        self.redoButton = QPushButton ('Redo')
        self.redoButton.setIcon (QIcon (':/images/Resources/redoIcon.png'))
        QtCore.QObject.connect (self.redoButton, QtCore.SIGNAL ('clicked ()'), self.root.redo)
        self.redoButton.setEnabled (False)
        _buttonBox.addWidget (self.redoButton)

        _buttonBox.addStretch ()
        _layout.addLayout (_buttonBox)
        self.expandedPane = 0
        self.setAcceptDrops (True)
        self.setToolTip ('Drag one or more nodes from the Galaxy graph, the Social Network graph or the communities graph to add them to the list of XY Plot associations.\n' +
                         'If you add three nodes, a new association of those three timeseries will be created.\n' +
                         'If you drag less than three nodes or more than three nodes, one association will be created for each timeseries.\n' +
                         '  - Each timeseries will be represented by the association\'s y value and the values of x and z will be made constant.\n' +
                         '  - This is useful seeing the shape of the timeseries against time in the XY Plot.')
    def dragEnterEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            _labels = event.mimeData ().text ().split (',')

            if len (_labels):
                event.acceptProposedAction ()
    def dropEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            event.acceptProposedAction ()
            _labels = event.mimeData ().text ().split (',')

            if len (_labels) == 3:
                _x = int (_labels [0])
                _y = int (_labels [1])
                _z = int (_labels [2])
                self.craftAssociationFromIndices (_x, _y, _z, logUndo = True)
            else:
                _x = -2
                _z = -2

                for _label in _labels:
                    _y = int (_label)
                    self.craftAssociationFromIndices (_x, _y, _z, logUndo = True)

                self.root.ancestor.vTimeButton.setChecked (True)
                self.root.ancestor.xyPlot.view.redrawAll ()
                self.root.ancestor.setLayoutType ('XYgraph')
    def list (self):
        return self.itemList
    def addAssociation (self, logUndo = True):
        _item = QtGui.QListWidgetItem ()

        _item.association = Association (self.root, self.root.labels, self.root.associationId, _item)
        self.root.associationId += 1
        self.itemList.addItem (_item)
        self.itemList.setItemWidget (_item, _item.association)
        _item.setSizeHint (_item.association.sizeHint ())
        _association = self.root.associations [self.root.associationId - 1]
        _association [0].setAssociationNames (False)
        _association [0].doHideAction (True)

        if logUndo:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.CREATE, [self.root.associationId - 1]))
    def craftAssociationFromIndices (self, x = None, y = None, z = None, logUndo = False):
        self.addAssociation (logUndo = False)
        _association = self.root.associations [self.root.associationId - 1]

        _previousLogState = self.root.noLog
        self.root.noLog = True
        _association [0].axis [0].combo.preselectFromIndex (x)
        _association [0].axis [1].combo.preselectFromIndex (y)
        _association [0].axis [2].combo.preselectFromIndex (z)
        _association [0].setAssociationNames (False)
        _association [1].associationChanged (_association, 0)
        self.root.noLog = _previousLogState

        if logUndo:
            self.root.undoBuffer.push (UndoableAssociationAction (UndoableAssociationAction.CREATE, [self.root.associationId - 1]))

        return self.root.associationId - 1
    def recreateFullAssociation (self, item): # item = [associationId, [timeseriesId, lag, log] * 3]
        _associationId = item [0]
        _data = item [1]
        _association = self.root.associations [_associationId]
        _association [2] = True
        self.root.view._scene.addItem (_association [1])

        for _axis in range (3):
            _association [0].axis [_axis].combo.preselectFromIndex (_data [_axis] [0])
            _association [0].axis [_axis].lagSpinBox.lagValue = _data [_axis] [1]
            _association [0].axis [_axis].checkbox.setCheckState (Qt.Checked if _data [_axis] [2] else Qt.Unchecked)

        _association [0].setAssociationNames (False)
        _association [1].associationChanged (_association, 0)
    def undeleteAssociation (self, associationId):
        _association = self.root.associations [associationId]
        _association [2] = True
        self.root.view._scene.addItem (_association [1])
        _association [1].associationChanged (_association, 0)
        self.itemList.item (associationId).setHidden (False)
        _association [1].bubble.locusChanged ()
        _association [0].doHideAction (True)

    def deleteAssociation (self, associationId):
        _association = self.root.associations [associationId]
        # Hide the list entry
        self.itemList.item (associationId).setHidden (True)
        # Hide the bubble
        self.root.view._scene.removeItem (_association [1])
        # Mark this entry as invalid (deleted)
        _association [2] = False

        #self.root.associationId -=1
        
        return

class PseudoTimeSeries ():
    def __init__ (self, label, newSeries, steps):
        self._normvalues = newSeries
        self._label = label
        self.steps = steps
    def startoff (self):
        return 0
    def endoff (self):
        return self.steps - 1
    def extent (self):
        return self.steps
    def getAllTimes (self):
        _dummy = []

        for _index in range (self.steps):
            _dummy.append (0)

        return _dummy
    def label (self):
        return self._label
    def __getitem__ (self, index):
        return self._normvalues [index]
    def getAllNormValues (self):
        return self._normvalues

class DummyValue ():
    def __init__ (self):
        None
    def value (self):
        return 0
    def setValue (self, a):
        None

class DummySlider ():
    def __init__ (self):
        self.slider = DummyValue ()
    def setSpan (self, a, b):
        None

class DummyXf ():
    def __init__ (self):
        None
    def transform (self, a, b, c):
        return  -1

class DummyView ():
    def __init__ (self, root):
        self.root = root
    def layout (self):
        self.root.bubbleScaling = self.root.nodeSizeSlider.slider.value () / 255.0

        for _association in self.root.associations:
            if _association [2]:
                _association [1].associationChanged (_association, self.root.timeSlider.index)

        self.root.displayLoci (True)

class DummyGraphic ():
    def __init__ (self, root):
        self.graphic = root

class Graph (QGraphicsView):
    def __init__ (self, root):
        QGraphicsView.__init__ (self)
        self.root = root
        self._scene = QGraphicsScene ()
        self.setScene (self._scene)
        self.setVerticalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
        self.setSceneRect (0, 0, FACTOR, FACTOR)

        self.numScheduledScalings = 0 # Used for mousewheel zoom
        self.zoomFactor = 1.2
        self.scale (0.4, 0.4)
        self.netZoom = 0.4

        self.setDragMode (QGraphicsView.ScrollHandDrag)

        # Draw the limit of the scene that we're using
        # We'll get Qt to resize on this object as to do this manually is a mess
        # This will function as our grid
        self.gridColor = self.root.ancestor.constants.xyGridColor
        pen = QtGui.QPen (self.gridColor, 0, QtCore.Qt.SolidLine)
        self.boundary = QtGui.QGraphicsRectItem (0, 0, FACTOR, FACTOR)
        #self.boundary.setFlag (QGraphicsItem.ItemClipsChildrenToShape, True)
        self._scene.addItem (self.boundary)

        # Add the watermark
        self.watermark = QGraphicsSimpleTextItem ('8888-88')
        self.watermark.setParentItem (self.boundary)
        self.watermark.setBrush (self.root.ancestor.constants.xyWatermarkColor)
        self.watermark.setFont (QFont ('lucida', 10, 99))
        self.watermark.setPos (0, 415)
        self.watermark.setZValue (0)

        # Add the gridlines
        for i in range (11):
            offset = FACTOR * i / 10.0
            line = QtGui.QGraphicsLineItem (offset, 0, offset, FACTOR)
            line.setPen (pen)
            self._scene.addItem (line)
            line = QtGui.QGraphicsLineItem (0, offset, FACTOR, offset)
            line.setPen (pen)
            self._scene.addItem (line)

        # Add a label for when the x axis is showing time
        self.root.vTimeLabel = QGraphicsTextItem ('Time')
        self._scene.addItem (self.root.vTimeLabel)
        self.root.vTimeLabel.setPos (FACTOR * 0.85, FACTOR)
        self.root.vTimeLabel.setScale (5)
        self.root.vTimeLabel.setVisible (False)

        # Add a label for when the y axis is showing time
        self.root.vYLabel = QGraphicsTextItem ('y')
        self._scene.addItem (self.root.vYLabel)
        self.root.vYLabel.setPos (-100, 0)
        self.root.vYLabel.setScale (5)
        self.root.vYLabel.setVisible (False)

        self.setScene (self._scene)
        self.setRenderHints (QtGui.QPainter.Antialiasing)
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
        self.netZoom = self.netZoom * self.factor
    def zoomIn (self):
        self.view.scale (self.zoomFactor, self.zoomFactor)
        self.netZoom = self.netZoom * self.zoomFactor
    def zoomOut (self):
        self.view.scale (1 / self.zoomFactor, 1 / self.zoomFactor)
        self.netZoom = self.netZoom / self.zoomFactor

class XYPlotUniverse (QHBoxLayout):
    def __init__ (self, ancestor = None):
        QHBoxLayout.__init__(self)
        self.bubbleScaling = 1.0
        self.ancestor = ancestor
        self.mainThread = DummyView (self)
        self.links = [DummyGraphic (self)]
        self.rotation = QPointF (0, 0)
        self.rotationEnabled = False
        self.labelDisplay = False
        self.tooltipDisplay = False
        self.noLog = False # True during an axis swap only - to stop undo buffer recording it as two separate actions

        # Start with an empty 'associations' list
        self.associationCount = 0
        self.associations = []
        self.associationId = 0

        # Used for axis swapping in the Associations list
        self.sourceAxis = -1

        # If there are not many timeslices, bubbles will appear to jump from slice to slice.
        # So set this to True to enable linear animation between the timeslices.
        self.animationOn = False

        # By default, colours are non-transparent
        self.alpha = 255

        self.cutoffSlider = DummySlider ()
        self.xf = DummyXf ()

        # Make a layout for the graph, the time slider and the events area
        _verticalLayout2 = QVBoxLayout ()
        
        # Add the graph
        self.view = Graph (self)
        _verticalLayout2.addWidget (self.view)

        # Add the time slider
        self.timeSlider = TimeSlider (self)
        #_verticalLayout2.addLayout (self.timeSlider)
        self.ancestor.tabPaneContainer.addLayout (self.timeSlider)

        # Add a toggle to animate bubble movements
        self.useAnimation = QtGui.QCheckBox ('Smooth time')
        self.useAnimation.setChecked (Qt.Checked)
        self.displayAnimation (True)
        #QtCore.QObject.connect (self.useAnimation, QtCore.SIGNAL ('stateChanged (int)'), self.displayAnimation)
        #self.controlsLayout.addWidget (self.useAnimation)

        _horizontalLayout = QHBoxLayout ()
        self.addLayout (_horizontalLayout)
        # Use self as layout for the above plus the key
        _horizontalLayout.addLayout (_verticalLayout2)

        # Build the key area
        self.selector = SelectionList (self)
        #_horizontalLayout.addWidget (self.selector)

        # Define the undo buffer
        self.undoBuffer = AssociationUndoBuffer (self)


    def presetXY (self, index):
       # print "amar12345"
       # self.reset () # Need to see how to get the reset to be working
        #self.addTargetSeries (index)
        #self.root.mainPanel.setCurrentIndex (1) # Display Forecasting tab

        _uniqueId = self.ancestor.tss.series () [index].uniqueId ()
        _matches = []

        _visibleNodes = list (self.ancestor.galaxy.view.visibleNodeDetails.nodeList ())


        _influencersAndValues = self.ancestor.cm.coeffs [index]
        # Create another array of key value pairs by flipping the negative values
        _absInfluencersAndValues = sorted(((abs(value), abs(key)) for (key,value) in _influencersAndValues.items ()), reverse = True)


        _influencersAndValues = sorted (((value, key) for (key,value) in _influencersAndValues.items ()), reverse = True)
        _influencers = []

       # print _influencersAndValues

        # Amar Create another dictonary of visible influencers to be added
        # Also sort this list based on absolute value of impact

        _visibleInfluencers = []

       # print _absInfluencersAndValues

        for (key,value) in _absInfluencersAndValues:
            if value in _visibleNodes:
                _visibleInfluencers.append(value)
                
        #print _influencersAndValues

        # Also delete all nodes already being displayed
        # And reset the Association Ids as well
        # Central node has to be displayed as well


        #find the number of associations already in the selector pane

        num_associations =  0

        self.selector.addAssociation()

        for i in range(0,len(self.associations)):
            _association = self.associations [i]
            if _association[2]:
                num_associations +=1
            
        

        if num_associations > len(_visibleInfluencers):
            index_visible = len(_visibleInfluencers) - 1
        else:
            index_visible = num_associations - 1
        
        _association [0].axis [0].combo.preselectFromIndex (_visibleInfluencers[index_visible])
        _association [0].axis [1].combo.preselectFromIndex (_visibleInfluencers[index_visible])
        _association [0].axis [2].combo.preselectFromIndex (_visibleInfluencers[index_visible])
        _association [0].setAssociationNames (False)
        _association [1].associationChanged (_association, 0)
        #self.root.noLog = _previousLogState


        
    def undo (self):
        _item = self.undoBuffer.pop ()

        if _item:
            if _item.action == UndoableAssociationAction.HIDE: # [associationId, state]
                _associationId = _item.data [0]
                _state = _item.data [1]
                self.associations [_associationId] [0].setAssociationVisibility (not _state, logUndo = False)
            elif _item.action == UndoableAssociationAction.SPECIAL: # [associationId, state]
                _associationId = _item.data [0]
                _state = _item.data [1]
                self.associations [_associationId] [0].setAssociationSpecial (not _state, logUndo = False)
            elif _item.action == UndoableAssociationAction.TIMESERIES: # [associationId, axis, newTimeseriesId, oldTimeseriesId]
                _associationId = _item.data [0]
                _axis = _item.data [1]
                _newId = _item.data [2]
                _oldId = _item.data [3]

                self.noLog = True
                _association = self.associations [_associationId] [0]
                _association.axis [_axis].combo.preselectFromIndex (_oldId)
                _association.setAssociationNames (True, special = _association.bubble.special) # Make sure the name is boldified, though
                self.noLog = False
            elif _item.action == UndoableAssociationAction.SWAP: # [associationId1, axis1, associationId2, axis2]
                _associationId1 = _item.data [0]
                _axis1 = _item.data [1]
                _id1 = self.associations [_associationId1] [0].axis [_axis1].combo.selectionId
                _associationId2 = _item.data [2]
                _axis2 = _item.data [3]
                _id2 = self.associations [_associationId2] [0].axis [_axis2].combo.selectionId

                self.noLog = True
                self.associations [_associationId1] [0].axis [_axis1].combo.preselectFromIndex (_id2)
                self.associations [_associationId2] [0].axis [_axis2].combo.preselectFromIndex (_id1)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.CREATE: # [associationId]
                _associationId = _item.data [0]

                self.noLog = True
                self.associations [_associationId] [0].delete (logUndo = False)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.DELETE: # [associationId]
                _associationId = _item.data [0]

                self.noLog = True
                self.selector.undeleteAssociation (_associationId)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.LABEL: # [associationId, newText, oldText]
                _associationId = _item.data [0]
                _oldText = _item.data [2]

                self.noLog = True
                self.associations [_associationId] [0].associationNameWidget.revert (_oldText)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.LAG: # [associationId, axis, newValue, oldValue]
                _associationId, _axis, _newValue, _oldValue = _item.data
                
                self.noLog = True
                self.associations [_associationId] [0].axis [_axis].lagSpinBox.setValue (_oldValue)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.LOG: # [associationId, axis, newState]
                _associationId, _axis, _newState = _item.data
                _oldState = Qt.Checked if _newState == Qt.Unchecked else Qt.Unchecked
                
                self.noLog = True
                self.associations [_associationId] [0].axis [_axis].newState (_oldState)
                self.noLog = False
            else:
                print ('ERROR: Unrecognised undoable action')
        else:
            print ('ERROR: Attempt to pop beyond end of undo buffer')
    def redo (self):
        _item = self.undoBuffer.redo ()

        if _item:
            if _item.action == UndoableAssociationAction.HIDE: # [associationId, state]
                _associationId = _item.data [0]
                _state = _item.data [1]
                self.associations [_associationId] [0].setAssociationVisibility (_state, logUndo = False)
            elif _item.action == UndoableAssociationAction.SPECIAL: # [associationId, state]
                _associationId = _item.data [0]
                _state = _item.data [1]
                self.associations [_associationId] [0].setAssociationSpecial (_state, logUndo = False)
            elif _item.action == UndoableAssociationAction.TIMESERIES: # [associationId, axis, newTimeseriesId, oldTimeseriesId]
                _associationId = _item.data [0]
                _axis = _item.data [1]
                _newId = _item.data [2]
                _oldId = _item.data [3]
                self.noLog = True
                _association = self.associations [_associationId] [0]
                _association.axis [_axis].combo.preselectFromIndex (_newId)
                _association.setAssociationNames (True, special = _association.bubble.special) # Make sure the name is boldified, though
                self.noLog = False
            elif _item.action == UndoableAssociationAction.SWAP: # [associationId1, axis1, associationId2, axis2]
                _associationId1 = _item.data [0]
                _axis1 = _item.data [1]
                _id1 = self.associations [_associationId1] [0].axis [_axis1].combo.selectionId
                _associationId2 = _item.data [2]
                _axis2 = _item.data [3]
                _id2 = self.associations [_associationId2] [0].axis [_axis2].combo.selectionId
                self.noLog = True
                self.associations [_associationId1] [0].axis [_axis1].combo.preselectFromIndex (_id2)
                self.associations [_associationId2] [0].axis [_axis2].combo.preselectFromIndex (_id1)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.CREATE: # [associationId]
                self.noLog = True
                self.selector.undeleteAssociation (_item.data [0])
                self.noLog = False
            elif _item.action == UndoableAssociationAction.DELETE: # [associationId]
                _associationId = _item.data [0]

                self.noLog = True
                self.associations [_associationId] [0].delete ()
                self.noLog = False
            elif _item.action == UndoableAssociationAction.LABEL: # [associationId, newText, oldText]
                _associationId = _item.data [0]
                _newText = _item.data [1]

                self.noLog = True
                self.associations [_associationId] [0].associationNameWidget.revert (_newText)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.LAG: # [associationId, axis, newValue, oldValue]
                _associationId, _axis, _newValue, _oldValue = _item.data
                
                self.noLog = True
                self.associations [_associationId] [0].axis [_axis].lagSpinBox.setValue (_newValue)
                self.noLog = False
            elif _item.action == UndoableAssociationAction.LOG: # [associationId, axis, newState]
                _associationId, _axis, _newState = _item.data
                
                self.noLog = True
                self.associations [_associationId] [0].axis [_axis].newState (Qt.Checked if _newState == Qt.Checked else Qt.Unchecked)
                self.noLog = False
            else:
                print ('ERROR: Unrecognised redoable action')
        else:
            print ('ERROR: Attempt to pop beyond end of redo buffer')
    def displayLoci (self, state):
        for _association in self.associations:
            if _association [2]:
                _association [1].bubble.locusChanged ()
    def toggleLabelDisplay (self, state):
        self.labelDisplay = state

        for _association in self.associations:
            if _association [2]:
                _association [1].label.setVisible (state or _association [1].special)
    def toggleTooltipDisplay (self, state):
        self.tooltipDisplay = state

        for _association in self.associations:
            if _association [2]:
                if state:
                    _association [1].setToolTip (_association [1].tooltipText)
                else:
                    _association [1].setToolTip ('')
                
    def adjustNodeSize (self, value):
        self.mainThread.layout ()
    def getValidEvents (self):
        self.minDatetime = dateutil.parser.parse (self.ancestor.tss.series () [0].getAllTimes () [0])
        self.maxDatetime = dateutil.parser.parse (self.ancestor.tss.series () [0].getAllTimes () [-1])

        _validEvents = []

        # Check the events
        for _eventIndex, _event in enumerate (self.ancestor.events):
            if _event [1] <= self.maxDatetime and _event [2] >= self.minDatetime:
                _validEvents.append (_eventIndex)

        return _validEvents
    def showNodes (self):
        None
    def redrawAll (self):
        for _association in self.associations:
            if _association [2]:
                _association [1].bubble.locusChanged ()
                _association [1].associationChanged (_association [1].association, 0)

        _timeDisplay = self.ancestor.vTimeButton.isChecked ()
        self.vTimeLabel.setVisible (_timeDisplay)
        self.vYLabel.setVisible (_timeDisplay)

        if _timeDisplay:
            self.view.setBackgroundBrush (self.ancestor.constants.xyTimeDisplayBackgroundTint)
        else:
            self.view.setBackgroundBrush (self.ancestor.constants.xyDisplayBackgroundTint)
    def reshade (self, opacity):
        if opacity > 255:
            self.alpha = 255
        else:
            self.alpha = opacity
     
        for _association in self.associations:
            if _association [2]:
                _association [1].bubble.locusChanged ()
                _association [1].associationChanged (_association [1].association, 0)
    def zapAllAssociations (self):
        for _association in self.associations:
            if _association [2]:
                _association [0].delete ()

        self.associations = []
        self.associationId = 0
        self.selector.itemList.clear ()
    def toolButton (self, iconFilename, tip, callback, parent = None):
        _button = QToolButton (parent)
        _button.setIcon (QIcon (iconFilename))
        _button.setToolTip (tip)
        QtCore.QObject.connect (_button, QtCore.SIGNAL ('clicked ()'), callback)
        return _button
    def displayAnimation (self, state):
        self.animationOn = state
    def rerun (self):
        if self.timeLine.state () == QtCore.QTimeLine.Running:
            self.pause ()
            self.run ()
    def setupTimeLine (self):
        self.timeLine = QtCore.QTimeLine (self.ancestor.durationControl.slider.value () * 1000.0)
        self.timeLine.setCurveShape (QtCore.QTimeLine.LinearCurve)
        QtCore.QObject.connect (self.timeLine, QtCore.SIGNAL ('frameChanged (int)'), self.runStep)
        QtCore.QObject.connect (self.timeLine, QtCore.SIGNAL ('finished ()'), self.runComplete)
    def run (self):
        if self.timeLine.state () == QtCore.QTimeLine.Running:
            return

        self.ancestor.pauseButton.setEnabled (True)
        self.ancestor.runButton.setEnabled (False)
        self.timeSlider.setEnabled (False)

        steps = self.timeSlider.steps ()

        if self.timeSlider.value () >= (self.timeSlider.finishPosition):
            saveAnimationState = self.animationOn
            self.animationOn = False
            self.timeSlider.setValue (self.timeSlider.startPosition)
            self.animationOn = saveAnimationState

        # Recompute the duration for this partial run
        remaining = (0.0 + self.timeSlider.finishPosition - self.timeSlider.value ()) / steps

        self.timeLine.setDuration (self.ancestor.durationControl.slider.value () * 1000.0 * remaining)
        self.timeLine.setFrameRange (self.timeSlider.value (), self.timeSlider.finishPosition)
        self.timeLine.start ()
    def pause (self):
        self.timeLine.stop ()
        self.ancestor.runButton.setEnabled (True)
        self.timeSlider.setEnabled (True)
        self.ancestor.pauseButton.setEnabled (False)
    def runComplete (self):
        self.ancestor.pauseButton.setEnabled (False)
        self.timeSlider.setEnabled (True)
        self.ancestor.runButton.setEnabled (True)
    def reset (self):
        for association in self.associations:
            if association [2]:
                association [0].delete ()

        self.selector.list ().clear ()
        self.associationId = 0
        self.associations = []
    def reloadTimeseries (self, tss):
        #self.tss = copy.deepcopy (tss)
        self.tss = tss
        self.undoBuffer.reset ()

        ts = self.tss.series ()
        _allTimes = self.tss.series () [0].getAllTimes ()
        self.totalSteps = len (_allTimes)

        if self.totalSteps == 0:
            self.timeSlider.configure ('', '', 0)
            self.timeSlider.updateTimeSliderCounter (0)
        else:
            self.timeSlider.configure (_allTimes [0], _allTimes [-1], self.totalSteps)
            self.timeSlider.updateTimeSliderCounter (_allTimes [0])

        # Make a list of labels of all timeserieses
        self.labels = []

        for n in range (len (self.tss)):
            s = ts [n]
            self.labels.append (s.label ())

        self.appendSeries ('LINEAR')
        self.appendSeries ('CONSTANT')

        # Setup any controls that need it when the database changes
        self.ancestor.durationControl.setSpan (1, self.totalSteps * 10)
        self.timeLine.stop ()
        self.pause ()
        self.timeSlider.setValue (0)
    def appendSeries (self, type):
        _steps = len (self.tss.series () [0].getAllTimes ())
        _newSeries = []

        if type == 'LINEAR':
            _start = 0.0

            if _steps == 1.0:
                _step = 1.0
            else:
                _step = 1.0 / (_steps - 1.0)

            for _value in range (_steps):
                _newSeries.append (_start)
                _start += _step
        elif type == 'CONSTANT':
            for _value in range (_steps):
                _newSeries.append (0.5)
        else:
            raise WrongTypeOfAppendedSeries

        self.labels.append (type)
        self.tss.series ().append (PseudoTimeSeries (type, _newSeries, _steps))
    def runStep (self, step):
        self.timeSlider.setValue (step)
