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


from xossynchronizer.modelaccessor import FabricCrossconnectServiceInstance, ServiceInstance, BNGPortMapping, model_accessor
from xossynchronizer.model_policies.policy import Policy

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))


class BNGPortMappingPolicy(Policy):
    model_name = "BNGPortMapping"

    def resync_xconnect(self, bngportmapping):
        fabric_crossconnect_service_instances = self.model_accessor.FabricCrossconnectServiceInstance.objects.filter(bngportmapping_id = bngportmapping.id)
        for fcsi in fabric_crossconnect_service_instances:
            fcsi.backend_code = 0
            fcsi.backend_status = "resynchronize due to BNGPortMapping instance change."
            fcsi.save(update_fields=["updated", "backend_code", "backend_status"], always_update_timestamp=True)

    def handle_create(self, bngportmapping):
        return self.handle_update(bngportmapping)

    def handle_update(self, bngportmapping):
        log.info("Handle_update BNGPortMapping instance : %s" % bngportmapping.id)
        self.resync_xconnect(bngportmapping)

    def handle_delete(self, bngportmapping):
        log.info("Handle_delete BNGPortMapping instance : %s" % bngportmapping.id)
        if(len(self.model_accessor.BNGPortMapping.objects.all()) == 1):
            #If only BNGPortMapping object present is removed, then associated cross-connects with it are also removed.
            fabric_crossconnect_service_instances = self.model_accessor.FabricCrossconnectServiceInstance.objects.filter(bngportmapping_id = bngportmapping.id)
            for fcsi in fabric_crossconnect_service_instances:
                fcsi.delete(purge=True)
        else:
            self.resync_xconnect(bngportmapping)
