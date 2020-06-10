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

import os, sys
import json
from xossynchronizer.steps.syncstep import SyncStep, DeferredException
from xossynchronizer.modelaccessor import model_accessor, FabricCrossconnectServiceInstance, ServiceInstance, BNGPortMapping

import requests
from requests import ConnectionError
from requests.auth import HTTPBasicAuth
from requests.models import InvalidURL

from xosconfig import Config
from multistructlog import create_logger

from helpers import Helpers
log = create_logger(Config().get('logging'))


class SyncBNGPortMapping(SyncStep):
    provides = [BNGPortMapping]
    observes = BNGPortMapping

    def remove_crossconnect(self, fcsis):
        for fcsi in fcsis:
            onos = Helpers.get_fabric_onos_info(self.model_accessor, fcsi.owner)

            url = onos['url'] + '/onos/segmentrouting/xconnect'
            data = {"deviceId": fcsi.switch_datapath_id,
                    "vlanId": fcsi.s_tag}
            log.info("Sending request to ONOS", url=url)
            r = requests.delete(url, json=data, auth=HTTPBasicAuth(onos['user'], onos['pass']))
            if r.status_code != 204:
                raise Exception("Failed to remove fabric crossconnect in ONOS: %s" % r.text)
            fcsi.save(always_update_timestamp = True)

    def find_crossconnect(self, bng_s_tag):
        if(bng_s_tag.isnumeric()):
            xconnect_si = self.model_accessor.FabricCrossconnectServiceInstance.objects.filter(s_tag=int(bng_s_tag))
            if xconnect_si:
                log.info("Crossconnects belonging having s-tag equal to s-tags: %s" % xconnect_si)
                return xconnect_si
        else:
            [fcsis_range, fcsis_any] = [[], []]
            for fcsi in self.model_accessor.FabricCrossconnectServiceInstance.objects.all():
                if Helpers.range_matches(fcsi.s_tag, bng_s_tag):
                    fcsis_range.append(fcsi)
                else:
                    fcsis_any.append(fcsi)
            if fcsis_range:
                log.info("Crossconnects belonging to bng range s-tags: %s" % fcsis_range)
                return fcsis_range
            else:
                log.info("Crossconnects belonging to bng any s-tags: %s" % fcsis_any)
                return fcsis_any

    def check_switch_port_change(self, model):
        fcsis = self.find_crossconnect(model.s_tag)
        isChanged = False
        remove_xconnect = []
        if fcsis:
            for fcsi in fcsis:
                onos = Helpers.get_fabric_onos_info(self.model_accessor, fcsi.owner)
                log.info("ONOS belonging to fabric crossconnect instance: %s" % onos)

                url = onos['url'] + '/onos/segmentrouting/xconnect'
                log.info("Sending request to ONOS", url=url)
                r = requests.get(url, auth=HTTPBasicAuth(onos['user'], onos['pass']))
                if r.status_code != 200:
                    log.error(r.text)
                    raise Exception("Failed to get onos devices")
                else:
                    try:
                        log.info("Get devices response", json=r.json())
                    except Exception:
                        log.info("Get devices exception response", text=r.text) 
                xconnects = r.json()["xconnects"]
                for xconn in xconnects:
                    val = xconn['deviceId']
                    if(str(fcsi.switch_datapath_id) == str(val)):
                        if model.switch_port not in xconn['endpoints']:
                            remove_xconnect.append(fcsi)
            self.remove_crossconnect(remove_xconnect)
            isChanged = True
        else:
            log.info("No Fabric-xconnect-si found & saving bng instance.")
        return isChanged

    def sync_record(self, model):
        log.info("Sync started for BNGPortMapping instance: %s" % model.id)
        log.info('Syncing BNGPortMapping instance', object=str(model), **model.tologdict()) 
        if model.old_s_tag:
            if (model.old_s_tag != model.s_tag):
                fcsis = self.find_crossconnect(model.old_s_tag)
                if fcsis:
                    log.info("Xconnect-instance linked to bng : %s" % fcsis)
                    self.remove_crossconnect(fcsis)
                else:
                    log.info("No crossconnect is found for current bng instance")
            else:
                self.check_switch_port_change(model)
        else:
            if self.check_switch_port_change(model):
                log.info("Changed bng switch port is repushed to ONOS")
        log.info("Completing Synchronization for BNGPortMapping instance: %s" % model.id)

    def delete_record(self,model):
        log.info('Deleting BNGPortMapping instance', object=str(model), **model.tologdict()) 
        fcsis = self.find_crossconnect(model.s_tag)
        if fcsis:
            log.info("Xconnect-instance linked to bng : %s" % fcsis)
            self.remove_crossconnect(fcsis)
        log.info("Completing deletion of bng instance")
