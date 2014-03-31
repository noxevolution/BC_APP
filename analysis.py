import numpy
import locale
import warnings
import sys
import time
import PySide
from datetime import date
from dateutil.relativedelta import *
import math
import re
import random
import tools
import rpy
import subprocess
import os
from rpy import *
import math
import csv

import PySide.QtCore as QtCore
import PySide.QtGui as QtGui
from PySide.QtUiTools import *
from PySide.QtWebKit import *
#from win32com.client import Dispatch



class DummyAnalysisSlider ():
    def __init__ (self):
        self.slider = QtGui.QSlider ()
    def setSpan (self, dummy1, dummy2):
        pass

class AnalysisTimeseriesSelectorLabel (QtGui.QLabel):
    def __init__ (self, root, listItem):
        QtGui.QLabel.__init__ (self)
        self.root = root
        self.listItem = listItem
        self.labels = []

        for ts in self.root.tss.series ():
            self.labels.append (ts.label ())

        self.index = 0
        self.setText (self.labels [0])

class AnalysisTimeseriesSelectorComboBox (QtGui.QComboBox):
    def __init__ (self, root, listItem, index = 0):
        QtGui.QComboBox.__init__ (self)
        self.lastIndex = index 
        self.root = root
        self.setMinimumContentsLength (10)

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_DROPONCOMBOBOX:
            self.setAcceptDrops (True)
        else:
            self.setEnabled (False)

        self.listItem = listItem
        self.labels = []

        for ts in self.root.tss.series ():
            self.labels.append (ts.label ())

        self.addItems (self.labels)
        #self.setToolTip (self.labels [0])
        self.setCurrentIndex (index)
        QtCore.QObject.connect (self, QtCore.SIGNAL ('currentIndexChanged (int)'), self.selectionChanged)
    def dragEnterEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            if len (event.mimeData ().text ().split (',')) == 1:
                event.acceptProposedAction ()
    def dropEvent (self, event):
        if event.mimeData ().hasFormat ('text/plain'):
            if len (event.mimeData ().text ().split (',')) == 1:
                event.acceptProposedAction ()
                self.setCurrentIndex (int (event.mimeData ().text ()))
                self.setToolTip (self.labels [self.currentIndex ()])
    def makeIntoList (self, thing, length):
        _list = []

        for i in range (length):
            _list.append (thing [i])

        return _list
    def getMostRecentTime (self, timeseriesId):
        _series = self.root.tss.series () [timeseriesId].getAllNormValues ()
        _seriesData = self.makeIntoList (_series, len (self.root.tss.series () [timeseriesId].getAllTimes ()))

        while _seriesData [-1] == None:
            _seriesData.pop ()

        return self.root.tss.series () [timeseriesId].getAllTimes () [len (_seriesData) - 1]
    def selectionChanged (self, index):
        if self.listItem.plotType == 'target':
            if self.root.analysisPlot.changeTargetSeries (self, self.lastIndex, index) != -1:
                self.lastIndex = index
        else:
            self.root.analysisPlot.changeSourceSeries (self, self.lastIndex, index)

        self.listItem.graph.timeseriesChanged ()
        self.listItem.graph.plot ()

class AnalysisView ():
    def __init__ (self, root, parent):
        self.root = root
        self.parent = parent
        self.cutoffSlider = DummyAnalysisSlider ()
        self.linkOpacitySlider = DummyAnalysisSlider ()
        self.nodeSizeSlider = DummyAnalysisSlider ()
        self.links = []
        self.rotation = QtCore.QPointF (0, 0)

class AnalysisGraph (QtGui.QGraphicsView):
    def __init__ (self, root, analysisPlot, labelPanel, timeseriesSelector, plotType):
        QtGui.QGraphicsView.__init__ (self)
        self.root = root
        self.analysisPlot = analysisPlot
        self.labelPanel = labelPanel
        self.timeseriesSelector = timeseriesSelector
        self.plotType = plotType
        self.setRenderHints (QtGui.QPainter.Antialiasing)

        self.setMinimumSize (1, 1)
        self.segments = []
        self.scene = QtGui.QGraphicsScene ()
        self.setScene (self.scene)
        self.setHorizontalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        self.timeseriesId = self.timeseriesSelector.currentIndex ()
        self.mousePressed = False
        
    def mousePressEvent (self, event):
        QtGui.QGraphicsView.mousePressEvent (self, event)
        self.mousePressed = True
        self.mousePressedPos = event.x ()
        self.initialOffset = self.analysisPlot.offset
    def mouseMoveEvent (self, event):
        QtGui.QGraphicsView.mouseMoveEvent (self, event)

        if self.mousePressed and not self.analysisPlot.movingPoint:
            self.displacement = (event.x () - self.mousePressedPos)
            self.analysisPlot.offset = min (self.analysisPlot.extendedTimesteps - self.analysisPlot.samples, \
                                            max (0, self.initialOffset + (self.analysisPlot.samples * self.displacement) / 400))
            self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
            self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
    def mouseReleaseEvent (self, event):
        QtGui.QGraphicsView.mouseReleaseEvent (self, event)
        self.mousePressed = False
        #self.parent ().forecast ()
        #self.mousePressed = False
    def wheelEvent (self, event):
        self.analysisPlot.samples = max (8, min (self.analysisPlot.extendedTimesteps, self.analysisPlot.samples - event.delta () / 50))
        self.analysisPlot.offset = min (self.analysisPlot.offset, self.analysisPlot.extendedTimesteps - self.analysisPlot.samples)
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
    def timeseriesChanged (self):
        self.timeseriesId = self.timeseriesSelector.currentIndex ()
        #self.plot () # Already done in line above
    def datasetChange (self):
        self.plot ()
    def resizeEvent (self, event):
        self.plot ()
        #self.root.application.processEvents ()
        #self.update ()
        self.analysisPlot.viewportWidth = self.width ()
    def scalingStats (self, timeseries):
        _min = 1e99
        _max = -1e99

        for i in range (self.analysisPlot.extendedTimesteps):
            try:
                if timeseries [i] != None:
                        _max = max (_max, timeseries [i])
                        _min = min (_min, timeseries [i])
            except:
                pass

            _diff = (_max - _min)

            try:
                 m = 1.0 / _diff
                 c = 1.0 - _max / _diff
            except:
                 m = 1.0
                 c = 0.0

        return _min, _max, m, c
    def fft (self, series, highCutoff, lowCutoff = 0):
        _ft = numpy.fft.rfft (series)

        for i in range (len (_ft)):
            if i > highCutoff or i < lowCutoff:
                _ft [i] = 0.0

        _ift = numpy.fft.irfft (_ft)

        return _ift
    def plot (self):
        
        self.scene.clear ()
        _plotType = self.plotType
        self.segments = []

        if _plotType == 'target':
            self.setStyleSheet ("background: pink")
        else:
            self.setStyleSheet ("background: lightYellow")

        # Draw a box around the region of interest
        _rect = QtCore.QRect (self.analysisPlot.extendedTimesteps - self.analysisPlot.offset - self.analysisPlot.samples, 0,
                self.analysisPlot.samples, self.analysisPlot.YFACTOR)

        _r = QtGui.QGraphicsRectItem (_rect)
        _r.setPen (self.analysisPlot.transparent)
        #_r.setPen (QtGui.QColor ('green'))
        self.scene.addItem (_r)
        self.segments.append (_r)
        self.fitInView (_r)
        
        if self.timeseriesId not in self.analysisPlot.validity:
            self.analysisPlot.makeExtendedTimeseries (self.timeseriesId)

        _timeseries = self.analysisPlot.originals [self.timeseriesId]

        # Get some scaling statistics
        self.minimum, self.maximum, m, c = self.scalingStats (_timeseries)
        #print self.minimum, self.maximum, m, c, _timeseries, self.analysisPlot.extendedTimesteps
        locale.setlocale (locale.LC_ALL, '')

        try:
            if abs (self.minimum) > 1e6 or abs (self.maximum) > 1e6:
                self.labelPanel.upper.setText ('%.1e' % self.maximum)
                self.labelPanel.lower.setText ('%.1e' % self.minimum)
            else:
                self.labelPanel.upper.setText (locale.format ('%.1f', self.maximum, True))
                self.labelPanel.lower.setText (locale.format ('%.1f', self.minimum, True))
        except:
            self.labelPanel.upper.setText ('?')
            self.labelPanel.lower.setText ('?')
            self.minimum = 0.0
            self.maximum = 0.0

        # Draw the x axis if it's in range
        if (self.maximum * self.minimum) < 0.0:
            _x = QtGui.QGraphicsLineItem (0, c * self.analysisPlot.YFACTOR, self.analysisPlot.extendedTimesteps - 1, c * self.analysisPlot.YFACTOR)
            _x.setPen (self.analysisPlot.axisColor)
            self.scene.addItem (_x)
            self.segments.append (_x)

        for x, y in enumerate (_timeseries [:self.analysisPlot.extendedTimesteps - 1]):
            x1 = x + 1

            """
            # Plot historic predictions
            if self.root.historicPredictionsCheckbox.isChecked () and _plotType == 'target' and self.analysisPlot.stata [self.timeseriesId] [x + 1]:
                try:
                    _prediction0 = self.analysisPlot.predictions [self.timeseriesId] [x]
                    _prediction1 = self.analysisPlot.predictions [self.timeseriesId] [x + 1]
                    y0 = (m * _prediction0 + c) * self.analysisPlot.YFACTOR
                    y1 = (m * _prediction1 + c) * self.analysisPlot.YFACTOR
                    _segment = QtCore.QLineF (x, y0, x1, y1)
                    _graphic = QtGui.QGraphicsLineItem (_segment)
                    _graphic.setPen (QtGui.QColor ('green'))
                    self.segments.append (_graphic)
                    _graphic.setZValue (1)
                    self.scene.addItem (_graphic)
                    #_pointGraphic = PointGraphic (self.root, self.analysisPlot, self.scene, self, _timeseries, _segment, self.timeseriesId, x1)
                except:
                    pass
            """

            # Plot future predictions
            y1 = 0

            try:
                y0 = (m * y + c) * self.analysisPlot.YFACTOR  
                y1 = (m * _timeseries [x + 1] + c) * self.analysisPlot.YFACTOR
                _segment = QtCore.QLineF (x, y0, x1, y1)
                _graphic = QtGui.QGraphicsLineItem (_segment)

                if self.analysisPlot.stata [self.timeseriesId] [x1]:
                    _graphic.setPen (self.analysisPlot.originalColor)
                else:
                    _graphic.setPen (self.analysisPlot.extendedColor)

                    if _plotType == 'source':
                        
                        _pointGraphic = PointGraphic (self.root, self.analysisPlot, self.scene, self, _timeseries, _segment, self.timeseriesId, x1)
            except:
                _segment = QtCore.QLineF (x - self.analysisPlot.offset, 0, x1 - self.analysisPlot.offset, self.analysisPlot.YFACTOR)
                _graphic = QtGui.QGraphicsLineItem (_segment)
                _graphic.setPen (self.analysisPlot.transparent)

            self.segments.append (_graphic)
            _graphic.setZValue (1)
            self.scene.addItem (_graphic)

        # Add some points for tooltips
        if _plotType == 'source':
            _p = self.mapToScene (7, 7) - self.mapToScene (0, 0)
        else:
            _p = self.mapToScene (3, 3) - self.mapToScene (0, 0)

        for x, y in enumerate (_timeseries [:self.analysisPlot.extendedTimesteps]):
            try:
                y0 = (m * y + c) * self.analysisPlot.YFACTOR
            except:
                pass
            else:
                #_graphic = QtGui.QGraphicsRectItem ()
                _graphic = FixedPointGraphic (self.root, self.scene, self.analysisPlot, x, y0, _p.x (), _p.y (), _plotType == 'source')

                #if _plotType == 'source':
                #    _graphic.setBrush (self.analysisPlot.transparent)
                #else:
                #    _graphic.setBrush (QtGui.QColor ('black'))

                #_graphic.setPen (QtGui.QColor ('black'))
                #self.scene.addItem (_graphic)
                _graphic.setToolTip ('(%s, %.2f)' % (self.analysisPlot.timePoints [x], _timeseries [x]))
                self.segments.append (_graphic)

class FixedPointGraphic (QtGui.QGraphicsRectItem):
    def __init__ (self, root, scene, analysisPlot, x, y, width, height, transparent):
        QtGui.QGraphicsRectItem.__init__ (self)

        self.root = root
        self.scene = scene
        self.plot = analysisPlot
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.transparent = transparent
        self.setRect (QtCore.QRectF (x - self.width / 2.0, y - self.height / 2.0, self.width, self.height))

        if transparent:
            self.setBrush (self.plot.transparent)
        else:
            self.setBrush (QtGui.QColor ('black'))

        self.setAcceptHoverEvents (True)
        scene.addItem (self)
    def hoverEnterEvent (self, event):
        #self.oldColor = self.brush ()
        #self.setBrush (QtGui.QColor ('green'))
        self.setRect (QtCore.QRectF (self.x - self.width, self.y - self.height, self.width * 2.0, self.height * 2.0))
        QtGui.QGraphicsRectItem.hoverEnterEvent (self, event)
    def hoverLeaveEvent (self, event):
        #self.setBrush (self.oldColor)
        self.setRect (QtCore.QRectF (self.x - self.width / 2.0, self.y - self.height / 2.0, self.width, self.height))
        QtGui.QGraphicsRectItem.hoverLeaveEvent (self, event)

class PointGraphic (QtGui.QGraphicsRectItem):
    def __init__ (self, root, analysisPlot, scene, view, timeseries, segment, timeseriesId, index):
        QtGui.QGraphicsRectItem.__init__ (self)
        
        self.root = root
        self.analysisPlot = analysisPlot
        self.scene = scene
        self.view = view
        self.timeseries = timeseries
        self.segment = segment
        self.timeseriesId = timeseriesId
        self.index = index
        self.x2 = self.segment.x2 ()
        self.y2 = self.segment.y2 ()
        _p = self.view.mapToScene (7, 7) - self.view.mapToScene (0, 0)
        self.width = _p.x ()
        self.height = _p.y ()
        self.yRange = self.view.maximum - self.view.minimum
        self.setRect (QtCore.QRectF (self.x2 - self.width / 2.0, self.y2 - self.height / 2.0, self.width, self.height))
        self.setBrush (self.analysisPlot.extendedColor)
        self.setPen (QtGui.QColor ('black'))
        self.scene.addItem (self)
        self.setAcceptHoverEvents (True)
        self.originalY = 0.0
    def hoverEnterEvent (self, event):
        #self.oldColor = self.brush ()
        #self.setBrush (QtGui.QColor ('green'))
        self.setRect (QtCore.QRectF (self.x2 - self.width, self.y2 - self.height, self.width * 2, self.height * 2))
        QtGui.QGraphicsRectItem.hoverEnterEvent (self, event)
    def hoverLeaveEvent (self, event):
        #self.setBrush (self.oldColor)
        self.setRect (QtCore.QRectF (self.x2 - self.width / 2.0, self.y2 - self.height / 2.0, self.width, self.height))
        QtGui.QGraphicsRectItem.hoverLeaveEvent (self, event)
    def mousePressEvent (self, event):
        
        self.mousePressed = True
        self.mouseDownPosition = event.pos ()

        if self.timeseriesId not in self.analysisPlot.validity:
            self.analysisPlot.makeExtendedTimeseries (self.timeseriesId)

        self.originalY = self.analysisPlot.originals [self.timeseriesId] [int (self.x2)]
        self.x1 = self.segment.x1 ()
        self.y1 = self.segment.y1 ()
        self.x2 = self.segment.x2 ()
        self.y2 = self.segment.y2 ()
        self.analysisPlot.movingPoint = True
    def mouseMoveEvent (self, event):
        
        if self.mousePressed:
            self.y2 = (event.pos ().y () / self.analysisPlot.YFACTOR) * self.yRange + self.view.minimum
            #### this takes the plot value while mouse moving 
            if self.timeseriesId not in self.analysisPlot.validity:
                self.analysisPlot.makeExtendedTimeseries (self.timeseriesId)
            self.x2  #################   This takes the position of which has been changed
            self.analysisPlot.originals [self.timeseriesId] [int (self.x2)] = self.y2
            self.setRect (QtCore.QRectF (self.x2 - self.width / 2.0, event.pos ().y () - self.height / 2.0, self.width, self.height))
    def mouseReleaseEvent (self, event):
        #### this method is called after mouse relelased
        _changes = True

        try:
            _changes = (self.originalY != self.analysisPlot.originals [self.timeseriesId] [int (self.x2)])
        except:
            _changes = True

        self.analysisPlot.movingPoint = False
        self.mousePressed = False
        ### Forecast bug fix 1
        if _changes:
            pass
            #self.view.parent ().forecast (self.x2)

        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
    def mouseDoubleClickEvent (self, event):
        _value = QtGui.QInputDialog.getDouble (self.analysisPlot, 'Enter Point Value', 'Value:', self.timeseries [self.index])
        self.y2 = _value [0]

        if self.timeseriesId not in self.analysisPlot.validity:
             self.analysisPlot.makeExtendedTimeseries (self.timeseriesId)

        self.analysisPlot.originals [self.timeseriesId] [int (self.x2)] = self.y2
        self.timeseries [self.index] = self.y2
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        #self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
        #self.view.parent ().forecast (self.x2)

class AnalysisGraphLabelPanel (QtGui.QVBoxLayout):
    def __init__ (self, root, plotType):
        QtGui.QVBoxLayout.__init__ (self)

        if plotType == 'target':
            _dummy = QtGui.QComboBox ()
        else:
            _dummy = QtGui.QLabel ()

        _dummy.setMaximumWidth (0)

        self.addWidget (_dummy)
        self.upper = QtGui.QLabel ()
        self.upper.setMinimumWidth (55)
        self.upper.setMaximumWidth (55)
        self.upper.setAlignment (QtCore.Qt.AlignRight)
        self.addWidget (self.upper)
        self.addStretch (1000)
        self.lower = QtGui.QLabel ()
        self.lower.setAlignment (QtCore.Qt.AlignRight)
        self.addWidget (self.lower)

class AnalysisPlotListItem (QtGui.QWidget):
    def __init__ (self, root, analysisPlot, listLayout, plotType, index = 0,trackForecastButton=0):
        QtGui.QWidget.__init__ (self)
        self.root = root
        self.setParent (analysisPlot)
        self.analysisPlot = analysisPlot
        self.listLayout = listLayout
        self.plotType = plotType
        self.index = index        

        self.hboxLayout = QtGui.QHBoxLayout ()
        self.setLayout (self.hboxLayout)
        self.labelPanel = AnalysisGraphLabelPanel (self.root, plotType)
        self.hboxLayout.addLayout (self.labelPanel)
        self.graphLayout = QtGui.QVBoxLayout ()
        self.graphLayout.setSpacing (0)
        self.timeseriesSelectorLayout = QtGui.QHBoxLayout ()
        self.graphLayout.addLayout (self.timeseriesSelectorLayout)

        self.timeseriesSelectorComboBox = AnalysisTimeseriesSelectorComboBox (self.root, self, index)
        self.timeseriesSelectorLayout.addWidget (self.timeseriesSelectorComboBox)

        # Add a zero button
        if plotType == 'source':
            self.zeroButton = QtGui.QToolButton ()
            self.zeroButton.setMinimumSize (QtCore.QSize (1, 1))
            self.zeroButton.setIcon (QtGui.QIcon (':/images/Resources/zero20x20.png'))
            self.zeroButton.setToolTip ('Reset the future values of this graph')
            self.zeroButton.setMinimumWidth (25)
            self.zeroButton.setMaximumWidth (25)
            self.timeseriesSelectorLayout.addWidget (self.zeroButton)
            QtCore.QObject.connect (self.zeroButton, QtCore.SIGNAL ('clicked ()'), self.zeroGraph)

        # Add a delete button
        self.deleteButton = QtGui.QToolButton ()
        self.deleteButton.setMinimumSize (QtCore.QSize (1, 1))
        self.deleteButton.setIcon (QtGui.QIcon (':/images/Resources/remove20x20.png'))
        self.deleteButton.setToolTip ('Remove this graph')
        self.deleteButton.setMinimumWidth (25)
        self.deleteButton.setMaximumWidth (25)
        QtCore.QObject.connect (self.deleteButton, QtCore.SIGNAL ('clicked ()'), self.removeGraph)
        
        # Add Lag Period
        #_layout = QtGui.QHBoxLayout ()
        #_b.addLayout (_layout)
        if plotType == 'source':
            self.lagSpinBox = QtGui.QSpinBox ()
            self.lagSpinBox.setValue (0)
            self.lagSpinBox.setMinimum (-20)
            self.lagSpinBox.setMaximum (9999)
            QtCore.QObject.connect (self.lagSpinBox, QtCore.SIGNAL ('valueChanged (int)'), self.lagAltered)
            self.timeseriesSelectorLayout.addWidget (self.lagSpinBox)
            
        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_ADDANDDELETE:
            self.timeseriesSelectorLayout.addWidget (self.deleteButton)
            
        if trackForecastButton==0:
            if plotType == 'source':
                self.listLayout.addWidget (self)
            else:
                self.listLayout.insertWidget (0, self)
        
        
            self.graph = AnalysisGraph (self.root, self.analysisPlot, self.labelPanel, self.timeseriesSelectorComboBox, plotType)
            self.graphLayout.addWidget (self.graph)
            self.hboxLayout.addLayout (self.graphLayout)
            self.graph.plot ()
    def zeroGraph (self):
        _future, _length = tools.findEnd (False, self.analysisPlot.stata [self.index])
        _mostRecentValue = self.analysisPlot.originals [self.index] [_future - 1]

        for i in range (_future, _length):
            self.analysisPlot.originals [self.index] [i] = _mostRecentValue
            self.analysisPlot.predictions [self.index] [i] = _mostRecentValue
        
        self.forecast ()
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
    def lagAltered(self,value):
    
        self.lagExtent = 'TBD'
        self.analysisPlot.extendForLagTime (value, self.lagExtent,self.graph.timeseriesId)
        self.graph.plot ()
        #self.forecast()
        #print self.index
        #_mostRecentValue = self.analysisPlot.originals [self.index] ### Plot value for this timeseries id
        
        #_future, _length = tools.findEnd (False, self.analysisPlot.stata [self.index])
        #print _length
        #_mostRecentValue = self.analysisPlot.originals [self.index] [_future - 1]

        #for i in range (_future, _length):
            #self.analysisPlot.originals [self.index] [i] = _mostRecentValue
            #self.analysisPlot.predictions [self.index] [i] = _mostRecentValue
        
        #self.forecast ()
        #self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        #self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
         
    def removeGraph (self):
        if self.plotType == 'target':
            self.analysisPlot.removeTargetSeries (self.index)
        else:
            self.analysisPlot.removeSourceSeries (self.index)
            self.forecast ()
    def refreshDisplay (self):
        
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))

    def displayMessageBox (self, title, message):
        self.messageBox = QtGui.QMessageBox (QtGui.QMessageBox.Information, title, message)
        self.messageBox.setStandardButtons (QtGui.QMessageBox.NoButton)
        self.messageBox.setWindowModality (QtGui.Qt.NonModal)
        self.messageBox.show ()

        for i in range (1000):
            self.application.processEvents ()

    def displayCancellableMessageBox (self, title, message):
        self.cancellableMessageBox = QtGui.QMessageBox (QtGui.QMessageBox.Information, title, message)
        self.cancellableMessageBox.setStandardButtons (QtGui.QMessageBox.Ok)
       # self.application.processEvents ()
        self.cancellableMessageBox.exec_ ()


    def forecast2 (self, index, future, length):
        ## index : the time series id from the dropdown
        ## future : the position/location of last trained value in the graph
        if index not in self.analysisPlot.validity:
             self.analysisPlot.makeExtendedTimeseries (index)
    
        _targetTimeseriesLatest = self.analysisPlot.originals [index] [future - 1] ## This is the last trained value the application is taking for forecast 
        
        #for _futureStep in range (length):
        for _futureStep in range (future, length):
            _sigmaY = 0
    
            for _subFutureStep in range (_futureStep, length):
                _sigmaY += self.root.deltaY [index] [_subFutureStep - future]            
            
            _yt = _sigmaY + _targetTimeseriesLatest

            _yt = self.root.deltaY [index] [_futureStep - future] 
                       
            self.analysisPlot.predictions [index] [_futureStep] = _yt ##### _yt is the value which will be plot in the extended graph of NPS Score
            
            if not self.analysisPlot.stata [index] [_futureStep]:
                self.analysisPlot.originals [index] [_futureStep] = _yt  ##### _yt is the value which will be plot in the extended graph of NPS Score
                
        
        self.refreshDisplay ()

    
    def forecast1 (self, index, future, length):
        
        self.root.deltaY = dict ()
        actualFuture = future
        _predictorsN = dict()
        _testN = dict()
        _newPredicatedVal = dict()

        _predictN = self.analysisPlot.originals [index]
        _countPredictors = 0
        
        
        _lenTarget = len(_predictN)
        
        _deltaY = []
        self.root.deltaY [index] = []
        i = 0
        k = 0
        for _futureStep in range (future,length, 1): # change future,length to future,future
            k += 1
            i += 1
            _sigmaX = 0
    
            try:
                for _sourceIndex in self.root.forecastingSources:
                    
                    if _sourceIndex not in self.analysisPlot.validity:
                        self.analysisPlot.makeExtendedTimeseries (_sourceIndex)
                    
                    _sourceSeries = self.analysisPlot.originals [_sourceIndex]
                    _series = self.root.tss.getseries
                    _seriesElement = _series (_sourceIndex)
                    values = _seriesElement.getAllValues()
                    times = _seriesElement.getAllTimes()

                    values_list = []
                    for i in range(len(times)):
                        if values[i] <> None:
                            values_list.append(values[i])
                            

                  #  _lenSource = len(times)

                  #  print ' length source ' + str(_lenSource) + 'target' + str(_lenTarget)

                  #  if (_lenSource == _lenTarget):
                  #      _countPredictors += 1
                  #      print ' length source ' + str(_lenSource) + 'target' + str(_lenTarget)
                        
                    _predictorsN['x'+ str(_sourceIndex)] = _sourceSeries[0:future] # training
                    _testN['x'+ str(_sourceIndex)] = _sourceSeries[future:length]  # test

                    
                    _sourceTimeseriesLatest = _sourceSeries [future - 1]
                    _deltaX = _sourceSeries [_futureStep] - _sourceTimeseriesLatest
                    _row = self.root.cm.coeffs [index]
                    _coefficient = 0 if self.root.cm.sparse and _sourceIndex not in _row else _row [_sourceIndex]
                    
                    try:
                        _sigmaX += _coefficient * _deltaX / _sourceTimeseriesLatest
                    except:
                        pass # This must surely be an error?
    
                if index not in self.analysisPlot.validity:
                    self.analysisPlot.makeExtendedTimeseries (index)
                    
                _value = self.analysisPlot.originals [index] [future - 1] * _sigmaX / (i * i)
            except:
                _value = 0
    
             # Random Forest predictor
            
            r('rm(model)')
            r('rm(df)')
            r.library("randomForest")
            #print _predictN[0:future]
            _predictorsN['Y'] = _predictN[0:future] # predicted variable
            newPredictedList = _predictorsN['Y']
            r.assign('df',_predictorsN)
            rpy.set_default_mode(rpy.NO_CONVERSION)
            r.set_seed(4543)
            model = r.randomForest(r("df$Y ~ ."), data = r("df"), ntree = 500)
            predicted = rpy.r.predict(model, _testN)          
            rpy.set_default_mode(rpy.BASIC_CONVERSION)
            rsq = mean(model[4]["rsq"]) # getting rsq
            predicted_vals = predicted.as_py()
            
            """ Tracking the first predicted value beacause this value will not be predicted again for the next loop as future increased by 1. """
            lstModifed=predicted_vals['1']
            

            """ Inserting the first predicted value in the _predictN list that next time to predict a forcast should take this into
            consideration."""
            _predictN[future]=lstModifed

            """Creating the dictionary with the latest predicted value and this will be ploted in the NPS forecast graph."""
            _newPredicatedVal[k] = lstModifed
            
            
##            for i in range(1,(length-future + 1)):
##                _deltaY.append(predicted_vals[str(i)])

          #  print future
          #  print predicted_vals
            
            

            if rsq < 0:
                rsq = 0
            else:
                rsq = rsq * 100

            rsq_print = round(rsq,2)
            
            if actualFuture == future and self.analysisPlot.showWarn==2:
                self.displayCancellableMessageBox (' Forecasting Confidence ', 'Prediction Accuracy:  ' + str(rsq_print) + '%')
                
            #for i in range(1,(length-future + 1)):
            ##    print length, future
            ##    x = float(pow(float(i)/float(12),4))
            ##    decay = exp(-1*x)
            ##    _deltaY.append(predicted_vals[str(i)]*decay)
                
            ##print _deltaY    
            
            future = future + 1
            
            #for i in range(1,len(predicted_vals)+1):
                
                #x = float(pow(float(i)/float(12),4))
                #decay = exp(-1*x)
                #_deltaY.append(predicted_vals[str(i)]*decay)
            
            #self.root.deltaY [index] = _deltaY
            
        #print _newPredicatedVal
        for j in range(1,len(_newPredicatedVal)+1):
            x = float(pow(float(j)/float(12),4))
            decay = exp(-1*x)
            _deltaY.append(_newPredicatedVal[j]*decay)

        self.root.deltaY [index] = _deltaY
        #print _deltaY
    def bucketise (self, series, targetFuture, length, numberOfBuckets):
        _bucketedData = []
        _min = 1e99
        _max = -1e99

        for _value in series [:length]:
            if _value != None:
                _max = max (_max, _value)
                _min = min (_min, _value)

        _bucketSize = (_max - _min) / numberOfBuckets
        #print _min, _max, _bucketSize, int ((_min - _min) / _bucketSize), '...', int ((_max - _min) / _bucketSize)
        #print series [:length]

        for i, _value in enumerate (series [:length]):
            if _value == None:
                _bucketedData.append (None)
            else:
                try:
                    if i >= targetFuture:
                        _bucketedData.append ((_value - _min) / _bucketSize)
                    else:
                        _bucketedData.append (int ((_value - _min) / _bucketSize))
                except:
                    _bucketedData.append (_value)

        return _bucketSize, _min, _bucketedData
##    def forecast (self):
##        NUMBER_OF_BUCKETS = 20
##        _outputFilename = os.path.expanduser ('~/.bcOutput.txt')
##        _csvFilename = os.path.expanduser ('~/.bcForecasting.csv')
##
##        for index in self.root.forecastingTargetSourceRelationships.keys ():
##            # Determine the extent of the future
##            _targetFuture, _targetLength = tools.findEnd (False, self.analysisPlot.stata [index])
##            _futurePeriods = self.root.futureSpinBox.value ()
##            #print 'TARGET: future =', _targetFuture, ', periods =', _futurePeriods, ', Length =', _targetLength
##
##            for _futurePeriod in range (_futurePeriods):
##                _future = _futurePeriod + 1
##                _length = _targetFuture + 1
##                #print 'Forecast: future =', _future, ', length =', _length
##
##                # Make the forecasting.csv file
##                _allBucketedData = []
##
##                for _source in self.root.forecastingSources:
##                    #_future, _length = tools.findEnd (False, self.analysisPlot.stata [_source])
##                    _dummy, _dummy, _bucketised = self.bucketise (self.analysisPlot.originals [_source], _targetFuture, _targetFuture + _futurePeriod + 1, NUMBER_OF_BUCKETS)
##                    _allBucketedData.append (_bucketised)
##
##                    #print 'S: (%d)' % _length,
##                
##                    #for v in self.analysisPlot.originals [_source] [:_length]:
##                    #    try:
##                    #        print '%.1f ' % (v),
##                    #    except:
##                    #       print v,
##                
##                    #print
##                    #print 'B:', _bucketised
##
##                #_future, _length = tools.findEnd (False, self.analysisPlot.stata [index])
##                #_future += self.root.futureSpinBox.value () - 1
##                #print 'Target length =', _targetLength, ', Future periods =', _futurePeriods
##                _bucketSize, _bucketMin, _bucketised = self.bucketise (self.analysisPlot.originals [index], _targetFuture, _targetFuture + _futurePeriod, NUMBER_OF_BUCKETS)
##                _bucketised.append (0)
##                _allBucketedData.append (_bucketised)
##
##                #print 'T: (%d)' % _future,
##            
##                #for v in self.analysisPlot.originals [index]:
##                #    print '%.1f ' % (v),
##            
##                #print
##                #print 'B:', _bucketised
##
##                #print 'Bucket data:', _allBucketedData
##
##                _csvFile = open (_csvFilename, 'w')
##
##                for _source in self.root.forecastingSources:
##                    _csvFile.write ('"Name%d",' % (_source))
##
##                _csvFile.write ('"TARGET"\n')
##
##                for i in range (_targetFuture + _futurePeriod + 1):
##                    for _sIndex, s in enumerate (_allBucketedData [:-1]):
##                        try:
##                            _csvFile.write ('%d,' % (s [i]))
##                        except:
##                            _csvFile.write ('None,')
##
##                    if (i != _targetFuture + _futurePeriod) or (_sIndex != len (_allBucketedData [:-1]) - 1):
##                        if _allBucketedData [-1] [i] == None:
##                            _csvFile.write ('None')
##                        else:
##                            if (i >= _targetFuture) and (_sIndex == len (_allBucketedData [:-1]) - 1):
##                                _csvFile.write ('%f\n' % (_allBucketedData [-1] [i]))
##                            else:
##                                _csvFile.write ('%d\n' % (_allBucketedData [-1] [i]))
##
##                _csvFile.write ('\n')
##                _csvFile.close ()
##                #print '-' * 80
##                #_data =  _csvFile.readlines ()
##
##                #for t in _data:
##                #    print t,
##
##                #print '#' * 80
##
##                # Call the R forecasting script
##                _outputFile = open (_outputFilename, 'w')
##                _errorFile = open (os.path.expanduser ('~/.bcErrorOutput'), 'w')
##                _bucketisationFile = os.path.expanduser ('~/.bcPredictor')
##                _result = subprocess.call (['Rscript', _bucketisationFile, _csvFilename, '%d' % (_futurePeriods)], stdout = _outputFile, stderr = _errorFile)
##                #_result = subprocess.call (['Rscript', _bucketisationFile, '/home/andy/SPECIAL.csv', '%d' % (_futurePeriods)], stdout = _outputFile, stderr = _errorFile)
##                _errorFile.close ()
##                _outputFile.close ()
##                _outputFile = open (_outputFilename)
##                _outputFile.readline ()
##
##                try:
##                    _result = _outputFile.readline ()
##                    _prediction = float (_result)
##                    _prediction = _bucketMin + _prediction * _bucketSize
##                except:
##                    print 'Bad forecast:', _result,
##                    _prediction = None
##
##                # Plot the results
##                #print _targetLength, _futurePeriod, self.analysisPlot.originals [index]
##                try:
##                    self.analysisPlot.originals [index] [_targetFuture + _futurePeriod] = _prediction
##                except:
##                    pass
##                #print 'Prediction: %.1f, (%d)' % (_prediction, _targetFuture + _futurePeriod)
    
    def forecast (self,future=''):
        
        _future = future
        _futurePeriods = self.root.futureSpinBox.value ()
        
        for index in self.root.forecastingTargetSourceRelationships.keys ():
            
            if _future!= '':
                _future = int(future)
            else:
                _future, _length = tools.findEnd (False, self.analysisPlot.stata [index])     
            #### Bug fixed for extended plot movement
            _length = self.analysisPlot.originalTimesteps + _futurePeriods
            #print "forecasting: %f, %d " % (_future, self.analysisPlot.originals [self.index] [_future])
 
           
            self.forecast1 (index, _future, _length)
            self.forecast2 (index, _future, _length)

            
    
    #        # Historic predictions
    #        #for _newFuture in range (1, _future - 1):
    #        #    self.forecast1 (index, _newFuture, _newFuture + 1)
    #        #    self.forecast2 (index, _newFuture, _newFuture + 1)

class XAxis (QtGui.QWidget):
    def __init__ (self, root, analysisPlot):
        QtGui.QWidget.__init__ (self)

        self.root = root
        self.analysisPlot = analysisPlot

        _layout = QtGui.QHBoxLayout ()
        self.setLayout (_layout)
        _layout.addStretch ()
        self.view = QtGui.QGraphicsView ()
        _layout.addWidget (self.view)

        self.scene = QtGui.QGraphicsScene ()
        self.view.setScene (self.scene)
        self.view.setHorizontalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setRenderHints (QtGui.QPainter.Antialiasing)
        self.view.setEnabled (False)
        self.view.setStyleSheet ("background: transparent; border: transparent")
    def resizeEvent (self, event):
        self.scene.clear ()
        self.view.setFixedSize (self.analysisPlot.viewportWidth, 70)
        self.numberOfLabelsToDisplay = max (1, int (self.analysisPlot.viewportWidth / 30))

        _visibleLabels = self.analysisPlot.viewportWidth / 30
        _rect = QtCore.QRect (self.analysisPlot.extendedTimesteps - self.analysisPlot.offset - self.analysisPlot.samples, 0, self.analysisPlot.samples, 10)
        _r = QtGui.QGraphicsRectItem (_rect)
        _r.setPen (self.analysisPlot.transparent)
        #_r.setPen (QtGui.QColor ('green'))
        self.scene.addItem (_r)
        self.view.fitInView (_r)
        _periodicity = max (self.analysisPlot.samples / self.numberOfLabelsToDisplay, 1)
        _p = self.view.mapToScene (11, 11) - self.view.mapToScene (0, 0)

        for x, labelText in enumerate (self.analysisPlot.timePoints):
            if (x % _periodicity) == 0:
                _labelItem = QtGui.QGraphicsTextItem (labelText)
                self.scene.addItem (_labelItem)
                _labelItem.setFont (QtGui.QFont ('courier', 8))
                _labelItem.setPos (x + _p.x (), 0)
                _labelItem.setRotation (90)
                _labelItem.setFlag (QtGui.QGraphicsItem.ItemIgnoresTransformations)

class AnalysisPlot (QtGui.QScrollArea):
    def __init__ (self, root):
        QtGui.QScrollArea.__init__ (self)
        self.root = root
        self.YFACTOR = -10.0
        self.offset = 0
        self.samples = 12
        self.pixelHeight = 150
        self.setWidgetResizable (True)
        self.view = AnalysisView (root, self)
        
        self.ruleMatches = '0'
        self.movingPoint = False
        self.viewportWidth = 20
        
        #self.setHorizontalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)

        self.originalColor = QtGui.QColor ('blue')
        self.extendedColor = QtGui.QColor ('red')
        self.transparent = QtGui.QColor (0, 0, 0, 0)
        self.axisColor = QtGui.QColor ('black')
        self.listLayout = tools.ForecastSplitter ()
        self.widget = self.listLayout
        self.setWidget (self.widget)
        self.setWidgetResizable (True)

        # Create a list of extended original timeseries
        self.originals = dict ()
        self.predictions = dict ()
        self.validity = dict ()
        self.numberOfTimeseries = 0
        self.timePoints = []
        self.originalTimesteps = 0
        self.extendedTimesteps = 0
        self.showWarn = 0

        if self.root.db:
            self.reset ()

            # We always have at least one graph
            self.addSomeTargetGraph ()
    def presetForecast (self, index):
       # print "amar12345"
        self.reset ()
        self.addTargetSeries (index)
        self.root.mainPanel.setCurrentIndex (1) # Display Forecasting tab

        
    def addSomeTargetGraph (self):
        self.addTargetSeries (0)
    def scrub (self, s):
        _result = ''

        for c in s:
            if ord (c) > 127:
                _result += ' '
            else:
                _result += c

        return _result
    
    def deduceInfluencers (self, index):
        _uniqueId = self.root.tss.series () [index].uniqueId ()
        _matches = []


        _visibleNodes = list (self.root.galaxy.view.visibleNodeDetails.nodeList ())

        #print _visibleNodes
        
        for _tsid, _ts in enumerate (self.root.tss.series ()):
            _forecastingInstructions = _ts.forecasting ()

            if re.search ("target[s][ ]*=[ ]*\[[^\]]*" + _uniqueId, _forecastingInstructions):
                _matches.append (_tsid)

        if len (_matches):
            print 'Source series from Amar:', _matches
            return _matches
        else:
            print 'No source series from Amar'

        # Find out the strongest influencers of this timeseries
        _influencersAndValues = self.root.cm.coeffs [index]


        # Create another array of key value pairs by flipping the negative values
        _absInfluencersAndValues = sorted(((abs(value), abs(key)) for (key,value) in _influencersAndValues.items ()), reverse = True)

        #print _absInfluencersAndValues

        
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

       # print _visibleInfluencers

        #for i in range (min (self.root.addInfluences, len (_influencersAndValues))):
        #    _influencers.append (_influencersAndValues [i] [1])

        for i in range (min (self.root.addInfluences, len (_visibleInfluencers))):
            _influencers.append (_visibleInfluencers [i])

       # print _influencers # Amar

        return _influencers
    
    def addSourceSeries (self, index = -1):
        if index == -1:
            _unusedSeries = list (self.setOfAllSeries - set (self.root.forecastingTargets) - set (self.root.forecastingSources))

            #_visibleNodes = set (self.galaxy.view.visibleNodeDetails.nodeList ())

            #print _visibleNodes

            #print set (self.root.forecastingTargets) # Amar
            #print _unusedSeries # Amar
            

            if len (_unusedSeries) > 0:
                index = _unusedSeries [0]
            else:
                return

            self.root.forecastingSourceReferences [index] = 1

        self.root.forecastingSources.append (index)
        self.root.forecastingGraphs [index] = self.addGraph (index, 'source')
        self.dump ()
        
    def removeSourceSeries (self, index):
        if index in self.root.forecastingSources:
            self.root.forecastingSources.remove (index)

            if index not in self.root.forecastingSourceReferences:
                pass
            elif self.root.forecastingSourceReferences [index] == 1:
                del self.root.forecastingSourceReferences [index]
            else:
                self.root.forecastingSourceReferences [index] -= 1

        self.removeGraph (index)
        self.dump ()
    def addTargetSeries (self, index = -1, addInfluencers = True):
        if index == -1:
            _remainingSeries = self.setOfAllSeries - set (self.root.forecastingTargets)

            if len (_remainingSeries) == 0:
                return -1
            else:
                index = list (_remainingSeries) [0]

        # Remove this series if it's already present as a source series
        if index in self.root.forecastingSources:
            self.removeSourceSeries (index)

        self.root.forecastingTargets.append (index)
        sources = self.deduceInfluencers (index)
        self.root.forecastingTargetSourceRelationships [index] = sources
         
        for source in sources:
            if source in self.root.forecastingTargets:
                if source not in self.root.forecastingSourceReferences:
                    self.root.forecastingSourceReferences [source] = 1
                else:
                    self.root.forecastingSourceReferences [source] += 1
            else:
                if addInfluencers:
                    if source not in self.root.forecastingSources:
                        self.root.forecastingSources.append (source)
                        self.root.forecastingGraphs [source] = self.addGraph (source, 'source')

                if source not in self.root.forecastingSourceReferences:
                    self.root.forecastingSourceReferences [source] = 1
                else:
                    self.root.forecastingSourceReferences [source] += 1

        self.root.forecastingGraphs [index] = self.addGraph (index, 'target')
        
        #print 'Future:', self.root.futureSpinBox.value ()
        #self.root.futureAltered (self.root.futureSpinBox.value ())
        self.dump ()
        return 0
    def dump (self):
        return
        print 'targets:', self.root.forecastingTargets
        print 'sources:', self.root.forecastingSources
        print 'sourceReferences:', self.root.forecastingSourceReferences
        print 'targetSourceRelationships:', self.root.forecastingTargetSourceRelationships
        print 'graphs:', self.root.forecastingGraphs
        print '#' * 20
    def removeTargetSeries (self, index):
        if len (self.root.forecastingTargets) == 1:
            return -1
        else:
            if index in self.root.forecastingTargetSourceRelationships:
                for source in self.root.forecastingTargetSourceRelationships [index]:
                    if source not in self.root.forecastingSourceReferences:
                        pass
                    elif self.root.forecastingSourceReferences [source] == 1:
                        del self.root.forecastingSourceReferences [source]
                    else:
                        self.root.forecastingSourceReferences [source] -= 1
 
                del self.root.forecastingTargetSourceRelationships [index]

            self.root.forecastingTargets.remove (index)
            self.removeGraph (index)

            if index in self.root.forecastingSourceReferences:
                self.root.forecastingSources.append (index)
                self.root.forecastingGraphs [index] = self.addGraph (index, 'source')

        self.dump ()
        return 0
    def removeGraph (self, index):
        if index in self.root.forecastingGraphs:
            _graph = self.root.forecastingGraphs [index]
            _graph.hide ()
            del self.root.forecastingGraphs [index]
    def changeSourceSeries (self, comboBox, oldIndex, newIndex):
        if newIndex in self.root.forecastingTargets:
            comboBox.setCurrentIndex (oldIndex)
        elif newIndex in self.root.forecastingSources:
            comboBox.setCurrentIndex (oldIndex)
        else:
            comboBox.lastIndex = newIndex
            self.root.forecastingSources.remove (oldIndex)

            if oldIndex in self.root.forecastingSourceReferences:
                if self.root.forecastingSourceReferences [oldIndex] == 1:
                    del self.root.forecastingSourceReferences [oldIndex]
                else:
                    self.root.forecastingSourceReferences [oldIndex] -= 1

            self.root.forecastingSources.append (newIndex)

            if newIndex in self.root.forecastingSourceReferences:
                self.root.forecastingSourceReferences [newIndex] += 1
            else:
                self.root.forecastingSourceReferences [newIndex] = 1

        self.dump ()
    def changeTargetSeries (self, comboBox, oldIndex, newIndex):
        # If we fail to change the selection, return the index of the old selection
        if newIndex in self.root.forecastingTargets:
            comboBox.setCurrentIndex (oldIndex)
            return -1
        else:
            if self.addTargetSeries (newIndex) == -1:
                return -1
            else:
                self.root.forecastingGraphs [newIndex].timeseriesSelectorComboBox.lastIndex = newIndex
                self.removeTargetSeries (oldIndex)
                self.root.futureAltered (self.root.futureSpinBox.value () + 1)
                self.root.futureAltered (self.root.futureSpinBox.value ())

        return 0
    def makeExtendedTimeseries (self, timeseriesId):
        #print timeseriesId
        # Get original series
        # Bug for ExtendedTime series done.
        _futurePeriods = self.root.futureSpinBox.value ()
        _series = self.makeIntoList (self.root.tss.series () [timeseriesId].getAllValues (), self.originalTimesteps + _futurePeriods)
        ### _series consists of the plot values for each forecast graph , this method is called after changing the timeseries from dropdown and will load the forecast graph
        ### correspondent to the time series id.
        self.originals [timeseriesId] = _series
        
        self.predictions [timeseriesId] = _series [:]
        
        self.stata [timeseriesId] = [True] * len (_series)
        
        # Extend it
        _ptr, _length = tools.findEnd (None, self.originals [timeseriesId])
    
        if _ptr > 0:
            _sustainValue = self.originals [timeseriesId] [_ptr - 1]
        else:
            _sustainValue = 0.0

        for _ptr in range (_ptr, _length):
            self.originals [timeseriesId] [_ptr] = _sustainValue
            self.predictions [timeseriesId] [_ptr] = _sustainValue
            self.stata [timeseriesId] [_ptr] = False
        
        self.validity [timeseriesId] = True

        
    def reset (self):
        

##      
##      for i in self.listLayout.children ():
##          #print i
##          i.hide ()
        
##      print self.listLayout.count()


        # Amar doing it the correct way.
    

        self.listLayout = tools.ForecastSplitter ()
        self.widget = self.listLayout
        self.setWidget (self.widget)
        self.setWidgetResizable (True)


        self.root.forecastingTargets = []
        self.root.forecastingSources = []
        self.root.forecastingSourceReferences = dict ()
        self.root.forecastingTargetSourceRelationships = dict ()
        self.root.forecastingGraphs = dict ()

        self.setOfAllSeries = set (range (self.root.N))
        self.numberOfTimeseries = len (self.root.tss.series ())
        self.timePoints = self.root.tss.series () [0].getAllTimes ()
        self.originalTimesteps = len (self.timePoints)
        self.timePoints = self.makeIntoList (self.root.tss.series () [0].getAllTimes (), self.originalTimesteps)
        self.originals = dict ()
        self.validity = dict ()
        self.predictions = dict ()
        self.stata = dict ()

        self.originalTimesteps = len (self.timePoints)
        self.extendedTimesteps = self.originalTimesteps


        # Add an x axis
        self.xAxis = XAxis (self.root, self)
        self.listLayout.insertWidget (0, self.xAxis)

        #self.setHorizontalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        warnings.simplefilter ('ignore', numpy.RankWarning)

        self.dump ()
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (1, 0)))
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (-1, 0)))
        
        

        
    def addGraph (self, index, type):
        
        _listItem = None

        if self.root.db:
            self.type = type
            _listItem = AnalysisPlotListItem (self.root, self, self.listLayout, self.type, index = index)


        return _listItem
    def extendTime (self, extraTimesteps, newEndOfTime):
        
        # Decode the date value of the last historic timeslice
        _lastHistoricTimestep = self.root.tss.series () [0].getAllTimes () [-1]
        _interval = self.root.tss.interval ()
        self.timePoints = self.makeIntoList (self.root.tss.series () [0].getAllTimes (), self.originalTimesteps)

        _years = int (_lastHistoricTimestep [:4])
        _months = 1
        _days = 1

        if _interval != 'yearly':
            _months = int (_lastHistoricTimestep [5:7])

        if (_interval == 'weekly') or (_interval == 'daily'):
            _days = int (_lastHistoricTimestep [8:10])

        _currentExtraTimesteps = self.extendedTimesteps - self.originalTimesteps

        if extraTimesteps == _currentExtraTimesteps:
            pass
        else:
            self.timePoints = self.makeIntoList (self.root.tss.series () [0].getAllTimes (), self.originalTimesteps)
            
            _stepsToAdd = extraTimesteps - _currentExtraTimesteps

            if _stepsToAdd >= 0:
                for _timeseriesId in range (self.numberOfTimeseries):
                    if _timeseriesId in self.validity:
                        _value = self.originals [_timeseriesId] [-1]

                        for i in range (_stepsToAdd):
                            self.originals [_timeseriesId].append (_value)
                            self.predictions [_timeseriesId].append (_value)
                            self.stata [_timeseriesId].append (False)
                                          

        for i in range (extraTimesteps):
            if _interval == 'yearly':
                _date = date (_years, _months, _days) + relativedelta (years = i + 1)
                self.timePoints.append (('%s' % _date) [:4])
            elif _interval == 'monthly':
                _date = date (_years, _months, _days) + relativedelta (months = i + 1)
                self.timePoints.append (('%s' % _date) [:7])
            elif _interval == 'weekly':
                _date = date (_years, _months, _days) + relativedelta (days = 7 * (i + 1))
                self.timePoints.append ('%s' % _date)
            elif _interval == 'daily':
                _date = date (_years, _months, _days) + relativedelta (days = i + 1)
                self.timePoints.append ('%s' % _date)

        self.extendedTimesteps = self.originalTimesteps + extraTimesteps
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (1, 0)))
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (-1, 0)))
    def extendForLagTime (self, extraTimesteps, newEndOfTime,currTimeSeriesId):
         # Decode the date value of the last historic timeslice
        _futurePeriods = self.root.futureSpinBox.value ()
        _Lagseries = self.makeIntoList (self.root.tss.series () [currTimeSeriesId].getAllValues (), self.originalTimesteps + _futurePeriods)
        _Lagoriginals= _Lagseries
        _Lagpredictions= _Lagseries [:]
        _ptr, _length = tools.findEnd (None, _Lagoriginals)
        if _ptr > 0:
            _sustainValue = _Lagoriginals [_ptr - 1]
        else:
            _sustainValue = 0.0

        for _ptr in range (_ptr, _length):
            _Lagoriginals [_ptr] = _sustainValue
            _Lagpredictions [_ptr] = _sustainValue
        _targetTimeseriesLatest = _Lagpredictions 
        
        #print _series [:]
        _valueFirst = _targetTimeseriesLatest[1]
        if extraTimesteps >=0:
            _targetTimeseriesLatest=[_valueFirst]*extraTimesteps + _targetTimeseriesLatest[:len(_targetTimeseriesLatest)-extraTimesteps]
            
        else:
            _valueLast = _targetTimeseriesLatest[-1]
            #print -extraTimesteps,':',len(_targetTimeseriesLatest)+extraTimesteps
            _targetTimeseriesLatest=_targetTimeseriesLatest[-extraTimesteps:len(_targetTimeseriesLatest)] + [_valueLast]*-extraTimesteps
            
        self.originals [currTimeSeriesId] = _targetTimeseriesLatest
        
        
        #print  _targetTimeseriesLatest
        
    def makeIntoList (self, thing, length):
        _list = []

        for i in range (length):
            _list.append (thing [i])
           
        return _list
    def exportCSV (self):
        _futurePeriods = self.root.futureSpinBox.value ()
        _outputFilename = os.path.expanduser ('~/.bcOutput.txt')
        #_csvFilename = os.path.expanduser ('~/.bcForecasting.csv')
        base_path = os.path.dirname(os.path.abspath(__file__))        
        #_csvFilename = os.path.join(base_path, "bcForecasting.csv")
        #_csvFile = open (_csvFilename, 'wb')
        #_csvFile = csv.writer(_csvFile, quoting=csv.QUOTE_ALL)
        _Header = ['Name']+self.makeIntoList (self.root.tss.series () [0].getAllTimes (), self.originalTimesteps + _futurePeriods)
        
        fileName, selectedFilter = QtGui.QFileDialog.getSaveFileName(self, "Save",base_path,"Excel (*.csv *.xls )")  
        if fileName:
            with open(fileName, "wb") as filel:
                writer = csv.writer(filel)
                writer.writerow(_Header)
                for index in self.validity:
                    _targetTimeseriesLatest = self.originals [index] 
                    _uniqueId = self.root.tss.series () [index].uniqueId ()
                    _targetTimeseriesLatest = [_uniqueId]+ _targetTimeseriesLatest
                    writer.writerow(_targetTimeseriesLatest)
               
            filel.close() 
        #xl = Dispatch('Excel.Application')
        
        #_csvFilename.replace('\\', '\\\\')
        #print _csvFilename
        #print _csvFilename
        #wb = xl.Workbooks.Open(_csvFilename)  
        #xl.Visible = True 
    def showWarning (self,val):
        print val
        self.showWarn = val  
        
    def showRecentForecast(self):
        objListItem = AnalysisPlotListItem (self.root, self, self.listLayout, self.type,index=0,trackForecastButton=1)
        objListItem.forecast()
        #self.view = QtGui.QGraphicsView ()
        #self.view.parent ().
        #self.view.forecast()
        #AnalysisPlotListItem.forecast(self)
        
         
            