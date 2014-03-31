#!/usr/bin/env python

####################################################################################
#
#        Application( appName, [ verbose [, test_mode ] ] )
#
#        This is the base class for creating a BC application
#
####################################################################################

import constants, os, sys, time
#from parameters import Parameters
from version import Version

class Application:

    applicationVersion          = Version.applicationVersion
    applicationDescription      = Version.applicationDescription
    applicationDate             = Version.applicationDate

    the_app = None

    def __init__(self, root, appName, *args):
        if root is None:
            class ConstantsContainer(object): pass
            root = ConstantsContainer()
            root.constants = constants.Constants()
            root.constants._load_()

        self.root = root

        global the_app

        Application.the_app               = self

        self.verbose_mode                 = len(args) > 0 and args[0] or False
        self.test_mode                    = len(args) > 1 and args[1] or False

        ## obsolete in bc/3.000
        ## self.operatingSystem              = os.uname()[0] == "Darwin" and "Mac OS X" or "Linux"              # one of "Mac OS X", "Linux", "Windows"
        ## self.operatingSystem              = os.name[0] == "Darwin" and "Mac OS X" or "Windows"              # one of "Mac OS X", "Linux", "Windows"
        ## self.homeDirectoryPath            = self.operatingSystem == "Mac OS X" and "/Users" or "/home"
        ## self.userHomeDirectoryPath        = self.homeDirectoryPath + os.sep + self.userName
        ## self.dataDirectoryPath            = self.test_mode and "test_data" or self.userHomeDirectoryPath + os.sep + "bc_data"
        ## self.dataDirectoryPath            = self.test_mode and "test_data" or "bc_data"
        ## self.dataDirectoryPath            = "bc_data"
        ## self.iniFilepath                  = self.dataDirectoryPath + os.sep + "bc.ini"
        ## self.logFilepath                  = self.dataDirectoryPath + os.sep + "bc.log"

        self.applicationName              = appName
        self.iniFilepath                  = os.path.expanduser('~/.bc_profile')
        self.logFilepath                  = os.path.expanduser('~/.bc_log')
        self.bclog                        = file(self.logFilepath,"a")
        self.logstderr                    = self.verbose_mode
        self.userName                     = os.getenv("LOGNAME") and os.getenv("LOGNAME") or os.getenv("USER") and os.getenv("USER") or ""
        self.testDbFilePath               = self.root.constants.databasePath + os.sep + "T.db"

        self.setDbFilePath()

        self.log("")
        self.log("-------------------------------------------------------------------------------------------------------------------")
        self.log("%s begins again @ %s, BC/%s-%s using data in %s" % (
            self.applicationName,
            time.asctime(),
            self.applicationVersion,
            self.applicationDescription,
            self.root.constants.databasePath,
            ))

    def log(self,message):
        print >> self.bclog, message
        if self.logstderr: print >> sys.stderr, message

    def logdb(self,message):
        if self.root.constants.debugDb:
            self.log(message)

    def loggr(self,message):
        if self.root.constants.debugGr:
            self.log(message)

    def logts(self,message):
        if self.root.constants.debugTs:
            self.log(message)

    def logui(self,message):
        if self.root.constants.debugUi:
            self.log(message)

    def setDbFilePath(self):
        self.dbFilePath = os.path.expanduser(self.root.constants.databasePath + os.sep + '?') #self.root.constants.databaseName)

    def UPDATE_WORKSPACE(self,newworkspace):
        self.params.UPDATE("workspace",newworkspace)
        self.setDbFilePath()

    @staticmethod
    def feq(x,y):                                        # float equality test: two floats are 'equal' if abs(relative difference) is with within epsilon
        epsilon = 1e-6
        return abs(x - y) <= abs(epsilon * x)


    @staticmethod
    def tunit(verbose):
        app = Application(None,"TestApplication",verbose,True)
        print "Application okay"


if __name__ == '__main__':
    Application.tunit(len(sys.argv) > 1)

