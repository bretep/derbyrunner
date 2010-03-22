#! /usr/bin/env python
################################################################################
##
##  ppngen.py
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

################################################################################
##  PPN_PARMS holds magic numbers derived from the original Young and Pope
##  javascript code.  In python this is represented as a big tuple indexed
##  by number of lanes. Each lane tuple contains tuples for a number of cars.
##  Each car tuple contains:
##
##  (min, max, (magic), (magic))
##
##  min -- Minimum number of cars this tuple applies to
##  max -- Maximum number of cars this tuple applies to
##  magic -- Magic values from Young and Pope
################################################################################
PPN_PARMS = (
    # Lanes = 0
    None,

    # Lanes = 1
    None,

    # Lanes = 2
    (
        (2, 2, (3, 3), (1, 1)),
        (3, 3, (2, 3), (2, 1)),
        (4, 4, (1, 1), (3, 2)),
        (5, 5, (1, 2, 1, 3), (3, 4, 2, 1)),
        (6, 6, (1, 1), (2, 5)),
        (7, 7, (1, 1, 2, 1, 1, 3), (3, 2, 1, 4, 5, 6)),
        (8, 8, (1, 1, 1), (3, 2, 1)),
        (9, 9, (1, 1, 1, 2, 1, 1, 1, 3), (4, 3, 2, 1, 5, 6, 7, 8)),
        (10, 10, (1, 1, 1, 1), (4, 3, 2, 1)),
        (11, 11, (1, 1, 1, 1, 2, 1, 1, 1, 1, 3), (5, 4, 3, 2, 1, 6, 7, 8, 9, 10)),
        (12, 12, (1, 1, 1, 1, 1), (5, 4, 3, 2, 1)),
        (13, 13, (1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 3), (6, 5, 4, 3, 2, 1, 7, 8, 9, 10, 11, 12)),
        (14, 14, (1, 1, 1, 1, 1, 1), (6, 5, 4, 3, 2, 1)),
        (15, 15, (1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1), (7, 6, 5, 4, 3, 2, 1, 8, 9, 10, 11, 12)),
        (16, 16, (1, 1, 1, 1, 1, 1, 1), (7, 6, 5, 4, 3, 2, 1)),
        (17, 17, (1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1), (8, 7, 6, 5, 4, 3, 2, 1, 9, 10, 11, 12)),
        (18, 18, (1, 1, 1, 1, 1, 1, 1, 1), (8, 7, 6, 5, 4, 3, 2, 1)),
        (19, 19, (1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1), (9, 8, 7, 6, 5, 4, 3, 2, 1, 10, 11, 12)),
        (20, 20, (1, 1, 1, 1, 1, 1, 1, 1, 1), (9, 8, 7, 6, 5, 4, 3, 2, 1)),
        (21, 21, (1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1), (10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 11, 12)),
        (22, 22, (1, 1, 1, 1, 1, 1, 1, 1, 1, 1), (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)),
        (23, 23, (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1), (11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 12)),
        (24, 24, (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), (11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)),
        (25, 25, (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2), (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)),
        (26, 200, (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)),
    ),

    # Lanes = 3
    (
        (3, 3, (2, 3), (2, 2, 1, 1)),
        (4, 4, (2, 3), (3, 3, 1, 1)),
        (5, 5, (1, 2, 1, 3), (2, 2, 1, 1, 3, 3, 4, 4)),
        (6, 6, (1, 1), (2, 3, 5, 2)),
        (7, 7, (2, 3), (2, 4, 5, 3)),
        (8, 8, (1, 1), (2, 5, 3, 4)),
        (9, 9, (1, 1), (2, 3, 3, 5)),
        (10, 10, (1, 1), (2, 7, 4, 5)),
        (11, 11, (1, 1), (2, 3, 3, 7)),
        (12, 12, (1,), (2, 3)),
        (13, 13, (1, 2, 1, 3), (3, 9, 7, 11, 10, 4, 6, 2)),
        (14, 14, (1,), (2, 3)),
        (15, 15, (1, 1), (2, 3, 6, 8)),
        (16, 16, (1, 1), (2, 3, 6, 9)),
        (17, 18, (1, 1), (2, 3, 4, 6)),
        (19, 19, (1, 1, 2, 1, 1, 3), (2, 3, 4, 6, 1, 7, 17, 16, 15, 13, 18, 12)),
        (20, 20, (1, 1), (2, 3, 4, 7)),
        (21, 200, (1, 1), (2, 3, 4, 6)),
    ),

    # Lanes = 4
    (
        (4, 4, (2, 3), (3, 3, 3, 1, 1, 1)),
        (5, 5, (2, 3), (2, 2, 2, 3, 3, 3)),
        (6, 6, (1, 1), (2, 2, 3, 3, 5, 5)),
        (7, 7, (2, 3), (2, 2, 4, 5, 5, 3)),
        (8, 8, (1, 1), (2, 2, 3, 3, 4, 2)),
        (9, 9, (1, 2), (2, 2, 4, 3, 5, 3)),
        (10, 10, (1, 1), (2, 2, 5, 3, 3, 6)),
        (11, 11, (1, 1), (2, 2, 6, 3, 3, 4)),
        (12, 12, (1, 1), (2, 4, 5, 3, 2, 8)),
        (13, 13, (2, 3), (2, 4, 12, 11, 9, 1)),
        (14, 14, (1, 1), (2, 4, 13, 3, 5, 2)),
        (15, 15, (1, 1), (2, 3, 4, 3, 2, 9)),
        (16, 16, (1, 1), (2, 3, 7, 3, 5, 9)),
        (17, 17, (1, 1), (2, 3, 4, 3, 2, 11)),
        (18, 18, (1, 1), (2, 3, 7, 3, 5, 9)),
        (19, 19, (1, 1), (2, 3, 4, 3, 5, 13)),
        (20, 20, (1, 1), (2, 14, 11, 12, 18, 3)),
        (21, 21, (1, 1), (4, 5, 10, 5, 13, 7)),
        (22, 22, (1, 1), (4, 5, 7, 8, 12, 21)),
        (23, 23, (1, 1), (4, 7, 10, 3, 5, 14)),
        (24, 26, (1,), (2, 3, 4)),
        (27, 27, (1, 1), (4, 5, 6, 7, 19, 25)),
        (28, 28, (1, 1), (4, 5, 6, 7, 20, 26)),
        (29, 29, (1, 1), (2, 3, 4, 6, 11, 28)),
        (30, 30, (1, 1), (2, 3, 4, 6, 11, 29)),
        (31, 31, (1, 1), (2, 3, 4, 6, 11, 30)),
        (32, 32, (1, 1), (2, 3, 4, 6, 12, 31)),
        (33, 33, (1, 1), (2, 3, 4, 6, 12, 32)),
        (34, 34, (1, 1), (2, 3, 4, 6, 13, 33)),
        (35, 35, (1, 1), (2, 3, 4, 6, 8, 10)),
        (36, 36, (1, 1), (2, 3, 4, 6, 8, 12)),
        (37, 37, (1, 1), (2, 3, 4, 6, 8, 10)),
        (38, 38, (1, 1), (2, 3, 4, 6, 8, 13)),
        (39, 41, (1, 1), (2, 3, 4, 6, 8, 10)),
        (42, 42, (1, 1), (2, 3, 4, 6, 8, 11)),
        (43, 47, (1, 1), (2, 3, 4, 6, 8, 10)),
        (48, 48, (1, 1), (2, 3, 4, 6, 8, 11)),
        (49, 200, (1, 1), (2, 3, 4, 6, 8, 10)),
    ),

    # Lanes = 5
    (
        (5, 5, (2, 3, 2, 3), (2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 1, 4, 4, 4, 4)),
        (6, 6, (2, 3), (5, 5, 5, 5, 1, 1, 1, 1)),
        (7, 7, (1, 1), (2, 2, 2, 2, 3, 3, 3, 3)),
        (8, 8, (1, 1), (2, 2, 3, 2, 3, 3, 4, 5)),
        (9, 9, (1, 2), (2, 2, 2, 4, 3, 3, 5, 8)),
        (10, 10, (1, 1), (2, 2, 3, 4, 3, 3, 6, 9)),
        (11, 11, (2, 3), (2, 2, 3, 5, 9, 9, 8, 6)),
        (12, 12, (1, 1), (2, 2, 3, 6, 3, 3, 2, 8)),
        (13, 13, (1, 1), (2, 2, 3, 7, 3, 3, 2, 4)),
        (14, 14, (1,), (2, 2, 3, 6)),
        (15, 15, (1, 1), (2, 2, 3, 9, 3, 4, 2, 5)),
        (16, 16, (1, 1), (2, 2, 4, 7, 3, 3, 6, 5)),
        (17, 17, (1, 1), (2, 2, 4, 16, 3, 3, 2, 8)),
        (18, 18, (1, 1), (2, 3, 4, 8, 3, 2, 2, 10)),
        (19, 19, (1, 1), (2, 2, 7, 13, 3, 3, 2, 10)),
        (20, 20, (0, 0), (2, 2, 3, 7, 3, 3, 2, 4)),
        (21, 21, (2, 3), (2, 5, 4, 18, 19, 16, 17, 3)),
        (22, 22, (0, 0), (2, 2, 3, 7, 3, 3, 2, 4)),
        (23, 23, (1, 1), (2, 3, 8, 16, 3, 2, 7, 10)),
        (24, 24, (1, 1), (2, 5, 4, 21, 3, 2, 6, 4)),
        (25, 25, (1, 1), (2, 3, 4, 10, 3, 2, 7, 12)),
        (26, 26, (1, 1), (2, 3, 7, 25, 3, 2, 4, 4)),
        (27, 27, (1, 1), (2, 3, 4, 6, 3, 2, 6, 20)),
        (28, 28, (1, 1), (2, 3, 4, 8, 3, 2, 8, 14)),
        (29, 29, (1, 1), (2, 3, 4, 6, 3, 2, 7, 28)),
        (30, 30, (1, 1), (2, 3, 4, 10, 3, 4, 8, 16)),
        (31, 31, (1, 1), (2, 3, 4, 6, 3, 2, 18, 30)),
        (32, 32, (1, 1), (1, 2, 4, 5, 2, 6, 7, 3)),
        (33, 33, (1, 1), (2, 3, 4, 6, 3, 5, 12, 32)),
        (34, 34, (1, 1), (2, 3, 4, 6, 3, 5, 12, 33)),
        (35, 35, (1, 1), (1, 2, 4, 5, 2, 6, 10, 4)),
        (36, 49, (1,), (2, 3, 4, 6)),
        (50, 50, (1, 1), (2, 3, 4, 6, 8, 11, 17, 34)),
        (51, 51, (1, 1), (2, 3, 4, 6, 8, 11, 18, 34)),
        (52, 52, (1,), (2, 3, 4, 6)),
        (53, 53, (1, 1), (2, 3, 4, 6, 8, 11, 18, 36)),
        (54, 54, (1, 1), (2, 3, 4, 6, 8, 11, 17, 38)),
        (55, 55, (1, 1), (2, 3, 4, 6, 8, 12, 17, 54)),
        (56, 56, (1, 1), (2, 3, 4, 6, 8, 11, 21, 55)),
        (57, 57, (1, 1), (2, 3, 4, 6, 8, 11, 17, 41)),
        (58, 58, (1, 1), (2, 3, 4, 6, 8, 11, 17, 42)),
        (59, 59, (1, 1), (2, 3, 4, 6, 8, 11, 17, 43)),
        (60, 60, (1, 1), (2, 3, 4, 6, 8, 11, 17, 44)),
        (61, 160, (1,), (2, 3, 4, 6)),
        (161, 200, (1, 1), (2, 3, 4, 6, 8, 11, 17, 44)),
    ),

    # Lanes = 6
    (
        (6, 6, (2, 3), (5, 5, 5, 5, 5, 1, 1, 1, 1, 1)),
        (7, 7, (2, 3), (2, 2, 2, 2, 2, 5, 5, 5, 5, 5)),
        (8, 8, (1,), (2, 2, 2, 3, 2)),
        (9, 9, (1,), (2, 2, 2, 2, 4)),
        (10, 10, (1,), (2, 2, 2, 3, 2)),
        (11, 11, (2,), (2, 2, 3, 5, 4)),
        (12, 12, (1,), (2, 2, 2, 3, 4)),
        (13, 13, (1,), (2, 2, 2, 3, 5)),
        (14, 14, (1,), (2, 2, 2, 3, 6)),
        (15, 15, (1,), (2, 2, 2, 3, 7)),
        (16, 17, (0,), (1, 2, 2, 3, 6)),
        (18, 18, (1,), (2, 2, 3, 5, 9)),
        (19, 19, (1,), (2, 2, 3, 4, 9)),
        (20, 20, (1,), (2, 2, 3, 4, 19)),
        (21, 21, (1,), (2, 2, 3, 4, 20)),
        (22, 22, (1,), (2, 2, 3, 4, 21)),
        (23, 23, (1,), (2, 2, 3, 4, 22)),
        (24, 24, (1,), (2, 2, 3, 6, 23)),
        (25, 25, (1,), (2, 2, 3, 6, 24)),
        (26, 26, (1,), (2, 2, 3, 6, 25)),
        (27, 27, (1,), (2, 2, 3, 6, 26)),
        (28, 28, (1,), (2, 5, 11, 4, 27)),
        (29, 30, (0,), (2, 3, 7, 15, 17)),
        (31, 31, (2,), (2, 3, 7, 15, 17)),
        (32, 34, (0,), (4, 1, 2, 8, 16)),
        (35, 35, (1,), (2, 3, 7, 19, 17)),
        (36, 36, (1,), (2, 3, 7, 20, 17)),
        (37, 37, (1,), (2, 3, 4, 10, 12)),
        (38, 38, (1,), (2, 3, 4, 8, 10)),
        (39, 39, (1,), (2, 3, 4, 19, 38)),
        (40, 40, (1,), (2, 3, 4, 6, 8)),
        (41, 41, (1,), (2, 3, 4, 6, 12)),
        (42, 42, (1,), (2, 3, 4, 8, 14)),
        (43, 43, (1,), (2, 3, 4, 6, 8)),
        (44, 44, (1,), (2, 3, 4, 6, 11)),
        (45, 45, (1,), (2, 3, 4, 6, 8)),
        (46, 46, (1,), (2, 3, 4, 6, 11)),
        (47, 200, (1,), (2, 3, 4, 6, 8)),
    ),
)

################################################################################
##
##  PpnException
##
################################################################################
class PpnException(Exception):
    pass

################################################################################
##
##  Weight
##
################################################################################
class Weight(object):
    ZERO   = 0
    LIGHT  = 1
    MEDIUM = 10
    HEAVY  = 100

################################################################################
##
##  makeArray
##
################################################################################
def makeArray(n, init=0):
    return [init] * (n+1)

################################################################################
##
##  printHeats
##
################################################################################
def printHeats(heats):
    i = 0
    for heat in heats:
        i += 1
        txt = "%3d:"%i
        for lane in heat:
            txt += " %3d"%lane
        print txt

################################################################################
##
##  Ppn
##
################################################################################
class Ppn(object):
    def __init__(self, nLanes, nCars):
        if not (2 <= nLanes <= 6):
            raise PpnException("Must have between 2 and 6 lanes")
        if not (2 <= nCars <= 200):
            raise ppnException("Must have between 2 and 200 cars")

        # Numbers of lanes and cars
        self.nLanes = nLanes
        self.nCars  = nCars

        # Number of rounds. Each round runs a full set of heats
        self.nRounds = 1

        # Weighting factors. Use constants in the Weight class.
        self.W1 = 0     # Balance heat counts
        self.W2 = 0     # Avoid consecutive heats
        self.W3 = 0     # Avoid consecutive lanes

        # Internal variables
        self.pn  = None
        self.pn2 = None
        self.T   = None
        self.tg  = None

    # Main function
    def generate(self):
        (T, tg) = self.getParms()

        if self.nRounds > len(T):
            print "Only up to %d rounds allowed for %d cars on %d lanes"%(len(T), nCars, nLanes)
            self.nRounds = len(T)

        self.gS     = self.nLanes - 1
        self.gens   = makeArray(self.gS * self.nRounds)
        self.nHeats = self.nCars * self.nRounds
        self.pn     = makeArray(self.nHeats * self.nLanes)
        self.pn2    = makeArray(self.nHeats * self.nLanes)
        self.hP     = (self.nHeats * self.nLanes) / self.nCars
        self.h2h    = (self.hP * (self.nLanes - 1)) / (self.nCars - 1);
        self.sums   = makeArray(self.nCars)

        aI = 0
        yI = 0
        for gL in range(0, self.nRounds):
            tI = aI
            for dL in range(0, self.gS):
                yI += 1
                self.gens[yI] = tg[tI]
                tI += 1
            aI = tI

        aI = 1
        pI = 0
        for gL in range(0, self.nRounds):
            for cL in range(1, self.nCars+1):
                self.pn[pI] = cL
                pI += 1
                tC = cL
                tI = aI
                for dL in range(0, self.gS):
                    tC += self.gens[tI]
                    tI += 1
                    if tC > self.nCars:
                        tC = tC - self.nCars
                    self.pn[pI] = tC
                    pI += 1
            aI = tI

        self.orderRaces()
        heats = self.makeHeats()

        return heats

    def orderRaces(self):
        if (self.W1 + self.W2 + self.W3) == 0:
            self.pn2 = self.pn
        else:
            nU = makeArray(self.nHeats-1, init=1)

            for i in range(0, self.nHeats):
                bR = self.nHeats - 1;
                bRt = 10000;

                k = 0;
                for j in range(0, self.nHeats):
                    if nU[j]:
                        k = self.rateRace(i, j)
                        if k < (bRt - 0.000001):
                            bRt = k
                            bR = j

                for l in range(0,self.nLanes):
                    car = self.pn[(self.nLanes * bR) + l]
                    self.pn2[(self.nLanes * i) + l] = car;
                    self.sums[car - 1] += 1
                nU[bR] = 0

    def getParms(self):
        if self.nCars < self.nLanes:
            self.nLanes = self.nCars

        for (lo, hi, T, tg) in PPN_PARMS[self.nLanes]:
            if lo <= self.nCars <= hi:
                return (T, tg)

        raise PpnException("Can't find parameters for nLanes=%d, nCars=%d")%(self.nLanes, self.nCars)

    ################################################################################
    ##
    ##  check1;
    ##  Goal: KEEP THE RACE COUNTS EVEN
    ##
    ################################################################################
    def check1(self, i, j):
        rC = makeArray(self.nCars)

        for l in range(0, self.nCars):
            rC[l] = self.sums[l]
        
        lo = self.nLanes * j
        hi = self.nLanes * (j+1)
        for m in range(lo, hi):
            car = self.pn[m]
            rC[car - 1] += 1

        dev = float(0)
        i = float(i)
        j = float(j)
        nL = float(self.nLanes)
        nC = float(self.nCars)
        tgt = ((i + 1) * nL) / nC;
        for l in range(0, self.nCars):
            dev += (rC[l] - tgt) * (rC[l] - tgt)
        dev = dev / ((i + 1) * self.nLanes)
        return dev

    ################################################################################
    ##
    ##  check2;
    ##  Goal: AVOID HAVING CARS IN CONSECUTIVE RACES
    ##
    ################################################################################
    def check2(self, i, j):
        cM = 0;

        for l in range(0, self.nLanes):
            for m in range(0,self.nLanes):
                if (self.pn[((j * self.nLanes) + l)] == self.pn2[(((i - 1) * self.nLanes) + m)]):
                    cM += 1

        return cM

    ################################################################################
    ##
    ##  check3;
    ##  Goal: AVOID HAVING CARS IN CONSECUTIVE RACES IN THE SAME LANES
    ##
    ################################################################################
    def check3(self, i, j):
        lM = 0

        for l in range(0, self.nLanes):
            if (self.pn[((j * self.nLanes) + l)] == self.pn2[(((i - 1) * self.nLanes) + l)]):
                lM += 1

        return lM

    ################################################################################
    ##
    ##  rateRace
    ##
    ################################################################################
    def rateRace(self, i, j):
        retVal = float(0)

        if self.W1:
            retVal += self.W1 * self.check1(i, j)

        # these checks don't make sense for the 1st race (race 0);
        if i > 0:
            if self.W2:
                retVal += self.W2 * self.check2(i, j)
            if self.W3:
                retVal += self.W3 * self.check3(i, j)

        return retVal

    ################################################################################
    ##
    ##  makeHeats
    ##
    ################################################################################
    def makeHeats(self):
        lo = 0
        heats = []

        while len(self.pn[lo:]) > 1:
            heats.append(self.pn2[lo:lo+self.nLanes])
            lo += self.nLanes

        return heats

##############################################################################
##
##  main
##
##############################################################################
if __name__ == '__main__':
    class TC01(unittest.TestCase):
        def check(self, tests):
            for (test, want) in tests.iteritems():
                (l,c,w1,w2,w3) = test
                ppn    = Ppn(l, c)
                ppn.W1 = w1
                ppn.W2 = w2
                ppn.W3 = w3
                got = ppn.generate()
                self.assertEqual(want,got,"\ntest=%s\nwant=%s\ngot =%s"%(test,want,got))

        def test_01(self):
            tests = {
                (2,2,0,0,0) : [[1,2],[2,1]],
                (3,3,0,0,0) : [[1,3,2],[2,1,3],[3,2,1]],
                (4,4,0,0,0) : [[1,4,3,2],[2,1,4,3],[3,2,1,4],[4,3,2,1]],
                (5,5,0,0,0) : [[1,3,5,2,4],[2,4,1,3,5],[3,5,2,4,1],[4,1,3,5,2],[5,2,4,1,3]],
                (6,6,0,0,0) : [[1,6,5,4,3,2],[2,1,6,5,4,3],[3,2,1,6,5,4],[4,3,2,1,6,5],[5,4,3,2,1,6],[6,5,4,3,2,1]],
            }
            self.check(tests)

        def test_02(self):
            tests = {
                (2,4,0,0,0)  : [[1,4],[2,1],[3,2],[4,3]],
                (2,8,0,0,0)  : [[1,4],[2,5],[3,6],[4,7],[5,8],[6,1],[7,2],[8,3]],
                (2,16,0,0,0) : [[1,8],[2,9],[3,10],[4,11],[5,12],[6,13],[7,14],[8,15],[9,16],[10,1],[11,2],[12,3],[13,4],[14,5],[15,6],[16,7]],
                (2,32,0,0,0) : [[1,13],[2,14],[3,15],[4,16],[5,17],[6,18],[7,19],[8,20],[9,21],[10,22],[11,23],[12,24],[13,25],[14,26],[15,27],[16,28],[17,29],[18,30],[19,31],[20,32],[21,1],[22,2],[23,3],[24,4],[25,5],[26,6],[27,7],[28,8],[29,9],[30,10],[31,11],[32,12]],
                (2,7,0,0,0)  : [[1,4],[2,5],[3,6],[4,7],[5,1],[6,2],[7,3]],
                (2,11,0,0,0) : [[1,6],[2,7],[3,8],[4,9],[5,10],[6,11],[7,1],[8,2],[9,3],[10,4],[11,5]],
                (2,13,0,0,0) : [[1,7],[2,8],[3,9],[4,10],[5,11],[6,12],[7,13],[8,1],[9,2],[10,3],[11,4],[12,5],[13,6]],
                (2,17,0,0,0) : [[1,9],[2,10],[3,11],[4,12],[5,13],[6,14],[7,15],[8,16],[9,17],[10,1],[11,2],[12,3],[13,4],[14,5],[15,6],[16,7],[17,8]],
            }
            self.check(tests)

        def test_03(self):
            tests = {
                (3,4,0,0,0)  : [[1,4,3],[2,1,4],[3,2,1],[4,3,2]],
                (3,8,0,0,0)  : [[1,3,8],[2,4,1],[3,5,2],[4,6,3],[5,7,4],[6,8,5],[7,1,6],[8,2,7]],
                (3,16,0,0,0) : [[1,3,6],[2,4,7],[3,5,8],[4,6,9],[5,7,10],[6,8,11],[7,9,12],[8,10,13],[9,11,14],[10,12,15],[11,13,16],[12,14,1],[13,15,2],[14,16,3],[15,1,4],[16,2,5]],
                (3,32,0,0,0) : [[1,3,6],[2,4,7],[3,5,8],[4,6,9],[5,7,10],[6,8,11],[7,9,12],[8,10,13],[9,11,14],[10,12,15],[11,13,16],[12,14,17],[13,15,18],[14,16,19],[15,17,20],[16,18,21],[17,19,22],[18,20,23],[19,21,24],[20,22,25],[21,23,26],[22,24,27],[23,25,28],[24,26,29],[25,27,30],[26,28,31],[27,29,32],[28,30,1],[29,31,2],[30,32,3],[31,1,4],[32,2,5]],
                (3,7,0,0,0)  : [[1,3,7],[2,4,1],[3,5,2],[4,6,3],[5,7,4],[6,1,5],[7,2,6]],
                (3,11,0,0,0) : [[1,3,6],[2,4,7],[3,5,8],[4,6,9],[5,7,10],[6,8,11],[7,9,1],[8,10,2],[9,11,3],[10,1,4],[11,2,5]],
                (3,13,0,0,0) : [[1,4,13],[2,5,1],[3,6,2],[4,7,3],[5,8,4],[6,9,5],[7,10,6],[8,11,7],[9,12,8],[10,13,9],[11,1,10],[12,2,11],[13,3,12]],
                (3,17,0,0,0) : [[1,3,6],[2,4,7],[3,5,8],[4,6,9],[5,7,10],[6,8,11],[7,9,12],[8,10,13],[9,11,14],[10,12,15],[11,13,16],[12,14,17],[13,15,1],[14,16,2],[15,17,3],[16,1,4],[17,2,5]],
            }
            self.check(tests)

        def test_04(self):
            tests = {
                (4,8,0,0,0)  : [[1,3,5,8],[2,4,6,1],[3,5,7,2],[4,6,8,3],[5,7,1,4],[6,8,2,5],[7,1,3,6],[8,2,4,7]],
                (4,16,0,0,0) : [[1,3,6,13],[2,4,7,14],[3,5,8,15],[4,6,9,16],[5,7,10,1],[6,8,11,2],[7,9,12,3],[8,10,13,4],[9,11,14,5],[10,12,15,6],[11,13,16,7],[12,14,1,8],[13,15,2,9],[14,16,3,10],[15,1,4,11],[16,2,5,12]],
                (4,32,0,0,0) : [[1,3,6,10],[2,4,7,11],[3,5,8,12],[4,6,9,13],[5,7,10,14],[6,8,11,15],[7,9,12,16],[8,10,13,17],[9,11,14,18],[10,12,15,19],[11,13,16,20],[12,14,17,21],[13,15,18,22],[14,16,19,23],[15,17,20,24],[16,18,21,25],[17,19,22,26],[18,20,23,27],[19,21,24,28],[20,22,25,29],[21,23,26,30],[22,24,27,31],[23,25,28,32],[24,26,29,1],[25,27,30,2],[26,28,31,3],[27,29,32,4],[28,30,1,5],[29,31,2,6],[30,32,3,7],[31,1,4,8],[32,2,5,9]],
                (4,7,0,0,0)  : [[1,3,5,2],[2,4,6,3],[3,5,7,4],[4,6,1,5],[5,7,2,6],[6,1,3,7],[7,2,4,1]],
                (4,11,0,0,0) : [[1,3,5,11],[2,4,6,1],[3,5,7,2],[4,6,8,3],[5,7,9,4],[6,8,10,5],[7,9,11,6],[8,10,1,7],[9,11,2,8],[10,1,3,9],[11,2,4,10]],
                (4,13,0,0,0) : [[1,3,7,6],[2,4,8,7],[3,5,9,8],[4,6,10,9],[5,7,11,10],[6,8,12,11],[7,9,13,12],[8,10,1,13],[9,11,2,1],[10,12,3,2],[11,13,4,3],[12,1,5,4],[13,2,6,5]],
                (4,17,0,0,0) : [[1,3,6,10],[2,4,7,11],[3,5,8,12],[4,6,9,13],[5,7,10,14],[6,8,11,15],[7,9,12,16],[8,10,13,17],[9,11,14,1],[10,12,15,2],[11,13,16,3],[12,14,17,4],[13,15,1,5],[14,16,2,6],[15,17,3,7],[16,1,4,8],[17,2,5,9]],
            }
            self.check(tests)

        def test_05(self):
            tests = {
                (5,8,0,0,0)  : [[1,3,5,8,2],[2,4,6,1,3],[3,5,7,2,4],[4,6,8,3,5],[5,7,1,4,6],[6,8,2,5,7],[7,1,3,6,8],[8,2,4,7,1]],
                (5,16,0,0,0) : [[1,3,5,9,16],[2,4,6,10,1],[3,5,7,11,2],[4,6,8,12,3],[5,7,9,13,4],[6,8,10,14,5],[7,9,11,15,6],[8,10,12,16,7],[9,11,13,1,8],[10,12,14,2,9],[11,13,15,3,10],[12,14,16,4,11],[13,15,1,5,12],[14,16,2,6,13],[15,1,3,7,14],[16,2,4,8,15]],
                (5,32,0,0,0) : [[1,2,4,8,13],[2,3,5,9,14],[3,4,6,10,15],[4,5,7,11,16],[5,6,8,12,17],[6,7,9,13,18],[7,8,10,14,19],[8,9,11,15,20],[9,10,12,16,21],[10,11,13,17,22],[11,12,14,18,23],[12,13,15,19,24],[13,14,16,20,25],[14,15,17,21,26],[15,16,18,22,27],[16,17,19,23,28],[17,18,20,24,29],[18,19,21,25,30],[19,20,22,26,31],[20,21,23,27,32],[21,22,24,28,1],[22,23,25,29,2],[23,24,26,30,3],[24,25,27,31,4],[25,26,28,32,5],[26,27,29,1,6],[27,28,30,2,7],[28,29,31,3,8],[29,30,32,4,9],[30,31,1,5,10],[31,32,2,6,11],[32,1,3,7,12]],
                (5,7,0,0,0)  : [[1,3,5,7,2],[2,4,6,1,3],[3,5,7,2,4],[4,6,1,3,5],[5,7,2,4,6],[6,1,3,5,7],[7,2,4,6,1]],
                (5,11,0,0,0) : [[1,3,5,8,2],[2,4,6,9,3],[3,5,7,10,4],[4,6,8,11,5],[5,7,9,1,6],[6,8,10,2,7],[7,9,11,3,8],[8,10,1,4,9],[9,11,2,5,10],[10,1,3,6,11],[11,2,4,7,1]],
                (5,13,0,0,0) : [[1,3,5,8,2],[2,4,6,9,3],[3,5,7,10,4],[4,6,8,11,5],[5,7,9,12,6],[6,8,10,13,7],[7,9,11,1,8],[8,10,12,2,9],[9,11,13,3,10],[10,12,1,4,11],[11,13,2,5,12],[12,1,3,6,13],[13,2,4,7,1]],
                (5,17,0,0,0) : [[1,3,5,9,8],[2,4,6,10,9],[3,5,7,11,10],[4,6,8,12,11],[5,7,9,13,12],[6,8,10,14,13],[7,9,11,15,14],[8,10,12,16,15],[9,11,13,17,16],[10,12,14,1,17],[11,13,15,2,1],[12,14,16,3,2],[13,15,17,4,3],[14,16,1,5,4],[15,17,2,6,5],[16,1,3,7,6],[17,2,4,8,7]],
            }
            self.check(tests)

        def test_06(self):
            tests = {
                (6,8,0,0,0)  : [[1,3,5,7,2,4],[2,4,6,8,3,5],[3,5,7,1,4,6],[4,6,8,2,5,7],[5,7,1,3,6,8],[6,8,2,4,7,1],[7,1,3,5,8,2],[8,2,4,6,1,3]],
                (6,16,0,0,0) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,1],[4,5,7,9,12,2],[5,6,8,10,13,3],[6,7,9,11,14,4],[7,8,10,12,15,5],[8,9,11,13,16,6],[9,10,12,14,1,7],[10,11,13,15,2,8],[11,12,14,16,3,9],[12,13,15,1,4,10],[13,14,16,2,5,11],[14,15,1,3,6,12],[15,16,2,4,7,13],[16,1,3,5,8,14]],
                (6,32,0,0,0) : [[1,5,6,8,16,32],[2,6,7,9,17,1],[3,7,8,10,18,2],[4,8,9,11,19,3],[5,9,10,12,20,4],[6,10,11,13,21,5],[7,11,12,14,22,6],[8,12,13,15,23,7],[9,13,14,16,24,8],[10,14,15,17,25,9],[11,15,16,18,26,10],[12,16,17,19,27,11],[13,17,18,20,28,12],[14,18,19,21,29,13],[15,19,20,22,30,14],[16,20,21,23,31,15],[17,21,22,24,32,16],[18,22,23,25,1,17],[19,23,24,26,2,18],[20,24,25,27,3,19],[21,25,26,28,4,20],[22,26,27,29,5,21],[23,27,28,30,6,22],[24,28,29,31,7,23],[25,29,30,32,8,24],[26,30,31,1,9,25],[27,31,32,2,10,26],[28,32,1,3,11,27],[29,1,2,4,12,28],[30,2,3,5,13,29],[31,3,4,6,14,30],[32,4,5,7,15,31]],
                (6,7,0,0,0)  : [[1,3,5,7,2,4],[2,4,6,1,3,5],[3,5,7,2,4,6],[4,6,1,3,5,7],[5,7,2,4,6,1],[6,1,3,5,7,2],[7,2,4,6,1,3]],
                (6,11,0,0,0) : [[1,3,5,8,2,6],[2,4,6,9,3,7],[3,5,7,10,4,8],[4,6,8,11,5,9],[5,7,9,1,6,10],[6,8,10,2,7,11],[7,9,11,3,8,1],[8,10,1,4,9,2],[9,11,2,5,10,3],[10,1,3,6,11,4],[11,2,4,7,1,5]],
                (6,13,0,0,0) : [[1,3,5,7,10,2],[2,4,6,8,11,3],[3,5,7,9,12,4],[4,6,8,10,13,5],[5,7,9,11,1,6],[6,8,10,12,2,7],[7,9,11,13,3,8],[8,10,12,1,4,9],[9,11,13,2,5,10],[10,12,1,3,6,11],[11,13,2,4,7,12],[12,1,3,5,8,13],[13,2,4,6,9,1]],
                (6,17,0,0,0) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[4,5,7,9,12,1],[5,6,8,10,13,2],[6,7,9,11,14,3],[7,8,10,12,15,4],[8,9,11,13,16,5],[9,10,12,14,17,6],[10,11,13,15,1,7],[11,12,14,16,2,8],[12,13,15,17,3,9],[13,14,16,1,4,10],[14,15,17,2,5,11],[15,16,1,3,6,12],[16,17,2,4,7,13],[17,1,3,5,8,14]],
            }
            self.check(tests)
        
        def test_07(self):
            L = Weight.LIGHT
            M = Weight.MEDIUM
            H = Weight.HEAVY
            tests = {
                (6,17,H,0,0) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[8,9,11,13,16,5],[9,10,12,14,17,6],[10,11,13,15,1,7],[11,12,14,16,2,8],[4,5,7,9,12,1],[12,13,15,17,3,9],[13,14,16,1,4,10],[14,15,17,2,5,11],[5,6,8,10,13,2],[15,16,1,3,6,12],[6,7,9,11,14,3],[7,8,10,12,15,4],[16,17,2,4,7,13],[17,1,3,5,8,14]],
                (6,17,0,H,0) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[4,5,7,9,12,1],[5,6,8,10,13,2],[6,7,9,11,14,3],[7,8,10,12,15,4],[8,9,11,13,16,5],[9,10,12,14,17,6],[10,11,13,15,1,7],[11,12,14,16,2,8],[12,13,15,17,3,9],[13,14,16,1,4,10],[14,15,17,2,5,11],[15,16,1,3,6,12],[16,17,2,4,7,13],[17,1,3,5,8,14]],
                (6,17,0,0,H) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[4,5,7,9,12,1],[5,6,8,10,13,2],[6,7,9,11,14,3],[7,8,10,12,15,4],[8,9,11,13,16,5],[9,10,12,14,17,6],[10,11,13,15,1,7],[11,12,14,16,2,8],[12,13,15,17,3,9],[13,14,16,1,4,10],[14,15,17,2,5,11],[15,16,1,3,6,12],[16,17,2,4,7,13],[17,1,3,5,8,14]],
                (6,17,L,M,H) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[10,11,13,15,1,7],[9,10,12,14,17,6],[8,9,11,13,16,5],[7,8,10,12,15,4],[17,1,3,5,8,14],[16,17,2,4,7,13],[15,16,1,3,6,12],[14,15,17,2,5,11],[4,5,7,9,12,1],[11,12,14,16,2,8],[12,13,15,17,3,9],[5,6,8,10,13,2],[6,7,9,11,14,3],[13,14,16,1,4,10]],
                (6,17,H,L,M) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[10,11,13,15,1,7],[9,10,12,14,17,6],[8,9,11,13,16,5],[17,1,3,5,8,14],[7,8,10,12,15,4],[11,12,14,16,2,8],[12,13,15,17,3,9],[13,14,16,1,4,10],[6,7,9,11,14,3],[16,17,2,4,7,13],[15,16,1,3,6,12],[5,6,8,10,13,2],[4,5,7,9,12,1],[14,15,17,2,5,11]],
                (6,17,M,H,L) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[10,11,13,15,1,7],[9,10,12,14,17,6],[8,9,11,13,16,5],[7,8,10,12,15,4],[17,1,3,5,8,14],[16,17,2,4,7,13],[15,16,1,3,6,12],[14,15,17,2,5,11],[4,5,7,9,12,1],[11,12,14,16,2,8],[12,13,15,17,3,9],[5,6,8,10,13,2],[6,7,9,11,14,3],[13,14,16,1,4,10]],
                (6,17,M,M,M) : [[1,2,4,6,9,15],[2,3,5,7,10,16],[3,4,6,8,11,17],[10,11,13,15,1,7],[9,10,12,14,17,6],[8,9,11,13,16,5],[7,8,10,12,15,4],[17,1,3,5,8,14],[16,17,2,4,7,13],[15,16,1,3,6,12],[14,15,17,2,5,11],[4,5,7,9,12,1],[11,12,14,16,2,8],[12,13,15,17,3,9],[5,6,8,10,13,2],[6,7,9,11,14,3],[13,14,16,1,4,10]],
            }
            self.check(tests)
            
    unittest.main()
