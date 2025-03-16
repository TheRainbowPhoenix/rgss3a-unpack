import os
import sys
import struct
import re
from io import BytesIO

__VERSION__ = "1.0.0"

# Errors
E_INVALIDHDR = "Input file header mismatch."
E_INVALIDVER = "Not supported version (must be 1-3)."
E_INVALIDMGC = "Magic number read failed."

def advance_magic(magic):
    old = magic
    magic = (magic * 7 + 3) & 0xFFFFFFFF
    return old, magic

def ru32(stream):
    data = stream.read(4)
    if len(data) < 4:
        return None
    return struct.unpack('<I', data)[0]

def wu32(stream, data):
    stream.write(struct.pack('<I', data))

def read_until_full(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)

class EntryData:
    def __init__(self, offset=0, magic=0, size=0):
        self.offset = offset
        self.magic = magic
        self.size = size

class Coder:
    def __init__(self):
        self.buf = bytearray(8192)

    def copy(self, stream_in, stream_out, data):
        stream_in.seek(data.offset)
        magic = data.magic
        remaining = data.size

        while remaining > 0:
            chunk_size = min(len(self.buf), remaining)
            chunk = bytearray(read_until_full(stream_in, chunk_size))
            if not chunk:
                break

            # Process aligned u32 chunks
            aligned_size = (len(chunk) // 4) * 4
            for i in range(0, aligned_size, 4):
                old_magic, magic = advance_magic(magic)
                val = struct.unpack('<I', chunk[i:i+4])[0]
                val ^= old_magic
                chunk[i:i+4] = struct.pack('<I', val)

            # Process remaining bytes
            for i in range(aligned_size, len(chunk)):
                chunk[i] ^= (magic >> ((i % 4) * 8)) & 0xFF

            stream_out.write(chunk)
            remaining -= len(chunk)

class Entry:
    def __init__(self, name, data):
        self.name = name
        self.data = data

class RGSSArchive:
    def __init__(self, magic, version, entries, stream):
        self.magic = magic
        self.version = version
        self.entries = entries
        self.stream = stream

    def close(self):
        if self.stream and not self.stream.closed:
            self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @classmethod
    def create(cls, location, version):
        if version < 1 or version > 3:
            raise ValueError(E_INVALIDVER)
        
        stream = open(location, 'wb+')
        stream.write(b'RGSSAD\x00' + bytes([version]))
        magic = 0 if version == 3 else 0xDEADCAFE
        return cls(magic, version, [], stream)

    @classmethod
    def open(cls, location):
        stream = open(location, 'rb')
        try:
            header = stream.read(8)
            if header[:6] != b'RGSSAD':
                raise ValueError(E_INVALIDHDR)
            
            version = header[7]
            stream.seek(0)
            if version in (1, 2):
                return cls.open_rgssad(stream, version)
            elif version == 3:
                return cls.open_rgss3a(stream, version)
            else:
                raise ValueError(E_INVALIDVER)
        except Exception:
            stream.close()
            raise

    @classmethod
    def open_rgssad(cls, stream, version):
        magic = 0xDEADCAFE
        entries = []
        stream.seek(8)

        while True:
            name_len = ru32(stream)
            if name_len is None:
                break
            name_len ^= advance_magic(magic)[0]

            name = bytearray()
            for _ in range(name_len):
                name_byte = stream.read(1)[0]
                name_byte ^= advance_magic(magic)[0] & 0xFF
                name.append(name_byte)
            
            name = name.replace(b'\\', b'/').decode('utf-8', 'ignore')
            size = ru32(stream)
            if size is None:
                break
            size ^= advance_magic(magic)[0]

            offset = stream.tell()
            stream.seek(size, 1)
            entries.append(Entry(name, EntryData(offset, magic, size)))

        stream.seek(0)
        return cls(magic, version, entries, stream)

    @classmethod
    def open_rgss3a(cls, stream, version):
        stream.seek(8)
        magic = ru32(stream)
        if magic is None:
            raise ValueError(E_INVALIDMGC)
        magic = (magic * 9 + 3) & 0xFFFFFFFF
        entries = []

        while True:
            offset = ru32(stream)
            if offset is None:
                break
            offset ^= magic
            
            if offset == 0:
                break

            size = ru32(stream) ^ magic
            start_magic = ru32(stream) ^ magic
            name_len = ru32(stream) ^ magic

            name = bytearray()
            for i in range(name_len):
                name_byte = stream.read(1)[0]
                name_byte ^= (magic >> ((i % 4) * 8)) & 0xFF
                name.append(name_byte)
            
            name = name.replace(b'\\', b'/').decode('utf-8', 'ignore')
            entries.append(Entry(name, EntryData(offset, start_magic, size)))

        stream.seek(0)
        return cls(magic, version, entries, stream)

    def write_entries(self, root):
        if self.version in (1, 2):
            self.write_entries_rgssad(root)
        elif self.version == 3:
            self.write_entries_rgss3a(root)
        else:
            raise ValueError(E_INVALIDVER)

    def write_entries_rgssad(self, root):
        coder = Coder()
        for entry in self.entries:
            print(f"Packing: {entry.name}")
            name = entry.name.replace('/', '\\').encode('utf-8')
            name_len = len(name)
            wu32(self.stream, name_len ^ advance_magic(self.magic)[0])

            encrypted_name = bytearray(name)
            for i in range(len(encrypted_name)):
                encrypted_name[i] ^= advance_magic(self.magic)[0] & 0xFF
            self.stream.write(encrypted_name)

            size = entry.data.size ^ advance_magic(self.magic)[0]
            wu32(self.stream, size)

            with open(os.path.join(root, entry.name), 'rb') as f:
                coder.copy(f, self.stream, EntryData(0, self.magic, entry.data.size))

    def write_entries_rgss3a(self, root):
        # Calculate entry metadata
        off = 8 + 4  # Header + Magic
        for entry in self.entries:
            off += 16 + len(entry.name)
        off += 4

        # Update entry offsets and magic
        for entry in self.entries:
            entry.data.offset = off
            off += entry.data.size
            entry.data.magic = 0xDEADCAFE

        # Write metadata
        wu32(self.stream, self.magic)
        self.magic = (self.magic * 9 + 3) & 0xFFFFFFFF

        for entry in self.entries:
            wu32(self.stream, entry.data.offset ^ self.magic)
            wu32(self.stream, entry.data.size ^ self.magic)
            wu32(self.stream, entry.data.magic ^ self.magic)
            wu32(self.stream, len(entry.name) ^ self.magic)

            encrypted_name = bytearray(entry.name.replace('/', '\\').encode('utf-8'))
            for i in range(len(encrypted_name)):
                encrypted_name[i] ^= (self.magic >> ((i % 4) * 8)) & 0xFF
            self.stream.write(encrypted_name)

        wu32(self.stream, 0 ^ self.magic)

        # Write file data
        coder = Coder()
        for entry in self.entries:
            print(f"Packing: {entry.name}")
            with open(os.path.join(root, entry.name), 'rb') as f:
                coder.copy(f, self.stream, EntryData(0, entry.data.magic, entry.data.size))

def usage():
    print("""Extract rgssad/rgss2a/rgss3a files.
Commands:
    help
    version
    list        <archive>
    unpack      <archive> <folder> [<filter>]
    pack        <folder> <archive> [<version>]""")

def list_archive(archive):
    for entry in archive.entries:
        print(f"{entry.name}: EntryData(size={entry.data.size}, offset={entry.data.offset}, magic={entry.data.magic})")

def pack(src, out, version):
    def collect_files(root):
        entries = []
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root).replace('\\', '/')
                size = os.path.getsize(full_path)
                entries.append(Entry(rel_path, EntryData(size=size)))
        return entries

    if not os.path.isdir(src):
        print("FAILED: source is not a directory.")
        return

    try:
        archive = RGSSArchive.create(out, version)
    except Exception as e:
        print(f"FAILED: unable to create output file. {e}")
        return

    archive.entries = collect_files(src)
    try:
        archive.write_entries(src)
    except Exception as e:
        print(f"FAILED: unable to write archive. {e}")

def unpack(archive, dir, filter_pattern):
    os.makedirs(dir, exist_ok=True)
    try:
        pattern = re.compile(filter_pattern)
    except re.error:
        print(f"FAILED: Invalid regex filter: {filter_pattern}")
        return

    coder = Coder()
    for entry in archive.entries:
        if not pattern.search(entry.name):
            continue

        print(f"Extracting: {entry.name}")
        path = os.path.join(dir, entry.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'wb') as f:
            # Ensure stream is at correct position for each entry
            archive.stream.seek(entry.data.offset)
            coder.copy(archive.stream, f, entry.data)

def main():
    args = sys.argv
    # args = [
    #     "", "unpack", "Game.rgss3a", "OUT"
    # ]

    if len(args) < 2:
        usage()
        return

    
    cmd = args[1]

    if cmd == "help":
        usage()
    elif cmd == "version":
        print(f"version: {__VERSION__}")
    elif cmd == "list":
        archive = RGSSArchive.open(args[2])
        list_archive(archive)
    elif cmd == "unpack":
        archive = RGSSArchive.open(args[2])
        filter_pattern = args[4] if len(args) > 4 else '.*'
        unpack(archive, args[3], filter_pattern)
    elif cmd == "pack":
        version = 1
        if len(args) > 4:
            try:
                version = int(args[4])
            except ValueError:
                print(E_INVALIDVER)
                return
        pack(args[2], args[3], version)
    else:
        usage()

if __name__ == "__main__":
    main()