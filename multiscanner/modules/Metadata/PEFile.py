# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
try:
    import pefile
except ImportError:
    print("pefile module not installed...")
    pefile = False

try:
    xrange(0, 1)
except NameError:
    xrange = range

__author__ = "Drew Bonasera"
__credits__ = ["Wesley Shields", "Mike Goffin"]
__license__ = "MPL 2.0"

import bitstring
import string
import bz2
import hashlib
import binascii
import struct
from time import strftime, localtime

from multiscanner.common.utils import convert_encoding
from multiscanner.config import PY3

TYPE = "Metadata"
NAME = "pefile"
REQUIRES = ["libmagic"]
DEFAULTCONF = {
    'ENABLED': True
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not pefile:
        return False
    if None in REQUIRES:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []
    libmagicresults, libmagicmeta = REQUIRES[0]

    for fname, libmagicresult in libmagicresults:
        if fname not in filelist:
            print("DEBUG: File not in filelist")
        if not libmagicresult.startswith('PE32'):
            continue
        result = {}
        pe = pefile.PE(fname)
        result['pehash'] = _get_pehash(pe)
        check, sha = _get_rich_header(pe)
        if check:
            result['rich_header_checksum'] = check
        if sha:
            result['rich_header_sha256'] = sha
        if callable(getattr(pe, 'get_imphash', None)):
            try:
                result['import_hash'] = pe.get_imphash()
            except Exception as e:
                # TODO: log exception
                pass
        if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
            result['resource_data'] = _dump_resource_data("ROOT",
            pe.DIRECTORY_ENTRY_RESOURCE,
            pe,
            False)
        result['sections'] = _get_sections(pe)
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            result['imports'] = _get_imports(pe)
        else:
            result['imports'] = None
        if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            result['exports'] = _get_exports(pe)
        else:
            result['exports'] = None
        result['pe_timestamp'] = _get_timestamp(pe)
        if hasattr(pe, 'DIRECTORY_ENTRY_DEBUG'):
            result['debug_info'] = _get_debug_info(pe)
        if hasattr(pe, 'VS_VERSIONINFO'):
            result['version_info'] = _get_version_info(pe)
        if hasattr(pe, 'DIRECTORY_ENTRY_TLS'):
            ret = _get_tls_info(pe)
            if ret:
                result['tls_callback_info'] = ret
        result = convert_encoding(result)
        results.append((fname, result))
    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Version"] = pefile.__version__
    metadata["Include"] = False
    return (results, metadata)


# This section is an adaption from the CRITS pefile service
# https://github.com/MITRECND/crits_services/blob/master/peinfo_service/__init__.py
def _get_pehash(exe):
    # image characteristics
    img_chars = bitstring.BitArray(hex(exe.FILE_HEADER.Characteristics))
    # Error condition
    # TODO: Insert padding instead of breaking
    while len(img_chars) < 16:
        return None
    # pad to 16 bits
    img_chars = bitstring.BitArray(bytes=img_chars.tobytes())

    img_chars_xor = img_chars[0:8] ^ img_chars[8:16]

    # start to build pehash
    pehash_bin = bitstring.BitArray(img_chars_xor)

    # subsystem -
    sub_chars = bitstring.BitArray(hex(exe.FILE_HEADER.Machine))
    # pad to 16 bits
    sub_chars = bitstring.BitArray(bytes=sub_chars.tobytes())
    sub_chars_xor = sub_chars[0:8] ^ sub_chars[8:16]
    pehash_bin.append(sub_chars_xor)

    # Stack Commit Size
    stk_size = bitstring.BitArray(hex(exe.OPTIONAL_HEADER.SizeOfStackCommit))
    if PY3:
        stk_size_bits = stk_size.bin.zfill(32)
    else:
        stk_size_bits = string.zfill(stk_size.bin, 32)
    # now xor the bits
    stk_size = bitstring.BitArray(bin=stk_size_bits)
    stk_size_xor = stk_size[8:16] ^ stk_size[16:24] ^ stk_size[24:32]
    # pad to 8 bits
    stk_size_xor = bitstring.BitArray(bytes=stk_size_xor.tobytes())
    pehash_bin.append(stk_size_xor)

    # Heap Commit Size
    hp_size = bitstring.BitArray(hex(exe.OPTIONAL_HEADER.SizeOfHeapCommit))
    if PY3:
        hp_size_bits = hp_size.bin.zfill(32)
    else:
        hp_size_bits = string.zfill(hp_size.bin, 32)
    # now xor the bits
    hp_size = bitstring.BitArray(bin=hp_size_bits)
    hp_size_xor = hp_size[8:16] ^ hp_size[16:24] ^ hp_size[24:32]
    # pad to 8 bits
    hp_size_xor = bitstring.BitArray(bytes=hp_size_xor.tobytes())
    pehash_bin.append(hp_size_xor)

    # Section chars
    for section in exe.sections:
        # virutal address
        sect_va = bitstring.BitArray(hex(section.VirtualAddress))
        sect_va = bitstring.BitArray(bytes=sect_va.tobytes())
        sect_va_bits = sect_va[8:32]
        pehash_bin.append(sect_va_bits)

        # rawsize
        sect_rs = bitstring.BitArray(hex(section.SizeOfRawData))
        sect_rs = bitstring.BitArray(bytes=sect_rs.tobytes())
        if PY3:
            sect_rs_bits = sect_rs.bin.zfill(32)
        else:
            sect_rs_bits = string.zfill(sect_rs.bin, 32)
        sect_rs = bitstring.BitArray(bin=sect_rs_bits)
        sect_rs = bitstring.BitArray(bytes=sect_rs.tobytes())
        sect_rs_bits = sect_rs[8:32]
        pehash_bin.append(sect_rs_bits)

        # section chars
        sect_chars = bitstring.BitArray(hex(section.Characteristics))
        sect_chars = bitstring.BitArray(bytes=sect_chars.tobytes())
        sect_chars_xor = sect_chars[16:24] ^ sect_chars[24:32]
        pehash_bin.append(sect_chars_xor)

        # entropy calulation
        address = section.VirtualAddress
        size = section.SizeOfRawData
        raw = exe.write()[address + size:]
        if size == 0:
            kolmog = bitstring.BitArray(float=1, length=32)
            pehash_bin.append(kolmog[0:8])
            continue
        bz2_raw = bz2.compress(raw)
        bz2_size = len(bz2_raw)
        # k = round(bz2_size / size, 5)
        k = bz2_size / size
        kolmog = bitstring.BitArray(float=k, length=32)
        pehash_bin.append(kolmog[0:8])

    m = hashlib.sha1()
    m.update(pehash_bin.tobytes())
    output = m.hexdigest()
    return output

# http://www.ntcore.com/files/richsign.htm


def _get_rich_header(pe):
    rich_hdr = pe.parse_rich_header()
    if not rich_hdr:
        return (None, None)
    data = {"raw": str(rich_hdr['values'])}
    richchecksum = hex(rich_hdr['checksum'])
    # self._add_result('rich_header', hex(rich_hdr['checksum']), data)

    # Generate a signature of the block. Need to apply checksum
    # appropriately. The hash here is sha256 because others are using
    # that here.
    #
    # Most of this code was taken from pefile but modified to work
    # on the start and checksum blocks.
    try:
        rich_data = pe.get_data(0x80, 0x80)
        if len(rich_data) != 0x80:
            return (richchecksum, None)
        data = list(struct.unpack("<32I", rich_data))
    except pefile.PEFormatError as e:
        return (richchecksum, None)

    checksum = data[1]
    headervalues = []

    for i in xrange(len(data) // 2):
        if data[2 * i] == 0x68636952:  # Rich
            if data[2 * i + 1] != checksum:
                # self._parse_error('Rich Header corrupted')
                return (richchecksum, None)
            break
        headervalues += [data[2 * i] ^ checksum, data[2 * i + 1] ^ checksum]

    sha_256 = hashlib.sha256()
    for hv in headervalues:
        sha_256.update(struct.pack('<I', hv))
    return (richchecksum, sha_256.hexdigest())


def _dump_resource_data(name, dir, pe, save):
    resultlist = []
    for i in dir.entries:
        try:
            if hasattr(i, 'data'):
                x = i.data
                rva = x.struct.OffsetToData
                "%s_%s_%s" % (name, i.name, x.struct.name)
                size = x.struct.Size
                data = pe.get_memory_mapped_image()[rva:rva + size]
                if not data:
                    data = ""
                # if len(data) > 0:
                #     if (save or data[:2] == 'MZ' or data[:4] == "%%PDF"):
                #         self._debug("Adding new file from resource len %d - %s" % (len(data), rname))
                #         self.added_files.append((rname, data))
                results = {
                        "resource_type": x.struct.name,
                        "resource_id": i.id,
                        "language": x.lang,
                        "sub_language": x.sublang,
                        "address": x.struct.OffsetToData,
                        "size": len(data),
                        "md5": hashlib.md5(data).hexdigest(),
                }
                # self._debug("Adding result for resource %s" % i.name)
                # self._add_result('pe_resource', x.struct.name, results)
                resultlist.append(results)
            if hasattr(i, "directory"):
                # self._debug("Parsing next directory entry %s" % i.name)
                resultlist.extend(_dump_resource_data(name + "_%s" % i.name,
                                         i.directory, pe, save))
        except Exception as e:
            print('pefile:', e)
            return None
        return resultlist


def _get_sections(pe):
    resultdict = {}
    for section in pe.sections:
        try:
            section_name = section.Name.decode('UTF-8', errors='replace')
            if section_name == "":
                section_name = "NULL"
            data = {
                    "virt_address": section.VirtualAddress,
                    "virt_size": section.Misc_VirtualSize,
                    "size": section.SizeOfRawData,
                    "md5": section.get_hash_md5(),
                    "entropy": section.get_entropy(),
            }
            # self._add_result('pe_section', section_name, data)
            resultdict[section_name] = data
        except Exception as e:
            continue
    return resultdict


def _get_imports(pe):
    result = {}
    try:
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for imp in entry.imports:
                if isinstance(entry.dll, bytes):
                    entry.dll = entry.dll.decode('utf-8')
                if isinstance(imp.ordinal, bytes):
                    entry.dll = imp.ordinal.decode('utf-8')
                if imp.name:
                    name = imp.name
                else:
                    name = "%s#%s" % (entry.dll, imp.ordinal)
                data = {
                        "dll": entry.dll,
                        "ordinal": imp.ordinal,
                }
                # self._add_result('pe_import', name, data)
                result[name] = data
    except Exception as e:
        # self._parse_error("imports", e)
        print(e)
    return result


def _get_exports(pe):
    results = {}
    try:
        for entry in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            data = {"rva_offset": pe.OPTIONAL_HEADER.ImageBase + entry.address}
            # self._add_result('pe_export', entry.name, data)
            results[entry.name] = data
    except Exception as e:
        # self._parse_error("exports", e)
        pass
    return results


def _get_timestamp(pe):
    try:
        timestamp = pe.FILE_HEADER.TimeDateStamp
        time_string = strftime('%Y-%m-%d %H:%M:%S', localtime(timestamp))
        # data = {"raw": timestamp}
        # self._add_result('pe_timestamp', time_string, data)
        return time_string
    except Exception as e:
        # self._parse_error("timestamp", e)
        return None


def _get_debug_info(pe):
    # woe is pefile when it comes to debug entries
    # we're mostly interested in codeview stuctures, namely NB10 and RSDS
    results = {}
    try:
        for dbg in pe.DIRECTORY_ENTRY_DEBUG:
            if hasattr(dbg.struct, "Type"):
                dbg_path = "debug"
                result = {
                     'MajorVersion': dbg.struct.MajorVersion,
                     'MinorVersion': dbg.struct.MinorVersion,
                     'PointerToRawData': dbg.struct.PointerToRawData,
                     'SizeOfData': dbg.struct.SizeOfData,
                     'TimeDateStamp': dbg.struct.TimeDateStamp,
                     'TimeDateString': strftime('%Y-%m-%d %H:%M:%S', localtime(dbg.struct.TimeDateStamp)),
                     'Type': dbg.struct.Type,
                     'subtype': 'pe_debug',
                }
                # type 0x2 is codeview, though not any specific version
                # for other types we don't parse them yet
                # but sounds like a great project for an enterprising CRITs coder...
                if dbg.struct.Type == 0x2:
                    debug_offset = dbg.struct.PointerToRawData
                    debug_size = dbg.struct.SizeOfData
                    # ok, this probably isn't right, fix me
                    if debug_size < 0x200 and debug_size > 0:
                        # there might be a better way than __data__ in pefile to get the raw data
                        # i think that get_data uses RVA's, which this requires physical address
                        debug_data = pe.__data__[debug_offset:debug_offset + debug_size]
                        # now we need to check the codeview version,
                        # http://www.debuginfo.com/articles/debuginfomatch.html
                        # as far as I can tell the gold is in RSDS and NB10
                        if debug_data[:4] == "RSDS":
                            result.update({
                                'DebugSig': debug_data[0x00:0x04],
                                'DebugGUID': binascii.hexlify(debug_data[0x04:0x14]),
                                'DebugAge': struct.unpack('I', debug_data[0x14:0x18])[0],
                            })
                            if dbg.struct.SizeOfData > 0x18:
                                dbg_path = debug_data[0x18:dbg.struct.SizeOfData - 1].decode('UTF-8', errors='replace')
                                result.update({
                                    'DebugPath': "%s" % dbg_path,
                                    'result': "%s" % dbg_path,
                                })
                        if debug_data[:4] == "NB10":
                            result.update({
                                'DebugSig': debug_data[0x00:0x04],
                                'DebugTime': struct.unpack('I', debug_data[0x08:0x0c])[0],
                                'DebugAge': struct.unpack('I', debug_data[0x0c:0x10])[0],
                            })
                            if dbg.struct.SizeOfData > 0x10:
                                dbg_path = debug_data[0x10:dbg.struct.SizeOfData - 1].decode('UTF-8', errors='replace')
                                result.update({
                                    'DebugPath': "%s" % dbg_path,
                                    'result': "%s" % dbg_path,
                                })
                # self._add_result('pe_debug', dbg_path, result)
                results[dbg_path] = result
    except Exception as e:
        # self._parse_error("could not extract debug info", e)
        print(e)
    return results


def _get_version_info(pe):
    results = {}
    if hasattr(pe, 'FileInfo'):
        try:
            for entry in pe.FileInfo:
                if hasattr(entry, 'StringTable'):
                    for st_entry in entry.StringTable:
                        for str_entry in st_entry.entries.items():
                            try:
                                value = str_entry[1].encode('ascii')
                                # result = {
                                #     'key': str_entry[0],
                                #     'value': value,
                                # }
                            except Exception as e:
                                # TODO: log exception
                                value = str_entry[1].encode('ascii', errors='ignore')
                                # raw = binascii.hexlify(str_entry[1].encode('utf-8'))
                                # result = {
                                #     'key': str_entry[0],
                                #     'value': value,
                                #     'raw': raw,
                                # }
                            # result_name = str_entry[0] + ': ' + value[:255]
                            # self._add_result('version_info', result_name, result)
                            results[str_entry[0]] = value[:255]
                elif hasattr(entry, 'Var'):
                    for var_entry in entry.Var:
                        if hasattr(var_entry, 'entry'):
                            for key in var_entry.entry.keys():
                                try:
                                    value = var_entry.entry[key].encode('ascii')
                                    # result = {
                                    #     'key': key,
                                    #     'value': value,
                                    # }
                                except Exception as e:
                                    # TODO: log exception
                                    value = var_entry.entry[key].encode('ascii', errors='ignore')
                                    # raw = binascii.hexlify(var_entry.entry[key])
                                    # result = {
                                    #     'key': key,
                                    #     'value': value,
                                    #     'raw': raw,
                                    # }
                                # result_name = key + ': ' + value
                                # self._add_result('version_var', result_name, result)
                                results[key] = value
        except Exception as e:
            pass
            # self._parse_error("version info", e)
        return results


def _get_tls_info(pe):
    results = {}
    # self._info("TLS callback table listed at 0x%08x" % pe.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks)
    callback_array_rva = pe.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks - pe.OPTIONAL_HEADER.ImageBase

    # read the array of TLS callbacks until we hit a NULL ptr (end of array)
    idx = 0
    callback_functions = []
    while pe.get_dword_from_data(pe.get_data(callback_array_rva + 4 * idx, 4), 0):
        callback_functions.append(pe.get_dword_from_data(pe.get_data(callback_array_rva + 4 * idx, 4), 0))
        idx += 1

    # if we start with a NULL ptr, then there are no callback functions
    if idx == 0:
        return None
        # self._info("No TLS callback functions supported")
    else:
        for idx, va in enumerate(callback_functions):
            va_string = "0x%08x" % va
            # self._info("TLS callback function at %s" % va_string)
            # data = {'Callback Function': idx}
            # self._add_result('tls_callback', va_string, data)
            results[va_string] = idx
    return results
