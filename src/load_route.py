# -*- coding: utf- -*-
import os
import json
import throwble
import logging
import math
import re
from grab import Grab
from encode import MyEncoder


class IRoutesLoader(object):

    def _saveToCache(self, city, routeID, routeData):
        fName = "cache/" + city + "/" + routeID + ".json"
        logging.info("Save route data to cache: %s", fName)
        try:
            os.makedirs('cache/' + city)
        except OSError:
            pass
        f = open(fName, 'w')
        f.write(json.dumps(routeData, ensure_ascii=False))
        f.close()
        logging.info("ok.")

    def _saveRoutesList(self, city, routesList):
        f = open("cache/routes_scheme_" + city + ".dat", "w")
        for list in routesList:
            f.write("\ntype: " + list["type"] + "\n")

            for r in list["list"]:
                f.write("Number : " + r["name"] + ", ID : " + r["id"] + "\n")
        f.close()

    def getRouteData(self, city, routeID):
        pass


class ServerRoutesLoader(IRoutesLoader):
    _grabber = None

    def __init__(self, proxy):
        self._grabber = Grab(log_dir='logs/')
        self._grabber.setup(debug=True)
        self._grabber.setup(proxy=proxy, proxy_type='http')
        self._grabber.setup(headers={'Accept-Language':
                            'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4'})
        self._grabber.setup(headers={'X-Requested-With': 'XMLHttpRequest'})

    def getRouteData(self, city, routeID):
        encoder = MyEncoder()
        langs = ["ru", "en", "ua"]
        routeData = {}
        logging.debug("get route data from eway-server...")
        for lang in langs:
            self._grabber.go('http://www.eway.in.ua/' + lang + '/cities/' +
                             city + '/routes/' + routeID)
            self._grabber.go('http://www.eway.in.ua/ajax/GetRouteData.php?id=' +
                             routeID + '&city=' + city)
            data = self._grabber.response.body
            data = encoder.decode(data)
            data = data[10:len(data) - 10]
            data = encoder.decode(data)
            data = data[10:len(data) - 10]
            data = encoder.decode(data)
            routeData[lang] = json.loads(data)
        self._saveRoutesList(city, routeData["ru"]["routesList"])
        logging.debug("ok.")
        return routeData


class TestRoutesLoader(IRoutesLoader):
    _testDir = None

    def __init__(self, testDir):
        self._testDir = testDir
        pass

    def getRouteData(self, city, routeID):
        encoder = MyEncoder()
        langs = ['ru', 'en', 'ua']
        routeData = {}
        for lang in langs:
            data = open(self._testDir + "/routeData.json", 'r').read()
            data = encoder.decode(data)
            data = data[10:len(data) - 10]
            data = encoder.decode(data)
            data = data[10:len(data) - 10]
            data = encoder.decode(data)
            routeData[lang] = json.loads(data)
        self._saveRoutesList(city, routeData["ru"]["routesList"])
        return routeData


class CacheRoutesLoader(IRoutesLoader):

    def __init__(self):
        pass

    def getRouteData(self, city, routeID):
        fName = "cache/" + city + "/" + routeID + ".json"
        try:
            f = open(fName, 'r')
            routeData = json.loads(f.read())
            f.close()
        except Exception:
            return None
        return routeData


class RoutesLoader(IRoutesLoader):
    _loader = None
    _cacheLoader = None
    _isSave = False

    def __init__(self, options):
        logging.debug(options)
        if options.load_mode == "server":
            self._loader = ServerRoutesLoader(options.proxy)
            self._isSave = True
        elif options.load_mode == "cache":
            self._cacheLoader = CacheRoutesLoader()
        elif options.load_mode == "server_cache":
            self._loader = ServerRoutesLoader(options.proxy)
            self._cacheLoader = CacheRoutesLoader()
            self._isSave = True
        elif options.load_mode == "test":
            if options.test_res is "":
                raise throwble.ConcoleArgsException(
                    "You mast set  the argument --test_res, for [test] mode.")
            self._loader = TestRoutesLoader(options.test_res)

    def getRouteData(self, city, routeID):
        routeData = None
        if self._cacheLoader is not None:
            routeData = self._cacheLoader.getRouteData(city, routeID)
        if routeData is None and self._loader is not None:
            routeData = self._loader.getRouteData(city, routeID)
            if routeData is not None and self._isSave is True:
                self._saveToCache(city, routeID, routeData)
        return routeData


class ImportRouteModel(dict):

    def _getServerLang(self, lang):
        serv_lang = "c_uk" if lang == "ua" else ("c_" + lang)
        return serv_lang

    def _parseWorkTime(self, wtimeStr):
        # 07:30 - 19:30
        logging.debug("Parsing string(work time): %s ", wtimeStr)
        p = re.compile(r'(?P<hh>[0-9]+):(?P<mm>[0-9]+)')
        work_time = []
        for m in p.finditer(wtimeStr):
            logging.debug(m.group("hh"))
            logging.debug(m.group("mm"))
            work_time.append(
                int(m.group("hh")) * 3600 + int(m.group("mm")) * 60)
        return (work_time[0], work_time[len(work_time) - 1])

    def _parseInterval(self, intervalStr):
        # 30-45
        logging.debug("Parsing string(interval): %s ", intervalStr)
        p = re.compile(r'(?P<time>[0-9]+)')
        m = p.match(intervalStr)
        interval = []
        for m in p.finditer(intervalStr):
            logging.debug(m.group("time"))
            interval.append(int(m.group("time")) * 60)
        return (interval[0], interval[len(interval) - 1])

    def parseRouteType(self, routeTypeStr):
        routeType = "c_route_"
        if routeTypeStr == "trol":
            return routeType + "trolley"
        return routeType + routeTypeStr

    def __init__(self, cityKey, routeData):
        rData = routeData["ru"]
        self["cityKey"] = cityKey
        self["cost"] = rData["price"]
        self["routeType"] = self.parseRouteType(
            rData["transportType"]["type"])
        self["routeID"] = rData["id"]
        self["number"] = rData["number"]

        (t_start, t_finish) = self._parseWorkTime(rData["workTime"])
        (interval_min, interval_max) = self._parseInterval(rData["interval"])
        self["timeStart"] = t_start
        self["timeFinish"] = t_finish
        self["intervalMin"] = interval_min
        self["intervalMax"] = interval_max

        self["directStations"] = []
        self["directRelations"] = []
        self["reverseStations"] = []
        self["reverseRelations"] = []

        logging.info("Routes ID: %s", self["routeID"])
        logging.info("Routes number: %s", self["number"])
        logging.info("Routes cost: %s", self["cost"])
        logging.info("Routes interval: (%d secs - %d secs)", self[
                     "intervalMin"], self["intervalMax"])
        logging.info("Routes work time: (%d secs - %d secs)", self[
                     "timeStart"], self["timeFinish"])
        i = 0

        # Сформируем станции
        for stop in rData["stops"]:
            if type(stop["forward"]) is dict and stop["forward"]["lat"] is not None:
                dStation = {}
                dStation["location"] = {
                    "x": float(stop["forward"]["lat"]),
                    "y": float(stop["forward"]["lng"])
                }
                dStation["names"] = []
                logging.debug("Direct station: %s", stop["forward"]["name"])
                for lang in routeData:
                    name_val = routeData[lang]["stops"][i]["forward"]["name"]
                    name_val = name_val.replace("\"", "")
                    name = {
                        "lang_id": self._getServerLang(lang),
                        "value": name_val
                    }
                    dStation["names"].append(name)
                self["directStations"].append(dStation)
            if type(stop["backward"]) is dict and stop["backward"]["lat"] is not None:
                dStation = {}
                dStation["location"] = {
                    "x": float(stop["backward"]["lat"]),
                    "y": float(stop["backward"]["lng"])
                }
                dStation["names"] = []
                logging.debug("Reverse station: %s", stop["backward"]["name"])
                for lang in routeData:
                    name_val = routeData[lang]["stops"][i]["backward"]["name"]
                    name_val = name_val.replace("\"", "")
                    name = {
                        "lang_id": self._getServerLang(lang),
                        "value": name_val
                    }

                    dStation["names"].append(name)
                self["reverseStations"].append(dStation)
            i += 1

        # Сформируем polylines
        lastPointInd = -1
        for st in self["directStations"]:
            currPointInd = self._getNearestPointInd(
                st, rData["points"]["forward"])
            if lastPointInd >= 0:
                points = []
                for p in rData["points"]["forward"][lastPointInd: currPointInd + 1]:
                    points.append({"x": p["lat"], "y": p["lng"]})
                self["directRelations"].append({"points": points})
            lastPointInd = currPointInd

        lastPointInd = -1
        for st in self["reverseStations"]:
            currPointInd = self._getNearestPointInd(
                st, rData["points"]["backward"])
            if lastPointInd >= 0:
                points = []
                for p in rData["points"]["backward"][lastPointInd: currPointInd + 1]:
                    points.append({"x": p["lat"], "y": p["lng"]})
                self["reverseRelations"].append({"points": points})
            lastPointInd = currPointInd

    def _distance(self, p1, p2):
        lat1 = float(p1["x"])
        lat2 = float(p2["x"])
        lon1 = float(p1["y"])
        lon2 = float(p2["y"])
        return math.sqrt((lat1 - lat2) * (lat1 - lat2) + (lon1 - lon2) * (lon1 - lon2))

    def _getNearestPointInd(self, station, points):
        st_location = station["location"]
        i = 0
        min_ind = 0
        min_distance = self._distance(
            st_location, {"x": points[0]["lat"], "y": points[0]["lng"]})
        for p in points:
            curr_dist = self._distance(
                st_location, {"x": p["lat"], "y": p["lng"]})
            if min_distance > curr_dist:
                min_distance = curr_dist
                min_ind = i
            i += 1
        return min_ind
