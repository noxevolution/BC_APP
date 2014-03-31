#!/usr/bin/env python

####################################################################################
#
#       Coefficients(Database, TimeSeriesSet, coeffid)
#
#       Coefficients handles all the coefficient matrices for a given TimeSeriesSet.
#
#       The matrix are named { value best secondary direction norm }.
#       See matrix_names in this module.
#
#       value   is the matrix of coefficients produced by the Jaba Importer
#               and as such is always present in any V4.000 BC database.
#
#       { best secondary direction norm } are matrices derived from value, and
#               as such are automatically created in the Database ONCE only
#
###################################################################################
#
#       CoefficientMatrix(matrixname, Coefficients)
#
#       CoefficientMatrix handles a named N x N square matrix of coefficients for
#       a given coeffid for a given TimeSeriesSet as found in Coefficients.
#       There are multiple CoefficientMatrix in the database for each matrix name
#       for a given coeffid. 
#
#       CoefficientMatrix is currently a subclass of Sparse, i.e. the storage for
#       coefficients in the matrix is always handled in a sparse manner, which saves
#       much in memory storage and greatly improves access time.
#
#       CoefficientMatrix mimics the interface and behaviour of its Java analogue
#       CREATE TABLE coeffvalue(coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#
#       The tablename used by the importer is coeffvalue. The derived coeff tables
#       are named after their matrixname, e.g.
#
#       { coeffbest coeffsecondary coeffdirection coeffnorm }
#
####################################################################################


import sys
from database import *
from dict import *
from sparse import *
from timeseries import *
from monitor import ConciseMonitor

imported_matrix_name            = 'value'                                               # the only original matrix name, from the import
matrix_names                    = 'value best secondary direction norm'.split(' ')      # all matrix names
derived_matrix_names            = [ matname for matname in matrix_names if matname != imported_matrix_name ]

matrix_tablenames               = dict( (matname, 'coeff%s' % matname) for matname in matrix_names )
derived_matrix_tablenames       = dict( (matname, 'coeff%s' % matname) for matname in derived_matrix_names )
derived_matrix_indexnames       = dict( (matname, '%s_coeffid_seriesid1_seriesid2' % derived_matrix_tablenames[matname]) for matname in derived_matrix_names )



####################################################################################
#
#       Coefficients(Database, TimeSeriesSet, coeffid)
#
####################################################################################

class Coefficients(object):

    def __init__(self, db, tss, coeffid, sparse=False):
        resource_usage = ConciseMonitor()

        self.sparse = sparse
        self._N = len(tss)
        self._db = db
        self._tss = tss
        self._coeffid = coeffid
        self._dict = Dict(db,"CoefficientMatrix",coeffid)          # legacy: CoefficientMatrix now refers to Coefficients in the dict for this class
        self._matrices = dict()                                    # all matrices: key is coefficient matrix name

        # public attributes: each of the named CoefficientMatrixs contained in this Coefficients object
        self.value          = self._load('value')                  # original imported coefficients
        self.coeffs         = self.value                           # legacy
        self.best           = self._load('best')                   # best coefficients
        self.secondary      = self._load('secondary')              # secondary coefficients
        self.direction      = self._load('direction')              # direction coefficients
        self.norm           = self._load('norm')                   # normalised coefficients

        resource_usage.report('%s #%s init %s matrices, values.cardinality=%s .fill=%.2f%% .mac=%s' % ('Coefficients', coeffid, len(matrix_names), self.cardinality(), 100*self.fill(), self.maxabscoeff()))

    def N(self):                return self._N
    def isarima(self):          return self._dict.getbool("isarima")
    def isdelta1(self):         return self._dict.getbool("isdelta1")
    def description(self):      return self._dict.get("description")
    def name(self):             return self._dict.get("name")
    def lagmax(self):           return self._dict.getint("lagmax")
    def minpoints(self):        return self._dict.getint("minpoints")
    def topn(self):             return self._dict.getint("topn")

    def values_issymmetrical(self):
        return self._dict.getbool("issymm")

    def coeffid(self):
        return self._coeffid

    def db(self):
        return self._db

    def tss(self):
        return self._tss

    def cardinality(self, matrixname='value'):
        return self._matrices[matrixname].cardinality()

    def fill(self, matrixname='value'):
        return self._matrices[matrixname].fill()

    def getmatrix(self, matrixname='value'):
        return self._matrices[matrixname]

    def issymmetrical(self, matrixname='value'):
        return self._matrices[matrixname].issymmetrical()

    def maxabscoeff(self, matrixname='value'):
        return self._matrices[matrixname].maxabscoeff()

    def readyloop(self, matrixname='value'):
        return (self._matrices[matrixname], self._N)

    def _load(self, matrixname='value'):
        self._matrices[matrixname] = CoefficientMatrix(matrixname, self)
        return self._matrices[matrixname]

    @classmethod
    def timeseriesset_matrix_index(cls,db,seriessetid):     # dict of { coeffid => coeffdict } for each CoefficientMatrix owned by seriessetid
        return dict( (coid,Dict(db,"CoefficientMatrix",coid)) for coid in db.selectColumn("SELECT coeffid FROM coeff WHERE seriessetid=?",seriessetid) )

    @classmethod
    def matrix_index(cls,db,coeffid):                       # dict of { matrixname => None | dict(n, cardinality, fill, maxabscoeff, tablename) }
                                                            #       for each matrixname in a CoefficientMatrix
        res = dict()                                        # the dict value is None if there is no matrix by that name in the database for the given coeffid
        coeffdict = Dict(db,"CoefficientMatrix",coeffid)
        seriessetid = int(db.selectValue("SELECT seriessetid FROM coeff WHERE coeffid=?",coeffid))
        n = int(db.selectValue("SELECT COUNT(*) FROM series WHERE seriessetid=?",seriessetid))
        nsquare = n*n
        ntriangular = n*(n-1)/2
        for matrixname in matrix_names:
            issymm = True                                   # all derived coeff matrices are symmetrical
            if matrixname == 'value':
                try:
                    issymm = coeffdict.getbool('issymm')
                except:
                    pass                                    # there are a few V4.000 databases that do not a 'issymm' entry in the dict :(
            tablename = matrix_tablenames[matrixname]
            try:
                cardinality = int(db.selectValue("SELECT COUNT(*) FROM %s WHERE coeffid=? AND coeff != 0" % tablename,coeffid))
                if issymm:
                    cardinality *= 2
                maxabscoeff = float(db.selectValue("SELECT MAX(ABS(coeff)) FROM %s WHERE coeffid=?" % tablename,coeffid))
                fill = cardinality/float(nsquare)
                assert fill <= 1
                res[matrixname] = dict(n=n, nsquare=nsquare, ntriangular=ntriangular, issymm=issymm, cardinality=cardinality, fill=fill, maxabscoeff=maxabscoeff, tablename=tablename)
            except:
                res[matrixname] = None
        return res


    ## EXAMPLE of speed improvement for CoefficientMatrix: calculate the sum of all coefficients using readyloop()

    def sum_by_rows(self):          ## fastest
        s = 0
        coeffs, n = self.readyloop()
        if self.sparse:
            for i in range(n):
                row = coeffs[i]
                for j in row:
                    s += row[j]
        else:
            for i in range(n):
                row = coeffs[i]
                for j in range(n):      ## note that s += reduce(lambda x, y: x+y, row) is 1.5 times slower!
                    s += row[j]
        return s
 
    def sum_by_cols(self):          ## perhaps 1/3 slower than sum_by_rows()
        s = 0
        coeffs, n = self.readyloop()
        if self.sparse:
            for j in range(n):
                for i in range(n):
                    if j in coeffs[i]:
                        s += coeffs[i][j]
        else:
            for j in range(n):
                for i in range(n):
                    s += coeffs[i][j]
        return s

###################################################################################
#
#       CoefficientMatrix(matrixname, Coefficients)
#
###################################################################################

class CoefficientMatrix(SparseMatrix):    # a read-only SparseMatrix of coefficients
    """ CoefficientMatrix is a SparseMatrix that stores coefficients for a Coefficients instance """

    def __init__(self, matrixname, coefficients):

        init__usage = ConciseMonitor()

        db = coefficients.db()
        tss = coefficients.tss()

        super(CoefficientMatrix,self).__init__(len(tss))

        self._matrixname = matrixname   # matrixname is one of the names in matrix_names
                                        # if matrixname != imported_matrix_name, the matrix is called a derived matrix
                                        # and as such will be created on demand by this constructor if it is not
                                        # found in the database

        try:
            db.cursor().execute("SELECT seriesid1,seriesid2,coeff FROM %s WHERE coeffid=?" % matrix_tablenames[matrixname],[coefficients.coeffid()])
        except:
            assert matrixname != imported_matrix_name
            self._create_all_derived_tables(db)
            db.cursor().execute("SELECT seriesid1,seriesid2,coeff FROM %s WHERE coeffid=?" % derived_matrix_tablenames[matrixname], [coefficients.coeffid()])

        cardinality = 0
        maxabscoeff = 0
        s2o = tss.seriesid2ordinal()
        if matrixname == 'value':
            issymm = coefficients.values_issymmetrical()    # the original imported value matrix may or may not be symmetrical
        else:
            issymm = True                                   # all derived matrices are symmetrical
        for (id1, id2, coeff) in db.cursor().fetchall():
            if id1 not in s2o: raise Exception, "seriesid1=%s not found for coeffid=%s in database %s for matrix %s" % (id1, coefficients.coeffid(), db.basename(), self._matrixname)
            if id2 not in s2o: raise Exception, "seriesid2=%s not found for coeffid=%s in database %s for matrix %s" % (id2, coefficients.coeffid(), db.basename(), self._matrixname)
            if coeff:
                cardinality += 1
                self [s2o[id1]] [s2o[id2]] = coeff
                if issymm:
                    assert s2o[id1] > s2o[id2]
                    cardinality += 1
                    self [s2o[id2]] [s2o[id1]] = coeff
                if abs(coeff) > maxabscoeff:
                    maxabscoeff = abs(coeff)

        self._cardinality = cardinality
        self._fill = cardinality / float(self.N*self.N)
        self._issymmetrical = issymm
        self._maxabscoeff = maxabscoeff

        init__usage.report('%s %s init %s non-zero coeffs %.2f%% mac=%s' % ('CoefficientMatrix', self.matrixname(),  self.cardinality(), self.fill(), self.mac()))

    def cardinality(self):
        return self._cardinality

    def fill(self):
        return self._fill

    def issymmetrical(self):
        return self._issymmetrical

    def mac(self):
        return self._maxabscoeff

    def maxabscoeff(self):
        return self._maxabscoeff

    def matrixname(self):
        return self._matrixname


    @classmethod
    def _create_all_derived_tables(cls, db):
        """ create and populate fresh derived tables in the database for all the derived coefficient matrices -- for all timeseries and all coeffids """

        for matrixname in derived_matrix_names:
            tablename = derived_matrix_tablenames[matrixname]
            indexname = derived_matrix_indexnames[matrixname]
            db_drop_create_usage = ConciseMonitor()
            db.execute("DROP TABLE IF EXISTS %s" % tablename)
            db.execute("DROP INDEX IF EXISTS %s" % indexname)
            db.execute("CREATE TABLE %s(coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL)" % tablename)
            db.execute("CREATE UNIQUE INDEX %s ON %s(coeffid,seriesid1,seriesid2)" % (indexname, tablename))
            db_drop_create_usage.report('DROP AND CREATE TABLE %s and its INDEX' % tablename)

        ninsert = 0
        for seriessetid in db.selectColumn("SELECT seriessetid FROM seriesset"):
            create_usage = ConciseMonitor()
            create_usage.report('CREATING post-import tables ONCE for database %s tssid %s' % (db.basename(), seriessetid))
            o2s = { }                                               # map timeseries' ordinal to seriesid for a given seriessetid
            s2o = { }                                               # and map seriesid to ordinal
            ordinal = 0
            for seriesid in db.selectColumn("SELECT seriesid FROM series WHERE seriessetid=? ORDER BY seriesid", seriessetid):
                o2s[ordinal] = seriesid
                s2o[seriesid] = ordinal
                ordinal += 1
            n = len(o2s)
            for coeffid in db.selectColumn("SELECT coeffid FROM coeff WHERE seriessetid=?", seriessetid):
                coeffdict = Dict(db,"CoefficientMatrix",coeffid)
                try:
                    issymm = coeffdict.getbool('issymm')    # the Coefficients's dict 'issymm' tells us if the original imported coeffvalues matrix is symmetrical
                except:
                    issymm = False                          # there are a few V4.000 databases that do not a 'issymm' entry in the dict :(
                maxabscoeff = 0
                originals = SparseMatrix(n)
                db.cursor().execute("SELECT seriesid1,seriesid2,coeff FROM coeffvalue WHERE coeffid=?",[coeffid])
                for (id1, id2, coeff) in db.cursor().fetchall():
                    if id1 not in s2o:
                        raise Exception("seriesid1=%s not found for coeffid=%s in database %s for coeffvalue" % (id1, coefficients.coeffid(), db.basename()))
                    if id2 not in s2o:
                        raise Exception("seriesid2=%s not found for coeffid=%s in database %s for coeffvalue" % (id2, coefficients.coeffid(), db.basename()))
                    if coeff:
                        originals [s2o[id1]] [s2o[id2]] = coeff
                        if issymm:
                            assert s2o[id1] > s2o[id2]
                            originals [s2o[id2]] [s2o[id1]] = coeff
                        if abs(coeff) > maxabscoeff:
                            maxabscoeff = abs(coeff)
                crumb = 0
                for i in range(n):
                    row = originals[i]
                    for j in range(i):
                        coeff1 = 0 if j not in row else row[j]
                        coeff2 = 0 if i not in originals[j] else originals[j][i]
                        if abs(coeff1) >= abs(coeff2):
                            best, secondary, direction = coeff1, coeff2, 1
                        else:
                            best, secondary, direction = coeff2, coeff1, 2
                        if best:
                            norm = abs(best) / maxabscoeff
                            id1 = o2s[i]
                            id2 = o2s[j]
                            db.execute_sans_commit("INSERT INTO %s(coeffid,seriesid1,seriesid2,coeff) VALUES(?,?,?,?)" % derived_matrix_tablenames['best'],
                                coeffid, id1, id2, best)
                            db.execute_sans_commit("INSERT INTO %s(coeffid,seriesid1,seriesid2,coeff) VALUES(?,?,?,?)" % derived_matrix_tablenames['secondary'],
                                coeffid, id1, id2, secondary)
                            db.execute_sans_commit("INSERT INTO %s(coeffid,seriesid1,seriesid2,coeff) VALUES(?,?,?,?)" % derived_matrix_tablenames['direction'],
                                coeffid, id1, id2, direction)
                            db.execute_sans_commit("INSERT INTO %s(coeffid,seriesid1,seriesid2,coeff) VALUES(?,?,?,?)" % derived_matrix_tablenames['norm'],
                                coeffid, id1, id2, norm)
                            ## create_usage.report('[%s] INSERT INTO {best,norm,direction...} WHERE coeffid=%s i=%s, j=%s' % (crumb, coeffid, i,j ))
                            crumb += 4
                db.commit()
                create_usage = create_usage.report('INSERT INTO {best,norm,direction...} WHERE coeffid=%s, %s INSERT operations tssid %s' % (coeffid,crumb,seriessetid))
                ninsert += crumb

        create_usage.report('CREATE port-import tables complete, %s INSERT operations across all tssids' % ninsert)
        return crumb


###################################################################################
#
#       Utilities
#
###################################################################################

def report_coefficients(db,brief,update):
    if update:
        print 'Ensuring that database %s contains the {best,norm,secondary,directory} derived coefficients' % db.basename()
    else:
        print db.basename()
    ind = '  '
    try:
        index = TimeSeriesSet.index(db)
    except:
        print '*** Skipping %s - not a valid BC 4.000 database' % db.basename()
    if update:
        TimeSeriesSet(db, index.keys()[0])    # force creation of all derived matrices in db if not present
    slice_index = TimeSeriesSet.slice_index(db)
    for seriessetid in sorted(index.keys()):
        try:
            tss_minfo = Coefficients.timeseriesset_matrix_index(db,seriessetid)  # dict of { coeffid => coeffdict } 
        except:
            print '*** Skipping %s - not a valid BC 4.000 database' % db.basename()
            return
        sinfo = slice_index[seriessetid]
        print '%sTimeSeriesSet %s from %s to %s, %s X %s' % (ind,
            seriessetid, sinfo['starttime'], sinfo['endtime'], sinfo['duration'], sinfo['interval']),
        if not brief:
            print
        totalmat = 0
        foundmat = 0
        for coeffid in sorted(tss_minfo.keys()):
            if not brief:
                print '%s%sCoefficientMatrix %s description=%s' % (ind,ind,coeffid,tss_minfo[coeffid]['description'])
            minfo = Coefficients.matrix_index(db,coeffid)   # dict of { matrixname => None | dict(n, cardinality, fill, maxabscoeff, tablename) }
            for matrixname in matrix_names:     # report in the order of matrix_names, not minfo.keys()
                totalmat += 1
                goodies = minfo[matrixname]
                if goodies:
                    foundmat += 1
                    fill = '%.2f' % (goodies['fill'] * 100)
                    if not brief:
                        print '%s%s%s%-20s n=%s n^2=%s ntriang=%s issymm=%s cardinality=%s fill=%s%% maxabscoeff=%s tablename=%s' % (ind,ind,ind,
                            matrixname,goodies['n'],goodies['nsquare'],goodies['ntriangular'],goodies['issymm'],goodies['cardinality'],fill,goodies['maxabscoeff'],goodies['tablename'])
                else:
                    if not brief:
                        print '%s%s%s%-20s *** DOES NOT YET EXIST' % (ind,ind,ind,matrixname)
        if brief:
            if foundmat == totalmat:
                print ' - found all %d of %d coeff matrices as required' % (foundmat, totalmat)
            else:
                print ' - *** only found %d of %d coeff matrices' % (foundmat, totalmat)


def utility():
    ConciseMonitor.enable(False)
    brief = False
    debug = False
    update = False
    default_dbfile = Application(None,"CoefficientMatrix Utility",False,True).dbFilePath
    dbfiles = [ ]
    for arg in sys.argv[1:]:
        if arg == '--help' or arg == '-?':
            print '%s: display coefficient matrix metrics in one or more BC database files, optionally installing post-import coefficient matrices as well' % sys.argv[0]
            print
            print 'use: %s [ option ]... [ databasefile ]...'
            print
            print '      databasefile    path to a BC databasefile; default is the dbfile found in .bc_profile:'
            print '                      %s' % default_dbfile
            print
            print 'options:'
            print ' -? --help            print the help information and exit'
            print ' -D --debug           turn on debugging'
            print ' -B --brief           brief display'
            print ' -M --monitor         turn on resource monitoring'
            print ' -U --update          update databases with any missing post-import coefficient matrices'
            sys.exit(1)
        elif arg == '-B' or arg == '--brief':
            brief = True
        elif arg == '-D' or arg == '--debug':
            debug = True
        elif arg == '-M' or arg == '--monitor':
            ConciseMonitor.enable(True)
        elif arg == '-U' or arg == '--update':
            update = True
        elif arg == '-D' or arg == '--debug':
            debug = True
        else:
            Database(arg)   # raise exception now if not a valid db file
            dbfiles.append(arg)
    if not dbfiles:
        dbfiles.append(default_dbfile)
    for dbfile in dbfiles:
        resuse = ConciseMonitor()
        db = Database(dbfile)
        report_coefficients(db,brief,update)
        resuse.report('%s finished' % db.basename())

if __name__ == '__main__':
    utility()

