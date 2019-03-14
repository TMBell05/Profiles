"""
Reads data file (JSON or netCDF) and stores the raw data

Authors Brian Greene, Jessica Wiedemeier, Tyler Bell, Gus Azevedo \n
Copyright University of Oklahoma Center for Autonomous Sensing and Sampling
2019
"""

import pint
import json
import numpy as np
from datetime import datetime as dt

units = pint.UnitRegistry()


class Raw_Profile():
    """ Contains data from one file. Data is stored as a pandas DataFrame.

    :var tuple temp: temperature as (voltage1, voltage2, ..., time: ms)
    :var tuple rh: relative humidity as (rh1, T1, rh2, T2, ..., time: ms)
    :var tuple co2: CO2 data as (CO2, CO2, ..., time: ms)
    :var tuple gps: GPS data as (lat, lon, alt_MSL, time: ms)
    :var tuple pres: barometer data as (pres, temp, ground_temp, alt_AGL,
                                        time: ms)
    :var tuple rotation: UAS position data as (roll, pitch, yaw, time:ms)
    :var bool dev: True if the data is from a developmental flight
    """

    def __init__(self, file_path, dev=False):
        """ Creates a Raw_Profile object and reads in data in the appropiate
        format.
        """
        self.temp = None
        self.rh = None
        self.temp_rh = None
        self.co2 = None
        self.gps = None
        self.pres = None
        self.rotation = None
        self.dev = dev
        if "json" in file_path or "JSON" in file_path:
            self._read_JSON(file_path)
        elif "csv" in file_path or "CSV" in file_path:
            self._read_netCDF

    def gps_data(self):
        """ Gets data needed by the Profile constructor.

        rtype: dict
        return: {"lat":, "lon":, "alt_MSL":, "time":}
        """

        return {"lat": self.gps[0] * units.degree, "lon": self.gps[1] *
                units.degree, "alt_MSL": self.gps[2] * units.m, "time":
                dt.fromtimestamp(self.gps[3])}

    def thermo_data(self):
        """ Gets data needed by the Thermo_Profile constructor.

        rtype: list
        return: [temp, rh, pres]
        """

    def co2_data(self):
        """ Gets data needed by the CO2_Profile constructor.

        rtype: list
        return: [co2, temp, rh]
        """

    def wind_data(self):
        """ Gets data needed by the Wind_Profile constructor.

        rtype: list
        return: [rotation]
        """

    def _read_JSON(self, file_path):
        """ Reads data from a .JSON file. Called by the constructor.
        """

        # Read the file into a list which pandas can normalize and read
        full_data = []
        for line in open(file_path, 'r'):
            full_data.append(json.loads(line))

        """
        Now full_data is a list of JSON element with 2 dictionaries each. If
        we refer to one JSON element as "tweet", the structure can be described
        as follows:

        tweet["meta"] contains "timestamp" and "type".

        tweet["data"] depends on tweet["meta"]["type"]. IMET, for example,
        could contain
            Temp1, float, 1, 286.2941589355469
            Temp2, float, 1, 286.27020263671875
            Temp3, float, 1, 286.0711364746094
            Temp4, float, 1, 0.0
            Time, int, 1, 60898080
            Volt1, float, 1, 4441.3125
            Volt2, float, 1, 4431.5625
            Volt3, float, 1, 4429.875
            Volt4, float, 1, 0.0

        Next, we iterate through full_data and identify line containing the
        types we want to keep. We then extract the data from each element
        using a different code for each type.
        """
        temp_list = None
        rh_list = None
        co2_list = None
        gps_list = None
        pres_list = None
        rotation_list = None
        # sensor_names will be dictionary of dictionaries formatted
        # {
        #     "IMET": {name: index, name: index, ...},
        #     "RHUM": {name: index, name: index, ...},
        #     ...
        # }
        sensor_names = {}
        for elem in full_data:

            # IMET -> Temperature
            if elem["meta"]["type"] == "IMET":

                # First time only - setup temp_list
                if temp_list is None:
                    # Create array of lists with one list per temperature
                    # sensor reported in the data file, plus one for times
                    temp_list = [[] for x in range(sum('Volt' in s for s in
                                 elem["data"].keys())+1)]

                    sensor_names["IMET"] = {}
                    # Determine field names
                    sensor_numbers = np.add(range(len(temp_list)-1), 1)
                    for num in sensor_numbers:
                        sensor_names["IMET"]["Volt"+str(num)] = num - 1
                    sensor_names["IMET"]["Time"] = -1

                # Read fields into temp_list, including Time
                for key, value in sensor_names["IMET"].items():
                    try:
                        if 'Time' in key:
                            time = dt.fromtimestamp(elem["meta"]["timestamp"])
                            if time.year < 2000:
                                raise KeyError("Time formatted incorrectly")
                            else:
                                temp_list[value].append(time)
                        else:
                            temp_list[value].append(elem["data"][key])
                    except KeyError:
                        temp_list[value].append(np.nan)

            # Humidity
            elif elem["meta"]["type"] == "RHUM":

                # First time only - setup rh_list and temp_rh_list
                if rh_list is None:
                    # Create array of lists with one list per RH
                    # sensor reported in the data file, plus one for times
                    rh_list = [[] for x in range(sum('Humi' in s for s in
                               elem["data"].keys()) * 2 + 1)]

                    sensor_names["RHUM"] = {}
                    # Determine field names
                    sensor_numbers = np.add(range(int((len(rh_list)-1)/2)), 1)
                    for num in sensor_numbers:
                        sensor_names["RHUM"]["Humi"+str(num)] = 2*num - 2
                        sensor_names["RHUM"]["Temp"+str(num)] = 2*num - 1
                    sensor_names["RHUM"]["Time"] = -1

                # Read fields into rh_list, including Time
                for key, value in sensor_names["RHUM"].items():
                    try:
                        if 'Time' in key:
                            time = dt.fromtimestamp(elem["meta"]["timestamp"])
                            if time.year < 2000:
                                raise KeyError("Time formatted incorrectly")
                            else:
                                rh_list[value].append(time)
                        else:
                            rh_list[value].append(elem["data"][key])
                    except KeyError:
                        rh_list[value].append(np.nan)

            # CO2
            elif elem["meta"]["type"] == "CO2":
                # TODO
                if co2_list is None:
                    co2_list = []

            # GPS
            elif elem["meta"]["type"] == "GPS":

                # First time only - setup gps_list
                if gps_list is None:
                    # Create array of lists with one list per [lat, lon, alt,
                    # time]
                    gps_list = [[] for x in range(4)]

                    sensor_names["GPS"] = {}

                    # Determine field names
                    sensor_names["GPS"]["Lat"] = 0
                    sensor_names["GPS"]["Lng"] = 1
                    sensor_names["GPS"]["Alt"] = 2
                    sensor_names["GPS"]["TimeUS"] = 3

                # Read fields into gps_list, including TimeUS
                for key, value in sensor_names["GPS"].items():
                    try:
                        if 'Time' in key:
                            time = dt.fromtimestamp(elem["meta"]["timestamp"])
                            if time.year < 2000:
                                raise KeyError("Time formatted incorrectly")
                            else:
                                gps_list[value].append(time)
                        else:
                            gps_list[value].append(elem["data"][key])
                    except KeyError:
                        gps_list[value].append(np.nan)

            # BARO -> Pressure
            elif elem["meta"]["type"] == "BARO":

                # First time only - setup gps_list
                if pres_list is None:
                    # Create array of lists with one list per [pres, temp,
                    # ground_temp, alt, time]
                    pres_list = [[] for x in range(5)]

                    sensor_names["BARO"] = {}

                    # Determine field names
                    sensor_names["BARO"]["Press"] = 0
                    sensor_names["BARO"]["Temp"] = 1
                    sensor_names["BARO"]["GndTemp"] = 2
                    sensor_names["BARO"]["Alt"] = 3
                    sensor_names["BARO"]["TimeUS"] = 4

                # Read fields into pres_list, including TimeUS
                for key, value in sensor_names["BARO"].items():
                    try:
                        if 'Time' in key:
                            time = dt.fromtimestamp(elem["meta"]["timestamp"])
                            if time.year < 2000:
                                raise KeyError("Time formatted incorrectly")
                            else:
                                pres_list[value].append(time)
                        else:
                            pres_list[value].append(elem["data"][key])
                    except KeyError:
                        pres_list[value].append(np.nan)

            # ATT -> Rotation
            elif elem["meta"]["type"] == "ATT":

                # First time only - setup gps_list
                if rotation_list is None:
                    # Create array of lists with one list per [roll, pitch,
                    # yaw, time]
                    rotation_list = [[] for x in range(4)]

                    sensor_names["ATT"] = {}

                    # Determine field names
                    sensor_names["ATT"]["Roll"] = 0
                    sensor_names["ATT"]["Pitch"] = 1
                    sensor_names["ATT"]["Yaw"] = 2
                    sensor_names["ATT"]["TimeUS"] = 3

                # Read fields into rotation_list, including TimeUS
                for key, value in sensor_names["ATT"].items():
                    try:
                        if 'Time' in key:
                            time = dt.fromtimestamp(elem["meta"]["timestamp"])
                            if time.year < 2000:
                                raise KeyError("Time formatted incorrectly")
                            else:
                                rotation_list[value].append(time)
                        else:
                            rotation_list[value].append(elem["data"][key])
                    except KeyError:
                        rotation_list[value].append(np.nan)

        self.temp = tuple(temp_list)
        self.rh = tuple(rh_list)
        self.gps = tuple(gps_list)
        self.pres = tuple(pres_list)
        self.rotation = tuple(rotation_list)

        self._save_netCDF()

    def _read_netCDF(self):
        """ Reads data from a NetCDF file. Called by the constructor.
        """

    def _save_netCDF(self):
        """ Save a NetCDF file to facilitate future processing if a .JSON was
        read.
        """
