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

        # We don't currently support changing the s_tag, dpid, or west_port of a FabricCrossconnectServiceInstance.
        # Need to think through the implications of changing these fields once sharing the same
        # FabricCrossconnectServiceInstance among many OLTService is supported.
        # See also SEBA-179.

        if (self.s_tag != self._initial["s_tag"]) and (self._initial["s_tag"] is not None):
            raise XOSValidationError("s_tag is immutable once set")

        if (self.dpid != self._initial["dpid"]) and (self._initial["dpid"]):
            raise XOSValidationError("dpid is immutable once set")

        if (self.west_port != self._initial["west_port"]) and (self._initial["west_port"] is not None):
            raise XOSValidationError("west_port is immutable once set")

        super(BNGPortMapping, self).save(*args, **kwargs)

