#!/usr/bin/env python

####################################################################################
#
#        TimeSeries(Database, tss, seriesid, ordinal)
#
#        TimeSeriesSet(Database, seriessetid)
#
#        Both of the above classes mimic the interface and behaviour of their Java analogues
#        
####################################################################################
#
#        EventSeries(event,times)           # a TimeSeries that very simply handles events
#
#        EventSeriesSet(Database)           # a TimeSeriesSet that only contains EventSeries
#
#        Both of the above classes mimic the interface and behaviour of their Java analogues
#
####################################################################################

import math, sys
from application import *
from coefficient import *
from database import *
from dict import *
from timepoint import *
from util import *
from monitor import ConciseMonitor
import constants
import random




class as_list(object):
    """ treat a getter method that can be called as method(i) as a list; the getter is then as_list(obj,getmethod)[i] """
    def __init__(self,obj,getmethod):
        self.obj = obj
        self.call = getattr(obj,getmethod)
    def __getitem__ (self,i):
        return self.call(i)

class TimeSeries(object):

    ## VF_INTERPOLATED = 0x0001                # value flags     ## V4.016 - remove valueflags and HandyAndySeries
    ## VF_ESTIMATED    = 0x0002

    def __init__(self,db,tss,seriesid,ordinal):

        self.app = Application.the_app
        self._values = None
        self._normvalues = None
        self._intensities = None
        self._seriesid = seriesid
        self._ordinal = ordinal
        self._categoryparts = None
        self._dict = Dict(db,"TimeSeries",seriesid)
        self._start = tss.start() + self.startoff()
        self._tss = tss

        self._categoryparts = self.category().split(':')

        self._load_values()

        # the getAllXxxxx(i) family of methods now access the required parts of the time series dynamically, taking startoff() and endoff() into account

        self._getAllValues =  as_list(self,'getvalue')
        self._getAllNormValues =  as_list(self,'getnormvalue')
        self._getAllIntensities =  as_list(self,'getintensity')
    def uniqueId(self):
       return self._dict["uniqueid"] if "uniqueid" in self._dict else ""
    def forecasting(self):
       return self._dict["forecasting"] if "forecasting" in self._dict else ""
    def _load_values(self):

        # load values: we discard NULL values since databases prior to the v4.023 Importer stored NULL value padding before startoff() and after endoff(), a waste of space
        self._values = [ float(v) for v in self._tss.db().selectColumn("SELECT value FROM seriesvalue WHERE seriesid=? AND value IS NOT NULL ORDER BY timeid",self._seriesid) ]

        LUMPIES = self.islumpy()

        self._minvalue = +1e50
        self._maxvalue = -1e50
        for val in self._values:
            if val != None:
                if (not LUMPIES) or (LUMPIES and val != 0):
                    self._minvalue = min(self._minvalue,val)
                    self._maxvalue = max(self._maxvalue,val)

        self._intensities = [ 1.0, ] * len(self)

        if LUMPIES:
            # the intensity of a displayed bubble varies during a sequence of zeros in the series
            # varies according to one complete cycle of the cosine function
            A = 0.75            # amplitude of the cosine, i.e. luminosity varies from 1.0 down to 1-A
            startzero = -1
            i = 0
            self._intensities = [ ]
            for val in self._values:
                if val == None:
                    self._intensities.append(None)
                elif val == 0:
                    if startzero < 0: startzero = i
                else:
                    if startzero >= 0:
                        N = i - startzero                # the number of zero values
                        # print >>sys.stderr,"Intensity time for [%s,%s]" % (startzero,i)
                        for j in range(N+2):
                            if j > 0 and j < N+1:        # intensities range from +1 through 1-A back up to +1; discard the +1 and -1
                                self._intensities.append( A/2 * math.cos(2*j*math.pi/(N+1)) + (1-A/2)  )
                                # print >>sys.stderr,"Appending intensity %s for %s/%s in ts %s" % (self._intensities[len(self._intensities)-1],j,N,self.label())
                        startzero = -1
                    self._intensities.append(1.0)
                i += 1
            if startzero >= 0:
                N = i - startzero                # the number of zero values
                # print >>sys.stderr,"Intensity time for [%s,%s]" % (startzero,i)
                for j in range(N+2):
                    if j > 0 and j < N+1:        # intensities range from +1 through 1-A back up to +1; discard the +1 and -1
                        self._intensities.append( A/2 * math.cos(2*j*math.pi/(N+1)) + (1-A/2)  )
                        # print >>sys.stderr,"Appending intensity %s for %s/%s in ts %s" % (self._intensities[len(self._intensities)-1],j,N,self.label())

            # zeros are set to their last non-zero (holding) value
            origvalues = self._values
            self._values = [ ]
            holding = 0
            for val in origvalues:
                if val == 0: val = holding
                self._values.append(val)
                holding = val
            holding = 0
            N = len(self._values)
            for i in range(N):      # catch any leading zeros and set to next holding value (by traversing in reverse)
                val = self._values[N-1-i]
                if val == 0: self._values[N-1-i] = holding
                else: holding = val

        maxmin = self._maxvalue - self._minvalue
        self._normvalues = []
        for val in self._values:
            assert val != None      # V4.016 - we only store the contiguous non-null "active" time series datapoints, sans null pre-padding and post-padding
            if maxmin == 0:
                if val == 0:
                    self._normvalues.append (0)
                else:
                    self._normvalues.append (1)
            else:
                self._normvalues.append((val-self._minvalue) / maxmin)

        self.log("TimeSeries: %s-%s %s %s %s[%s] LRD=%s minv=%s maxv=%s" % (
              self.startoff()
            , self.endoff()
            , self.label()
            , self.category()
            , self.tooltip()
            , len(self)
            , self.lastdeltapc()
            , self.min()
            , self.max()
        ))


    maxStringisedDatapoints = 9

    def __len__(self):
        return len(self._values)

    def __str__(self):
        res = "[%s-%s-%s#%s$%s%%%s]" % (self.label(),self.category(),self.tooltip(),self.ordinal(),self.seriesid(),self.lastdeltapc())
        tpoint = self.start().clone()
        for i in range(len(self)):
            if i >= self.maxStringisedDatapoints-1: break
            res +=  " %s,%s" % (self._values[i], tpoint)
            tpoint.next()   # or tpoint += 1 for that matter :)
        if i < self.maxStringisedDatapoints: res += " ..."
        return res

    def __getitem__ (self, column):
        return self.getvalue(column)

    def min(self):
        return self._minvalue

    def max(self):
        return self._maxvalue

    def log(self,message):
            self.app.logts(message)

    # ANDY Got so fed up with Amar's non-printing characters in labels, decided to do something positive about it.
    #def label(self):
    #    return self._dict["label"]
    def label(self):
        _oldLabel = self._dict["label"]
        _newLabel = ''

        for c in _oldLabel:
            if ord (c) > 127:
                _newLabel += ' '
            else:
                _newLabel += c

        return _newLabel
    def lastdeltapc(self):
        return float(self._dict["lastdeltapc"])

    def isevent(self):
        return False

    def islumpy(self):
        return len(self._dict["islumpy"]) > 0        # booleans in the labeldict are considered True only if a value is present and has a length()>0

    def category(self):
        return self._dict["category"]

    def startoff(self):
        return int(self._dict["startoff"])

    def endoff(self):
        return int(self._dict["endoff"])

    def extent(self):
        return len(self)

    def getvalue(self,i):
        return self._values[i - self.startoff()] if i >= self.startoff() and i <= self.endoff() else None

    def getnormvalue(self,i):
        return self._normvalues[i - self.startoff()] if i >= self.startoff() and i <= self.endoff() else None

    def getintensity(self,i):
        return self._intensities[i - self.startoff()] if i >= self.startoff() and i <= self.endoff() else None

    def tooltip(self):
        return self._dict["tooltip"]

    def start(self):            # returns the starting TimePoint for the time series
        return self._start

    def ordinal(self):
        return self._ordinal

    def seriesid(self):
        return self._seriesid

    def categoryparts(self):
        return self._categoryparts

    def ensure_categoryparts(self,n):
        while len(self._categoryparts) < n:
            self._categoryparts.append("")

    ## V4.016 - TimeSeries does not store flags, times, all values and normalised values and intensities (rather just non null values), nor any original values, binary values

    def getAllValues(self):
        return self._getAllValues

    def getAllNormValues(self):
        return self._getAllNormValues

    def getAllIntensities(self):
        return self._getAllIntensities
    
    def getAllTimes(self):
        return self._tss.times()

    ##    def gettime(self,i):
    ##        return self.getAllTimes()[self.startoff() + i]
    ##
    ##    def getoriginalvalue(self,i):
    ##        return self.getAllOriginalValues()[self.startoff() + i]
    ##
    ##    def getbinaryvalue(self,i):
    ##        return self.getAllBinaryValues()[self.startoff() + i]
    ##
    ##    def getAllTimes(self):            # legacy support: was self.times()
    ##        return self._times
    ##
    ##    def getAllValues(self):           # legacy support: was self.values()
    ##        return self._values
    ##
    ##    def getAllOriginalValues(self):   # useful for lumpy series: the original unmodified values
    ##        return self._origvalues
    ##
    ##    def getAllNormValues(self):       # legacy support: was self.normvalues()
    ##        return self._normvalues
    ##
    ##    def getAllBinaryValues(self): 
    ##        return self._binaryvalues
    ##
    ##    def getAllIntensities(self):
    ##        return self._intensities
    ##
    ##    def getAllValueFlags(self):       # legacy support: was self.flags()
    ##        return self._valueflags
    ##  
    ##    def getvalueflag(self,i):
    ##        return self.getAllValueFlags()[self.startoff() + i]



class TimeSeriesSet(object):

    def clone(self):                        # return a copy of this TimeSeriesSet, *** coefficient matrices and the time series are NOT deep copied ***

        copy = TimeSeriesSet()

        copy.app = self.app = Application.the_app

        copy._series = list(self._series)
        copy._shared_times = list(self._shared_times)
        copy._start = self._start.clone()
        copy._interesting_categoryparts_ordinal = list(self._interesting_categoryparts_ordinal)
        copy._interesting_categoryparts_level = self._interesting_categoryparts_level
        copy._events = self._events
        copy._dict = dict(self._dict)
        copy._db = self._db
        copy._seriessetid = self._seriessetid
        copy._coeffids = None
        copy._coeffindex = self._coeffindex
        copy._coeffnames = self._coeffnames
        copy._coefficients = self._coefficients
        copy._usesparse = self._usesparse

        return copy

    def __init__(self, db=None, seriessetid=None):

        resource_usage = ConciseMonitor()
        resource_timeseries = 0
        resource_coefficients = 0

        if db and not seriessetid: raise Exception("cannot create a TimeSeriesSet from the database (db=%s) without a seriessetid" % db.filepath())

        self.app = Application.the_app

        self._series = [ ]
        self._shared_times = None
        self._start = None
        self._interesting_categoryparts_ordinal = [ ]        # each unique "first interesting" TimeSeries category part is assigned an ordinal starting at 0
        self._interesting_categoryparts_level = 0            # "first interesting" means the level into the category parts that changes form one TimeSeries to the next
        self._events = None
        self._dict = None
        self._db = db
        self._seriessetid = None
        self._coeffids = [ ]
        self._coeffindex = dict()
        self._coeffnames = dict()
        self._coefficients = None
        self._usesparse = True

        if db:
            Dict.KNOWNCLASSES = None      # HACK HACK HACK - force Dict to reload its KNOWNCLASSES since they can vary from one database to another
            self._dict = Dict(db,"TimeSeriesSet",seriessetid)
            self._seriessetid = seriessetid
            self._shared_times = db.selectColumn("SELECT time FROM time WHERE seriessetid=? ORDER BY timeid",seriessetid)
            self._start = TimePoint.fromString(TimePoint.intervalOf(self._shared_times), self._shared_times[0])

            seriesids = db.selectColumn("SELECT seriesid FROM series WHERE seriessetid=?",self._seriessetid)
            for ordinal in range(len(seriesids)):
                self._series.append(TimeSeries(db,self,seriesids[ordinal],ordinal))
            resource_timeseries = len(self)
            self._events = EventSeriesSet(self,db)  # load the events only after _shared_times has been initialised
            self.app.log("TimeSeriesSe %s [%s series]" % (self.details(), len(self)))

            for row in db.selectRows("SELECT coeffid,value FROM coeff c, dict d WHERE c.seriessetid=? AND c.coeffid=d.clientid AND d.key='description' ORDER BY coeffid DESC",seriessetid):
                self._coeffids.append(int(row[0]))
                self._coeffindex[int(row[0])] = row[1]

            for row in db.selectRows("SELECT value,coeffid FROM coeff c, dict d WHERE c.coeffid=d.clientid AND d.key='name'"):
                self._coeffnames[row[0]] = row[1]

            self.loadcoefficients(db,self._coeffids[0])
            resource_coefficients = self._coefficients.cardinality()

        lpi = 0        # give each different interesting (first or deeper "level" or interesting_categoryparts_level) categorypart a unique ordinal
        maxnparts = 0
        for ts in self._series:
            maxnparts = max(maxnparts, len(ts.categoryparts()))
        for ts in self._series:
            ts.ensure_categoryparts(maxnparts)

        for _interesting_categoryparts_level in range(maxnparts):
            self._interesting_categoryparts_ordinal = { }        # map categorypart string to ordinal int
            for ts in self._series:
                if ts.categoryparts()[self._interesting_categoryparts_level] not in self._interesting_categoryparts_ordinal:
                    self._interesting_categoryparts_ordinal[ts.categoryparts()[_interesting_categoryparts_level]] = lpi
                    lpi += 1
            if len(self._interesting_categoryparts_ordinal):
                break
        if len(self._interesting_categoryparts_ordinal) == 0:
            self._interesting_categoryparts_level = 0

        self.log("interesting_categoryparts_ordinal = %s" % self._interesting_categoryparts_ordinal)

        tssid = '#%s' % self.seriessetid() if self.seriessetid() else ''
        resource_usage.report('%s init %s %s ts %s coeffs' % (type(self).__name__, tssid, resource_timeseries, resource_coefficients))


    def __len__(self):
        return len(self._series)

    def coeffids(self):                   # return a list of coeffids in descending order, so that the most recent coeff matrix is first
        return self._coeffids

    def coeffindex(self):                 # return a dict of { coeffid, description } for all coefficient matrices found in the database for this tss
        return self._coeffindex

    def coeffnames(self):                 # return a dict of { name, coeffid } for all coefficient matrices found in the database for this tss
        return self._coeffnames

    def loadcoefficients(self,db,coeffid):
        self._coefficients = Coefficients(db, self, coeffid, self._usesparse)
        return self._coefficients

    def events(self):
        return self._events

    def getseries(self,i):
        return self._series[i]

    def series(self):
        return self._series

    def getcmat(self,matrixname='value'):
        return self._coefficients._matrices[matrixname]

    def getcoeff(self,i,j,matrixname='value'):
        if random.random() < 0.001:
            print >>sys.stderr,'*** PeriodicDeprecationAnnoyance: tss.getcoeff(%s,%s,%s) must be replaced with: 0 if %s not in row else row[%s]' % (i,j,matrixname,j,j)
        ## CAREFUL: we are assuming ALL the matrices in the Coefficients are sparse for the POC
        ## return 0 if self._sparse and j not in self._coeffs[i] else self._coeffs[i][j]
        return 0 if j not in self._coefficients._matrices[matrixname][i] else self._coefficients._matrices[matrixname][i][j]

    def details(self):
        return self._dict["details"]

    def interval(self):
        return self._start.interval()

    def isevents(self):
        return False

    def lagmax(self):
        return int(self._dict["lagmax"])

    def topn(self):
        return int(self._dict["topn"])

    def minreg(self):
        return int(self._dict["minreg"])

    def interesting_categoryparts_ordinal(self,ts):
        if ts.categoryparts()[self._interesting_categoryparts_level] not in self._interesting_categoryparts_ordinal:
            raise Exception, "TimeSeries %s has no interesting_categoryparts_ordinal" % ts
        return self._interesting_categoryparts_ordinal[ ts.categoryparts()[self._interesting_categoryparts_level] ]

    def seriessetid(self):
        return self._seriessetid

    def seriesid2ordinal(self):
        _seriesid2ordinal = { }        # map seriesid to timeseries' ordinal
        expectord = 0
        for ts in self._series:
            assert expectord == ts.ordinal()
            _seriesid2ordinal[ts.seriesid()] = ts.ordinal()
            expectord += 1
        return _seriesid2ordinal

    def lastreldelta_quintiles(self):                # return a map of TimeSeries' ordinal to lastreldelta quintile number (latter being in range(5))

        sortedts = sorted(self._series, key=lambda ts: abs(ts.lastdeltapc()), reverse=False)
        self.log( "lastreldelta_quintiles: sorted LRD=%s"  %  map(lambda ts: "(%s %s)" % (ts.lastdeltapc(), ts.ordinal()),sortedts) )
        if len(sortedts) != len(self): raise Exception,"lastreldelta_quintiles: sorted ts len=%s, should be %s" % (len(sortedts),len(self))

        NTILE = 5                        # partition the sorted lastreldelta()s into NTILE parts, i.e. quintiles, sorted descending
        N = len(self)
        QN = (N+NTILE-1)/NTILE            # quintile iteration increment
        res = { }                        # map ordinal to quintile number, which will be used to determine bubble radius for a TimeSeries node
        for i in range(0,N,QN):
            for j in range(i,min(i+QN,N)):
                res[sortedts[j].ordinal()] = i/QN
        self.log("lastreldelta_quintiles: LRDMap=%s" % res)
        for ordinal, quintile in res.iteritems():
            if ordinal >= N: raise Exception, "lastreldelta_quintiles: ordinal %s out of range(%s)" % (ordinal,N)
            if quintile >= NTILE: raise Exception, "lastreldelta_quintiles: quintile index %s out of range(%s)" % (quintile,NTILE)
        return res

    def log(self,message):
        self.app.logts(message)

    def ntimes(self):
        return len(self._shared_times)

    def times(self):
        return self._shared_times

    def start(self):            # returns the starting TimePoint for the entire set of timeseries
        return self._start

    def db(self):
        return self._db

    def orphan_index(self):     # return a list of tuples:
                                # (coeffdict, list of orphaned TimeSeries)
                                # of those time series that are orphaned, i.e. no coefficient connects the ts to other ts
                                # one tuple per coeffid
        my_ordinals = dict( (ts.ordinal(),False) for ts in self._series)
        s2o = self.seriesid2ordinal()
        db = self.db()
        seriessetid = self.seriessetid()
        cindex = dict( (coid,Dict(db,"CoefficientMatrix",coid)) for coid in db.selectColumn("SELECT coeffid FROM coeff WHERE seriessetid=?",seriessetid) )
        res = [ ]
        for coeffid in cindex:
            ords = dict(my_ordinals)
            db.cursor().execute("SELECT seriesid1,seriesid2,coeff FROM coeffvalue WHERE coeffid=?",[coeffid])
            for (id1, id2, coeff) in self._db.cursor().fetchall():
                if id1 not in s2o: raise Exception, "seriesid1=%s not found for coeffid=%s" % (id1, coeffid)
                if id2 not in s2o: raise Exception, "seriesid2=%s not found for coeffid=%s" % (id2, coeffid)
                if coeff: ords[s2o[id1]] = ords[s2o[id2]] = True
            orphans = [ self._series[ord] for ord in ords if not ords[ord] ]
            res.append( (cindex[coeffid], orphans) )
        return res


    @staticmethod
    def seriessetids(db):
        return db.selectColumn("SELECT seriessetid FROM seriesset ORDER BY seriessetid")

    @staticmethod
    def index(db):
        ind = dict()
        for row in db.selectRows("SELECT seriessetid,value FROM seriesset tss, dict d WHERE tss.seriessetid=d.clientid AND d.key='details' ORDER BY seriessetid"):
            ind[row[0]] = row[1]
        return ind

    @staticmethod
    def slice_index(db):
        assert db
        idx = TimeSeriesSet.index(db)
        res = dict()
        for seriessetid in idx.keys():
            times = db.selectColumn("SELECT time FROM time WHERE seriessetid=? ORDER BY timeid",seriessetid)
            interval = TimePoint.intervalOf(times)
            res[seriessetid] = dict(
                label=idx[seriessetid],
                starttime=times[0],
                endtime=times[-1],
                interval=interval,
                duration=TimePoint.fromString(interval,times[-1]) - TimePoint.fromString(interval,times[0]) + 1,
            )
        return res

    @staticmethod
    def uniqueid(db):
        assert db
        try:
            u1 = ';'.join([ str(c) for c in db.selectRows("SELECT * FROM version ORDER BY number LIMIT 1")[0]])
        except:
            u1 = ';'
        try:
            u2 = ';'.join(db.selectColumn("SELECT value FROM dictclient dc, dict d WHERE dc.classname='TimeSeriesSet' AND d.client=dc.client AND d.key='details' ORDER BY VALUE"))
        except:
            u2 = ';'
        return '%s;%s' % (u1,u2)


    @staticmethod
    def tunit(verbose):
        ConciseMonitor.enable(False)
        app = Application(None,"TestTimeSeries",verbose,True)
        db = Database(app.dbFilePath)
        if verbose: print >>sys.stderr,'TimeSeriesSet.uniqueid for %s is %s' % (db.basename(),TimeSeriesSet.uniqueid(db))
        tssids = TimeSeriesSet.seriessetids(db)
        if not len(tssids): raise Exception, "there are no TimeSeriesSets in %s" % db.filepath()
        tss = TimeSeriesSet(db,tssids[0])
        tss.lastreldelta_quintiles()
        evs = tss.events()

        print "TimeSeries and TimeSeriesSet okay"
        print "EventSeries and EventSeriesSet okay"

if __name__ == '__main__':
    TimeSeriesSet.tunit(len(sys.argv) > 1)



####################################################################################
#
#        EventSeries(event,times)           # a TimeSeries that very simply handles events
#
#        EventSeriesSet(Database)           # a TimeSeriesSet that only contains EventSeries
#
#        Both of the above classes mimic the interface and behaviour of their Java analogues
#
####################################################################################

class EventSeries(TimeSeries):

    def __init__(self,event,ess):          # construct a really simple time series that records an event: event values are non-zero if the event is current

        description, startdate, enddate, displaytype, fademonths = event    # event contains [ string, TimePoint, TimePoint, int, int ]

        self.app = Application.the_app              # TODO - remove the need for self.app - use Application.the_app instead
        self._values = [ ]
        self._seriesid = None
        self._ordinal = None
        self._categoryparts = None
        self._dict = dict(label=description, startdate=str(startdate), enddate=str(enddate), displaytype=displaytype, fademonths=fademonths, startoff=None, endoff=None, islumpy="")
        self._minvalue = None
        self._maxvalue = None
        self._intensities = None
        self._normvalues = None
        self._start = ess.start()

        timelinestart = ess.start()
        timelineend   = ess.start() + (ess.ntimes() - 1)

        if timelinestart > timelineend:
            raise Exception, "timeline start (%s) occurs after the timeline end (%s)" % (timelinestart,timelineend)
        if timelinestart.interval() != timelineend.interval():  
            raise Exception, "timeline start interval (%s) != the timeline end interval (%s)" % (timelinestart.interval(),timelineend.interval())

        runner = timelinestart.clone()
        endoff = 0
        while runner <= timelineend:
            value = 0
            # Java suckage is reads much better in Python. Compare: if runner.compareTo(event.startdate) >= 0 && runner.compareTo(event.enddate) <= 0
            if runner >= startdate and runner <= enddate: value = displaytype
            self._values.append(value)
            endoff += 1
            runner.next()

        self._dict["startoff"] = "0"
        self._dict["endoff"] = str(endoff)

        self._getAllValues =  as_list(self,'getvalue')
        #self._getAllNormValues =  as_list(self,'getnormvalue')
        #self._getAllIntensities =  as_list(self,'getintensity')

        self.log("EventSeries: %s [%s]" % (self.label() , len(self)))

    def startdate(self):        return DailyTimePoint(self._dict["startdate"])
    def enddate(self):          return DailyTimePoint(self._dict["enddate"])
    def displaytype(self):      return int(self._dict["displaytype"])
    def fademonths(self):       return int(self._dict["fademonths"])

    def isevent(self):          return True

    ## def setlabel(self,key,value):
        ## self._labeldict[key] = value

    def __str__(self):
        res = self.label()
        for i in range(len(self)):
            if i >= self.maxStringisedDatapoints-1: break
            res +=  " %s,%s" % (self.getAllTimes()[i],self.getAllValues()[i])
        if i < self.maxStringisedDatapoints: res += " ..."
        return res

    def extent(self):
        return None



class EventSeriesSet(TimeSeriesSet):

    def __init__(self,tss,db):          # an EventSeriesSet is a set of EventSeries, the EventSeries being created from the event table rows

        TimeSeriesSet.__init__(self)

        self._dict = dict(details = "events", lagmax=0, topn=0, minreg=0)

        self._shared_times = tss.times()
        self._start = TimePoint.fromString(TimePoint.intervalOf(self._shared_times), self._shared_times[0])
        self._seriessetid = None
        self._events = None

        for row in db.selectRows("SELECT description,startdate,enddate,displaytype,fademonths FROM event"):
            if len(row) != 5: raise Exception, "EventSeriesSet: event has %s columns, not 5" % len(row)
            event = [ row[0], DailyTimePoint(row[1]), DailyTimePoint(row[2]), int(row[3]), int(row[4]) ]
            self._series.append(EventSeries(event,self))

    def isevents(self): return True

    def getcoeff(self,i,j,matrixname='value'):
                                        raise Exception, "EventSeriesSet.getcoeff() is not supported"
    def events(self):                   raise Exception, "EventSeriesSet.events() is not supported"
    def seriesid2ordinal(self):         raise Exception, "EventSeriesSet.seriesid2ordinal() is not supported"
    def lastreldelta_quintiles(self):   raise Exception, "EventSeriesSet.lastreldelta_quintiles() is not supported"
    def seriessetids(db):               raise Exception, "EventSeriesSet.seriessetids() is not supported"
    def index(db):                      raise Exception, "EventSeriesSet.index() is not supported"

