#!/bin/bash
# =============================================================
# Killshot Installer
# Downloads all offensive tools and sets up the avbypass toolkit
# for offline use. Run once with internet, then deploy anywhere.
#
# Usage:
#   ./install.sh              # Full install (tools + Go + donut)
#   ./install.sh --tools-only # Only download tool binaries
#   ./install.sh --update     # Re-download tools (latest versions)
#   ./install.sh --check      # Verify all tools are present
# =============================================================

# No set -e: individual download failures are handled gracefully

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR="$(mktemp -d)"

# ─── Detect environment ─────────────────────────────────────
# Exegol:  /.exegol-skel exists or EXEGOL_NAME is set
# Kali:    /etc/os-release contains "Kali"
# Other:   generic Linux

PLATFORM="unknown"
if [ -d "/.exegol" ] || [ -f "/opt/.exegol_version" ] || echo "${HOSTNAME:-}" | grep -q "^exegol-"; then
    PLATFORM="exegol"
elif grep -qi "kali" /etc/os-release 2>/dev/null; then
    PLATFORM="kali"
else
    PLATFORM="linux"
fi

# Set paths based on platform
if [ "$PLATFORM" = "exegol" ]; then
    # Exegol: tools live inside the avbypass tree (portable with my-resources)
    TOOLS_DIR="$SCRIPT_DIR/tools"
    GO_DIR="$SCRIPT_DIR/go"
elif [ "$PLATFORM" = "kali" ] || [ "$PLATFORM" = "linux" ]; then
    # Kali / bare Linux: tools go to /opt for system-wide access
    TOOLS_DIR="/opt/killshot/tools"
    GO_DIR="/opt/killshot/go"
    OUTPUT_DIR="/opt/killshot/output"
    # Ensure we can write to /opt
    if [ ! -w "/opt/killshot" ] 2>/dev/null; then
        if command -v sudo &>/dev/null; then
            sudo mkdir -p /opt/killshot
            sudo chown "$(id -u):$(id -g)" /opt/killshot
        else
            echo "[!] Cannot write to /opt — run as root or with sudo"
            exit 1
        fi
    fi
    mkdir -p "$OUTPUT_DIR" 2>/dev/null || true
fi

POTATOES_DIR="$TOOLS_DIR/potatoes"
WINDOWS_DIR="$TOOLS_DIR/windows"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

trap 'rm -rf "$TEMP_DIR"' EXIT

# ─── Helpers ─────────────────────────────────────────────────

ok()   { echo -e "  ${GREEN}[+]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[!]${NC} $1"; }
fail() { echo -e "  ${RED}[-]${NC} $1"; }
info() { echo -e "  ${BLUE}[*]${NC} $1"; }

download() {
    local url="$1" dest="$2" desc="$3"
    if [ -f "$dest" ] && [ "$UPDATE" != "1" ]; then
        ok "$desc (cached)"
        return 0
    fi
    info "Downloading $desc..."
    if curl -sL --fail -o "$dest" "$url" 2>/dev/null; then
        # Verify it's not HTML (failed download) and not empty
        if [ ! -s "$dest" ]; then
            fail "$desc (empty file)"
            rm -f "$dest"
            return 1
        fi
        # Check for HTML error pages (but allow legitimate text files like .ps1)
        if echo "$dest" | grep -qvE '\.(ps1|txt|cs|py|sh)$'; then
            if file "$dest" | grep -qE "HTML|ASCII text"; then
                fail "$desc (got HTML/text, bad URL)"
                rm -f "$dest"
                return 1
            fi
        fi
        local size=$(du -h "$dest" | cut -f1)
        ok "$desc ($size)"
        return 0
    else
        fail "$desc (download failed)"
        return 1
    fi
}

download_zip() {
    local url="$1" dest="$2" inner="$3" desc="$4"
    if [ -f "$dest" ] && [ "$UPDATE" != "1" ]; then
        ok "$desc (cached)"
        return 0
    fi
    info "Downloading $desc..."
    local zip="$TEMP_DIR/$(basename "$url")"
    if curl -sL --fail -o "$zip" "$url" 2>/dev/null; then
        if [ -n "$inner" ]; then
            unzip -jo "$zip" "$inner" -d "$(dirname "$dest")" > /dev/null 2>&1
            # Rename if needed
            local extracted="$(dirname "$dest")/$(basename "$inner")"
            if [ "$extracted" != "$dest" ] && [ -f "$extracted" ]; then
                mv "$extracted" "$dest"
            fi
        else
            unzip -jo "$zip" -d "$(dirname "$dest")" > /dev/null 2>&1
        fi
        if [ -s "$dest" ]; then
            local size=$(du -h "$dest" | cut -f1)
            ok "$desc ($size)"
            rm -f "$zip"
            return 0
        else
            fail "$desc (extraction failed - expected $dest)"
            rm -f "$zip" "$dest"
            return 1
        fi
    else
        fail "$desc (download failed)"
        return 1
    fi
}

get_latest_release() {
    local repo="$1"
    curl -sL "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null | \
        grep '"tag_name"' | head -1 | sed 's/.*: "\(.*\)".*/\1/'
}

# ─── Parse args ──────────────────────────────────────────────

TOOLS_ONLY=0
UPDATE=0
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tools-only) TOOLS_ONLY=1; shift;;
        --update)     UPDATE=1; shift;;
        --check)      CHECK_ONLY=1; shift;;
        --help|-h)
            echo ""
            echo "  Killshot Installer"
            echo "  Downloads all offensive tools, installs compilers, and sets up"
            echo "  the toolkit for offline use. Run once with internet access."
            echo ""
            echo "  USAGE"
            echo "    ./install.sh                Full install (tools + Go + Donut + garble)"
            echo "    ./install.sh --update       Re-download tools & update compilers to latest"
            echo "    ./install.sh --tools-only   Only download tool binaries (skip compilers)"
            echo "    ./install.sh --check        Verify all tools & compilers are present"
            echo ""
            echo "  WHAT IT INSTALLS"
            echo "    Tools:      25+ offensive Windows binaries (potatoes, SharpCollection, quick wins, etc.)"
            echo "    Go:         Cross-compiler for runner.exe (>= 1.24, latest stable)"
            echo "    Donut:      PE-to-shellcode converter (pip package)"
            echo "    Garble:     Go binary obfuscator (optional)"
            echo "    MinGW-w64:  Windows CGO cross-compiler (optional)"
            echo "    UPX:        Binary packer (optional)"
            echo ""
            echo "  TOOL SOURCES"
            echo "    SharpCollection: Rubeus, Certify, Seatbelt, SharpDPAPI, SharpUp,"
            echo "      SharpChrome, Whisker, KrbRelayUp, SharpGPOAbuse, ADSearch"
            echo "    GitHub Releases: GodPotato, PrintSpoofer, RunasCs, Snaffler, SQLRecon,"
            echo "      SharpHound, winPEAS, ligolo-ng, mimikatz, lazagne"
            echo "    Delivery: gen_hta.py (mshta), gen_xsl.py (wmic), gen_lnk.py (shortcut/ISO)"
            echo ""
            exit 0;;
        *) shift;;
    esac
done

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ${NC}Killshot Toolkit Installer${BLUE}           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ─── Check mode ──────────────────────────────────────────────

if [ "$CHECK_ONLY" = "1" ]; then
    echo -e "${BLUE}[*] Checking toolkit status...${NC}"
    echo ""
    echo "  Platform: $PLATFORM | Tools: $TOOLS_DIR"
    echo ""
    MISSING=0
    WARNINGS=0

    echo "  Generators:"
    for f in gen_runner.py gen_stager.py gen_potato.py gen_tool_stager.py killshot.py killshot.sh; do
        if [ -f "$SCRIPT_DIR/$f" ]; then
            ok "$f"
        else
            fail "$f MISSING"
            MISSING=$((MISSING+1))
        fi
    done

    echo ""
    echo "  Compilers & Dependencies:"

    # Python3
    PY3="$(which python3 2>/dev/null)"
    if [ -n "$PY3" ]; then
        ok "python3 $($PY3 --version 2>&1 | awk '{print $2}') ($PY3)"
    else
        fail "python3 NOT FOUND"
        MISSING=$((MISSING+1))
    fi

    # Go
    GO_FOUND=""
    for gp in "$GO_DIR/bin/go" "/opt/my-resources/bin/go/bin/go" "$(which go 2>/dev/null)"; do
        if [ -n "$gp" ] && [ -f "$gp" ]; then
            GO_VER=$("$gp" version 2>/dev/null | grep -oP 'go\K[0-9]+\.[0-9]+(\.[0-9]+)?')
            GO_MAJOR=$(echo "$GO_VER" | cut -d. -f1-2)
            if python3 -c "exit(0 if tuple(map(int,'$GO_MAJOR'.split('.'))) >= (1,24) else 1)" 2>/dev/null; then
                ok "go $GO_VER ($gp)"
                GO_FOUND=1
            else
                warn "go $GO_VER ($gp) — too old, need >= 1.24"
                WARNINGS=$((WARNINGS+1))
            fi
            break
        fi
    done
    [ -z "$GO_FOUND" ] && { fail "Go NOT FOUND (need >= 1.24)"; MISSING=$((MISSING+1)); }

    # Garble
    GARBLE_FOUND=""
    for gp in "$GO_DIR/bin/garble" "$HOME/go/bin/garble" "$(which garble 2>/dev/null)"; do
        if [ -n "$gp" ] && [ -f "$gp" ]; then
            ok "garble ($gp)"
            GARBLE_FOUND=1
            break
        fi
    done
    [ -z "$GARBLE_FOUND" ] && { warn "garble not found (optional — binary obfuscation)"; WARNINGS=$((WARNINGS+1)); }

    # Donut
    DONUT_OK=0
    for p in "/opt/tools/Empire/venv/bin/python3" "$(which python3 2>/dev/null)"; do
        if [ -f "$p" ] && "$p" -c "import donut" 2>/dev/null; then
            DONUT_VER=$("$p" -c "import donut; print(donut.__version__)" 2>/dev/null || echo "?")
            ok "donut $DONUT_VER ($p)"
            DONUT_OK=1
            break
        fi
    done
    [ "$DONUT_OK" = "0" ] && { fail "donut NOT FOUND"; MISSING=$((MISSING+1)); }

    # MinGW
    MINGW="$(which x86_64-w64-mingw32-gcc 2>/dev/null)"
    if [ -n "$MINGW" ]; then
        ok "mingw-w64 ($MINGW)"
    else
        info "mingw-w64 not found (optional — CGO cross-compile)"
    fi

    # UPX
    UPX="$(which upx 2>/dev/null)"
    if [ -n "$UPX" ]; then
        ok "upx ($($UPX --version 2>/dev/null | head -1 | awk '{print $2}'))"
    else
        info "upx not found (optional — binary packing)"
    fi

    # Mono
    MONO="$(which mcs 2>/dev/null)"
    if [ -n "$MONO" ]; then
        ok "mono/mcs ($MONO)"
    else
        info "mono not found (optional — .NET source compile)"
    fi

    echo ""
    echo "  Go module:"
    [ -f "$SCRIPT_DIR/go.mod" ] && ok "go.mod" || { fail "go.mod MISSING"; MISSING=$((MISSING+1)); }
    [ -f "$SCRIPT_DIR/go.sum" ] && ok "go.sum" || { fail "go.sum MISSING"; MISSING=$((MISSING+1)); }

    echo ""
    echo "  Potato exploits:"
    for f in GodPotato.exe PrintSpoofer.exe BadPotato.exe EfsPotato.exe; do
        found=0
        for d in "$POTATOES_DIR" "/opt/my-resources/tools/potatoes"; do
            [ -f "$d/$f" ] && { ok "$f ($d)"; found=1; break; }
        done
        [ "$found" = "0" ] && { warn "$f not found"; WARNINGS=$((WARNINGS+1)); }
    done

    echo ""
    echo "  Windows tools:"
    for f in Rubeus.exe SharpHound.exe Certify.exe Seatbelt.exe SharpDPAPI.exe SharpUp.exe \
             SharpChrome.exe winPEAS.exe Whisker.exe KrbRelayUp.exe SharpGPOAbuse.exe ADSearch.exe \
             RunasCs.exe Snaffler.exe SQLRecon.exe \
             ligolo-agent.exe mimikatz.exe lazagne.exe; do
        found=0
        for d in "$WINDOWS_DIR" "/opt/my-resources/tools/windows" "/opt/resources/windows/chisel"; do
            if [ -f "$d/$f" ] || [ -f "$d/chisel64.exe" -a "$f" = "chisel.exe" ]; then
                ok "$f ($d)"
                found=1
                break
            fi
        done
        [ "$found" = "0" ] && { warn "$f not found"; MISSING=$((MISSING+1)); }
    done

    echo ""
    if [ "$MISSING" -gt 0 ]; then
        fail "$MISSING required components missing. Run ./install.sh to fix."
    elif [ "$WARNINGS" -gt 0 ]; then
        warn "All required present, $WARNINGS optional items missing. Run ./install.sh --update to fix."
    else
        ok "All components present. Toolkit is ready for offline use."
    fi
    exit 0
fi

# ─── Step 1: Create directories ─────────────────────────────

echo -e "${BLUE}[1/6] Setting up directories...${NC}"
info "Platform detected: ${PLATFORM}"
info "Tools directory: ${TOOLS_DIR}"
mkdir -p "$TOOLS_DIR" "$POTATOES_DIR" "$WINDOWS_DIR"
ok "Directory structure created"

# ─── Step 2: Download tool binaries ──────────────────────────

echo ""
echo -e "${BLUE}[2/6] Downloading offensive tools...${NC}"
echo ""

TOTAL=0
SUCCESS=0

# --- Potato exploits ---
echo "  Potato Exploits:"

download \
    "https://github.com/BeichenDream/GodPotato/releases/latest/download/GodPotato-NET4.exe" \
    "$POTATOES_DIR/GodPotato.exe" "GodPotato" && SUCCESS=$((SUCCESS+1))
TOTAL=$((TOTAL+1))

download \
    "https://github.com/itm4n/PrintSpoofer/releases/latest/download/PrintSpoofer64.exe" \
    "$POTATOES_DIR/PrintSpoofer.exe" "PrintSpoofer" && SUCCESS=$((SUCCESS+1))
TOTAL=$((TOTAL+1))

# BadPotato - no precompiled binary available; try local copies, then SweetPotato as replacement
if [ -f "$POTATOES_DIR/BadPotato.exe" ] && [ "$UPDATE" != "1" ]; then
    ok "BadPotato (cached)"
    SUCCESS=$((SUCCESS+1))
else
    BADPOTATO_FOUND=""
    for src in "/opt/tools/Kraken/net_assemblies/bin/BadPotato-mod/BadPotato_net48_x64.exe" \
               "/opt/my-resources/tools/potatoes/BadPotato.exe"; do
        if [ -f "$src" ]; then
            cp "$src" "$POTATOES_DIR/BadPotato.exe"
            ok "BadPotato (copied from $src)"
            BADPOTATO_FOUND=1
            break
        fi
    done
    if [ -z "$BADPOTATO_FOUND" ]; then
        # Use SweetPotato as BadPotato replacement (same potato-family privesc)
        download \
            "https://github.com/Flangvik/SharpCollection/raw/master/NetFramework_4.7_Any/SweetPotato.exe" \
            "$POTATOES_DIR/BadPotato.exe" "BadPotato (via SweetPotato)" && BADPOTATO_FOUND=1
    fi
    [ -n "$BADPOTATO_FOUND" ] && SUCCESS=$((SUCCESS+1)) || warn "BadPotato not available"
fi
TOTAL=$((TOTAL+1))

# EfsPotato - no precompiled binary; try local copies, compile from source, or SweetPotato
if [ -f "$POTATOES_DIR/EfsPotato.exe" ] && [ "$UPDATE" != "1" ]; then
    ok "EfsPotato (cached)"
    SUCCESS=$((SUCCESS+1))
else
    EFSPOTATO_FOUND=""
    for src in "/opt/tools/Kraken/net_assemblies/bin/EfsPotato-mod/EfsPotato_net40_x64.exe" \
               "/opt/my-resources/tools/potatoes/EfsPotato.exe"; do
        if [ -f "$src" ]; then
            cp "$src" "$POTATOES_DIR/EfsPotato.exe"
            ok "EfsPotato (copied from $src)"
            EFSPOTATO_FOUND=1
            break
        fi
    done
    # Try compiling from source with mono
    if [ -z "$EFSPOTATO_FOUND" ] && command -v mcs &>/dev/null; then
        info "Compiling EfsPotato from source..."
        if curl -sL --fail -o "$TEMP_DIR/EfsPotato.cs" \
            "https://raw.githubusercontent.com/zcgonvh/EfsPotato/master/EfsPotato.cs" 2>/dev/null; then
            if mcs -out:"$POTATOES_DIR/EfsPotato.exe" "$TEMP_DIR/EfsPotato.cs" 2>/dev/null; then
                ok "EfsPotato (compiled from source)"
                EFSPOTATO_FOUND=1
            fi
        fi
    fi
    # Fallback: SweetPotato as EfsPotato replacement
    if [ -z "$EFSPOTATO_FOUND" ]; then
        download \
            "https://github.com/Flangvik/SharpCollection/raw/master/NetFramework_4.7_Any/SweetPotato.exe" \
            "$POTATOES_DIR/EfsPotato.exe" "EfsPotato (via SweetPotato)" && EFSPOTATO_FOUND=1
    fi
    [ -n "$EFSPOTATO_FOUND" ] && SUCCESS=$((SUCCESS+1)) || warn "EfsPotato not available"
fi
TOTAL=$((TOTAL+1))

echo ""
echo "  .NET Offensive Tools (SharpCollection):"

for tool in Rubeus Certify Seatbelt SharpDPAPI SharpUp SharpChrome Whisker KrbRelayUp \
            SharpGPOAbuse ADSearch; do
    download \
        "https://github.com/Flangvik/SharpCollection/raw/master/NetFramework_4.7_Any/${tool}.exe" \
        "$WINDOWS_DIR/${tool}.exe" "$tool" && SUCCESS=$((SUCCESS+1))
    TOTAL=$((TOTAL+1))
done

echo ""
echo "  Quick Win Tools (GitHub Releases):"

# RunasCs — runas with credentials, no interactive session needed
info "Resolving latest RunasCs..."
RC_TAG=$(get_latest_release "antonioCoco/RunasCs")
if [ -n "$RC_TAG" ]; then
    download_zip \
        "https://github.com/antonioCoco/RunasCs/releases/download/${RC_TAG}/RunasCs.zip" \
        "$WINDOWS_DIR/RunasCs.exe" "RunasCs.exe" "RunasCs $RC_TAG" && SUCCESS=$((SUCCESS+1))
else
    download \
        "https://github.com/antonioCoco/RunasCs/releases/latest/download/RunasCs.exe" \
        "$WINDOWS_DIR/RunasCs.exe" "RunasCs (latest)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

# Snaffler — credential/secret file hunting in SMB shares
info "Resolving latest Snaffler..."
SN_TAG=$(get_latest_release "SnaffCon/Snaffler")
if [ -n "$SN_TAG" ]; then
    download \
        "https://github.com/SnaffCon/Snaffler/releases/download/${SN_TAG}/Snaffler.exe" \
        "$WINDOWS_DIR/Snaffler.exe" "Snaffler $SN_TAG" && SUCCESS=$((SUCCESS+1))
else
    download \
        "https://github.com/SnaffCon/Snaffler/releases/latest/download/Snaffler.exe" \
        "$WINDOWS_DIR/Snaffler.exe" "Snaffler (latest)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

# SQLRecon — MSSQL enumeration
info "Resolving latest SQLRecon..."
SR_TAG=$(get_latest_release "skahwah/SQLRecon")
if [ -n "$SR_TAG" ]; then
    download \
        "https://github.com/skahwah/SQLRecon/releases/download/${SR_TAG}/SQLRecon.exe" \
        "$WINDOWS_DIR/SQLRecon.exe" "SQLRecon $SR_TAG" && SUCCESS=$((SUCCESS+1))
else
    download \
        "https://github.com/skahwah/SQLRecon/releases/latest/download/SQLRecon.exe" \
        "$WINDOWS_DIR/SQLRecon.exe" "SQLRecon (latest)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

echo ""
echo "  Tools with GitHub Releases:"

# SharpHound - latest release (zip)
info "Resolving latest SharpHound..."
SH_TAG=$(get_latest_release "SpecterOps/SharpHound")
if [ -n "$SH_TAG" ]; then
    download_zip \
        "https://github.com/SpecterOps/SharpHound/releases/download/${SH_TAG}/SharpHound_${SH_TAG}_windows_x86.zip" \
        "$WINDOWS_DIR/SharpHound.exe" "SharpHound.exe" "SharpHound $SH_TAG" && SUCCESS=$((SUCCESS+1))
else
    # Fallback to SharpCollection
    download \
        "https://github.com/Flangvik/SharpCollection/raw/master/NetFramework_4.7_Any/SharpHound.exe" \
        "$WINDOWS_DIR/SharpHound.exe" "SharpHound (SharpCollection)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

# winPEAS - latest release
info "Resolving latest winPEAS..."
WP_TAG=$(get_latest_release "peass-ng/PEASS-ng")
if [ -n "$WP_TAG" ]; then
    download \
        "https://github.com/peass-ng/PEASS-ng/releases/download/${WP_TAG}/winPEASx64.exe" \
        "$WINDOWS_DIR/winPEAS.exe" "winPEAS $WP_TAG" && SUCCESS=$((SUCCESS+1))
else
    download \
        "https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64.exe" \
        "$WINDOWS_DIR/winPEAS.exe" "winPEAS (latest)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

# ligolo-ng agent - latest release (zip)
info "Resolving latest ligolo-ng..."
LIG_TAG=$(get_latest_release "nicocha30/ligolo-ng")
if [ -n "$LIG_TAG" ]; then
    LIG_VER="${LIG_TAG#v}"
    download_zip \
        "https://github.com/nicocha30/ligolo-ng/releases/download/${LIG_TAG}/ligolo-ng_agent_${LIG_VER}_windows_amd64.zip" \
        "$WINDOWS_DIR/ligolo-agent.exe" "agent.exe" "ligolo-agent $LIG_TAG"
    # Rename if extracted as agent.exe
    [ -f "$WINDOWS_DIR/agent.exe" ] && [ ! -f "$WINDOWS_DIR/ligolo-agent.exe" ] && \
        mv "$WINDOWS_DIR/agent.exe" "$WINDOWS_DIR/ligolo-agent.exe"
    [ -f "$WINDOWS_DIR/ligolo-agent.exe" ] && SUCCESS=$((SUCCESS+1))
else
    warn "Could not resolve ligolo-ng latest release"
fi
TOTAL=$((TOTAL+1))

# chisel - latest release (zip for windows, gz for linux)
info "Resolving latest chisel..."
CH_TAG=$(get_latest_release "jpillora/chisel")
if [ -n "$CH_TAG" ]; then
    CH_VER="${CH_TAG#v}"
    # Try .zip first (Windows releases), then .gz
    download_zip \
        "https://github.com/jpillora/chisel/releases/download/${CH_TAG}/chisel_${CH_VER}_windows_amd64.zip" \
        "$WINDOWS_DIR/chisel.exe" "chisel.exe" "chisel $CH_TAG"
    if [ ! -s "$WINDOWS_DIR/chisel.exe" ]; then
        info "Trying .gz format..."
        curl -sL --fail \
            "https://github.com/jpillora/chisel/releases/download/${CH_TAG}/chisel_${CH_VER}_windows_amd64.gz" \
            -o "$TEMP_DIR/chisel.gz" 2>/dev/null
        if [ -s "$TEMP_DIR/chisel.gz" ]; then
            gunzip -c "$TEMP_DIR/chisel.gz" > "$WINDOWS_DIR/chisel.exe" 2>/dev/null
            chmod +x "$WINDOWS_DIR/chisel.exe" 2>/dev/null
        fi
    fi
    if [ -s "$WINDOWS_DIR/chisel.exe" ]; then
        ok "chisel $CH_TAG"
        SUCCESS=$((SUCCESS+1))
    else
        fail "chisel extraction failed"
        rm -f "$WINDOWS_DIR/chisel.exe"
    fi
else
    warn "Could not resolve chisel latest release"
fi
TOTAL=$((TOTAL+1))

# mimikatz - latest release (zip)
info "Resolving latest mimikatz..."
MK_TAG=$(get_latest_release "gentilkiwi/mimikatz")
if [ -n "$MK_TAG" ]; then
    download_zip \
        "https://github.com/gentilkiwi/mimikatz/releases/download/${MK_TAG}/mimikatz_trunk.zip" \
        "$WINDOWS_DIR/mimikatz.exe" "x64/mimikatz.exe" "mimikatz $MK_TAG" && SUCCESS=$((SUCCESS+1))
else
    download_zip \
        "https://github.com/gentilkiwi/mimikatz/releases/latest/download/mimikatz_trunk.zip" \
        "$WINDOWS_DIR/mimikatz.exe" "x64/mimikatz.exe" "mimikatz (latest)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

# lazagne - latest release (single exe)
info "Resolving latest LaZagne..."
LZ_TAG=$(get_latest_release "AlessandroZ/LaZagne")
if [ -n "$LZ_TAG" ]; then
    download \
        "https://github.com/AlessandroZ/LaZagne/releases/download/${LZ_TAG}/lazagne.exe" \
        "$WINDOWS_DIR/lazagne.exe" "lazagne $LZ_TAG" && SUCCESS=$((SUCCESS+1))
else
    download \
        "https://github.com/AlessandroZ/LaZagne/releases/latest/download/lazagne.exe" \
        "$WINDOWS_DIR/lazagne.exe" "lazagne (latest)" && SUCCESS=$((SUCCESS+1))
fi
TOTAL=$((TOTAL+1))

# Invoke-Mimikatz.ps1 - try Empire local copy first, then PowerSploit
MIMI_PS1=""
for src in "/opt/tools/Empire/empire/server/data/module_source/credentials/Invoke-Mimikatz.ps1" \
           "/opt/my-resources/avbypass/Invoke-Mimikatz.ps1"; do
    if [ -f "$src" ]; then
        cp "$src" "$WINDOWS_DIR/Invoke-Mimikatz.ps1"
        ok "Invoke-Mimikatz.ps1 (copied from $src)"
        MIMI_PS1=1
        break
    fi
done
if [ -z "$MIMI_PS1" ]; then
    download \
        "https://raw.githubusercontent.com/PowerShellMafia/PowerSploit/dev/Exfiltration/Invoke-Mimikatz.ps1" \
        "$WINDOWS_DIR/Invoke-Mimikatz.ps1" "Invoke-Mimikatz.ps1"
fi
[ -f "$WINDOWS_DIR/Invoke-Mimikatz.ps1" ] && SUCCESS=$((SUCCESS+1)) || warn "Invoke-Mimikatz.ps1 not available"
TOTAL=$((TOTAL+1))

echo ""
info "Tools: $SUCCESS/$TOTAL downloaded successfully"

if [ "$TOOLS_ONLY" = "1" ]; then
    echo ""
    ok "Tools-only install complete."
    echo ""
    exit 0
fi

# ─── Step 3: Compilers & Dependencies ────────────────────────

echo ""
echo -e "${BLUE}[3/6] Setting up compilers & dependencies...${NC}"
echo ""

# --- 3a. Python ---
echo "  Python:"
PYTHON3="$(which python3 2>/dev/null)"
if [ -n "$PYTHON3" ]; then
    PY_VER=$("$PYTHON3" --version 2>&1 | awk '{print $2}')
    ok "python3 $PY_VER ($PYTHON3)"
else
    fail "python3 not found - required for all generators"
fi

# --- 3b. Go toolchain ---
echo ""
echo "  Go (cross-compiler for runner.exe):"

GO_MIN_VERSION="1.24"
GO_WANT_VERSION=""  # Will be set to latest stable if we need to install

get_go_ver() {
    "$1" version 2>/dev/null | grep -oP 'go\K[0-9]+\.[0-9]+(\.[0-9]+)?'
}

check_go_min() {
    local ver=$(get_go_ver "$1")
    [ -n "$ver" ] && python3 -c "
v = '$ver'.split('.')
m = '$GO_MIN_VERSION'.split('.')
exit(0 if (int(v[0]),int(v[1])) >= (int(m[0]),int(m[1])) else 1)
" 2>/dev/null
}

resolve_latest_go() {
    # Get latest stable Go version, but cap at what garble supports.
    # Garble v0.15.0 supports up to Go 1.25.x — Go 1.26+ breaks it.
    local latest=$(curl -sL "https://go.dev/VERSION?m=text" 2>/dev/null | head -1)
    latest="${latest#go}"
    if [ -z "$latest" ]; then
        echo "1.25.3"
        return
    fi

    local major_minor=$(echo "$latest" | cut -d. -f1-2)
    # If latest Go is too new for garble, use latest 1.25.x instead
    if python3 -c "exit(0 if tuple(map(int,'$major_minor'.split('.'))) > (1,25) else 1)" 2>/dev/null; then
        # Fetch latest 1.25.x patch version
        local go125=$(curl -sL "https://go.dev/dl/?mode=json" 2>/dev/null | \
            python3 -c "import json,sys; vs=[r['version'] for r in json.load(sys.stdin) if r['version'].startswith('go1.25')]; print(vs[0].lstrip('go') if vs else '1.25.3')" 2>/dev/null)
        echo "${go125:-1.25.3}"
    else
        echo "$latest"
    fi
}

# Find best available Go
GO_BIN=""
GO_CURRENT_VER=""
for candidate in "$GO_DIR/bin/go" "/opt/my-resources/bin/go/bin/go" "$(which go 2>/dev/null)"; do
    if [ -n "$candidate" ] && [ -f "$candidate" ] && check_go_min "$candidate"; then
        GO_BIN="$candidate"
        GO_CURRENT_VER=$(get_go_ver "$candidate")
        break
    fi
done

NEED_GO_INSTALL=0
if [ -n "$GO_BIN" ]; then
    ok "Go $GO_CURRENT_VER ($GO_BIN)"
    export PATH="$(dirname "$GO_BIN"):$PATH"

    # Check if update available
    if [ "$UPDATE" = "1" ]; then
        GO_WANT_VERSION=$(resolve_latest_go)
        if [ -n "$GO_WANT_VERSION" ] && [ "$GO_CURRENT_VER" != "$GO_WANT_VERSION" ]; then
            info "Update available: $GO_CURRENT_VER -> $GO_WANT_VERSION"
            NEED_GO_INSTALL=1
        else
            ok "Go is up to date"
        fi
    fi
elif command -v go &>/dev/null; then
    warn "System Go $(get_go_ver "$(which go)") is too old (need >= $GO_MIN_VERSION)"
    NEED_GO_INSTALL=1
else
    warn "Go not found"
    NEED_GO_INSTALL=1
fi

if [ "$NEED_GO_INSTALL" = "1" ]; then
    [ -z "$GO_WANT_VERSION" ] && GO_WANT_VERSION=$(resolve_latest_go)
    info "Installing Go $GO_WANT_VERSION..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  GO_ARCH="amd64";;
        aarch64) GO_ARCH="arm64";;
        *)       GO_ARCH="amd64";;
    esac

    curl -sL "https://go.dev/dl/go${GO_WANT_VERSION}.linux-${GO_ARCH}.tar.gz" -o "$TEMP_DIR/go.tar.gz"
    if [ -f "$TEMP_DIR/go.tar.gz" ]; then
        rm -rf "$GO_DIR"
        mkdir -p "$GO_DIR"
        tar -xzf "$TEMP_DIR/go.tar.gz" -C "$GO_DIR" --strip-components=1
        export PATH="$GO_DIR/bin:$PATH"
        GO_BIN="$GO_DIR/bin/go"
        ok "Go $GO_WANT_VERSION installed to $GO_DIR"
    else
        fail "Go download failed"
    fi
fi

# Cache Go modules for offline use
if [ -n "$GO_BIN" ]; then
    info "Caching Go module dependencies..."
    cd "$SCRIPT_DIR"
    go mod download 2>/dev/null && ok "Go modules cached for offline use" || warn "Go module cache may be incomplete"
fi

# --- 3c. Garble (Go binary obfuscator) ---
echo ""
echo "  Garble (binary obfuscation):"
GARBLE_BIN=""
for gp in "$GO_DIR/bin/garble" "$HOME/go/bin/garble" "$(which garble 2>/dev/null)"; do
    if [ -n "$gp" ] && [ -f "$gp" ]; then
        GARBLE_BIN="$gp"
        break
    fi
done

if [ -n "$GARBLE_BIN" ] && [ "$UPDATE" != "1" ]; then
    GARBLE_VER=$("$GARBLE_BIN" version 2>/dev/null | head -1 || echo "unknown")
    ok "garble $GARBLE_VER"
else
    info "Installing/updating garble..."
    GARBLE_DEST="$GO_DIR/bin"
    [ ! -d "$GARBLE_DEST" ] && GARBLE_DEST="$HOME/go/bin"
    GOBIN="$GARBLE_DEST" go install mvdan.cc/garble@latest 2>/dev/null
    if [ -f "$GARBLE_DEST/garble" ]; then
        ok "garble installed to $GARBLE_DEST"
    else
        warn "garble install failed (may not support this Go version yet)"
    fi
fi

# --- 3d. mingw-w64 (optional, for CGO Windows cross-compile) ---
echo ""
echo "  MinGW-w64 (optional CGO cross-compiler):"
MINGW_CC="$(which x86_64-w64-mingw32-gcc 2>/dev/null)"
if [ -n "$MINGW_CC" ]; then
    MINGW_VER=$("$MINGW_CC" --version 2>/dev/null | head -1)
    ok "x86_64-w64-mingw32-gcc ($MINGW_VER)"
else
    info "Not found (optional - only needed for CGO builds)"
    # Try to install if apt is available
    if command -v apt-get &>/dev/null; then
        info "Installing mingw-w64..."
        apt-get update -qq 2>/dev/null && apt-get install -y -qq gcc-mingw-w64-x86-64 2>/dev/null && \
            ok "mingw-w64 installed" || warn "mingw-w64 install failed (optional)"
    fi
fi

# ─── Step 4: Donut (PE-to-shellcode) ────────────────────────

echo ""
echo -e "${BLUE}[4/6] Setting up Donut (PE-to-shellcode)...${NC}"

DONUT_OK=0
DONUT_PY=""
# Check if donut is already available
for p in "/opt/tools/Empire/venv/bin/python3" "$(which python3 2>/dev/null)"; do
    if [ -f "$p" ] && "$p" -c "import donut" 2>/dev/null; then
        DONUT_VER=$("$p" -c "import donut; print(donut.__version__)" 2>/dev/null || echo "unknown")
        ok "donut $DONUT_VER via $p"
        DONUT_OK=1
        DONUT_PY="$p"
        break
    fi
done

if [ "$DONUT_OK" = "0" ] || [ "$UPDATE" = "1" ]; then
    info "Installing/updating donut-shellcode..."
    # Try pip in various locations; --break-system-packages needed on Arch/CachyOS/Debian 12+
    for pip_cmd in "pip3" "pip" "$PYTHON3 -m pip"; do
        if $pip_cmd install --upgrade donut-shellcode 2>/dev/null; then
            ok "donut-shellcode installed/updated"
            DONUT_OK=1
            break
        elif $pip_cmd install --upgrade --break-system-packages donut-shellcode 2>/dev/null; then
            ok "donut-shellcode installed/updated (--break-system-packages)"
            DONUT_OK=1
            break
        fi
    done
    [ "$DONUT_OK" = "0" ] && warn "donut-shellcode install failed (install manually: pip install donut-shellcode --break-system-packages)"
fi

# ─── Step 5: NASM (optional, for raw shellcode work) ────────

echo ""
echo -e "${BLUE}[5/6] Checking optional tools...${NC}"

echo "  NASM (assembler):"
NASM_BIN="$(which nasm 2>/dev/null)"
if [ -n "$NASM_BIN" ]; then
    NASM_VER=$("$NASM_BIN" -v 2>/dev/null | awk '{print $3}')
    ok "nasm $NASM_VER"
else
    info "Not found (optional - only for custom shellcode)"
    if command -v apt-get &>/dev/null; then
        apt-get install -y -qq nasm 2>/dev/null && ok "nasm installed" || true
    fi
fi

echo "  UPX (binary packer):"
UPX_BIN="$(which upx 2>/dev/null)"
if [ -n "$UPX_BIN" ]; then
    UPX_VER=$("$UPX_BIN" --version 2>/dev/null | head -1 | awk '{print $2}')
    ok "upx $UPX_VER"
else
    info "Not found (optional - reduces binary size)"
    if command -v apt-get &>/dev/null; then
        apt-get install -y -qq upx-ucl 2>/dev/null && ok "upx installed" || true
    fi
fi

echo "  Mono (optional .NET cross-compiler):"
MONO_BIN="$(which mcs 2>/dev/null)"
if [ -n "$MONO_BIN" ]; then
    MONO_VER=$("$MONO_BIN" --version 2>/dev/null | head -1 | grep -oP 'version \K[0-9.]+')
    ok "mcs $MONO_VER"
else
    info "Not found (optional - for compiling .NET from source)"
fi

echo "  MSI builder (wixl or msibuild, for AppLocker bypass):"
WIXL_BIN="$(which wixl 2>/dev/null)"
MSIBUILD_BIN="$(which msibuild 2>/dev/null)"
if [ -n "$WIXL_BIN" ]; then
    ok "wixl ($(wixl --version 2>&1 | head -1))"
elif [ -n "$MSIBUILD_BIN" ]; then
    ok "msibuild ($MSIBUILD_BIN)"
else
    info "Not found — installing msitools from Debian..."
    MSI_TMP=$(mktemp -d)
    (
        cd "$MSI_TMP"
        curl -sL -O "http://ftp.debian.org/debian/pool/main/g/gcab/libgcab-1.0-0_1.6-1+b3_amd64.deb" \
            -O "http://ftp.debian.org/debian/pool/main/m/msitools/libmsi-1.0-0_0.106+repack-1_amd64.deb" \
            -O "http://ftp.debian.org/debian/pool/main/m/msitools/msitools_0.106+repack-1_amd64.deb" 2>/dev/null
        dpkg -i libgcab-1.0-0_*.deb libmsi-1.0-0_*.deb msitools_*.deb 2>/dev/null
    )
    rm -rf "$MSI_TMP"
    if command -v wixl &>/dev/null; then
        ok "wixl installed"
    elif command -v msibuild &>/dev/null; then
        ok "msibuild installed (MSI generation via IDT tables)"
    else
        warn "msitools install failed (MSI will fall back to DLL-only output)"
    fi
fi

# ─── Step 6: Verify & create symlinks ───────────────────────

echo ""
echo -e "${BLUE}[6/6] Finalizing installation...${NC}"

# Create symlinks from /opt/my-resources/tools if we're in exegol
if [ -d "/opt/my-resources" ] && [ "$SCRIPT_DIR" != "/opt/my-resources/avbypass" ]; then
    info "Creating symlinks to /opt/my-resources/tools..."
    mkdir -p /opt/my-resources/tools/potatoes /opt/my-resources/tools/windows

    for f in "$POTATOES_DIR"/*.exe; do
        [ -f "$f" ] && ln -sf "$f" "/opt/my-resources/tools/potatoes/$(basename "$f")" 2>/dev/null
    done
    for f in "$WINDOWS_DIR"/*.exe "$WINDOWS_DIR"/*.ps1; do
        [ -f "$f" ] && ln -sf "$f" "/opt/my-resources/tools/windows/$(basename "$f")" 2>/dev/null
    done
    ok "Symlinks created"
fi

# Make output dir writable by the real user (not root when run via sudo)
if [ "$PLATFORM" = "kali" ] || [ "$PLATFORM" = "linux" ]; then
    REAL_USER="${SUDO_USER:-$(id -un)}"
    if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
        chown -R "$REAL_USER:$REAL_USER" /opt/killshot/output 2>/dev/null || true
    fi
fi

# Make scripts executable
chmod +x "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.py 2>/dev/null

# Create killshot symlink in PATH
if [ ! -L "/usr/local/bin/killshot" ] || [ "$UPDATE" = "1" ]; then
    if [ -w "/usr/local/bin" ]; then
        ln -sf "$SCRIPT_DIR/killshot.sh" /usr/local/bin/killshot
        ok "killshot command available globally"
    elif command -v sudo &>/dev/null; then
        sudo ln -sf "$SCRIPT_DIR/killshot.sh" /usr/local/bin/killshot
        ok "killshot command available globally (via sudo)"
    else
        info "Add to PATH manually: ln -s $SCRIPT_DIR/killshot.sh /usr/local/bin/killshot"
    fi
fi

# Print summary
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ${GREEN}Installation Complete${BLUE}                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Directory: $SCRIPT_DIR"
echo ""
echo "  Toolkit components:"
echo "    killshot.sh         - One-command payload generation"
echo "    killshot.py       - Tool-to-shellcode converter"
echo "    gen_runner.py     - Polymorphic runner generator"
echo "    gen_stager.py     - PowerShell stager generator"
echo "    gen_potato.py     - Potato privesc generator"
echo "    gen_tool_stager.py - Tool loader generator"
echo "    install.sh        - This installer"
echo ""
echo "  Tool binaries: $TOOLS_DIR"
echo ""

# Count tools
POT_COUNT=$(ls -1 "$POTATOES_DIR"/*.exe 2>/dev/null | wc -l)
WIN_COUNT=$(ls -1 "$WINDOWS_DIR"/*.exe "$WINDOWS_DIR"/*.ps1 2>/dev/null | wc -l)
echo "    Potatoes:  $POT_COUNT"
echo "    Windows:   $WIN_COUNT"
echo ""

echo "  Quick start:"
echo "    killshot generate -l LHOST --all   # Generate everything"
echo "    killshot generate --runner         # Just runner.exe"
echo "    killshot generate --tool Certify   # Single tool"
echo "    killshot list                      # List available tools"
echo "    killshot check                     # Verify installation"
echo "    ./install.sh --update              # Update all tools"
echo ""
