package main

import (
	"bytes"
	"encoding/binary"
	"math"
	"os"
)

// Mesh is one Warband BRF mesh: one position per vertex, optional skinning to skel_human.
type Mesh struct {
	Name, Material string
	Pos, Nrm       []V3
	UV             [][2]float64
	Tri            [][3]int
	Bones          [][4]int     // per vertex, -1 = unused
	Weights        [][4]float64 // per vertex
}

type Material struct {
	Name, Shader, Diffuse string
	Bump, SpecMap         string // texture names, "" = none
	Flags                 uint32
	Specular              float64
	RGB                   [3]float64
}

type bw struct{ bytes.Buffer }

func (b *bw) i(v int)     { binary.Write(b, binary.LittleEndian, int32(v)) }
func (b *bw) u(v uint32)  { binary.Write(b, binary.LittleEndian, v) }
func (b *bw) f(v float64) { binary.Write(b, binary.LittleEndian, float32(v)) }
func (b *bw) s(v string)  { b.i(len(v)); b.WriteString(v) }
func (b *bw) v3(v V3)     { b.f(v[0]); b.f(v[1]); b.f(v[2]) }

// WriteBRF writes a Warband ("rfver 1") resource file with textures, materials and meshes.
func WriteBRF(path string, textures []string, mats []Material, meshes []*Mesh) error {
	var b bw
	b.s("rfver ")
	b.i(1)
	if len(textures) > 0 {
		b.s("texture")
		b.i(len(textures))
		for _, t := range textures {
			b.s(t + ".dds")
			b.u(0)
		}
	}
	if len(mats) > 0 {
		b.s("material")
		b.i(len(mats))
		for _, m := range mats {
			b.s(m.Name)
			b.u(m.Flags)
			b.s(m.Shader)
			b.s(m.Diffuse)
			b.s("none")
			b.s(orNone(m.Bump))
			b.s("none")
			b.s(orNone(m.SpecMap))
			b.f(m.Specular)
			b.f(m.RGB[0])
			b.f(m.RGB[1])
			b.f(m.RGB[2])
		}
	}
	if len(meshes) > 0 {
		b.s("mesh")
		b.i(len(meshes))
		for _, m := range meshes {
			b.s(m.Name)
			b.u(0x30000) // tangent field + Warband format
			b.s(m.Material)
			b.i(len(m.Pos))
			for _, p := range m.Pos {
				b.v3(p)
			}
			// skinning: grouped per bone as (vertex, weight) pairs
			if len(m.Bones) == len(m.Pos) && len(m.Pos) > 0 {
				per := map[int][][2]float64{}
				maxb := -1
				for vi := range m.Bones {
					for k := 0; k < 4; k++ {
						bi := m.Bones[vi][k]
						if bi < 0 || m.Weights[vi][k] <= 0 {
							continue
						}
						per[bi] = append(per[bi], [2]float64{float64(vi), m.Weights[vi][k]})
						if bi > maxb {
							maxb = bi
						}
					}
				}
				b.i(len(per))
				for bi := 0; bi <= maxb; bi++ {
					l, ok := per[bi]
					if !ok {
						continue
					}
					b.i(bi)
					b.i(len(l))
					for _, p := range l {
						b.i(int(p[0]))
						b.f(p[1])
					}
				}
			} else {
				b.i(0)
			}
			b.i(0) // no extra vertex-animation frames
			b.i(len(m.Pos))
			tan := tangents(m)
			for vi := range m.Pos {
				n := m.Nrm[vi]
				b.i(vi)
				b.u(0xFFFFFFFF)
				b.v3(n)
				b.v3(tan[vi])
				b.WriteByte(0)
				u, v := m.UV[vi][0], m.UV[vi][1]
				if math.IsNaN(u) || math.IsNaN(v) {
					u, v = 0, 0
				}
				b.f(u)
				b.f(v)
			}
			b.i(len(m.Tri))
			for _, t := range m.Tri {
				b.i(t[0])
				b.i(t[1])
				b.i(t[2])
			}
		}
	}
	b.s("end")
	return os.WriteFile(path, b.Bytes(), 0o644)
}

func orNone(s string) string {
	if s == "" {
		return "none"
	}
	return s
}

// tangents returns one unit tangent per vertex: the direction in which the texture's U grows, made perpendicular to the normal.
func tangents(m *Mesh) []V3 {
	acc := make([]V3, len(m.Pos))
	for _, t := range m.Tri {
		p0, p1, p2 := m.Pos[t[0]], m.Pos[t[1]], m.Pos[t[2]]
		u0, u1, u2 := m.UV[t[0]], m.UV[t[1]], m.UV[t[2]]
		e1, e2 := p1.Sub(p0), p2.Sub(p0)
		du1, dv1, du2, dv2 := u1[0]-u0[0], u1[1]-u0[1], u2[0]-u0[0], u2[1]-u0[1]
		det := du1*dv2 - du2*dv1
		if math.Abs(det) < 1e-12 {
			continue
		}
		d := e1.Mul(dv2 / det).Sub(e2.Mul(dv1 / det))
		if l := d.Len(); l > 1e-12 && !math.IsNaN(l) {
			d = d.Mul(1 / l)
			for _, vi := range t {
				acc[vi] = acc[vi].Add(d)
			}
		}
	}
	for vi := range acc {
		n := m.Nrm[vi]
		t := acc[vi].Sub(n.Mul(acc[vi].Dot(n)))
		if t.Len() < 1e-6 {
			t = n.Cross(V3{0, 0, 1})
			if t.Len() < 1e-6 {
				t = V3{1, 0, 0}
			}
		}
		acc[vi] = t.Norm()
	}
	return acc
}
