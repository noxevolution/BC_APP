#!/usr/bin/env python

import re,sys
from application import *
from timeseries import *
from coefficient import *       # problems arise if you import coefficient before timeseries :(
from monitor import ConciseMonitor
from util import *


ConciseMonitor.enable(False)


class Showxy:

    DEFAULT_DATAPOINTS = TimeSeries.maxStringisedDatapoints

    def __init__(self,**args):

        debugpatt = re.compile('debug_')
        app = Application(None,"Showxy",args['debug'],False)

        if args['debug']:
            for k in args.keys():
                if debugpatt.search(k):
                    app.params.params[k] = True

        dbfile = args['dbfile'] or app.dbFilePath
        db = args['db'] = Database(dbfile)
        tssids = TimeSeriesSet.seriessetids(db)
        index = TimeSeriesSet.index(db)
        if not len(tssids): raise Exception, "there are no TimeSeriesSets in %s" % db.filepath()
        seriessetid = tssids[0]
        if args['seriessetid'] != None:
            seriessetid = args['seriessetid']
            if not seriessetid in index: raise Exception("there is no time series set with id=%s" % seriessetid)
        tss = TimeSeriesSet(db,seriessetid)
        ## if args['handy']:
            ## tss.series().append(HandyAndySeries.LINEAR(tss))
            ## tss.series().append(HandyAndySeries.CONSTANT(tss))

        if args['debug']: print "Hello from Showxy(%s)" % args

        if args['listindex']:
            for seriessetid in index.keys():
                print "id=%s  details=%s" % (seriessetid,index[seriessetid])
        else:
            if args['coeff'] or args['all']:
                self.dump_coefficient_matrices(tss,**args)
            elif args['orphan']:
                self.dump_orphans(tss,**args)
            elif args['RFORMAT']:
                self.dump_R(tss,**args)
            else:
                self.dump_timeseriesset(tss,**args)

            if args['all']:
                self.dump_timeseriesset(tss,**args)
                print '\n\n\nDUMPING CLONE:\n'
                self.dump_timeseriesset(tss.clone(),**args)

            if len(tssids) == 2 and args['seriessetid'] == None:
                print "\nNOTE: there is %s other time series set stored in %s: use the -t option to select and show it" % (len(tssids)-1,dbfile)
            elif len(tssids) > 1 and args['seriessetid'] == None:
                print "\nNOTE: there are %s other time series sets stored in %s: use the -t option to select and show one of them" % (len(tssids)-1,dbfile)

    def dump_orphans(self,tss,**args):
        print 'Orphaned TimeSeries for database %s:' % args['db'].basename()
        for (coeffdict,orphans) in tss.orphan_index():
            if not orphans:
                print '  TimeSeriesSet #%s has no orphans out of %s TimeSeries in CoeffMatrix %s' % (tss.seriessetid(), len(tss), coeffdict['description'])
            else:
                print '  TimeSeriesSet #%s has %s orphans out of %s TimeSeries in CoeffMatrix %s' % (tss.seriessetid(), len(orphans), len(tss), coeffdict['description'])
                if not args['brief']:
                    for ts in sorted(orphans, lambda x,y: cmp(x.ordinal(), y.ordinal())):
                        print '    TimeSeries #%s is orphaned (%s, %s)' % (ts.ordinal(), ts.label(), ts.category())

    def dump_timeseriesset(self,tss,**args):

        classname = tss.isevents() and "EventSeriesSet" or "TimeSeriesSet"
        print "Dump of %s %s, seriessetid=%s, interval=%s, LAGMAX=%s, isevents=%s" % (classname,tss.details(),tss.seriessetid(),tss.interval(),tss.lagmax(),tss.isevents())
        if len(tss) == 0:
            print "%s is empty." % classname
            return
        leadfmt = "%-30.30s %3s %10s %10s "
        eventleadfmt = "%-30.30s "
        blankleader = leadfmt % ('','','','')
        colfmt = " %8s"
        if not tss.isevents(): print leadfmt % ('label','n','min','max'),
        if tss.isevents(): print eventleadfmt % ('label'),
        N = min(args['n'] or self.DEFAULT_DATAPOINTS,len(tss.times()))
        NR = range(N)
        dailypatt = re.compile('\d+\D\d+\D\d+')
        isdaily = dailypatt.search(tss.times()[0])
        for t in zip(tss.times(),NR):
            tdisp = t[0]
            if isdaily: tdisp = tdisp[0:4]+tdisp[5:7]+tdisp[8:10]
            print colfmt % tdisp,
        print
        def getthings(listlike,n):
            return [ listlike[i] for i in range(n) ]
        for ts in tss.series():
            if not tss.isevents(): leader = leadfmt % (ts.label(), len(ts), '%.2f'%ts.min(), '%.2f'%ts.max())
            if tss.isevents(): leader = eventleadfmt % ts.label()
            if args['real']:
                print leader,
                for r in getthings(ts.getAllValues(),N): # zip(ts.getAllValues(),NR):
                    if not tss.isevents(): print colfmt % (r == None and 'None' or ('%.1f' % r)),
                    if tss.isevents(): print colfmt % (not int(r) and ' ' or r),
                print
                leader = blankleader
                ## V4.016 - remove originalvalues
                ## if ts.islumpy():
                    ## print leader,
                    ## for r in getthings(ts.getAllOriginalValues(),N): # zip(ts.getAllOriginalValues(),NR):
                        ## print colfmt % (r == None and 'None' or ('%.1f' % r)),
                    ## print
            if not tss.isevents():
                if args['norm']:
                    print leader,
                    for m in getthings(ts.getAllNormValues(),N): # zip(ts.getAllNormValues(),NR):
                        print colfmt % (m == None and 'None' or ('%.5f' % m)),
                    print
                    leader = blankleader
                ## V4.016 - remove flags and HandyAndySeries
                ## if args['flag'] and any(ts.getAllValueFlags()):
                    ## print leader,
                    ## for f in zip(ts.flags(),N):
                        ## print colfmt % TimeSeries.formatflags(f[0]),
                    ## print
                    ## leader = blankleader
                if args['intensities'] or ts.islumpy():
                    print leader,
                    for m in getthings(ts.getAllIntensities(),N): # zip(ts.getAllIntensities(),NR):
                        print colfmt % (m == None and 'None' or ('%.3f' % m)),
                    print
                    leader = blankleader
        print
        if not tss.isevents(): self.dump_timeseriesset(tss.events(),**args)

    def dump_coefficient_matrices(self,tss,**args):
        for coeffid in tss.coeffindex().keys():
            cmat = tss.loadcoefficients(args['db'],coeffid)
            coeffdict = dict(cmat._dict)
            coeffdict["cardinality"] = cmat.cardinality()
            coeffdict["fill"] = "%.2f" % cmat.fill()
            coeffdict["size"] = cmat._N * cmat._N
            print "Coefficients %s - %s using lagmax=%s" % (cmat.name(), cmat.description(), cmat.lagmax())
            print "attributes: %s" % Util.obj2jslim(coeffdict)
            for matrixname in matrix_names:
                # HACK: 'value' in matrix_names is known as 'coeffs' to clients of the Coefficients class
                show_matrixname = matrixname if matrixname != 'value' else 'coeffs'
                print 'Sparse subMatrix   *** %-18s cardinality=%s fill=%.2f issymmetrical=%s maxabscoeff=%s' % (show_matrixname, cmat.cardinality(matrixname), cmat.issymmetrical(matrixname), (100*cmat.fill(matrixname)), cmat.maxabscoeff(matrixname))
                leadfmt = "%-4s %-30.30s  "
                ordinalfmt = "[%d]"
                coefffmt = "%7.4f"
                colfmt = " %8s"
                print leadfmt % ("    ",""),
                NC = args['n'] or self.DEFAULT_DATAPOINTS
                issymm = cmat.issymmetrical(matrixname)
                colmax = issymm and NC-1 or NC
                for t in zip(range(len(tss)),range(colmax)):
                    print colfmt % (ordinalfmt % t[0]),
                print
                mat = tss.getcmat(matrixname)
                for i in range(len(tss)):
                    print leadfmt % (ordinalfmt % i,tss.getseries(i).label()),
                    jmax = min(len(tss),NC)
                    if issymm: jmax = i
                    for j in range(jmax):
                        print colfmt % (coefffmt % mat.get(i,j)),
                    print
                print

    def dump_R(self,tss,**args):
        # e.g. X1=c(17698.57,16350.16,17449.77,14558.84,14226.08,14444.82,14497.09,14759.5,15172.38,13434.42)
        for ts in tss.series():
            sys.stdout.write("N%s=\"%s\"\n" % (ts.ordinal(),ts.label()))
            sys.stdout.write("X%s=c(" % ts.ordinal())
            separator = ""
            for i in range(ts.extent()):
                sys.stdout.write("%s%s" % (separator,ts.getvalue(i)))
                separator = ","
            sys.stdout.write(")\n")
            if ts.islumpy():
                sys.stdout.write("O%s=c(" % ts.ordinal())
                separator = ""
                for i in range(ts.extent()):
                    sys.stdout.write("%s%s" % (separator,ts.getoriginalvalue(i)))
                    separator = ","
                sys.stdout.write(")\n")
                sys.stdout.write("L%s=c(" % ts.ordinal())
                separator = ""
                for i in range(ts.extent()):
                    sys.stdout.write("%s%s" % (separator,ts.getbinaryvalue(i)))
                    separator = ","
                sys.stdout.write(")\n")

    @staticmethod
    def help():
        print """%s: display XY data made available by the timeseries class for the XY Plot python script
use: %s [ options ]...  [ dbfile [ n ] ]

where:

      dbfile       optional database file containing a time series set; default is the workspace in the ~/.bc_profile file
      n            max number of datapoints (or ceofficients) to display; default is %s

options:
  -?   --help        show this help info and exit
  -A   --all         display the ceofficient matrices (--coeff) followed by the timeseries
  -C   --coeff       display the ceofficient matrices instead of the time series values
  -D   --debug       turn all debugging on by overriding debug settings in ~/.bc_profile file
  -i   --index       list the index for the database and exit
  -I   --intensities include display of time series XY plot intensities (useful for XY plot of lumpy series)
       --RFORMAT     dump the time series values in a format suitable for by R (n is ignored)
                     for lumpies: Xn=values On=origvalues Ln=binaryvalues
  -M   --monitor     turn on resource monitoring
  -o   --brieforphan brief report on orphaned time series for each coefficient matrix in the database
  -O   --orphan      report on orphaned time series for each coefficient matrix in the database
  -t   --tssid n     show the time series set whose seriessetid is n instead of the first one in the database
 --n   --nonorm      do not display the normalised timeseries values; just show the real values
 --r   --noreal      do not display the real timeseries values; just show the normalised values

NOTE: Lumpy series display an extra line after the values: the original values before zero correction.
      Note that intensities are always shown for lumpies.

TODO: dump the derived coefficient matrices (-C or -A options)
""" % (sys.argv[0], sys.argv[0], Showxy.DEFAULT_DATAPOINTS)

    @staticmethod
    def main():
        clargs = dict(debug=False, norm=True, real=True, dbfile=None, n=None, coeff=False, intensities=False, RFORMAT=False, all=False, listindex=False, seriessetid=None, orphan=False, brief=False);
        ai = 1
        while ai < len(sys.argv):
            arg = sys.argv[ai]
            ai += 1
            if arg == "-?" or arg == "--help":
                Showxy.help()
                sys.exit(1)
            elif arg == "-A" or arg == "--all":
                clargs['all'] = True
                clargs['n'] = 1000000
            elif arg == "-C" or arg == "--coeff":
                clargs['coeff'] = True
            elif arg == "-D" or arg == "--debug":
                clargs['debug'] = True
            elif arg == "-E" or arg == "--export":
                clargs['export'] = True
            elif arg == "-i" or arg == "--index":
                clargs['listindex'] = True
            elif arg == "-I" or arg == "--intensities":
                clargs['intensities'] = True
            elif arg == "-t" or arg == "--tssid":
                if ai >= len(sys.argv): raise Exception("%s missing n: try --index to see an index of the database and a list of the tssids" % arg)
                clargs['seriessetid'] = int(sys.argv[ai])
                ai += 1
            elif arg == "-M" or arg == "--monitor":
                ConciseMonitor.enable(True)
            elif arg == "--n" or arg == "--nonorm":
                clargs['norm'] = False
            elif arg == "-o" or arg == "--brieforphan":
                clargs['orphan'] = True
                clargs['brief'] = True
            elif arg == "-O" or arg == "--orphan":
                clargs['orphan'] = True
                clargs['brief'] = False
            elif arg == "--RFORMAT":
                clargs['RFORMAT'] = True
            elif arg == "--r" or arg == "--noreal":
                clargs['real'] = False
            elif clargs['dbfile'] == None:
                clargs['dbfile'] = arg
            elif clargs['n'] == None:
                clargs['n'] = int(arg)
            else:
                raise Exception, "unrecognised arg: %s" % arg
        showxy = Showxy(**clargs)

if __name__ == '__main__':
    Showxy.main()
