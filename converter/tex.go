package main

import (
	"bytes"
	"encoding/binary"
	"image"
	"image/draw"
	_ "image/png"
	"os"
)

// LoadRGBA decodes a PNG and box-filters it down until neither side exceeds maxSide.
func LoadRGBA(path string, maxSide int) (*image.RGBA, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	src, _, err := image.Decode(f)
	if err != nil {
		return nil, err
	}
	b := src.Bounds()
	img := image.NewRGBA(image.Rect(0, 0, b.Dx(), b.Dy()))
	draw.Draw(img, img.Bounds(), src, b.Min, draw.Src)
	for img.Bounds().Dx() > maxSide || img.Bounds().Dy() > maxSide {
		img = halve(img)
	}
	return img, nil
}

func halve(src *image.RGBA) *image.RGBA {
	w, h := src.Bounds().Dx(), src.Bounds().Dy()
	nw, nh := max(w/2, 1), max(h/2, 1)
	dst := image.NewRGBA(image.Rect(0, 0, nw, nh))
	for y := 0; y < nh; y++ {
		for x := 0; x < nw; x++ {
			var s [4]int
			for dy := 0; dy < 2; dy++ {
				for dx := 0; dx < 2; dx++ {
					sx, sy := min(x*2+dx, w-1), min(y*2+dy, h-1)
					o := src.PixOffset(sx, sy)
					for c := 0; c < 4; c++ {
						s[c] += int(src.Pix[o+c])
					}
				}
			}
			o := dst.PixOffset(x, y)
			for c := 0; c < 4; c++ {
				dst.Pix[o+c] = uint8((s[c] + 2) / 4)
			}
		}
	}
	return dst
}

func to565(r, g, b int) uint16 { return uint16((r>>3)<<11 | (g>>2)<<5 | (b >> 3)) }
func from565(c uint16) (int, int, int) {
	r, g, b := int(c>>11)&31, int(c>>5)&63, int(c)&31
	return r<<3 | r>>2, g<<2 | g>>4, b<<3 | b>>2
}

// dxt1Block encodes one 4x4 block (opaque DXT1) using the colour bounding box as endpoints.
func dxt1Block(px *[16][3]int, out []byte) {
	lo, hi := [3]int{255, 255, 255}, [3]int{0, 0, 0}
	for i := 0; i < 16; i++ {
		for c := 0; c < 3; c++ {
			lo[c] = min(lo[c], px[i][c])
			hi[c] = max(hi[c], px[i][c])
		}
	}
	// inset slightly, as the classic range-fit encoders do
	for c := 0; c < 3; c++ {
		in := (hi[c] - lo[c]) >> 4
		lo[c] = min(lo[c]+in, 255)
		hi[c] = max(hi[c]-in, 0)
	}
	c0, c1 := to565(hi[0], hi[1], hi[2]), to565(lo[0], lo[1], lo[2])
	if c0 < c1 {
		c0, c1 = c1, c0
	}
	var idx uint32
	if c0 != c1 {
		var pal [4][3]int
		pal[0][0], pal[0][1], pal[0][2] = from565(c0)
		pal[1][0], pal[1][1], pal[1][2] = from565(c1)
		for c := 0; c < 3; c++ {
			pal[2][c] = (2*pal[0][c] + pal[1][c]) / 3
			pal[3][c] = (pal[0][c] + 2*pal[1][c]) / 3
		}
		for i := 0; i < 16; i++ {
			best, bd := 0, 1<<30
			for k := 0; k < 4; k++ {
				d := 0
				for c := 0; c < 3; c++ {
					e := px[i][c] - pal[k][c]
					d += e * e
				}
				if d < bd {
					bd, best = d, k
				}
			}
			idx |= uint32(best) << (2 * i)
		}
	}
	binary.LittleEndian.PutUint16(out[0:], c0)
	binary.LittleEndian.PutUint16(out[2:], c1)
	binary.LittleEndian.PutUint32(out[4:], idx)
}

// WriteDDS writes img as a DXT1 DDS with a full mip chain, the format Warband's Textures folder expects.
func WriteDDS(path string, img *image.RGBA) error {
	w, h := img.Bounds().Dx(), img.Bounds().Dy()
	var levels [][]byte
	cur := img
	for {
		cw, ch := cur.Bounds().Dx(), cur.Bounds().Dy()
		bw, bh := (cw+3)/4, (ch+3)/4
		data := make([]byte, bw*bh*8)
		var px [16][3]int
		for by := 0; by < bh; by++ {
			for bx := 0; bx < bw; bx++ {
				for i := 0; i < 16; i++ {
					x, y := min(bx*4+i%4, cw-1), min(by*4+i/4, ch-1)
					o := cur.PixOffset(x, y)
					px[i] = [3]int{int(cur.Pix[o]), int(cur.Pix[o+1]), int(cur.Pix[o+2])}
				}
				dxt1Block(&px, data[(by*bw+bx)*8:])
			}
		}
		levels = append(levels, data)
		if cw == 1 && ch == 1 {
			break
		}
		cur = halve(cur)
	}
	var b bytes.Buffer
	b.WriteString("DDS ")
	hdr := make([]uint32, 31)
	hdr[0] = 124
	hdr[1] = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000 // caps, height, width, pixelformat, mipmapcount, linearsize
	hdr[2] = uint32(h)
	hdr[3] = uint32(w)
	hdr[4] = uint32(len(levels[0]))
	hdr[6] = uint32(len(levels))
	hdr[18] = 32                      // pixel format size
	hdr[19] = 0x4                     // fourcc
	hdr[20] = 0x31545844              // "DXT1"
	hdr[26] = 0x1000 | 0x8 | 0x400000 // texture, complex, mipmap
	binary.Write(&b, binary.LittleEndian, hdr)
	for _, l := range levels {
		b.Write(l)
	}
	return os.WriteFile(path, b.Bytes(), 0o644)
}
