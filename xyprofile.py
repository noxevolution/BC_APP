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

class XyProfile (QDialog):
    def __init__ (self, tss, association, timeSlice, normalised = False, parent = None, *args): 
        QDialog.__init__ (self, *args)
        self.setAttribute (Qt.WA_DeleteOnClose, True)

        self.setWindowTitle ('Profile Snapshot')
        self.setMinimumSize (QSize (500, 150))
        _layout = QVBoxLayout (self)
        self.columns = ['x', 'y', 'z']
        self.view = QTableView (self)
        _layout.addWidget (self.view)
        self.model = ProfileModel (tss, association, self.columns, normalised, parent, *args)
        self.view.setModel (self.model)

        # hide grid
        #self.view.setShowGrid (False)

        # set column width to fit contents
        #self.view.resizeColumnsToContents()

        # Colour the current column
        self.view.selectColumn (timeSlice)
        self.view.showColumn (timeSlice)

        # Add an 'OK' button
        self.okButton = QPushButton ('OK')
        _layout.addWidget (self.okButton)
        QObject.connect (self.okButton, SIGNAL ('clicked ()'), self.ok)
    def ok (self):
        self.done (0)

class ProfileModel (QAbstractTableModel): 
    def __init__ (self, tss, association, columns, normalised, parent = None, *args): 
        QAbstractTableModel.__init__ (self, parent, *args) 
        self.tss = tss
        self.columns = columns
        self.series = []

        if normalised:
            self.series.append (tss.series () [association.axis [0].combo.selectionId].getAllNormValues ())
            self.series.append (tss.series () [association.axis [1].combo.selectionId].getAllNormValues ())
            self.series.append (tss.series () [association.axis [2].combo.selectionId].getAllNormValues ())
        else:
            self.series.append (tss.series () [association.axis [0].combo.selectionId])
            self.series.append (tss.series () [association.axis [1].combo.selectionId])
            self.series.append (tss.series () [association.axis [2].combo.selectionId])

        self.allTimes = self.tss.series () [0].getAllTimes ()
        self.totalSteps = len (self.allTimes)
 
    def rowCount (self, parent): 
        return 3
 
    def columnCount (self, parent): 
        return self.totalSteps
 
    def data (self, index, role): 
        if not index.isValid (): 
            return None
        elif role != Qt.DisplayRole: 
            return None

        return self.series [index.row ()] [index.column ()]

    def headerData (self, col, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.allTimes [col]
            elif orientation == Qt.Vertical:
                return self.columns [col]

        return None
