
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


from xosapi.orm import ORMWrapper, register_convenience_wrapper
from xosapi.convenience.serviceinstance import ORMWrapperServiceInstance

import logging as log

class ORMWrapperFabricCrossconnectService(ORMWrapperServiceInstance):

    def acquire_service_instance(self, subscriber_service_instance):
        """ Given a subscriber_service_instance:
              1) If there is an eligible provider_service_instance that can be used, then link to it
              2) Otherwise, create a new provider_service_instance and link to it.
        """

        ServiceInstance = self.stub.ServiceInstance

        si = ServiceInstance.objects.get(id=subscriber_service_instance.id)
        s_tag = si.get_service_instance_properties("s_tag")
        switch_datapath_id = si.get_service_instance_properties("switch_datapath_id")
        source_port = si.get_service_instance_properties("switch_port")

        if (s_tag is None):
            raise Exception("Subscriber ServiceInstance %s s-tag is None" % subscriber_service_instance.id)

        if (not switch_datapath_id):
            raise Exception("Subscriber ServiceInstance %s switch_datapath_id is unset" % subscriber_service_instance.id)

        if (source_port is None):
            raise Exception("Subscriber ServiceInstance %s switch_port is None" % subscriber_service_instance.id)

        s_tag = int(s_tag)
        source_port = int(source_port)

        # Validate the existing links. If there's already a valid link from the provider_service_instance to a
        # subscriber_service_instance, then there's nothing further we need to do.
        if self.validate_existing_links(subscriber_service_instance, s_tag, switch_datapath_id, source_port):
            return

        candidates = FabricCrossconnectServiceInstance.objects.filter(owner_id=self.id,
                                                                      s_tag=s_tag,
                                                                      switch_datapath_id=switch_datapath_id,
                                                                      source_port=source_port)

        if candidates:
            provider_service_instance = candidates[0]
        else:
            provider_service_instance = FabricCrossconnectServiceInstance.objects.filter(owner=self,
                                                                        s_tag=s_tag,
                                                                        switch_datapath_id=switch_datapath_id,
                                                                        source_port=source_port)
            provider_service_instance.save()

        # NOTE: Lack-of-atomicity vulnerability -- provider_service_instance could be deleted before we created the
        # link.

        link = ServiceInstanceLink(provider_service_instance=provider_service_instance,
                                   subscriber_service_instance=subscriber_service_instance)
        link.save()

    def validate_links(self, subscriber_service_instance):
        """ Validate existing links between the provider and subscriber service instances. If a valid link exists,
            then return it. Return None otherwise.

            As a side-effect, delete any invalid links.
        """

        # Short-cut -- if there are no subscriber links then we can skip getting all the properties.
        if not subscriber_service_instance.subscriber_links.exists():
            return None

        ServiceInstance = self.stub.ServiceInstance

        si = ServiceInstance.objects.get(id=subscriber_service_instance.id)
        s_tag = si.get_service_instance_properties("s_tag")
        switch_datapath_id = si.get_service_instance_properties("switch_datapath_id")
        source_port = si.get_service_instance_properties("switch_port")

        matched = None
        for link in subscriber_service_instance.subscriber_links:
            if link.provider_service_instance.owner.id == self.id:
                fcsi = link.provider_service_instance.leaf_model
                if (fcsi.s_tag == s_tag) and (fcsi.switch_datapath_id == switch_datapath_id) and \
                    (fcsi.source_port == source_port):
                    matched=fcsi
                else:
                    link.delete()
        return matched

register_convenience_wrapper("FabricCrossconnectService", ORMWrapperFabricCrossconnectService)
