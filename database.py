#!/usr/bin/env python

########################################################################################
#
#       Database(sqlite3file)
#
#       sqlite3file is the path to an sqlite3 database file
#
#       CAVEAT: transactions are the default for databases in python: don't forget to commit
#
#       Schema V4.000 (20110606)
#
#       CREATE TABLE coeff(coeffid INTEGER PRIMARY KEY AUTOINCREMENT, seriessetid INTEGER);
#       CREATE TABLE coeffvalue(coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#       CREATE TABLE config(configid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, pickle BLOB);
#       CREATE TABLE dict(dictid INTEGER PRIMARY KEY AUTOINCREMENT, client TEXT, clientid INTEGER, key TEXT, value TEXT);
#       CREATE TABLE dictclient(classname TEXT, client TEXT, PRIMARY KEY (classname, client));
#       CREATE TABLE event(eventid INTEGER PRIMARY KEY AUTOINCREMENT, startdate TEXT, enddate TEXT, description TEXT, displaytype INTEGER, fademonths INTEGER);
#       CREATE TABLE series(seriesid INTEGER PRIMARY KEY AUTOINCREMENT, seriessetid INTEGER);
#       CREATE TABLE seriesset(seriessetid INTEGER PRIMARY KEY AUTOINCREMENT);
#       CREATE TABLE seriesvalue(seriesid INTEGER, timeid INTEGER, value REAL, PRIMARY KEY (seriesid, timeid));
#       CREATE TABLE time(timeid INTEGER PRIMARY KEY AUTOINCREMENT, seriessetid INTEGER, time TEXT);
#       CREATE TABLE version(number REAL, date TEXT, description TEXT);
#       
#       Schema V4.021 (20111025) optional derived coeffvalue tables created on demand
#
#       CREATE TABLE coeffbest       (coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#       CREATE TABLE coeffsecondary  (coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#       CREATE TABLE coeffdirection  (coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#       CREATE TABLE coeffnorm       (coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#       CREATE TABLE coeffinvertnorm (coeffid INTEGER, seriesid1 INTEGER, seriesid2 INTEGER, coeff REAL);
#
#       CREATE UNIQUE INDEX coeffbest_coeffid_seriesid1_seriesid2       ON coeffbest       (coeffid,seriesid1,seriesid2);
#       CREATE UNIQUE INDEX coeffsecondary_coeffid_seriesid1_seriesid2  ON coeffsecondary  (coeffid,seriesid1,seriesid2);
#       CREATE UNIQUE INDEX coeffdirection_coeffid_seriesid1_seriesid2  ON coeffdirection  (coeffid,seriesid1,seriesid2);
#       CREATE UNIQUE INDEX coeffnorm_coeffid_seriesid1_seriesid2       ON coeffnorm       (coeffid,seriesid1,seriesid2);
#       CREATE UNIQUE INDEX coeffinvertnorm_coeffid_seriesid1_seriesid2 ON coeffinvertnorm (coeffid,seriesid1,seriesid2);
#
############################################################################################

import os, sqlite3, stat, sys

from application import Application

class Database:

    def __init__(self,sqlite3file,*args):
        must_exist = len(args) < 1 or not args[0]
        skip_version_check = len(args) < 2 or not args[1]
        if must_exist and not os.path.exists(sqlite3file): raise Exception, "Database: sqlite3 file %s not found" % sqlite3file
        self.app = Application.the_app
        self.sqlite3filepath = sqlite3file
        self.conn = sqlite3.connect(sqlite3file)
        self.curs = self.conn.cursor()
        if skip_version_check:
            self._version, self._versiondate, self._versiondescription = 0.0, os.stat(sqlite3file)[stat.ST_MTIME], "not a BC database"
        else:
            versiontablefound = self.selectColumn("SELECT name FROM sqlite_master WHERE type='table' AND name='version'")
            if len(versiontablefound) == 0: raise Exception, "Database file %s is not compatible - the version table is missing" % sqlite3file
            for row in self.selectRows("SELECT number,date,description FROM version"):
                self._version, self._versiondate, self._versiondescription = row
        self.log("Database: connected to sqlite3 database file %s, v%s" % (self.filepath(),self.version()))

    def connection(self):
        return self.conn

    def cursor(self):
        return self.curs

    def version(self):
        return self._version

    def versiondate(self):
        return self._versiondate

    def versiondescription(self):
        return self._versiondescription

    def filepath(self):
        return self.sqlite3filepath

    def basename(self):
        return os.path.basename(self.filepath())

    def commit(self):
        self.conn.commit()

    def execute(self,sql,*params):
        self.log("Database.execute(%s,%s)" % (sql,list(params)))
        self.curs.execute(sql,list(params))
        self.commit()

    def execute_sans_commit(self,sql,*params):                          # don't forget to call commit() when you are done
        self.log("Database.execute(%s,%s)" % (sql,list(params)))
        self.curs.execute(sql,list(params))

    def log(self,message):
            self.app.logdb(message)

    def selectValue(self,sql,*params):
        self.curs.execute(sql,list(params))
        once = True
        row = [ None ]
        for row in self.curs.fetchall():
            if not once: raise Exception, "Database.selectValue(%s,%s) returned more than one row" % (sql,list(params))
            if len(row) > 1: raise Exception, "Database.selectValue(%s,%s) returned %s columns, not one" % (sql,list(params),len(row))
            once = False
        if row != None:
            self.log("Database.selectValue(%s,%s) = %s" % (sql,list(params), row[0]))
        else:
            self.log("Database.selectValue(%s,%s) returns nothing" % (sql,list(params)))
        return row[0]

    def selectColumn(self,sql,*params):
        self.curs.execute(sql,list(params))
        column = [ ]
        for row in self.curs.fetchall():
            if len(row) > 1: raise Exception, "Database.selectColumn(%s,%s) returned %s columns, not one" % (sql,list(params),len(row))
            column.append(row[0])
        self.log("Database.selectColumn(%s,%s) = %s" % (sql,list(params), column))
        return tuple(column)

    def selectRows(self,sql,*params):
        self.curs.execute(sql,list(params))
        rows = self.curs.fetchall()
        self.log("Database.selectRows(%s,%s) = %s" % (sql,list(params), rows))
        return rows

    sequence_tablename = "sqlite_sequence"

    def sequenceid(self,tablename):     # returns the largest AUTOINCREMENT primary key for the given table
        return int(self.selectValue("SELECT seq FROM %s WHERE name=?" % self.sequence_tablename,tablename))

    def stored_schema(self):            # returns a dict of { tablename: None }
        schema = dict()
        # get sqlite tables: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
        # get sqlite table metadata: PRAGMA table_info(tablename) ===> <colnum,colname,coltype,colisnull,coldefault>
        for tablename in self.selectColumn("SELECT name FROM sqlite_master WHERE type='table'"):
            schema[tablename] = None
        return schema

    @staticmethod
    def tunit(verbose):

        app = Application(None,"TestDatabase",verbose,True)

        testdb = sqlite3.connect(":memory:")
        testnulls = testdb.cursor()
        testnulls.execute("CREATE TABLE testnull(name,addr)")
        testnulls.execute("INSERT INTO testnull VALUES('rick','aus')")
        testnulls.execute("INSERT INTO testnull VALUES('rick',NULL)")
        testnulls.execute("INSERT INTO testnull VALUES(NULL,'aus')")
        testnulls.execute("INSERT INTO testnull VALUES(NULL,NULL)")
        testnulls.execute("SELECT * FROM testnull")    
        results = testnulls.fetchall()
        for row in results:
            assert len(row) == 2
        assert results[0][0] == "rick" and results[0][1] == "aus"
        assert results[1][0] == "rick" and results[1][1] == None 
        assert results[2][0] == None   and results[2][1] == "aus"
        assert results[3][0] == None   and results[3][1] == None 
        testdb.close()

        conn = sqlite3.connect(app.testDbFilePath)
        curs = conn.cursor()
        curs.execute("CREATE TABLE IF NOT EXISTS addrbook(name, address, phone)")
        curs.execute("DELETE FROM addrbook");
        curs.close()
        conn.commit()
        conn.close()

        addrbook = [
            ( "andy",   "Helsinki FI",      "+77 8888 8888"   ),
            ( "doug",   "Forster NSW AU",   "+61 2 5532 4343" ),
            ( "johnno", "Mudgee NSW AU",    "+61 2 6666 1234" ),
            ( "rick",    "Ballina NSW AU",    "+61 2 3456 2321" ),
        ]

        db = Database(app.testDbFilePath)
        for addr in addrbook:
            db.execute("INSERT INTO addrbook VALUES(?,?,?)",*addr)

        count = db.selectValue("SELECT COUNT(*) FROM addrbook")
        if count != len(addrbook): raise Exception, "expected %d rows in database %s - found %s" % (len(addrbook),dbfile,count)

        phones = db.selectColumn("SELECT phone FROM addrbook ORDER BY name")
        if len(phones) != len(addrbook): raise Exception,"expected %d phone numbers in database %s - found %s" % (len(addrbook),dbfile,len(phones))

        rows = db.selectRows("SELECT * FROM addrbook ORDER BY name")
        if len(rows) != len(addrbook): raise Exception, "expected %d rows in database %s - found %s" % (len(addrbook),dbfile,len(rows))

        i = 0
        for row in rows:
            if row != addrbook[i]: raise Exception, "expected row[%s] to be %s in database %s - found %s" % (i,addrbook[i],dbfile,row)
            i += 1
        db.commit()    

        print "Database okay"

        
if __name__ == '__main__':
    Database.tunit(len(sys.argv) > 1)

