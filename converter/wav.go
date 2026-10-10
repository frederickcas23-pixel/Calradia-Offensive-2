package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
)

// ConvertWAV rewrites a PCM WAV as 16-bit mono (Warband positions mono sounds in 3D). Other encodings are copied unchanged.
func ConvertWAV(src, dst string) error {
	d, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	if len(d) < 44 || string(d[0:4]) != "RIFF" || string(d[8:12]) != "WAVE" {
		return fmt.Errorf("%s is not a WAV file", src)
	}
	var format, channels, bits uint16
	var rate uint32
	var pcm []byte
	for o := 12; o+8 <= len(d); {
		id := string(d[o : o+4])
		sz := int(binary.LittleEndian.Uint32(d[o+4:]))
		body := d[o+8 : min(o+8+sz, len(d))]
		switch id {
		case "fmt ":
			if len(body) < 16 {
				return fmt.Errorf("%s: short fmt chunk", src)
			}
			format = binary.LittleEndian.Uint16(body[0:])
			channels = binary.LittleEndian.Uint16(body[2:])
			rate = binary.LittleEndian.Uint32(body[4:])
			bits = binary.LittleEndian.Uint16(body[14:])
		case "data":
			pcm = body
		}
		o += 8 + sz + sz%2
	}
	if format != 1 || bits != 16 || channels == 0 || pcm == nil {
		return os.WriteFile(dst, d, 0o644)
	}
	frames := len(pcm) / (2 * int(channels))
	out := make([]byte, frames*2)
	for i := 0; i < frames; i++ {
		s := 0
		for c := 0; c < int(channels); c++ {
			s += int(int16(binary.LittleEndian.Uint16(pcm[(i*int(channels)+c)*2:])))
		}
		binary.LittleEndian.PutUint16(out[i*2:], uint16(int16(s/int(channels))))
	}
	var b bytes.Buffer
	b.WriteString("RIFF")
	binary.Write(&b, binary.LittleEndian, uint32(36+len(out)))
	b.WriteString("WAVEfmt ")
	binary.Write(&b, binary.LittleEndian, uint32(16))
	binary.Write(&b, binary.LittleEndian, uint16(1))
	binary.Write(&b, binary.LittleEndian, uint16(1))
	binary.Write(&b, binary.LittleEndian, rate)
	binary.Write(&b, binary.LittleEndian, rate*2)
	binary.Write(&b, binary.LittleEndian, uint16(2))
	binary.Write(&b, binary.LittleEndian, uint16(16))
	b.WriteString("data")
	binary.Write(&b, binary.LittleEndian, uint32(len(out)))
	b.Write(out)
	return os.WriteFile(dst, b.Bytes(), 0o644)
}
