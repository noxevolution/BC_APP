#!/usr/bin/env python

import sys
import time
import PySide
import math
import graph
import tools

from PySide.QtCore import *
import PySide.QtCore as QtCore
from PySide.QtGui import *
from PySide.QtUiTools import *

from bc import *
from tools import *

import universe as universeNamespace

from pylab import plot,show
from numpy import vstack,array
from numpy.random import rand
from scipy.cluster.vq import kmeans,vq

CLUSTER_MARKER_DIAMETER = 20
### This takes the DIAMETER of the blue circle behind

class Cluster ():
    
    def __init__ (self, index):
        self._index = index
        self._nodes = []
    def index (self):
        return self._index
    def addNode (self, nodeIndex): ### This function creates the self._nodes list to view nodes in Communities for diffenr sphere diff lists created
        self._nodes.append (nodeIndex)
        
    def nodes (self):
        return self._nodes
    def __len__ (self):
        return len (self._nodes)

class ClusterLayoutThread (QThread):
    def __init__ (self, root):
        QThread.__init__ (self)
        self.root = root
        self.interruptRequest = False
        self.iAmWorking = False
        done = QtCore.Signal ()
        self.suspend = False
        QtCore.QObject.connect (self, QtCore.SIGNAL ('done ()'), self.root.cluster.view.mainThread.display) # Starts from here
        self.secondaryScaling = CLUSTER_MARKER_DIAMETER
    def setup (self, nodes, cm): ###  Imp function
        
        self.nodes = nodes
        self.cm = cm
        #<coefficient.Coefficients object at 0x090ADF90>
    def interrupt (self):
        if self.iAmWorking:
            self.interruptRequest = True
    def working (self):
        return self.iAmWorking
    def suspendRedraw (self, state):
        self.suspend = state
    def interruptRequested (self):
        return self.interruptRequest
    def computeInterClusterCoefficients (self):
        _x = ConciseMonitor ()
        # Create an empty list
        self.interClusterCoefficients = []

        # make a list of visible nodes:
        _visibleNodeList = []
        
        for _nodeIndex, _node in enumerate (self.nodes):
            if not _node.hiding:
                _visibleNodeList.append (_nodeIndex)

        _x.report ('  Cluster: visibleNodeList')
        # make an empty coefficient list
        #_visibleNodeList this combines all the visible nodes in diff circle to a single list
        # self.clusters [<clusterlayout.Cluster instance at 0x0B822A58>, <clusterlayout.Cluster instance  at 0x01BD8F80>]
        for _sourceCluster in self.clusters:
            _list = []
            self.interClusterCoefficients.append (_list)
            #self.interClusterCoefficients [[]] [[0.0, 0.0], []]
            for _targetCluster in self.clusters:
                _list.append (0.0)
                
        
        _x.report ('  Cluster: empty coefficient list')
        # Calculate the inter-cluster coefficients
        _sparse = self.cm.sparse #true
        #self.clusterMembership 
        """{0: <clusterlayout.Cluster instance at 0x01BD8F80>, 12: <clusterlayout.Cluster instance at 0x0B830A58>, 20: <clusterlayout.Cluster instance at 0x0B830A58>, 6: <
clusterlayout.Cluster instance at 0x01BD8F80>}"""
        for _sourceNodeIndex in _visibleNodeList:
            if self.interruptRequested (): break

            if _sourceNodeIndex not in self.clusterMembership:
                continue
                

            _coefficients = self.cm.norm [_sourceNodeIndex] # Not working 
            
            #_coefficients = {}
            for _targetNodeIndex in _visibleNodeList:
                if _targetNodeIndex not in self.clusterMembership:
                    continue

                if _sourceNodeIndex == _targetNodeIndex:
                    continue

                if _targetNodeIndex in _coefficients:
                    self.interClusterCoefficients [self.clusterMembership [_sourceNodeIndex].index ()] \
                                                  [self.clusterMembership [_targetNodeIndex].index ()] += _coefficients [_targetNodeIndex]
                                                    
        
        #self.interClusterCoefficients = [[6.471049908, 7.471049908], [8.471049908, 9.471049908]]
        # This defines where the blue circles should be 
        _x.report ('  Cluster: compute coefficients')
        # Calculate the cluster strength
        for _cluster in self.clusters:            
            _members = _cluster.nodes () # [20, 12]  [6, 0]
            _sum = 0
            
            for i in _members:
                for j in _members:
                    
                    #self.cm.norm [i] Same as _coefficients
                    if j in self.cm.norm [i]:
                        
                        # self.cm.norm [i][j] 
                        _sum += self.cm.norm [i] [j]

            _length = len (_members)
            _length = 4
            
            #_sum = 126 This basically sets the background clour of circle 
            if _length > 0:
                self.interClusterCoefficients [_cluster.index ()] [_cluster.index ()] = _sum / (_length * _length)
            else:
                self.interClusterCoefficients [_cluster.index ()] [_cluster.index ()] = 0

        _x.report ('  Cluster: calculate cluster strengths')
        # Find the maximum value of all coefficients
        _maxCoefficient = 0.0

        for _sourceClusterIndex, _sourceCluster in enumerate (self.clusters):
            for _targetClusterIndex, _targetCluster in enumerate (self.clusters):
                if _targetClusterIndex != _sourceClusterIndex:
                    if self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex] > _maxCoefficient:
                        _maxCoefficient = self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex]

        if _maxCoefficient == 0.0:
            _maxCoefficient = 1.0

        _x.report ('  Cluster: find max')
        # Normalise the coefficients
        self.allCoefficients = []

        if _maxCoefficient > 0.0:
            for _sourceClusterIndex, _sourceCluster in enumerate (self.clusters):
                _allCoefficients = dict ()

                for _targetClusterIndex, _targetCluster in enumerate (self.clusters):
                    if _targetClusterIndex != _sourceClusterIndex:
                        _coeff = self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex]
                        self.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex] /= _maxCoefficient
                        _allCoefficients [_targetClusterIndex] = abs (_coeff * 0.8 / _maxCoefficient)

                self.allCoefficients.append (_allCoefficients)
        #self.allCoefficients = [{1: 20.8}, {0: 0.8}] very important it defines the nodes plotted area
        #self.interClusterCoefficients = [[0.09194061925, 1.0], [1.0, 0.082111251375]]
        
        _x.report ('  Cluster: normalise')
    def graphClustering (self):
        self.root.cluster.view.visibleNodeDetails.resetNodeList ()
        self.root.cluster.view.visibleNodeDetails.resetPositions ()
        # if both statements are comment out nothing changes
        
        _totalClusters = len (self.clusters)
        
        if _totalClusters == 0:
            return
        #self.root.SCALING = 200
        #self.root.OFFSET = 50
        _primaryScaling = (self.root.SCALING + self.root.OFFSET) * 0.9
        #_primaryScaling = 200000 no affect 
        _radius = self.root.clusterLayoutThread.secondaryScaling
        self.root.cluster.view.circles = []
        
        for _clusterNumber, _cluster in enumerate (self.clusters):
            
            if self.interruptRequested ():
                break

            _totalNodes = len (_cluster)
            
            if _totalNodes:
                _xCluster = self._coordinates [_clusterNumber].x ()
                _yCluster = self._coordinates [_clusterNumber].y ()
                self.root.cluster.view.circles.append (CircleDescriptor (_xCluster, _yCluster, _radius))

                _graph = graph.Spiral (len (_cluster.nodes ()), scaling = CLUSTER_MARKER_DIAMETER * 0.7, cutoff = 20)
                
                _coordinates = _graph.coordinates ()
                # defind in graph.py
                #print _cluster.nodes ()= [20,12]
                for _nodeNumber, _node in enumerate (_cluster.nodes ()):
                    _x = _xCluster + _coordinates [_nodeNumber].x ()
                    _y = _yCluster + _coordinates [_nodeNumber].y ()
                    self.root.cluster.view.visibleNodeDetails.setPosition (_node, QPointF (_x, _y))
                    self.root.cluster.view.visibleNodeDetails.addIndex (_node)
        #print self.root.cluster.view.circles           
    def doClustering (self):
        resource_usage = ConciseMonitor ()
        self.root.cluster.view.links = []
        _cutoff = self.root.cluster.view.cutoffSlider.slider.value () / 255.0
        self.nodeList = []
        self.clusters = []
        self.clusterCount = 0

        # Make a list of visible nodes
        #print enumerate(self.nodes)
        for _index, _node in enumerate (self.nodes):
            if not self.nodes [_index].hiding:
                self.nodeList.append (_index)
                _node.cluster.linksIn = []
                _node.cluster.linksOut = []

        self.unallocatedNodes = self.nodeList [:]
        resource_usage.report ('Cluster: Visible nodes')

        # Calculate link strengths
        _sparse = self.cm.sparse
        _strengths = []

        for i, data in enumerate (self.cm.norm):
            if i in self.nodeList:
                for j in data:
                    if j < i:
                        if j in self.nodeList:
                            _coeff = data [j]

                            if _coeff > 0.005:
                                _strengths.append ([_coeff, i, j])

        self.strengths = sorted (_strengths, key = lambda _strength: _strength [0])
        resource_usage.report ('Cluster: Link strengths')

        # Create the links
        _maxCoefficient = 1.0 if self.root.cm.maxabscoeff () == 0.0 else self.root.cm.maxabscoeff ()

        for _link in self.strengths:
            _coeff, i, j = _link

            if _coeff > _cutoff:
                _linkObject = self.root.cluster.view.addLink (i, j, _coeff, _maxCoefficient)
                _linkObject.state = universeNamespace.LinkDrawState.RESET
                _linkObject.zValue = 1
                self.root.cluster.view.links.append (_linkObject)

        resource_usage.report ('Cluster: Create links')

        # Do the clustering
        self.clusterMembership = dict ()
        _strengths = self.strengths [:]
        _clusterCount = -1
        print "cluster"
        print self.unallocatedNodes
        while len (_strengths):
            if self.interruptRequested (): break
            _coeff, _i, _j = _strengths.pop ()

            if _i in self.clusterMembership:
                if _j not in self.clusterMembership:
                    self.clusterMembership [_j] = self.clusterMembership [_i]
                    self.clusters [self.clusterMembership [_i].index ()].addNode (_j)
                    self.unallocatedNodes.remove (_j)
            else:
                if _j in self.clusterMembership:
                    self.clusterMembership [_i] = self.clusterMembership [_j]
                    self.clusters [self.clusterMembership [_j].index ()].addNode (_i)
                    self.unallocatedNodes.remove (_i)
                else:
                    _clusterCount += 1
                    _cluster = Cluster (_clusterCount)
                    self.clusters.append (_cluster)
                    self.clusterMembership [_i] = _cluster
                    self.clusterMembership [_j] = _cluster
                    _cluster.addNode (_i)
                    _cluster.addNode (_j)
                    
                    self.unallocatedNodes.remove (_i)
                    self.unallocatedNodes.remove (_j)

        resource_usage.report ('Cluster: Clustering')

        if self.interruptRequested ():
            return

        self.computeInterClusterCoefficients ()
        resource_usage.report ('Cluster: Intercluster coefficients')

        # Do a force layout for the collection of clusters
        _maximumCoefficient = 0.0
        _coeffs = []

        if len (self.clusters) > 0:
            _fruchtTime = ConciseMonitor ()
            self.root.message [self.root.CLUSTER].display ('Starting layout')
            _initialPositions = []
            
            for i in range (len (self.allCoefficients)):
                _angle = 2.0 * math.pi * i / len (self.allCoefficients)
                _position = QPointF (math.cos (_angle), math.sin (_angle))
                _initialPositions.append (_position)

            _graph = graph.FruchtermanReingold (self.root.application, self.root.cluster.view, self.allCoefficients, _initialPositions, \
                                                checkInterruptFunction = self.interruptRequested, \
                                                messageItem = self.root.message [self.root.CLUSTER], minimumKineticEnergy = 0.001)
            _fruchtTime.report ('    Cluster: RuchtermanFreingold')
                    
            if _graph.wasInterrupted ():
                self._coordinates = []

            self._coordinates = _graph.result ()

            for i, dummy in enumerate (self._coordinates):
                self._coordinates [i] *= self.root.TOTAL_SCALING

            # Draw the graph
            #_graphTime = ConciseMonitor ()
            self.graphClustering ()

            if _graph.wasInterrupted ():
                self.root.cluster.view.update ()
                self.root.application.processEvents ()

            #_graphTime.report ('    Cluster: graphClustering')
        else:
            self.root.cluster.view.visibleNodeDetails.resetNodeList ()
            self.root.cluster.view.visibleNodeDetails.resetPositions ()
            self.root.message [self.root.CLUSTER].display ('No clusters')
            self.root.cluster.view.update ()
            self.root.application.processEvents ()
            resource_usage.report ('Cluster: Layout (Empty)')
            return True

        resource_usage.report ('Cluster: Layout')
        return False
    def run (self):
        self.iAmWorking = True
        self.root.cluster.view.circles = []

        if not self.suspend:
            _leaveMessage = self.doClustering ()
            #_leaveMessage = False

            try:
                if not _graph.wasInterrupted ():
                    self.done.emit ()
            except:
                if len (self.clusters) > 0:
                    self.done.emit ()

            if not _leaveMessage: self.root.message [self.root.CLUSTER].hide () ### This hides the Starting Layout

        self.interruptRequest = False
        self.iAmWorking = False
    def newFun(self,val):
        newList = []
        timePoints = self.root.tss.series () [0].getAllTimes ()
        originalTimesteps = len (timePoints)

        ### First Node ####
        _series = self.makeIntoList (self.root.tss.series () [0].getAllValues (),originalTimesteps)
        _series1 = self.makeIntoList (self.root.tss.series () [6].getAllValues (),originalTimesteps)
        #_series2 = self.makeIntoList (self.root.tss.series () [12].getAllValues (),originalTimesteps)
        #_series3 = self.makeIntoList (self.root.tss.series () [20].getAllValues (),originalTimesteps)
        #_series4 = self.makeIntoList (self.root.tss.series () [26].getAllValues (),originalTimesteps)
        #_series5 = self.makeIntoList (self.root.tss.series () [32].getAllValues (),originalTimesteps)
        #_series6 = self.makeIntoList (self.root.tss.series () [38].getAllValues (),originalTimesteps)
        #_series7 = self.makeIntoList (self.root.tss.series () [44].getAllValues (),originalTimesteps)
        #_series8 = self.makeIntoList (self.root.tss.series () [99].getAllValues (),originalTimesteps)
        #_series9 = self.makeIntoList (self.root.tss.series () [105].getAllValues (),originalTimesteps)
        #_series10 = self.makeIntoList (self.root.tss.series () [111].getAllValues (),originalTimesteps)

        #### Second Node ####
        _series_2 = self.makeIntoList (self.root.tss.series () [1].getAllValues (),originalTimesteps)
        _series_21 = self.makeIntoList (self.root.tss.series () [7].getAllValues (),originalTimesteps)

        #### Third Node ####
        _series_3 = self.makeIntoList (self.root.tss.series () [2].getAllValues (),originalTimesteps)
        _series_31 = self.makeIntoList (self.root.tss.series () [8].getAllValues (),originalTimesteps)

        #### Fourth Node ####
        _series_4 = self.makeIntoList (self.root.tss.series () [3].getAllValues (),originalTimesteps)
        _series_41 = self.makeIntoList (self.root.tss.series () [9].getAllValues (),originalTimesteps)

        #### Fifth Node ####
        _series_5 = self.makeIntoList (self.root.tss.series () [4].getAllValues (),originalTimesteps)
        _series_51 = self.makeIntoList (self.root.tss.series () [10].getAllValues (),originalTimesteps)

        #### Six Node ####
        _series_6 = self.makeIntoList (self.root.tss.series () [5].getAllValues (),originalTimesteps)
        _series_61 = self.makeIntoList (self.root.tss.series () [11].getAllValues (),originalTimesteps)
        
        tempdict = {}
        myListValues =[]
        myListKeys = []
        tempdict['0'] = _series[0]
        tempdict['6'] = _series1[0]
        tempdict['1'] = _series_2[0]
        tempdict['7'] = _series_21[0]
        tempdict['2'] = _series_3[0]
        tempdict['8'] = _series_31[0]
        tempdict['3'] = _series_4[0]
        tempdict['9'] = _series_41[0]
        tempdict['4'] = _series_5[0]
        tempdict['10'] = _series_51[0]
        tempdict['5'] = _series_6[0]
        tempdict['11'] = _series_61[0]
        
        #tempdict['12'] = _series2[0]
        #tempdict['20'] = _series3[0]
        #tempdict['26'] = _series4[0]
        #tempdict['32'] = _series5[0]
        #tempdict['38'] = _series6[0]
        #tempdict['44'] = _series7[0]
        #tempdict['99'] = _series8[0]
        #tempdict['105'] = _series9[0]
        #tempdict['111'] = _series10[0]
        #[[ 0.86331394  0.77951832  0.96983028  0.24389262  0.79920703  0.50693795]
         #[ 0.63492098  0.70823343  0.63531361  0.96416378  0.50030982  0.75487837]]
        myListNew1 = [_series[0],_series_2[0],_series_3[0],_series_4[0],_series_5[0],_series_6[0]]
        myListNew2 = [_series1[0],_series_21[0],_series_31[0],_series_41[0],_series_51[0],_series_61[0]]

        myListNew1 = [_series[0],_series1[0]]
        myListNew2 = [_series_2[0],_series_21[0]]
        myListNew3 = [_series_3[0],_series_31[0]]
        myListNew4 = [_series_4[0],_series_41[0]]
        myListNew5 = [_series_5[0],_series_51[0]]
        myListNew6 = [_series_6[0],_series_61[0]]
        myListValues.append(myListNew1)
        myListValues.append(myListNew2)
        myListValues.append(myListNew3)
        myListValues.append(myListNew4)
        myListValues.append(myListNew5)
        myListValues.append(myListNew6)
        
        myList = tempdict.values()
        myListKeys = tempdict.keys()
        
        data = vstack((array(myListValues)))        
        centroids,_ = kmeans(data,2)
        print "*"*100
        print centroids[0]
        print centroids[1]
        # assign each sample to a cluster
        idx,_ = vq(data,centroids)

        # some plotting using numpy's logical indexing
        plot(data[idx==0,0],data[idx==0,1],'ob',
             data[idx==1,0],data[idx==1,1],'or')
        plot(centroids[:,0],centroids[:,1],'sg',markersize=8)
        show()
        centroidList =[]
        centroidList.append(list(centroids[0]))
        centroidList.append(list(centroids[1]))
        print "1"*100
        print centroidList
        
        
        resource_usage = ConciseMonitor ()
        self.root.cluster.view.links = []
        _cutoff = self.root.cluster.view.cutoffSlider.slider.value () / 255.0        
        self.nodeList = []
        self.clusters = []
        self.clusterCount = 0

        # Make a list of visible nodes
        #print enumerate(self.nodes)
        for _index, _node in enumerate (self.nodes):
            if not self.nodes [_index].hiding:
                self.nodeList.append (_index)
                _node.cluster.linksIn = []
                _node.cluster.linksOut = []

        self.unallocatedNodes = self.nodeList [:]
        resource_usage.report ('Cluster: Visible nodes')

        # Calculate link strengths
        _sparse = self.cm.sparse
        _strengths = []
        
        for i, data in enumerate (self.cm.norm):
            
            if i in self.nodeList:
                for j in data:
                    if j < i:
                        if j in self.nodeList:
                            _coeff = data [j]

                            if _coeff > 0.005:
                                _strengths.append ([_coeff, i, j])

        self.strengths = sorted (_strengths, key = lambda _strength: _strength [0])
        #print self.strengths
        #self.strengths= [[0.497986624, 12, 0], [0.553540103, 20, 6], [0.588712775, 20, 0], [0.648992237, 12, 6], [0.656890011, 6, 0], [0.735524954, 20, 12]]
        resource_usage.report ('Cluster: Link strengths')

        # Create the links
        _maxCoefficient = 1.0 if self.root.cm.maxabscoeff () == 0.0 else self.root.cm.maxabscoeff ()
        
        for _link in self.strengths:
            _coeff, i, j = _link

            if _coeff > _cutoff:                
                _linkObject = self.root.cluster.view.addLink (i, j, _coeff, _maxCoefficient)
                _linkObject.state = universeNamespace.LinkDrawState.RESET
                _linkObject.zValue = 1
                self.root.cluster.view.links.append (_linkObject)

        resource_usage.report ('Cluster: Create links')

        # Do the clustering
        self.clusterMembership = dict ()
        _strengths = self.strengths [:]
        # same as self.strengths [:]
        _clusterCount = -1
        _cluster1 =''
        _cluster2 =''
         
        for k in myListValues:
            
            if self.interruptRequested (): break
            
            #dist1 = math.sqrt((centroidList[0][0]-k[0])* (centroidList[0][1]-k[1]))
            dist1 = math.sqrt(((centroidList[0][0]-k[0])*(centroidList[0][0]-k[0])) + ((centroidList[0][1]-k[1])*(centroidList[0][1]-k[1]))) 
            print "******"
            
            print centroidList[0]
            
            print k
            
            print dist1
            print "#######"
            dist2 = math.sqrt(((centroidList[1][0]-k[0])*(centroidList[1][0]-k[0])) + ((centroidList[1][1]-k[1])*(centroidList[1][1]-k[1])))            
            print centroidList[1]
            print k
            print dist2
            print "?????"
            if dist1 < dist2:
                if isinstance(_cluster1,Cluster):
                    pass
                else:
                    _clusterCount += 1
                    _cluster1 = Cluster (_clusterCount)
                    self.clusters.append (_cluster1)
                self.clusterMembership [int(myListKeys[myList.index(k[0])])] = _cluster1
                _cluster1.addNode (int(myListKeys[myList.index(k[0])]))
                self.unallocatedNodes.remove (int(myListKeys[myList.index(k[0])]))
                #self.clusterMembership [int(myListKeys[myList.index(k[1])])] = _cluster1
                #_cluster1.addNode (int(myListKeys[myList.index(k[1])]))
                #self.unallocatedNodes.remove (int(myListKeys[myList.index(k[1])]))
                #print "First"
                #print myListKeys[myListValues.index(myListValues[k])]
            if dist2 < dist1:
                if isinstance(_cluster2,Cluster):
                    pass
                else:
                    _clusterCount += 1
                    _cluster2 = Cluster (_clusterCount)
                    self.clusters.append (_cluster2)
                self.clusterMembership [int(myListKeys[myList.index(k[0])])] = _cluster2
                _cluster2.addNode (int(myListKeys[myList.index(k[0])]))
                #print "1st"
                #print myListKeys[myListValues.index(myListValues[k])]
                #print centroidList[1]
                self.unallocatedNodes.remove (int(myListKeys[myList.index(k[0])]))
                #self.clusterMembership [int(myListKeys[myList.index(k[1])])] = _cluster2
                #_cluster2.addNode (int(myListKeys[myList.index(k[1])]))
                #self.unallocatedNodes.remove (int(myListKeys[myList.index(k[1])]))


        
        
        resource_usage.report ('Cluster: Clustering')

        if self.interruptRequested ():
            return

        self.computeInterClusterCoefficients ()
        resource_usage.report ('Cluster: Intercluster coefficients')

        # Do a force layout for the collection of clusters
        _maximumCoefficient = 0.0
        _coeffs = []
        
        if len (self.clusters) > 0:
            _fruchtTime = ConciseMonitor ()
            self.root.message [self.root.CLUSTER].display ('Starting layout')
            _initialPositions = []
            #self.allCoefficients = [{1: 18.8}, {0: 0.8}]
            for i in range (len (self.allCoefficients)):
                #print self.allCoefficients [{1: 0.8}, {0: 0.8}] [{1: 0.8}, {0: 0.8}]
                _angle = 2.0 * math.pi * i / len (self.allCoefficients)
                _position = QPointF (math.cos (_angle), math.sin (_angle))
                _initialPositions.append (_position)

            _graph = graph.FruchtermanReingold (self.root.application, self.root.cluster.view, self.allCoefficients, _initialPositions, \
                                                checkInterruptFunction = self.interruptRequested, \
                                                messageItem = self.root.message [self.root.CLUSTER], minimumKineticEnergy = 0.001)
            _fruchtTime.report ('    Cluster: RuchtermanFreingold')
                    
            if _graph.wasInterrupted ():
                self._coordinates = []

            self._coordinates = _graph.result ()

            for i, dummy in enumerate (self._coordinates):
                self._coordinates [i] *= self.root.TOTAL_SCALING

            # Draw the graph            
            #_graphTime = ConciseMonitor () Seems to be not needed
            #print _graphTime
            self.graphClustering ()

            if _graph.wasInterrupted ():
                self.root.cluster.view.update ()
                self.root.application.processEvents ()

            #_graphTime.report ('    Cluster: graphClustering')
        else:
            self.root.cluster.view.visibleNodeDetails.resetNodeList ()
            self.root.cluster.view.visibleNodeDetails.resetPositions ()
            self.root.message [self.root.CLUSTER].display ('No clusters')
            self.root.cluster.view.update ()
            self.root.application.processEvents ()
            resource_usage.report ('Cluster: Layout (Empty)')
            return True

        resource_usage.report ('Cluster: Layout')
        self.done.emit ()
        self.root.message [self.root.CLUSTER].hide ()
        
    def makeIntoList (self, thing, length):
        _list = []

        for i in range (length):
            _list.append (thing [i])
           
        return _list
class ClusterCircle (QGraphicsEllipseItem):
    def __init__ (self, root, x, y, width, height, nodeList):
        QGraphicsEllipseItem.__init__ (self)
        self.root = root
        self.nodeList = nodeList
        self.setRect (QRectF (x, y, width, height))
        self.setAcceptHoverEvents (True)
    def hoverEnterEvent (self, event):
        try:
            for _nodeIndex in self.nodeList:
                _node = self.root.nodes [_nodeIndex].cluster.graphic
                _node.realPen = _node.pen ()
                _bodyColor = self.root.nodes [_nodeIndex].bodyColor
                _bodyIsBright = (_bodyColor.red () > 190) + (_bodyColor.green () > 190) + (_bodyColor.blue () > 190)

                if _bodyIsBright >= 4:
                    _node.setPen (QPen (QColor ('red'), 3))
                else:
                    _node.setPen (QPen (QColor ('white'), 3))
        except:
            pass
    def hoverLeaveEvent (self, event):
        try:
            for _nodeIndex in self.nodeList:
                _node = self.root.nodes [_nodeIndex].cluster.graphic
                _node.setPen (_node.realPen)
        except:
            pass
    def mouseDoubleClickEvent (self, event):
        self.root.hideNodes (list (set (self.root.cluster.view.visibleNodeDetails.nodeList ()) - set (self.nodeList)))
        self.root.setLayoutType ('Centrifuge')
        self.root.updateSelectionsAndHideButtons ()

class ClusterLayout ():
    def __init__ (self, root):
        self.root = root
    def layout (self):
        if self.root.clusterLayoutThread.working ():
            self.root.clusterLayoutThread.interrupt ()

        self.root.clusterLayoutThread.wait ()
        #self.root.setUpdatesEnabled (False)
        self.root.clusterLayoutThread.setup (self.root.nodes [:], self.root.clusterCm)
        self.root.clusterLayoutThread.start ()
        #self.root.setUpdatesEnabled (True)
    def display (self):
        _savedSelectionList = self.root.selectionList [:]        
        self.root.setUpdatesEnabled (False)
        self.root.cluster.view.xf.setup (0, 0, 0, self.root.cluster.view.rotation.y (), self.root.cluster.view.rotation.x (), 0)
        self.root.cluster.view.removeAllGraphicsItemsFromScene ()
        self.root.cluster.view.realizeNodes (self.root.cluster.view.visibleNodeDetails.nodeList (), _savedSelectionList)

        if self.root.linksCheckbox.checkState () == Qt.Checked:
            self.root.cluster.view.realizeLinks (self.root.cosmeticLinksCheckbox.checkState () == Qt.Checked)

        # Get the cluster marker colour
        _color = self.root.constants.clusterMarkerColor

        # Display cluster markers
        for _clusterIndex, _cluster in enumerate (self.root.cluster.view.circles):
            _radius = _cluster.radius ()
            _diameter = 2.0 * _radius
            _x, _y, _z = self.root.cluster.view.xf.transform (_cluster.x (), _cluster.y (), 0)
            _rx, _ry, _rz = self.root.cluster.view.xf.transform (_radius, _radius, 0)
            _c = ClusterCircle (self.root, _x - _radius, _y - _radius, _diameter, _diameter, self.root.clusterLayoutThread.clusters [_clusterIndex].nodes ())
            _cluster.setGraphic (_c)
            _c.setPen (Qt.NoPen)
            _coeff = self.root.clusterLayoutThread.interClusterCoefficients [_clusterIndex] [_clusterIndex] * 255
            _markerColor = QColor (_color.red (), _color.green (), _color.blue (), _coeff)
            _c.setBrush (_markerColor)
            _c.setZValue (0)
            self.root.cluster.view.scene.addItem (_c)

        # Show intercluster coefficients
        #for _sourceClusterIndex, _sourceCluster in enumerate (self.root.cluster.view.circles):
        #    for _targetClusterIndex, _targetCluster in enumerate (self.root.cluster.view.circles):
        #        if _targetClusterIndex < _sourceClusterIndex:
        #            _xS, _yS, _zS = self.root.cluster.view.xf.transform (_sourceCluster.x (), _sourceCluster.y (), 0)
        #            _xT, _yT, _zT = self.root.cluster.view.xf.transform (_targetCluster.x (), _targetCluster.y (), 0)
        #            _coeff = self.root.clusterLayoutThread.interClusterCoefficients [_sourceClusterIndex] [_targetClusterIndex] * 255
        #            _line = QGraphicsLineItem (_xS, _yS, _xT, _yT)
        #            _line.setPen (QColor (0, 0, 255, _coeff))
        #            self.root.cluster.view.scene.addItem (_line)
        
        self.root.cluster.view.showNodes ()

        if self.root.linksCheckbox.checkState () == Qt.Checked:
            _showLinks = True

            for _link in self.root.cluster.view.links:
                _link.graphic.setZValue (_link.zValue)
                _link.graphic.setVisible (_showLinks)

        self.root.cluster.updateStatus ()
        self.root.setUpdatesEnabled (True)
        self.root.cluster.view.update ()
        self.root.application.processEvents ()
       
