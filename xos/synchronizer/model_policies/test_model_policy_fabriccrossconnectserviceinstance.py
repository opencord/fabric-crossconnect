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

import unittest

import functools
from mock import patch, call, Mock, PropertyMock, MagicMock
import requests_mock
import multistructlog
from multistructlog import create_logger

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def mock_get_westbound_service_instance_properties(props, prop):
    return props[prop]

def match_json(desired, req):
    if desired!=req.json():
        raise Exception("Got request %s, but body is not matching" % req.url)
        return False
    return True

class TestPolicyFabricCrossconnectServiceInstance(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_fabric_crossconnect_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("fabric-crossconnect", "fabric-crossconnect.xproto"),])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from model_policy_fabriccrossconnectserviceinstance import FabricCrossconnectServiceInstancePolicy, \
            model_accessor

        self.model_accessor = model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.policy_step = FabricCrossconnectServiceInstancePolicy
        self.policy_step.log = Mock()

        # mock onos-fabric
        self.onos_fabric = Service(name = "onos-fabric",
                              rest_hostname = "onos-fabric",
                              rest_port = "8181",
                              rest_username = "onos",
                              rest_password = "rocks")

        self.service = FabricCrossconnectService(name = "fcservice",
                                                 provider_services = [self.onos_fabric])

    def mock_westbound(self, fsi, s_tag, switch_datapath_id, switch_port):
        # Mock out a ServiceInstance so the syncstep can call get_westbound_service_instance_properties on it
        si = ServiceInstance(id=fsi.id)
        si.get_westbound_service_instance_properties = functools.partial(
            mock_get_westbound_service_instance_properties,
            {"s_tag": s_tag,
             "switch_datapath_id": switch_datapath_id,
             "switch_port": switch_port})

        fsi.provided_links=Mock(exists=Mock(return_value=True))

        return si

    def test_handle_update(self):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, s_tag=None, source_port=None,
                                                    switch_datapath_id=None)

            serviceinstance_objects.return_value = [fsi]

            si = self.mock_westbound(fsi, s_tag=111, switch_datapath_id = "of:0000000000000201", switch_port = 3)
            serviceinstance_objects.return_value = [si]

            self.policy_step(model_accessor=self.model_accessor).handle_update(fsi)

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

if __name__ == '__main__':
    unittest.main()
