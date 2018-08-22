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

    def make_handle(self, s_tag, switch_datapath_id):
        # Generate a backend_handle that uniquely identifies the cross connect. ONOS doesn't provide us a handle, so
        # we make up our own. This helps us to detect other FabricCrossconnectServiceInstance using the same
        # entry, as well as to be able to extract the necessary information to delete the entry later.
        return "%d/%s" % (s_tag, switch_datapath_id)

    def extract_handle(self, backend_handle):
        (s_tag, switch_datapath_id) = backend_handle.split("/",1)
        s_tag = int(s_tag)
        return (s_tag, switch_datapath_id)

    def range_matches(self, value, pattern):
        value=int(value)
        for this_range in pattern.split(","):
            this_range = this_range.strip()
            if "-" in this_range:
                (first, last) = this_range.split("-")
                first = int(first.strip())
                last = int(last.strip())
                if (value>=first) and (value<=last):
                    return True
            elif this_range.lower()=="any":
                return True
            else:
                if (value==int(this_range)):
                    return True
        return False

    def find_bng(self, s_tag):
        # See if there's a mapping for our s-tag directly
        bng_mappings = BNGPortMapping.objects.filter(s_tag=str(s_tag))
        if bng_mappings:
            return bng_mappings[0]

        # TODO(smbaker): Examine miss performance, and if necessary set a flag in the save method to allow filtering
        # of mappings based on whether they are ranges or any.

        # See if there are any ranges or "any" that match
        for bng_mapping in BNGPortMapping.objects.all():
            if self.range_matches(s_tag, bng_mapping.s_tag):
                 return bng_mapping

        return None

    def sync_record(self, o):
        self.log.info("Sync'ing Fabric Crossconnect Service Instance", service_instance=o)

        if (o.policed is None) or (o.policed < o.updated):
            raise DeferredException("Waiting for model_policy to run on fcsi %s" % o.id)

        onos = self.get_fabric_onos_info(o)

        si = ServiceInstance.objects.get(id=o.id)

        if (o.s_tag is None):
            raise Exception("Cannot sync FabricCrossconnectServiceInstance if s_tag is None on fcsi %s" % o.id)

        if (o.source_port is None):
            raise Exception("Cannot sync FabricCrossconnectServiceInstance if source_port is None on fcsi %s" % o.id)

        if (not o.switch_datapath_id):
            raise Exception("Cannot sync FabricCrossconnectServiceInstance if switch_datapath_id is unset on fcsi %s" % o.id)

        bng_mapping = self.find_bng(s_tag = o.s_tag)
        if not bng_mapping:
            raise Exception("Unable to determine BNG port for s_tag %s" % o.s_tag)
        east_port = bng_mapping.switch_port

        data = { "deviceId": o.switch_datapath_id,
                 "vlanId": o.s_tag,
                 "ports": [ int(o.source_port), int(east_port) ] }

        url = onos['url'] + '/onos/segmentrouting/xconnect'

        self.log.info("Sending request to ONOS", url=url, body=data)

        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))

        if r.status_code != 200:
            raise Exception("Failed to create fabric crossconnect in ONOS: %s" % r.text)

        # TODO(smbaker): If the o.backend_handle changed, then someone must have changed the
        #   FabricCrossconnectServiceInstance. If so, then we potentially need to clean up the old
        #   entry in ONOS. Furthermore, we might want to also save the two port numbers that we used,
        #   to detect someone changing those.

        o.backend_handle = self.make_handle(o.s_tag, o.switch_datapath_id)
        o.save(update_fields=["backend_handle"])

        self.log.info("ONOS response", res=r.text)

    def delete_record(self, o):
        self.log.info("Deleting Fabric Crossconnect Service Instance", service_instance=o)

        if o.backend_handle:
            onos = self.get_fabric_onos_info(o)

            # backend_handle has everything we need in it to delete this entry.
            (s_tag, switch_datapath_id) = self.extract_handle(o.backend_handle)

            data = { "deviceId": switch_datapath_id,
                     "vlanId": s_tag }

            url = onos['url'] + '/onos/segmentrouting/xconnect'

            r = requests.delete(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))

            if r.status_code != 204:
                raise Exception("Failed to remove fabric crossconnect in ONOS: %s" % r.text)

            self.log.info("ONOS response", res=r.text)
