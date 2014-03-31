#!/usr/bin/env python

####################################################################################
#
#        Dict(db,classname,clientid)
#
#        The above class mimics the interface and behaviour of its Java analogue
#        
####################################################################################

import sys
from application import *
from database import *

class Dict(dict):

    def __init__(self,db,classname,clientid):
        client = self.clientOf(db,classname)            # TODO V5.000 rename client to clientnonce
        for row in db.selectRows("SELECT key,value FROM dict WHERE client=? AND clientid=?",client,clientid):
            self[row[0]] = row[1]

    def get(self,key):          return self[key]
    def getint(self,key):       return int(self[key])
    def getdouble(self,key):    return float(self[key])

    def put(self,key,val):      self[key] = str(val)
    def putbool(self,key,val):  self[key] = '1' if val else ''

    def getbool(self,key):
        if not len(self[key]):
            return False
        v = self[key].lower()
        return not (v=="0" or v=="false" or v=="no" or v=="off")

    KNOWNCLASSES = None

    @staticmethod
    def clientOf(db,classname):
        if Dict.KNOWNCLASSES == None:
            Dict.KNOWNCLASSES = dict()
            for row in db.selectRows("SELECT classname,client FROM dictclient"):
                Dict.KNOWNCLASSES[row[0]] = row[1]
            # print >>sys.stderr,"*Loaded Dict.KNOWNCLASSES=%s" % Dict.KNOWNCLASSES
        if classname not in Dict.KNOWNCLASSES: raise Exception("classname %s not found in dictclient table for database %s" % (classname,db.filepath()))
        return Dict.KNOWNCLASSES[classname]

    @staticmethod
    def tunit(verbose):
        app = Application(None,"TestDict",verbose,True)
        db = Database(app.dbFilePath)
        classname = 'TestDict'
        client = 9819823123
        clientid = 1092323
        tdict = dict(
            databaseName   = "some database.db",
            databasePath   = os.sep + "This is the" + os.sep + "Path" + os.sep + "To" + os.sep + "Enlightenment",
            debugDb        = "True",
            debugGr        = "yes",
            debugTs        = "1",
            debugUi        = "on",
            moveTime       = "3333",
            baseCutoff     = "0.554",
        )
        db.execute("DELETE FROM dictclient WHERE client=?",client)
        db.execute("INSERT INTO dictclient(classname,client) values(?,?)",classname,client)
        db.execute("DELETE FROM dict WHERE client=? AND clientid=?",client,clientid)
        for key in tdict.keys():
            if verbose: print "insert(%s:%s:%s:%s=%s)" % (app.dbFilePath,client,clientid,key,tdict[key])
            db.execute("INSERT INTO dict(client,clientid,key,value) VALUES(?,?,?,?)",client,clientid,key,tdict[key])
        d = Dict(db,classname,clientid)
        for key in tdict.keys():
            assert(key in d)
            assert(d[key] == tdict[key])
            if verbose: print "%s:%s:%s:%s=%s" % (app.dbFilePath,client,clientid,key,d[key])

        print "Dict okay"

if __name__ == '__main__':
    Dict.tunit(len(sys.argv) > 1)

