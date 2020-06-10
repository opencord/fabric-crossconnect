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

from xossynchronizer.pull_steps.pullstep import PullStep

from xosconfig import Config
from multistructlog import create_logger

import requests
from requests import ConnectionError
from requests.auth import HTTPBasicAuth
from requests.models import InvalidURL

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = create_logger(Config().get('logging'))

class ONOSXconnectPullStep(PullStep):
    def __init__(self, model_accessor):
        super(ONOSXconnectPullStep, self).__init__(model_accessor=model_accessor)

    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    def get_fabric_onos_info(self, service):
        # get the onos_fabric service
        fabric_crossconnect = self.model_accessor.Service.objects.get(id=service.id)
        fabric_onos = [s.leaf_model for s in fabric_crossconnect.provider_services if "onos" in s.name.lower()]
        if len(fabric_onos) == 0:
            raise Exception('Cannot find ONOS service in provider_services of Fabric-Crossconnect')

        fabric_onos = fabric_onos[0]
        return {
            'url': ONOSXconnectPullStep.format_url(
                "%s:%s" %
                (fabric_onos.rest_hostname,
                fabric_onos.rest_port)),
                'user': fabric_onos.rest_username,
                'pass': fabric_onos.rest_password}

    def pull_records(self):
        log.debug("[ONOS] Xconnect Pull Steps")

        for fcsi in self.model_accessor.FabricCrossconnectServiceInstance.objects.all():
            onos = self.get_fabric_onos_info(fcsi.owner)
            log.info("ONOS belonging to fabric crossconnect instance: %s" % onos)
	    resync = 0
            url = onos['url'] + '/onos/segmentrouting/xconnect'
            log.info("Sending request to ONOS", url=url)
            r = requests.get(url, auth=HTTPBasicAuth(onos['user'], onos['pass']))
            if r.status_code != 200:
                log.error(r.text)
                raise Exception("Failed to get onos devices")
            else:
                try:
                    log.info("Get devices response", json=r.json())
                except Exception:
                    log.info("Get devices exception response", text=r.text)

            xconnects = r.json()["xconnects"]
            log.info("data: %s" % xconnects)
            bng_mapping = self.model_accessor.BNGPortMapping.objects.filter(id=fcsi.bngportmapping_id)

            if not bng_mapping:
                log.debug("BNGPortMapping instance for current fabric-crossconnect-instance is not found")
	        resync = resync + 1
            else:
                for xconnect in xconnects:
                    val = xconnect['endpoints']
                    if(str(bng_mapping[0].switch_port) not in val):
                        resync = resync + 1

	    if(resync != 0):
	        fcsi.backend_code = 0
		fcsi.backend_status = "resynchronize due to BNGPortMappingObject Change"
		fcsi.save(update_fields=["updated", "backend_code", "backend_status"], always_update_timestamp=True)
