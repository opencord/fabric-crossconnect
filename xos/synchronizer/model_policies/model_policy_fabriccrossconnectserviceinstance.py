
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


from synchronizers.new_base.modelaccessor import FabricCrossconnectServiceInstance, ServiceInstance, model_accessor
from synchronizers.new_base.policy import Policy
from synchronizers.new_base.exceptions import *

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class FabricCrossconnectServiceInstancePolicy(Policy):
    model_name = "FabricCrossconnectServiceInstance"

    def handle_create(self, service_instance):
        return self.handle_update(service_instance)

    def handle_update(self, service_instance):
        log.info("Handle_update Fabric Crossconnect Service Instance", service_instance=service_instance)

        if (service_instance.link_deleted_count > 0) and (not service_instance.provided_links.exists()):
            # If this instance has no links pointing to it, delete
            self.handle_delete(service_instance)
            if FabricCrossconnectServiceInstance.objects.filter(id=service_instance.id).exists():
                service_instance.delete()
            return

    def handle_delete(self, service_instance):
        log.info("Handle_delete Fabric-Crossconnect Service Instance", service_instance=service_instance)


