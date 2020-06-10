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
# Generated by Django 1.11.29 on 2020-06-17 16:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fabric-crossconnect', '0004_auto_20190409_1839'),
    ]

    operations = [
        migrations.AddField(
            model_name='bngportmapping_decl',
            name='old_s_tag',
            field=models.CharField(blank=True, help_text=b'Field for tracking old s-tag of bngportmapping instance', max_length=1024, null=True),
        ),
    ]