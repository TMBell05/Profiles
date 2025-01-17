"""
Manages data from a collection of flights or profiles at a specific location

Authors Brian Greene, Jessica Blunt, Tyler Bell, Gus Azevedo \n
Copyright University of Oklahoma Center for Autonomous Sensing and Sampling
2019

Component of Profiles v1.0.0
"""
import os
import netCDF4
import datetime as dt
import numpy as np
from metpy.units import units
from profiles.Profile import Profile
from profiles.Raw_Profile import Raw_Profile
from profiles.Thermo_Profile import Thermo_Profile
from profiles.Wind_Profile import Wind_Profile
import profiles.utils as utils
#from memory_profiler import profile
from copy import deepcopy


class Profile_Set():
    """ This class manages data (in the form of Profile objects) from one or
    many flights.

    :var Location location: information about the location of the flights
    :var list<Profile> profiles: list of Profile objects at this location
    :var bool ascent: True if data from the ascending leg of the profile is \
       to be used. If False, the descending leg will be processed instead
    :var bool dev: True if data from developmental flights is to be uploaded
    :var int resolution: the vertical resolution desired
    :var str res_units: the units in which the vertical resolution is given
    :var bool confirm_bounds: if True, the user will be asked to verify the \
       automatically-determined start, peak, and end times of each profile
    :var int profile_start_height: either passed to the constructor or \
       provided by the user during processing
    """

    def __init__(self, resolution=10, res_units='m', ascent=True,
                 dev=False, confirm_bounds=True, profile_start_height=None,
                 nc_level='none',
                 coefs_path=os.path.join(utils.package_path, "coefs")):
        """ Creates a Profiles object.

        :param int resolution: resolution to which data should be
           calculated in units of altitude or pressure
        :param str res_units: units of resolution in a format which can \
           be parsed by pint
        :param bool ascent: True to use ascending leg of flight, False to use \
           descending leg
        :param bool dev: True if data is from a developmental flight
        :param confirm_bounds: False to bypass user confirmation of \
           automatically identified start, peak, and end times
        :param int profile_start_height: if provided, the user will not be \
           prompted to enter the starting height for each profile separately.\
           This can be usefull when processing many profiles from the same \
           mission, but at least one profile should be processed without this \
           parameter to determine its correct value.
        :param str nc_level: either 'low', or 'none'. This parameter \
           is used when processing non-NetCDF files to determine which types \
           of NetCDF files will be generated. For individual files for each \
           Raw, Thermo, \
           and Wind Profile, specify 'low'. For no NetCDF files, specify \
           'none'. To generate a single, Profile_Set-level file, call \
           Profile_Set.save_netCDF where you are done adding data.
        """
        self.resolution = resolution
        self.res_units = res_units
        self.ascent = ascent
        self.dev = dev
        self.confirm_bounds = confirm_bounds
        self.profiles = []
        self.profile_start_height = profile_start_height
        self.meta = None
        self._nc_level = nc_level
        self.root_dir = ""
        self._base_start = None
        self.coefs_path = coefs_path

    def add_all_profiles(self, file_path, scoop_id=None,
                         meta_flight_path=None, meta_header_path=None):
        """ Reads a file, splits it in to several vertical profiles, and adds
        all Profiles to profiles

        :param str file_path: the data file
        :param str scoop_id: the identifier of the sensor package used
        """
        file_path = os.path.abspath(file_path)
        file_dir = os.path.dirname(file_path) + "/"
        if(self.root_dir is ""):
            self.root_dir = file_dir
        else:
            match_up_to = -1
            for i in range(len(self.root_dir)):
                if i < len(file_dir):
                    if self.root_dir[i] == file_dir[i]:
                        match_up_to = i
                    else:
                        # print(self.root_dir[i], file_dir[i])
                        break
                else:
                    # print(self.root_dir[:i-1], file_dir[:i-1])
                    break
            # print(self.root_dir)
            self.root_dir = self.root_dir[:match_up_to+2]
            # print(self.root_dir)
            self.root_dir = self.root_dir[:self.root_dir.rindex("/")+1]
            # print(self.root_dir)
        # Process altitude data for profile identification
        raw_profile_set = Raw_Profile(file_path, self.dev, scoop_id,
                                      nc_level=self._nc_level,
                                      meta_header_path=meta_header_path,
                                      meta_flight_path=meta_flight_path,
                                      coefs_path=self.coefs_path)
        pos = raw_profile_set.pos_data()

        # Identify the start, peak, and end indices of each profile
        index_list = utils.identify_profile(pos["alt_MSL"].magnitude,
                                            pos["time"], self.confirm_bounds,
                                            to_return=[],
                                            profile_start_height=self
                                            .profile_start_height)

        # Create a Profile object for each profile identified
        for profile_num in np.add(range(len(index_list)), 1):
            prof = Profile(file_path, self.resolution, self.res_units,
                           profile_num, self.ascent, self.dev,
                           self.confirm_bounds, index_list=index_list,
                           raw_profile=raw_profile_set,
                           profile_start_height=self.profile_start_height,
                           nc_level=self._nc_level,
                           base_start=self._base_start)
            self.profiles.append(prof)
            if self.meta is None:
                self.meta = prof.meta
            else:
                self.meta.combine(prof.meta)

            if self._base_start is None:
                self._base_start = self.profiles[-1]._base_start
                self.profiles = []
                # re-add with standardized start
                self.profiles.append(Profile(file_path, self.resolution,
                                             self.res_units, profile_num,
                                             self.ascent, self.dev,
                                             self.confirm_bounds,
                                             index_list=index_list,
                                             raw_profile=raw_profile_set,
                                             profile_start_height=self
                                             .profile_start_height,
                                             nc_level=self._nc_level,
                                             base_start=self._base_start,
                                             coefs_path=self.coefs_path))

        self.profiles.sort()
        print(len(self.profiles), "profile(s) including those added from file",
              file_path)

    def add_profile(self, file_path,
                    time=dt.datetime(dt.MINYEAR, 1, 1, tzinfo=None),
                    profile_num=None, scoop_id=None, meta_header_path=None,
                    meta_flight_path=None):
        """ Reads a file and creates a Profile for the first vertical profile
        after time OR for the profile_numth profile.

        :param string file_path: the data file
        :param datetime time: the time after which the profile begins
           (used only if profile_num is not specified)
        :param int profile_num: use the nth profile in the file
        :param str scoop_id: the identifier of the sensor package used
        """

        file_dir = os.path.dirname(file_path)
        if(self.root_dir is ""):
            self.root_dir = file_dir
        else:
            match_up_to = -1
            for i in range(len(self.root_dir)):
                if i < len(file_dir):
                    if self.root_dir[i] == file_dir[i]:
                        match_up_to = i
                    else:
                        # print(self.root_dir[i], file_dir[i])
                        break
                else:
                    # print(self.root_dir[:i-1], file_dir[:i-1])
                    break
            self.root_dir = os.path.dirname(self.root_dir[0:match_up_to+1])

        # Process altitude data for profile identification
        raw_profile = Raw_Profile(file_path, self.dev, scoop_id,
                                  nc_level=self._nc_level,
                                  meta_header_path=meta_header_path,
                                  meta_flight_path=meta_flight_path,
                                  coefs_path=self.coefs_path)
        pos = raw_profile.pos_data()

        # Identify the start, peak, and end indices of each profile
        index_list = utils.identify_profile(pos["alt_MSL"].magnitude,
                                            pos["time"], self.confirm_bounds,
                                            to_return=[])

        if(profile_num is None):
            self.profiles.append(Profile(file_path, self.resolution,
                                         self.res_units, 1,
                                         self.ascent, self.dev,
                                         self.confirm_bounds,
                                         index_list=index_list,
                                         raw_profile=raw_profile,
                                         profile_start_height=self
                                         .profile_start_height,
                                         nc_level=self._nc_level,
                                         coefs_path=self.coefs_path))
        else:
            for profile_num_guess in range(len(index_list)):
                # Check if this profile is the first to start after time
                if (index_list[profile_num_guess][0] >= time):
                    profile_num = profile_num_guess + 1
                    self.profiles.append(Profile(file_path, self.resolution,
                                         self.res_units, profile_num,
                                         self.ascent, self.dev,
                                         self.confirm_bounds,
                                         index_list=index_list,
                                         raw_profile=raw_profile,
                                         profile_start_height=self
                                         .profile_start_height,
                                         nc_level=self._nc_level,
                                         coefs_path=self.coefs_path))

                # No need to add any more profiles from this file
                break

        print(len(self.profiles), "profiles including profile number ",
              str(profile_num), " added from file", file_path)

    def merge(self, to_add):
        """ Loads all Profile objects from a pre-existing Profiles into this
        Profiles. All flights must be from the same location.

        :param Profiles to_add: the Profiles object to be merged in
        """

        if to_add.resolution != self.resolution or \
           to_add.res_units != self.res_units:
            print("NOTICE: All future Profiles added will have resolution "
                  + str(self.resolution*self.res_units))

        if to_add.ascent != self.ascent:
            if self.ascent:
                print("NOTICE: All future Profiles added will be treated as \
                      ascending")
            else:
                print("NOTICE: All future Profiles added will be treated as \
                      descending")

        if to_add.profile_start_height != self.profile_start_height:
            print("NOTICE: All future Profiles added will start at height "
                  + str(self.profile_start_height))

        if to_add.dev != self.dev:
            if self.dev:
                print("NOTICE: All future Profiles added will be considered \
                      developmental")
            else:
                print("NOTICE: All future Profiles added will be considered \
                      operational")

        if len(self.profiles) > 0:
            units = self.profiles[0]._units

        for new_profile in to_add.profiles:

            self.profiles.append(deepcopy(new_profile))  # this doesn't include units

    def read_netCDF(self, file_path):
        """ Re-creates a Profile_Set object which has been saved as a NetCDF

        :param string file_path: the NetCDF file
        """

        main_file = netCDF4.Dataset(file_path, "r", format="NETCDF4",
                                    mmap=False)
        self.dev = bool(main_file.dev)
        self.resolution = main_file.resolution
        self.res_units = main_file.res_units
        self.ascent = bool(main_file.ascent)
        groups = main_file.groups

        units.define('percent = 0.01*count = %')

        for profile_name in groups:
            profile_under_construction = Profile()
            profile_source = main_file[profile_name]

            #
            # Thermo
            #

            thermo_const = Thermo_Profile()  # Thermo_Profile underconstruction
            thermoExists = True  # Assume that there is thermo info until
            # there is evidence otherwise.

            # try:
            thermo_const.alt = np.array(profile_source.variables["alt"])\
                                   [np.array(profile_source.variables["alt"]) < 1e10] \
                * units.parse_expression(profile_source.variables["alt"]
                                         .units)
            thermo_const.pres = np.array(profile_source.variables["pres"])\
                                    [np.array(profile_source.variables["pres"]) < 1e10]\
                * units.parse_expression(profile_source.variables["pres"]
                                         .units)
            thermo_const.rh = np.array(profile_source.variables["rh"])\
                                  [np.array(profile_source.variables["rh"]) < 1e10] \
                * units.parse_expression(profile_source.variables["rh"]
                                         .units)
            thermo_const.temp = np.array(profile_source.variables["temp"])\
                                    [np.array(profile_source.variables["temp"]) < 1e10]\
                * units.parse_expression(profile_source.variables["temp"]
                                         .units)
            thermo_const.mixing_ratio = \
                np.array(profile_source.variables["mr"])[np.array(profile_source.variables["mr"]) < 1e10] \
                * units.parse_expression(profile_source.variables["mr"]
                                         .units)
            base_time = dt.datetime(2010, 1, 1, 0, 0, 0, 0)
            thermo_const.gridded_times = []
            for i in range(len(profile_source.variables["time"][:])):
                thermo_const.gridded_times.append(base_time + \
                                                  dt.timedelta(microseconds =
                                                               int(profile_source.variables["time"][i])))
                                                               # Hardcoded to microseconds since 2010-1-1

            profile_under_construction._thermo_profile = thermo_const
            # except Exception:
            #    thermoExists = False

            wind_const = Wind_Profile()
            windExists = True

            # try:
            wind_const.dir = np.array(profile_source.variables["dir"])\
                                 [np.array(profile_source.variables["dir"]) < 1e10] * \
                units.parse_expression(profile_source.
                                       variables["dir"].units)
            wind_const.speed = np.array(profile_source.variables["speed"])\
                                 [np.array(profile_source.variables["speed"]) < 1e10]\
                * units.parse_expression(profile_source.
                                         variables["speed"].units)
            wind_const.u = np.array(profile_source.variables["u"])\
                                 [np.array(profile_source.variables["u"]) < 1e10] * \
                units.parse_expression(profile_source.variables["u"].units)
            wind_const.v = np.array(profile_source.variables["v"])\
                                 [np.array(profile_source.variables["v"]) < 1e10] * \
                units.parse_expression(profile_source.variables["v"].units)
            wind_const.alt = np.array(profile_source.variables["alt"])\
                                 [np.array(profile_source.variables["alt"]) < 1e10] * \
                units.parse_expression(profile_source.variables["alt"]
                                       .units)
            wind_const.pres = np.array(profile_source.variables["pres"])\
                                 [np.array(profile_source.variables["pres"]) < 1e10] \
                * units.parse_expression(profile_source.variables["pres"]
                                         .units)
            wind_const.gridded_times = np.array(netCDF4.num2date
                                                (profile_source
                                                 .variables["time"][:],
                                                 units=profile_source
                                                 .variables["time"].units))
            profile_under_construction._wind_profile = wind_const
            # except Exception:
            #    windExists = False

            if thermoExists or windExists:
                self.profiles.append(profile_under_construction)
                print("Profile added with")
            if thermoExists:
                print("\tThermo_Profile")
            if windExists:
                print("\tWind_Profile")

        main_file.close()

    def save_netCDF(self, file_path):
        """ Stores all attributes of this Profile_Set object as a NetCDF

        :param string file_path: the file name to which attributes should be
           saved
        """
        main_file = netCDF4.Dataset(os.path.join(self.root_dir,
                                                 "processed", file_path),
                                    "w", format="NETCDF4", mmap=False)
        if self.meta is not None:
            self.meta.write_public_meta(
                os.path.join(self.root_dir,"processed", file_path)[:-3]
                + "_meta.txt")
        main_file.dev = str(self.dev)
        main_file.resolution = self.resolution
        main_file.res_units = self.res_units
        main_file.ascent = str(self.ascent)

        for i in range(len(self.profiles)):
            profile_group = main_file.createGroup("Profile" + str(i))
            profile_group.createDimension("time", None)

            #
            # Thermo
            #

            thermo = self.profiles[i]._thermo_profile

            if thermo is not None:

                # RH
                try:
                    rh_var = profile_group.createVariable("rh", "f8",
                                                          ("time",))
                    rh_var[:] = thermo.rh.magnitude
                    rh_var.units = str(thermo.rh.units)
                except Exception:
                    print("")
                # TEMP
                try:
                    temp_var = profile_group.createVariable("temp", "f8",
                                                            ("time",))
                    temp_var[:] = thermo.temp.magnitude
                    temp_var.units = str(thermo.temp.units)
                except Exception:
                    print("")
                # MIXING RATIO
                try:
                    mr_var = profile_group.createVariable("mr", "f8",
                                                          ("time",))
                    mr_var[:] = thermo.mixing_ratio.magnitude
                    mr_var.units = str(thermo.mixing_ratio.units)
                except Exception:
                    print("")
                # TIME
                try:
                    time_var = profile_group.createVariable("time", "f8",
                                                            ("time",))
                    time_var[:] = netCDF4.date2num(thermo.gridded_times,
                                                   units='microseconds since \
                                                   2010-01-01 00:00:00:00')
                    time_var.units = \
                        'microseconds since 2010-01-01 00:00:00:00'
                except Exception:
                    print("")
                # ALT
                try:
                    alt_var = profile_group.createVariable("alt", "f8",
                                                           ("time",))
                    alt_var[:] = thermo.alt.magnitude
                    alt_var.units = str(thermo.alt.units)
                except Exception:
                    print("")
                # PRES
                try:
                    pres_var = profile_group.createVariable("pres", "f8",
                                                            ("time",))
                    pres_var[:] = thermo.pres.magnitude
                    pres_var.units = str(thermo.pres.units)
                except Exception:
                    print("")

            #
            # Wind
            #

            wind = self.profiles[i]._wind_profile

            if wind is not None:

                # DIRECTION
                try:
                    dir_var = profile_group.createVariable("dir", "f8",
                                                           ("time",))
                    dir_var[:] = wind.dir.magnitude
                    dir_var.units = str(wind.dir.units)
                except Exception:
                    print("")
                # SPEED
                try:
                    spd_var = profile_group.createVariable("speed", "f8",
                                                           ("time",))
                    spd_var[:] = wind.speed.magnitude
                    spd_var.units = str(wind.speed.units)
                except Exception:
                    print("")
                # U
                try:
                    u_var = profile_group.createVariable("u", "f8",
                                                         ("time",))
                    u_var[:] = wind.u.magnitude
                    u_var.units = str(wind.u.units)
                except Exception:
                    print("")
                # V
                try:
                    v_var = profile_group.createVariable("v", "f8", ("time",))
                    v_var[:] = wind.v.magnitude
                    v_var.units = str(wind.v.units)
                except Exception:
                    print("")
                # PRES
                try:
                    pres_var = profile_group.createVariable("pres", "f8",
                                                            ("time",))
                    pres_var[:] = wind.pres.magnitude
                    pres_var.units = str(wind.pres.units)
                except Exception:
                    print("")
                # TIME
                try:
                    time_var = profile_group.createVariable("time", "f8",
                                                            ("time",))
                    time_var[:] = netCDF4.date2num(wind.gridded_times,
                                                   units='microseconds since \
                                                   2010-01-01 00:00:00:00')
                    time_var.units = \
                        'microseconds since 2010-01-01 00:00:00:00'
                except Exception:
                    print("")
                # ALT
                try:
                    alt_var = profile_group.createVariable("alt", "f8",
                                                           ("time",))
                    alt_var[:] = wind.alt.magnitude
                    alt_var.units = str(wind.alt.units)
                except Exception:
                    print("")


        #
        # META
        #
        if self.meta is not None:
            # print("\n\n" + str(self.meta.public_fields) + "\n\n")
            for key in np.unique(self.meta.public_fields):
                if self.meta.get(key) is not None:
                    # print(key)
                    main_file.key = self.meta.get(key)
                    main_file.renameAttribute("key", key)

        main_file.close()

    def __str__(self):
        to_return = "=====================================================\n" \
                    + "Profile Set with " + str(len(self.profiles)) + \
                    " Profiles\n"
        for profile in self.profiles:
            to_return = to_return + "\t" + str(profile) + "\n"
        return to_return
