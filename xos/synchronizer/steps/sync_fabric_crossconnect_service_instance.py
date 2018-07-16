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

from synchronizers.new_base.syncstep import SyncStep, DeferredException
from synchronizers.new_base.modelaccessor import model_accessor, FabricCrossconnectServiceInstance, ServiceInstance

from xosconfig import Config
from multistructlog import create_logger
import urllib
import requests
from requests.auth import HTTPBasicAuth


class SyncFabricCrossconnectServiceInstance(SyncStep):
    provides = [FabricCrossconnectServiceInstance]
    log = create_logger(Config().get('logging'))

    observes = FabricCrossconnectServiceInstance

    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_fabric_onos_info(si):

        # get the fabric-crossconnect service
        fabric_crossconnect = si.owner

        # get the onos_fabric service
        fabric_onos = [s.leaf_model for s in fabric_crossconnect.provider_services if "onos" in s.name.lower()]

        if len(fabric_onos) == 0:
            raise Exception('Cannot find ONOS service in provider_services of Fabric-Crossconnect')

        fabric_onos = fabric_onos[0]

        return {
            'url': SyncFabricCrossconnectServiceInstance.format_url("%s:%s" % (fabric_onos.rest_hostname, fabric_onos.rest_port)),
            'user': fabric_onos.rest_username,
            'pass': fabric_onos.rest_password
        }

    def get_bng_port(self, o):
        # TODO(smbaker): Get BNG port from somewhere
        return 2

    def sync_record(self, o):
        self.log.info("Sync'ing Fabric Crossconnect Service Instance", service_instance=o)

        onos = self.get_fabric_onos_info(o)

        si = ServiceInstance.objects.get(id=o.id)

        s_tag = si.get_westbound_service_instance_properties("s_tag")
        west_dpid = si.get_westbound_service_instance_properties("switch_datapath_id")
        west_port = si.get_westbound_service_instance_properties("switch_port")
        east_port = self.get_bng_port(o)

        data = { "deviceId": west_dpid,
                 "vlanId": s_tag,
                 "ports": [ west_port, east_port ] }

        url = onos['url'] + '/onos/segmentsrouting/xconnect'

        self.log.info("Sending request to ONOS", url=url, body=data)

        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))

        if r.status_code != 200:
            raise Exception("Failed to create fabric crossconnect in ONOS: %s" % r.text)

        self.log.info("ONOS response", res=r.text)

    def delete_record(self, o):
        self.log.info("Deleting Fabric Crossconnect Service Instance", service_instance=o)

        # TODO(smbaker): make sure it's not in use by some other subscriber

        if o.enacted:
            onos = self.get_fabric_onos_info(o)

            si = ServiceInstance.objects.get(id=o.id)

            # TODO(smbaker): unable to get westbound service_instance while deleting?

            s_tag = si.get_westbound_service_instance_properties("s_tag")
            west_dpid = si.get_westbound_service_instance_properties("switch_datapath_id")

            data = { "deviceId": west_dpid,
                     "vlanID": s_tag }

            url = onos['url'] + '/onos/segmentrouting/xconnect'

            r = requests.delete(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))

            if r.status_code != 204:
                raise Exception("Failed to remove fabric crossconnect in ONOS: %s" % r.text)

            self.log.info("ONOS response", res=r.text)
