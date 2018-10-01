import json
import logging
import os
import sys

from flask_helpers.ErrorHandler import ErrorHandler
from flask import Flask
from Persistence.PersistenceEngine import PersistenceEngine


class Configurator(object):
    """
    Provides a configuration control to enable the Python Cowbull Server to execute_load
    configuration from a set of variables or from a configuration file.
    """

    def __init__(self):
        self.app = None
        self.configuration = {}
        self.error_handler = None
        self.env_vars = [
            {
                "name": "PERSISTER",
                "description": "The persistence engine object",
                "required": False,
                "default": '{"engine_name": "redis", "parameters": {"host": "redis-master", "port": 6379, "db": 0}}',
                "caster": PersistenceEngine
            },
            {
                "name": "FLASK_HOST",
                "description": "For debug purposes, defines the Flask host. Default is 0.0.0.0",
                "required": False,
                "default": "0.0.0.0"
            },
            {
                "name": "FLASK_PORT",
                "description": "For debug purposes, the port Flask should serve on. Default is 5000",
                "required": False,
                "default": 5000,
                "caster": int
            },
            {
                "name": "FLASK_DEBUG",
                "description": "For debug purposes, set Flask into debug mode.",
                "required": False,
                "default": True,
                "caster": bool
            },
            {
                "name": "COWBULL_DRY_RUN",
                "description": "Do not run the server, simply report the configuration that would "
                               "be used to run it.",
                "required": False,
                "default": False,
                "caster": bool
            },
            {
                "name": "COWBULL_CUSTOM_MODES",
                "description": "A file which defines additional "
                               "modes to be defined in addition to the default modes. The "
                               "file must be a list of JSON objects containing mode "
                               "definitions. Each object must contain (at a minimum): mode, digits, and "
                               "priority",
                "required": False,
                "default": None,
                "caster": self._load_from_json
            }
        ]

    def execute_load(self, app):
        if app is None:
            raise ValueError("The Flask app must be passed to the Configurator")
        if not isinstance(app, Flask):
            raise TypeError("Expected a Flask object")

        self.app = app
        self.app.config["PYTHON_VERSION_MAJOR"] = sys.version_info[0]

        self.app.config["LOGGING_FORMAT"] = os.getenv(
            "logging_format",
            os.getenv("LOGGING_FORMAT", "%(asctime)s %(levelname)s: %(message)s")
        )
        self.app.config["LOGGING_LEVEL"] = os.getenv(
            "logging_level",
            os.getenv("LOGGING_LEVEL", logging.WARNING)
        )

        self.error_handler = ErrorHandler(
            module="Configurator",
            method="__init__",
            level=self.app.config["LOGGING_LEVEL"],
            format=self.app.config["LOGGING_FORMAT"]
        )

        self.error_handler.log(
            message="Initialized logging (level: {}, format: {})"
                .format(
                    self.app.config["LOGGING_LEVEL"],
                    self.app.config["LOGGING_FORMAT"]
                ),
            logger=logging.info
        )

        self.error_handler.log(message="Configuring environment variables.", logger=logging.info)

        self.configuration = {}

        config_file = self._set_config(
            source=os.getenv,
            name="COWBULL_CONFIG"
        )
        self.app.config["COWBULL_CONFIG"] = config_file

        self.error_handler.log(
            message="Loading configuration from: {}".format(
                config_file if config_file else "environment variables"
            )
        )

        source = {}
        if config_file:
            _file = open(config_file, 'r')
            try:
                source = json.load(_file)
            except:
                raise
            finally:
                _file.close()

        self.load_variables(source=source)

    def get_variables(self):
        return [
                   ("LOGGING_LEVEL", "An integer representing the Python "
                                     "logging level (e.g. 10 for debug, 20 for warning, etc.)"),
                   ("LOGGING_FORMAT", "The format for logs. The default is >> "
                                      "%(asctime)s %(levelname)s: %(message)s"),
                   ("COWBULL_CONFIG", "A path and filename of a configuration file "
                                      "used to set env. vars. e.g. /path/to/the/file.cfg")
               ]\
               + [(i["name"], i["description"]) for i in self.env_vars]

    def dump_variables(self):
        return [
                   ("LOGGING_LEVEL", self.app.config["LOGGING_LEVEL"]),
                   ("LOGGING_FORMAT", self.app.config["LOGGING_FORMAT"]),
                   ("COWBULL_CONFIG", self.app.config["COWBULL_CONFIG"])
               ] \
               + \
               [(i["name"], self.app.config[i["name"]]) for i in self.env_vars]

    def print_variables(self):
        print('')
        print('=' * 80)
        print('=', ' '*30, 'CONFIGURATION', ' '*31, '=')
        print('=' * 80)
        print('The following environment variables may be set to dynamically configure the')
        print('server. Alternately, these can be defined in a file and passed using the env.')
        print('var. COWBULL_CONFIG. Please note, the file must be a JSON data object.')
        print('')
        print('Please note. Env. Var. names can be *ALL* lowercase or *ALL* uppercase.')
        print('')
        print('-' * 80)
        print('| Current configuration set:')
        print('-' * 80)
        for name, val in self.dump_variables():
            outstr = "| {:20s} | {}".format(name, val)
            print(outstr)
        print('-' * 80)
        print('')

    def load_variables(self, source=None):
        if source:
            _fetch = source.get
        else:
            _fetch = os.getenv

        for item in self.env_vars:
            if isinstance(item, dict):
                self._set_config(
                    source=_fetch,
                    **item
                )
            elif isinstance(item, str):
                self._set_config(
                    name=item,
                    source=_fetch
                )
            elif isinstance(item, list):
                self.load_variables(source=item)
            else:
                raise TypeError("Unexpected item in configuration: {}, type: {}".format(item, type(item)))

    def _set_config(
            self,
            source=None,
            name=None,
            description=None,
            required=None,
            default=None,
            errmsg=None,
            caster=None,
            choices=None
    ):
        value = source(
            name.lower(),
            source(name.upper(), None)
        )

        if required and value is None and default is None:
            raise ValueError(
                errmsg or
                "Problem fetching config item: "
                "{}. It is required and was not found or the value was None.".format(name)
            )

        if value is None:
            value = default

        if caster:
            if caster == PersistenceEngine:
                if not isinstance(value, dict):
                    #
                    # Added .replace to remove single quotes being added by PyCharm
                    #
                    value = json.loads(str(value).replace("'", ""))
                value = caster(**value)
            else:
                value = caster(value)

        if choices:
            if value not in choices:
                raise ValueError(
                    errmsg or
                    "The configuration value for {}({}) is not in the list of choices: ()".format(
                        name,
                        value,
                        choices
                    )
                )

        self.app.config[name] = value
        return value

    def _load_from_json(self, json_file_name):
        if not json_file_name:
            return None

        f = None
        return_value = None

        try:
            f = open(json_file_name, 'r')
            return_value = json.load(f)
        except Exception as e:
            self.error_handler.error(
                module="Configurator.py",
                method="_load_from_json",
                status=500,
                exception=repr(e),
                message="An exception occurred!"
            )
            raise IOError(
                "A JSON file ({}) cannot be loaded. Exception: {}".format(
                    json_file_name,
                    repr(e)
                )
            )
        finally:
            if f:
                f.close()
        return return_value
