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

import PySide.QtCore as QtCore
import PySide.QtGui as QtGui

class DummyAnalysisSlider ():
    def __init__ (self):
        self.slider = QtGui.QSlider ()
    def setSpan (self, dummy1, dummy2):
        pass

class AnalysisTimeseriesTransformComboBox (QtGui.QComboBox):
    def __init__ (self, root, listItem):
        QtGui.QComboBox.__init__ (self)

        self.root = root
        self.listItem = listItem
        self.transforms = []

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_ORIGINAL:
            self.recognize ('original')

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_AVERAGE:
            self.recognize ('average')

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_TREND:
            self.recognize ('trend')

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_ELASTICITY:
            self.recognize ('elasticity')

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_RULEBASED:
            self.recognize ('rule-based')
            
        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_LAG:
            self.recognize ('lag')   

        QtCore.QObject.connect (self, QtCore.SIGNAL ('currentIndexChanged (int)'), self.selectionChanged)
    def setCurrentText (self, text):
        for i, v in enumerate (self.transforms):
            if v == text:
                self.setCurrentIndex (i)
                return
    def recognize (self, text):
        self.addItem (text)
        self.transforms.append (text)
    def selectionChanged (self, index):
        self.listItem.graph.plot ()

class AnalysisTimeseriesSelectorComboBox (QtGui.QComboBox):
    def __init__ (self, root, listItem):
        QtGui.QComboBox.__init__ (self)

        self.root = root

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_DROPONCOMBOBOX:
            self.setAcceptDrops (True)
        else:
            self.setEnabled (False)

        self.listItem = listItem
        #self.setMaximumWidth (100)
        self.labels = []

        for ts in self.root.tss.series ():
            self.labels.append (ts.label ())

        self.addItems (self.labels)
        self.setToolTip (self.labels [0])
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
    def selectionChanged (self, index):
        self.listItem.graph.timeseriesChanged ()
        self.listItem.graph.plot ()
        self.listItem.controlPanel.ruleBasedTextChanged ()

class RuleBasedTextWidget (QtGui.QTextEdit):
    def __init__ (self, root):
        QtGui.QTextEdit.__init__ (self)

        self.root = root
        self.setTextInteractionFlags (QtCore.Qt.TextEditorInteraction)
    def dropEvent (self, event):
        print 'hiiiiiiiiiiiiiiiiiiii'
        if event.mimeData ().hasFormat ('text/plain'):
            if len (event.mimeData ().text ().split (',')) == 1:
                event.acceptProposedAction ()
                self.insertPlainText ('{*' + self.root.tss.getseries (int (event.mimeData ().text ())).label () + '}')

        event.mimeData ().setText ('')
        QtGui.QTextEdit.dropEvent (self, event)
        self.listItem.graph.plot () 
class AnalysisGraphControlPanel (QtGui.QVBoxLayout):
    def __init__ (self, root, analysisPlot, pseudoList, listItem):
        QtGui.QVBoxLayout.__init__ (self)
        self.root = root
        self.analysisPlot = analysisPlot
        self.pseudoList = pseudoList
        self.listItem = listItem
        self.graph = None

        self.timeseriesTransformComboBox = AnalysisTimeseriesTransformComboBox (self.root, listItem)
        self.addWidget (self.timeseriesTransformComboBox)
        QtCore.QObject.connect (self.timeseriesTransformComboBox, QtCore.SIGNAL ('activated (int)'), self.changeGraphTypePanel)

        # Add the graph specific control panels
        self.stackedLayout = QtGui.QStackedLayout ()
        self.addLayout (self.stackedLayout)
        # original
        _originalWidget = QtGui.QWidget ()
        _originalLayout = QtGui.QVBoxLayout ()
        _originalLayout.setContentsMargins (0, 0, 0, 0)
        _originalWidget.setLayout (_originalLayout)
        self.stackedLayout.addWidget (_originalWidget)
        # average
        _averageWidget = QtGui.QWidget ()
        _averageLayout = QtGui.QVBoxLayout ()
        _averageLayout.setContentsMargins (0, 0, 0, 0)
        _averageLayout.addWidget (QtGui.QLabel ('Integration period:'))
        self.averageIntegrationPeriodWidget = QtGui.QSpinBox ()
        self.averageIntegrationPeriodWidget.setMinimum (1)
        self.averageIntegrationPeriodWidget.setValue (3)
        QtCore.QObject.connect (self.averageIntegrationPeriodWidget, QtCore.SIGNAL ('valueChanged (int)'), self.selectionChanged)
        _averageLayout.addWidget (self.averageIntegrationPeriodWidget)
        _averageLayout.addStretch ()
        _averageWidget.setLayout (_averageLayout)
        self.stackedLayout.addWidget (_averageWidget)
        # trend
        _trendWidget = QtGui.QWidget ()
        _trendLayout = QtGui.QVBoxLayout ()
        _trendLayout.addWidget (QtGui.QLabel ('Polynomial order:'))
        _trendLayout.setContentsMargins (0, 0, 0, 0)
        self.trendOrderWidget = QtGui.QSpinBox ()
        self.trendOrderWidget.setRange (1, 17)
        self.trendOrderWidget.setValue (1)
        QtCore.QObject.connect (self.trendOrderWidget, QtCore.SIGNAL ('valueChanged (int)'), self.selectionChanged)
        _trendLayout.addWidget (self.trendOrderWidget)
        _trendLayout.addStretch ()
        _trendWidget.setLayout (_trendLayout)
        self.stackedLayout.addWidget (_trendWidget)
        # elasticity
        _elasticityWidget = QtGui.QWidget ()
        _elasticityLayout = QtGui.QVBoxLayout ()
        _elasticityLayout.addWidget (QtGui.QLabel ('Integration period:'))
        _elasticityLayout.setContentsMargins (0, 0, 0, 0)
        self.elasticityIntegrationPeriodWidget = QtGui.QSpinBox ()
        self.elasticityIntegrationPeriodWidget.setMinimum (1)
        self.elasticityIntegrationPeriodWidget.setValue (1)
        _elasticityLayout.addWidget (self.elasticityIntegrationPeriodWidget)
        QtCore.QObject.connect (self.elasticityIntegrationPeriodWidget, QtCore.SIGNAL ('valueChanged (int)'), self.selectionChanged)
        _elasticityLayout.addWidget (QtGui.QLabel ('Price timeseries:'))
        self.elasticityPriceWidget = AnalysisTimeseriesSelectorComboBox (self.root, self.listItem)
        self.elasticityPriceWidget.setMaximumWidth (200)
        _elasticityLayout.addWidget (self.elasticityPriceWidget)
        _elasticityLayout.addStretch ()
        _elasticityWidget.setLayout (_elasticityLayout)
        self.stackedLayout.addWidget (_elasticityWidget)
        # rule-based
        _ruleBasedWidget = QtGui.QWidget ()
        _ruleBasedLayout = QtGui.QVBoxLayout ()
        _ruleBasedLayout.setContentsMargins (0, 0, 0, 0)
        _ruleBasedWidget.setLayout (_ruleBasedLayout)
        _ruleBasedLayout.addStretch ()
        self.stackedLayout.addWidget (_ruleBasedWidget)
        self.ruleBasedTextWidget = RuleBasedTextWidget (self.root)
        self.ruleBasedTextWidget.setSizePolicy (QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.ruleBasedTextWidget.setMaximumHeight (110)
        self.ruleBasedTextWidget.setMaximumWidth (200)
        QtCore.QObject.connect (self.ruleBasedTextWidget, QtCore.SIGNAL ('textChanged ()'), self.ruleBasedTextChanged)
        _ruleBasedLayout.addWidget (self.ruleBasedTextWidget)
        
        # Lag
        _lagWidget = QtGui.QWidget ()
        _lagLayout = QtGui.QVBoxLayout ()
        _lagLayout.setContentsMargins (0, 0, 0, 0)
        _lagLayout.addWidget (QtGui.QLabel ('Lag period:'))
        self.lagIntegrationPeriodWidget = QtGui.QSpinBox ()
        #self.lagIntegrationPeriodWidget.setMinimum (0)
        #self.lagIntegrationPeriodWidget.setValue (0)
        self.lagIntegrationPeriodWidget.setValue (0)
        self.lagIntegrationPeriodWidget.setMinimum (-20)
        QtCore.QObject.connect (self.lagIntegrationPeriodWidget, QtCore.SIGNAL ('valueChanged (int)'), self.lagAltered)
        _lagLayout.addWidget (self.lagIntegrationPeriodWidget)
        _lagLayout.addStretch ()
        _lagWidget.setLayout (_lagLayout)
        self.stackedLayout.addWidget (_lagWidget)
        
        _deleteButton = QtGui.QToolButton ()
        _deleteButton.setIcon (QtGui.QIcon (':/images/Resources/remove32x32.png'))
        _deleteButton.setToolTip ('Remove this graph')
        QtCore.QObject.connect (_deleteButton, QtCore.SIGNAL ('clicked ()'), self.removeGraph)

        if self.root.constants.facilitiesKey & self.root.constants.FACILITIES_ANALYSIS_ADDANDDELETE:
            self.addWidget (_deleteButton)
    def ruleBasedTextChanged (self):
        _matchPattern = '([{][^{}]+[}])'
        _matches = re.split (_matchPattern, self.ruleBasedTextWidget.toPlainText ())

        for _matchIndex, _match in enumerate (_matches):
            if len (_match) > 1 and _match [0:2] == '{*' and _match [-1] == '}':
                _matches [_matchIndex] = ''
                _matchText = _match [2:-1]

                for t in range (self.root.N):
                    if _matchText == self.root.tss.getseries (t).label ():
                        _matches [_matchIndex] = 'self.analysisPlot.originals [%d] [i]' % (t)
                        break
            elif len (_match) == 3 and _match == '{!}':
                _matches [_matchIndex] = 'self.analysisPlot.originals [%d]' % self.listItem.timeseriesSelectorComboBox.currentIndex ()
            elif len (_match) == 4 and _match == '{!*}':
                _matches [_matchIndex] = 'self.analysisPlot.originals [%d] [i]' % self.listItem.timeseriesSelectorComboBox.currentIndex ()
            elif len (_match) > 0 and _match [0] == '{' and _match [-1] == '}':
                _matches [_matchIndex] = ''
                _matchText = _match [1:-1]

                for t in range (self.root.N):
                    if _matchText == self.root.tss.getseries (t).label ():
                        _matches [_matchIndex] = 'self.analysisPlot.originals [%d]' % (t)
                        break

        self.analysisPlot.ruleMatches = ''.join (_matches)
        self.listItem.graph.plot ()
    def changeGraphTypePanel (self, index):
        _plotType = self.timeseriesTransformComboBox.currentText ()

        if _plotType == 'original':
            self.stackedLayout.setCurrentIndex (0)
        elif _plotType == 'average':
            self.stackedLayout.setCurrentIndex (1)
        elif _plotType == 'trend':
            self.stackedLayout.setCurrentIndex (2)
        elif _plotType == 'elasticity':
            self.stackedLayout.setCurrentIndex (3)
        elif _plotType == 'rule-based':
            self.stackedLayout.setCurrentIndex (4)
        elif _plotType == 'lag':
            self.stackedLayout.setCurrentIndex (5)    
    def removeGraph (self):
        self.listItem.hide ()
        self.analysisPlot.visibleChildren.remove (self.listItem)
    def selectionChanged (self, value):
        self.listItem.graph.timeseriesChanged ()
        self.listItem.graph.plot ()
    def lagAltered (self, value):
        
        self.futureExtent = 'TBD'

        #self.endOfTimeLabel.setText (self.futureExtent)
        self.analysisPlot.extendTime (value, self.futureExtent)    
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
    def __init__ (self, root, analysisPlot, controlPanel, labelPanel, timeseriesSelector):
        QtGui.QGraphicsView.__init__ (self)
        self.root = root
        self.analysisPlot = analysisPlot
        self.controlPanel = controlPanel
        self.labelPanel = labelPanel
        self.timeseriesSelector = timeseriesSelector

        self.setFixedHeight (self.analysisPlot.pixelHeight)
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
        self.plot ()  
    def mouseReleaseEvent (self, event):
        QtGui.QGraphicsView.mouseReleaseEvent (self, event)
        self.mousePressed = False
    def wheelEvent (self, event):
        self.analysisPlot.samples = max (8, min (self.analysisPlot.extendedTimesteps, self.analysisPlot.samples - event.delta () / 50))
        self.analysisPlot.offset = min (self.analysisPlot.offset, self.analysisPlot.extendedTimesteps - self.analysisPlot.samples)
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
        
    def timeseriesChanged (self):
        self.timeseriesId = self.timeseriesSelector.currentIndex ()
        self.plot ()
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

        try:
            for i in range (self.analysisPlot.extendedTimesteps):
                if timeseries [i] != None:
                    _max = max (_max, timeseries [i])
                    _min = min (_min, timeseries [i])

            _diff = (_max - _min)
            m = 1.0 / _diff
            c = 1.0 - _max / _diff
        except:
            _min = 0.0

            try:
                m = 1.0 / (_max - _min)
            except:
                m = 0.0

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
        _plotType = self.controlPanel.timeseriesTransformComboBox.currentText ()
        self.segments = []

        # Draw a box around the region of interest
        #_r = QtGui.QGraphicsRectItem (0, 0, self.analysisPlot.extendedTimesteps - 1, self.analysisPlot.YFACTOR)
        _rect = QtCore.QRect (self.analysisPlot.extendedTimesteps - self.analysisPlot.offset - self.analysisPlot.samples, 0, self.analysisPlot.samples, self.analysisPlot.YFACTOR)
        _r = QtGui.QGraphicsRectItem (_rect)
        _r.setPen (self.analysisPlot.transparent)
        #_r.setPen (QtGui.QColor ('green'))
        self.scene.addItem (_r)
        self.segments.append (_r)
        self.fitInView (_r)

        if _plotType == 'original':
            _timeseries = self.analysisPlot.originals [self.timeseriesId]
        elif _plotType == 'rule-based':
            _timeseries = []
            samples = self.analysisPlot.extendedTimesteps
            seriesCount = self.root.N
            fft = self.fft # Make this function accessible to the user

            for i, original in enumerate (self.analysisPlot.originals [self.timeseriesId]):
                try:
                    _timeseries.append (eval (self.analysisPlot.ruleMatches)),
                except:
                    _timeseries.append (0)
        elif _plotType == 'average':
            _timeseries = []
            _integrationPeriod = self.controlPanel.averageIntegrationPeriodWidget.value ()

            for i in range (self.analysisPlot.extendedTimesteps):
                _samples = 0
                _sum = 0.0

                for j in range (_integrationPeriod):
                    if (i - j) >= 0:
                        _samples += 1

                        try:
                            _sum += self.analysisPlot.originals [self.timeseriesId] [i - j]
                        except:
                            _sum = None
                            break
                
                try:
                    _timeseries.append (_sum / _samples)
                except:
                    _timeseries.append (_sum)
        elif _plotType == 'trend':
            _timeseries = []
            _order = self.controlPanel.trendOrderWidget.value ()
            _x = []
            _y = []

            for i, v in enumerate (self.analysisPlot.originals [self.timeseriesId]):
                if v != None:
                    _x.append (i)
                    _y.append (v)

            _coeffs = numpy.polyfit (_x, _y, _order)

            for x in range (self.analysisPlot.extendedTimesteps):
                y = 0.0

                for _coeffIndex in range (_order):
                    y += _coeffs [_coeffIndex] * math.pow (x, (_order - _coeffIndex))

                _timeseries.append (y + _coeffs [-1])
        elif _plotType == 'elasticity':
            _timeseries = []
            _integrationPeriod = self.controlPanel.elasticityIntegrationPeriodWidget.value ()
            _priceSeries = self.analysisPlot.originals [self.controlPanel.elasticityPriceWidget.currentIndex ()]

            for x in range (self.analysisPlot.extendedTimesteps):
                q0 = self.analysisPlot.originals [self.timeseriesId] [x]
                p0 = _priceSeries [x]

                if x - _integrationPeriod > 0:
                    q1 = self.analysisPlot.originals [self.timeseriesId] [x - _integrationPeriod]
                    p1 = _priceSeries [x - _integrationPeriod]

                    try:
                        _timeseries.append (((q0 - q1) * (p0 + p1))/((p0 - p1) * (q0 + q1)))
                    except:
                        _timeseries.append (None)
                else:
                    _timeseries.append (None)
        elif _plotType == 'lag':
            _timeseries = []
            _integrationPeriod = self.controlPanel.lagIntegrationPeriodWidget.value () ## takes the input of changed value
                           
            _timeseries = self.analysisPlot.originals [self.timeseriesId]
            
        # Get some scaling statistics
        self.minimum, self.maximum, m, c = self.scalingStats (_timeseries)
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

        # Draw the x axis if it's in view
        if (self.maximum * self.minimum) < 0.0:
            _x = QtGui.QGraphicsLineItem (0, c * self.analysisPlot.YFACTOR, self.analysisPlot.extendedTimesteps - 1, c * self.analysisPlot.YFACTOR)
            _x.setPen (self.analysisPlot.axisColor)
            self.scene.addItem (_x)
            self.segments.append (_x)

        for x, y in enumerate (_timeseries [:self.analysisPlot.extendedTimesteps - 1]):
            x1 = x + 1
            y1 = 0

            try:
                y0 = (m * y + c) * self.analysisPlot.YFACTOR
                y1 = (m * _timeseries [x + 1] + c) * self.analysisPlot.YFACTOR
                _segment = QtCore.QLineF (x, y0, x1, y1)

                if x >= (self.analysisPlot.originalTimesteps - 1):
                    _graphic = QtGui.QGraphicsLineItem (_segment)
                    _graphic.setPen (self.analysisPlot.extendedColor)

                    if _plotType == 'original':
                        _pointGraphic = PointGraphic (self.analysisPlot, self.scene, self, _segment, self.timeseriesId, x1)
                else:
                    _graphic = QtGui.QGraphicsLineItem (_segment)
                    _graphic.setPen (self.analysisPlot.originalColor)
            except:
                _segment = QtCore.QLineF (x - self.analysisPlot.offset, 0, x1 - self.analysisPlot.offset, self.analysisPlot.YFACTOR)
                _graphic = QtGui.QGraphicsLineItem (_segment)
                _graphic.setPen (self.analysisPlot.transparent)
                

            self.segments.append (_graphic)
            _graphic.setZValue (1)
            self.scene.addItem (_graphic)

        # Add some points for tooltips
        if _plotType == 'original':
            _p = self.mapToScene (7, 7) - self.mapToScene (0, 0)
        else:
            _p = self.mapToScene (3, 3) - self.mapToScene (0, 0)

        for x, y in enumerate (_timeseries [:self.analysisPlot.extendedTimesteps]):
            try:
                y0 = (m * y + c) * self.analysisPlot.YFACTOR
                _graphic = QtGui.QGraphicsRectItem ()
                _graphic.setRect (QtCore.QRectF (x - _p.x () / 2.0, y0 - _p.y () / 2.0, _p.x (), _p.y ()))

                if _plotType == 'original':
                    _graphic.setBrush (self.analysisPlot.transparent)
                else:
                    _graphic.setBrush (QtGui.QColor ('black'))

                _graphic.setPen (QtGui.QColor ('black'))
                self.scene.addItem (_graphic)
                _graphic.setToolTip ('(%s, %.2f)' % (self.analysisPlot.timePoints [x], _timeseries [x]))
                self.segments.append (_graphic)
            except:
                pass

class PointGraphic (QtGui.QGraphicsRectItem):
    def __init__ (self, analysisPlot, scene, view, segment, timeseriesId, index):
        QtGui.QGraphicsRectItem.__init__ (self)

        self.analysisPlot = analysisPlot
        self.scene = scene
        self.view = view
        self.segment = segment
        self.index = index
        self.timeseriesId = timeseriesId
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
    def hoverEnterEvent (self, event):
        self.oldColor = self.brush ()
        self.setBrush (QtGui.QColor ('green'))
        QtGui.QGraphicsRectItem.hoverEnterEvent (self, event)
    def hoverLeaveEvent (self, event):
        self.setBrush (self.oldColor)
        QtGui.QGraphicsRectItem.hoverLeaveEvent (self, event)
    def mousePressEvent (self, event):
        self.mousePressed = True
        self.mouseDownPosition = event.pos ()
        self.originalY = self.analysisPlot.originals [self.timeseriesId] [int (self.x2)]
        self.x1 = self.segment.x1 ()
        self.y1 = self.segment.y1 ()
        self.x2 = self.segment.x2 ()
        self.y2 = self.segment.y2 ()
        self.analysisPlot.movingPoint = True
        #QtGui.QGraphicsRectItem.mousePressEvent (self, event)
        #event.accept ()
    def mouseMoveEvent (self, event):
        if self.mousePressed:
            self.y2 = (event.pos ().y () / self.analysisPlot.YFACTOR) * self.yRange + self.view.minimum
            self.analysisPlot.originals [self.timeseriesId] [int (self.x2)] = self.y2
            self.setRect (QtCore.QRectF (self.x2 - self.width / 2.0, event.pos ().y () - self.height / 2.0, self.width, self.height))

        #QtGui.QGraphicsRectItem.mouseMoveEvent (self, event)
    def mouseReleaseEvent (self, event):
        self.analysisPlot.movingPoint = False
        self.mousePressed = False
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (1, 0)))
        self.analysisPlot.resize (QtCore.QSize (self.analysisPlot.size () + QtCore.QSize (-1, 0)))
        #QtGui.QGraphicsRectItem.mouseReleaseEvent (self, event)
        #event.accept ()

class AnalysisGraphLabelPanel (QtGui.QVBoxLayout):
    def __init__ (self, root):
        QtGui.QVBoxLayout.__init__ (self)
        _dummy = QtGui.QComboBox ()
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
    def __init__ (self, root, analysisPlot, listLayout):
        QtGui.QWidget.__init__ (self)
        self.root = root
        self.setParent (analysisPlot)
        self.analysisPlot = analysisPlot
        self.listLayout = listLayout

        self.hboxLayout = QtGui.QHBoxLayout ()
        self.setLayout (self.hboxLayout)
        self.controlPanel = AnalysisGraphControlPanel (self.root, self.analysisPlot, self.listLayout, self)
        
        self.hboxLayout.addLayout (self.controlPanel)
        self.labelPanel = AnalysisGraphLabelPanel (self.root)
        self.hboxLayout.addLayout (self.labelPanel)
        self.graphLayout = QtGui.QVBoxLayout ()
        self.timeseriesSelectorComboBox = AnalysisTimeseriesSelectorComboBox (self.root, self)
        self.graphLayout.addWidget (self.timeseriesSelectorComboBox)
        self.graph = AnalysisGraph (self.root, self.analysisPlot, self.controlPanel, self.labelPanel, self.timeseriesSelectorComboBox)
        self.controlPanel.graph = self.graph
        self.graphLayout.addWidget (self.graph)
        self.hboxLayout.addLayout (self.graphLayout)

        if self.listLayout.parent:
            self.listLayout.insertWidget (len (self.listLayout.parent ().children ()) - 1, self)
        else:
            self.listLayout.addWidget (self)

        self.hboxLayout.setStretchFactor (self.controlPanel, 0)
        self.hboxLayout.setStretchFactor (self.labelPanel, 0)
        self.hboxLayout.setStretchFactor (self.graphLayout, 1000)
        self.graph.plot ()

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

        #self.view.setFixedHeight (60)
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

        _visibleLabels = self.analysisPlot.viewportWidth / 30
        _rect = QtCore.QRect (self.analysisPlot.extendedTimesteps - self.analysisPlot.offset - self.analysisPlot.samples, 0, self.analysisPlot.samples, 0.5)
        _r = QtGui.QGraphicsRectItem (_rect)
        _r.setPen (self.analysisPlot.transparent)
        #_r.setPen (QtGui.QColor ('green'))
        self.scene.addItem (_r)
        self.view.fitInView (_r)
        _periodicity = self.analysisPlot.samples / 8
        _p = self.view.mapToScene (11, 11) - self.view.mapToScene (0, 0)

        for x, labelText in enumerate (self.analysisPlot.timePoints):
            if (x % _periodicity) == 0:
                _labelItem = QtGui.QGraphicsTextItem (labelText)
                self.scene.addItem (_labelItem)
                _labelItem.setFont (QtGui.QFont ('courier', 8))
                _labelItem.setPos (x + _p.x (), 0)
                _labelItem.setRotation (90)
                _labelItem.setFlag (QtGui.QGraphicsItem.ItemIgnoresTransformations)

class LagPlot (QtGui.QScrollArea):
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

        self.originalColor = QtGui.QColor ('blue')
        self.extendedColor = QtGui.QColor ('red')
        self.transparent = QtGui.QColor (0, 0, 0, 0)
        self.axisColor = QtGui.QColor ('black')
        self.widget = QtGui.QWidget ()
        self.setWidget (self.widget)
        self.listLayout = QtGui.QVBoxLayout ()
        self.listLayout.addStretch (1000)

        # Add an x axis
        self.xAxis = XAxis (self.root, self)
        self.listLayout.insertWidget (0, self.xAxis)

        self.setHorizontalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        self.widget.setLayout (self.listLayout)
        warnings.simplefilter ('ignore', numpy.RankWarning)
        self.visibleChildren = []
        self.endOfTime = None
        self.endOfExtendedTime = None

        # Create a list of extended original timeseries
        self.originals = []
        self.numberOfTimeseries = 0
        self.timePoints = []
        self.originalTimesteps = 0
        self.extendedTimesteps = 0

        if self.root.db:
            self.reset ()
    def reset (self):
        self.numberOfTimeseries = len (self.root.tss.series ())
        self.timePoints = self.root.tss.series () [0].getAllTimes ()
        self.originalTimesteps = len (self.timePoints)
        self.timePoints = self.makeIntoList (self.root.tss.series () [0].getAllTimes (), self.originalTimesteps)
        self.originals = []

        for _timeseriesId in range (self.numberOfTimeseries):
            self.originals.append (self.makeIntoList (self.root.tss.series () [_timeseriesId].getAllValues (), self.originalTimesteps))

        self.originalTimesteps = len (self.timePoints)
        self.extendedTimesteps = self.originalTimesteps
        self.endOfOriginalTime = self.timePoints [-1]
        self.endOfExtendedTime = self.endOfOriginalTime
        self.visibleChildren = []

        self.resize (QtCore.QSize (self.size () + QtCore.QSize (1, 0)))
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (-1, 0)))
    def clear (self):
        for _child in self.visibleChildren:
            _child.hide ()

        self.reset ()
    def addGraph (self):
        if self.root.db:
            _listItem = AnalysisPlotListItem (self.root, self, self.listLayout)
            self.visibleChildren.append (_listItem)

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
        elif (_currentExtraTimesteps + extraTimesteps) < 0:
            self.timePoints = self.makeIntoList (self.root.tss.series () [0].getAllTimes (), self.originalTimesteps)
        elif extraTimesteps > _currentExtraTimesteps:
            _stepsToAdd = extraTimesteps - _currentExtraTimesteps

            for _timeseriesId in range (self.numberOfTimeseries):
                _value = self.originals [_timeseriesId] [-1]

                for i in range (_stepsToAdd):
                    self.originals [_timeseriesId].append (_value)

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
        else:
            for _timeseriesId in range (self.numberOfTimeseries):
                self.originals [_timeseriesId] = self.originals [_timeseriesId] [:self.extendedTimesteps - 1]

        self.extendedTimesteps = self.originalTimesteps + extraTimesteps
        self.endOfExtendedTime = newEndOfTime
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (1, 0)))
        self.resize (QtCore.QSize (self.size () + QtCore.QSize (-1, 0)))
    def makeIntoList (self, thing, length):
        _list = []

        for i in range (length):
            _list.append (thing [i])

        return _list
