# -*- coding: utf-8 -*-
#
# License:  AGPLv3
# This file is part of eduMFA. eduMFA is a fork of privacyIDEA which was forked from LinOTP.
# Copyright (c) 2024 eduMFA Project-Team
# Previous authors by privacyIDEA project:
#
# 2017 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# (c) 2017. Cornelius Kölbel
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
__doc__ = """This is the event handler module for eduMFA federations.
Requests can be forwarded to other eduMFA servers.
"""
from edumfa.lib.eventhandler.base import BaseEventHandler
from edumfa.lib.edumfaserver import get_edumfaservers, get_edumfaserver
from edumfa.lib import _
from edumfa.lib.utils import is_true
import json
import logging
import requests
from flask import current_app


log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """

    FORWARD = "forward"


class FederationEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandling definitions
    """

    identifier = "Federation"
    description = "This event handler can forward the request to other eduMFA servers"

    # TODO: Do we need to change the federation handler this way, that it does only pre-handling?

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        pi_servers = [x.config.identifier for x in get_edumfaservers()]
        actions = {
            ACTION_TYPE.FORWARD: {
                "eduMFA": {
                    "type": "str",
                    "required": True,
                    "value": pi_servers,
                    "description": _("The remote/child eduMFA Server."),
                },
                "realm": {
                    "type": "str",
                    "description": _(
                        "Change the realm name to a realm on the child eduMFA system."
                    ),
                },
                "resolver": {
                    "type": "str",
                    "description": _(
                        "Change the resolver name to a resolver on the child eduMFA system."
                    ),
                },
                "forward_client_ip": {
                    "type": "bool",
                    "description": _(
                        "Forward the client IP to the child eduMFA server. Otherwise this server will be the client."
                    ),
                },
                "forward_authorization_token": {
                    "type": "bool",
                    "description": _(
                        "Forward the authorization header. This allows to also forward request like token- and system-requests."
                    ),
                },
            }
        }
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return:
        """
        g = options.get("g")
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        if action == ACTION_TYPE.FORWARD:
            server_def = handler_options.get("eduMFA")
            pi_server = get_edumfaserver(server_def)

            # the new url is the configured server url and the original path
            url = pi_server.config.url + request.path
            # We use the original method
            method = request.method
            tls = pi_server.config.tls
            # We also transfer the original payload
            data = request.all_data
            if is_true(handler_options.get("forward_client_ip", False)):
                data["client"] = g.client_ip
            if handler_options.get("realm"):
                data["realm"] = handler_options.get("realm")
            if handler_options.get("resolver"):
                data["resolver"] = handler_options.get("resolver")

            log.info(f"Sending {method} request to {url!r}")
            requestor = None
            params = None
            headers = {}

            # We need to pass an authorization header if we forward administrative requests
            if is_true(handler_options.get("forward_authorization_token", False)):
                auth_token = request.headers.get("Authorization")
                headers["Authorization"] = auth_token

            if method.upper() == "GET":
                params = data
                data = None
                requestor = requests.get
            elif method.upper() == "POST":
                requestor = requests.post
            elif method.upper() == "DELETE":
                requestor = requests.delete

            if requestor:
                r = requestor(
                    url, params=params, data=data, headers=headers, verify=tls
                )
                # convert requests Response to werkzeug Response
                response_dict = json.loads(r.text)
                if "detail" in response_dict:
                    detail = response_dict.setdefault("detail", {})
                    # In case of exceptions we may not have a detail
                    detail["origin"] = url
                # We will modify the response!
                # We can not use flask.jsonify(response_dict) here, since we
                # would work outside of application context!
                options["response"] = current_app.response_class(
                    json.dumps(response_dict), mimetype="application/json"
                )
                options["response"].status_code = r.status_code
            else:
                log.warning(f"Unsupported method: {method!r}")

        return True
