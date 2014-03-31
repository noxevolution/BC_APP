#!/usr/bin/env python

####################################################################################
#
#       tp = TimePoint.fromString(interval,str) # interval is one of 'daily','weekly','monthly','yearly' or None
#
#       tp = DailyTimePoint(str)               # str is "YYYY-MM-DD" or "DD-MM-YYYY"
#       tp = DailyTimePoint(other)
#       tp = DailyTimePoint(year,month,day)
#
#       tp = WeeklyTimePoint(str)              # str is "YYYY-MM-DD" or "DD-MM-YYYY"
#       tp = WeeklyTimePoint(other)
#       tp = WeeklyTimePoint(year,month,day)
#
#       tp = MonthlyTimePoint(str)             # str is "YYYY-MM" or "MM-YYYY"
#       tp = MonthlyTimePoint(other)
#       tp = MonthlyTimePoint(year,month)
#
#       tp = YearlyTimePoint(str)              # str is "YYYY"
#       tp = YearlyTimePoint(other)
#       tp = YearlyTimePoint(year)
#
#       The above classes mimic the interface and behaviour of their Java analogues
#    
####################################################################################

import re, sys
from application import *

class TimePoint:

    yearlyPat  = re.compile(r'^(\d{1,4})$')
    monthlyPat = re.compile(r'^(\d{1,4})\D(\d{1,4})$')
    dailyPat   = re.compile(r'^(\d{1,4})\D(\d{1,4})\D(\d{1,4})$')

    def __init__(self, interval, year, month, day):     # must construct one of the derived classes, DailyWeeklyTimePointMonthlyTimePointTimePoint YearlyTimePoint
                                                        # as this is an abstract base class
        if isinstance(interval, TimePoint):
            other = interval
            self._interval = other._interval
            self._year = other._year
            self._month = other._month
            self._day = other._day
        else:
            self._interval = interval
            self._year = year
            self._month = month
            self._day = day
        self.calcHashCode()
        self.validate()

    @staticmethod
    def fromString(interval,str):                       # TimePoint factory creates a correctly typed TimePoint (derived class) based on str
                                                        # interval is force to match correct type if provided or an exception is raised
        mat = TimePoint.yearlyPat.match(str)
        if mat:
            if interval and interval != 'yearly': raise Exception, "TimePoint %s is yearly, not %s as requested" % (str,interval)
            return YearlyTimePoint(mat.group(1))
        mat = TimePoint.monthlyPat.match(str)
        if mat:
            if interval and interval != 'monthly': raise Exception, "TimePoint %s is monthly, not %s as requested" % (str,interval)
            year, month = int(mat.group(1)), int(mat.group(2))
            if year < month:  year, month = month, year
            return MonthlyTimePoint(year,month)
        mat = TimePoint.dailyPat.match(str)
        if mat:
            if interval and interval != 'daily' and interval != 'weekly': raise Exception, "TimePoint %s is daily or weekly, not %s as requested" % (str,interval)
            year, month, day = int(mat.group(1)), int(mat.group(2)), int(mat.group(3))
            if day >= 100: year, day = day, year
            if interval and interval == 'daily': return DailyTimePoint(year,month,day)
            return WeeklyTimePoint(year,month,day)
        raise Exception, "TimePoint '%s' is not recognised: should be one of YYYY, MM-YYYY or YYYY-MM, YYYY-MM-DD or DD-MM-YYYY" % str

    def __str__(self):       raise Exception, "TimePoint.__str__() is abstract"
    def clone(self):         raise Exception, "TimePoint.clone() is abstract"
    def next(self):          raise Exception, "TimePoint.next() is abstract"
    def prev(self):          raise Exception, "TimePoint.prev() is abstract"

    def interval(self):      return self._interval
    def year(self):          return self._year
    def month(self):         return self._month
    def day(self):           return self._day
    
    def __hash__(self):      return self._hashCode
    def __cmp__(self,other): return self._hashCode - other._hashCode

    def __sub__(self,other):
        d = 0
        iter = (self < other and self or other).clone()
        end = self < other and other or self
        incr = self < other and -1 or +1
        while iter < end:
            d += incr
            iter.next()
        return d

    def __add__(self,ninterval):
        res = self.clone()
        if ninterval >= 0:
            while ninterval > 0:
                res.next()
                ninterval -= 1
        else:
            while ninterval < 0:
                res.prev()
                ninterval += 1
        return res

    def transmogrify(self,interval):     # TimePoint cloned from self, but whose type is based on the provided interval
        if interval == 'daily':     return DailyTimePoint(self._year,self._month,self._day)
        if interval == 'weekly':    return WeeklyTimePoint(self._year,self._month,self._day)
        if interval == 'monthly':   return MonthlyTimePoint(self._year,self._month)
        if interval == 'yearly':    return YearlyTimePoint(self._year)
        raise Exception, "cannot transmogrify(%s,%s)" % (self,interval)

    def timeVector(self,ntimes):
        times = [ ]
        timePoint = self.clone()
        for i in range(ntimes):
            times.append(str(timePoint))
            timePoint.next()
        return times

    @staticmethod
    def intervalOf(times):
        if len(times) == 0: raise Exception,"cannot determine time interval from 0 times"
        time1 = times[0]
        time2 = len(times) > 1 and times[1] or ""
        mat = TimePoint.yearlyPat.match(time1)
        if mat: return 'yearly'
        mat = TimePoint.monthlyPat.match(time1)
        if mat: return 'monthly'
        mat = TimePoint.dailyPat.match(time1)
        if mat:
            if not time2: return 'weekly'
            if abs(TimePoint.fromString('daily',time2) - TimePoint.fromString('daily',time1)) > 1: return 'weekly'
            return 'daily'
        raise Exception, "intervalOf(times): TimePoint '%s' is not recognised: should be one of YYYY, MM-YYYY or YYYY-MM, YYYY-MM-DD or DD-MM-YYYY" % time1

    @staticmethod
    def timesStart(times): return TimePoint.fromString(TimePoint.intervalOf(times),times[0])

    @staticmethod
    def timesEnd(times): return TimePoint.fromString(TimePoint.intervalOf(times),times[-1])

    dim = [ 31,28,31,30,31,30,31,31,30,31,30,31 ]

    @staticmethod
    def daysInMonth(year, month):
        if month != 2: return TimePoint.dim[month-1]
        if year % 4 != 0 or (year % 100 == 0 and year % 400 != 0): return TimePoint.dim[month-1]
        return TimePoint.dim[month-1] + 1

    def calcHashCode(self):
        self._hashCode = ((self._year * 100) + self._month) * 100 + self._day

    def nextyear(self):
        self._year += 1
        self.calcHashCode()

    def prevyear(self):
        self._year -= 1
        self.calcHashCode()

    def nextmonth(self):
        self._month += 1
        if self._month > 12:
            self._month = 1
            self._year += 1
        self.calcHashCode()

    def prevmonth(self):
        self._month -= 1
        if self._month < 1:
            self._month = 12
            self._year -= 1
        self.calcHashCode()

    def nextdays(self, ndays):
        if ndays < 0 or ndays > 7: raise Exception, "nextdays(%s) is invalid: must be in range[0,7]" % ndays
        self._day += ndays
        dim = TimePoint.daysInMonth(self._year,self._month)
        while self._day > dim:
            self._day -= dim
            self._month += 1
            if self._month > 12:
                self._month = 1
                self._year += 1
            dim = TimePoint.daysInMonth(self._year,self._month)
        self.calcHashCode()

    def prevdays(self, ndays):
        if ndays < 0 or ndays > 7: raise Exception, "prevdays(%s) is invalid: must be in range[0,7]" % ndays
        self._day -= ndays
        if self._day < 0:
            self._month -= 1
            if self._month < 1:
                self._month = 12
                self._year -= 1
            self._day += TimePoint.daysInMonth(self._year,self._month)
        self.calcHashCode()

    def validate(self):
        if self._month < 1 or self._month > 12:
            raise Exception, "TimePoint '%s' has an invalid month: '%s' should be between 1 and 12" % (self,self._month)
        if self._day < 1 or self._day > TimePoint.daysInMonth(self._year,self._month):
            raise Exception, "TimePoint '%s' has an invalid day: '%s' should be between 1 and %s" % (self,self._day,TimePoint.daysInMonth(self._year,self._month))

    @staticmethod
    def tunit(verbose):
        app = Application(None,"TestTimePoint",verbose,True)

        # YearlyTimePoints

        p1 = YearlyTimePoint(2004)
        assert p1.interval()=='yearly'
        assert p1.year()==2004
        assert p1.month()==1
        assert p1 < YearlyTimePoint(2005)
        assert p1 > YearlyTimePoint(2003)
        assert str(p1)=="2004"
        assert p1+0 == p1
        assert p1+1 == YearlyTimePoint(2005)
        assert p1+10 == YearlyTimePoint(2014)
        assert p1+-1 == YearlyTimePoint(2003)       # NOTE: p1-1 does not work: __sub__ is for difference between TimePoints
        assert p1+-10 == YearlyTimePoint(1994)
        pclone = p1.clone()
        pclone += 40
        pclone += -40
        assert p1 == pclone

        p2 = YearlyTimePoint(2004)
        assert p1==p2
        assert p1.__cmp__(p2)==0
        assert hash(p1)==hash(p2)
            
        p3 = p2.clone()
        assert p3==p2

        p4 = TimePoint.fromString(None,"2004")
        assert p4==p2
        p4.next()
        assert p4.year()==2005
        assert p4.month()==1
        assert p4.day()==1

        times = p1.timeVector(3)
        assert len(times)==3
        assert times[0]=="2004"
        assert times[1]=="2005"
        assert times[2]=="2006"

        assert YearlyTimePoint(1994)-p1 == -10
        assert YearlyTimePoint(1997)-p1 ==  -7
        assert YearlyTimePoint(2003)-p1 ==  -1
        assert p1-YearlyTimePoint(2004) ==   0
        assert p1-YearlyTimePoint(2003) ==  +1
        assert p1-YearlyTimePoint(1997) ==  +7
        assert p1-YearlyTimePoint(1994) == +10
            
        print "YearlyTimePoint okay"

        # MonthlyTimePoints
        
        p1 = MonthlyTimePoint(2004,12)
        assert p1.interval()=='monthly'
        assert p1.year()==2004
        assert p1.month()==12
        assert p1 < MonthlyTimePoint(2005,1)
        assert p1 > MonthlyTimePoint(2003,12)
        assert str(p1)=="2004-12"
        assert p1+0 == p1
        assert p1+1 == MonthlyTimePoint(2005,1)
        assert p1+10 == MonthlyTimePoint(2005,10)
        assert p1+-1 == MonthlyTimePoint(2004,11)
        assert p1+-10 == MonthlyTimePoint(2004,2)
        pclone = p1.clone()
        pclone += 40
        pclone += -40
        assert p1 == pclone

        p2 = MonthlyTimePoint(2004,12)
        assert p1==p2
        assert p1.__cmp__(p2)==0
        assert hash(p1)==hash(p2)
            
        p3 = p2.clone()
        assert p3==p2

        p4 = TimePoint.fromString(None,"2004-12")
        assert p4==p2
        p4.next()
        assert p4.year()==2005
        assert p4.month()==1

        times = p1.timeVector(6)
        assert len(times) == 6
        assert times[0]=="2004-12"
        assert times[1]=="2005-01"
        assert times[2]=="2005-02"
        assert times[3]=="2005-03"
        assert times[4]=="2005-04"
        assert times[5]=="2005-05"
            
        assert MonthlyTimePoint(2002,11)-p1 == -25
        assert MonthlyTimePoint(2004,5)-p1  ==  -7
        assert MonthlyTimePoint(2004,11)-p1 ==  -1
        assert p1-MonthlyTimePoint(2004,12) ==   0
        assert p1-MonthlyTimePoint(2004,11) ==  +1
        assert p1-MonthlyTimePoint(2004,5)  ==  +7
        assert p1-MonthlyTimePoint(2002,11) == +25

        print "MonthlyTimePoint okay"

        # Weekly TimePoints
 
        p1 = WeeklyTimePoint(2000,2,27)
        assert p1.interval()=='weekly'
        assert p1.year()==2000
        assert p1.month()==2
        assert p1.day()==27
        assert p1 < WeeklyTimePoint(2005,1,1)
        assert p1 > WeeklyTimePoint(1998,12,1)
        assert str(p1)=="2000-02-27"
        assert p1+0 == p1
        assert p1+1 == WeeklyTimePoint(2000,3,5)
        assert p1+10 == WeeklyTimePoint(2000,5,7)
        assert p1+-1 == WeeklyTimePoint(2000,2,20)
        assert p1+-10 == WeeklyTimePoint(1999,12,19)
        pclone = p1.clone()
        pclone += 40
        pclone += -40
        assert p1 == pclone

        p2 = WeeklyTimePoint(2000,2,27)
        assert p1==p2
        assert p1.__cmp__(p2)==0
        assert hash(p1)==hash(p2)
            
        p3 = p2.clone()
        assert p3==p2

        p4 = TimePoint.fromString(None,"2000-02-27")
        assert p4==p2
        p4.next()
        assert p4.year()==2000
        assert p4.month()==3
        assert p4.day()==5

        times = p1.timeVector(7)
        assert len(times) == 7
        assert times[0]=="2000-02-27"
        assert times[1]=="2000-03-05"
        assert times[2]=="2000-03-12"
        assert times[3]=="2000-03-19"
        assert times[4]=="2000-03-26"
        assert times[5]=="2000-04-02"
        assert times[6]=="2000-04-09"
            
        times = WeeklyTimePoint(1,1,1).timeVector(3)
        assert len(times) == 3
        assert times[0]=="0001-01-01"
        assert times[1]=="0001-01-08"
        assert times[2]=="0001-01-15"
            
        assert WeeklyTimePoint(1999,2,28)-p1 == -52
        assert WeeklyTimePoint(2000,1,31)-p1 ==  -4
        assert WeeklyTimePoint(2000,2,20)-p1 ==  -1
        assert p1-WeeklyTimePoint(2000,2,27) ==   0
        assert p1-WeeklyTimePoint(2000,2,20) ==  +1
        assert p1-WeeklyTimePoint(2000,1,31) ==  +4
        assert p1-WeeklyTimePoint(1999,2,28) == +52

        print "WeeklyTimePoint okay"

        # Daily TimePoints
        
        p1 = DailyTimePoint(2000,2,27)
        assert p1.interval()=='daily'
        assert p1.year()==2000
        assert p1.month()==2
        assert p1.day()==27
        assert p1 < DailyTimePoint(2005,1,1)
        assert p1 > DailyTimePoint(1998,12,1)
        assert str(p1)=="2000-02-27"
        assert p1+0 == p1
        assert p1+1 == DailyTimePoint(2000,2,28)
        assert p1+10 == DailyTimePoint(2000,3,8)
        assert p1+-1 == DailyTimePoint(2000,2,26)
        assert p1+-10 == DailyTimePoint(2000,2,17)
        pclone = p1.clone()
        pclone += 40
        pclone += -40
        assert p1 == pclone

        p2 = DailyTimePoint("2000-2-27")
        assert p1==p2
        assert p1.__cmp__(p2)==0
        assert hash(p1)==hash(p2)
            
        p3 = p2.clone()
        assert p3==p2

        p4 = TimePoint.fromString('daily',"27-02-2000")
        assert p4==p2
        p4.next()
        assert p4.year()==2000
        assert p4.month()==2
        assert p4.day()==28

        times = p1.timeVector(10)
        assert len(times) == 10
        assert times[0]=="2000-02-27"
        assert times[1]=="2000-02-28"
        assert times[2]=="2000-02-29"
        assert times[3]=="2000-03-01"
        assert times[4]=="2000-03-02"
        assert times[5]=="2000-03-03"
        assert times[6]=="2000-03-04"
        assert times[7]=="2000-03-05"
        assert times[8]=="2000-03-06"
        assert times[9]=="2000-03-07"
            
        times = DailyTimePoint(1,1,1).timeVector(3)
        assert len(times) == 3
        assert times[0]=="0001-01-01"
        assert times[1]=="0001-01-02"
        assert times[2]=="0001-01-03"
            
        assert DailyTimePoint(1999,2,27)-p1 == -365
        assert DailyTimePoint(2000,1,27)-p1 ==  -31
        assert DailyTimePoint(2000,2,26)-p1 ==   -1
        assert p1-DailyTimePoint(2000,2,27) ==    0
        assert p1-DailyTimePoint(2000,2,26) ==   +1
        assert p1-DailyTimePoint(2000,1,27) ==  +31
        assert p1-DailyTimePoint(1999,2,27) == +365

        print "DailyTimePoint okay"

        print "TimePoint okay"

class YearlyTimePoint(TimePoint):

    def __init__(self,str):
        if isinstance(str,TimePoint):
            TimePoint.__init__(self,str,None,None,None)
        else:
            TimePoint.__init__(self,'yearly',int(str),1,1)

    def __str__(self):  return "%04d" % self._year
    def clone(self):    return YearlyTimePoint(self)
    def next(self):     return self.nextyear()
    def prev(self):     return self.prevyear()

class MonthlyTimePoint(TimePoint):

    def __init__(self,*args):
        if isinstance(args[0],TimePoint):
            TimePoint.__init__(self,args[0],None,None,None)
        elif len(args) > 1:
            TimePoint.__init__(self,'monthly',args[0],args[1],1)
        else:
            TimePoint.__init__(self,TimePoint.fromString('monthly',args[0]),None,None,None)

    def __str__(self):  return "%04d-%02d" % (self._year,self._month)
    def clone(self):    return MonthlyTimePoint(self)
    def next(self):     return self.nextmonth()
    def prev(self):     return self.prevmonth()

class DailyTimePoint(TimePoint):

    def __init__(self,*args):
        if isinstance(args[0],TimePoint):
            TimePoint.__init__(self,args[0],None,None,None)
        elif len(args) > 2:
            TimePoint.__init__(self,'daily',args[0],args[1],args[2])
        else:
            TimePoint.__init__(self,TimePoint.fromString('daily',args[0]),None,None,None)

    def __str__(self):  return "%04d-%02d-%02d" % (self._year,self._month,self._day)
    def clone(self):    return DailyTimePoint(self)
    def next(self):     return self.nextdays(1)
    def prev(self):     return self.prevdays(1)

class WeeklyTimePoint(TimePoint):

    def __init__(self,*args):
        if isinstance(args[0],TimePoint):
            TimePoint.__init__(self,args[0],None,None,None)
        elif len(args) > 2:
            TimePoint.__init__(self,'weekly',args[0],args[1],args[2])
        else:
            TimePoint.__init__(self,TimePoint.fromString('weekly',args[0]),None,None,None)

    def __str__(self):  return "%04d-%02d-%02d" % (self._year,self._month,self._day)
    def clone(self):    return WeeklyTimePoint(self)
    def next(self):     return self.nextdays(7)
    def prev(self):     return self.prevdays(7)

if __name__ == '__main__':
    TimePoint.tunit(len(sys.argv) > 1)

from timeseries import *
