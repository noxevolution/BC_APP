#!/usr/bin/env python

####################################################################################
#
#        Monitor
#
#        The Monitor class reports on usage of system resources
#        
####################################################################################

import psutil
import sys
import time

KB = 1024
MB = KB * KB
GB = KB * KB * KB

def format_storage(bytes):
    if bytes < KB:
        return '%d' % bytes
    elif bytes < MB:
        return '%dK' % ((bytes+KB-1)/KB)
    elif bytes < GB:
        return '%dM' % ((bytes+MB-1)/MB)
    else:
        return '%dG' % ((bytes+GB-1)/GB)

def format_percent(percent):
    return '%d%%' % int(percent)

def format_time(microsec):
    return '%.3f' % microsec

FORMATTERS = dict(

        cpu         = format_time,
        wall        = format_time,
        mem_total   = format_storage,
        mem         = format_storage,
        mem_free    = format_storage,
        mem_pc      = format_percent,
        vmem_total  = format_storage,
        vmem        = format_storage,
        vmem_free   = format_storage,
        vmem_pc     = format_percent,
)


class Monitor(dict):

    enabled = True
    mcounter = 1

    def __init__(self,report_attrnames=None,out=None,*args,**kwargs):
        super(Monitor,self).__init__(*args,**kwargs)
        super(Monitor,self).__setattr__('__dict__',self)    # access keys as attributes
        self.snapshot()                                     # record the current values
        self._report_attrnames = report_attrnames
        self._out = out
        self._mcounter = Monitor.mcounter
        if self._mcounter == 1 and Monitor.enabled:
            if not out: out = sys.stderr
            lmt = time.localtime()
            print >>out, '%02d:%02d:%02d %-65s |%d|' % (lmt.tm_hour, lmt.tm_min, lmt.tm_sec, 'Monitor started %s' % time.asctime(), 0)
        Monitor.mcounter += 1

    def __sub__(self,another):                              # deltas = self - another
        diff = Monitor(self._report_attrnames, self)
        Monitor.mcounter -= 1
        diff.cpu        -= another.cpu
        diff.wall       -= another.wall
        diff.mem_total  -= another.mem_total
        diff.mem        -= another.mem
        diff.mem_free   -= another.mem_free
        diff.mem_pc     -= another.mem_pc
        diff.vmem_total -= another.vmem_total
        diff.vmem       -= another.vmem
        diff.vmem_free  -= another.vmem_free
        diff.vmem_pc    -= another.vmem_pc
        return diff

    def snapshot(self):
        phymem  = psutil.phymem_usage()                     # memory usage is in bytes (long int)
        virtmem = psutil.virtmem_usage()
        self.cpu        = time.clock()                      # current process cpu time in seconds (float)
        self.wall       = time.time()                       # current wall clock time in seconds since the epoch (float)
        self.mem_total  = phymem.total
        self.mem        = phymem.used
        self.mem_free   = phymem.free
        self.mem_pc     = phymem.percent
        self.vmem_total = virtmem.total
        self.vmem       = virtmem.used
        self.vmem_free  = virtmem.free
        self.vmem_pc    = virtmem.percent

    def report(self, prefix='', out=None, attrnames=None):
        now = Monitor(self._report_attrnames)
        Monitor.mcounter -= 1
        deltas = now - self
        if not out: out = self._out
        if not out: out = sys.stderr
        if not attrnames: attrnames = self._report_attrnames
        if not attrnames: attrnames = [ key for key in self.__dict__ if not key.startswith('_') ]
        if Monitor.enabled:
            lmt = time.localtime()
            print >>out, '%02d:%02d:%02d %-65s |%d|' % (lmt.tm_hour, lmt.tm_min, lmt.tm_sec, prefix, self._mcounter),
            for attr in attrnames:
                print >>out, '%s=%s' % (attr,FORMATTERS[attr](deltas[attr])),
            print >>out
        return now

    @classmethod
    def enable(cls,flag):
        Monitor.enabled = flag

class ConciseMonitor(Monitor):
    def __init__(self,report_attrnames=None,*args,**kwargs):
        if not report_attrnames: report_attrnames = 'cpu wall mem vmem'.split(' ')
        super(ConciseMonitor,self).__init__(report_attrnames,*args,**kwargs)

def unittest():
    Monitor.enable(len(sys.argv) > 1)
    outfile = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '-':
            outfile = sys.stdout
        else:
            try:
                outfile = file(sys.argv[1],'a')
                print >> sys.stderr, 'appending monitor output to file %s' % sys.argv[1]
            except:
                outfile = None
    def gobble(keep):
        for i in range(1000):
            array = list()
            for j in range(1000):
                array.append(j)
            keep += array
    keep = [ ]
    startup = mon = ConciseMonitor(out=outfile)
    for i in range(5):
        gobble(keep)
        mon = mon.report('iteration #%s' % i,out=outfile)
    startup.report('overall')
    print "Monitor okay"


if __name__ == '__main__':
    unittest()

