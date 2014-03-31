#!/usr/bin/env python

#################################################################################################################################################################
#                                                                                                                                                               #
# Brand Communities User Attributes                                                                                                                             #
#                                                                                                                                                               #
#################################################################################################################################################################

from PySide.QtGui import *
import os
##import bc##not required
import re

class Constants:
    def __init__ (self):
        # Define some constants to query the facilitiesKey
        self.FACILITIES_TAB_CENTRIFUGE               = 0x80000000
        self.FACILITIES_TAB_NETWORK                  = 0x40000000
        self.FACILITIES_TAB_COMMUNITIES              = 0x20000000
        self.FACILITIES_TAB_XY                       = 0x02000000
        self.FACILITIES_TAB_ANALYSIS                 = 0x01000000
        self.FACILITIES_TAB_LAG                      = 0x00800000

        self.FACILITIES_TOOL_SELECTIONTREE           = 0x00600000
        self.FACILITIES_TOOL_TIMEDIMENSION           = 0x00400000
        self.FACILITIES_TOOL_COMMONCONTROLS          = 0x00200000
        self.FACILITIES_TOOL_LAYOUTCONTROLS          = 0x00100000
        self.FACILITIES_TOOL_SEEKNODE                = 0x00080000
        self.FACILITIES_TOOL_XYASSOCIATIONS          = 0x00020000

        self.FACILITIES_FILE_OPEN                    = 0x00008000
        self.FACILITIES_FILE_SAVECONFIGURATION       = 0x00001000
        self.FACILITIES_FILE_SAVECONFIGTOFILE        = 0x00000800
        self.FACILITIES_FILE_LOADCONFIGFROMFILE      = 0x00000200
        self.FACILITIES_FILE_COMMANDLINE             = 0x00000100

        self.FACILITIES_ANALYSIS_SOURCE              = 0x00000090
        self.FACILITIES_ANALYSIS_TARGET              = 0x00000080 
        self.FACILITIES_ANALYSIS_ORIGINAL            = 0x00000060
        self.FACILITIES_ANALYSIS_AVERAGE             = 0x00000040
        self.FACILITIES_ANALYSIS_TREND               = 0x00000020
        self.FACILITIES_ANALYSIS_ELASTICITY          = 0x00000010
        self.FACILITIES_ANALYSIS_RULEBASED           = 0x00000008
        self.FACILITIES_ANALYSIS_LAG                 = 0x00000006
        self.FACILITIES_ANALYSIS_FUTURE              = 0x00000004
        self.FACILITIES_ANALYSIS_ADDANDDELETE        = 0x00000002
        self.FACILITIES_ANALYSIS_DROPONCOMBOBOX      = 0x00000001

        self.profileFilePath = os.path.expanduser('~/.bc_profile')
        self.referenceFilePath = ('.bc_profile')
    def _adopt_ (self, fileHandle):
        # Rewind the file to the beginning
        fileHandle.seek (0)

        while True:
            _line = fileHandle.readline ()

            if not _line:
                break

            exec (_line)
    def _writeProfile_ (self, path):
        try:
            _fileHandle = open (self.profileFilePath, 'r')
        except:
            print 'Warning: Profile update failed to open profile'
            return True

        try:
            _sourceCode = _fileHandle.read ()
        except:
            print 'Warning: Profile update failed to read profile'
            _fileHandle.close ()
            return True
            
        # Update the databasePath constant in the profile
        _pathMatch = re.search ("""^ *self\.databasePath *= *[ru]*["]([^"]*)["]""", _sourceCode, re.M)

        if _pathMatch:
            _sourceCode = _sourceCode [:_pathMatch.span (1)[0]] + path + _sourceCode [_pathMatch.span (1)[1]:]
        else:
            print 'Warning: Unable to update database path name in profile file. Profile not updated.'
            _fileHandle.close ()
            return True

        _fileHandle.close ()

        try:
            _fileHandle = open (self.profileFilePath, 'w')
        except:
            print 'Warning: Profile update failed to open profile for writing'
            return True

        try:
            _fileHandle.write (_sourceCode)
            None
        except:
            print 'Warning: Profile update failed to update profile'
            _fileHandle.close ()
            return True
        
        _fileHandle.close ()
        return False
    def _makeNewProfile_ (self):
        try:
            _sourceFileHandle = open (self.referenceFilePath, 'r')
        except:
            print 'Warning: Failed to open reference profile'
            return True

        try:
            _sourceCode = _sourceFileHandle.read ()
        except:
            print 'Warning: Failed to read reference profile'
            _sourceFileHandle.close ()
            return True
            
        try:
            self._adopt_ (_sourceFileHandle)
        except:
            print 'Warning: Failed to adopt reference profile'
            _sourceFileHandle.close ()
            raise

        try:
            _targetFileHandle = open (self.profileFilePath, 'w')
        except:
            print 'Warning: Failed to open working profile'
            _sourceFileHandle.close ()
            return True

        try:
            _targetFileHandle.write (_sourceCode)
        except:
            print 'Warning: Failed to write working profile'
            _sourceFileHandle.close ()
            _targetFileHandle.close ()
            return True
        
        _sourceFileHandle.close ()
        _targetFileHandle.close ()
        return False
    def _load_ (self):
        if os.path.exists (self.profileFilePath): 
            try:
                _sourceFileHandle = open (self.profileFilePath, 'r')
            except:
                print 'Warning: Failed to open working profile'
                return True
                
            try:
                self._adopt_ (_sourceFileHandle)
            except:
                _sourceFileHandle.close ()
                raise

            _sourceFileHandle.close ()
            return False
        else:
            if self._makeNewProfile_ ():
                print 'Warning: Failed to make working profile'
                return True
            
if __name__ == '__main__':
    print ('### constants ' + '#' * 116)

    _a = Constants ()
    _a._load_ ()

    for _constant in dir (_a):
        if '_' not in _constant:
            try:
                print '# %30s = %-93.93s #' % (_constant, eval ('_a.' + _constant))
            except:
                print '# %30s = <undefined> %-81.81s #' % (_constant, '')

    print ('#' * 130)
