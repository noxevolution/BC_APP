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
import galaxylayout

class CasualCheckActionSelected (QDialog):
    def __init__ (self,thisNode,index,root, tss, centralNodeId, centralNode, normalised = False, parent = None, visibleOnly = True, *args):
        
        resource_usage = ConciseMonitor()
        QDialog.__init__ (self, *args)
        self.tss = tss
        self.thisNode = thisNode
        self.centralNodeId = centralNodeId
        self.centralNode = centralNode
        self.normalised = normalised
        self.parent = parent
        self.visibleOnly = visibleOnly
        self.index = index
        self.root = root
        self.columns = [node.labelText for node in thisNode.root.nodes]
        

        #self._layout = QVBoxLayout (self)
        
        
        self.window = Window(3, 6,tss, centralNodeId, centralNode, normalised, parent, index,root,self.columns)
        self.window.setAttribute (Qt.WA_DeleteOnClose, True)
        #window.setMinimumSize (1000, 200)
        self.window.setWindowTitle ('Operator Expertise')
        self.window.show()
        self.window.exec_()
        
 

class Window(QtGui.QWidget):
    def __init__(self, rows, columns,tss, centralNodeId, centralNode, normalised, parent, index,root,names):
        self.root=root
        self.tss = tss
        self.centralNodeId = centralNodeId
        self.centralNode = centralNode
        self.index = index
        self.rows=rows
        self.columns= columns
        self.names = names
        QtGui.QWidget.__init__(self)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label1 = QtGui.QLabel('Our algorithms indicate that `'+names[index]+'` is a contributory cause of `'+names[0]+'`.', self)
        self.label2 = QtGui.QLabel('Your input however (domain expertise) is also extremely important to help further interpret inferences about contributory cause and effect (see "INUS" and "Hill" causal conditions, BC website).', self)
        #label1.move(15, 10)
        self.label1.setFont(font)
        self.label2.setFont(font)
        
        self.layout = QtGui.QVBoxLayout(self)
        self.layout.addWidget(self.label1)
        self.layout.addWidget(self.label2)
        
        self.allButton = QPushButton ('Take Survey')
        self.allButton2 = QPushButton ('Cancel')
        self.allButton.setMaximumWidth(200)
        self.allButton2.setMaximumWidth(200)
        #self.allButton.setGeometry(120, 0, 120,100)
        self.layout.addWidget(self.allButton)
        self.layout.addWidget(self.allButton2)        
        QObject.connect (self.allButton, SIGNAL ('clicked ()'), self.allNodes)
        QObject.connect (self.allButton2, SIGNAL ('clicked ()'), self.closenode)
        self._list = []

    def closenode(self):
        self.hide()
    
        
    def allNodes (self):
        
        rows= self.rows
        columns= self.columns
        self.resize(1230, 200)
        self.table = QtGui.QTableWidget(rows, columns, self)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        
        
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(0, 705)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 80)
        
        self.vector1 = [['Considering the relationship between `'+self.names[self.index]+'` and `'+self.names[0]+'`, on the basis of your experience and knowledge: ','Agree', 'Somewhat agree','Neither A nor D','Somewhat disagree','Disagree'],['1. '+self.names[self.index]+' alone OR in combination with other factors (in the data tree or not) may serve as part of the cause of '+self.names[0],'', '','','',''],['2. The relationship is plausible/ feasible (it passes your commonsense test)','', '','','','']]
        for column in range(columns):
            
            for row in range(rows):                   
                item = QtGui.QTableWidgetItem(self.vector1[row ][column])
                if self.vector1[row ][column]=='':
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)                 

                self.table.setItem(row, column, item)
        self.table.itemClicked.connect(self.handleItemClicked)
        #layout = QtGui.QVBoxLayout(self)
        self.layout.addWidget(self.table)
        self.allButton3 = QPushButton ('Submit')
        self.layout.addWidget(self.allButton3)
        self.layout.removeWidget(self.allButton)
        self.layout.removeWidget(self.allButton2)
        self.layout.removeWidget(self.label1)
        self.layout.removeWidget(self.label2)
        QObject.connect (self.allButton3, SIGNAL ('clicked ()'), self.calculate)
        
       
    def handleItemClicked(self, item):
        if item.checkState() == QtCore.Qt.Checked:
            
            abc = [item.row(),item.column()]
            if abc not in self._list:                
                self._list.append(abc)
            else:
                self._list.remove(abc)
            
        else:
            abc = [item.row(),item.column()]
            if abc in self._list:                
                self._list.remove(abc)
                
    def doLayout (self, signal):
        if self.root.db:
            self.root.galaxyLayoutThread.interruptRequested = True
            self.busyIndicator = BusyIndicator (self.root, self)
            self.busyIndicator.setState (True)
            self.root.galaxy.view.largeBlueCircle.rotation = 0.0
            signal.emit ()
    def calculate(self):        
        #_coefficientMatrix = self.centralNode.root.cm.coeffs
        newdict = {1:5,2:4,3:3,4:2,5:1}
        _coefficientMatrix =self.root.cm.best
        #print _coefficientMatrix
        sum = 0
        self.w = None
        newlist = []
        for i in range(len(_coefficientMatrix)):
            if _coefficientMatrix[i].has_key(self.index):
                pass
                #print _coefficientMatrix[i][self.index]
                #_coefficientMatrix[i][self.index] = 0.820023473
        self.root.updateSelectionsAndHideButtons ()
        gal = galaxylayout.GalaxyLayoutThread(self.root)
        
        if len(self._list)<=2:
            for i in range(len(self._list)):
                newlist.append(self._list[i][0])
                sum +=newdict[self._list[i][1]] 
                newlist = list(set(newlist))
            if(len(newlist)==len(self._list)):  
                if sum >8:
                    reply = QtGui.QMessageBox.question(self, 'Message',
                                                       "Since your interpretation tends to Agree, it is suggested you continue with `" +self.names[self.index] + "` in any further analysis (do not HIDE it). " )
                    
                else:
                    reply = QtGui.QMessageBox.question(self, 'Message',
                                                       "Since your interpretation tends to Disagree, it is suggested you HIDE `"+self.names[self.index]+"` from further analysis (right-click it). " )
            else:
                reply = QtGui.QMessageBox.question(self, 'Message',
                                                   "You have to check single option against a checkbox!")
        else:
            reply = QtGui.QMessageBox.question(self, 'Message',
                                                   "You have checked too many options!")
            
        self.doLayout (self.root.galaxyLayoutThread.task_makeLinksSignal)
        self.hide()    
class BusyIndicator (QGraphicsRectItem):
    def __init__ (self, root, parent):
        QGraphicsRectItem.__init__ (self, root.TOTAL_SCALING, -root.TOTAL_SCALING, -20.0, 20.0)
        self.root = root
        self.parent = parent
        self.setBrush (self.root.constants.busyIndicatorBrush)
        self.setPen (self.root.constants.busyIndicatorPen)
        self.hide ()
        #parent.scene.addItem (self)
    def setState (self, state):
        self.setVisible (state)
        self.parent.update ()
        self.root.application.processEvents ()

class MyPopup(QWidget):
    def __init__(self):
        QWidget.__init__(self)

    def paintEvent(self, e):
        dc = QPainter(self)
        dc.drawLine(0, 0, 100, 100)
        dc.drawLine(100, 0, 0, 100)           
