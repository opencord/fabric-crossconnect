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
import os, sys
from mock import patch, Mock, MagicMock

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
service_dir=os.path.join(test_path, "../../../..")
xos_dir=os.path.join(test_path, "../../..")
if not os.path.exists(os.path.join(test_path, "new_base")):
    xos_dir=os.path.join(test_path, "../../../../../../orchestration/xos/xos")
    services_dir=os.path.join(xos_dir, "../../xos_services")

# mocking XOS exception, as they're based in Django
class Exceptions:
    XOSValidationError = Exception
    XOSProgrammingError = Exception
    XOSPermissionDenied = Exception

class XOS:
    exceptions = Exceptions

class TestFabricCrossconnectModels(unittest.TestCase):
    def setUp(self):

        self.sys_path_save = sys.path
        sys.path.append(xos_dir)

        self.xos = XOS

        self.models_decl = Mock()
        self.models_decl.BNGPortMapping_decl = MagicMock
        self.models_decl.BNGPortMapping_decl.save = Mock()
        self.models_decl.BNGPortMapping_decl.objects = Mock()
        self.models_decl.BNGPortMapping_decl.objects.filter.return_value = []


        modules = {
            'xos.exceptions': self.xos.exceptions,
            'models_decl': self.models_decl
        }

        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        self.volt = Mock()

        from models import BNGPortMapping

        self.BNGPortMapping = BNGPortMapping()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_validate_range_single(self):
        bpm = self.BNGPortMapping()
        bpm.validate_range("123")

    def test_validate_range_commas(self):
        bpm = self.BNGPortMapping()
        bpm.validate_range("123, 456")

    def test_validate_range_ANY(self):
        bpm = self.BNGPortMapping()
        bpm.validate_range("ANY")
        bpm.validate_range("any")

    def test_validate_range_dash(self):
        bpm = self.BNGPortMapping()
        bpm.validate_range("123-456")

    def test_validate_dash_commas(self):
        bpm = self.BNGPortMapping()
        bpm.validate_range("123-456, 789 - 1000")

    def test_validate_range_empty(self):
        bpm = self.BNGPortMapping()
        with self.assertRaises(Exception) as e:
            bpm.validate_range("")

        self.assertEqual(e.exception.message, 'Malformed range ')

    def test_validate_range_none(self):
        bpm = self.BNGPortMapping()
        with self.assertRaises(Exception) as e:
            bpm.validate_range("")

        self.assertEqual(e.exception.message, 'Malformed range ')

    def test_validate_range_all(self):
        bpm = self.BNGPortMapping()
        with self.assertRaises(Exception) as e:
            bpm.validate_range("badstring")

        self.assertEqual(e.exception.message, 'Malformed range badstring')

    def test_validate_half_range(self):
        bpm = self.BNGPortMapping()
        with self.assertRaises(Exception) as e:
            bpm.validate_range("123-")

        self.assertEqual(e.exception.message, 'Malformed range 123-')

    def test_validate_half_comma(self):
        bpm = self.BNGPortMapping()
        with self.assertRaises(Exception) as e:
            bpm.validate_range("123,")

        self.assertEqual(e.exception.message, 'Malformed range 123,')

if __name__ == '__main__':
    unittest.main()
