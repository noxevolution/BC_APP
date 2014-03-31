#!/usr/bin/env python

####################################################################################
#
#        Version - application revision history
#
####################################################################################

import sys

#   Revision History
#   
#    VERSION_  DESCRIPTION                      DATE       DETAILS
#    NUMBER
#   
#    0.001     alpha1                           20101215   alpha version - menus, main window
#    0.002     alpha2                           20101217   alpha2 - persistence - store
#    0.003     alpha3                           20101218   alpha3 - persistence - indexes
#    0.004     alpha4                           20101218   alpha4 - persistence - retrieve, Dump utility
#    0.005     alpha5                           20101219   alpha5 - Excel support, CSV support
#    0.006     alpha6                           20110107   alpha6 - cleanup code, add multiple varieties of TimeSeriesSets to SampleTimeSeriesSet
#    0.007     alpha7                           20110108   alpha7 - moved to tour
#    0.008     alpha8                           20110111   alpha8 - new utility Spread2Tab
#    0.112     XY-demo                          20110228   Andy's XY plot is ready to play with
#    0.113     layout-types                     20110228   layout types - return to Andy on 20110228
#    0.114     anim-types                       20110303   animation types from Andy
#    0.115     locus                            20110305   locus on XY from Andy
#    1.000     split-disparatemodel             20110309   single combined split window for Universe + XY; new disparate timeline data model
#    1.002     lumpy                            20110312   support for lumpy time series in data model, Importe, BC app
#    1.003     XYpopulate                       20110316   AC adds XY-populate (right click in Universe), profile, mouse panning and more
#    1.004     radial+ego                       20110317   added radial and ego graphing suing new dependencies GraphViz + NetworkX
#    1.005     new layout                       20110322   AC's new layout algorithm
#    1.006     Doug enhancement                 20110324   AC's enhancements prompted by Doug
#    1.007     Universe declustering            20110327   AC's enhancements
#    1.008     Universe declustering disc       20110328   AC's enhancements
#    1.009     Centering from the selection lst 20110329   AC
#    2.000     lagcorr+arima+config             20110329   R used for auto arima corrections and lagged ccf - new data model; save config to database
#    2.001     tree+drag+drop                   2011-04-04 AC Drag&drop, category tree, saving of state, dropbox - preissue
#    2.002     tree+drag+drop                   2011-04-04 AC Drag&drop, category tree, saving of state, dropbox
#    2.003     node colours+help		        2011-04-18 AC Node colours, help text, fixed tree bug, better db path handling
#    2.004     UI and UI performance            2011-04-23 AC Many changes to GUI, principally concerned with performance. Some UI improvements
#    2.005     Interim version w/o hang         2011-04-27 AC version for Doug to try which doesn't hang
#    2.006     Help available, Scale crosslinks 2011-04-30 AC help working, indirect renamed to "Scale crosslinks" and now working
#    3.000     regressions+weeklies+events      2011-05-03 RW regressions, weekly time series, events in the data model
#    3.001     scaling (interim)		        2011-05-06 AC Scaling so we can see what's happening with regressions
#    3.002     delta1+dict                      2011-05-07 RW delta1 - correlation using first order deltas of time series values; dict table replaces label table
#                                                          RW as well, BC now handles empty time series
#    3.003     1stOrder+regression corrected    2011-05-09 AC problems with nodes disappearing from tss have been corrected. Now have visualisation of dx/dy fns.
#    3.004     GUI enhancements                 2011-05-22 AC tree colours, corrected node tooltips, single-click node hiding, bubble label editing, bug fixes...
#    4.000     manyregressors-prerelease        2011-06-06 RW remove many tables and replace with unified coeff table which stores many regression matrices
#	           many regressors & social network 2011-06-13 AC social network graph
#    4.003     layout algorithm bug correction  2011-06-14 AC correction of 3 bugs in new social network layout algorithm
#    4.004     dictionary bugfix                2011-06-14 RW force reload of dictclients when fresh time series set is loaded
#    4.005     advanced zoom + bug fix on hide  2011-06-24 AC Zoom now maintains node sizes. Arrowheads better. Can now hide all selected nodes
#    4.006     inclusion of cloud layout        2011-06-30 AC Added cloud layout plus some GUI enhancements
#    4.007     clustering evaluation            2011-07-04 AC Added basic clustering layout for evaluation and development
#    4.008     node inversion                   2011-07-07 AC Node inversion, hide selected nodes, tree cleaning, clustering improvements, undo hide, values on sliders
#    4.009     General cleanup and XY features  2011-07-23 AC XY Plot usability improvements, tabbed universes, consistency, added tools
#    4.010     Inverse centrifuge               2011-07-27 AC Added Nicholas' inverse centrifuge and zeroStrip slider
#    4.011     Galaxy usability improvements    2011-08-03 AC Galaxy is quicker and doesn't block the UI (except during Qt repaints with silly numbers of lines)
#    4.012     Bug fixes (1)                    2011-08-11 AC Fixing of various detailed bugs
#    4.013     Small enhancements and fixes     2011-08-22 AC Addition of many small enhancements
#    4.014     Small cosmetic changes           2011-09-23 AC Change of names of some tabs, suppression of some warnings, tidy event reporting
#    4.015     Basic time dimension             2011-10-15 AC Added functionality for a basic implementation of the time dimension w/o XY Plot interaction
#    4.016     Memory optimisation              2011-10-16 RW Adapt to optimised database format from Importer (optimised and unoptimised are both V4.000 Database compatible)
#    4.018     Internal interim version         2011-10-22 AC Internal release incorporating changes from AC and RW
#    4.019     Resource monitor                 2011-10-22 RW ConciseMonitor() for reporting on resource usage (see monitor.py)
#    4.020     Internal interim handover vers.  2011-10-24 AC Pre Rick modifications
#    4.021     Model Optimisation               2011-10-26 RW optimise data model: on-demand precalculated coeff matrices, coefficients (space+time opt), plus postimp.py (time opt)
#    4.022     Interim                          2011-10-28 from AC 20111028               
#    4.023     Coefficients                     2011-10-29 RW new Coefficients class fixes bug in loading of derived coeff tables, i.e. the Post Import tables
#    4.024     Memory footprint reduction       2011-11-03 AC Significant reduction of memory requirements. Centrifuge and Communities speed enhancements. Several GUI enhancements.
#    4.025     Clustering speed                 2011-11-05 AC Significant improvement of clustering speed. Plus some small fixes.
#    4.026     Configuration files              2011-11-15 AC New config. file system, XY undo and lots of small fixes
#    4.027     Interim - bug fixes 1            2011-11-16 AC Bug fixes, ongoing testing...
#    4.028     Analytics added                  2011-11-21 AC Added analytics graphs
#    4.029     Analytics refinements            2011-11-25 AC Added zoom, pan, an x-axis, data points, etc. and a fourier transform function
#    4.030     Facilities management            2011-12-05 AC Added facilities management to .bc_profile
#    4.031     Amar's Forecasting prototype     2012-05-03 AC Added Amar's initial forecasting algorithm. Testing only - works with only one database
#    4.032     Forecasting interface tweaks     2012-05-22 AC Forecasting now works with badly-formed databases, added time slider to all graphs, enabled forecasting interface features
#    4.033     Added centrifuge printing        2012-05-30 AC Added two buttons in centrifuge for hard copy printing of nodes
#    4.034     Forecast from node or tree       2012-06-04 AC Can now forecast any node from the tree or the centrifuge
#    4.035     Better spheres                   2012-06-13 AC Spheres in Centrifuge, Network and Communities are now more 3-D in appearance
#    4.036     Forecasting improvement          2012-07-11 AC Integration of Amar's new forecaster
#    4.037     Random Foreset Forecasting       2013-04-01 AD New Random Forest Forecasting Algorithm
#    4.038     Forecast from Centrfuge          2013-04-16 AD Updated Forecast from Centrifuge functionality
#    4.039     New Skin                         2013-05-23 AD Updated Skin for Domino and Communities
#    4.040     Modified Message                 2013-05-27 AD Updated message for Domino and Communities
#    4.041     Debugged multiple db issue       2013-05-29 AD Debugged issue related to loading multiple dbs
#    4.042     Add from Centrifuge for XY       2013-06-23 AD Add from Centrifuge for XY


class Version:

    @staticmethod
    def tunit(verbose):
        print "Version %s/%s (%s) okay" % (Version.applicationVersion,Version.applicationDescription,Version.applicationDate)

    applicationVersion = 4.042
    applicationDescription = "Brand Communities"
    applicationDate = "2013-06-23"


if __name__ == '__main__': Version.tunit(len(sys.argv) > 1)
