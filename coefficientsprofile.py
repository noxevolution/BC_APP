#!/usr/bin/env python

import sys
import time
import PySide

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtUiTools import *

from constants import *
from application import *
from timeseries import *
from random import *
from xyplot import *
from monitor import ConciseMonitor

class CoefficientsProfile (QDialog):
    def __init__ (self, tss, thisNode, normalised = False, parent = None, visibleOnly = True, *args): 
        resource_usage = ConciseMonitor()
        QDialog.__init__ (self, *args)
        self.tss = tss
        self.thisNode = thisNode
        self.normalised = normalised
        self.parent = parent
        self.visibleOnly = visibleOnly
        self.setAttribute (Qt.WA_DeleteOnClose, True)

        self.setWindowTitle ('Coefficients')
        self.setMinimumSize (QSize (700, 400))
        _layout = QVBoxLayout (self)
        _currentRow = thisNode.index

        self.view = QTableView (self)
        _layout.addWidget (self.view)
        self.model = ProfileModel (tss, thisNode, normalised, parent, visibleOnly)
        self.view.setModel (self.model)

        # hide grid
        #self.view.setShowGrid (False)

        # set column width to fit contents
        #self.view.resizeColumnsToContents ()

        # Colour the current row
        self.view.selectRow (_currentRow)
        self.view.showRow (_currentRow)

        # Add a status line for Rick
        self.statusLine = QLabel (self.reportStatistics ())
        _layout.addWidget (self.statusLine)

        # Add buttons
        _buttonLayout = QHBoxLayout ()
        _layout.addLayout (_buttonLayout)
        self.allButton = QPushButton ('All nodes')
        _buttonLayout.addWidget (self.allButton)
        QObject.connect (self.allButton, SIGNAL ('clicked ()'), self.allNodes)
        self.visibleButton = QPushButton ('Visible nodes only')
        _buttonLayout.addWidget (self.visibleButton)
        QObject.connect (self.visibleButton, SIGNAL ('clicked ()'), self.visibleNodes)
        self.okButton = QPushButton ('OK')
        _buttonLayout.addWidget (self.okButton)
        QObject.connect (self.okButton, SIGNAL ('clicked ()'), self.ok)
        resource_usage.report('CoefficientsProfile init')
    def allNodes (self):
        self.model = ProfileModel (self.tss, self.thisNode, self.normalised, self.parent, False)
        self.view.setModel (self.model)
        self.statusLine.setText (self.reportStatistics ())
    def visibleNodes (self):
        self.model = ProfileModel (self.tss, self.thisNode, self.normalised, self.parent, True)
        self.view.setModel (self.model)
        self.statusLine.setText (self.reportStatistics ())
    def ok (self):
        self.done (0)
    def reportStatistics (self):
        _tableSize = self.model.columnCount (self.parent)
        return 'There are %d cells in total; %d of them are non-zero (%d are negative and %d are positive)' % \
                (_tableSize * _tableSize, self.model.nonZeroCount, self.model.negativeCount, self.model.nonZeroCount - self.model.negativeCount)

class ProfileModel (QAbstractTableModel): 
    def __init__ (self, tss, thisNode, normalised = False, parent = None, visibleOnly = True): 
        QAbstractTableModel.__init__ (self) 
        self.tss = tss
        self.thisNode = thisNode
        self.visibleOnly = visibleOnly
        self.series = []
        self.nonZeroCount = 0
        self.negativeCount = 0

        _coefficientMatrix = thisNode.root.cm.coeffs

        if visibleOnly:
            self.visibleCount = 0
            self.columns = []
            self.lookup = []

            for i, node in enumerate (thisNode.root.nodes):
                if not node.hiding:
                    self.visibleCount += 1
                    self.columns.append (node.labelText)
                    self.lookup.append (i)

                if thisNode.index == i:
                    _currentRow = len (self.lookup) - 1
        else:
            self.columns = [node.labelText for node in thisNode.root.nodes]
            self.visibleCount = len (self.columns)
            self.lookup = range (len (thisNode.root.nodes))

        for x, i in enumerate (self.lookup):
            if self.visibleOnly:
                _coefficientVector = []

                for j in self.lookup:
                    if j in _coefficientMatrix [i]:
                        _coefficientVector.append (_coefficientMatrix [i] [j])
            else:
                _coefficientVector = _coefficientMatrix [i]

            self.nonZeroCount += len (_coefficientVector)

            if self.columns [x].find ('Dilo') != -1:
                if len (_coefficientVector) > 0:
                    print self.columns [x], len (_coefficientVector)

            for _coeff in _coefficientVector:
                if _coeff < 0.0:
                    self.negativeCount += 1
    def rowCount (self, parent): 
        return self.visibleCount
    def columnCount (self, parent): 
        return self.visibleCount
    def data (self, index, role): 
        if not index.isValid (): 
            return None
        elif role != Qt.DisplayRole: 
            return None

        _coefficients = self.thisNode.root.cm.coeffs [self.lookup [index.row ()]]

        if len (_coefficients) == 0:
            return None

        _column = self.lookup [index.column ()]

        if _column not in _coefficients:
            return None

        return _coefficients [_column]
    def headerData (self, col, orientation, role):
        if role == Qt.DisplayRole:
            return self.columns [col]

        return None
