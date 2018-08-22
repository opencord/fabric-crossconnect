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

# Hack to load synchronizer framework
test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
xos_dir=os.path.join(test_path, "../../..")
if not os.path.exists(os.path.join(test_path, "new_base")):
    xos_dir=os.path.join(test_path, "../../../../../../orchestration/xos/xos")
    services_dir = os.path.join(xos_dir, "../../xos_services")
sys.path.append(xos_dir)
sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))
# END Hack to load synchronizer framework

# generate model from xproto
def get_models_fn(service_name, xproto_name):
    name = os.path.join(service_name, "xos", xproto_name)
    if os.path.exists(os.path.join(services_dir, name)):
        return name
    else:
        name = os.path.join(service_name, "xos", "synchronizer", "models", xproto_name)
        if os.path.exists(os.path.join(services_dir, name)):
            return name
    raise Exception("Unable to find service=%s xproto=%s" % (service_name, xproto_name))
# END generate model from xproto

def mock_get_westbound_service_instance_properties(props, prop):
    return props[prop]

def match_json(desired, req):
    if desired!=req.json():
        raise Exception("Got request %s, but body is not matching" % req.url)
        return False
    return True

class TestSyncFabricCrossconnectServiceInstance(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_fabric_crossconnect_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("fabric-crossconnect", "fabric-crossconnect.xproto")])
        import synchronizers.new_base.modelaccessor

        from sync_fabric_crossconnect_service_instance import SyncFabricCrossconnectServiceInstance, model_accessor, DeferredException

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncFabricCrossconnectServiceInstance
        self.sync_step.log = Mock()

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
        return si

    def test_format_url(self):
        url = self.sync_step().format_url("foo.com/bar")
        self.assertEqual(url, "http://foo.com/bar")

        url = self.sync_step().format_url("http://foo.com/bar")
        self.assertEqual(url, "http://foo.com/bar")

    def test_make_handle_extract_handle(self):
        h = self.sync_step().make_handle(222, "of:0000000000000201")
        (s_tag, switch_datapath_id) = self.sync_step().extract_handle(h)

        self.assertEqual(s_tag, 222)
        self.assertEqual(switch_datapath_id, "of:0000000000000201")

    def test_get_fabric_onos_init(self):
        fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service)

        d = self.sync_step().get_fabric_onos_info(fsi)

        self.assertEqual(d["url"], "http://onos-fabric:8181")
        self.assertEqual(d["user"], "onos")
        self.assertEqual(d["pass"], "rocks")

    def test_range_matches_single(self):
        self.assertTrue(self.sync_step().range_matches(123, "123"))

    def test_range_matches_single_incorrect(self):
        self.assertFalse(self.sync_step().range_matches(123, "456"))

    def test_range_matches_range(self):
        self.assertTrue(self.sync_step().range_matches(123, "122-124"))

    def test_range_matches_range_incorrect(self):
        self.assertFalse(self.sync_step().range_matches(123, "110-113"))

    def test_range_matches_any(self):
        self.assertTrue(self.sync_step().range_matches(123, "ANY"))
        self.assertTrue(self.sync_step().range_matches(123, "any"))

    def test_find_bng_single(self):
        with patch.object(BNGPortMapping.objects, "get_items") as bng_objects, \
                patch.object(self.sync_step, "range_matches") as range_matches:
            bngmapping = BNGPortMapping(s_tag="111", switch_port=4)
            bng_objects.return_value = [bngmapping]

            # this should not be called
            range_matches.return_value = False

            found_bng = self.sync_step().find_bng(111)
            self.assertTrue(found_bng)
            self.assertEqual(found_bng.switch_port, 4)

            range_matches.assert_not_called()

    def test_find_bng_any(self):
        with patch.object(BNGPortMapping.objects, "get_items") as bng_objects:
            bngmapping = BNGPortMapping(s_tag="ANY", switch_port=4)
            bng_objects.return_value = [bngmapping]

            found_bng = self.sync_step().find_bng(111)
            self.assertTrue(found_bng)
            self.assertEqual(found_bng.switch_port, 4)

    def test_find_bng_range(self):
        with patch.object(BNGPortMapping.objects, "get_items") as bng_objects:
            bngmapping = BNGPortMapping(s_tag="100-200", switch_port=4)
            bng_objects.return_value = [bngmapping]

            found_bng = self.sync_step().find_bng(111)
            self.assertTrue(found_bng)
            self.assertEqual(found_bng.switch_port, 4)

    @requests_mock.Mocker()
    def test_sync(self, m):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(BNGPortMapping.objects, "get_items") as bng_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, s_tag=111, source_port=3,
                                                    switch_datapath_id="of:0000000000000201", updated=1, policed=2)

            serviceinstance_objects.return_value = [fsi]

            bngmapping = BNGPortMapping(s_tag="111", switch_port=4)
            bng_objects.return_value = [bngmapping]

            desired_data = {"deviceId": "of:0000000000000201",
                    "vlanId": 111,
                    "ports": [3, 4]}

            m.post("http://onos-fabric:8181/onos/segmentrouting/xconnect",
                   status_code=200,
                   additional_matcher=functools.partial(match_json, desired_data))

            self.sync_step().sync_record(fsi)
            self.assertTrue(m.called)

            self.assertEqual(fsi.backend_handle, "111/of:0000000000000201")
            fcsi_save.assert_called()

    def test_sync_no_bng_mapping(self):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, s_tag=111, source_port=3,
                                                    switch_datapath_id="of:0000000000000201", updated=1, policed=2)

            serviceinstance_objects.return_value = [fsi]

            with self.assertRaises(Exception) as e:
                self.sync_step().sync_record(fsi)

            self.assertEqual(e.exception.message, "Unable to determine BNG port for s_tag 111")

    def test_sync_not_policed(self):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, source_port=3,
                                                    switch_datapath_id="of:0000000000000201", updated=1, policed=0)

            serviceinstance_objects.return_value = [fsi]

            with self.assertRaises(Exception) as e:
                self.sync_step().sync_record(fsi)

            self.assertEqual(e.exception.message, "Waiting for model_policy to run on fcsi 7777")

    def test_sync_no_s_tag(self):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, source_port=3,
                                                    switch_datapath_id="of:0000000000000201", updated=1, policed=2)

            serviceinstance_objects.return_value = [fsi]

            with self.assertRaises(Exception) as e:
                self.sync_step().sync_record(fsi)

            self.assertEqual(e.exception.message, "Cannot sync FabricCrossconnectServiceInstance if s_tag is None on fcsi 7777")

    def test_sync_no_switch_datapath_id(self):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, source_port=3, s_tag=111,
                                                    updated=1, policed=2)

            serviceinstance_objects.return_value = [fsi]

            with self.assertRaises(Exception) as e:
                self.sync_step().sync_record(fsi)

            self.assertEqual(e.exception.message, "Cannot sync FabricCrossconnectServiceInstance if switch_datapath_id is unset on fcsi 7777")

    def test_sync_no_source_port(self):
        with patch.object(ServiceInstance.objects, "get_items") as serviceinstance_objects, \
            patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:

            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service, s_tag=111,
                                                    switch_datapath_id="of:0000000000000201", updated=1, policed=2)

            serviceinstance_objects.return_value = [fsi]

            with self.assertRaises(Exception) as e:
                self.sync_step().sync_record(fsi)

            self.assertEqual(e.exception.message, "Cannot sync FabricCrossconnectServiceInstance if source_port is None on fcsi 7777")

    @requests_mock.Mocker()
    def test_delete(self, m):
        with patch.object(FabricCrossconnectServiceInstance.objects, "get_items") as fcsi_objects, \
                patch.object(FabricCrossconnectServiceInstance, "save") as fcsi_save:
            fsi = FabricCrossconnectServiceInstance(id=7777, owner=self.service,
                                                    backend_handle="111/of:0000000000000201",
                                                    enacted=True)

            fcsi_objects.return_value=[fsi]

            desired_data = {"deviceId": "of:0000000000000201",
                            "vlanId": 111}

            m.delete("http://onos-fabric:8181/onos/segmentrouting/xconnect",
                   status_code=204,
                   additional_matcher=functools.partial(match_json, desired_data))

            self.sync_step().delete_record(fsi)
            self.assertTrue(m.called)

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

if __name__ == '__main__':
    unittest.main()
