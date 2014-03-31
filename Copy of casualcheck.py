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

class CasualCheckActionSelected (QDialog):
    def __init__ (self, tss, centralNodeId, centralNode, normalised = False, parent = None, visibleOnly = True, *args): 
        resource_usage = ConciseMonitor()
        QDialog.__init__ (self, *args)
        self.tss = tss
        self.centralNodeId = centralNodeId
        self.centralNode = centralNode
        self.normalised = normalised
        self.parent = parent
        self.visibleOnly = visibleOnly
        

        _layout = QVBoxLayout (self)
        
        window = Window(4, 6)
        window.setAttribute (Qt.WA_DeleteOnClose, True)
        window.setMinimumSize (QSize (900, 400))
        window.setWindowTitle ('Soft Causal Check')
        window.show()
        sys.exit(app.exec_())
        
 

class Window(QtGui.QWidget):
    def __init__(self, rows, columns):
        QtGui.QWidget.__init__(self)
        self.table = QtGui.QTableWidget(rows, columns, self)
        
        self.vector1 = [['On the basis of your experience and knowledge:(For each question, please check a box to the right)','Agree', 'Somewhat agree','Neither A nor D','Somewhat disagree','Disagree'],['Q1: The above relationship is plausible/ feasible (it passes the commonsense test)','', '','','',''],['Q2: There exists a "mechanism", a "connection" or a "forcing quality" (implicitly or explicitly) between X and Y such that X could serve as a contributory cause of Y','', '','','',''],['Q3: The above relationship is plausible/ feasible (it passes the commonsense test)','', '','','','']]
        for column in range(columns):
            
            for row in range(rows):                   
                item = QtGui.QTableWidgetItem(self.vector1[row ][column])
                if self.vector1[row ][column]=='':
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)                 

                self.table.setItem(row, column, item)
        self.table.itemClicked.connect(self.handleItemClicked)
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.table)
        self._list = []

    def handleItemClicked(self, item):
        if item.checkState() == QtCore.Qt.Checked:
            print('"%s" Checked' % item.text())
            self._list.append(item.row())
            print(self._list)
        else:
            print('"%s" Clicked' % item.text())

