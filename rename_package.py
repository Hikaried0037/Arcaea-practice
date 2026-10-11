"""Rename this APK's application ID without rebuilding its resource IDs."""
import re
import struct

ORIGINAL_PACKAGE = 'moe.inf.arc'


def validate_package(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', name):
        raise ValueError('Invalid Android package name: ' + name)
    if len(name.encode('utf-16-le')) > 254:
        raise ValueError('Package name is too long')


def _length(data, offset, utf8):
    if utf8:
        first = data[offset]
        if first & 0x80:
            return ((first & 0x7f) << 8) | data[offset + 1], offset + 2
        return first, offset + 1
    first, = struct.unpack_from('<H', data, offset)
    if first & 0x8000:
        second, = struct.unpack_from('<H', data, offset + 2)
        return ((first & 0x7fff) << 16) | second, offset + 4
    return first, offset + 2


def _encode_length(n, utf8):
    if utf8:
        if n > 0x7fff:
            raise ValueError('UTF-8 string exceeds Android string-pool limit')
        return bytes((n,)) if n < 0x80 else bytes((0x80 | (n >> 8), n & 0xff))
    return struct.pack('<H', n) if n < 0x8000 else struct.pack('<HH', 0x8000 | (n >> 16), n & 0xffff)


def _rename_pool(chunk, old, new):
    kind, header_size, size = struct.unpack_from('<HHI', chunk)
    assert kind == 1 and header_size >= 28 and size == len(chunk)
    count, style_count, flags, strings_start, styles_start = struct.unpack_from('<5I', chunk, 8)
    utf8 = bool(flags & 0x100)
    offsets, payload, changes = [], bytearray(), []
    for i in range(count):
        offset, = struct.unpack_from('<I', chunk, header_size + i * 4)
        pos = strings_start + offset
        char_len, pos = _length(chunk, pos, utf8)
        if utf8:
            byte_len, pos = _length(chunk, pos, True)
            value = chunk[pos:pos + byte_len].decode('utf-8')
        else:
            value = chunk[pos:pos + char_len * 2].decode('utf-16-le')
        updated = new + value[len(old):] if value == old or value.startswith(old + '.') else value
        if updated != value:
            changes.append((value, updated))
        offsets.append(len(payload))
        n = len(updated.encode('utf-16-le')) // 2
        if utf8:
            encoded = updated.encode('utf-8')
            payload.extend(_encode_length(n, True) + _encode_length(len(encoded), True) + encoded + b'\0')
        else:
            payload.extend(_encode_length(n, False) + updated.encode('utf-16-le') + b'\0\0')
    payload.extend(b'\0' * (-len(payload) % 4))
    style_offsets = chunk[header_size + count * 4:header_size + (count + style_count) * 4]
    styles = chunk[styles_start:] if styles_start else b''
    strings_start = header_size + (count + style_count) * 4
    new_styles_start = strings_start + len(payload) if styles_start else 0
    header = bytearray(chunk[:header_size])
    struct.pack_into('<I', header, 4, strings_start + len(payload) + len(styles))
    struct.pack_into('<5I', header, 8, count, style_count, flags & ~1, strings_start, new_styles_start)
    return bytes(header) + struct.pack('<' + 'I' * count, *offsets) + style_offsets + payload + styles, changes


def rename_manifest(data, new, old=ORIGINAL_PACKAGE):
    validate_package(new)
    kind, header_size, size = struct.unpack_from('<HHI', data)
    if kind != 3 or size != len(data):
        raise ValueError('Expected a binary Android manifest')
    out, pos, changes = bytearray(data[:header_size]), header_size, []
    while pos < size:
        child_kind, _, child_size = struct.unpack_from('<HHI', data, pos)
        if child_size < 8 or pos + child_size > size:
            raise ValueError('Invalid manifest chunk')
        chunk = data[pos:pos + child_size]
        if child_kind == 1:
            chunk, changed = _rename_pool(chunk, old, new)
            changes.extend(changed)
        out.extend(chunk)
        pos += child_size
    if (old, new) not in changes and old != new:
        raise ValueError('Original manifest package not found')
    struct.pack_into('<I', out, 4, len(out))
    return bytes(out), changes


def rename_resources(data, new, old=ORIGINAL_PACKAGE):
    validate_package(new)
    kind, header_size, size = struct.unpack_from('<HHI', data)
    if kind != 2 or size != len(data):
        raise ValueError('Expected an Android resource table')
    out, pos, changed = bytearray(data), header_size, 0
    while pos < size:
        child_kind, child_header_size, child_size = struct.unpack_from('<HHI', data, pos)
        if child_size < 8 or pos + child_size > size:
            raise ValueError('Invalid resource-table chunk')
        if child_kind == 0x200:
            if child_header_size < 268:
                raise ValueError('Invalid resource-package header')
            name = data[pos + 12:pos + 268].decode('utf-16-le').split('\0', 1)[0]
            if name == old:
                out[pos + 12:pos + 268] = new.encode('utf-16-le').ljust(256, b'\0')
                changed += 1
        pos += child_size
    if not changed and old != new:
        raise ValueError('Original resource package not found')
    return bytes(out), changed
