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
from unidecode import unidecode

class UniverseProfile (QDialog):
    def __init__ (self, tss, thisNode, normalised = False, parent = None, *args): 
        QDialog.__init__ (self, *args)
        self.setAttribute (Qt.WA_DeleteOnClose, True)
        self.thisNode = thisNode
        
        self.setWindowTitle ('Profile Snapshot')
        self.setMinimumSize (QSize (700, 400))
        _layout = QVBoxLayout (self)
        self.columns = [node.labelText for node in thisNode.root.nodes]
        self.view = QTableView (self)
        _layout.addWidget (self.view)
        self.model = ProfileModel (tss, self.columns, thisNode, normalised, parent, *args)
        self.view.setModel (self.model)
        _hLayout = QHBoxLayout ()
        _layout.addLayout (_hLayout)

        # hide grid
        #self.view.setShowGrid (False)

        # set column width to fit contents
        self.view.resizeColumnsToContents()

        # Colour the current column
        self.view.selectRow (thisNode.index)
        self.view.showRow (thisNode.index)

        # Add an 'OK' button
        self.okButton = QPushButton ('OK')
        _hLayout.addWidget (self.okButton)
        QObject.connect (self.okButton, SIGNAL ('clicked ()'), self.ok)

        # Add a 'Dump' button
        self.dumpButton = QPushButton ('Dump')
        _hLayout.addWidget (self.dumpButton)
        QObject.connect (self.dumpButton, SIGNAL ('clicked ()'), self.dump)
    def ok (self):
        self.done (0)
    def dump (self):
        print '\t',

        for i in self.model.allTimes:
            print '%s\t' % i,

        print

        for i in range (len (self.thisNode.root.nodes)):
            try:
                print '%s\t' % unidecode(self.model.columns [i]),
            except:
                print 'ILLEGAL CHARACTER IN NAME\t',

            for j in range (len (self.model.series [i])):
                try:
                    print '%.2f\t' % self.model.series [i] [j],
                except:
                    print '\t',
            print

        sys.stdout.flush ()

class ProfileModel (QAbstractTableModel): 
    def __init__ (self, tss, columns, thisNode, normalised = False, parent = None, *args): 
        QAbstractTableModel.__init__ (self, parent, *args) 
        self.tss = tss
        self.columns = columns
        self.thisNode = thisNode
        self.series = []

        for i in range (len (thisNode.root.nodes)):
            if normalised:
                self.series.append (self.tss.series () [i].getAllNormValues ())
            else:
                self.series.append (self.tss.series () [i])

        self.allTimes = self.tss.series () [0].getAllTimes ()
        self.totalSteps = len (self.allTimes)

    def rowCount (self, parent): 
        return self.thisNode.root.N
 
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
