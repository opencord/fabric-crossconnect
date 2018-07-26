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
from synchronizers.new_base.modelaccessor import model_accessor, FabricCrossconnectServiceInstance, ServiceInstance, BNGPortMapping

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

    def make_handle(self, s_tag, west_dpid):
        # Generate a backend_handle that uniquely identifies the cross connect. ONOS doesn't provide us a handle, so
        # we make up our own. This helps us to detect other FabricCrossconnectServiceInstance using the same
        # entry, as well as to be able to extract the necessary information to delete the entry later.
        return "%d/%s" % (s_tag, west_dpid)

    def extract_handle(self, backend_handle):
        (s_tag, dpid) = backend_handle.split("/",1)
        s_tag = int(s_tag)
        return (s_tag, dpid)

    def sync_record(self, o):
        self.log.info("Sync'ing Fabric Crossconnect Service Instance", service_instance=o)

        onos = self.get_fabric_onos_info(o)

        si = ServiceInstance.objects.get(id=o.id)

        s_tag = si.get_westbound_service_instance_properties("s_tag")
        dpid = si.get_westbound_service_instance_properties("switch_datapath_id")
        west_port = si.get_westbound_service_instance_properties("switch_port")

        bng_mappings = BNGPortMapping.objects.filter(s_tag = s_tag)
        if not bng_mappings:
            raise Exception("Unable to determine BNG port for s_tag %s" % s_tag)
        east_port = bng_mappings[0].switch_port

        data = { "deviceId": dpid,
                 "vlanId": s_tag,
                 "ports": [ int(west_port), int(east_port) ] } 

        url = onos['url'] + '/onos/segmentrouting/xconnect'

        self.log.info("Sending request to ONOS", url=url, body=data)

        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))

        if r.status_code != 200:
            raise Exception("Failed to create fabric crossconnect in ONOS: %s" % r.text)

        o.backend_handle = self.make_handle(s_tag, dpid)
        o.save(update_fields=["backend_handle"])

        self.log.info("ONOS response", res=r.text)

    def delete_record(self, o):
        self.log.info("Deleting Fabric Crossconnect Service Instance", service_instance=o)

        if o.backend_handle:
            onos = self.get_fabric_onos_info(o)

            # If some other subscriber is using the same entry, then we shouldn't delete it
            other_subscribers = FabricCrossconnectServiceInstance.objects.filter(backend_handle=o.backend_handle)
            other_subscribers = [x for x in other_subscribers if x.id != o.id]
            if other_subscribers:
                self.log.info("Other subscribers exist using same fabric crossconnect entry. Not deleting.")
                return

            # backend_handle has everything we need in it to delete this entry.
            (s_tag, dpid) = self.extract_handle(o.backend_handle)

            data = { "deviceId": dpid,
                     "vlanId": s_tag }

            url = onos['url'] + '/onos/segmentrouting/xconnect'

            r = requests.delete(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))

            if r.status_code != 204:
                raise Exception("Failed to remove fabric crossconnect in ONOS: %s" % r.text)

            self.log.info("ONOS response", res=r.text)
