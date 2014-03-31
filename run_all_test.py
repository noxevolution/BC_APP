#!/usr/bin/env python

###########################################################################################
#
#        Run_all_tests: the "static" class to run all the BC python packages' tunit() tests
#
###########################################################################################

import sys

# the 'c' classes: controller stuff

from application import *

# the 'm' classes: data model

from config import *
from database import *
from dict import *
from sparse import *
from timepoint import *
from timeseries import *
from version import *

class Run_all_tests:                    # "static" class since it only contains one static method

    @staticmethod
    def main(verbose):

        ##  this would be nice:
        ##    for cls in a.__init__.__all__:
        ##        cls.tunit(verbose)

        # test the c classes

        Application.tunit(verbose)

        # test the m classes

        Config.tunit(verbose)
        Database.tunit(verbose)
        Dict.tunit(verbose)
        SparseMatrix.tunit(verbose)
        TimePoint.tunit(verbose)
        TimeSeriesSet.tunit(verbose)
        Version.tunit(verbose)

if __name__ == '__main__':
    Run_all_tests.main(len(sys.argv) > 1)
