package main

import (
	"encoding/binary"
	"fmt"
	"math"
	"os"
)

// WBSkeleton is Warband's skel_human rest pose in mesh space (X right, Y forward, Z up), read from the player's own CommonRes/skeletons.brf.
type WBSkeleton struct {
	Names  []string
	Parent []int
	Pos    []V3
	Rot    []M3 // columns are the bone's local axes in mesh space
}

type br struct {
	d []byte
	o int
}

func (r *br) i() (int, error) {
	if r.o+4 > len(r.d) {
		return 0, fmt.Errorf("unexpected end of BRF")
	}
	v := int(int32(binary.LittleEndian.Uint32(r.d[r.o:])))
	r.o += 4
	return v, nil
}
func (r *br) s() (string, error) {
	n, err := r.i()
	if err != nil || n < 0 || r.o+n > len(r.d) {
		return "", fmt.Errorf("bad string in BRF")
	}
	v := string(r.d[r.o : r.o+n])
	r.o += n
	return v, nil
}
func (r *br) v3() (V3, error) {
	if r.o+12 > len(r.d) {
		return V3{}, fmt.Errorf("unexpected end of BRF")
	}
	var v V3
	for k := 0; k < 3; k++ {
		v[k] = float64(math.Float32frombits(binary.LittleEndian.Uint32(r.d[r.o+4*k:])))
	}
	r.o += 12
	return v, nil
}

func LoadWBSkeleton(path string) (*WBSkeleton, error) {
	d, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	r := &br{d: d}
	for {
		tok, err := r.s()
		if err != nil {
			return nil, err
		}
		if tok == "rfver " {
			if _, err := r.i(); err != nil {
				return nil, err
			}
			continue
		}
		if tok != "skeleton" {
			return nil, fmt.Errorf("skeletons.brf: expected a skeleton section first, found %q", tok)
		}
		break
	}
	n, err := r.i()
	if err != nil {
		return nil, err
	}
	for k := 0; k < n; k++ {
		name, err := r.s()
		if err != nil {
			return nil, err
		}
		nb, err := r.i()
		if err != nil {
			return nil, err
		}
		sk := &WBSkeleton{}
		var lt []V3
		var lm []M3
		for b := 0; b < nb; b++ {
			par, _ := r.i()
			bn, err := r.s()
			if err != nil {
				return nil, err
			}
			if _, err := r.i(); err != nil {
				return nil, err
			}
			a, _ := r.v3()
			bb, _ := r.v3()
			c, _ := r.v3()
			t, err := r.v3()
			if err != nil {
				return nil, err
			}
			sk.Names = append(sk.Names, bn)
			sk.Parent = append(sk.Parent, par)
			lt = append(lt, t)
			// the three stored vectors are the columns of the local rotation
			lm = append(lm, M3{{a[0], bb[0], c[0]}, {a[1], bb[1], c[1]}, {a[2], bb[2], c[2]}})
		}
		if name != "skel_human" {
			continue
		}
		sk.Pos = make([]V3, nb)
		sk.Rot = make([]M3, nb)
		for b := 0; b < nb; b++ {
			p := sk.Parent[b]
			if p < 0 {
				sk.Pos[b], sk.Rot[b] = lt[b], lm[b]
			} else {
				if p >= b {
					return nil, fmt.Errorf("skel_human: bone %d before its parent", b)
				}
				sk.Pos[b] = sk.Pos[p].Add(sk.Rot[p].MulV(lt[b]))
				sk.Rot[b] = sk.Rot[p].Mul(lm[b])
			}
		}
		return sk, nil
	}
	return nil, fmt.Errorf("skel_human not found in %s", path)
}

func (s *WBSkeleton) Index(name string) int {
	for i, n := range s.Names {
		if n == name {
			return i
		}
	}
	return -1
}
