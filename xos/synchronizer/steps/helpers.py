# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class Helpers():

    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_fabric_onos_info(model_accessor, service):
        fabric_onos = [s.leaf_model for s in service.provider_services if "onos" in s.name.lower()]
        if len(fabric_onos) == 0:
            raise Exception('Cannot find ONOS service in provider_services of Fabric-Crossconnect')

        fabric_onos = fabric_onos[0]
        return {
            'url': Helpers.format_url(
                "%s:%s" %
                (fabric_onos.rest_hostname,
                fabric_onos.rest_port)),
                'user': fabric_onos.rest_username,
                'pass': fabric_onos.rest_password}

    @staticmethod
    def range_matches(value, pattern):
        value = int(value)
        for this_range in pattern.split(","):
            this_range = this_range.strip()
            if "-" in this_range:
                (first, last) = this_range.split("-")
                first = int(first.strip())
                last = int(last.strip())
                if (value >= first) and (value <= last):
                    return True
            elif this_range.lower() == "any":
                return False
