#!/usr/bin/env python

import sys
import math
import os
from datetime import date
import sqlite3
import pickle
import dateutil.parser

import PySide
import PySide.QtCore as QtCore
import PySide.QtGui as QtGui
import PySide.QtWebKit as QtWebKit
import PySide.QtNetwork as QtNetwork

class ForecastSplitter (QtGui.QSplitter):
    def __init__ (self):
        QtGui.QSplitter.__init__ (self, QtCore.Qt.Vertical)
        self.setHandleWidth (1)
        self.setContentsMargins (0, 0, 0, 0)

class OverlapAxis (QtGui.QHBoxLayout):
    def __init__ (self, label):
        QtGui.QHBoxLayout.__init__ (self)
        self.setSpacing (0)
        self.part = []

        for _part in [0,1,2]:
            _item = QtGui.QLabel ('')
            _item.setAlignment (QtCore.Qt.AlignCenter)
            _item.setMaximumHeight (3)
            self.addWidget (_item)
            self.part.append (_item)
            _item.setMinimumWidth (0)
            _item.setStyleSheet ('background-color: transparent')
            self.setStretchFactor (_item, 1000)

        self.part [1].setText (label)
        self.setStretchFactor (self.part [1], 0)

class OverlapWidget (QtGui.QWidget):
    def __init__ (self, root):
        QtGui.QWidget.__init__ (self)
        self.root = root
        _vertical = QtGui.QVBoxLayout ()
        _vertical.setSpacing (1)
        _vertical.setContentsMargins (30, 3, 30, 3)
        self.setLayout (_vertical)
        self.setToolTip ('Shows the validity of the three axes (x, y, z) of this association and their overlap.\n' +
                            'A bubble can only be visible if all three axes have data at any time point.\n' +
                            'The locus is visible if the x and y axes have valid data at this time point.')

        # Add three rows for x, y and z
        self.axis = []

        for _counter in [0,1,2]:
            _axis = OverlapAxis ('')
            self.axis.append (_axis)
            _vertical.addLayout (_axis)
    def removeOldOverlaps (self):
        for _axis in [0, 1, 2]:
            self.axis [_axis].setStretchFactor (self.axis [_axis].part [0], 1000)
            self.axis [_axis].setStretchFactor (self.axis [_axis].part [1], 0)
            self.axis [_axis].setStretchFactor (self.axis [_axis].part [2], 0)
    def setTimeseries (self, seriesIds, color):
        if len (seriesIds) != 3:
            return
        else:
            for _axis, _seriesId in enumerate (seriesIds):
                _series = self.root.tss.series () [_seriesId]
                _startoff = int (_series.startoff ())
                _endoff = int (_series.endoff ())
                _extent = len (_series.getAllTimes ())
                _width = self.width ()

                if _extent == 1:
                    _lhs = 0
                    _rhs = 0
                else:
                    _lhs = _startoff / (_extent - 1.0) * 1000
                    _middle = (_endoff - _startoff) / (_extent - 1.0) * 1000
                    _rhs = 1000 - (_endoff / (_extent - 1.0)) * 1000

                self.axis [_axis].setStretchFactor (self.axis [_axis].part [0], _lhs)
                self.axis [_axis].setStretchFactor (self.axis [_axis].part [1], _middle)
                self.axis [_axis].setStretchFactor (self.axis [_axis].part [2], _rhs)
                self.axis [_axis].part [1].setStyleSheet ('background-color: rgb(%d,%d,%d)' % (color.red (), color.green (), color.blue ()))

class EventLine (QtGui.QHBoxLayout):
    def __init__ (self, root, label, parent = None):
        QtGui.QHBoxLayout.__init__ (self)
        self.root = root
        self.setSpacing (0)
        self.part = []

        for _part in [0,1,2]:
            _item = QtGui.QLabel ('', parent)
            _item.setParent (parent)
            _item.setAlignment (QtCore.Qt.AlignCenter)
            _item.setMaximumHeight (8)
            _item.setMinimumWidth (0)
            _item.setStyleSheet ('background-color: transparent')
            _item.setFont (QtGui.QFont ('lucida', self.root.ancestor.constants.eventFontSize))
            _item.setIndent (2)

            if _part == 0:
                _item.setAlignment (QtCore.Qt.AlignRight)
            elif _part == 1:
                _item.setText (label)
                self.setStretchFactor (_item, 0)
            elif _part == 2:
                _item.setAlignment (QtCore.Qt.AlignLeft)

            self.addWidget (_item)
            self.part.append (_item)
    def shrinkToNothing (self):
        for _part in [0,1,2]:
            self.part [_part].setMaximumHeight (0)

class EventsWidget (QtGui.QWidget):
    def __init__ (self, root):
        QtGui.QWidget.__init__ (self)
        self.root = root
        self.setToolTip ('Shows the state of all events that are effective during the timeline of this database.')
        self.vertical = QtGui.QVBoxLayout ()
        self.vertical.setSpacing (1)
        self.vertical.setContentsMargins (33, 3, 33, 3)
        #self.vertical.setContentsMargins (0, 3, 0, 0)
        self.setLayout (self.vertical)
    def removeOldEventLines (self):
        _child = self.vertical.takeAt (0)

        while _child:
            _child.shrinkToNothing ()
            _grandchild = _child.takeAt (0)

            while _grandchild:
                _child.removeItem (_grandchild)
                del _grandchild
                _grandchild = _child.takeAt (0)

            #ANDY 2011-10-09 THIS FAILS ON NETBOOK !!! self.vertical.removeItem (_child)
            _child.deleteLater ()
            _child = self.vertical.takeAt (0)
    def setup (self, color):
        #Delete all previous event lines
        self.removeOldEventLines ()

        self.color = color
        self.minimum = dateutil.parser.parse (self.root.ancestor.tss.series () [0].getAllTimes () [0])
        self.maximum = dateutil.parser.parse (self.root.ancestor.tss.series () [0].getAllTimes () [-1])
        self.viewDuration = self.maximum - self.minimum

        # Add rows for valid events
        self.validEvents = self.root.getValidEvents ()
        self.eventLine = []

        for _eventIndex in self.validEvents:
            _eventLine = EventLine (self.root, '', self)
            self.eventLine.append (_eventLine)
            self.vertical.addLayout (_eventLine)
    def showEvents (self):
        _events = self.root.ancestor.events

        for _eventIndex, _validEvent in enumerate (self.validEvents):
            _start = _events [_validEvent] [1]
            _finish = _events [_validEvent] [2]
            _lhsDays = (_start - self.minimum).days
            _rhsDays = (self.maximum - _finish).days
            _middleDays = (_finish - _start).days

            if _lhsDays < 0:
                _lhsDays = 0

                if _rhsDays > self.viewDuration.days:
                    _rhsDays = self.viewDuration.days
                    _middleDays = 0
                elif _rhsDays< 0:
                    _rhsDays = 0
                    _middleDays = self.viewDuration.days
                else:
                    _middleDays = self.viewDuration.days - _rhsDays
            elif _lhsDays > self.viewDuration.days:
                _lhsDays = self.viewDuration.days
                _middleDays = 0
                _rhsDays = 0
            elif _rhsDays < 0:
                _rhsDays = 0
                _middleDays = self.viewDuration.days - _lhsDays
            elif _rhsDays > self.viewDuration.days:
                _rhsDays = self.viewDuration.days
                _middleDays = 0

            _lhs = 1000.0 * float (_lhsDays) / float (self.viewDuration.days)
            _middle = 1000.0 * float (_middleDays) / float (self.viewDuration.days)
            _rhs = 1000.0 * float (_rhsDays) / float (self.viewDuration.days)

            _segments = sorted ([[_lhs, 0], [_middle, 1], [_rhs, 2]])
            #print 'Duration=%d, start=%s, finish=%s, lhs=%d, middle=%d, rhs=%d' % (self.viewDuration.days, _start, _finish, _lhs, _middle, _rhs)

            for _segment in _segments [:-1]:
                self.eventLine [_eventIndex].part [_segment [1]].setText ('')

            self.eventLine [_eventIndex].part [_segments [-1] [1]].setText (_events [_validEvent] [0])
            self.eventLine [_eventIndex].setStretchFactor (self.eventLine [_eventIndex].part [0], _lhs)
            self.eventLine [_eventIndex].setStretchFactor (self.eventLine [_eventIndex].part [1], _middle)
            self.eventLine [_eventIndex].setStretchFactor (self.eventLine [_eventIndex].part [2], _rhs)
            self.eventLine [_eventIndex].part [1].setStyleSheet ('background-color: rgb(%d,%d,%d)' % (self.color.red (), self.color.green (), self.color.blue ()))
            _numberFormat = r'%.' + '%d' % (_events [_validEvent] [5]) + 's'
            _format = _numberFormat + ' ... ' + _numberFormat
            self.eventLine [_eventIndex].part [1].setToolTip (_format % (_start, _finish))
            #print 'ToolTip set for %s' % _events [_validEvent] [0], _format % (_start, _finish)

class Endstop (QtGui.QLabel):
    def __init__ (self, parent, root, invertDelta = False):
        QtGui.QLabel.__init__ (self)
        self._parent = parent
        self.root = root
        self.invertDelta = invertDelta
        _pixmap = QtGui.QPixmap (':/images/Resources/endstop.png')
        self.setPixmap (_pixmap)
        self.endstopWidth = _pixmap.width () + self._parent.sliderAdjustment
        self.setMinimumWidth (self.endstopWidth)
        self.moving = False
    def mousePressEvent (self, event):
        if self.root.ancestor.db:
            self.moving = True
            self.pressedPos = event.globalPos ()
            self.oldWidth = self.width ()
            self.delta = 0
            self.layoutWidth = self._parent.sliderBarLayout.geometry ().width ()
            self.sliderWidth = self._parent.slider.width ()
            self.lumpiness = ((self.layoutWidth - 2.0 * self.endstopWidth) / (self._parent._steps - 1))

            if 40 > self.lumpiness:
                self._parent.slider.setMinimumWidth (40)
            else:
                self._parent.slider.setMinimumWidth (self.lumpiness)
    def mouseReleaseEvent (self, event):
        self.moving = False
    def setSlider (self, slider):
        self.slider = slider
    def setSibling (self, sibling):
        self.sibling = sibling
    def mouseMoveEvent (self, event):
        if self.moving:
            _mousePositionNow = event.globalPos ()

            if self.invertDelta:
                self.delta = (self.pressedPos - _mousePositionNow).x ()
            else:
                self.delta = (_mousePositionNow - self.pressedPos).x ()

            _siblingWidth = self.sibling.width ()
            _sliderMinimumWidth = self._parent.slider.minimumWidth ()
            _sliderWidth = self._parent.slider.width ()
            _myAnalogueNewWidth = self.oldWidth + self.delta
            _myDigitalNewWidth = self.lumpiness * int ((_myAnalogueNewWidth - self.endstopWidth) / self.lumpiness) + self.endstopWidth
            _myDigitalNewWidth = int (_myDigitalNewWidth) + 1

            if _myDigitalNewWidth > (self.layoutWidth - (_siblingWidth + _sliderMinimumWidth)):
                _myDigitalNewWidth = self.layoutWidth - (_siblingWidth + _sliderMinimumWidth)

            if (_myDigitalNewWidth - self.endstopWidth) < 0:
                _myDigitalNewWidth = self.endstopWidth

            return _myDigitalNewWidth, _siblingWidth

class LeftEndstop (Endstop):
    def __init__ (self, parent, root):
        Endstop.__init__ (self, parent, root)
        self.setAlignment (QtCore.Qt.AlignRight)
    def mouseMoveEvent (self, event):
        if self.moving:
            _myDigitalNewWidth, _siblingWidth = Endstop.mouseMoveEvent (self, event)

            _lhs = _myDigitalNewWidth
            _middle = self.layoutWidth - _myDigitalNewWidth - _siblingWidth
            _rhs = _siblingWidth

            self._parent.sliderBarLayout.setStretchFactor (self, _lhs)
            self._parent.sliderBarLayout.setStretchFactor (self.slider, _middle)
            self._parent.sliderBarLayout.setStretchFactor (self.sibling, _rhs)

            _oldStart = self._parent.startPosition
            _oldFinish = self._parent.finishPosition
            self._parent.startPosition = int (((_lhs - self.endstopWidth) * (self._parent._steps - 1.0) / (self.layoutWidth - 2.0 * self.endstopWidth)))
            self._parent.finishPosition = self._parent._steps - int (((_rhs - self.endstopWidth) * (self._parent._steps - 1.0) / (self.layoutWidth - 2.0 * self.endstopWidth))) - 1
            self._parent.slider.setRange (self._parent.startPosition, self._parent.finishPosition)
            self._parent.lower.setText (self.root.tss.series () [0].getAllTimes () [self._parent.startPosition])

            if (_oldStart != self._parent.startPosition) or (_oldFinish != self._parent.finishPosition):
                self.root.redrawAll ()

                if (self._parent.finishPosition - self._parent.startPosition) < 20:
                    self._parent.slider.setTickInterval (1)
                else:
                    self._parent.slider.setTickInterval (0)

class RightEndstop (Endstop):
    def __init__ (self, parent, root):
        Endstop.__init__ (self, parent, root, invertDelta = True)
        self.setAlignment (QtCore.Qt.AlignLeft)
    def mouseMoveEvent (self, event):
        if self.moving:
            _myDigitalNewWidth, _siblingWidth = Endstop.mouseMoveEvent (self, event)

            _lhs = _siblingWidth
            _middle = self.layoutWidth - _myDigitalNewWidth - _siblingWidth
            _rhs = _myDigitalNewWidth

            self._parent.sliderBarLayout.setStretchFactor (self.sibling, _lhs)
            self._parent.sliderBarLayout.setStretchFactor (self.slider, _middle)
            self._parent.sliderBarLayout.setStretchFactor (self, _rhs)

            self._parent.startPosition = int (((_lhs - self.endstopWidth) * (self._parent._steps - 1.0) / (self.layoutWidth - 2.0 * self.endstopWidth)))
            self._parent.finishPosition = self._parent._steps - int (((_rhs - self.endstopWidth) * (self._parent._steps - 1.0) / (self.layoutWidth - 2.0 * self.endstopWidth))) - 1
            self._parent.slider.setRange (self._parent.startPosition, self._parent.finishPosition)
            self._parent.higher.setText (self.root.tss.series () [0].getAllTimes () [self._parent.finishPosition])

            self.root.redrawAll ()

            if (self._parent.startPosition - self._parent.finishPosition) < 10:
                self._parent.slider.setTickInterval (1)
            else:
                self._parent.slider.setTickInterval (0)

class TimeSlider (QtGui.QVBoxLayout):
    def __init__ (self, root):
        QtGui.QVBoxLayout.__init__ (self)
        self.setSpacing (0)
        self.root = root
        self._steps = 0
        self.startPosition = 0
        self.finishPosition = 0
        self.sliderAdjustment = 12

        # This is the column index into the timeseries and it represents time
        self.index = 0

        # Put everything in a grid
        _grid = QtGui.QGridLayout ()
        self.addLayout (_grid)

        # Slider limit labels
        _grid.addWidget (QtGui.QLabel (''), 0, 0)
        _labelLayout = QtGui.QHBoxLayout ()
        _grid.addLayout (_labelLayout, 0, 1)
        self.lower = QtGui.QLabel ('LOW')
        _labelLayout.addWidget (self.lower)
        self.higher = QtGui.QLabel ('HIGH')
        self.higher.setAlignment (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        _labelLayout.addWidget (self.higher)

        # Slider
        _grid.addWidget (QtGui.QLabel (''), 1, 0)
        self.sliderBarLayout = QtGui.QHBoxLayout ()
        self.sliderBarLayout.setSpacing (0)
        _grid.addLayout (self.sliderBarLayout, 1, 1)

        self.leftEndstop = LeftEndstop (self, self.root)
        self.sliderBarLayout.addWidget (self.leftEndstop)

        self.slider = QtGui.QSlider (QtCore.Qt.Horizontal)
        self.slider.setTickPosition (QtGui.QSlider.TicksBelow)
        self.slider.setTracking (True)
        self.slider.setMinimumWidth (40)
        self.slider.setPageStep (1)
        self.sliderBarLayout.addWidget (self.slider)

        self.rightEndstop = RightEndstop (self, self.root)
        self.sliderBarLayout.addWidget (self.rightEndstop)

        self.leftEndstop.setSlider (self.slider)
        self.rightEndstop.setSlider (self.slider)
        self.leftEndstop.setSibling (self.rightEndstop)
        self.rightEndstop.setSibling (self.leftEndstop)

        # Add a timeseries overlap indicator
        _label = QtGui.QLabel ('Axis overlap')
        _label.setAlignment (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        _grid.addWidget (_label, 2, 0)
        self.overlapWidget = OverlapWidget (self.root)
        _grid.addWidget (self.overlapWidget, 2, 1)

        # Add a timeseries events indicator
        _label = QtGui.QLabel ('Events')
        _label.setAlignment (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        _grid.addWidget (_label, 3, 0)
        self.eventsWidget = EventsWidget (self.root)
        _grid.addWidget (self.eventsWidget, 3, 1)
        
        QtCore.QObject.connect (self.slider, QtCore.SIGNAL ('valueChanged (int)'), self.timeSliderMoved)
    def setSteps (self, steps):
        self._steps = steps
        self.slider.setRange (0, steps - 1)
    def steps (self):
        return self._steps
    def updateTimeSliderCounter (self, value):
        _watermarkWidget = self.root.view.watermark
        _watermarkWidget.setText ('%s' % value)
        _fontMetrics = QtGui.QFontMetrics (_watermarkWidget.font ())
        _factor = self.root.view.boundary.rect ().width () / _fontMetrics.width (_watermarkWidget.text ())
        _watermarkWidget.setFont (QtGui.QFont ('lucida', _watermarkWidget.font ().pointSizeF () * _factor, 99))
    def configure (self, lower, upper, steps):
        self.lower.setText (lower)
        self.higher.setText (upper)
        self._steps = steps
        self.startPosition = 0
        self.finishPosition = steps - 1
        self.slider.setRange (0, steps - 1)
    def showChangedEvents (self):
        if self.index > -9999999: #0:
            _events = self.root.ancestor.events

            for _eventIndex, _validEvent in enumerate (self.eventsWidget.validEvents):
                _start = _events [_validEvent] [1]
                _finish = _events [_validEvent] [2]
                _timestamps = self.root.ancestor.tss.series () [0].getAllTimes ()

                if len (_timestamps [self.index]) == 7: # Only year and month given
                    _thisTimestamp = dateutil.parser.parse (_timestamps [self.index] + '-01')
                    #_previousTimestamp = dateutil.parser.parse (_timestamps [self.index - 1] + '-01')
                else:
                    _thisTimestamp = dateutil.parser.parse (_timestamps [self.index])
                    #_previousTimestamp = dateutil.parser.parse (_timestamps [self.index - 1])

                #if _finish > _previousTimestamp and _finish <= _thisTimestamp:
                #    print 'Finish event', _events [_validEvent] [0], _start, _finish, _thisTimestamp, _previousTimestamp
                #elif _start > _previousTimestamp and _start <= _thisTimestamp:
                #    print 'Start event', _events [_validEvent] [0], _start, _finish, _thisTimestamp, _previousTimestamp

                #print 'Event', _events [_validEvent] [0], _start, _finish, _thisTimestamp #, _previousTimestamp

                if _start <= _thisTimestamp <= _finish:
                    _color = (self.eventsWidget.color.red (), self.eventsWidget.color.green (), self.eventsWidget.color.blue ())
                    self.eventsWidget.eventLine [_eventIndex].part [1].setStyleSheet ('background-color: rgb(%d,%d,%d)' % _color)
                else:
                    self.eventsWidget.eventLine [_eventIndex].part [1].setStyleSheet ('background-color: transparent')
    def timeSliderMoved (self, step):
        try:
            self.index = step
            _time = self.root.tss.series () [0].getAllTimes () [step]
            self.updateTimeSliderCounter (_time)

            for association in self.root.associations:
                if association [2]:
                    association [1].associationChanged (association, step)

            self.eventsWidget.showEvents ()
        except:
            None

        if self.root.ancestor.db:
            self.showChangedEvents ()
    def timeIndex (self):
        return self.index
    def value (self):
        return self.slider.value ()
    def setValue (self, value):
        self.slider.setValue (value)

def findEnd (marker, timeseries):
    _future = len (timeseries) - 1

    # Find out where the end of measured data is
    while timeseries [_future] == marker and _future > 0:
        _future -= 1

    return _future + 1, len (timeseries)

def getMacAddress ():
    for interface in QtNetwork.QNetworkInterface.allInterfaces ():
        # Return only the first non-loopback MAC Address
        if not (interface.flags () & QtNetwork.QNetworkInterface.IsLoopBack):
            return interface.hardwareAddress ()

    return None

def getUsername ():
    _homePath = os.path.expanduser ('~')
    _path, _name = os.path.split (_homePath)
    return _name

def runLengthEncode (aList):
    _result = []

    try: # If it's None or not a list or dict we return None
        _listLength = len (aList)
    except:
        return _result

    if _listLength == 0:
        return _result

    _previousValue = aList [0]
    _runLength = 1
    _startPosition = 0

    for _index, _currentValue in enumerate (aList [1:]):
        if _currentValue == _previousValue:
            _runLength += 1
        else:
            _result.append ([_previousValue, _runLength])
            _runLength = 1
            _startPosition = _index + 1
            _previousValue = _currentValue

    if _runLength > 0:
        _result.append ([_previousValue, _runLength])

    if len (_result) > _listLength / 2.2:
        _result = aList

    return _result

def runLengthDecode (aRunLengthList): # [[value, runLength]]
    _result = []

    try: # If it's None or not a list or dict we return an empty list
        _listLength = len (aRunLengthList)
    except:
        return _result

    if _listLength == 0:
        return _result

    if isinstance (aRunLengthList [0], list):
        for _element in aRunLengthList:
            for _repetition in range (_element [1]):
                _result.append (_element [0])
    else:
        _result = aRunLengthList [:]

    return _result

def sequenceEncode (aList):
    _result = []

    try: # If it's None or not a list or dict we return None
        _listLength = len (aList)
    except:
        return _result

    if _listLength == 0:
        return _result

    _list = sorted (aList)
    _previousValue = _list [0]
    _runLength = 1
    _startValue = _list [0]

    for _index, _currentValue in enumerate (_list [1:]):
        if _currentValue == _previousValue + 1:
            _runLength += 1
        else:
            _result.append ([_startValue, _runLength])
            _runLength = 1
            _startValue = _list [_index + 1]

        _previousValue = _currentValue

    if _runLength > 0:
        _result.append ([_startValue, _runLength])

    if len (_result) > _listLength / 2:
        _result = _list

    return _result

def sequenceDecode (aRunLengthList): # [[value, runLength]]
    _result = []

    try: # If it's None or not a list or dict we return an empty list
        _listLength = len (aRunLengthList)
    except:
        return _result

    if _listLength == 0:
        return _result

    if isinstance (aRunLengthList [0], list):
        for _element in aRunLengthList:
            for _repetition in range (_element [1]):
                _result.append (_element [0] + _repetition)
    else:
        _result = aRunLengthList [:]

    return _result

class TimesliceFrequencySelector (QtGui.QComboBox):
    def __init__ (self, root):
        QtGui.QComboBox.__init__ (self)
        self.root = root
        QtCore.QObject.connect (self, QtCore.SIGNAL ('currentIndexChanged (int)'), self.timesliceFrequencyChanged)
    def defineChoices (self, choices):

        for i in range (self.count ()):
            self.removeItem (0)

        self.addItems (choices)
    def timesliceFrequencyChanged (self, _index):
        _frequency = self.root.timesliceFrequencySelector.currentText ()
        _choices = list ()

        for i in self.root.tssids [1:]:
            if self.root.tss.slice_index (self.root.db) [i] ['interval'] == _frequency:
                _choices.append (i)

        if len (_choices) == 0:
            _choices = list ()
            _choices.append (1)

        self.root.timesliceSelector.defineChoices (_choices)

        if len (_choices) > 1:
            _low = 0
            _high = len (_choices) - 1
            self.root.timesliceSlider.setSpan (_low, _high)
            self.root.timesliceSlider.setValue (_low)
            self.root.timesliceSlider.setEnabled (True)
            self.root.timesliceSelector.timesliceChanged (0)
        else:
            self.root.timesliceSlider.setEnabled (False)
            self.root.timesliceSelector.timesliceChanged (0)

class TimesliceSelector (QtGui.QComboBox):
    def __init__ (self, root):
        QtGui.QComboBox.__init__ (self)
        self.root = root
        QtCore.QObject.connect (self, QtCore.SIGNAL ('currentIndexChanged (int)'), self.timesliceChanged)
        self.acceptChanges = True
    def defineChoices (self, choices):
        self.acceptChanges = False

        for i in range (self.count ()):
            self.removeItem (0)

        self.acceptChanges = False
        self.root.timesliceChoices = list ()

        for _item in choices:
            _itemLabel = self.root.tss.slice_index (self.root.db) [_item] ['starttime'] + '...' + self.root.tss.slice_index (self.root.db) [_item] ['endtime']
            self.root.timesliceChoices.append (_item)
            self.addItem (_itemLabel)

        self.acceptChanges = True
    def timesliceChanged (self, index):
        if self.acceptChanges:
            self.root.timeslice = self.root.timesliceChoices [index] - 1
            self.root.timesliceSlider.setValue (index)
            self.root.refreshGraphs ()

class DockingWindow (QtGui.QDockWidget):
    def __init__ (self, title, parent, area):
        QtGui.QDockWidget.__init__ (self, title, parent)
        self.setAllowedAreas (QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setFeatures (QtGui.QDockWidget.DockWidgetMovable | QtGui.QDockWidget.DockWidgetFloatable | QtGui.QDockWidget.DockWidgetClosable)
        self.setObjectName (title)
        self.setMinimumWidth (250)
        self.setFeatures (QtGui.QDockWidget.DockWidgetClosable | QtGui.QDockWidget.DockWidgetMovable) # QtGui.QDockWidget.DockWidgetVerticalTitleBar | QtGui.QDockWidget.DockWidgetFloatable
        parent.addDockWidget (area, self)
        self.setStyleSheet ('QDockWidget::title {background: white; padding: 4px 2px 4px 2px; border: 1px solid lightgrey}')

class UndoableAction ():
    HIDE = 1
    SHOW = 2
    CENTER = 3
    def __init__ (self, action, data):
        self.action = action
        self.data = data

class UndoBuffer ():
    def __init__ (self, root):
        self.root = root
        self.reset ()
    def reset (self):
        self.undoBuffer = []
        self.redoBuffer = []
        self.root.menubar.undoItem.setEnabled (False)
        self.root.menubar.redoItem.setEnabled (False)
        self.root.menubar.undoButton.setEnabled (False)
        self.root.menubar.redoButton.setEnabled (False)
    def push (self, instruction):
        self.undoBuffer.append (instruction)
        self.redoBuffer = []
        self.root.menubar.undoItem.setEnabled (True)
        self.root.menubar.redoItem.setEnabled (False)
        self.root.menubar.undoButton.setEnabled (True)
        self.root.menubar.redoButton.setEnabled (False)
    def lenUndo (self):
        return len (self.undoBuffer)
    def lenRedo (self):
        return len (self.redoBuffer)
    def pop (self):
        if len (self.undoBuffer):
            _item = self.undoBuffer.pop ()
            self.redoBuffer.append (_item)
            self.root.menubar.redoItem.setEnabled (True)
            self.root.menubar.redoButton.setEnabled (True)

            if len (self.undoBuffer) == 0:
                self.root.menubar.undoItem.setEnabled (False)
                self.root.menubar.undoButton.setEnabled (False)

            return _item
        else:
            return None
    def redo (self):
        if len (self.redoBuffer):
            _item = self.redoBuffer.pop ()
            self.undoBuffer.append (_item)
            self.root.menubar.undoItem.setEnabled (True)
            self.root.menubar.undoButton.setEnabled (True)

            if len (self.redoBuffer) == 0:
                self.root.menubar.redoItem.setEnabled (False)
                self.root.menubar.redoButton.setEnabled (False)

            return _item
        else:
            return None
    def undoable (self):
        return self.undoBuffer
    def redoable (self):
        return self.redoBuffer

class CircleDescriptor ():
    def __init__ (self, x, y, radius):
        self._x = x
        self._y = y
        self._radius = radius
        self._graphic = None
    def setGraphic (self, graphic):
        self._graphic = graphic
    def graphic (self):
        return self._graphic
    def x (self):
        return self._x
    def y (self):
        return self._y
    def radius (self):
        return self._radius

def key (a, b):
    if a < b:
        return '%d:%d' % (a, b)
    else:
        return '%d:%d' % (b, a)

class SliderLabel (QtGui.QLabel):
    def __init__ (self, label, parent, resetValue):
        QtGui.QLabel.__init__ (self, label)

        self._parent = parent
        self.resetValue = resetValue
    def mouseDoubleClickEvent (self, event):
        self._parent.slider.setValue (self.resetValue)

class TimesliceSlider (QtGui.QFrame):
    def __init__ (self, root, low, high, initial, callback):
        QtGui.QFrame.__init__ (self)
        self.root = root
        self.setFrameShape (QtGui.QFrame.StyledPanel)
        self.setContentsMargins (1, 1, 1, 1)

        self.layout = QtGui.QHBoxLayout ()
        self.layout.setSpacing (0)
        self.layout.setContentsMargins (2, 2, 2, 2)
        self.setLayout (self.layout)

        # Slider
        self.slider = QtGui.QSlider (QtCore.Qt.Horizontal)
        self.slider.setTracking (True)
        self.slider.setMinimum (low)
        self.slider.setMaximum (high)
        self.slider.setValue (initial)
        self.slider.setPageStep (1)
        self.layout.addWidget (self.slider)

        if callback:
            QtCore.QObject.connect (self.slider, QtCore.SIGNAL ('valueChanged (int)'), self.setValue)
            QtCore.QObject.connect (self.slider, QtCore.SIGNAL ('valueChanged (int)'), callback)
    def setMinimum (self, value):
        self.slider.setMinimum (value)
    def setMaximum (self, value):
        self.slider.setMaximum (value)
    def setValue (self, value):
        self.slider.setValue (value)
    def setSpan (self, low, high):
        self.slider.setMinimum (low)
        self.slider.setMaximum (high)

class Slider (QtGui.QFrame):
    def __init__ (self, label, low, high, initial, callback, parent = None):
        QtGui.QFrame.__init__ (self)
        self.setFrameShape (QtGui.QFrame.StyledPanel)
        self.setContentsMargins (1, 1, 1, 1)

        self.layout = QtGui.QHBoxLayout ()
        self.layout.setSpacing (0)
        self.layout.setContentsMargins (12, 2, 12, 2)
        self.setLayout (self.layout)

        # Label
        self.label = SliderLabel (label, self, initial)
        self.label.setMinimumWidth (80)
        self.layout.addWidget (self.label)

        # Slider
        self.slider = QtGui.QSlider (QtCore.Qt.Horizontal)
        self.slider.setTracking (True)
        self.slider.setMinimum (low)
        self.slider.setMaximum (high)
        self.slider.setValue (initial)
        self.layout.addWidget (self.slider)

        # Value
        self.val = QtGui.QLabel ()
        self.val.setAlignment ( QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.val.setMinimumWidth (25)
        self.layout.addWidget (self.val)
        self.setSpan (low, high)
        self.setValue (initial)

        # Units
        self.units = QtGui.QLabel ('%')
        self.layout.addWidget (self.units)

        if callback:
            QtCore.QObject.connect (self.slider, QtCore.SIGNAL ('valueChanged (int)'), self.setValue)
            QtCore.QObject.connect (self.slider, QtCore.SIGNAL ('valueChanged (int)'), callback)
    def setMinimum (self, value):
        self.slider.setMinimum (value)
    def setMaximum (self, value):
        self.slider.setMaximum (value)
    def setValue (self, value):
        self.slider.setValue (value)
        self.val.setText ('%.0f' % (value / 2.55))
    def setSpan (self, low, high):
        self.slider.setMinimum (low)
        self.slider.setMaximum (high)

class HelpDialog (QtGui.QDialog):
    def __init__ (self):
        QtGui.QDialog.__init__ (self)

        _layout = QtGui.QVBoxLayout ()
        self.setLayout (_layout)
        _buttons = QtGui.QHBoxLayout ()
        _layout.addLayout (_buttons)

        self.webView = QtWebKit.QWebView ()
        _layout.addWidget (self.webView)

        _backButton = QtGui.QToolButton ()
        _backButton.setIcon (QtGui.QIcon (':/images/Resources/back.png'))
        _backButton.setToolTip ('Back to previous item')
        _buttons.addWidget (_backButton)
        QtCore.QObject.connect (_backButton, QtCore.SIGNAL ('clicked()'), self.webView.back)

        _forwardButton = QtGui.QToolButton ()
        _forwardButton.setIcon (QtGui.QIcon (':/images/Resources/forward.png'))
        _forwardButton.setToolTip ('Forward to next item')
        _buttons.addWidget (_forwardButton)
        QtCore.QObject.connect (_forwardButton, QtCore.SIGNAL ('clicked()'), self.webView.forward)

        self.searchText = QtGui.QLineEdit ()
        _buttons.addWidget (self.searchText, 1)

        _searchButton = QtGui.QToolButton ()
        _searchButton.setIcon (QtGui.QIcon (':/images/Resources/goIcon.png'))
        _searchButton.setToolTip ('Search for text')
        _buttons.addWidget (_searchButton)
        QtCore.QObject.connect (_searchButton, QtCore.SIGNAL ('clicked()'), self.searchHelpText)
    def searchHelpText (self):
        self.webView.page ().findText (self.searchText.text ())

class AboutDialog (QtGui.QMessageBox):
    def __init__ (self, app):
        QtGui.QMessageBox.__init__ (self)
        self.setWindowModality (QtCore.Qt.ApplicationModal)
        self.setMinimumWidth (700)
        self.setIcon (QtGui.QMessageBox.Information)
        now = date.today ()
        text = '<br/><b>BrandCommunities %s (%s-%s)</b><br/> <br/>' % (app.applicationVersion, app.applicationDate, app.applicationDescription)
        text += '<b>Python: </b>' + sys.version + '<br/>'
        text += '<b>PySide: </b>' + str (PySide) [8:-1] + ' : ' + PySide.__version__ + '<br/>'
        text += '<b>QtCore: </b>' + PySide.QtCore.__version__ + '<br/>'
        text += '<b>sqlite3: </b>' + sqlite3.version
        text += '<br/> <br/><b>Authors: </b>Rick Welykochy & Andy Cooper (Paradiggle)'
        self.setText (text)

# 3D transform
#   a is the point to be transformed
#   v is the point representing the camera
#   t are the angles of rotation of the camera
class Transform ():
    def __init__ (self):
        None
    def setup (self, vx, vy, vz, tx, ty, tz):
        self.sx = math.sin (tx)
        self.sy = math.sin (ty)
        self.sz = math.sin (tz)
        self.cx = math.cos (tx)
        self.cy = math.cos (ty)
        self.cz = math.cos (tz)
        self.vx = vx
        self.vy = vy
        self.vz = vz
    def transform (self, ax, ay, az):
        self.dx = ax - self.vx
        self.dy = ay - self.vy
        self.dz = az - self.vz

        self.a = self.cz * self.dy - self.sz * self.dx
        self.c = self.cz * self.dx
        self.d = self.sz * self.dy
        self.e = self.cy * self.dz
        self.b = -self.c - self.d
        self.x = self.cy * self.b - self.sy * self.dz
        self.y = self.sx * (self.sy * self.b - self.e) + self.cx * self.a
        self.z = self.cx * (self.e - self.sy * (self.d - self.c)) + self.sx * self.a
        return -self.x, self.y, self.z

def getArgv (label = None):
    if label == None:
        _present = None

        for _arg in sys.argv [1:]:
            if _arg [0:2] != '--':
                _present = _arg
                break
    else:
        _present = False

        for _arg in sys.argv:
            if _arg == '--' + label:
                _present = True
                break

    return _present

class BcFiles ():
    def __init__ (self, root, databaseFolderName = '', databaseFilename = '', stub = False):
        self.root = root

        # Define some constants
        self.DATABASE_NAME_EXTENSION = '.db'
        self.CONFIGURATION_FILENAME_EXTENSION = '.bcc'
        self.DATABASE_NAME_EXTENSION_LENGTH = len (self.DATABASE_NAME_EXTENSION)
        self.CONFIGURATION_FILENAME_EXTENSION_LENGTH = len (self.CONFIGURATION_FILENAME_EXTENSION)

        if not stub:
            if self.sanityCheck (databaseFolderName, databaseFilename):
                """A message has already been displayed so just propagate the error"""
    def emitWarning (self, title, message):
        _messageBox = QtGui.QMessageBox (QtGui.QMessageBox.Warning, title, message)
        _messageBox.show ()
        _messageBox.exec_ ()
    def sanityCheck (self, databaseFolderName, databaseFilename):
        self.databaseFolderName = databaseFolderName
        self.databaseFilename = databaseFilename

        # Reject if database folder name a zero length name
        if len (self.databaseFolderName) < 1:
            self.emitWarning ('Database folder is not given', 'Database folder "%s" not found.' % (self.databaseFolderName))
            return True

        # Reject if database filename has a zero length name
        if len (self.databaseFilename) < 1:
            emitWarning ('Database name is not given', 'Database "%s" not found.' % (self.databaseFilename))
            return True

        # Reject of the database filename contains slashes
        if ('/' in self.databaseFilename) or ('\\' in self.databaseFilename):
            self.emitWarning ('Slashes not allowed in the database name', 'Database "%s" contains slash or backslach characters.' % (self.databaseFilename))
            return True

        # Reject if the database folder does not exist
        if not os.path.isdir (self.databaseFolderName):
            self.emitWarning ('Database folder name is missing or is not a folder', 'Database folder "%s" missing or not a folder.' % (self.databaseFolderName))
            return True

        self.databasePathName = os.path.join (self.databaseFolderName + '/', self.databaseFilename)

        # Reject if the database file does not exist
        if not os.path.isfile (self.databasePathName):
            self.emitWarning ('Database file is missing or of the wrong type', 'Database file "%s" missing or wrong type.' % (self.databasePathName))
            return True

        # Reject if the database file has the wrong filename extension
        if len (self.databaseFilename) <= self.DATABASE_NAME_EXTENSION_LENGTH:
            self.emitWarning ('Database filename too short', 'Database file "%s" is too short to contained the required filename extension "%s".' \
                        % (self.databaseFilename, DATABASE_NAME_EXTENSION))
            return True
        elif self.databaseFilename [-self.DATABASE_NAME_EXTENSION_LENGTH:] != self.DATABASE_NAME_EXTENSION:
            self.emitWarning ('Database file does not have the correct extension', 'Database file "%s" is missing its filename extension "%s" or it has no name.' \
                        % (self.databaseFilename, self.DATABASE_NAME_EXTENSION))
            return True

        self.username = getUsername ()

        # Reject if the username is too short
        if len (self.username) < 1:
            self.emitWarning ('Username too short', 'The username "%s" is too short.' % (self.username))
            return True

        self.configurationFileFolderName = os.path.join (databaseFolderName + '/', 'bc_config_%s' % (self.username))

        if not os.path.isdir (self.configurationFileFolderName):
            # The user's configuration file for this folder is missing. Try to create it.
            try:
                os.makedirs (self.configurationFileFolderName)
            except OSError:
                self.emitWarning ('Unable to create missing configuration directory', 'Unable to create directory "%s" for the user "%s".') % \
                            (self.configurationFileFolderName, username)
                return True
            
        self.databaseFilenameRoot = self.databaseFilename [:-self.DATABASE_NAME_EXTENSION_LENGTH]
        self.configurationFilename = '%s%s' % (self.databaseFilenameRoot, self.CONFIGURATION_FILENAME_EXTENSION)
        self.configurationFilePathname = os.path.join (self.configurationFileFolderName + '/', self.configurationFilename)
        return False
    def configurationFilename (self):
        return self.configurationFilePathname, self.configurationFilename
    def clearInternalConfiguration (self):
        try:
            del (self.db)
            self.db = Database (os.path.join (self.constants.databasePath + '/', self.constants.databaseFilename))
            _config.store (self.db)
        except:
            self.emitWarning ('Unable to clear database configuration', 'Unable to clear the inetrnal configuration from database "%s" for user "%s".') % \
                        (self.DatabaseName, self.username)

        return self.db
    def loadConfiguration (self, pathname):
        _file = open (pathname, 'r')
        _data = _file.read ()
        _config = pickle.loads (_data)
        _file.close ()
        return _config
    def loadConfigurationFromNamedFile (self, filename = ''):
        if not filename:
            filename, _dummy = QtGui.QFileDialog.getOpenFileName (self.root, 'Load Configuration from Named File', '', 'Configuration Files (*.bcc)')

        if filename:
            _config = self.loadConfiguration (filename)
            _temporaryBcFiles = BcFiles (self.root, _config ['databaseFolderName'], _config ['databaseFilename'])
            self.root.suspendForLoading (True)

            try:
                self.root.loadNamedDatabase (_temporaryBcFiles.databasePathName, _config)
            except:
                pass
            else:
                if _config:
                    self.root.applyConfiguration (_config)
            
                self.root.doRequiredLayouts ()

            self.root.suspendForLoading (False)
        else:
            _temporaryBcFiles = None

        return _temporaryBcFiles
    def saveConfiguration (self):
        self.writeConfigurationToFile (self.configurationFilePathname)
    def saveConfigurationToNamedFile (self):
        _filename, _dummy = QtGui.QFileDialog.getSaveFileName (self.root, 'Save Configuration to Named File', '', 'Configuration Files (*.bcc)')

        if _filename:
            if len (_filename) > self.CONFIGURATION_FILENAME_EXTENSION_LENGTH:
                if _filename [-self.CONFIGURATION_FILENAME_EXTENSION_LENGTH:] != self.CONFIGURATION_FILENAME_EXTENSION:
                    _filename = _filename + self.CONFIGURATION_FILENAME_EXTENSION
            else:
                _filename = _filename + self.CONFIGURATION_FILENAME_EXTENSION

            self.writeConfigurationToFile (_filename)
    def writeConfigurationToFile (self, filename):
        _config = self.root.gatherConfigurationData ()
        _file = open (filename, 'w')

        try:
            _config ['databaseFolderName'] = self.databaseFolderName
            _config ['databaseFilename'] = self.databaseFilename
            _config ['databaseUniqueId'] = self.root.tss.uniqueid (self.root.db)
            _file.write (pickle.dumps (_config))
            _file.close ()
        except:
            os.remove (filename)
            raise
