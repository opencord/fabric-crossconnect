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

from xos.exceptions import XOSValidationError

from models_decl import FabricCrossconnectService_decl, FabricCrossconnectServiceInstance_decl, BNGPortMapping_decl

class FabricCrossconnectService(FabricCrossconnectService_decl):
    class Meta:
        proxy = True

class FabricCrossconnectServiceInstance(FabricCrossconnectServiceInstance_decl):
   class Meta:
        proxy = True

class BNGPortMapping(BNGPortMapping_decl):
    class Meta:
        proxy = True

    def validate_range(self, pattern):
        for this_range in pattern.split(","):
            this_range = this_range.strip()
            if "-" in this_range:
                (first, last) = this_range.split("-")
                try:
                    int(first.strip())
                    int(last.strip())
                except ValueError:
                    raise XOSValidationError("Malformed range %s" % pattern)
            elif this_range.lower()=="any":
                pass
            else:
                try:
                    int(this_range)
                except ValueError:
                    raise XOSValidationError("Malformed range %s" % pattern)

    def save(self, *args, **kwargs):
        self.validate_range(self.s_tag)

        super(BNGPortMapping, self).save(*args, **kwargs)

