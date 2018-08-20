
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

        # If there is a westbound link, then make sure the SerivceInstance is consistent with the
        # westbound fields.

        if service_instance.provided_links.exists():
            updated_fields = []

            si = ServiceInstance.objects.get(id=service_instance.id)
            s_tag = si.get_westbound_service_instance_properties("s_tag")
            switch_datapath_id = si.get_westbound_service_instance_properties("switch_datapath_id")
            source_port = si.get_westbound_service_instance_properties("switch_port")

            if (s_tag is None):
                raise Exception("Westbound ServiceInstance s-tag is None on fcsi %s" % service_instance.id)

            if (not switch_datapath_id):
                raise Exception("Westbound ServiceInstance switch_datapath_id is unset on fcsi %s" % service_instance.id)

            if (source_port is None):
                raise Exception("Westbound ServiceInstance switch_port is None on fcsi %s" % service_instance.id)

            s_tag = int(s_tag)
            source_port = int(source_port)

            if (s_tag != service_instance.s_tag):
                if service_instance.s_tag is not None:
                    raise Exception("Westbound ServiceInstance changing s-tag is not currently permitted")
                service_instance.s_tag = s_tag
                updated_fields.append("s_tag")
            if (switch_datapath_id != service_instance.switch_datapath_id):
                if service_instance.switch_datapath_id:
                    raise Exception("Westbound ServiceInstance changing switch_datapath_id is not currently permitted")
                service_instance.switch_datapath_id = switch_datapath_id
                updated_fields.append("switch_datapath_id")
            if (source_port != service_instance.source_port):
                if service_instance.source_port is not None:
                    raise Exception("Westbound ServiceInstance changing source_port is not currently permitted")
                service_instance.source_port = source_port
                updated_fields.append("source_port")

            if updated_fields:
                service_instance.save(update_fields = updated_fields)

    def handle_delete(self, service_instance):
        log.info("Handle_delete Fabric-Crossconnect Service Instance", service_instance=service_instance)


