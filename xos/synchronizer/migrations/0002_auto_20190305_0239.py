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

# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2019-03-05 07:39
from __future__ import unicode_literals

import core.models.xosbase_header
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('fabric-crossconnect', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bngportmapping_decl',
            name='backend_status',
            field=models.CharField(blank=True, default=b'Provisioning in progress', max_length=1024),
        ),
        migrations.AlterField(
            model_name='bngportmapping_decl',
            name='leaf_model_name',
            field=models.CharField(blank=True, help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024),
        ),
        migrations.AlterField(
            model_name='bngportmapping_decl',
            name='updated',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer'),
        ),
        migrations.AlterField(
            model_name='fabriccrossconnectserviceinstance_decl',
            name='switch_datapath_id',
            field=core.models.xosbase_header.StrippedCharField(blank=True, help_text=b'Datapath id of switch where crossconnect will be installed', max_length=256),
        ),
    ]
