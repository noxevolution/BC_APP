#!/usr/bin/env python

#################################################################################
#
#   20111023  First optimisation of the BC visualisation app - The CoefficientMatrix
#
#   RESULTS:
#
#   1. 6 X speed increase in TimeSeriesSet database load
#
#   2. 0.1 X memory decrease with new CoefficientMatrix implementation using python arrays
#      but the memory savings in CoefficientMatrix enjoy a slight speed decrease of 5%
#
#   3. 3 X speed increase by implicitly calculating functions of the coefficent matrix, i.e.
#      using methods in the object instead of explicitly making the calculations, which are loop-bound
#
#
#   DETAILS
#
#   1. calc cardinality once during DB load
#
#       METRIC: Databases-V4.016/Biggy-Random-Regressions-1%.db
#           TimeSeriesSet load time was: 19.759 sec
#           TimeSeriesSet load time now:  2.527 sec
#
#   2. CoefficientMatrix vs ArrayedCoefficientMatrix
#
#       19:40:46 Monitor started Sun Oct 23 19:40:46 2011                     |0|
#       19:40:48 EventSeriesSet init    sansdb, 0 ts 0 coeff                  |3| cpu=0.000 wall=0.000 mem=0 vmem=0
#       19:40:48 CoefficientMatrix init, 23094 coeffs                         |4| cpu=0.530 wall=0.530 mem=124M vmem=0
#       19:40:48 TimeSeriesSet init #1 withdb, 3957 ts 23094 coeff            |2| cpu=2.214 wall=2.215 mem=149M vmem=0
#       19:40:49 CoefficientMatrix init, 23094 coeffs                         |6| cpu=0.565 wall=0.591 mem=122M vmem=0
#       19:40:49 load Coefficien      combined NestleOct11.xlsx cardinality=23094 |5| cpu=0.565 wall=0.593 mem=122M vmem=0
#       19:40:57 sum of all 15657849 cells = 3297.29789667                    |7| cpu=7.881 wall=7.917 mem=-561152 vmem=0
#       19:40:57 CoefficientMatrix                                            |1| cpu=10.661 wall=10.727 mem=271M vmem=0
#       19:40:59 EventSeriesSet init    sansdb, 0 ts 0 coeff                  |10| cpu=0.000 wall=0.000 mem=0 vmem=0
#       19:41:00 ArrayedCoefficientMatrix init, 23094 coeffs                  |11| cpu=1.630 wall=1.630 mem=124M vmem=0
#       19:41:00 TimeSeriesSet init #1 withdb, 3957 ts 23094 coeff            |9| cpu=3.625 wall=3.626 mem=147M vmem=0
#       19:41:02 ArrayedCoefficientMatrix init, 23094 coeffs                  |13| cpu=1.570 wall=1.570 mem=120M vmem=0
#       19:41:02 load ArrayedCoe      combined NestleOct11.xlsx cardinality=23094 |12| cpu=1.570 wall=1.570 mem=120M vmem=0
#       19:41:10 sum of all 15657849 cells = 3297.29789667                    |14| cpu=8.438 wall=8.457 mem=-274432 vmem=0
#       19:41:10 ArrayedCoefficientMatrix                                     |8| cpu=13.634 wall=13.654 mem=267M vmem=0
#
#   3. The sum of all coeffs in the CoefficientMatrix can be calculated by severals different methods. Explicit
#      summing calculates the sum by calling the CM object to access each cell in the matrix using the get() method.
#      Implicit summing leaves the job to the CM object itself. The overhead of the explicit method is significant:
#      calls to cm.get(i,j) are expensive. So expensive that it takes 3++ times longer for the sum to be calculated!
#
#   4. The get() method has been removed. Now the client of the CM class accesses the coeffs directly.
#
#################################################################################


import array
import sys

from application import *
from database import *
from timeseries import *
from monitor import ConciseMonitor

def time_nested_loop(n):
    loopuse = ConciseMonitor()
    for i in range(n):
        for j in range(n):
            pass
    loopuse.report('loopuse - empty nested loop of %s x %s = %s iterations' % (n,n,n*n))

def time_minimum(n):
    loopuse = ConciseMonitor()
    for i in range(n):
        for j in range(n):
            k = i
            if i < j:
                k = j
    loopuse = loopuse.report('loopuse - loop of i<j for minimum: %s x %s = %s iterations' % (n,n,n*n))
    for i in range(n):
        for j in range(n):
            k = min(i,j)
    loopuse = loopuse.report('loopuse - loop of min() for minimum: %s x %s = %s iterations' % (n,n,n*n))

def time_one(db, tssid):
    keep = list()     # keep is required to prevent python GC from deleting unused tss and coeff matrices
    for usesparse in (False,True):
        resuse = ConciseMonitor()
        tss = TimeSeriesSet(db,tssid) # ,usesparse)
        tss._usesparse = usesparse
        keep.append(tss)
        cindex = tss.coeffindex()       # dict of { coeffid, description } for all coefficient matrices 
        keep.append(tss.coefficients())
        for coeffid in sorted(cindex.keys()):
            localuse = ConciseMonitor()
            cm = tss.loadcoefficients(db,coeffid)
            keep.append(cm)
            localuse.report('load %10.10s %30.30s cardinality=%s' % (type(cm).__name__, cm.description(), cm.cardinality()))
            sumuse = ConciseMonitor()
            coeffs, n = cm.readyloop()
            sum = 0
            if cm.sparse:
                for i in range(n):
                    row = coeffs[i]
                    for j in row:
                        sum += row[j]
            else:
                for i in range(n):
                    row = coeffs[i]
                    for j in range(n):
                        sum += row[j]
            sumuse = sumuse.report('sum of all %s cells = %s explicit' % (n*n, sum))
            if cm.sparse:
                coeffs, n = cm.readyloop()
                sum = 0
                for i in range(n):
                    for j in coeffs[i]:
                        sum += coeffs.get(i,j)
            sumuse = sumuse.report('sum of all %s cells = %s using Sparse.get(i,j)' % (n*n, sum))
            sumuse = sumuse.report('sum of all %s cells = %s implicit by row' % (n*n, cm.sum_by_rows()))
            sumuse.report('sum of all %s cells = %s implicit by col' % (n*n, cm.sum_by_cols()))
        resuse.report('test_one %s ^^^^^^^^^^^^^^^^^' % cm.matrix_type())

    
def unittest():
    if '--help' in sys.argv or '-?' in sys.argv:
        print 'use: %s [ dbpath [ tssid ]]' % sys.argv[0]
        sys.exit(1)

    verbose = False
    test = True
    app = Application(None,__name__,verbose,test)

    dbpath = app.dbFilePath if len(sys.argv) < 2 else sys.argv[1]
    tssid = None if len(sys.argv) < 3 else int(sys.argv[2])
    db = Database(dbpath)
    if tssid is None:
        tssid = TimeSeriesSet.seriessetids(db)[0]
    time_one(db,tssid)

if __name__ == '__main__': 
    unittest()

