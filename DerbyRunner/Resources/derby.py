from ConfigParser import SafeConfigParser
from htmltags import *
import ppngen
import operator
import optparse
import os
import os.path
import re
import subprocess
import sys
import time
import csv
import uuid

RESDIR = str(Titanium.Filesystem.getResourcesDirectory())
APPDIR = str(Titanium.Filesystem.getApplicationDataDirectory())
CFGFILE = os.path.join(APPDIR, 'derby.cfg')

tri_asc = '&#x25B4;'
tri_dsc = '&#x25BE;'

################################################################################
##
##  Logger
##
################################################################################
class Logger(object):
    FATAL    = Titanium.API.FATAL
    CRITICAL = Titanium.API.CRITICAL
    ERROR    = Titanium.API.ERROR
    WARN     = Titanium.API.WARN
    NOTICE   = Titanium.API.NOTICE
    INFO     = Titanium.API.INFO
    DEBUG    = Titanium.API.DEBUG

    def fatal(self, msg):
        Titanium.API.log(Titanium.API.FATAL, str(msg))
    def critical(self, msg):
        Titanium.API.log(Titanium.API.CRITICAL, str(msg))
    def error(self, msg):
        Titanium.API.log(Titanium.API.ERROR, str(msg))
    def warn(self, msg):
        Titanium.API.log(Titanium.API.WARN, str(msg))
    def notice(self, msg):
        Titanium.API.log(Titanium.API.NOTICE, str(msg))
    def info(self, msg):
        Titanium.API.log(Titanium.API.INFO, str(msg))
    def debug(self, msg):
        Titanium.API.log(Titanium.API.DEBUG, str(msg))

################################################################################
##
##  Vehicle
##
################################################################################
class Vehicle(object):
    __slots__ = ('uuid', 'vin', 'owner', 'group')

    def __init__(self, vin='', owner='', group=''):
        self.uuid  = str(uuid.uuid4())
        self.vin   = vin
        self.owner = owner
        self.group = group
        log.notice("New vehicle uuid=%s"%self.uuid)

    def __str__(self):
        txt = []
        txt.append('[VEHICLE]')
        txt.append('uuid = %s'%(self.uuid,))
        txt.append('vin = %s'%(self.vin,))
        txt.append('owner = %s'%(self.owner,))
        txt.append('group = %s'%(self.group,))
        return '\n'.join(txt)

    def __repr__(self):
        return 'Vehicle uuid=%s vin=%s owner=%s group=%s'%(
                self.uuid, self.vin, self.owner, self.group)

    def config(self, key, val):
        try:
            self.__setattr__(key, val)
        except AttributeError:
            return False
        return True

################################################################################
##
##  VehicleSort
##
################################################################################
class VehicleSort(object):
    class SortOrder(object):
        VIN_UP = 'VIN_UP'
        VIN_DN = 'VIN_DN'
        OWN_UP = 'OWN_UP'
        OWN_DN = 'OWN_DN'
        GRP_UP = 'GRP_UP'
        GRP_DN = 'GRP_DN'

        parms = {
            VIN_UP : ('vin', False),
            VIN_DN : ('vin', True),
            OWN_UP : ('owner', False),
            OWN_DN : ('owner', True),
            GRP_UP : ('group', False),
            GRP_DN : ('group', True),
        }

    def _fget_sorted(self):
        known = set([x.uuid for x in self._sorted])
        uuids = set(self.cfg.vehicles.keys())
        add = uuids - known
        rem = known - uuids
        for i in reversed(range(0,len(self._sorted))):
            if self._sorted[i].uuid in rem:
                del self._sorted[i]
        for uuid in add:
            self._sorted.append(self.cfg.vehicles[uuid])
        return self._sorted
    sorted = property(fget=_fget_sorted)

    def __init__(self, cfg, render):
        self.cfg     = cfg
        self.render  = render
        self.order   = self.SortOrder.VIN_UP
        self._sorted = []
        dummy = self.sorted
        self.sort()

    def toggle_vin(self):
        if self.order == self.SortOrder.VIN_UP:
            self.order = self.SortOrder.VIN_DN
        else:
            self.order = self.SortOrder.VIN_UP
        self.sort()
        self.render()

    def toggle_own(self):
        if self.order == self.SortOrder.OWN_UP:
            self.order = self.SortOrder.OWN_DN
        else:
            self.order = self.SortOrder.OWN_UP
        self.sort()
        self.render()

    def toggle_grp(self):
        if self.order == self.SortOrder.GRP_UP:
            self.order = self.SortOrder.GRP_DN
        else:
            self.order = self.SortOrder.GRP_UP
        self.sort()
        self.render()

    def sort(self):
        (attr, rev) = self.SortOrder.parms[self.order]
        self._sorted.sort(key=operator.attrgetter(attr), reverse=rev)

################################################################################
##
##  Race
##
################################################################################
class Race(object):
    __slots__ = ('uuid', 'title', '_lanes', 'vehicles', 'standings', 'heats',
            'balanceHeats', 'avoidConsecutiveHeats', 'avoidConsecutiveLanes')

    def _fset_lanes(self, lanes):
        self.heats = None
        self._lanes = int(lanes)
        if not (2 <= self._lanes <= 6):
            log.warn("Bad number of lanes, defaulting to 6")
            self._lanes = 6
    def _fget_lanes(self):
        return self._lanes
    lanes = property(fset=_fset_lanes, fget=_fget_lanes)

    def __init__(self, title='', lanes=6):
        self.uuid  = str(uuid.uuid4())
        self.title = title
        self.lanes = lanes
        self.vehicles = set()
        log.notice("New race uuid=%s"%self.uuid)

        self.standings = None
        self.heats     = None
        self.balanceHeats          = ppngen.Weight.MEDIUM
        self.avoidConsecutiveHeats = ppngen.Weight.MEDIUM
        self.avoidConsecutiveLanes = ppngen.Weight.MEDIUM

    def __str__(self):
        txt = []
        txt.append('[RACE]')
        txt.append('uuid = %s'%(self.uuid,))
        txt.append('title = %s'%(self.title,))
        txt.append('lanes = %s'%(self.lanes,))
        log.notice(str(self.vehicles))
        for uuid in self.vehicles:
            txt.append('vehicle = %s'%(uuid,))
        return '\n'.join(txt)

    def __repr__(self):
        return 'Race uuid=%s title=%s lanes=%s vehicles=%s'%(
                self.uuid, self.title, self.lanes, self.vehicles)

    def addVehicle(self, uuid):
        self.heats = None
        if uuid in cfg.vehicles:
            self.vehicles.add(uuid)

    def delVehicle(self, uuid):
        self.heats = None
        try:
            self.vehicles.remove(uuid)
        except KeyError:
            pass

    def config(self, key, val):
        if key == 'vehicle':
            self.addVehicle(val)
        else:
            try:
                self.__setattr__(key, val)
            except AttributeError:
                return False
        return True

    def makeHeats(self):
        if not self.heats:
            ppn = ppngen.Ppn(self.lanes, len(self.vehicles))
            ppn.W1 = self.balanceHeats
            ppn.W2 = self.avoidConsecutiveHeats
            ppn.W3 = self.avoidConsecutiveLanes
            ppnheats = ppn.generate()

            vehicles = [cfg.vehicles[uuid] for uuid in self.vehicles]
            vehicles.sort(key=operator.attrgetter('vin'))

            self.heats = []
            for h in range(0, len(ppnheats)):
                heat = []
                self.heats.append(heat)
                for l in range(0, self.lanes):
                    res = Result()
                    res.vehicle = vehicles[ppnheats[h][l]-1]
                    res.position = 0
                    heat.append(res)

            self.standings = {}
            for v in vehicles:
                self.standings[v.uuid] = Standing(v)

class Result(object):
    def __init__(self):
        self.vehicle = None
        self.position = None

class Standing(object):
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.points = 0

################################################################################
##
##  Config
##
################################################################################
class Config(object):
    SECTIONS = ('VEHICLE','RACE')

    def __init__(self, filename):
        self.filename = filename
        self.vehicles = {}
        self.races = {}

    def addObject(self, obj):
        log.notice('addObject %s'%repr(obj))
        if isinstance(obj, Vehicle):
            self.vehicles[str(obj.uuid)] = obj
        elif isinstance(obj, Race):
            self.races[str(obj.uuid)] = obj

    def delObject(self, obj):
        log.notice('delObject %s'%repr(obj))
        if str(obj.uuid) in self.vehicles:
            del self.vehicles[obj.uuid]
            for uuid in self.races:
                race = self.races[str(uuid)]
                if str(obj.uuid) in race.vehicles:
                    race.delVehicle(obj.uuid)
        if obj.uuid in self.races:
            del self.races[obj.uuid]

    def read(self):
        log.notice('Config.read()')
        try:
            fh = open(self.filename)
        except IOError, e:
            log.warn(str(e))
            return

        re_section = re.compile(r'^\[\s*(.*?)\s*\]$')
        re_config = re.compile(r'^(\S+)\s*=\s*(.*)$')

        section = None
        lineno = 0
        item = None
        for x in fh:
            lineno += 1
            x = x.strip()
            if not x:
                continue

            mo = re_section.search(x)
            if mo:
                section = mo.group(1).upper()
                if section not in Config.SECTIONS:
                    window.alert("Unknown section [%s]", section)
                    return
                log.notice('Found %s'%(section,))
                if section == 'VEHICLE':
                    item = Vehicle()
                elif section == 'RACE':
                    item = Race()
                continue

            mo = re_config.search(x)
            if mo:
                key = mo.group(1).lower()
                val = mo.group(2)
                log.notice('Found %s = %s'%(key,val))
                self.delObject(item)
                if not item.config(key, val):
                    log.error("Unknown key for [%s]: %s", section, key)
                self.addObject(item)
                continue

    def write(self):
        log.notice('Config.write()')
        try:
            fh = open(self.filename, 'w')
        except Exception, e:
            window.alert("Error writing '%s'\n%s", self.filename, e)
            return

        for (k,v) in self.vehicles.iteritems():
            print >>fh, str(v)
            print >>fh

        for (k,v) in self.races.iteritems():
            print >>fh, str(v)
            print >>fh

        fh.close()

################################################################################
##
##  Page
##
################################################################################
class Page(object):
    title = ''
    special = ''

    def __init__(self, cfg):
        self.cfg = cfg

    def __str__(self):
        return self.content()

    def content(self):
        return ''

    def render(self):
        document.getElementById('hdr-center').innerHTML = self.title
        document.getElementById('hdr-right').innerHTML = self.special
        document.getElementById('content').innerHTML = self.content()

################################################################################
##
##  HelpPage
##
################################################################################
class HelpPage(Page):
    title = 'DerbyRunner Help'

    def content(self):
        try:
            fh = open(os.path.join(RESDIR, 'help.html'))
            help = fh.read()
            fh.close()
        except IOError, e:
            help = str( P() <= 'Sorry, no help available' )

        back = DIV()
        back <= HR()
        link = P()
        link \
                <= A(href="javascript:homePage.render()") \
                <= IMG(Class="mini-button", src="shield.png")
        link \
                <= A(href="javascript:homePage.render()") \
                <= "Back to Home Page"
        back <= link

        return help + str(back)

################################################################################
##
##  HomePage
##
################################################################################
class HomePage(Page):
    title = "Home Page"

    def content(self):
        global ma

        root = DIV(id='homePage')
        ht = TABLE(id='home-table', align="center")
        tr = TR()
        tr \
            <= TD() \
            <= A(href="javascript:manageVehicles.render()") \
            <= IMG(Class='home-button', src='vehicles.png') \
                + P('Manage Vehicles')
        tr \
            <= TD() \
            <= A(href="javascript:manageRaces.render()") \
            <= IMG(Class='home-button', src='races.png') \
                + P('Manage Races')
        ht <= tr

        tr = TR()
        tr \
            <= TD(colspan="2") \
            <= A(href="javascript:helpPage.render()") \
            <= IMG(Class='home-button', src='help.png') \
                + P('Get Help')
        ht <= tr

        root <= ht
        return str(root)

################################################################################
##
##  ManageVehicles
##
################################################################################
class ManageVehicles(Page):
    title = "Manage Vehicles"

    def __init__(self, cfg):
        super(ManageVehicles, self).__init__(cfg)

    def content(self):
        root = DIV(id='root')
        tbl = TABLE()
        tr = TR()

        hdr = 'Vehicle ID'
        if manageVehiclesSort.order == manageVehiclesSort.SortOrder.VIN_UP:
            hdr += ' ' + tri_asc
        elif manageVehiclesSort.order == manageVehiclesSort.SortOrder.VIN_DN:
            hdr += ' ' + tri_dsc
        tr <= TH() <= A(href="javascript:manageVehiclesSort.toggle_vin()") <= hdr

        hdr = 'Owner Name'
        if manageVehiclesSort.order == manageVehiclesSort.SortOrder.OWN_UP:
            hdr += ' ' + tri_asc
        elif manageVehiclesSort.order == manageVehiclesSort.SortOrder.OWN_DN:
            hdr += ' ' + tri_dsc
        tr <= TH() <= A(href="javascript:manageVehiclesSort.toggle_own()") <= hdr

        hdr = 'Group'
        if manageVehiclesSort.order == manageVehiclesSort.SortOrder.GRP_UP:
            hdr += ' ' + tri_asc
        elif manageVehiclesSort.order == manageVehiclesSort.SortOrder.GRP_DN:
            hdr += ' ' + tri_dsc
        tr <= TH() <= A(href="javascript:manageVehiclesSort.toggle_grp()") <= hdr

        tbl <= tr
        root <= tbl

        for v in manageVehiclesSort.sorted:
            tr = TR()
            tr <= TD() <= INPUT(type="text", id="vin+%s"%v.uuid, value="%s"%v.vin, onchange="manageVehicles.update(this)")
            tr <= TD() <= INPUT(type="text", id="owner+%s"%v.uuid, value="%s"%v.owner, onchange="manageVehicles.update(this)")
            tr <= TD() <= INPUT(type="text", id="group+%s"%v.uuid, value="%s"%v.group, onchange="manageVehicles.update(this)")
            tr <= TD() <= INPUT(type="button", id="del+%s"%v.uuid, value="Delete", onclick="manageVehicles.remove(this)")
            tbl <= tr

        p = P()
        p <= INPUT(type="button", id="add", value="Add Vehicle", onclick="manageVehicles.add(this)")
        p <= INPUT(type="button", id="import", value="Import CSV File", onclick="manageVehicles.chooseFile()")
        root <= p

        return str(root)

    def add(self, this):
        v = Vehicle()
        self.cfg.addObject(v)
        self.cfg.write()
        self.render()

    def update(self, this):
        (col, uuid) = this.id.split('+')
        val = this.value.strip()
        log.notice("update %s %s %s"%(uuid,col,val))
        self.cfg.vehicles[uuid].config(col, val)
        self.cfg.write()

    def remove(self, this):
        (col, uuid) = this.id.split('+')
        log.notice("remove %s vin=%s"%(uuid,self.cfg.vehicles[uuid].vin))
        self.cfg.delObject(self.cfg.vehicles[uuid])
        self.cfg.write()
        self.render()

    def chooseFile(self):
        options = {
            'multiple'         : False,
            'title'            : "Import CSV File",
            'types'            : ['csv', 'txt'],
            'files'            : True,
            'directories'      : False,
            'typesDescription' : "All files",
            'defaultName'      : None,
            'path'             : Titanium.Filesystem.getUserDirectory()
        }
        Titanium.UI.openFileChooserDialog(manageVehicles.importCsv, options)

    def importCsv(self, filelist):
        for f in filelist:
            log.notice(f)
            try:
                reader = csv.reader(open(f, "rb"))
            except Exception, e:
                window.alert("Can't read %s:\n%s"%(f,e))
                continue

            i = 0
            for row in reader:
                i += 1
                if len(row) != 3:
                    window.alert("Parse error at %s:%d\nMust have VechicleID, Owner, and Group"%(f,i))
                    continue
                v = Vehicle()
                v.vin   = row[0].strip()
                v.owner = row[1].strip()
                v.group = row[2].strip()
                self.cfg.addObject(v)

        self.cfg.write()
        self.render()

################################################################################
##
##  ManageRaces
##
################################################################################
class ManageRaces(Page):
    title = "Manage Races"

    def content(self):
        root = DIV(id='root')
        tbl = TABLE()
        tr = TR()
        tr <= TH(Class='label') <= 'Race Title'
        tr <= TH() <= 'Lanes'
        tr <= TH() <= 'Vehicles'
        tr <= TH()
        tr <= TH()
        tbl <= tr
        root <= tbl

        races = sorted(self.cfg.races.values(), key=operator.attrgetter('title'))
        for r in races:
            log.notice(str(r.uuid))
            tr = TR()
            tr <= TD() <= r.title
            tr <= TD(Class='center') <= str(r.lanes)
            tr <= TD(Class='center') <= str(len(r.vehicles))
            tr <= TD(Class='center') <= INPUT(type="button", id="edt+%s"%r.uuid, value="Edit",   onclick="manageRaces.edit(this)")
            tr <= TD(Class='center') <= INPUT(type="button", id="del+%s"%r.uuid, value="Delete", onclick="manageRaces.remove(this)")
            tr <= TD(Class='center') <= INPUT(type="image",  id="run+%s"%r.uuid, Class="micro-button", src="go.png", onclick="manageRaces.run(this)")
            tbl <= tr

        p = P()
        p <= INPUT(type="button", id="add", value="Add Race", onclick="manageRaces.add(this)")
        root <= p

        return str(root)

    def add(self, this):
        log.notice('ManageRaces.add()')
        race = Race()
        self.cfg.addObject(race)
        self.cfg.write()
        editRace.race = race
        editRace.render()

    def remove(self, this):
        (col, uuid) = this.id.split('+')
        race = self.cfg.races[uuid]
        log.notice('ManageRaces.remove() uuid=%s title=%s'%(uuid,race.title))
        self.cfg.delObject(race)
        self.cfg.write()
        self.render()

    def edit(self, this):
        (col, uuid) = this.id.split('+')
        race = self.cfg.races[uuid]
        log.notice('ManageRaces.edit() uuid=%s title=%s'%(uuid,race.title))
        editRace.race = race
        editRace.render()

    def run(self, this):
        (col, uuid) = this.id.split('+')
        race = self.cfg.races[uuid]
        log.notice('ManageRaces.run() uuid=%s title=%s'%(uuid,race.title))
        if len(race.vehicles) < 2:
            window.alert("Need at least two vehicles to race.")
            return
        if len(race.vehicles) < race.lanes:
            race.lanes = len(race.vehicles)
        runRace.race = race
        runRace.render()

################################################################################
##
##  EditRace
##
################################################################################
class EditRace(Page):
    title = "Edit Race"

    def content(self):
        root = DIV(id='root')
        p = P()
        p <= "Race Title: "
        p <= INPUT(type="text", id="title", value="%s"%self.race.title, onchange="editRace.update_title(this)")
        p <= "Number of Lanes: "
        sel = SELECT(id='lanesel', onchange="editRace.update_lanes(this)")
        for i in range(2,7):
            flag = (i == self.race.lanes)
            sel <= OPTION(value="%s"%i, SELECTED=flag) <= "%s"%i
        p <= sel
        root <= p

        tbl = TABLE()
        tr = TR()

        hdr = 'Vehicle ID'
        if editRaceSort.order == editRaceSort.SortOrder.VIN_UP:
            hdr += ' ' + tri_asc
        elif editRaceSort.order == editRaceSort.SortOrder.VIN_DN:
            hdr += ' ' + tri_dsc
        tr <= TH() <= A(href="javascript:editRaceSort.toggle_vin()") <= hdr

        hdr = 'Owner Name'
        if editRaceSort.order == editRaceSort.SortOrder.OWN_UP:
            hdr += ' ' + tri_asc
        elif editRaceSort.order == editRaceSort.SortOrder.OWN_DN:
            hdr += ' ' + tri_dsc
        tr <= TH() <= A(href="javascript:editRaceSort.toggle_own()") <= hdr

        hdr = 'Group'
        if editRaceSort.order == editRaceSort.SortOrder.GRP_UP:
            hdr += ' ' + tri_asc
        elif editRaceSort.order == editRaceSort.SortOrder.GRP_DN:
            hdr += ' ' + tri_dsc
        tr <= TH() <= A(href="javascript:editRaceSort.toggle_grp()") <= hdr

        tbl <= tr
        root <= tbl

        for v in editRaceSort.sorted:
            flag = v.uuid in self.race.vehicles
            tr = TR()
            tr <= TD() <= v.vin
            tr <= TD() <= v.owner
            tr <= TD() <= v.group
            tr <= TD() <= INPUT(type="checkbox", id="uuid+%s"%v.uuid, CHECKED=flag, onchange="editRace.check(this)")
            tbl <= tr

        return str(root)

    def update_title(self, this):
        log.notice('update_title')
        val = this.value.strip()
        self.race.title = val
        self.cfg.write()

    def update_lanes(self, this):
        log.notice('update_lanes')
        val = int(this.value)
        self.race.lanes = val
        self.cfg.write()

    def check(self, this):
        log.notice('check')
        val = bool(this.value)
        (col, uuid) = this.id.split('+')
        if val:
            self.race.addVehicle(uuid)
        else:
            self.race.delVehicle(uuid)
        self.cfg.write()

################################################################################
##
##  RunRace
##
################################################################################
class RunRace(Page):
    title = "Run The Race"
    special = ''

    def _fget_race(self):
        return self._race
    def _fset_race(self, race):
        self._race = race
        self.title = "Run The Race: %s"%self._race.title
        clr = INPUT(type="button", id="clr+%s"%self._race.uuid, value="Clear", onclick="runRace.clear(this)")
        sav = INPUT(type="button", id="sav+%s"%self._race.uuid, value="Save",  onclick="runRace.save(this)")
        self.special = str(clr) + str(sav)
    race = property(fget=_fget_race, fset=_fset_race)

    def content(self):
        root = DIV(id='root')
        heatdiv = DIV(id="heatdiv")
        standiv = DIV(id="standiv")
        root <= heatdiv
        root <= standiv

        self.race.makeHeats()
        nHeats = len(self.race.heats)
        nLanes = self.race.lanes
        tbl = TABLE(id="heats")
        tr = TR()
        tr <= TH() <= 'Heat'
        for l in range(0, nLanes):
            tr <= TH() <= 'Lane %d'%(l+1)
        tbl <= tr

        for h in range(0, nHeats):
            tr = TR(id="heat%03d"%h)
            tr <= TD() <= "%d"%(h+1)
            for l in range(0, nLanes):
                res = self.race.heats[h][l]
                v = res.vehicle
                if 0 < res.position <= nLanes:
                    pos = str(res.position)
                else:
                    pos = ''
                td = TD()
                td <= v.vin
                td <= INPUT(id="%03d+%03d+%s"%(h,l,v.uuid), type="text",
                        value=pos, size="1", maxlength="1",
                        onblur="runRace.blur(this)",
                        onfocus="runRace.focus(this)",
                        onchange="runRace.update(this)")
                tr <= td
            tbl <= tr

        heatdiv <= tbl
        standiv <= self.standingsTable()

        return str(root)

    def standingsTable(self):
        for std in self.race.standings.values():
            std.points = 0

        nHeats = len(self.race.heats)
        nLanes = self.race.lanes
        for h in range(0, nHeats):
            for l in range(0, nLanes):
                heat = self.race.heats[h][l]
                if heat.position > 0:
                    std = self.race.standings[heat.vehicle.uuid]
                    std.points += 1 + nLanes - heat.position

        tbl = TABLE()
        tr = TR(id="standings")
        tr <= TH(Class="center") <= 'Points'
        tr <= TH(Class="center") <= 'Vehicle'
        tr <= TH(Class="left") <= 'Owner'
        tbl <= tr

        standings = self.race.standings.values()
        standings.sort(key=operator.attrgetter('points'), reverse=True)
        for s in standings:
            tr = TR()
            tr <= TD(Class="center") <= str(s.points)
            tr <= TD(Class="center") <= s.vehicle.vin
            tr <= TD(Class="left") <= s.vehicle.owner
            tbl <= tr

        return str(tbl)

    def focus(self, this):
        log.notice("runRace.focus() %s"%this.id)
        (h,l,uuid) = this.id.split('+')
        h = int(h)
        l = int(l)
        rowid = "heat%03d"%h
        row = document.getElementById(rowid)
        row.style.fontWeight = "bold"
        row.style.color = "#F2CA00"
        row.style.backgroundColor = "#1A417E"

    def blur(self, this):
        log.notice("runRace.blur() %s"%this.id)
        (h,l,uuid) = this.id.split('+')
        h = int(h)
        l = int(l)
        rowid = "heat%03d"%h
        row  = document.getElementById(rowid)
        row.style.fontWeight = "normal"
        row.style.color = "black"
        row.style.backgroundColor = "transparent"

    def update(self, this):
        log.notice("runRace.update() %s"%this.id)
        (h,l,uuid) = this.id.split('+')
        h = int(h)
        l = int(l)
        try:
            pos = int(this.value)
        except ValueError:
            pos = 0
        if not (1 <= pos <= self.race.lanes):
            pos = 0
            this.value = ''
        self.race.heats[h][l].position = pos

        document.getElementById('standiv').innerHTML = self.standingsTable()

    def clear(self, this):
        self.race.heats = None
        self.render()

    def save(self, this):
        log.notice("runRace.save()")
#        options = {
#            'multiple'         : False,
#            'title'            : "Save Race Results",
#            'files'            : True,
#            'directories'      : False,
#            'typesDescription' : "All files",
#            'defaultName'      : "%s.txt"%self.race.title,
#            'path'             : Titanium.Filesystem.getUserDirectory()
#        }
#        Titanium.UI.openSaveAsDialog(runRace.write, options)
        fname = os.path.join(APPDIR, '%s.txt'%(self.race.title,))
        self.write([fname])
        window.alert('Race results written to\n%s'%fname)

    def write(self, filelist):
        fname = filelist[0]
        log.notice("runRace.write() %s"%fname)
        try:
            fh = open(fname,'w')
        except IOError, e:
            window.alert("Can't write to %s\n%s"%(fname, e))
            return

        fh.write("Race Results: %s\n\n"%(self.race.title))
        standings = self.race.standings.values()
        standings.sort(key=operator.attrgetter('points'), reverse=True)
        for std in standings:
            fh.write("%d\t%s\t%s\n"%(std.points, std.vehicle.vin, std.vehicle.owner))
        fh.close()

################################################################################
##
##  DerbyRunner
##
################################################################################
log = Logger()
cfg = Config(CFGFILE)
cfg.read()

helpPage        = HelpPage(cfg)
homePage        = HomePage(cfg)
manageVehicles  = ManageVehicles(cfg)
manageRaces     = ManageRaces(cfg)
runRace         = RunRace(cfg)
editRace        = EditRace(cfg)

manageVehiclesSort = VehicleSort(cfg, manageVehicles.render)
editRaceSort       = VehicleSort(cfg, editRace.render)
