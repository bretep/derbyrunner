#! /usr/bin/env python
################################################################################
##
##  mktest.py
##
##  Copyright (c) 2010 Arbor Networks, Inc.
##  All rights reserved. Proprietary and confidential.
##
##  $Id$
##
################################################################################
import optparse
import os
import os.path
import re
import subprocess
import sys
import time
import unittest

##############################################################################
##
##  main
##
##############################################################################
if __name__ == '__main__':
    heats = []
    for x in sys.stdin:
        x = x.strip()
        if x:
            vals = x.split('\t')
            n = vals[0]
            cars = [int(z.strip()) for z in vals[1:]]
            heats.append(cars)

    nCars = len(heats)
    nLanes = len(heats[0])
    print str((nLanes, nCars, 0,0,0)) + ' : ' + str(heats) + ','
