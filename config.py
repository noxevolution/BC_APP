#!/usr/bin/env python

####################################################################################
#
#       Config(name [,Database])        if Database is provided, load the named config
#
#       CREATE TABLE config(configid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, pickle BLOB);
#
####################################################################################

from database import *
import cPickle 

class Config:

    NAME_OF_CURRENT = "___ CURRENT ___"             # store the name of the currently loaded config at this special name

    def __init__(self,name,*args):
        self._name = name
        self._conf = dict()                         # config dict for the given name
        db = len(args) > 0 and args[0]
        if (db):
            pickled = db.selectValue("SELECT pickle FROM config WHERE name=?",name)
            if pickled == None: raise Exception, "Config(%s) not found in database %s" % (name,db.filepath())
            if name == Config.NAME_OF_CURRENT:
                self._conf = { Config.NAME_OF_CURRENT:pickled }
            else:
                self._conf = cPickle.loads(str(pickled))  # important: convert pickled from unicode to ascii string for loads
                self._set_current_name(db,name)

    def _set_current_name(self,db,name):
        db.execute("DELETE FROM config WHERE name=?",Config.NAME_OF_CURRENT)
        db.execute("INSERT INTO config(name,pickle) VALUES(?,?)",Config.NAME_OF_CURRENT,name)

    def keys(self):
        return self._conf.keys()

    def store(self,db):
        db.execute("DELETE FROM config WHERE name=?",self._name)
        db.execute("INSERT INTO config(name,pickle) VALUES(?,?)",self._name,cPickle.dumps(self._conf))
        self._set_current_name(db,self._name)

    @staticmethod
    def current_name(db):
        return db.selectValue("SELECT pickle FROM config WHERE name=?",Config.NAME_OF_CURRENT)

    @staticmethod
    def names(db):
        return list(db.selectColumn("SELECT name FROM config WHERE name != ? ORDER BY name",Config.NAME_OF_CURRENT))

    def __contains__(self, key):
        return key in self._conf

    def __getitem__(self, key, type=None):
        return self._conf[key]

    def __setitem__(self, key, value):
        self._conf[key] = value

    def __delitem__(self, key):
        del self._conf[key]

    def __str__(self):
        return self._conf.__str__()

    def __repr__(self):
        return self._conf.__repr__()

    @staticmethod
    def tunit(verbose):
        app = Application(None,"TestConfig",False,True)

        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            db = Database(sys.argv[1])
            print "Dump of config table from database %s, current name is %s" % (db.filepath(),Config.current_name(db))
            for name in Config.names(db):
                print
                conf = Config(name,db)
                print name
                for key in conf.keys():
                    print "     %-20s = %s" % (key,conf[key])
            return

        dbfile = app.dbFilePath
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]): dbfile = sys.argv[1]
        db = Database(dbfile)

        upper = Config("TESTING-upper")
        upper["a"] = "A"
        upper["b"] = "B"
        upper["c"] = "C"
        upper["z"] = "Z"
        assert upper["a"] == "A"
        assert upper["b"] == "B"
        assert upper["c"] == "C"
        del upper["z"]
        assert not "z" in upper
        upper.store(db)

        upper = Config("TESTING-upper",db)
        assert upper["a"] == "A"
        assert upper["b"] == "B"
        assert upper["c"] == "C"

        struct = Config("TESTING-struct")
        struct["list"] = [10,20,30,-5]
        struct["tuple"] = (-1,-2,-3,0,0,1,-5)
        struct["dict"] = { 1:10, 2:20, 4:44, 'last':-5 }
        struct["nesty"] = dict( a=[1,2,3,4,5], origin=dict(x=2,y=4,z=-5), last=dict(last=-5) )
        struct.store(db)

        struct = Config("TESTING-struct",db)
        assert struct["list"][len(struct["list"])-1] == -5
        assert struct["tuple"][len(struct["tuple"])-1] == -5
        assert struct["dict"]["last"] == -5
        assert struct["nesty"]["last"]["last"] == -5
        assert struct["nesty"]["origin"]["z"] == -5

        objects = Config("TESTING-objects")
        objects["rick"] = ConfTestObject("rick",11,28192,-5)
        objects["andy"] = ConfTestObject("andy",111,-1,-5)
        assert objects["rick"].last() == -5
        assert objects["andy"].last() == -5
        objects.store(db)

        objects = Config("TESTING-objects",db)
        assert objects["rick"].name() == "rick"
        assert objects["andy"].name() == "andy"
        assert objects["rick"].last() == -5
        assert objects["andy"].last() == -5

        try:
            Config("crap0129309123",db)
            assert false
        except:
            pass

        names = Config.names(db)
        assert "TESTING-upper" in names
        assert "TESTING-struct" in names
        assert "TESTING-objects" in names
        db.execute("DELETE FROM config WHERE name IN (?,?,?,?)","TESTING-upper","TESTING-struct","TESTING-objects",Config.NAME_OF_CURRENT)

        print "Config okay"


class ConfTestObject:
    def __init__(self,name,iq,wobble,last): self._name = name; self._last = last
    def __str__(self): return "ConfTestObject(%s,%s)" % (self.name(),self.last())
    def name(self): return self._name
    def last(self): return self._last


if __name__ == '__main__':
    Config.tunit(len(sys.argv) > 1)

