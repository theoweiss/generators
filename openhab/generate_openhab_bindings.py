#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
openHAB Bindings Config Generator
Copyright (C) 2019 Theo Weiss <theo@m1theo.org>

generate_openhab_bindings.py: Generator for openHAB bindings configuration

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

import sys
import os
import shutil

sys.path.append(os.path.split(os.getcwd())[0])
import common
import openhab_common

class OpenhabBindingsPacket(openhab_common.OpenhabPacket):
    def has_setter(self):
        return True if len(self.get_elements(direction="in")) > 0 else False
        
class OpenhabBindingsDevice(openhab_common.OpenhabDevice):
    def get_openhab_class(self):
        template = """
\"{0}\": {{
    \"bricklet\": \"{1}\",
    \"className\": \"{2}\",
    \"brickletConfig\": \"{3}DeviceConfig\",
    \"package\": \"{0}\",
    \"deviceType\": \"{0}\",
    \"callbackChannels\": \"{4}\",
    \"hasConfig\": \"{5}\",
    \"configureTemplate\": \"Configure{6}.mvel\",
    
"""
        has_config = "true" if self.has_config() else "false"
        has_callbacks = "true" if len(self.get_packets('callback')) > 0 else "false"
        return template.format(self.get_name().camel.lower(), self.get_java_class_name(), self.get_openhab_class_name(), self.get_name().camel, has_callbacks, has_config, self.get_name().camel)

    def has_config(self):
        has_config = False
        for packet in self.get_packets('function'):
            if packet.has_setter():
                has_config = True
                break
        return has_config
    

    def create_device_extra_config(self):
        template = """#
# {0}
#
\"xconfig\": {{
    \"config_func\": [{1}],
    \"setter_func\": [{1}],
    \"getter_func\": [{2}],
    \"callbacks\": [{3}]
}}

"""
        blacklist = [
            "Get Bootloader Mode",
            "Get Chip Temperature",
            "Reset",
            "Read UID",
            "Write UID",
            "Write Firmware",
            "Set Write Firmware Pointer",
            "Set Bootloader Mode"
        ]
        blacklist_end = [
            "Callback Configuration",
            "Callback Period",
            "Callback Threshold"
        ]
        setter = []
        getter = []
        callbacks = []
        callback_getters = []
        for packet in self.get_packets('callback'):
            callbacks.append(packet.get_name().space)
            callback_getters.append("Get " + packet.get_name().space)
        for packet in self.get_packets('function'):
            if not packet.get_name().space in blacklist:
                end = " ".join(packet.get_name().space.split(' ')[-2:])
                if not end in blacklist_end:
                    print end
                    if packet.has_setter():
                        setter.append(packet.get_name().space)
                    else:
                        if not packet.get_name().space in callback_getters:
                            getter.append(packet.get_name().space)
        setter_entry = ", ".join(list(map(lambda x: "\"" + x + "\"", setter)))
        getter_entry = ", ".join(list(map(lambda x: "\"" + x + "\"", getter)))

        callbacks_entry = ", ".join(list(map(lambda x: "\"" + x + "\"", callbacks)))

        return template.format(self.get_openhab_device_name(), setter_entry, getter_entry, callbacks_entry)

    def get_config(self):
        template = """
    \"config\": [
      {{
        \"name\": \"{0}\",
        \"type\": \"Integer\",
        \"ohtype\": \"integer\",
        \"ohmultiple\": \"false\",
        \"converter\": \"Integer.parseInt\",
        \"getter\": \"getReferenceAirPressure\",
        \"default\": \"1013250\",
        \"min\": \"10000\",
        \"max\": \"1200000\",
        \"description\": \"Reference air pressure in mbar/1000. Default is 1013250 => 1013.250mbar\"
      }}
    ]
"""
        entries = []
        if not self.has_config:
            return config
        else:
         for packet in self.get_packets('function'):
            if packet.has_setter():
                entries.append(template.format(packet.get_openhab_name()))
        return ",\n".join(entries)

    def get_openhab_source(self):
        source  = self.get_openhab_class()
        source += self.get_config()
        return source

class OpenhabBindingsGenerator(common.BindingsGenerator):
    def __init__(self, *args, **kwargs):
        common.BindingsGenerator.__init__(self, *args, **kwargs)
        
        self.part_files = []

    def get_bindings_name(self):
        return 'openhab'

    def get_bindings_display_name(self):
        return 'openHAB'

    def get_device_class(self):
        return OpenhabBindingsDevice

    def get_packet_class(self):
        return OpenhabBindingsPacket

    def get_element_class(self):
        return openhab_common.MQTTElement

    def generate_xconfig(self, device):
        xconfig_dir = os.path.join(self.get_root_dir(), "xconfig")
        if device.is_bricklet():
            filename = '{0}-config.py'.format(device.get_openhab_device_name())

            with open(os.path.join(xconfig_dir, filename), 'w') as f:
                f.write(device.create_device_extra_config())

    def generate(self, device):
        self.generate_xconfig(device)
        filename = '{0}.part'.format(device.get_openhab_device_name())

        if device.is_bricklet():
            with open(os.path.join(self.get_bindings_dir(), filename), 'w') as f:
                f.write(device.get_openhab_source())

            if device.is_released():
                self.part_files.append(filename)

    def finish(self):
        common.BindingsGenerator.finish(self)

        root_dir = self.get_root_dir()
        bindings_dir = self.get_bindings_dir()
        version = self.get_changelog_version()
        openhab = open(os.path.join(bindings_dir, 'tinkerforge_openhab'), 'w')

        for filename in sorted(self.part_files):
            if filename.endswith('.part'):
                with open(os.path.join(bindings_dir, filename), 'r') as f:
                    openhab.write(f.read())

        openhab.close()

def generate(root_dir):
    xconfig_dir = os.path.join(root_dir, "xconfig")
    if os.path.exists(xconfig_dir):
        shutil.rmtree(xconfig_dir)
    os.makedirs(xconfig_dir)

    common.generate(root_dir, 'en', OpenhabBindingsGenerator)

if __name__ == '__main__':
    generate(os.getcwd())
