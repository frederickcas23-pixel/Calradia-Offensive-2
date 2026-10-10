package main

import (
	"encoding/binary"
	"fmt"
	"os"
	"path/filepath"
)

// Warband draws its own crosshair from small pictures inside two shared interface textures. The module draws a
// CS2-style crosshair instead, so the player's own copies of those textures are copied into the module with just
// the crosshair pictures blanked. Rectangles are fractions of the texture: x0, y0, x1, y1 from the top-left corner.
var crosshairBlanks = map[string][][4]float64{
	"ui_gadgets.dds": {{0.03, 0.027, 0.209, 0.127}, {0.074, 0.118, 0.247, 0.319}, {0, 0.297, 0.175, 0.508}},
	"ui.dds":         {{0.845, 0.028, 0.897, 0.079}},
}

func blankCrosshair(game, texDir string) error {
	for name, rects := range crosshairBlanks {
		d, err := os.ReadFile(filepath.Join(game, "Textures", name))
		if err != nil {
			return fmt.Errorf("crosshair: %w", err)
		}
		if len(d) < 128 || string(d[:4]) != "DDS " {
			return fmt.Errorf("crosshair: %s is not a DDS file", name)
		}
		h, w := int(binary.LittleEndian.Uint32(d[12:])), int(binary.LittleEndian.Uint32(d[16:]))
		mips := max(int(binary.LittleEndian.Uint32(d[28:])), 1)
		var blk int
		switch string(d[84:88]) {
		case "DXT1":
			blk = 8
		case "DXT3", "DXT5":
			blk = 16
		default:
			return fmt.Errorf("crosshair: %s has an unexpected format %q", name, d[84:88])
		}
		off := 128
		for m := 0; m < mips && w >= 32 && h >= 32; m++ {
			bw, bh := (w+3)/4, (h+3)/4
			if off+bw*bh*blk > len(d) {
				break
			}
			for _, r := range rects {
				x0, y0 := int(r[0]*float64(w))/4, int(r[1]*float64(h))/4
				x1, y1 := min((int(r[2]*float64(w))+3)/4, bw-1), min((int(r[3]*float64(h))+3)/4, bh-1)
				for by := y0; by <= y1; by++ {
					for bx := x0; bx <= x1; bx++ {
						o := off + (by*bw+bx)*blk
						for i := 0; i < blk; i++ {
							d[o+i] = 0 // black and fully transparent; these pictures are drawn additively
						}
					}
				}
			}
			off += bw * bh * blk
			w, h = max(w/2, 1), max(h/2, 1)
		}
		if err := os.WriteFile(filepath.Join(texDir, name), d, 0o644); err != nil {
			return err
		}
	}
	return nil
}
