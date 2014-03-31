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

class CoefficientsList (QDialog):
    def __init__ (self, tss, centralNodeId, centralNode, normalised = False, parent = None, visibleOnly = True, *args): 
        resource_usage = ConciseMonitor()
        QDialog.__init__ (self, *args)
        self.tss = tss
        self.centralNodeId = centralNodeId
        self.centralNode = centralNode
        self.normalised = normalised
        self.parent = parent
        self.visibleOnly = visibleOnly
        self.setAttribute (Qt.WA_DeleteOnClose, True)

        self.setWindowTitle ('Coefficient List')
        self.setMinimumSize (QSize (700, 400))
        _layout = QVBoxLayout (self)

        self.view = QTableView (self)
        _layout.addWidget (self.view)
        self.model = ProfileModel (tss, centralNodeId, centralNode, normalised, parent, visibleOnly)
        self.view.setModel (self.model)

        # hide grid
        #self.view.setShowGrid (False)

        # sorting
        self.proxyModel = QSortFilterProxyModel ()
        self.proxyModel.setSourceModel (self.model)
        self.proxyModel.setDynamicSortFilter (True)
        self.view.setModel (self.proxyModel)
        self.view.setSortingEnabled (False)
        self.view.horizontalHeader ().setSortIndicatorShown (False)
        self.view.horizontalHeader ().setClickable (False)

        self.view.setColumnHidden (0, True)
        self.view.setColumnHidden (1, True)

        # set column width to fit contents
        self.view.resizeColumnsToContents ()

        # Add a status line
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

        self.view.showRow (0)
        self.sortIt ()
    def allNodes (self):
        self.model.dataReset (False)
        self.statusLine.setText (self.reportStatistics ())
        self.sortIt ()
    def visibleNodes (self):
        self.model.dataReset (True)
        self.statusLine.setText (self.reportStatistics ())
        self.sortIt ()
    def sortIt (self):
        self.proxyModel.sort (1, order = QtCore.Qt.DescendingOrder)
    def ok (self):
        self.done (0)
    def reportStatistics (self):
        return None

class ProfileModel (QAbstractTableModel): 
    def __init__ (self, tss, centralNodeId, centralNode, normalised = False, parent = None, visibleOnly = True): 
        QAbstractTableModel.__init__ (self) 
        self.tss = tss
        self.centralNodeId = centralNodeId
        self.centralNode = centralNode
        self.visibleOnly = visibleOnly
        self.dataReset (visibleOnly)
    def dataReset (self, visibleOnly):
        self.visibleOnly = visibleOnly
        self.series = []
        self.nonZeroCount = 0
        self.negativeCount = 0
        self.columns = ['Index', 'Absolute Large Coefficient', 'Large Coefficient', 'Small Coefficient']
        self.vector = dict ()

        _coefficientMatrix = self.centralNode.root.cm.coeffs

        self.visibleCount = 0
        self.vector = []

        for i, _node in enumerate (self.centralNode.root.nodes):
            if not self.visibleOnly or not _node.hiding:
                _c1 = None if self.centralNodeId not in _coefficientMatrix [i] else _coefficientMatrix [i] [self.centralNodeId]
                _c2 = None if i not in _coefficientMatrix [self.centralNodeId] else _coefficientMatrix [self.centralNodeId] [i]
                self.vector.append (self.encode (i, self.centralNodeId, _c1, _c2, _node.labelText))
                self.visibleCount += 1
		print self.vector
        self.reset ()
    def encode (self, i, centralNodeId, c1, c2, label):
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
    def rowCount (self, parent): 
        return self.visibleCount
    def columnCount (self, parent): 
        return len (self.columns)
    def data (self, index, role): 
        if not index.isValid (): 
            return None
        elif role != Qt.DisplayRole: 
            return None

        if self.vector [index.row ()] [0] == self.centralNodeId:
            if index.column () == 2:
                return 'Central Node'
            elif index.column () < 2:
                return self.vector [index.row ()] [index.column ()]
        else:
            return self.vector [index.row ()] [index.column ()]
    def headerData (self, row, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.columns [row]
            else:
                return self.vector [row] [4]

        return None
