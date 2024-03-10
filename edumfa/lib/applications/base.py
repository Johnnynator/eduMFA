# -*- coding: utf-8 -*-
#
# License:  AGPLv3
# This file is part of eduMFA. eduMFA is a fork of privacyIDEA which was forked from LinOTP.
# Copyright (c) 2024 eduMFA Project-Team
# Previous authors by privacyIDEA project:
#
# 2014 Cornelius Kölbel
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import sys
import os
from edumfa.lib.log import log_with
import edumfa.lib.applications
from edumfa.lib.policy import TYPE
from importlib import import_module

log = logging.getLogger(__name__)


def get_machine_application_class_list():
    """
    Get the list of class names of applications like
    "lib.applications.luks.MachineApplication".

    :return: list of application class names
    :rtype: list
    """
    class_list = []
    # We add each python module in this directory to the class list
    path = os.path.dirname(edumfa.lib.applications.__file__)
    files = os.listdir(path)
    modules = [
        f.split(".")[0] for f in files if f.endswith(".py") and f != "__init__.py"
    ]
    for module in modules:
        class_list.append(f"edumfa.lib.applications.{module!s}.MachineApplication")
    return class_list


def get_machine_application_class_dict():
    """
    get a dictionary of the application classes with the type as the key.

    :return: {'base':
                <class
                'edumfa.lib.applications.base.MachineApplicationBase'>
              'luks': <class
              'edumfa.lib.applications.base.MachineApplication'>
              }
    """
    ret = {}
    long_class_names = get_machine_application_class_list()
    for long_class_name in long_class_names:
        module_name = ".".join(long_class_name.split(".")[:-1])
        class_name = long_class_name.split(".")[-1:]

        mod = import_module(module_name)
        # should be able to run as class or as object
        auth_class = mod.MachineApplication
        mtype = auth_class.application_name

        ret[mtype] = auth_class
    return ret


class MachineApplication(object):
    application_name = "base"
    """If bulk_call is false, the administrator may
    only retrieve authentication items for the
    very host he is starting the request.
    """
    allow_bulk_call = False

    @classmethod
    def get_name(cls):
        """
        returns the identifying name of this application class
        """
        return cls.application_name

    @staticmethod
    def get_authentication_item(
        token_type, serial, challenge=None, options=None, filter_param=None
    ):
        """
        returns a dictionary of authentication items
        like public keys, challenges, responses...

        :param filter_param: Additional URL request parameters
        :type filter_param: dict
        """
        return "nothing"

    @staticmethod
    def get_options():
        """
        returns a dictionary with a list of required and optional options
        """
        return {
            "optionA": {"type": TYPE.BOOL, "required": True},
            "optionB": {"type": TYPE.STRING, "value": ["val1", "val2"]},
        }


@log_with(log)
def get_auth_item(
    application, token_type, serial, challenge=None, options=None, filter_param=None
):
    options = options or {}
    # application_module from application
    class_dict = get_machine_application_class_dict()
    # should be able to run as class or as object
    auth_class = class_dict.get(application)
    auth_item = auth_class.get_authentication_item(
        token_type,
        serial,
        challenge=challenge,
        options=options,
        filter_param=filter_param,
    )
    return auth_item


@log_with(log)
def is_application_allow_bulk_call(application_module):
    mod = import_module(application_module)
    auth_class = mod.MachineApplication
    return auth_class.allow_bulk_call


@log_with(log)
def get_application_types():
    """
    This function returns a dictionary of application types with the
    corresponding available attributes.

    {"luks": {"options": {"slot": {"type": "int"},
                          "partition": {"type": "str"}},
     "ssh": {"options": {"user": {"type": "str"}}
    }

    :return: dictionary describing the applications
    """
    ret = {}
    current_module = sys.modules[__name__]
    module_dir = os.path.dirname(current_module.__file__)

    # load all modules and get their application names
    files = [
        os.path.basename(f)[:-3] for f in os.listdir(module_dir) if f.endswith(".py")
    ]
    for f in files:
        if f not in ["base", "__init__"]:
            try:
                mod = import_module(f"edumfa.lib.applications.{f!s}")
                name = mod.MachineApplication.application_name
                options = mod.MachineApplication.get_options()
                ret[name] = {"options": options}
            except Exception as exx:
                log.info(f"Can not get application type: {exx!s}")

    return ret
