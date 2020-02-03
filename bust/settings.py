import os
import logging
from collections import OrderedDict


class Settings(object):
    """ Class for containing paths and other settings """

    def __init__(self, json_path, settings):
        self.logger = logging.getLogger(__name__)

        if json_path is None and settings is None:
            self.logger.info("No input to Settings. Using default settings.")
            self.json_path = ""
            self.project_path = ""
            self.json_name = ""
            self.mod_subdir = True
            self.bus_subdir = True
            self.uvvm_relative_path = None
            self.coverage = False
        else:

            self.json_path = json_path
            json_dir, file_name = os.path.split(json_path)

            self.json_name = file_name

            if 'proj_dir' not in settings:
                self.project_path = json_dir
            else:
                self.project_path = settings['proj_dir']

            if 'mod_subdir' not in settings:
                self.logger.warning('Module subdir setting not specified. Choosing default: True')
                self.mod_subdir = True
            else:
                self.mod_subdir = settings['mod_subdir']

            if 'bus_subdir' not in settings:
                self.logger.warning('Bus subdir setting not specified. Choosing default: True')
                self.bus_subdir = True
            else:
                self.bus_subdir = settings['bus_subdir']

            if 'uvvm_relative_path' not in settings:
                self.logger.warning("UVVM Path is not specified. No testbench can be generated!")
                self.uvvm_relative_path = None
            else:
                self.uvvm_relative_path = settings['uvvm_relative_path']

            if 'coverage' not in settings:
                self.logger.warning("Coverage is not specified. Choosing default: False")
                self.coverage = False
            else:
                self.coverage = settings['coverage']

        self.hdl_dir = 'hdl'
        self.script_dir = 'scripts'
        self.tb_dir = 'tb'
        self.doc_dir = 'doc'
        self.header_dir = 'header'
        self.sim_dir = 'sim'


    def return_JSON(self):
        json = OrderedDict()
        json['mod_subdir'] = self.mod_subdir
        json['bus_subdir'] = self.bus_subdir
        if self.uvvm_relative_path is not None:
            json['uvvm_relative_path'] = self.uvvm_relative_path
        json['coverage'] = self.coverage
        return json

    def return_sim_bus_path(self, bus_type):
        """ Return bus path used for simulation compilation scripts """
        path = "../"
        if self.bus_subdir:
            path = os.path.join(path, "../{}/".format(bus_type))
        return path

    def return_sim_uvvm_path(self):
        """ Return UVVM path used for simulation compilation script """
        # Must add one extra subdir because of scripts/
        path = "../"
        path = os.path.join(path, self.uvvm_relative_path)
        return path