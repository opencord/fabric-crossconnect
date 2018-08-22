
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
from xosapi.convenience.service import ORMWrapperService

class ORMWrapperFabricCrossconnectService(ORMWrapperService):

    """ Calling convention. Assume the subscribing service does approximately (needs some checks to see
        if the methods exist before calling them) the following in its model_policy:

        if not eastbound_service.validate_links(self):
             eastbound_service.acquire_service_instance(self)
    """

    def acquire_service_instance(self, subscriber_service_instance):
        """ Given a subscriber_service_instance:
              1) If there is an eligible provider_service_instance that can be used, then link to it
              2) Otherwise, create a new provider_service_instance and link to it.
        """
        (s_tag, switch_datapath_id, source_port) = self._get_west_fields(subscriber_service_instance)

        FabricCrossconnectServiceInstance = self.stub.FabricCrossconnectServiceInstance
        ServiceInstanceLink = self.stub.ServiceInstanceLink

        candidates = FabricCrossconnectServiceInstance.objects.filter(owner_id=self.id,
                                                                      s_tag=s_tag,
                                                                      switch_datapath_id=switch_datapath_id,
                                                                      source_port=source_port)

        if candidates:
            provider_service_instance = candidates[0]
        else:
            provider_service_instance = FabricCrossconnectServiceInstance(owner=self,
                                                                        s_tag=s_tag,
                                                                        switch_datapath_id=switch_datapath_id,
                                                                        source_port=source_port)
            provider_service_instance.save()

        # NOTE: Lack-of-atomicity vulnerability -- provider_service_instance could be deleted before we created the
        # link.

        link = ServiceInstanceLink(provider_service_instance=provider_service_instance,
                                   subscriber_service_instance=subscriber_service_instance)
        link.save()

        return provider_service_instance

    def validate_links(self, subscriber_service_instance):
        """ Validate existing links between the provider and subscriber service instances. If a valid link exists,
            then return it. Return [] otherwise.

            As a side-effect, delete any invalid links.
        """

        # Short-cut -- if there are no subscriber links then we can skip getting all the properties.
        if not subscriber_service_instance.subscribed_links.exists():
            return None

        (s_tag, switch_datapath_id, source_port) = self._get_west_fields(subscriber_service_instance)

        matched = []
        for link in subscriber_service_instance.subscribed_links.all():
            if link.provider_service_instance.owner.id == self.id:
                fcsi = link.provider_service_instance.leaf_model
                if (fcsi.s_tag == s_tag) and (fcsi.switch_datapath_id == switch_datapath_id) and \
                    (fcsi.source_port == source_port):
                    matched.append(fcsi)
                else:
                    link.delete()
        return matched

    def _get_west_fields(self, subscriber_si):
        """ _get_west_fields()

            Helper function to inspect westbound service instance for fields that will be used inside of
            FabricCrossconnectServiceInstance.
        """

        s_tag = subscriber_si.get_westbound_service_instance_properties("s_tag", include_self=True)
        switch_datapath_id = subscriber_si.get_westbound_service_instance_properties("switch_datapath_id", include_self=True)
        source_port = subscriber_si.get_westbound_service_instance_properties("switch_port", include_self=True)

        if (s_tag is None):
            raise Exception("Subscriber ServiceInstance %s s-tag is None" % subscriber_si.id)

        if (not switch_datapath_id):
            raise Exception("Subscriber ServiceInstance %s switch_datapath_id is unset" % subscriber_si.id)

        if (source_port is None):
            raise Exception("Subscriber ServiceInstance %s switch_port is None" % subscriber_si.id)

        s_tag = int(s_tag)
        source_port = int(source_port)

        return (s_tag, switch_datapath_id, source_port)

register_convenience_wrapper("FabricCrossconnectService", ORMWrapperFabricCrossconnectService)
