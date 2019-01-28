# The MIT License (MIT)
#
# Copyright (c) 2016, The MITRE Corporation. All rights reserved.
#
# Approved for Public Release; Distribution Unlimited 14-1511
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# https://raw.githubusercontent.com/crits/crits_services/master/office_meta_service/office_meta.py
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals


__author__ = "Mike Goffin"
__license__ = "MPL 2.0"

import sys
import time
import array
import hashlib
import binascii
import struct
import pprint

sys.setrecursionlimit(10000)

class OfficeParser(object):
    summary_mapping = {
        b"\xE0\x85\x9F\xF2\xF9\x4F\x68\x10\xAB\x91\x08\x00\x2B\x27\xB3\xD9": {
            'name':         'SummaryInformation',
            0x01:           'Codepage',
            0x02:           'Title',
            0x03:           'Subject',
            0x04:           'Author',
            0x05:           'Keywords',
            0x06:           'Comments',
            0x07:           'Template',
            0x08:           'Last Saved By',
            0x09:           'Revision Number',
            0x0a:           'Total Edititing Time',
            0x0b:           'Last printed Date',
            0x0c:           'Creation Date',
            0x0d:           'Last Saved Date',
            0x0e:           'Number of Pages',
            0x0f:           'Number of Words',
            0x10:           'Number of Characters',
            0x11:           'Thumbnail',
            0x12:           'Name of Creating Appliction',
            0x13:           'Security',
        },
        b"\x02\xD5\xCD\xD5\x9C\x2E\x1B\x10\x93\x97\x08\x00\x2B\x2C\xF9\xAE": {
            'name':         'DocumentSummaryInformation',
            0x01:           'Codepage',
            0x02:           'Category',
            0x03:           'Presentation Target',
            0x04:           'Number of Bytes',
            0x05:           'Number of Lines',
            0x06:           'Number of Paragraphs',
            0x07:           'Number of Slides',
            0x08:           'Number of Notes',
            0x09:           'Number of Hidden Slides',
            0x0a:           'MMClips',
            0x0b:           'ScaleCrops',
            0x0c:           'HeadingPairs',
            0x0d:           'Title of Parts',
            0x0e:           'Manager',
            0x0f:           'Company',
            0x10:           'Links up to date'
        },
        b"\x05\xD5\xCD\xD5\x9C\x2E\x1B\x10\x93\x97\x08\x00\x2B\x2C\xF9\xAE": {
            'name':         'Other DocumentSummaryInformation',
            # what the heck do these values mean?
        }
    }
    office_magic = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    def __init__(self, data, verbose=False):
        self.data = data
        self.verbose = verbose
        self.office_header = {}
        self.directory = []
        self.properties = []
        self.fat_table = []
        self.mini_fat_table = []
        self.mini_fat_data = ''
        self.sector_size = 512

    def get_mini_fat_chain(self, sector):
        if sector in [0xffffffff, 0xfffffffe]:
            return ''
        elif sector < len(self.mini_fat_table):
            if self.mini_fat_table[sector] == 0xfffffffe:
                return self.get_mini_fat_sector(sector)
            elif sector != self.mini_fat_table[sector]:
                data = self.get_mini_fat_sector(sector)
                return data + self.get_mini_fat_chain(self.mini_fat_table[sector])
        return ''

    def get_mini_fat_sector(self, sector):
        return self.mini_fat_data[(sector) * 64 : (sector + 1) * 64]

    def get_fat_chain(self, sector):
        if sector in [0xffffffff, 0xfffffffe]:
            return ''
        elif sector < len(self.fat_table):
            if self.verbose:
                print("request sector %d - len %d" % (sector, len(self.fat_table)))
            if self.fat_table[sector] == 0xfffffffe:
                return self.get_fat_sector(sector)
            elif sector != self.fat_table[sector]:
                data = self.get_fat_sector(sector)
                return data + self.get_fat_chain(self.fat_table[sector])
        return ''

    def get_mini_fat_sector_chain(self, sector):
        if sector in [0xffffffff, 0xfffffffe, 0xfffffffd]:
            return []
        elif sector < len(self.fat_table):
            if self.fat_table[sector] == 0xfffffffe:
                return [sector]
            elif sector != self.fat_table[sector]:
                return [sector] + self.get_mini_fat_sector_chain(self.fat_table[sector])
        return []

    def get_fat_sector(self, sector):
        return self.data[(sector + 1) * self.sector_size : (sector+2) * self.sector_size]

    def make_fat(self, sector_list):
        fat = array.array('I')
        if self.verbose:
            print("sector_list = %s" % sector_list)
        for sector in sector_list:
            sect_data = (self.get_fat_sector(sector))
            if len(sect_data) > 0:
                fat += array.array('I', self.get_fat_sector(sector))
            else:
                if self.verbose:
                    print("!!!!! Error, invalid SAT table, sector missing")
        return fat

    def parse_office_header(self):
        office_header = {
            'magic':                binascii.hexlify(self.data[:8]),
            'clsid':                binascii.hexlify(self.data[8:24]),
            'min_ver':              struct.unpack('H', self.data[24:26])[0],
            'maj_ver':              struct.unpack('H', self.data[26:28])[0],
            'byte_order':           struct.unpack('H', self.data[28:30])[0],
            'sector_shift':         struct.unpack('H', self.data[30:32])[0],
            'mini_sector_shift':    struct.unpack('H', self.data[32:34])[0],
            'reserved':             binascii.hexlify(self.data[34:40]),
            'num_dir_sect':         struct.unpack('I', self.data[40:44])[0],
            'num_fat_sect':         struct.unpack('I', self.data[44:48])[0],
            'first_dir_sect':       struct.unpack('I', self.data[48:52])[0],
            'transaction_sig':      struct.unpack('I', self.data[52:56])[0],
            'mini_stream_cutoff':   struct.unpack('I', self.data[56:60])[0],
            'first_mini_fat_sect':  struct.unpack('I', self.data[60:64])[0],
            'num_mini_fat_sect':    struct.unpack('I', self.data[64:68])[0],
            'first_difat':          struct.unpack('I', self.data[68:72])[0],
            'num_difat':            struct.unpack('I', self.data[72:76])[0],
            'difat_0':              struct.unpack('I', self.data[76:80])[0],
        }
        if self.verbose:
            pprint.pprint(office_header)
        if office_header['maj_ver'] in [3,4] and office_header['byte_order'] == 65534:
            fat_array = array.array('I', self.data[76:76 + (4 * office_header['num_fat_sect'])])
            self.fat_table = self.make_fat(fat_array)
            if office_header['num_mini_fat_sect'] > 0:
                mini_fat_sectors = self.get_mini_fat_sector_chain(office_header['first_mini_fat_sect'])
                if mini_fat_sectors:
                    self.mini_fat_table = self.make_fat(mini_fat_sectors)
        if self.verbose:
            print("[+] FAT Tables")
            print(self.fat_table)
            print(self.mini_fat_table)
        return office_header

    def find_office_header(self):
        offset = self.data.find(self.office_magic)
        if offset >= 0:
            if self.verbose:
                print("\t[+] found office header at offset %04X" % offset)
            self.data = self.data[offset:]
            return offset
        if self.verbose:
            print("\t[-] could not find office header")
        return None

    def parse_property_set_header(self, prop_data):
        if len(prop_data) >= 28:
            system_values = {
                0:  'Win16',
                1:  'Macintosh',
                2:  'Win32',
            }
            property_set_header = {
                'byte_order':           binascii.hexlify(prop_data[:2]),
                'format':               struct.unpack('H', prop_data[2:4])[0],
                'system_version':       struct.unpack('I', prop_data[4:8])[0],
                'clsid':                binascii.hexlify(prop_data[8:24]),
                'num_properties':       struct.unpack('I', prop_data[24:28])[0],
                'property_list':        [],
            }
            # provide a text string for the system value
            if property_set_header['num_properties'] not in [1,2] or property_set_header['byte_order'] != b'feff':
                if self.verbose:
                    print("[+] invalid property set record")
                return property_set_header
            property_set_header['system_name'] = system_values.get(property_set_header['system_version'], 'Unknown')
            for i in range(property_set_header['num_properties']):
                if len(prop_data) >= (28 + (i*20) + 20):
                    offset = (i * 20) + 28
                    prop = {
                        'clsid':            binascii.hexlify(prop_data[offset:offset+16]),
                        'offset':           struct.unpack('I', prop_data[offset+16:offset+20])[0],
                    }
                    property_set_header["property_list"].append(prop)
            return property_set_header
        return {}

    def lookup_property_id(self, prop_id, prop_type):
        table = self.summary_mapping.get(binascii.unhexlify(prop_type), {})
        if table:
            return table.get(prop_id, 'Unknown (%d)' % prop_id)
        return 'Unknown'

    def timestamp_string(self, wtimestamp):
        timestamp = (wtimestamp / 10000000) - 11644473600
        if timestamp > 0:
            datestring = time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(timestamp))
        else:
            timestamp = (wtimestamp / 10000000)
            datestring = "%02d:%02d:%02d" % (timestamp / 360, timestamp / 60, timestamp % 60)
        return (timestamp, datestring)

    def parse_properties(self, prop_data, prop_type):
        if len(prop_data) >= 8:
            properties = {
                'size':                 struct.unpack('I', prop_data[:4])[0],
                'num_properties':       struct.unpack('I', prop_data[4:8])[0],
                'properties':           [],
            }
            for i in range(properties['num_properties']):
                offset = (i * 8) + 8
                if len(prop_data) < (offset+8):
                    break
                prop = {
                    'id':               struct.unpack('I', prop_data[offset:offset+4])[0],
                    'offset':           struct.unpack('I', prop_data[offset+4:offset+8])[0],
                }
                offset = prop['offset']
                if offset >= len(prop_data):
                    continue
                prop['name'] = self.lookup_property_id(prop['id'], prop_type)
                prop['type'] = struct.unpack('I', prop_data[offset:offset+4])[0]
                if prop['type'] == 0x02:
                    prop['value'] = struct.unpack('h', prop_data[offset+4:offset+6])[0]
                elif prop['type'] == 0x03:
                    prop['value'] = struct.unpack('i', prop_data[offset+4:offset+8])[0]
                elif prop['type'] == 0x1e:
                    prop['str_len'] = struct.unpack('i', prop_data[offset+4:offset+8])[0]
                    if properties.get('code_page', 0) == 0x4b0:
                        prop['value'] = prop_data[offset+8:offset+8+prop['str_len']-2]
                    else:
                        prop['value'] = prop_data[offset+8:offset+8+prop['str_len']-1].replace(b'\x00', b'')
                elif prop['type'] == 0x0b:
                    prop['value'] = binascii.hexlify(prop_data[offset+4:offset+8])
                elif prop['type'] == 0x40:
                    prop['value'] = struct.unpack('Q', prop_data[offset+4:offset+12])[0]
                    (prop['timestamp'], prop['date']) = self.timestamp_string(prop['value'])
                elif prop['type'] == 0x1f:
                    prop['str_len'] = struct.unpack('I', prop_data[offset+4:offset+8])[0]
                    prop['value'] = prop_data[offset+8: offset+8+(prop['str_len'] * 2)]
                else:
                    prop['value'] = binascii.hexlify(prop_data[:8])
                if isinstance(prop['value'], str):
                    prop['value'] = prop['value'].decode('cp1252').encode('utf-8')
                elif isinstance(prop['value'], bytes):
                    prop['value'] = prop['value'].decode('utf-8')
                elif isinstance(prop['value'], int):
                    prop['value'] = str(prop['value'])
                prop['result'] = "%s: %s" % (prop['name'], prop['value'])
                if prop['id'] == 0x01:
                    properties['code_page'] = prop['result']
                properties['properties'].append(prop)
            return properties
        return {}

    def parse_summary_information(self, summary_data, prop_type):
        if self.verbose:
            print("\t[+] parsing %d bytes of summary_data for %s" % (len(summary_data), prop_type))
        if len(summary_data) >= 28:
            property_set_header = self.parse_property_set_header(summary_data)
            for item in property_set_header["property_list"]:
                item['properties'] = self.parse_properties(summary_data[item["offset"]:], item["clsid"])
                if self.verbose:
                    pprint.pprint(item)
            return property_set_header
        return {}

    def parse_directory(self, data):
        if len(data) >= 128:
            #if data[:8] == '\x00\x10\x00\x00\x00\x00\x00\x00':
            #    print "trucating first 8 bytes"
            #    self.parse_directory(data[8:])
            entry = {
                'name':             data[:64],
                'name_len':         struct.unpack('H', data[64:66])[0],
                'object_type':      struct.unpack('B', data[66:67])[0],
                'color':            struct.unpack('B', data[67:68])[0],
                'left_sibling':     struct.unpack('I', data[68:72])[0],
                'right_sibling':    struct.unpack('I', data[72:76])[0],
                'child':            struct.unpack('I', data[76:80])[0],
                'clsid':            binascii.hexlify(data[80:96]),
                'state':            struct.unpack('I', data[96:100])[0],
                'create_time':      struct.unpack('Q', data[100:108])[0],
                'modify_time':      struct.unpack('Q', data[108:116])[0],
                'start_sect':       struct.unpack('I', data[116:120])[0],
                'stream_size':      struct.unpack('Q', data[120:128])[0],
            }
            # /version 3 limits this field to 32 bits
            if self.office_header['maj_ver'] == 3:
                entry['stream_size'] = entry['stream_size'] & 0x7fffffff
            # fix up the name to a normalized ascii name for display
            name_len = entry['name_len'] - 2
            norm_name = entry['name'][:name_len].replace(b'\x00', b'')
            # check for known subtype headers indicating special objects
            if len(norm_name) >= 1:
                if norm_name[0:1] in [b'\x01', b'\x03', b'\x05']:
                    norm_name = norm_name[1:]
            entry['norm_name'] = norm_name
            entry['result'] = norm_name
            # fetch any directory data if available
            if entry['object_type'] == 0x05:
                dir_data = self.get_fat_chain(entry['start_sect'])
                self.mini_fat_data = dir_data
            elif entry['stream_size'] > 0 and entry['stream_size'] < self.office_header['mini_stream_cutoff']:
                dir_data = self.get_mini_fat_chain(entry['start_sect'])
            elif entry['stream_size'] >= self.office_header['mini_stream_cutoff']:
                dir_data = self.get_fat_chain(entry['start_sect'])
            else:
                 dir_data = ''
            if self.verbose:
                print("[+] got %d data from %s" % (len(dir_data), entry['result']))
            # check the directory specific content and parse
            if entry['object_type'] in [0,2] and len(dir_data) > 0:
                for clsid in list(self.summary_mapping.keys()):
                    if clsid in dir_data:
                        self.properties.append(self.parse_summary_information(dir_data, clsid))
                        if self.verbose:
                            print(self.properties)
            if len(dir_data) > 0:
                entry['md5'] = hashlib.md5(dir_data).hexdigest()
                entry['data'] = dir_data
            if self.verbose:
                pprint.pprint(entry)
            self.directory.append(entry)
            self.parse_directory(data[128:])
        return {}

    def pretty_print(self):
        print("\nDocument Summary\n" + "-" * 40)
        print("%20s:%20s" % ("Magic", self.office_header['magic']))
        print("%20s:%20s" % ("Version", "%d.%d" % (self.office_header['maj_ver'], self.office_header['min_ver'])))
        print("\nDirectories\n" + "-" * 40)
        for directory in self.directory:
            if len(directory['norm_name']) > 0:
                print("\t%40s - %10d - %32s" % (directory.get('norm_name', ''), directory.get('stream_size', 0), directory.get('md5', 0)))
        print("\nProperties\n" + "-" * 40)
        for prop_list in self.properties:
            for prop in prop_list['property_list']:
                prop_summary = self.summary_mapping.get(binascii.unhexlify(prop['clsid']), {})
                prop_name = prop_summary.get('name', 'Unknown')
                print("\n\t%s" % prop_name)
                if len(prop.get('properties', [])) > 0:
                    if len(prop['properties'].get('properties', [])) > 0:
                        for item in prop['properties']['properties']:
                            value = item.get('date', item['value'])
                            print("%50s - %40s" % (item['name'], value))
    def parse_office_doc(self):
        if (self.find_office_header() == None):
            return None
        self.office_header = self.parse_office_header()
        if self.office_header['maj_ver'] in [3,4]:
            self.parse_directory(self.get_fat_chain(self.office_header['first_dir_sect']))
