#!/usr/bin/env python

import constants
import sys
import time
import PySide
import sqlite3
from datetime import date
import re
import os
import signal

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtUiTools import *
from PySide.QtWebKit import *

from application import *
from timeseries import *
from random import *
from xyplot import *
from universeprofile import *
from config import *
from universe import *
from tools import *
#from unicodedata import *

import bc_rc
import types
import dateutil.parser as parseDate
import pickle
from monitor import ConciseMonitor
import graph
import random
import clusterlayout
import analysis

class KeyFilter (QtCore.QObject):
    def __init__ (self, root):
        QtCore.QObject.__init__ (self)
        self.root = root
    def eventFilter (self, anObject, event):
        if event.type () == QtCore.QEvent.KeyPress:
            if event.key () == QtCore.Qt.Key_Control:
                if isinstance (self.root.layoutType (), XYPlot) or isinstance (self.root.layoutType (), XYForecastPlot):
                    self.root.xyPlot.view.view.setDragMode (QtGui.QGraphicsView.RubberBandDrag)
                elif not isinstance (self.root.layoutType (), analysis.AnalysisPlot):
                    self.root.layoutType ().view.setDragMode (QtGui.QGraphicsView.RubberBandDrag)
                return True
        elif event.type () == QtCore.QEvent.KeyRelease:
            if event.key () == QtCore.Qt.Key_Control:
                if isinstance (self.root.layoutType (), XYPlot) or isinstance (self.root.layoutType (), XYForecastPlot):
                    self.root.xyPlot.view.view.setDragMode (QtGui.QGraphicsView.ScrollHandDrag)
                elif not isinstance (self.root.layoutType (), analysis.AnalysisPlot):
                    self.root.layoutType ().view.setDragMode (QtGui.QGraphicsView.ScrollHandDrag)
                return True

        return QtCore.QObject.eventFilter (self, self, event)

class MenuBar (QMenuBar):
    def __init__ (self, mac, parent = None):
        QMenuBar.__init__ (self)
        self.root = parent
        self.setGeometry (QRect (0, 0, 800, 25))

        # File menu
        self.fileMenu = self.addMenu ("&File")
        # Open
        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_FILE_OPEN:
            self.openItem = QAction ('&Open', self)
            self.openItem.setShortcut ('Ctrl+O')
            self.fileMenu.addAction (self.openItem)
            QObject.connect (self.openItem, SIGNAL ('triggered()'), self.openFile)
        # Save configuration
        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_FILE_SAVECONFIGURATION:
            self.saveItem = QAction ('&Save configuration', self)
            self.saveItem.setShortcut ('Ctrl+S')
            self.fileMenu.addAction (self.saveItem)
            QObject.connect (self.saveItem, SIGNAL ('triggered()'), self.root.saveConfiguration)
        # Separator
        if self.root.constants.facilitiesKey & (self.root.constants.FACILITIES_FILE_SAVECONFIGURATION | self.root.constants.FACILITIES_FILE_OPEN):
            self.fileMenu.addSeparator ()
        # Save configuration to file
        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_FILE_SAVECONFIGTOFILE:
            self.saveFileItem = QAction ('Save Con&figuration to file', self)
            self.saveFileItem.setShortcut ('Ctrl+F')
            self.fileMenu.addAction (self.saveFileItem)
            QObject.connect (self.saveFileItem, SIGNAL ('triggered()'), self.root.saveConfigurationToNamedFile)
        # Load configuration from file
        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_FILE_LOADCONFIGFROMFILE:
            self.loadFileItem = QAction ('&Load Configuration from file', self)
            self.loadFileItem.setShortcut ('Ctrl+L')
            self.fileMenu.addAction (self.loadFileItem)
            QObject.connect (self.loadFileItem, SIGNAL ('triggered()'), self.root.loadConfigurationFromNamedFile)
        # Separator
        if self.root.constants.facilitiesKey & (self.root.constants.FACILITIES_FILE_SAVECONFIGTOFILE | self.root.constants.FACILITIES_FILE_LOADCONFIGFROMFILE):
            self.fileMenu.addSeparator ()
        # Exit
        self.exitFileItem = QAction ('&Exit', self)
        self.exitFileItem.setShortcut ('Ctrl+Q')
        self.fileMenu.addAction (self.exitFileItem)
        QObject.connect (self.exitFileItem, SIGNAL ('triggered()'), self.root.leave)

        # Edit menu
        self.editMenu = self.addMenu ("&Edit")
        # Undo
        self.undoItem = QAction ('&Undo', self)
        self.undoItem.setEnabled (False)
        self.undoItem.setShortcut ('Ctrl+Z')
        self.editMenu.addAction (self.undoItem)
        QObject.connect (self.undoItem, SIGNAL ('triggered()'), self.root.undo)
        # Redo
        self.redoItem = QAction ('&Redo', self)
        self.redoItem.setEnabled (False)
        self.redoItem.setShortcut ('Ctrl+Y')
        self.editMenu.addAction (self.redoItem)
        QObject.connect (self.redoItem, SIGNAL ('triggered()'), self.root.redo)
        # Select all
        self.selectAllItem = QAction ('Select &all', self)
        self.selectAllItem.setShortcut ('Ctrl+A')
        self.editMenu.addAction (self.selectAllItem)
        QObject.connect (self.selectAllItem, SIGNAL ('triggered()'), self.root.selectAll)

        # View menu
        if (self.root.constants.facilitiesKey & (self.root.constants.FACILITIES_TOOL_SELECTIONTREE | \
                                                self.root.constants.FACILITIES_TOOL_TIMEDIMENSION | \
                                                self.root.constants.FACILITIES_TOOL_COMMONCONTROLS| \
                                                self.root.constants.FACILITIES_TOOL_LAYOUTCONTROLS | \
                                                self.root.constants.FACILITIES_TOOL_SEEKNODE | \
                                                self.root.constants.FACILITIES_TOOL_XYASSOCIATIONS)):
            self.viewMenu = self.addMenu ("&View")

            if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_TOOL_SELECTIONTREE:
                self.viewMenu.addAction (self.root.selectionTreeWindow.toggleViewAction ())

            if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_TOOL_TIMEDIMENSION:
                self.viewMenu.addAction (self.root.timeDimensionWindow.toggleViewAction ())

            if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_TOOL_COMMONCONTROLS:
                self.viewMenu.addAction (self.root.commonControlsWindow.toggleViewAction ())

            if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_TOOL_LAYOUTCONTROLS:
                self.viewMenu.addAction (self.root.layoutSpecificControlsWindow.toggleViewAction ())

            if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_TOOL_SEEKNODE:
                self.viewMenu.addAction (self.root.seekNodeWindow.toggleViewAction ())

            if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_TOOL_XYASSOCIATIONS:
                self.root.associationWindowToggleViewAction = self.root.associationWindow.toggleViewAction ()
                self.viewMenu.addAction (self.root.associationWindowToggleViewAction)
                self.root.showAssociationsToolbox (False)

        # Tools menu
        self.toolsMenu = self.addMenu ("&Tools")
        # Hide
        self.hideSelectedItem = QAction ('&Hide selected', self)
        self.hideSelectedItem.setShortcut ('Ctrl+H')
        self.toolsMenu.addAction (self.hideSelectedItem)
        QObject.connect (self.hideSelectedItem, SIGNAL ('triggered()'), self.hideAllSelectedNodes)
        # Hide unselected
        self.hideUnselectedItem = QAction ('Hide &unselected', self)
        self.hideUnselectedItem.setShortcut ('Ctrl+U')
        self.toolsMenu.addAction (self.hideUnselectedItem)
        QObject.connect (self.hideUnselectedItem, SIGNAL ('triggered()'), self.hideAllUnselectedNodes)

        # Help menu
        self.helpMenu = self.addMenu ("&Help")
        # About
        self.aboutDialog = AboutDialog (Application)
        self.aboutItem = QAction ("&About", self)
        self.helpMenu.addAction (self.aboutItem)
        QObject.connect (self.aboutItem, SIGNAL ('triggered()'), self.aboutDialog.exec_)
        # Separator
        self.helpMenu.addSeparator ()
        # User guide
        self.userGuideItem = QAction ('&User Guide', self)
        self.helpMenu.addAction (self.userGuideItem)
        QObject.connect (self.userGuideItem, SIGNAL ('triggered()'), self.showUserGuideDialog)

        # Undo button
        self.undoButton = self.addAction ('<-')
        self.undoButton.setIcon (QIcon (':/images/Resources/undoIcon.png'))
        self.undoButton.setToolTip ('Undo') # This doesn't work
        QObject.connect (self.undoButton, SIGNAL ('triggered()'), self.root.undo)

        # Hide selected button
        self.hideSelectedButton = self.addAction ('Hide Selected')
        QObject.connect (self.hideSelectedButton, SIGNAL ('triggered()'), self.hideAllSelectedNodes)

        # Hide unselected button
        self.hideUnselectedButton = self.addAction ('Hide Unselected')
        QObject.connect (self.hideUnselectedButton, SIGNAL ('triggered()'), self.hideAllUnselectedNodes)

        # Redo button
        self.redoButton = self.addAction ('->')
        self.redoButton.setIcon (QIcon (':/images/Resources/redoIcon.png'))
        self.redoButton.setToolTip ('Redo') # This doesn't work
        QObject.connect (self.redoButton, SIGNAL ('triggered()'), self.root.redo)

    def hideAllUnselectedNodes (self):
        self.root.hideNodes (list (set (self.root.layoutType ().view.visibleNodeDetails.nodeList ()) - set (self.root.selectionList)))
        self.root.updateSelectionsAndHideButtons ()
    def hideAllSelectedNodes (self):
        _selectionList = self.root.selectionList [:]
        self.root.selectionList = []
        self.root.hideNodes (_selectionList)
        self.root.updateSelectionsAndHideButtons ()
    def popupHelp (self):
        self.root.helpDialog.show ()
        self.root.helpDialog.raise_ ()
    def showUserGuideDialog (self):
        self.root.helpDialog.webView.setUrl ('Resources/Help.html')
        self.popupHelp ()
    def openFile (self):
        self.root.socialLayoutThread.suspendRedraw (True)
        self.root.galaxyLayoutThread.suspendRedraw (True)
        self.root.clusterLayoutThread.suspendRedraw (True)

        try:
            if self.root.bcFiles:
                self.root.saveConfiguration ()
        except:
            pass

        _filename, _dummy = QtGui.QFileDialog.getOpenFileName (self, 'Open Database', self.root.constants.databasePath, 'Databases (*.db)')

        if _filename:
            self.root.loadNewDatabase (_filename)

        self.root.socialLayoutThread.suspendRedraw (False)
        self.root.galaxyLayoutThread.suspendRedraw (False)
        self.root.clusterLayoutThread.suspendRedraw (False)
    def openFileByName (self, filename):
        self.root.loadingFile = True

        # Save the current configuration
        if len (self.root.nodes):
            self.root.saveConfiguration ()

        self.root.constants.databasePath, _databaseFilename = os.path.split (filename)
        self.profileName = tools.getUsername ()
        _fullPathname = os.path.join (self.root.constants.databasePath + '/', _databaseFilename)

        self.root.scenarioSelectorCombo.setCurrentIndex (0)

        if not self.root.readDataset (_fullPathname):
            return

        # If there is no database loaded, ensure that the center node is defined
        try:
            self.root.setCenterNode (self.root.centerNode ())
        except:
            self.root.setCenterNode (0)

        if (self.root.N):
            # Save the database filename and pathname to the .bc_profile
            self.root.constants._writeProfile_ (self.root.constants.databasePath)
            self.root.START = self.root.INSTRUMENT_LOAD ('load:update .bc_profile', self.root.START)

            # Determine the frequency choices and setup the frequency choice comboBox
            self.root.timeslice = 0
            _frequencyChoices = set ()
            _mainChoice = 'ALL (' + self.root.tss.slice_index (self.root.db) [1] ['interval'] + ')'

            for _slice in self.root.tssids [1:]:
                _frequencyChoices.add (self.root.tss.slice_index (self.root.db) [_slice] ['interval'])

            _allChoices = list ()
            _allChoices.append (_mainChoice)

            for _frequency in _frequencyChoices:
                _allChoices.append (_frequency)

            self.root.timesliceFrequencySelector.defineChoices (_allChoices)
            self.root.scenarioSelectorCombo.setSelections (self.root.tss.coeffindex ())
            self.root.loadConfiguration ()

            # Ensure that the center node is checked in the selection tree
            self.root.setCenterNode (self.root.centerNode ())
            self.root.newSelector.nodeDictionary [self.root.centerNode ()].checked = Qt.Checked
            self.root.newSelector.model.propagateToggleStateUp (Qt.Checked, self.root.newSelector.nodeDictionary [self.root.centerNode ()])
            self.root.nodes [self.root.centerNode ()].hiding = True

            # Protect us from displaying links on large datasets
            if self.root.N > 100:
                self.root.linksCheckbox.setCheckState (Qt.Unchecked)

            self.root.loadingFile = False
            self.doRequiredLayouts ()
        else:
            self.root.loadingFile = False

class ScenarioSelectorCombo (QComboBox):
    def __init__ (self, root):
        QComboBox.__init__ (self)
        self.root = root
        self.setMaximumWidth (300)
        self.items = dict ()
        QObject.connect (self, SIGNAL ('currentIndexChanged (int)'), self.changeScenario)
        self.comboDisabled = True
    def disableCombo (self, state):
        self.comboDisabled = state
    def changeScenario (self, index):
        if self.comboDisabled:
            return

        if index < 0 or index >= len (self.items):
            return

        self.root.busyCursor (True)
        self.root.interruptLayoutsAndWaitForCompletion ()

        if not self.root.loadingFile:
            self.root.doLayoutA ()

            if len (self.items):
                self.type = self.items [index + 1]
                self.setCurrentIndex (index)
                self.root.loadCoefficients ()

            self.root.doLayoutB ()

        self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_preambleSignal)
        self.root.busyCursor (False)
    def setSelections (self, items):
        self.items = items

        for i in range (self.count ()):
            self.removeItem (0)

        for item in self.root.tss.coeffids ():
            self.addItem (items [item])

class AnimationTypeCombo (QComboBox):
    def __init__ (self, root):
        QComboBox.__init__ (self)
        self.root = root

        self.items = [QEasingCurve.Linear, QEasingCurve.InQuad, QEasingCurve.OutQuad,
                    QEasingCurve.InOutQuad, QEasingCurve.OutInQuad, QEasingCurve.InCubic,
                    QEasingCurve.OutCubic, QEasingCurve.InOutCubic, QEasingCurve.OutInCubic,
                    QEasingCurve.InQuart, QEasingCurve.OutQuart, QEasingCurve.InOutQuart,
                    QEasingCurve.OutInQuart, QEasingCurve.InQuint, QEasingCurve.OutQuint,
                    QEasingCurve.InOutQuint, QEasingCurve.OutInQuint, QEasingCurve.InSine,
                    QEasingCurve.OutSine, QEasingCurve.InOutSine, QEasingCurve.OutInSine,
                    QEasingCurve.InExpo, QEasingCurve.OutExpo, QEasingCurve.InOutExpo,
                    QEasingCurve.OutInExpo, QEasingCurve.InCirc, QEasingCurve.OutCirc,
                    QEasingCurve.InOutCirc, QEasingCurve.OutInCirc, QEasingCurve.InElastic,
                    QEasingCurve.OutElastic, QEasingCurve.InOutElastic, QEasingCurve.OutInElastic,
                    QEasingCurve.InBack, QEasingCurve.OutBack, QEasingCurve.InOutBack,
                    QEasingCurve.OutInBack, QEasingCurve.InBounce, QEasingCurve.OutBounce,
                    QEasingCurve.InOutBounce, QEasingCurve.OutInBounce]

        self.labels = self.tidyText (self.items)
        self.addItems (self.labels)

        # Create a dictionary, just so we can look up the startup option by name :)
        dictOfLabels = {}

        for item in range (len (self.items)):
            dictOfLabels [self.labels [item]] = item

        self.changeEasing (dictOfLabels ['InOutQuint'])
        QObject.connect (self, SIGNAL ('currentIndexChanged (int)'), self.changeEasing)
    def changeEasing (self, index):
        self.type = self.items [index]
        self.setCurrentIndex (index)
    def tidyText (self, labels):
        result = []

        for label in labels:
            result.append (label.name)

        return result

class TreeItem ():
    def __init__ (self, root, data = '', label = '', id = None, parent = None):
        self.root = root
        self.data = data
        self.label = label
        self.id = id
        self.selected = False
        self.color = QColor ('')

        try:
            intId = int (id)
        except:
            None
        else:
            self.root.nodes [intId].selectorTreeNode = self
            self.root.nodes [intId].hiding = True

        self.myParent = parent
        self.checked = Qt.Unchecked
        self.myChildren = []

        if parent != None:
            parent.appendChild (self)
    def __del__ (self):
        None
    def setId (self, value):
        self.id = value
    def setLabel (self, value):
        self.label = value
    def setChildren (self, children):
        self.myChildren = children [:]
    def removeChild (self, child):
        if child in self.myChildren:
            self.myChildren.remove (child)
    def appendChild (self, child):
        self.myChildren.append (child)
    def child (self, row):
        if row < len (self.myChildren):
            return self.myChildren [row]
        else:
            return None
    def childCount (self):
        return len (self.myChildren)
    def children (self):
        return self.myChildren
    def columnCount (self):
        return 3
    def data (self, column):
        return self.data
    def setData (self, data):
        None
    def label (self):
        return self.label
    def parent (self):
        return self.myParent
    def setParent (self, parent):
        self.myParent = parent
    def row (self):
        if self.myParent:
            return self.myParent.myChildren.index (self)
        else:
            return 0
    def setSelected (self, state):
        if state:
            self.root.newSelector.setSelection (QRect (0, 0, 0, 0), QItemSelectionModel.Select)

class TreeModel (QAbstractItemModel):
    def __init__ (self, root, data, checkable = True):
        QAbstractItemModel.__init__ (self)

        self.root = root
        self.treeRoot = TreeItem (root, 'ALL', '', '', None)
        self.itemdict = {}
        self.itemdict [id (self.treeRoot)] = self.treeRoot

        if checkable:
            self.userCheckable = Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        else:
            self.userCheckable = Qt.ItemIsEnabled

        for timeseries in data:
            self.addNode (self.treeRoot, timeseries, None)
    def _getInvertedNode (self, tree, node):
        _path = ''
        _here = node
        _tree = tree

        while _here.parent () and _here.parent ().data != 'ALL':
            _path = _here.parent ().data + ':' + _path
            _here = _here.parent ()

        if node.id != '':
            _tree += _path [:-1] + '\t' +  node.data + '\t' + node.id + '\n'

        for _child in node.children ():
            _tree = self._getInvertedNode (_tree, _child)

        return _tree
    def getInvertedTree (self):
        _tree = ''
        _tree = self._getInvertedNode (_tree, self.treeRoot)
        return _tree [:-1]
    def columnCount (self, parent):
        if parent.isValid ():
            try:
                return self.itemdict [parent.internalId ()].columnCount ()
            except:
                return 3
        else:
            return self.treeRoot.columnCount ()
    def data (self, index, role):
        if not index.isValid ():
            return None

        try:
            item = self.itemdict [index.internalId ()]
        except:
            return None

        if role == Qt.CheckStateRole:
            if index.column () == 0:
                return item.checked
            else:
                return None
        elif role == Qt.ForegroundRole:
            item = self.itemdict [index.internalId ()]

            if item.color == '':
                return QColor ('grey')
            elif item.color == QColor ('black'):
                return QColor ('white')
            else:
                return QColor ('black')
        elif role == Qt.BackgroundRole:
            item = self.itemdict [index.internalId ()]

            if item.color == '':
                return QColor ('white')
            else:
                return QColor (item.color).lighter (130)
        elif role == QtCore.Qt.DisplayRole:
            pass
        else:
            return None

        if index.column () == 0:
            return item.data
        elif index.column () == 1:
            return item.label
        else:
            return item.id
    def showNode (self, state, node):
        node.visible = state
        node.labelVisible = (node.special or (state and self.root.labelsCheckbox.checkState () == Qt.Checked))
        node.hiding = not state

        if state:
            self.root.unhideNodes ([node.index], echoToTree = False, putInUndoBuffer = (node.index != self.root.centerNode ()), redisplay = False)
        else:
            self.root.hideNodes ([node.index], echoToTree = False, putInUndoBuffer = (node.index != self.root.centerNode ()), redisplay = False)
    def setData (self, index, value, role):
        # If a display task is running, interrupt it and wait for it to stop
        self.root.interruptLayoutsAndWaitForCompletion ()

        if not index.isValid ():
            return None

        item = self.itemdict [index.internalId ()]

        if role == Qt.CheckStateRole:
            self.root.busyCursor (True)

            if item.childCount () == 0:
                if int (item.id) == self.root.centerNode ():
                    _checkState = Qt.Checked
                else:
                    if value or item.checked == Qt.Unchecked:
                        _checkState = Qt.Checked
                    else:
                        _checkState = Qt.Unchecked
            else:
                if item.checked == Qt.Unchecked:
                    _checkState = Qt.Checked
                elif item.checked == Qt.PartiallyChecked:
                    _checkState = Qt.Checked
                else:
                    _checkState = Qt.Unchecked

            _centerNodeItem = self.propagateToggleStateDown (_checkState, item)

            if _checkState == Qt.Unchecked and _centerNodeItem:
                self.propagateToggleStateUp (Qt.PartiallyChecked, _centerNodeItem)

            self.propagateToggleStateUp (_checkState, item)
            self.dataChanged.emit (QModelIndex (), QModelIndex ())
            self.root.updateSelectionsAndHideButtons ()
            
            if not isinstance (self.root.layoutType (), Galaxy):
                self.root.doLayout ()

            self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
            self.root.busyCursor (False)
            return True
        elif role == QtCore.Qt.DisplayRole:
            return None
        else:
            return None
    def propagateToggleStateDown (self, checkState, item):
        _centerNodeItem = None

        if item.childCount () == 0:
            if int (item.id) == self.root.centerNode ():
                self.showNode (True, self.root.nodes [int (item.id)])
                item.checked = Qt.Checked
                _centerNodeItem = item
            else:
                self.showNode (checkState == Qt.Checked, self.root.nodes [int (item.id)])
                item.checked = checkState
        else:
            item.checked = checkState

            for subItem in item.children ():
                if subItem.checked != checkState:
                    _maybeCenterNode = self.propagateToggleStateDown (checkState, subItem)

                    if _maybeCenterNode:
                        _centerNodeItem = _maybeCenterNode

        return _centerNodeItem
    def propagateToggleStateUp (self, checkState, item):
        _parent = item.parent ()

        if _parent == None:
            return

        if _parent.checked == checkState:
            return

        _propagate = checkState

        for subItem in _parent.children ():
            if subItem.checked == Qt.PartiallyChecked:
                _propagate = Qt.PartiallyChecked
                break
            elif subItem.checked != checkState:
                _propagate = Qt.PartiallyChecked
                break

        _parent.checked = _propagate
        self.propagateToggleStateUp (_propagate, _parent)
    def flags (self, index):
        if not index.isValid ():
            return QtCore.Qt.ItemIsEnabled

        try:
            item = self.itemdict [index.internalId ()]
        except:
            return self.userCheckable | Qt.ItemIsTristate

        if item.childCount ():
            return self.userCheckable | Qt.ItemIsTristate
        else:
            return self.userCheckable | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
    def headerData (self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Timeseries'
            elif section == 1:
                return 'Label'
            else:
                return 'Id'

        return None
    def index (self, row, column, parent):
        if parent.isValid ():
            _parent = self.itemdict [parent.internalId ()]
        else:
            _parent = self.treeRoot

        child = _parent.child (row)

        if child:
            _index = self.createIndex (row, column, child)
            self.itemdict [_index.internalId ()] = child
            return _index
        else:
            return QtCore.QModelIndex ()
    def parent (self, index):
        if not index.isValid ():
            return QtCore.QModelIndex ()

        try:
            child = self.itemdict [index.internalId ()]
        except:
            return QtCore.QModelIndex ()

        myParent = child.parent ()

        if myParent == self.treeRoot:
            return PySide.QtCore.QModelIndex ()

        _index = self.createIndex (myParent.row (), 0, myParent)
        self.itemdict [id (_index)] = myParent
        return _index
    def rowCount (self, parent):
        if not parent.isValid ():
            _parent = self.treeRoot
        else:
            try:
                _parent = self.itemdict [parent.internalId ()]
            except:
                return 0

        return _parent.childCount ()
    def printTree (self, indent, node):
        print (' ' * indent, node.data, node.label, node.id)

        for child in node.myChildren:
            self.printTree (indent + 2, child)
    def addNode (self, root, data, parent):
        timeseriesString, timeseriesLabel, timeseriesId = data
        timeseriesString += ':' + timeseriesLabel
        timeseriesHierarchy = re.split (' *: *', timeseriesString)

        node = root
        depth = len (timeseriesHierarchy)
        currentDepth = 0

        for categoryPart in timeseriesHierarchy:
            currentDepth += 1
            foundNode = self.findNode (node, categoryPart)

            if foundNode:
                node = foundNode
            else:
                if currentDepth == depth:
                    node = TreeItem (self.root, categoryPart, timeseriesLabel, timeseriesId, node)
                else:
                    node = TreeItem (self.root, categoryPart, '', '', node)

                self.root.newSelector.nodeDictionary [timeseriesId] = node
                self.itemdict [id (node)] = node

        return node
    def findNode (self, root, level):
        if root:
            for subnode in root.myChildren:
                if subnode.data == level:
                    return subnode

        return None

class InversionTreeNode ():
    def __init__ (self, text, index):
        self.text = text
        self.index = index
        self.elements = set (a.strip () for a in text.split (':'))
        self.category = ''
        self.level = 0

class NewSelector (QTreeView):
    def __init__ (self, root, parent = None):
        QTreeView.__init__ (self, parent)
        self.root = root
        self.iconPixmap = QPixmap (':/images/Resources/add32x32.png')
        self.dragStartPosition = 0
        self.setDragEnabled (True)
        self.setDragDropMode (QAbstractItemView.DragOnly)
        self.nodeDictionary = dict ()
        self.model = None
        self.setHeaderHidden (True)
        #self.setMouseTracking (True)
        self.mouseIsPressed = False
        self.dragInProgress = False
    def currentChanged (self, current, previous):
        _currentItem = self.model.itemdict [current.internalId ()].id

        if _currentItem != '':
            _currentItemId = int (_currentItem)

            try:
                Ellipse.hoverEnterEvent (self.root.nodes [_currentItemId].galaxy.graphic, None)
                Ellipse.hoverEnterEvent (self.root.nodes [_currentItemId].social.graphic, None)
                Ellipse.hoverEnterEvent (self.root.nodes [_currentItemId].cluster.graphic, None)
            except:
                None

        if previous.isValid ():
            _previousItem = self.model.itemdict [previous.internalId ()].id

            try:
                if _previousItem != '':
                    _previousItemId = int (_previousItem)
                    Ellipse.hoverLeaveEvent (self.root.nodes [_previousItemId].galaxy.graphic, None)
                    Ellipse.hoverLeaveEvent (self.root.nodes [_previousItemId].social.graphic, None)
                    Ellipse.hoverLeaveEvent (self.root.nodes [_previousItemId].cluster.graphic, None)
            except:
                None
    def mousePressEvent (self, event):
        QTreeView.mousePressEvent (self, event)
        self.dragStartPosition = event.pos ()
    def mouseMoveEvent (self, event):
        if not (event.buttons () & Qt.LeftButton):
            return

        if (self.dragStartPosition - event.pos ()).manhattanLength () < 100:
            return

        self.mouseIsPressed = False
        self.dragInProgress = True

        self.mimeData = QMimeData ()
        _selectedIndexes = self.selectedIndexes ()
        _string = ''

        for _index in _selectedIndexes:
            _item = self.model.itemdict [_index.internalId ()]

            if _item.childCount () == 0:
                _id = _item.id
                _string += ',%d' % (_id)

        if len (_string):
            _string = _string [1:]
            self.mimeData.setData ('text/plain', PySide.QtCore.QByteArray (str (_string)))
            _drag = QDrag (self)
            _drag.setMimeData (self.mimeData)
            _dropAction = _drag.exec_ (Qt.CopyAction)
            self.dragInProgess = False
    def treeInversionSort (self, nodes):
        _maxLevel = 1
        _emptyRows = 0
        _totalRows = len (nodes)

        while _emptyRows < _totalRows:
            while True:
                _frequencies = dict ()

                for _row in nodes:
                    if _row.level < _maxLevel:
                        for _element in _row.elements:
                            if _element in _frequencies:
                                _frequencies [_element] += 1
                            else:
                                _frequencies [_element] = 1

                _frequencies = sorted (((value,key) for (key,value) in _frequencies.items ()))

                if len (_frequencies) == 0:
                    _maxLevel += 1
                else:
                    break

            _maxLevel = 0

            if len (_frequencies) == 0:
                break

            for _row in nodes:
                _tag = _frequencies [-1] [1]

                if _tag in _row.elements:
                    _row.elements.remove (_tag)
                    _row.category += _tag + ':'
                    _row.level += 1

                    if len (_row.elements) == 0:
                        _emptyRows += 1

                    if _row.level > _maxLevel:
                        _maxLevel = _row.level

        for _row in nodes:
            _row.category = _row.category [:-1]

        return nodes
    def treeInversionMakeNodes (self):
        _nodes = []

        for _index in range (self.root.N):
            _timeseries = self.root.tss.getseries (_index)
            _nodes.append (InversionTreeNode (_timeseries.category () + ':' + _timeseries.label (), _index))

        return _nodes
    def contextMenuEvent (self, event): # Display a contextual help popup
        _menu = QMenu ()

        # Set color
        _setColorAction = _menu.addAction ('Set colour')
        QtCore.QObject.connect (_setColorAction, QtCore.SIGNAL ('triggered ()'), self.setColorFromTree)

        # Forecast
        _setForecastAction = _menu.addAction ('Forecast')
        PySide.QtCore.QObject.connect (_setForecastAction, PySide.QtCore.SIGNAL ('triggered ()'), self.forecastFromTree)

        # Hierarchy Up
        #_setPromoteAction = _menu.addAction ('Promote')
        #PySide.QtCore.QObject.connect (_setPromoteAction, PySide.QtCore.SIGNAL ('triggered ()'), self.promoteFromTree)

        _selectedAction = _menu.exec_ (QCursor.pos ())
    def forecastFromTree (self):
        _item = self.model.itemdict [self.currentIndex ().internalId ()]
        self.root.analysisPlot.presetForecast (int (_item.id))
    def promoteFromTree (self):
        _item = self.model.itemdict [self.currentIndex ().internalId ()]
        _originalParent = _item.parent ()

        if _originalParent and _originalParent.data != 'ALL':
            self.model.layoutAboutToBeChanged.emit ()
            _grandparent = _originalParent.parent ()
            _originalParentChildren = _originalParent.children ()

            if _grandparent:
                _grandparent.removeChild (_originalParent)

            for _count, _item in enumerate (_originalParentChildren [:]):
                if _grandparent:
                    _grandparent.appendChild (_item)

                _parent = TreeItem (self.root, _originalParent.data, _item.label, _item.id, _item.parent ())
                self.setTreeColor (_parent, _item.color)
                _children = _item.children () [:]
                _item.setParent (_grandparent)
                _item.setId ('')
                _item.setLabel ('')
                _item.setChildren ([_parent])
                _parent.setParent (_item)

                for _child in _children:
                    _parent.appendChild (_child)
                    _child.setParent (_parent)
                    self.setTreeColor (_child, _child.color)

            # Maybe there are now several nodes at the same level and with the same name. Merge them.
            if _grandparent:
                _repeats = dict ()

                for _node in _grandparent.children ():
                    if _node.data in _repeats:
                        _repeats [_node.data] += 1
                    else:
                        _repeats [_node.data] = 1

                for _key, _value in _repeats.items ():
                    if _value > 1:
                        _found = None

                        for _node in _grandparent.children () [:]:
                            if _node.data == _key:
                                if _found:
                                    for _child in _node.children ():
                                        _child.setParent (_found)
                                        _found.appendChild (_child)
                                        self.setTreeColor (_child, _child.color)

                                    _node.parent ().removeChild (_node)
                                    del _node
                                else:
                                    _found = _node

            self.expand ()
            self.model.layoutChanged.emit ()
    def setTreeColor (self, item, color):
        # Sets the colors of all leaves in this branch
        try:
            idValue = int (item.id)
            self.root.setNodeColor (int (item.id), color)
            item.color = color
        except:
            for child in item.children ():
                self.setTreeColor (child, color)
                item.color = color

        _parent = item.parent ()

        while _parent:
            for subItem in _parent.children ():
                if subItem.color == color:
                    _propagate = color
                else:
                    _propagate = QColor ()
                    break

            _parent.color = _propagate
            _parent = _parent.parent ()
    def setColorFromTree (self):
        _item = self.model.itemdict [self.currentIndex ().internalId ()]
        _color = QColorDialog.getColor (Qt.black, self, 'Set Node Color')
        self.setTreeColor (_item, _color)

        if isinstance (self.root.layoutType (), Galaxy):
            #self.root.galaxy.view.doLayout (self.root.galaxyLayoutThread.task_cutoffCentralLinksSignal)
            self.root.galaxy.view.mainThread.directDisplay ()
        else:
            self.root.doLayout ()
    def dumpNode (self, node, indent):
        if (node.id):
            print ('%s%s [%s] %s' % (' ' * indent, node.data, node.label, node.id))
        else:
            print ('%s%s' % (' ' * indent, node.data))

        for _child in node.children:
            self.dumpNode (_child, indent + 2)
    def dumpTree (self):
        self.dumpNode (self.root.newSelector.model.treeRoot, 0)
    def expand (self):
        self.expandAll ()
    def collapse (self):
        self.collapseAll ()
    def selectEverything (self):
        self.selectAll ()
    def selectNone (self):
        self.clearSelection ()
    def zapChildren (self, node):
        try:
            for _child in node.children ():
                self.zapChildren (_child)
        except:
            None

        node.children = None
        node.parent = None
        node.data = None
        node.id = None
        node.selected = None
        node.label = None
    def loadTree (self):
        loadTreeMonitor = ConciseMonitor()
        # Remove any previous tree
        if self.model:
            self.zapChildren (self.root)

        _categoryData = [] 

        if self.root.db:
            _series = self.root.tss.getseries

            for i in range (self.root.N):
                _seriesElement = _series (i)
                _categoryData.append ([_seriesElement.category (), _seriesElement.label (), i])

        self.loadTreeAsIs (_categoryData)
        loadTreeMonitor.report ('loadTree')
    def loadTreeAsIs (self, categoryData):
        self.root.categoryData = categoryData
        self.model = TreeModel (self.root, categoryData)
        self.setModel (self.model)
        self.hideColumn (1)
        self.hideColumn (2)
        self.setAnimated (True)
        self.setUniformRowHeights (True)
        self.collapseAll ()
        self.setSelectionMode (QTreeView.ExtendedSelection)
        self.setAllColumnsShowFocus (True)
    def selectionChanged (self, selected, deselected):
        for _index in selected.indexes ():
            _item = self.model.itemdict [_index.internalId ()]

            if _item.childCount () == 0:
                self.root.nodes [int (_item.id)].selected = True

        for _index in deselected.indexes ():
            _item = self.model.itemdict [_index.internalId ()]

            if _item.childCount () == 0:
                self.root.nodes [int (_item.id)].selected = False

        self.model.dataChanged.emit (QModelIndex (), QModelIndex ())
    def mouseDoubleClickEvent (self, event):
        _index = self.indexAt (event.pos ())

        try:
            _item = self.model.itemdict [_index.internalId ()]
        except:
            return

        if _item.childCount () == 0:
            _node = self.root.nodes [int (_item.id)]
            self.root.setCenterNode (_node.index)
            self.model.setData (_index, True, Qt.CheckStateRole)

class WaitMessage (QGraphicsSimpleTextItem):
    def __init__ (self, scene):
        QGraphicsSimpleTextItem.__init__ (self, '')
        self.setPen (QColor ('grey'))
        self.setBrush (QColor ('yellow'))
        self.setFont (QFont ('lucida', 38))
        self.setZValue (1000000)
        self.setPos (QPointF (-250, -20))
        scene.addItem (self)
        self.hide ()
    def display (self, message):
        self.setText (message)
        self.show ()

#################################################################################
# This is the Brand Communities main window
#################################################################################
class BrandCommunities (QMainWindow): 
    def __init__ (self, application, appname):
        QMainWindow.__init__(self)

        self.setDockOptions (QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks) # QMainWindow::AllowTabbedDocks | QMainWindow::ForceTabbedDocks | QMainWindow::VerticalTabs
        self.dummyLayoutControlPanels = [] # Put Layout Control Panels here if they are not used (facilities management)
        self.loadingFile = False
        #self.ancestor = self # This is needed for the TimeSlider to work

        # Forecasting
        self.forecastingTargets = []
        self.forecastingSources = []
        self.forecastingSourceReferences = dict ()
        self.forecastingTargetSourceRelationships = dict ()
        self.forecastingGraphs = dict ()
        self.addInfluences = 5

        # Show timings
        _showTiming = getArgv ('timing')
        ConciseMonitor.enable (_showTiming)
        resource_usage = ConciseMonitor ()

        self.application = application
        #self.savingOfCategoryTree = False
        self.loadedTimeslice = -1
        self.displayedLastTime = []
        self.nodeFontSize = 10
        self.nodeHighlightFontSize = 12
        self.message = dict ()

        # constants
        self.SOCIAL = 0
        self.CLUSTER = 1
        self.constants = constants.Constants ()
        self.constants._load_ ()

        # Docking windows
        try:
            self.constants.facilitiesKey
        except:
            print 'Please ensure that facilitiesKey is defined in the .bc_profile file (in your home directory). If you do not know how to do this, just delete that .bc_profile file.'
            self.leave ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_SELECTIONTREE:
            self.selectionTreeWindow = DockingWindow ("Selection Tree", self, Qt.LeftDockWidgetArea)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_COMMONCONTROLS:
            self.commonControlsWindow = DockingWindow ("Common Controls", self, Qt.LeftDockWidgetArea)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_TIMEDIMENSION:
            self.timeDimensionWindow = DockingWindow ("Time Dimension", self, Qt.RightDockWidgetArea)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_LAYOUTCONTROLS:
            self.layoutSpecificControlsWindow = DockingWindow ("Layout Controls", self, Qt.RightDockWidgetArea)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_SEEKNODE:
            self.seekNodeWindow = DockingWindow ("Seek node", self, Qt.LeftDockWidgetArea)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_XYASSOCIATIONS:
            self.associationWindow = DockingWindow ("XY Associations", self, Qt.RightDockWidgetArea)
        # END OF docking windows

        self.CENTRIFUGE_INSTRUMENTED = False
        self.LOAD_INSTRUMENTED = False

        # Define the currently-selected layout
        self.layoutTypeId = 0
        self.layoutTypeSelectionList = []
        self.layoutSelectionList = []

        # Create the help dialog
        self.helpDialog = HelpDialog ()
        self.helpDialog.setWindowTitle ("Help")
    
        # Keep a list of all selected nodes
        self.selectionList = []
        self.seriesLabels = []

        # Make sure we know we have no data at startup
        self.db = None
        self.nodes = []
        self.N = 0

        # Install an event filter to recognise when the CTRL button is pressed. We use this to switch to
        # rubber band selection in the Universe graph instead of panning
        self.keyPressFilter = KeyFilter (self)
        self.installEventFilter (self.keyPressFilter)

        self.mac = (os.name == "mac")
        self.menubar = MenuBar (self.mac, self)
        self.setMenuBar (self.menubar)

        self.connect (self, SIGNAL ('closeTheApp ()'), SLOT ('close ()'))
        self.setWindowTitle ("Brand Communities")

        self.tabPaneContainerWidget = QWidget ()
        self.tabPaneContainer = QVBoxLayout ()
        self.tabPaneContainerWidget.setLayout (self.tabPaneContainer)
        self.setCentralWidget (self.tabPaneContainerWidget)

        self.mainPanel = QTabWidget (self)
        self.mainPanel.setTabPosition (QTabWidget.West)
        self.tabPaneContainer.addWidget (self.mainPanel)
        _color = self.constants.tabBarColor
        self.mainPanel.tabBar ().setStyleSheet ('background-color: rgb(%d,%d,%d)' % (_color.red (), _color.green (), _color.blue ()) +
                                                '; font-size: %dpx' % (self.constants.tabBarFontSize))

        # Stuff for LsRadial layout
        self.SCALING = 200.0
        self.OFFSET = 50.0
        self.MAX_CROSSLINK_LENGTH = 2.0 * (self.SCALING + self.OFFSET)
        self.TOTAL_SCALING = self.SCALING + self.OFFSET
        self.MINIMUM_SEPARATION = 50
        self.MINIMUM_SEPARATION_SQUARED = math.pow (self.MINIMUM_SEPARATION, 2)

        # Add the layout panes
        self.galaxy = Galaxy (self)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_CENTRIFUGE:
            self.defineLayoutType ('Centrifuge', self.galaxy)
            self.mainPanel.addTab (self.galaxy, 'Centrifuge')

        # Forecasting
        self.analysisPlot = analysis.AnalysisPlot (self)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_ANALYSIS:
            self.defineLayoutType ('analysis', self.analysisPlot)
            self.mainPanel.addTab (self.analysisPlot, 'Forecasting')

        self.xyPlot = XYPlot (self)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_XY:
            self.defineLayoutType ('XYgraph', self.xyPlot)
            self.mainPanel.addTab (self.xyPlot, 'XY Graph')

        # Make the text of the tabs a non-standard color
        for _tabIndex in range (self.mainPanel.tabBar ().count ()):
            self.mainPanel.tabBar ().setTabTextColor (_tabIndex, self.constants.tabBarFontColor)

        # Define common controls
        self.controlButtons = self.makeControlButtons ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_COMMONCONTROLS:
            self.commonControlsWindow.setWidget (self.controlButtons)

        self.social = Social (self)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_NETWORK:
            self.defineLayoutType ('Network', self.social)
            self.mainPanel.addTab (self.social, 'Domino')

        self.message [self.SOCIAL] = WaitMessage (self.social.view.scene)

        self.cluster = Cluster (self)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_COMMUNITIES:
            self.defineLayoutType ('Communities', self.cluster)
            self.mainPanel.addTab (self.cluster, 'Communities')

        self.message [self.CLUSTER] = WaitMessage (self.cluster.view.scene)

        self.xyForecastPlot = XYForecastPlot (self)

        
        # Make the color of Domino and Communities tab into red and green to highlight they are work in progress
        for _tabIndex in range (3,5):
            self.mainPanel.tabBar ().setTabTextColor  (_tabIndex, 'red')

        

        # Define the XY Association pane
        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_XYASSOCIATIONS:
            self.associationWindow.setWidget (self.xyPlot.view.selector)

        # Define the node seek pane
        self.seekNodePane = self.makeSeekNodeControls ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_SEEKNODE:
            self.seekNodeWindow.setWidget (self.seekNodePane)

        # Define the time dimension pane
        self.timeDimensionPane = self.makeTimeDimensionControls ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_TIMEDIMENSION:
            self.timeDimensionWindow.setWidget (self.timeDimensionPane)

        # Define the layout specific pane
        self.layoutSpecificPane = self.makeLayoutControlButtons ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_LAYOUTCONTROLS:
            self.layoutSpecificControlsWindow.setWidget (self.layoutSpecificPane)
        ##################### End of docking panes

        self.xyPlot.view.setupTimeLine ()
        self.categoryData = []
        self.selectorPage (self.mainPanel)

        # Make an undo buffer for node hiding
        self.undoBuffer = UndoBuffer (self)

        # Kick off some threads
        self.socialLayoutThread = SocialNetworkLayoutThread (self)
        self.galaxyLayoutThread = GalaxyLayoutThread (self)
        self.clusterLayoutThread = ClusterLayoutThread (self)
        self.socialLayoutThread.suspendRedraw (True)
        self.clusterLayoutThread.suspendRedraw (True)
        self.galaxyLayoutThread.start ()

        # Initialise the model
        self._init_model_ (appName)

        self.profileName = self.app.userName
        self.connect (self.mainPanel, SIGNAL ('currentChanged (int)'), self.setLayoutTypeById)

        # We recycle some Qt objects to avoid recreating them all the time. A sort of cache.
        self.linkStore = []
        self.circleStore = []
        self.nodeStore = []

        # Is there a database named on the command line?
        if self.constants.facilitiesKey & self.constants.FACILITIES_FILE_COMMANDLINE:
            _filename = getArgv ()

            if _filename:
                if _filename [-4:] == '.bcc':
                    _config = dict ()
                    _temporaryBcFiles = BcFiles (self, stub = True)
                    self.bcFiles = _temporaryBcFiles.loadConfigurationFromNamedFile (_filename)
                else:
                    self.loadNewDatabase (_filename)
            else:
                self.bcFiles = None

        self.socialLayoutThread.suspendRedraw (False)
        self.galaxyLayoutThread.suspendRedraw (False)
        self.clusterLayoutThread.suspendRedraw (False)

        resource_usage.report('Main Window')
    #def dumpWindow (self, windowId):
    #    pixmap = QPixmap.grabWindow (windowId)
    #    print pixmap
    def redrawCosmeticLinks (self):
        if not self.loadingFile:
            if isinstance (self.layoutType (), Social) or isinstance (self.layoutType (), Cluster):
                self.doLayout ()

            self.galaxy.view.mainThread.directDisplay ()
    def selectGraphic (self, node, state):
        try:
            if state != node.graphic.isSelected ():
                node.graphic.setSelected (state)
        except:
            """print 'EXCEPTION'"""
    def selectAll (self):
        for _node in self.nodes:
            self.selectGraphic (_node.galaxy, False)
            self.selectGraphic (_node.social, False)
            self.selectGraphic (_node.cluster, False)

        for _nodeIndex in self.layoutType ().view.visibleNodeDetails.nodeList ():
            _node = self.nodes [_nodeIndex]
            self.selectGraphic (_node.galaxy, True)
            self.selectGraphic (_node.social, True)
            self.selectGraphic (_node.cluster, True)
    def updateSelectionsAndHideButtonsForGalaxy (self):
        _nodesForSelection = set (self.selectionList)

        try:
            _visibleNodes = set (self.galaxy.view.visibleNodeDetails.nodeList ())
            _selectedNodes = list (_nodesForSelection & _visibleNodes)
            _unselectedNodes = list (_visibleNodes - _nodesForSelection)

            #print _visibleNodes # amar
            

            for _nodeIndex in _selectedNodes:
                print 'amar Galaxy' + str(_nodeIndex)
                _node = self.nodes [_nodeIndex]
                self.selectGraphic (_node.galaxy, True)

            for _nodeIndex in _unselectedNodes:
                _node = self.nodes [_nodeIndex]
                self.selectGraphic (_node.galaxy, False)
        except:
            pass
            #print 'PROBLEM: 1768'
        else:
            self.galaxy.updateStatus ()

        _visibleNodes = set (self.galaxy.view.visibleNodeDetails.nodeList ())
        _selectedNodes = len (_nodesForSelection & _visibleNodes)
        _unselectedNodes = len (_visibleNodes - _nodesForSelection)
        self.menubar.hideSelectedButton.setEnabled (_selectedNodes)
        self.menubar.hideSelectedItem.setEnabled (_selectedNodes)
        self.menubar.hideUnselectedButton.setEnabled (_unselectedNodes)
        self.menubar.hideUnselectedItem.setEnabled (_unselectedNodes)
    def updateSelectionsAndHideButtonsForSocial (self):
        _nodesForSelection = set (self.selectionList)

        try:
            _visibleNodes = set (self.social.view.visibleNodeDetails.nodeList ())
            _selectedNodes = list (_nodesForSelection & _visibleNodes)
            _unselectedNodes = list (_visibleNodes - _nodesForSelection)

            for _nodeIndex in _selectedNodes:
                _node = self.nodes [_nodeIndex]
                self.selectGraphic (_node.social, True)

            for _nodeIndex in _unselectedNodes:
                _node = self.nodes [_nodeIndex]
                self.selectGraphic (_node.social, False)
        except:
            pass
            #print 'PROBLEM: 1769'
        else:
            self.social.updateStatus ()

        _visibleNodes = set (self.social.view.visibleNodeDetails.nodeList ())
        _selectedNodes = len (_nodesForSelection & _visibleNodes)
        _unselectedNodes = len (_visibleNodes - _nodesForSelection)
        self.menubar.hideSelectedButton.setEnabled (_selectedNodes)
        self.menubar.hideSelectedItem.setEnabled (_selectedNodes)
        self.menubar.hideUnselectedButton.setEnabled (_unselectedNodes)
        self.menubar.hideUnselectedItem.setEnabled (_unselectedNodes)
    def updateSelectionsAndHideButtonsForCluster (self):
        _nodesForSelection = set (self.selectionList)

        try:
            _visibleNodes = set (self.cluster.view.visibleNodeDetails.nodeList ())
            _selectedNodes = list (_nodesForSelection & _visibleNodes)
            _unselectedNodes = list (_visibleNodes - _nodesForSelection)

            for _nodeIndex in _selectedNodes:
                _node = self.nodes [_nodeIndex]
                self.selectGraphic (_node.cluster, True)

            for _nodeIndex in _unselectedNodes:
                _node = self.nodes [_nodeIndex]
                self.selectGraphic (_node.cluster, False)
        except:
            pass
            #print 'PROBLEM: 1770'
        else:
            self.cluster.updateStatus ()

        _visibleNodes = set (self.cluster.view.visibleNodeDetails.nodeList ())
        _selectedNodes = len (_nodesForSelection & _visibleNodes)
        _unselectedNodes = len (_visibleNodes - _nodesForSelection)
        self.menubar.hideSelectedButton.setEnabled (_selectedNodes)
        self.menubar.hideSelectedItem.setEnabled (_selectedNodes)
        self.menubar.hideUnselectedButton.setEnabled (_unselectedNodes)
        self.menubar.hideUnselectedItem.setEnabled (_unselectedNodes)
    def updateSelectionsAndHideButtons (self):
        _type = self.layoutType ()

        if isinstance (_type, Cluster):
            self.updateSelectionsAndHideButtonsForCluster ()
        elif isinstance (_type, Social):
            self.updateSelectionsAndHideButtonsForSocial ()
        elif isinstance (_type, Galaxy):
            self.updateSelectionsAndHideButtonsForGalaxy ()
            #self.root.galaxy.view.mainThread.directDisplay ()
    def unhideNodes (self, nodeList, putInUndoBuffer = True, echoToTree = True, redisplay = True):
        _hiddenNodes = list (set (nodeList [:]))

        if len (_hiddenNodes):
            self.interruptLayoutsAndWaitForCompletion ()

            for _nodeIndex in _hiddenNodes:
                _node = self.nodes [_nodeIndex]

                if _nodeIndex in self.selectionList:
                    self.selectionList.remove (_nodeIndex)

                if echoToTree:
                    _node.selectorTreeNode.checked = Qt.Checked
                    self.newSelector.model.dataChanged.emit (QModelIndex (), QModelIndex ())
                    self.newSelector.model.propagateToggleStateUp (Qt.Checked, _node.selectorTreeNode)

                _node.hiding = False
                _node.selected = False

            if putInUndoBuffer:
                self.undoBuffer.push (UndoableAction (UndoableAction.SHOW, _hiddenNodes))

            if redisplay:
                self.galaxy.view.doLayout (self.galaxyLayoutThread.task_cutoffCentralLinksSignal)

                if not isinstance (self.layoutType (), Galaxy):
                    self.doLayout ()
    def hideNodes (self, nodeList, putInUndoBuffer = True, echoToTree = True, redisplay = True):
        _hiddenNodes = list (set (nodeList))

        if self.centerNode () in _hiddenNodes:
            _hiddenNodes.remove (self.centerNode ())

        if len (_hiddenNodes):
            self.interruptLayoutsAndWaitForCompletion ()

            for _nodeIndex in _hiddenNodes:
                _node = self.nodes [_nodeIndex]

                if _nodeIndex in self.selectionList:
                    self.selectionList.remove (_nodeIndex)

                if echoToTree:
                    _node.selectorTreeNode.checked = Qt.Unchecked
                    self.newSelector.model.dataChanged.emit (QModelIndex (), QModelIndex ())
                    self.newSelector.model.propagateToggleStateUp (Qt.Unchecked, _node.selectorTreeNode)

                _node.hiding = True
                _node.selected = False

            if putInUndoBuffer:
                self.undoBuffer.push (UndoableAction (UndoableAction.HIDE, _hiddenNodes))

            if redisplay:
                self.galaxy.view.doLayout (self.galaxyLayoutThread.task_cutoffCentralLinksSignal)

                if not isinstance (self.layoutType (), Galaxy):
                    self.doLayout ()
    def undo (self):
        _item = self.undoBuffer.pop ()

        if _item:
            if _item.action == UndoableAction.HIDE:
                _nodeList = _item.data

                for _node in _nodeList:
                    self.nodes [_node].unhideNode ()

                self.refreshUndoRedo ()
            elif _item.action == UndoableAction.SHOW:
                _nodeList = _item.data

                for _node in _nodeList:
                    self.nodes [_node].hideNode ()

                self.refreshUndoRedo ()
            elif _item.action == UndoableAction.CENTER:
                self.setCenterNode (_item.data [0])
                self.refreshUndoRedo ()
            else:
                print ('ERROR: Unrecognised undoable action')
        else:
            print ('ERROR: Attempt to pop beyond end of undo buffer')
    def redo (self):
        _item = self.undoBuffer.redo ()

        if _item:
            if _item.action == UndoableAction.HIDE:
                _nodeList = _item.data

                self.hideNodes (_nodeList, putInUndoBuffer = False)
                self.refreshUndoRedo ()
            elif _item.action == UndoableAction.SHOW:
                _nodeList = _item.data

                self.unhideNodes (_nodeList, putInUndoBuffer = False)
                self.refreshUndoRedo ()
            elif _item.action == UndoableAction.CENTER:
                self.setCenterNode (_item.data [1])
                self.refreshUndoRedo ()
            else:
                print ('ERROR: Unrecognised redoable action')
        else:
            print ('ERROR: Attempt to pop beyond end of redo buffer')
    def loadCoefficients (self):
        self.tss = TimeSeriesSet (self.db, self.tssids [self.timeslice])
        _scenario = self.scenarioSelectorCombo.currentIndex ()
        self.cm = self.tss.loadcoefficients (self.db, self.tss.coeffids () [_scenario])
        self.xyTss = self.tss.clone ()
        self.clusterCm = self.tss.loadcoefficients (self.db, self.tss.coeffids () [_scenario])
    def loadTimeslice (self):
        if self.timeslice != self.loadedTimeslice:
            self.loadCoefficients ()
            self.loadedTimeslice = self.timeslice
    def refreshGraphs (self):
        if not self.loadingFile:
            self.doLayoutA ()
            self.loadTimeslice ()
            self.galaxy.view.doLayout (self.galaxyLayoutThread.task_computeCoefficientsSignal)
            self.doLayoutB ()
            self.analysisPlot.reset ()
    def refreshUndoRedo (self):
        self.updateSelectionsAndHideButtons ()
        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_cutoffCentralLinksSignal)

        if isinstance (self.layoutType (), Cluster):
            self.doLayout ()
        elif isinstance (self.layoutType (), Social):
            self.doLayout ()
    def INSTRUMENT_LOAD (self, text, startTime):
        if not self.LOAD_INSTRUMENTED: return
        print ('%40.40s:%d ms' % (text, (time.time () - startTime) * 1000))
        return time.time ()
    def INSTRUMENT_CENTRIFUGE (self, text, startTime):
        if not self.CENTRIFUGE_INSTRUMENTED: return
        print ('%40.40s:%d ms' % (text, (time.time () - startTime) * 1000))
        return time.time ()
    def loadConfigurationFromNamedFile (self):
        _temporaryBcFiles = BcFiles (self, stub = True)
        self.bcFiles = _temporaryBcFiles.loadConfigurationFromNamedFile ()
    def saveConfigurationToNamedFile (self):
        if self.bcFiles:
            self.bcFiles.saveConfigurationToNamedFile ()
    def addNode (self, root, i, outlineColor, bodyColor, textColor, labelText, font, tipText, radius, infoText):
        return Node (root, i, outlineColor, bodyColor, textColor, labelText, font, tipText, radius, infoText)
    def setToolboxVisibility (self, action, panel, state):
        action.setChecked (state)
        panel.setVisible (state)
    def showAssociationsToolbox (self, state):
        try:
            self.setToolboxVisibility (self.associationWindowToggleViewAction, self.associationWindow, state)
            self.associationWindowToggleViewAction.setChecked (state)
        except:
            pass
    def setLayoutTypeById (self, index):
        if isinstance (self.layoutSelectionList [index], Cluster):
            if self.checkIfClusterOperationLikelyToBeSlowAndBlocking ():
                self.displayAlgoSpecificPanel (self.layoutTypeId)
                self.mainPanel.setCurrentIndex (self.layoutTypeId)
                return
        else:
            # If we choose anything other than the cluster graph, ensure the clustering stops
            self.clusterLayoutThread.interrupt ()
            #self.clusterLayoutThread.wait ()

        self.layoutTypeId = index
        self.displayAlgoSpecificPanel (index)
        self.mainPanel.setCurrentIndex (index)

        if isinstance (self.layoutType (), Galaxy):
            self.showAssociationsToolbox (False)
            self.linksCheckbox.setEnabled (True)
            self.linkQuantityTextField.setEnabled (True)

            if self.linksCheckbox.isChecked ():
                self.arrowheadsCheckbox.setEnabled (True)
            else:
                self.arrowheadsCheckbox.setEnabled (False)
        elif isinstance (self.layoutType (), analysis.AnalysisPlot):
            self.showAssociationsToolbox (False)
            self.linksCheckbox.setEnabled (False)
            self.linkQuantityTextField.setEnabled (False)
            self.arrowheadsCheckbox.setEnabled (False)
        elif isinstance (self.layoutType (), XYPlot):
            self.xyForecastPlot.panel.takeAt (0)
            self.xyPlot.view.setParent (None)
            self.xyPlot.panel.insertLayout (0, self.xyForecastPlot.view)
            self.showAssociationsToolbox (True)
            self.linksCheckbox.setEnabled (False)
            self.linkQuantityTextField.setEnabled (False)
            self.arrowheadsCheckbox.setEnabled (False)

            if self.db:
                self.layoutType ().view.mainThread.layout ()
        #elif isinstance (self.layoutType (), XYForecastPlot):
        #    self.xyPlot.panel.takeAt (0)
        #    self.xyForecastPlot.panel.insertLayout (0, self.xyPlot.view)
        #    self.showAssociationsToolbox (True)
        #    self.linksCheckbox.setEnabled (False)
        #    self.linkQuantityTextField.setEnabled (False)
        #    self.arrowheadsCheckbox.setEnabled (False)
        #
        #    if self.db:
        #        self.layoutType ().view.mainThread.layout ()
        elif isinstance (self.layoutType (), Social):

            self.displayCancellableMessageBox ('Domino Tab', "This module has not been activated and is not yet licensed to this user. Please contact your BC representative should you wish to activate it. It will still produce indicative displays, so please feel free to \'play\'.")           

            # Amar
            # self.message [self.SOCIAL].display ('Under Development')
            
            self.showAssociationsToolbox (False)
            self.linksCheckbox.setEnabled (True)
            self.linkQuantityTextField.setEnabled (False)
            self.arrowheadsCheckbox.setEnabled (True)

            if not self.loadingFile:
                self.doLayout ()
        elif isinstance (self.layoutType (), Cluster):
            self.displayCancellableMessageBox ('Communities Tab', "This module has not been activated and is not yet licensed to this user. Please contact your BC representative should you wish to activate it. It will still produce indicative displays, so please feel free to \'play\'.")           

            # Amar
            #self.message [self.SOCIAL].display ('Under Development')
            # Make sure we're not in the middle of a clustering
            self.clusterLayoutThread.interrupt ()
            self.clusterLayoutThread.wait ()
            self.showAssociationsToolbox (False)
            self.linksCheckbox.setEnabled (True)
            self.linkQuantityTextField.setEnabled (False)
            self.arrowheadsCheckbox.setEnabled (False)

            if not self.loadingFile:
                self.doLayout ()
        else:
            print 'Error: unrecognized layout type'

        self.updateSelectionsAndHideButtons ()
    # doLayout is split into doLayoutA and doLayoutB. Either call doLayout or call doLayout before a time-consuming operation and then call doLayoutB
    def doLayoutA (self):
        if not self.db:
            return

        if isinstance (self.layoutType (), Cluster):
            _layoutType = self.CLUSTER
        elif isinstance (self.layoutType (), Social):
            _layoutType = self.SOCIAL
        else:
            return

        self.clusterLayoutThread.interrupt ()
        self.clusterLayoutThread.wait ()
        self.layoutType ().view.setUpdatesEnabled (False)
        self.message [_layoutType].display ('Please wait...')
        self.layoutType ().view.setUpdatesEnabled (True)
        self.application.processEvents ()
    def doLayoutB (self):
        if self.db:
            if isinstance (self.layoutType (), Cluster) or isinstance (self.layoutType (), Social):
                QtCore.QTimer.singleShot (50, self.layoutType ().view.mainThread.layout)
    def doLayout (self):
        if not self.db:
            return

        if isinstance (self.layoutType (), Cluster):
            _layoutType = self.CLUSTER
        elif isinstance (self.layoutType (), Social):
            _layoutType = self.SOCIAL
        else:
            return

        self.clusterLayoutThread.interrupt ()
        self.clusterLayoutThread.wait ()

        if not _layoutType in self.message:
            self.message [_layoutType] = WaitMessage (self.layoutType ().view.scene)

        if len (self.nodes) > 50:
            self.message [_layoutType].display ('Please wait...')

        QtCore.QTimer.singleShot (50, self.layoutType ().view.mainThread.layout)
    def setLayoutType (self, text):
        self.layoutTypeId = self.layoutTypeSelectionList.index (text)
        self.mainPanel.setCurrentIndex (self.layoutTypeId)
    def defineLayoutType (self, text, objectItem):
        self.layoutTypeSelectionList.append (text)
        self.layoutSelectionList.append (objectItem)
        self.layoutTypeId = len (self.layoutTypeSelectionList) - 1
    def layoutTypeString (self):
        return self.layoutTypeSelectionList [self.layoutTypeId]
    def layoutType (self):
        return self.layoutSelectionList [self.layoutTypeId]
    def layoutTypeId (self):
        return self.layoutTypeId
    def busyCursor (self, state):
        if state:
            self.setCursor (Qt.WaitCursor)
            self.update ()
        else:
            self.unsetCursor ()
    def setCenterNode (self, nodeId = None):
        self.centralNodeIndex = nodeId
    def centerNode (self):
        try:
            return self.centralNodeIndex
        except:
            return 0
    def limitRangeOfCenterNode (self):
        if self.centerNode () >= self.N:
            self.setCenterNode (0)
        elif self.centerNode () < 0:
            self.setCenterNode (0)
    def interruptLayoutsAndWaitForCompletion (self):
        self.clusterLayoutThread.interrupt ()
        self.socialLayoutThread.interrupt ()
        self.socialLayoutThread.wait ()
        self.clusterLayoutThread.wait ()
    def setNodeColor (self, nodeId, color):
        radius = self.nodes [nodeId].radius
        gradient = QRadialGradient (0, 0, radius, -radius, -radius);
        gradient.setColorAt (0, color.lighter ().lighter ())
        gradient.setColorAt (1, color)
        self.nodes [nodeId].brush = QBrush (gradient)
        self.nodes [nodeId].pen = QPen (QColor (self.constants.nodeOutlineColor))
        self.nodes [nodeId].bodyColor = color
        return self.nodes [nodeId].brush
    def setNodeColors (self, nodeId):
        _color = QColorDialog.getColor (self.nodes [nodeId].brush.color (), self, 'Set Node Color')

        if _color.isValid ():
            if not nodeId in self.selectionList:
                self.setNodeColor (nodeId, _color)
                self.newSelector.setTreeColor (self.nodes [nodeId].selectorTreeNode, _color)

            for i in self.selectionList:
                self.setNodeColor (i, _color)
                self.newSelector.setTreeColor (self.nodes [i].selectorTreeNode, _color)
    def numberListToCommaSeparatedString (self, list):
        _result = ''

        for _item in list: 
            if len (_result):
                _result += ',' + str (_item)
            else:
                _result = str (_item)

        return _result
    def selectorPage (self, tabWidget):
        self.selectionTreeWidget = QWidget ()
        _layout = QGridLayout (self.selectionTreeWidget)
        self.newSelector = NewSelector (self)
        #self.popupTreeSelectorDialog = PopupTreeSelectorDialog (self)
        _layout.addWidget (self.newSelector, 0, 0, 1, 2)

        _collapse = QPushButton ('Collapse all')
        _layout.addWidget (_collapse, 1, 0)
        QObject.connect (_collapse, SIGNAL ('clicked ()'), self.newSelector.collapse)

        _expand = QPushButton ('Expand all')
        _layout.addWidget (_expand, 1, 1)
        QObject.connect (_expand, SIGNAL ('clicked ()'), self.newSelector.expand)

        if self.constants.facilitiesKey & self.constants.FACILITIES_TOOL_SELECTIONTREE:
            self.selectionTreeWindow.setWidget (self.selectionTreeWidget)
    def configWarning (self, message):
        """ We don't show these messages anymore """
    def displayCancellableMessageBox (self, title, message):
        self.cancellableMessageBox = QMessageBox (QMessageBox.Information, title, message)
        self.cancellableMessageBox.setStandardButtons (QMessageBox.Ok)
        self.application.processEvents ()
        self.cancellableMessageBox.exec_ ()
    def displayMessageBox (self, title, message):
        self.messageBox = QMessageBox (QMessageBox.Information, title, message)
        self.messageBox.setStandardButtons (QMessageBox.NoButton)
        self.messageBox.setWindowModality (Qt.NonModal)
        self.messageBox.show ()

        for i in range (1000):
            self.application.processEvents ()
    def cancelMessageBox (self):
        del (self.messageBox)
    def suspendForLoading (self, state):
        if state:
            self.interruptLayoutsAndWaitForCompletion ()

        self.scenarioSelectorCombo.disableCombo (state)
        self.socialLayoutThread.suspendRedraw (state)
        self.galaxyLayoutThread.suspendRedraw (state)
        self.clusterLayoutThread.suspendRedraw (state)
        self.xyPlot.view.noLog = state
        self.loadingFile = state
    def resetForLoading (self):
        self.cleanupOldData ()
        return None
    def loadNamedDatabaseAfterPause (self, pathname, config):
        self._pathname = pathname
        self._config = config
        QtCore.QTimer.singleShot (50, self.loadNamedDatabaseAfterPause2)
    def loadNamedDatabaseAfterPause2 (self):
        self.loadNamedDatabase (self._pathname, self._config)
    def loadNewDatabase (self, pathname):
        self.suspendForLoading (True)
        self.displayMessageBox ('Loading Database', 'Please wait whilst the database is loaded')
        _databaseFolderName, _databaseFilename = os.path.split (pathname)
        _temporaryBcFiles = BcFiles (self, _databaseFolderName, _databaseFilename)

        try:
            _config = _temporaryBcFiles.loadConfiguration (_temporaryBcFiles.configurationFilePathname)
        except:
            _config =  {}

        self.bcFiles = _temporaryBcFiles

        try:
            self.loadNamedDatabase (pathname, _config)
        except sqlite3.OperationalError:
            self.displayMessageBox ('Read Only Database', 'An attempt was made to write to a read-only database.')
            print 'ERROR: An attempt was made to write to a read-only database.'
            self.suspendForLoading (False)
            time.sleep (2)
        else:
            if not _config:
                try:
                    _config = Config (self.bcFiles.username, self.db)
                except:
                    _config = {}

            if _config:
                self.applyConfiguration (_config)
            
            self.suspendForLoading (False)
            self.doRequiredLayouts ()

        self.cancelMessageBox ()
    def doRequiredLayouts (self):
        if isinstance (self.layoutType (), Cluster) or isinstance (self.layoutType (), Social):
            self.doLayout ()

        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_preambleSignal)
    def loadNamedDatabase (self, pathname, config):
        self.suspendForLoading (True)
        _db = self.installDatabase (pathname)

        # If there is no database loaded, ensure that the center node is defined
        self.setCenterNode (0)

        if (_db):
            if ('databaseUniqueId' in config) and (self.tss.uniqueid (self.db) != config ['databaseUniqueId']):
                self.displayCancellableMessageBox ('Wrong Database', 'The database file "%s" and its configuration file do not belong together.' % (pathname))
                self.db = self.resetForLoading ()
                raise WrongConfigurationFile

            self.db = _db

            # Save the database filename and pathname to the .bc_profile
            self.constants._writeProfile_ (self.constants.databasePath)

            # Determine the frequency choices and setup the frequency choice comboBox
            self.timeslice = 0
            _frequencyChoices = set ()
            _mainChoice = 'ALL (' + self.tss.slice_index (self.db) [1] ['interval'] + ')'

            for _slice in self.tssids [1:]:
                _frequencyChoices.add (self.tss.slice_index (self.db) [_slice] ['interval'])

            _allChoices = list ()
            _allChoices.append (_mainChoice)

            for _frequency in _frequencyChoices:
                _allChoices.append (_frequency)

            self.timesliceFrequencySelector.defineChoices (_allChoices)
            self.scenarioSelectorCombo.setSelections (self.tss.coeffindex ())

            # Ensure that the center node is checked in the selection tree
            self.setCenterNode (self.centerNode ())
            self.newSelector.nodeDictionary [self.centerNode ()].checked = Qt.Checked
            self.newSelector.model.propagateToggleStateUp (Qt.Checked, self.newSelector.nodeDictionary [self.centerNode ()])
            self.nodes [self.centerNode ()].hiding = True

            # Protect us from displaying links on large datasets
            if self.N > 100:
                self.linksCheckbox.setCheckState (Qt.Unchecked)
    def applyConfiguration (self, config):
        _config = config

        # Get the node colors
        try:
            _colors = tools.runLengthDecode (_config ['nodeColors'])
        except:
            self.configWarning ('Warning: nodeColors not found in configuration file.')
        else:
            for _nodeIndex in range (self.N):
                _color = _colors [_nodeIndex]
                _baseColor = QColor ()
                _baseColor.setRgb (_color)
                self.nodes [_nodeIndex].bodyColor = _baseColor

                try:
                    self.newSelector.setTreeColor (self.nodes [_nodeIndex].selectorTreeNode, _baseColor)
                except:
                    self.configWarning ('Warning: unable to set selection tree colours from configuration file.')

        # Docking windows
        try:
            self.restoreState (_config ['mainWindowState'])
        except:
            self.configWarning ('Warning: Unable to restore state of main window.')

        # Layout
        try:
            self.setLayoutType (_config ['layout'])
            self.setLayoutTypeById (self.layoutTypeId)
        except:
            self.configWarning ('Warning: layout not found in configuration file.')

        # Scenario
        try:
            self.scenarioSelectorCombo.changeScenario (_config ['scenario'])
        except:
            self.configWarning ('Warning: scenario not found in configuration file.')
            self.scenarioSelectorCombo.changeScenario (0)

        # Window characteristics
        try:
            self.setGeometry (_config ['geometry'])
        except:
            self.configWarning ('Warning: geometry not found in configuration file.')

        # selected, hiding and special nodes:
        try:
            _selectedNodes = tools.sequenceDecode (_config ['selectedNodes'])
            _hiddenNodes = tools.sequenceDecode (_config ['hiddenNodes'])
            _specialNodes = tools.sequenceDecode (_config ['specialNodes'])
        except:
            self.configWarning ('Warning: selectedNodes, hidden nodes or specialNodes not found in configuration file.')
        else:
            for _nodeIndex in range (self.N):
                _node = self.nodes [_nodeIndex]
                _node.selected = (_nodeIndex in _selectedNodes)
                _node.hiding = (_nodeIndex in _hiddenNodes)
                _node.special = (_nodeIndex in _specialNodes)

                if _node.selectorTreeNode:
                    if _node.hiding:
                        _node.selectorTreeNode.checked = Qt.Unchecked
                        self.newSelector.model.propagateToggleStateUp (Qt.Unchecked, _node.selectorTreeNode)
                    else:
                        _node.selectorTreeNode.checked = Qt.Checked
                        self.newSelector.model.propagateToggleStateUp (Qt.Checked, _node.selectorTreeNode)

        # Central opaque disk
        try:
            self.galaxy.view.opaqueDisk.setOpacity (_config ['opaqueDiskOpacity'])
        except:
            self.configWarning ('Warning: opaqueDiskOpacity not found in configuration file.')
            self.galaxy.view.opaqueDisk.setOpacity (0)

        try:
            self.galaxy.view.opaqueDisk.setSize (_config ['opaqueDiskSize'])
        except:
            self.configWarning ('Warning: opaqueDiskSize not found in configuration file.')
            self.galaxy.view.opaqueDisk.setSize (100)

        # Small blue circle
        try:
            self.OFFSET = _config ['smallBlueCircleSize']
            self.SCALING = self.TOTAL_SCALING - self.OFFSET
            self.MAX_CROSSLINK_LENGTH = 2.0 * (self.SCALING + self.OFFSET)
            self.galaxy.view.smallBlueCircle.setSize (self.OFFSET)
        except:
            self.configWarning ('Warning: smallBlueCircleSize not found in configuration file.')
            self.OFFSET = 50
            self.galaxy.view.smallBlueCircle.setSize (self.OFFSET)

        # Social circle opacity slider
        try:
            self.onionRingOpacitySlider.slider.setValue (_config ['socialCircleOpacity'])
        except:
            self.configWarning ('Warning: socialCircleOpacity not found in configuration file.')
            self.onionRingOpacitySlider.slider.setValue (255)
        
        try:
            self.galaxy.view.centrifugeSlider.slider.setValue (_config ['centrifuge'])
        except:
            self.configWarning ('Warning: centrifuge not found in configuration file.')

        try:
            self.galaxy.view.centralLinkCutoffSlider.slider.setValue (_config ['centralLinks'])
        except:
            self.configWarning ('Warning: centralLinks not found in configuration file.')

        try:
            self.galaxy.view.declutterSlider.slider.setValue (_config ['declutter'])
        except:
            self.configWarning ('Warning: declutter not found in configuration file.')

        # Link opacity slider, link cutoff slider and node size slider
        try:
            for _index, _layoutText in enumerate (self.layoutTypeSelectionList):
                _layout = self.layoutSelectionList [_index].view
                _layout.linkOpacitySlider.slider.setValue (_config [_layoutText + 'LinkOpacity'])
                _layout.cutoffSlider.slider.setValue (_config [_layoutText + 'CutoffValue'])
                _layout.nodeSizeSlider.slider.setValue (_config [_layoutText + 'NodeSize'])

                if _layout.rotationEnabled:
                    _layout.rotation = _config [_layoutText + 'Rotation']
        except:
            self.configWarning ('Warning: LinkOpacity, CutoffValue or Nodesize not found in configuration file.')

        # show tooltips
        try:
            self.tooltipsCheckbox.setCheckState (Qt.Checked if _config ['showTooltips'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: showTooltips not found in configuration file.')
            self.tooltipsCheckbox.setCheckState (Qt.Unchecked)

        # hover labels
        try:
            self.hoverLabelsCheckbox.setCheckState (Qt.Checked if _config ['hoverLabels'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: hoverLabels not found in configuration file.')
            self.hoverLabelsCheckbox.setCheckState (Qt.Unchecked)

        # cosmetic links
        try:
            self.cosmeticLinksCheckbox.setCheckState (Qt.Checked if _config ['cosmeticLinks'] else Qt.Unchecked)
            #self.cosmeticLinksCheckbox.setCheckState (Qt.Checked)
        except:
            self.configWarning ('Warning: cosmeticshowLinks not found in configuration file.')
            self.cosmeticLinksCheckbox.setCheckState (Qt.Checked)

        # show links
        try:
            self.linksCheckbox.setCheckState (Qt.Checked if _config ['showLinks'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: showLinks not found in configuration file.')
            self.linksCheckbox.setCheckState (Qt.Unchecked)

        # link quantity
        try:
            self.linkQuantityTextField.setText (_config ['linkQuantity'])
        except:
            self.configWarning ('Warning: linkQuantity not found in configuration file.')
            self.linkQuantityTextField.setText ('20')

        # show arrowheads
        try:
            self.arrowheadsCheckbox.setCheckState (Qt.Checked if _config ['showArrowheads'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: showArrowheads not found in configuration file.')
            self.arrowheadsCheckbox.setCheckState (Qt.Unchecked)

        # font size control
        try:
            self.fontSizeControl.slider.setValue (int (_config ['fontSize']))
        except:
            self.configWarning ('Warning: fontSize not found in configuration file.')
            self.fontSizeControl.slider.setValue (70)

        # show node labels
        try:
            self.labelsCheckbox.setCheckState (Qt.Checked if _config ['showLabels'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: showLabels not found in configuration file.')
            self.labelsCheckbox.setCheckState (Qt.Unchecked)

        # show locus
        try:
            self.xyPlot.view.showLoci.setCheckState (Qt.Checked if _config ['showLocus'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: showLoci not found in configuration file.')

        # Centre node
        try:
            self.setCenterNode (_config ['centralNode'])
        except:
            self.configWarning ('Warning: centralNode not found in configuration file.')
            self.setCenterNode (0)

        # Smooth time
        try:
            self.xyPlot.view.useAnimation.setCheckState (Qt.Checked if _config ['smoothTime'] else Qt.Unchecked)
        except:
            self.configWarning ('Warning: smoothTime not found in configuration file.')
            self.xyPlot.view.useAnimation.setCheckState (Qt.Checked)

        # Timeslice
        try:
            self.xyPlot.view.timeSlider.slider.setValue (_config ['timeSlice'])
        except:
            self.configWarning ('Warning: timeSlice not found in configuration file.')

        # Duration
        try:
            self.durationControl.slider.setValue (_config ['duration'])
        except:
            self.configWarning ('Warning: duration not found in configuration file.')

        # Associations
        self.xyPlot.view.zapAllAssociations ()
        
        try:
            for _association in _config ['associations']:
                _id = _association [0]
                self.xyPlot.view.selector.craftAssociationFromIndices (_association [4] [0] [2], _association [4] [1] [2], _association [4] [2] [2], logUndo = False)
                self.xyPlot.view.associations [_id] [1].special = _association [2]

                if _association [3] == '':
                    self.xyPlot.view.associations [_id] [0].associationName = ''
                else:
                    self.xyPlot.view.associations [_id] [0].associationName = _association [3]
                    self.xyPlot.view.associations [_id] [0].labelChanged = True

                self.xyPlot.view.associations [_id] [1].label.adjustFontSize ()
                self.xyPlot.view.associations [_id] [0].setAssociationNames (False, special = _association [2])

                for _axisId in [0, 1, 2]:
                    _axis = self.xyPlot.view.associations [_id] [0].axis [_axisId]
                    _axis.lagSpinBox.setValue (_association [4] [_axisId] [0])
                    _axis.checkbox.setCheckState (Qt.Checked if _association [4] [_axisId] [1] else Qt.Unchecked)
                    _axis.combo.preselectFromIndex (_association [4] [_axisId] [2])
        except:
            self.configWarning ('Warning: problem reading associations from the configuration file.')

        # Forecasting
        try:
            _futureValue = _config ['futurePeriods']
            self.initialFutureValue = _futureValue
            self.futureSpinBox.setValue (_futureValue)
        except:
            self.configWarning ('Warning: futurePeriods not found in configuration file.')

        try:
            self.analysisPlot.reset ()

            for _type, _timeseries in config ['analysisAttributes']:
                if _type == 'target':
                    self.analysisPlot.addTargetSeries (_timeseries, addInfluencers = False)
                else:
                    self.analysisPlot.addSourceSeries (_timeseries)

            self.futureAltered (_futureValue)
        except:
            self.configWarning ('Warning: problem reading analysis data from the configuration file.')

    def gatherConfigurationData (self):
        _config = {}
        _config ['layout'] = self.layoutTypeString ()
        _config ['scenario'] = self.scenarioSelectorCombo.currentIndex ()
        _config ['geometry'] = self.geometry ()

        # Docking windows
        _config ['mainWindowState'] = self.saveState ()

        # selected, hiding and special nodes:
        _selectedNodes = []
        _specialNodes = []
        _hiddenNodes = []
        _nodeColors = []

        for i in range (self.N):
            if self.nodes [i].special: _specialNodes.append (i)
            if self.nodes [i].hiding: _hiddenNodes.append (i)
            if self.nodes [i].selected: _selectedNodes.append (i)
            _nodeColors.append (self.nodes [i].bodyColor.rgb ())
            
        _config ['selectedNodes'] = tools.sequenceEncode (_selectedNodes)
        _config ['specialNodes'] = tools.sequenceEncode (_specialNodes)
        _config ['hiddenNodes'] = tools.sequenceEncode (_hiddenNodes)
        _config ['nodeColors'] = tools.runLengthEncode (_nodeColors)
        _config ['opaqueDiskOpacity'] = self.galaxy.view.opaqueDisk.opacity ()
        _config ['opaqueDiskSize'] = self.galaxy.view.opaqueDisk.size ()
        _config ['smallBlueCircleSize'] = self.galaxy.view.smallBlueCircle.size ()
        _config ['socialCircleOpacity'] =  self.onionRingOpacitySlider.slider.value ()
        _config ['centrifuge'] =  self.galaxy.view.centrifugeSlider.slider.value ()
        _config ['centralLinks'] =  self.galaxy.view.centralLinkCutoffSlider.slider.value ()
        _config ['declutter'] = self.galaxy.view.declutterSlider.slider.value ()

        # Link opacity slider, link cutoff slider and node size slider
        for _index, _layoutText in enumerate (self.layoutTypeSelectionList):
            _layout = self.layoutSelectionList [_index]
            _config [_layoutText + 'LinkOpacity'] = _layout.view.linkOpacitySlider.slider.value ()
            _config [_layoutText + 'CutoffValue'] = _layout.view.cutoffSlider.slider.value ()
            _config [_layoutText + 'NodeSize'] = _layout.view.nodeSizeSlider.slider.value ()
            _config [_layoutText + 'Rotation'] = _layout.view.rotation

        _config ['animationType'] = self.animationTypeCombo.currentIndex ()
        _config ['showTooltips'] = (self.tooltipsCheckbox.checkState () == Qt.CheckState.Checked)
        _config ['hoverLabels'] = (self.hoverLabelsCheckbox.checkState () == Qt.CheckState.Checked)
        _config ['showLinks'] = (self.linksCheckbox.checkState () == Qt.CheckState.Checked)
        _config ['linkQuantity'] = self.linkQuantityTextField.text ()
        _config ['showArrowheads'] = (self.arrowheadsCheckbox.checkState () == Qt.CheckState.Checked)
        _config ['fontSize'] = self.fontSizeControl.slider.value ()
        _config ['showLabels'] = (self.labelsCheckbox.checkState () == Qt.CheckState.Checked)
        _config ['showLocus'] = (self.xyPlot.view.showLoci.checkState () == Qt.CheckState.Checked)
        _config ['nodeLabels'] = []
        _config ['centralNode'] = self.centerNode ()
        _config ['smoothTime'] = self.xyPlot.view.animationOn == Qt.CheckState.Checked
        _config ['timeSlice'] = self.xyPlot.view.timeSlider.index
        _config ['duration'] = self.durationControl.slider.value ()
        _config ['cosmeticLinks'] = (self.cosmeticLinksCheckbox.checkState () == Qt.CheckState.Checked)

        # Associations
        _specialBubbles = []
        _bubbleLabels = {}
        _associations = []

        _id = 0

        for _association in self.xyPlot.view.associations:
            _root = _association [0]

            if _root and _association [2]:
                _axisInfo = []
                _special = _association [1].special

                if _root.labelChanged:
                    _label = _association [1].label.toPlainText ()
                else:
                    _label = ''

                _hidden = _root.hidden

                for _axisId in [0, 1, 2]:
                    _axis = _root.axis [_axisId]
                    _axisInfo.append ([_axis.lagSpinBox.lag (), _axis.checkbox.checkState () == Qt.CheckState.Checked, _axis.combo.selectionId])

                _associations.append ([_id, _hidden, _special, _label, _axisInfo])
                _id += 1

        _config ['associations'] = _associations

        # Analysis data
        _config ['futurePeriods'] = self.futureSpinBox.value ()
        _allAttributes = []

        for _graphId, _graph in self.forecastingGraphs.items ():
            _allAttributes.append ((_graph.plotType, _graph.timeseriesSelectorComboBox.currentIndex ()))

        _config ['analysisAttributes'] = sorted (_allAttributes, reverse = True)

        return _config
    def saveConfiguration (self):
        if self.bcFiles:
            self.bcFiles.saveConfiguration ()
    def displayXYPlot (self):
        self.timeLine = QTimeLine (3000, self)
        self.timeLine.setFrameRange (0, 100)
        self.timeLine.setEasingCurve (QEasingCurve.OutQuad)
        QObject.connect (self.timeLine, SIGNAL ('frameChanged (int)'), self.tweakSplitter)
        self.timeLine.start ()
    def makeLayoutControlButtons (self):
        _widget = QStackedWidget ()

        # Galaxy
        _a = QWidget ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_CENTRIFUGE:
            _widget.addWidget (_a)
        else:
            self.dummyLayoutControlPanels.append (_a)

        _b = QVBoxLayout ()
        _a.setLayout (_b)
        _b.addWidget (QLabel ('<b>Centrifuge</b>'))
        self.galaxy.view.linkOpacitySlider = Slider ('Link Opacity:', 0, 511, 255, self.adjustOpacity)
        _b.addWidget (self.galaxy.view.linkOpacitySlider)
        self.galaxy.view.nodeSizeSlider = Slider ('Node size:', 0.2 * 255.0, 4.0 * 255.0, 1.0 * 255.0, self.galaxy.view.adjustNodeSize)
        _b.addWidget (self.galaxy.view.nodeSizeSlider)
        self.galaxy.view.cutoffSlider = Slider ('Cross influence:', 0, 255, 255, self.galaxy.view.adjustCrosslinkCutoff)
        self.galaxy.view.cutoffSlider.setToolTip (r"""
Adjusts the cutoff value applied to links between non-central nodes. This means all links that are not central links.
Links with coefficients less than the setting of this slider will not be displayed (even if the Show links checkbox has been checked).
Nor will they be considered in layout calculations.
The slider's range is between 0 and 100%, with 100% corresponding to the largest value of coefficient amongst all links.
""")
        _b.addWidget (self.galaxy.view.cutoffSlider)
        self.galaxy.view.centrifugeSlider = Slider ('Centrifuge:', 0, 255, 0, self.galaxy.view.adjustCentrifuge)
        _b.addWidget (self.galaxy.view.centrifugeSlider)
        self.galaxy.view.centralLinkCutoffSlider = Slider ('Data sieve:', 0, 255, 0, self.galaxy.view.adjustCentralLinkCutoff)
        self.galaxy.view.centralLinkCutoffSlider.setToolTip (r"""
Adjusts the cutoff value applied to links between the central node and all other nodes.
Links with coefficients less than the setting of this slider will not be displayed (even if the Show links checkbox has been checked).
Nor will they be considered in layout calculations.
If the link between the central node and any other node has been 'cut off' by the setting of this slider, that node will not be displayed.
Nor will it be considered in layout calculations.
The slider's range is between 0 and 100%, with 100% corresponding to the largest value of coefficient amongst all the central links.
""")
        _b.addWidget (self.galaxy.view.centralLinkCutoffSlider)
        self.galaxy.view.diskOpacitySlider = Slider ('Disk opacity:', 0, 255, 0, self.galaxy.view.opaqueDisk.setOpacity)
        _b.addWidget (self.galaxy.view.diskOpacitySlider)
        self.galaxy.view.declutterSlider = Slider ('Declutter:', 0, 255, 0, self.setDeclutter)
        self.galaxy.view.declutterSlider.setToolTip ('Helps to separate overlapping nodes')
        _b.addWidget (self.galaxy.view.declutterSlider)
        _b.addStretch ()

        

        # Analysis plot
        _a = QWidget ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_ANALYSIS:
            _widget.addWidget (_a)
        else:
            self.dummyLayoutControlPanels.append (_a)

        _b = QVBoxLayout ()
        _a.setLayout (_b)
        _b.addWidget (QLabel ('<b>Analysis</b>'))

        # 'Future' spinbox
        _layout = QHBoxLayout ()
        _b.addLayout (_layout)
        _label = QLabel ('Future periods:')
        self.futureSpinBox = QSpinBox ()
        self.futureSpinBox.setValue (0)
        self.futureSpinBox.setMinimum (-20)
        self.futureSpinBox.setMaximum (9999)
        QObject.connect (self.futureSpinBox, SIGNAL ('valueChanged (int)'), self.futureAltered)

        if self.constants.facilitiesKey & self.constants.FACILITIES_ANALYSIS_FUTURE:
            _layout.addWidget (_label)
            _layout.addWidget (self.futureSpinBox)
            _helpButton = QPushButton ('Help')
            QObject.connect (_helpButton, SIGNAL ('clicked ()'), self.helpOnAnalysis)
            _layout.addWidget (_helpButton)

        # 'Influences' spinbox
        _layout2 = QHBoxLayout ()
        _b.addLayout (_layout2)
        _label = QLabel ('Influences to add:')
        _layout2.addWidget (_label)
        self.influencesSpinBox = QSpinBox ()
        self.influencesSpinBox.setValue (5)
        self.influencesSpinBox.setMinimum (0)
        self.influencesSpinBox.setMaximum (15)
        _layout2.addWidget (self.influencesSpinBox)
        QObject.connect (self.influencesSpinBox, SIGNAL ('valueChanged (int)'), self.influencesAltered)

        # Historic predictions checkbox
        self.historicPredictionsCheckbox = QCheckBox ('Show historic predictions')
        #_b.addWidget (self.historicPredictionsCheckbox)

        # 'Add target graph' button
        _layout3 = QHBoxLayout ()
        _b.addLayout (_layout3)
        _addTargetButton = QPushButton ('Add Target Graph')
        _layout3.addWidget (_addTargetButton)
        _addTargetButton.setToolTip ('add a target timeseries to the forecasting graph display')
        QtCore.QObject.connect (_addTargetButton, QtCore.SIGNAL ('clicked ()'), self.addForecastingTargetGraph)

        # 'Add source graph' button
        _addSourceButton = QPushButton ('Add Source Graph')
        _layout3.addWidget (_addSourceButton)
        _addSourceButton.setToolTip ('add a source timeseries to the forecasting graph display')
        QtCore.QObject.connect (_addSourceButton, QtCore.SIGNAL ('clicked ()'), self.addForecastingSourceGraph)

        # 'Delete all source graphs' button
        _deleteAllSourceGraphsButton = QPushButton (QIcon (':/images/Resources/remove20x20.png'), 'Delete All Source Graphs')
        _b.addWidget (_deleteAllSourceGraphsButton)
        _deleteAllSourceGraphsButton.setToolTip ('remove all source timeseries from the forecasting graph display')
        QtCore.QObject.connect (_deleteAllSourceGraphsButton, QtCore.SIGNAL ('clicked ()'), self.deleteAllSourceGraphs)

        # 'Forecast From Centrifuge' button
        _forecastFromCentrifugeButton = QPushButton ('Forecast From Centrifuge')
        _b.addWidget (_forecastFromCentrifugeButton)
        _forecastFromCentrifugeButton.setToolTip ('Show forecasting for the centrifuge central node')
        QtCore.QObject.connect (_forecastFromCentrifugeButton, QtCore.SIGNAL ('clicked ()'), self.presetForecast)

        _b.addStretch ()
        _widget.setSizePolicy (QSizePolicy.Ignored, QSizePolicy.Maximum)


        # XY Plot
        _a = QWidget ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_XY:
            _widget.addWidget (_a)
        else:
            self.dummyLayoutControlPanels.append (_a)

        _b = QVBoxLayout ()
        _a.setLayout (_b)
        _b.addWidget (QLabel ('<b>XY Graph</b>'))
        self.xyPlot.view.linkOpacitySlider = Slider ('Link Opacity:', 0, 255, 255, self.adjustOpacity)
        _b.addWidget (self.xyPlot.view.linkOpacitySlider)
        self.xyPlot.view.nodeSizeSlider = Slider ('Node size:', 0.2 * 255.0, 4.0 * 255.0, 1.0 * 255.0, self.xyPlot.view.adjustNodeSize)
        _b.addWidget (self.xyPlot.view.nodeSizeSlider)
        self.xyPlot.view.cutoffSlider = Slider ('Unused:', 0, 255, 255, None)
        self.durationControl = Slider ('Duration:', 0, 30, 30, self.adjustDuration)
        _b.addWidget (self.durationControl)
        # Add a toggle to show loci
        self.xyPlot.view.showLoci = QtGui.QCheckBox ('Show locus')
        _b.addWidget (self.xyPlot.view.showLoci)
        QtCore.QObject.connect (self.xyPlot.view.showLoci, QtCore.SIGNAL ('stateChanged (int)'), self.xyPlot.view.displayLoci)
        _b.addStretch ()

        _runLayout = QtGui.QHBoxLayout ()
        _b.addLayout (_runLayout)

        # 'display v Time' button
        self.vTimeButton = ToolButton (self.xyPlot, ':/images/Resources/clock.png', 'Display against time in the x axis', self.xyPlot.view.redrawAll)
        self.vTimeButton.setToolTip ('Display against time in the x axis')
        self.vTimeButton.setCheckable (True)
        _runLayout.addWidget (self.vTimeButton)

        # Add the 'pause' button
        self.pauseButton = QtGui.QPushButton ()
        self.pauseButton.setIcon (QIcon (':/images/Resources/pause.png'))
        QtCore.QObject.connect (self.pauseButton, QtCore.SIGNAL ('clicked ()'), self.xyPlot.view.pause)
        self.pauseButton.setEnabled (False)
        _runLayout.addWidget (self.pauseButton)

        # Add the 'play' button
        self.runButton = QtGui.QPushButton ()
        self.runButton.setIcon (QIcon (':/images/Resources/play.png'))
        QtCore.QObject.connect (self.runButton, QtCore.SIGNAL ('clicked ()'), self.xyPlot.view.run)
        _runLayout.addWidget (self.runButton)

        # 'Add' button
        _addButton = ToolButton (self.xyPlot, ':/images/Resources/add32x32.png', 'Add a new association', self.xyPlot.view.selector.addAssociation)
        _runLayout.addWidget (_addButton)

        # Social network
        _a = QWidget ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_NETWORK:
            _widget.addWidget (_a)
        else:
            self.dummyLayoutControlPanels.append (_a)

        _b = QVBoxLayout ()
        _a.setLayout (_b)
        _b.addWidget (QLabel ('<b>Network</b>'))
        self.social.view.linkOpacitySlider = Slider ('Link Opacity:', 0, 511, 255, self.adjustOpacity)
        _b.addWidget (self.social.view.linkOpacitySlider)
        self.social.view.nodeSizeSlider = Slider ('Node size:', 0.2 * 255.0, 4.0 * 255.0, 1.0 * 255.0, self.social.view.adjustNodeSize)
        _b.addWidget (self.social.view.nodeSizeSlider)
        self.social.view.cutoffSlider = Slider ('Link Cutoff:', 0, 255, 255, self.adjustLinkCutoff)
        _b.addWidget (self.social.view.cutoffSlider)
        self.inflowCheckbox = self.aCheckBox ('Inflow', Qt.Checked, self.toggleInflow)
        _b.addWidget (self.inflowCheckbox)
        self.onionRingOpacitySlider = Slider ('Circle opacity:', 0, 255, 255, self.adjustOnionRingOpacity)
        _b.addWidget (self.onionRingOpacitySlider)
        _b.addStretch ()
        
        # Cluster
        _a = QWidget ()

        if self.constants.facilitiesKey & self.constants.FACILITIES_TAB_COMMUNITIES:
            _widget.addWidget (_a)
        else:
            self.dummyLayoutControlPanels.append (_a)

        _b = QVBoxLayout ()
        _a.setLayout (_b)
        _b.addWidget (QLabel ('<b>Communities</b>'))
        self.cluster.view.linkOpacitySlider = Slider ('Link Opacity:', 0, 511, 255, self.adjustOpacity)
        _b.addWidget (self.cluster.view.linkOpacitySlider)
        self.cluster.view.nodeSizeSlider = Slider ('Node size:', 0.2 * 255.0, 4.0 * 255.0, 1.0 * 255.0, self.cluster.view.adjustNodeSize)
        _b.addWidget (self.cluster.view.nodeSizeSlider)
        self.cluster.view.cutoffSlider = Slider ('Link Cutoff:', 0, 255, 255, self.adjustLinkCutoff)
        _b.addWidget (self.cluster.view.cutoffSlider)
        #self.refinePushButton = self.aButton ('Refine', self.refine)
        #_b.addWidget (self.refinePushButton)
        _b.addStretch ()
        
        

        

        return _widget
    def presetForecast (self):
        self.analysisPlot.presetForecast (self.centerNode ())
    def deleteAllSourceGraphs (self):
        if self.db:
            for i in self.forecastingSources [:]:
                self.analysisPlot.removeSourceSeries (i)
    def addForecastingTargetGraph (self):
        if self.db:
            self.analysisPlot.addTargetSeries ()
    def addForecastingSourceGraph (self):
        if self.db:
            self.analysisPlot.addSourceSeries ()
    def helpOnAnalysis (self):
        self.helpDialog.webView.setUrl ('Resources/HelpOnForecasting.html')
        self.menubar.popupHelp ()
    def influencesAltered (self, value):
        self.addInfluences = value
    def futureAltered (self, value):
        if not self.db:
            return

        self.futurePeriods = value
        _firstTime = self.tss.series () [0].getAllTimes () [0]
        _lastTime = self.tss.series () [0].getAllTimes () [-1]
        _interval = self.tss.interval ()
        _year = 0
        _month = 0
        _date = 0

        try:
            _year = int (_lastTime [0:4])
            _month = int (_lastTime [5:7])
            _date = int (_lastTime [8:10])
        except:
            None

        if _interval == 'yearly':
            _year += value
            self.futureExtent = '%4d' % (_year)
        elif _interval == 'monthly':
            _newMonth = (_month - 1 + value) % 12 + 1
            _newYear = _year + int ((_month - 1 + value) / 12)
            self.futureExtent = '%4d-%02d' % (_newYear, _newMonth)
        elif _interval == 'weekly':
            self.futureExtent = 'TBD'
        elif _interval == 'daily':
            self.futureExtent = 'TBD'

        #self.endOfTimeLabel.setText (self.futureExtent)
        self.analysisPlot.extendTime (value, self.futureExtent)
    def setDeclutter (self, declutter):
        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_setupAdjustSignal)
    def adjustDuration (self, value):
        self.xyPlot.view.rerun ()
    def toggleInflow (self, state):
        self.doLayout ()
    def seekNodePressed (self):
        if isinstance (self.layoutType (), Galaxy) or isinstance (self.layoutType (), Cluster) or isinstance (self.layoutType (), Social):
            _text = self.seekNodeTextField.text ()
            self.soughtNodes = []

            for _nodeIndex in self.layoutType ().view.visibleNodeDetails.nodeList ():
                _node = self.nodes [_nodeIndex]
                _label = _node.labelText
                self.soughtNodes.append (_node)

                if _text.lower () in _label.lower ():
                    if isinstance (self.layoutType (), Galaxy):
                        Ellipse.hoverEnterEvent (_node.galaxy.graphic, None)
                    elif isinstance (self.layoutType (), Social):
                        Ellipse.hoverEnterEvent (_node.social.graphic, None)
                    elif isinstance (self.layoutType (), Cluster):
                        Ellipse.hoverEnterEvent (_node.cluster.graphic, None)
    def seekNodeReleased (self):
        if isinstance (self.layoutType (), Galaxy) or isinstance (self.layoutType (), Cluster) or isinstance (self.layoutType (), Social):
            for _node in self.soughtNodes:
                if isinstance (self.layoutType (), Galaxy):
                    Ellipse.hoverLeaveEvent (_node.galaxy.graphic, None)
                elif isinstance (self.layoutType (), Social):
                    Ellipse.hoverLeaveEvent (_node.social.graphic, None)
                elif isinstance (self.layoutType (), Cluster):
                    Ellipse.hoverLeaveEvent (_node.cluster.graphic, None)
    def makeSeekNodeControls (self):
        _widget = QWidget ()
        _layout = QHBoxLayout ()
        _widget.setLayout (_layout)

        # Add a text field
        self.seekNodeTextField = QLineEdit ()
        _layout.addWidget (self.seekNodeTextField)

        # Add a button
        self.seekNodePushButton = QPushButton ('Seek')
        _layout.addWidget (self.seekNodePushButton)
        QObject.connect (self.seekNodePushButton, SIGNAL ('pressed ()'), self.seekNodePressed)
        QObject.connect (self.seekNodePushButton, SIGNAL ('released ()'), self.seekNodeReleased)

        _widget.setSizePolicy (QSizePolicy.Ignored, QSizePolicy.Maximum)

        return _widget
    def makeTimeDimensionControls (self):
        _widget = QWidget ()
        _layout = QVBoxLayout ()
        _widget.setLayout (_layout)

        _grid = QGridLayout ()
        _layout.addLayout (_grid)

        # Define a timeslice selection combobox
        self.timesliceSelector = TimesliceSelector (self)
        _grid.addWidget (self.timesliceSelector, 0, 1)

        # Define a frequency selection combobox
        self.timesliceFrequencySelector = TimesliceFrequencySelector (self)
        _grid.addWidget (self.timesliceFrequencySelector, 0, 0)

        # Define the timeslice slider
        self.timesliceChoices = list () 
        self.timesliceSlider = TimesliceSlider (self, 0, 1, 0, self.timesliceSliderHasBeenMoved)
        _grid.addWidget (self.timesliceSlider, 1, 0, 1, 2)

        _widget.setSizePolicy (QSizePolicy.Ignored, QSizePolicy.Maximum)

        return _widget
    def timesliceSliderHasBeenMoved (self, index):
        if self.db:
            self.timeslice = self.timesliceChoices [index] - 1
            self.timesliceSelector.setCurrentIndex (index)
    def makeControlButtons (self):
        _widget = QWidget ()
        _layout = QVBoxLayout ()
        _widget.setLayout (_layout)

        # Define toggles to switch on and off the display of nodes, links, labels and tooltips
        _grid = QGridLayout ()
        _layout.addLayout (_grid)

        self.labelsCheckbox = self.aCheckBox ('Show labels', Qt.Checked, self.toggleLabelDisplay)
        _grid.addWidget (self.labelsCheckbox, 0, 0)
        #self.fullscreenCheckbox = self.aCheckBox ('Fullscreen', Qt.Unchecked, self.toggleFullscreen)
        #_grid.addWidget (self.fullscreenCheckbox, 0, 1)
        self.hoverLabelsCheckbox = self.aCheckBox ('Highlight labels', Qt.Checked, self.toggleHoverLabelDisplay)
        _grid.addWidget (self.hoverLabelsCheckbox, 0, 1)
        self.tooltipsCheckbox = self.aCheckBox ('Show tooltips', Qt.Checked, self.toggleTooltipDisplay)
        _grid.addWidget (self.tooltipsCheckbox, 1, 0)
        #self.directMovesCheckbox = self.aCheckBox ('Direct moves', Qt.Checked, self.toggleDirectMoves)
        #_grid.addWidget (self.directMovesCheckbox, 1, 1)
        self.linksCheckbox = self.aCheckBox ('Show links', Qt.Unchecked, self.toggleLinkDisplay)
        _grid.addWidget (self.linksCheckbox, 2, 0)
        self.cosmeticLinksCheckbox = self.aCheckBox ('Cosmetic links', Qt.Unchecked, self.redrawCosmeticLinks)
        _grid.addWidget (self.cosmeticLinksCheckbox, 1, 1)

        _textLayout = QHBoxLayout ()
        _label = QLabel ('Max. links:')
        _textLayout.addWidget (_label)
        _grid.addLayout (_textLayout, 2, 1)
        self.linkQuantityTextField = QLineEdit ()
        self.linkQuantityTextField.setText ('20')
        QtCore.QObject.connect (self.linkQuantityTextField, QtCore.SIGNAL ('editingFinished ()'), self.refreshLinkQuantity)
        _textLayout.addWidget (self.linkQuantityTextField)
        
        self.arrowheadsCheckbox = self.aCheckBox ('Show arrowheads', Qt.Unchecked, self.toggleArrowheadsDisplay)
        self.arrowheadsCheckbox.setEnabled (False)
        _grid.addWidget (self.arrowheadsCheckbox, 3, 0)

        self.fontSizeControl = Slider ('Font size:', 0, 255, 70, self.adjustFontSize)
        _grid.addWidget (self.fontSizeControl, 4, 0, 1, 2)

        # create comboboxes for the selection of the graphing scenario and the animation type
        _grid = QGridLayout ()
        _layout.addLayout (_grid)

        self.tssSelectorLabel = QLabel ('Scenario:')
        _grid.addWidget (self.tssSelectorLabel, 0, 0, 1, 2)
        self.scenarioSelectorCombo = ScenarioSelectorCombo (self)
        _grid.addWidget (self.scenarioSelectorCombo, 1, 0, 1, 2)

        #self.animationTypeLabel = QLabel ('Animation type:')
        #_grid.addWidget (self.animationTypeLabel, 2, 0, 1, 2)
        self.animationTypeCombo = AnimationTypeCombo (self)
        #_grid.addWidget (self.animationTypeCombo, 4, 0, 1, 2)

        #_layout.addStretch ()
        _widget.setSizePolicy (QSizePolicy.Ignored, QSizePolicy.Maximum)

        return _widget
    def adjustFontSize (self, value):
        _pointSize = (22.0 / 255.0) * value + 2.0
        self.nodeFontSize = _pointSize
        self.nodeHighlightFontSize = _pointSize * 1.3

        if not isinstance (self.layoutType (), Galaxy):
            if not self.loadingFile:
                self.doLayout ()

        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_noLongerWorkingSignal)
    def toggleDirectMoves (self, value):
        """ When ON, nodes move 'as the clow fries'; when OFF they travel around the perimeter of their onion ring """
    def optionOfAbortingSlowAndBlockingOperation (self, message):
        _messageBox = QMessageBox ( QMessageBox.Information, 'Warning of Time-Consuming Operation', message)
        _messageBox.setStandardButtons (QMessageBox.Cancel | QMessageBox.Yes)
        _messageBox.setDefaultButton (QMessageBox.Cancel)
        _userChoice = _messageBox.exec_ ()

        return (_userChoice == QMessageBox.Cancel)
    def checkIfClusterOperationLikelyToBeSlowAndBlocking (self):
        _visibleNodeCount = 0

        for _node in self.nodes:
            if not _node.hiding:
                _visibleNodeCount += 1

        if _visibleNodeCount > self.constants.lotsOfNodesToCluster:
            return self.optionOfAbortingSlowAndBlockingOperation ("Clustering of many nodes can be very time-consuming. Are you sure you want to do this?")
        else:
            return False
    def checkIfLinkToggleOperationLikelyToBeSlowAndBlocking (self, layoutType):
        if isinstance (layoutType, Galaxy) or isinstance (layoutType, Cluster):
            try:
                if (self.linksCheckbox.checkState () == Qt.Checked) and (len (self.galaxy.view.links) > self.constants.lotsOfLinks):
                    return self.optionOfAbortingSlowAndBlockingOperation ("This may significantly slow down the display and cannot be interrupted. Are you sure you want to continue?")
            except:
                return False

        return False
    def refreshLinkQuantity (self):
        if not isinstance (self.layoutType (), Galaxy):
            self.doLayout ()

        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_makeLinksSignal)
    def toggleArrowheadsDisplay (self, value):
        if not isinstance (self.layoutType (), Galaxy):
            if not self.loadingFile:
                self.doLayout ()

        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_makeLinksSignal)
    def toggleLinkDisplay (self, value):
        if self.checkIfLinkToggleOperationLikelyToBeSlowAndBlocking (self.layoutType ()):
            self.linksCheckbox.setCheckState (Qt.Unchecked)
            return

        if isinstance (self.layoutType (), Social):
            self.doLayout ()
            self.arrowheadsCheckbox.setEnabled (False)
        elif isinstance (self.layoutType (), Cluster):
            if not self.loadingFile:
                self.doLayout ()
        elif isinstance (self.layoutType (), Galaxy):
            self.arrowheadsCheckbox.setEnabled (value)

        self.galaxy.view.doLayout (self.galaxyLayoutThread.task_makeLinksSignal)
    #def toggleFullscreen (self, value):
    #    if value == Qt.Checked:
    #        bc.showFullScreen ()
    #    else:
    #        bc.showNormal ()
    def adjustOnionRingOpacity (self, opacity):
        _circles = self.social.view.mainThread.circles

        for _circle in _circles:
            _intensity = _circle [1]
            _circle [0].setOpacity (opacity)
    def displayAlgoSpecificPanel (self, index):
        try:
            self.layoutSpecificPane.setCurrentIndex (index)
        except:
            None
    def textButton (self, text, tip, callback, layout):
        _button = QPushButton (text)
        _button.setToolTip (tip)
        QObject.connect (_button, SIGNAL ('clicked ()'), callback)
        layout.addWidget (_button)
        return _button
    def toolButton (self, iconFilename, tip, callback, layout):
        _button = QToolButton ()
        _button.setIcon (QIcon (iconFilename))
        _button.setToolTip (tip)
        QObject.connect (_button, SIGNAL ('clicked ()'), callback)
        layout.addWidget (_button)
        return _button
    def toggleHoverLabelDisplay (self, state):
        None
    def toggleTooltipDisplay (self, state):
        self.busyCursor (True)
        self.galaxy.view.toggleNodeTooltips (state)
        self.cluster.view.toggleNodeTooltips (state)
        self.social.view.toggleNodeTooltips (state)

        self.galaxy.view.toggleLinkTooltips (state)
        self.cluster.view.toggleLinkTooltips (state)
        self.social.view.toggleLinkTooltips (state)

        self.xyPlot.view.toggleTooltipDisplay (state)
        self.busyCursor (False)
    def toggleLabelDisplay (self, state):
        self.xyPlot.view.toggleLabelDisplay (state)

        for _index in range (self.N):
            _node = self.nodes [_index]
            _graphics = []
            
            try:
                _graphics.append (_node.galaxy.graphic)
            except:
                None

            try:
                _graphics.append (_node.cluster.graphic)
            except:
                None

            try:
                _graphics.append (_node.social.graphic)
            except:
                None

            for _graphic in _graphics:
                _graphic.label.setText (_node.labelText)
                _graphic.label.setVisible (state or _node.special)
                _graphic.label.backwash.setVisible (state or _node.special)
    def aCheckBox (self, label, state, action, parent = None):
        self.checkbox = QCheckBox (label, parent)
        self.checkbox.setCheckState (state)
        QObject.connect (self.checkbox, SIGNAL ('stateChanged (int)'), action)
        return self.checkbox
    def aButton (self, label, action, parent = None):
        self.button = QPushButton (label, parent)
        QObject.connect (self.button, SIGNAL ('clicked ()'), action)
        return self.button
    def adjustOpacity (self, value):
        if len (self.layoutType ().view.links):
            for _link in self.layoutType ().view.links:
                try:
                    _link.graphic.reshade (value)
                except:
                    None
    def adjustLinkCutoff (self, value):
        if isinstance (self.layoutType (), Galaxy):
            self.galaxy.view.doLayout (self.galaxyLayoutThread.task_cutoffCentralLinksSignal)
        else:
            if not self.loadingFile:
                self.doLayout ()
    def _init_model_(self, appname):
        self.app = Application (self, appname, False, False)
    def cleanupOldData (self):
        self.galaxy.view.cleanupOldData ()
        self.cluster.view.cleanupOldData ()
        self.social.view.cleanupOldData ()
        self.db = None
        self.newSelector.loadTree ()
    def scrub (self, s):
        _result = ''

        for c in s:
            if ord (c) > 127:
                _result += ' '
            else:
                _result += c

        return _result
    def openDatabaseFile (self, filename):
        self.db = Database (filename)
        self.timeslice = 0
        self.tssids = TimeSeriesSet.seriessetids (self.db)
        self.loadedTimeslice = -1
        self.loadTimeslice ()
        self.loadedTimeslice = 0
        self.tss.lastreldelta_quintiles ()
        self.tss.UseRegression = True
        self.N = len (self.tss)

        """
        # Devine Amar's timeseries
        _soughtUniqueIds = ['Toyota_Sml_Car_Sales_Volume_Buyer_Private_Toyota', 'TMCA_COROLLA_MS_Adelaide_ADS10_Adelaide_AFL', \
                            'TMCA_COROLLA_MS_Adelaide_One_Adelaide_Sports_Tonight', 'TMCA_COROLLA_MS_Brisbane_One_Brisbane_Sports_Tonight', \
                            'TMCA_COROLLA_MS_Melbourne_One_Melbourne_Sports_Tonight', 'TMCA_COROLLA_MS_National_Comedy_Channel_Titan_Maximum', \
                            'TMCA_COROLLA_MS_National_Fox_Sports_News_FSN_Express', 'TMCA_COROLLA_MS_National_Fox_Sports_News_FSN_Morning_News', \
                            'TMCA_COROLLA_MS_National_Fox_Sports_News_FSN_News_Full_Time', 'TMCA_COROLLA_MS_National_Sci_Fi_Sanctuary', \
                            'TMCA_COROLLA_MS_National_TV1_Seinfeld', 'TMCA_COROLLA_MS_Perth_One_Perth_Sports_Tonight']

        for i, _dummy in enumerate (_soughtUniqueIds):
            _soughtUniqueIds [i] = _soughtUniqueIds [i].lower ()

        _series = self.tss.getseries
        _scenario = 0
        cm = self.tss.loadcoefficients (self.db, self.tss.coeffids () [_scenario])
        _dependent = 0

        for i in range (self.N):
            _seriesElement = _series (i)
            _uniqueId = self.scrub (_seriesElement._dict ['uniqueid']).lower ()
            print i, _uniqueId, _series (i).label (),

            for t in _series (i).getAllValues ():
                print '%f\t' % t,

        for i in range (self.N):
            _seriesElement = _series (i)
            _label = self.scrub (_seriesElement.label ()).lower ()
            _uniqueId = self.scrub (_seriesElement._dict ['uniqueid']).lower ()
            _uniqueIdLength = len (_uniqueId)

            if _uniqueIdLength > 10:
                try:
                    for l in range (10):
                        _truncUniqueId = _uniqueId [0:max (0, _uniqueIdLength - (10 - l))]

                        for s, v in enumerate (_soughtUniqueIds):
                            _truncSoughtUniqueId = v [0:max (0, _uniqueIdLength - (10 - l))]

                            if _truncUniqueId == _truncSoughtUniqueId:
                                _row = self.cm.coeffs [_dependent]
                                _dependent = 103
                                _coefficient = 0.0 if self.cm.sparse and i not in _row else _row [i]
                                print '%.4d: %s (%.2f)' % (i, _uniqueId, _coefficient)
                                raise
                except:
                    pass
        """
    def installDatabase (self, filename):
        self.openDatabaseFile (filename)

        # Create the node description structures
        self.createNodes (self.tss)

        # Events
        self.events = []

        for _index in range (len (self.tss.events ()._series)):
            _event = self.tss.events ().getseries (_index)
            _dateLength = len (self.tss.series () [0].getAllTimes () [0])
            _startDate = dateutil.parser.parse ('%s' % (_event.startdate ()))
            _endDate = dateutil.parser.parse ('%s' % (_event.enddate ()))
            self.events.append ([_event.label (), _startDate, _endDate, _event.displaytype (), _event.fademonths (), _dateLength])

        self.xyPlot.view.timeSlider.eventsWidget.setup (self.constants.eventBarColor)
        # END OF Events

        # prepare the XY graph
        self.xyPlot.view.reloadTimeseries (self.xyTss)
        self.xyPlot.view.timeSlider.overlapWidget.removeOldOverlaps ()

        # Reset the galaxy display
        self.galaxyLayoutThread.displayReset.emit ()

        # reset the link cutoff slider and the link opacity slider
        self.layoutType ().view.cutoffSlider.setSpan (self.constants.baseCutoff * 255.0, 255)

        # Reset the undo buffer
        self.undoBuffer.reset ()

        # Reset the analysis tool
        self.analysisPlot.reset ()

        # Make the first node the default centre node
        self.setCenterNode (0)

        # Load the tree
        self.newSelector.loadTree ()
        return self.db
    def readDataset (self, filename):
        resource_usage = ConciseMonitor()

        # Ensure all layout threads are stopped before we kick off any more
        self.START = time.time ()
        self.interruptLayoutsAndWaitForCompletion ()
        self.START = self.INSTRUMENT_LOAD ('load:interrupt', self.START)
        self.cleanupOldData ()
        self.START = self.INSTRUMENT_LOAD ('load:cleanupOldData', self.START)

        self.openDatabaseFile (filename)

        if self.N == 0:
            return

        # Create the node description structures
        self.createNodes (self.tss)
        self.START = self.INSTRUMENT_LOAD ('load:createNodes', self.START)

        # Events
        self.events = []

        for _index in range (len (self.tss.events ()._series)):
            _event = self.tss.events ().getseries (_index)
            _dateLength = len (self.tss.series () [0].getAllTimes () [0])
            _startDate = dateutil.parser.parse ('%s' % (_event.startdate ()))
            _endDate = dateutil.parser.parse ('%s' % (_event.enddate ()))
            #print _event.label (), _startDate, _endDate, _event.displaytype (), _event.fademonths ()
            self.events.append ([_event.label (), _startDate, _endDate, _event.displaytype (), _event.fademonths (), _dateLength])

        self.xyPlot.view.timeSlider.eventsWidget.setup (self.constants.eventBarColor)
        self.START = self.INSTRUMENT_LOAD ('load:preprocessed events', self.START)
        # END OF Events

        # prepare the XY graph
        self.xyPlot.view.reloadTimeseries (self.xyTss)
        self.xyPlot.view.timeSlider.overlapWidget.removeOldOverlaps ()
        self.START = self.INSTRUMENT_LOAD ('load:xy graph prepared', self.START)

        # Reset the galaxy display
        self.galaxyLayoutThread.displayReset.emit ()
        self.START = self.INSTRUMENT_LOAD ('load:centrifuge reset', self.START)

        # reset the link cutoff slider and the link opacity slider
        self.layoutType ().view.cutoffSlider.setSpan (self.constants.baseCutoff * 255.0, 255)

        # Reset the undo buffer
        self.undoBuffer.reset ()

        # Make the first node the default centre node
        self.setCenterNode (0)
        self.START = self.INSTRUMENT_LOAD ('load:readDataset finish off', self.START)

        resource_usage.report('readDataset')
        return self.db
    def createNodes (self, tss):
        self.nodes = []
        _quintiles = tss.lastreldelta_quintiles ()
        _series = tss.getseries
        _red = QColor ('red')
        _font = QFont ('Decorative', 8)

        for i in range (self.N):
            _labelText = _series (i).label ()

            self.nodes.append (self.addNode (self, i,
                    _red, _red, _red, # These colours should never be seen
                    _labelText,
                    _font, # This font should never be seen
                    _series (i).tooltip (),
                    _quintiles [i] / 3.0 + 1.0, _labelText))
    def closeEvent (self, event):
        self.helpDialog.close ()
        event.accept()
    def leave (self):
        try:
            self.interruptLayoutsAndWaitForCompletion ()

            if self.db and self.bcFiles:
                self.bcFiles.saveConfiguration ()

            self.socialLayoutThread.exit ()
            self.galaxyLayoutThread.exit ()
            self.clusterLayoutThread.exit ()

            app.exit () # This is to quit Qt (PySide)
        except:
            None

        # Alas, when we quit Pyside it does some cleanup which can take forever. So, brutally quit the Python application to avoid this
        os.kill (os.getpid (), 9)

if __name__ == '__main__':
    app = QApplication (sys.argv)

    # Set the aplication-wide stylesheet
    file = QFile (':/config/Resources/stylesheet.qss')
    file.open (QFile.ReadOnly)
    app.setStyleSheet (str (file.readAll ()))

    appName = "We Are The Brand Communicators"
    bc = BrandCommunities (app, appName)
    bc.show ()

    if bc.mac:
        bc.activateWindow ()
        bc.raise_ ()

    QObject.connect (app, SIGNAL ('lastWindowClosed ()'), bc.leave)
    app.exec_ ()
