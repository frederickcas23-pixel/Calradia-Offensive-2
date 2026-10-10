package main

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
)

type gltfDoc struct {
	Accessors []struct {
		BufferView    int    `json:"bufferView"`
		ByteOffset    int    `json:"byteOffset"`
		ComponentType int    `json:"componentType"`
		Count         int    `json:"count"`
		Type          string `json:"type"`
		Normalized    bool   `json:"normalized"`
	} `json:"accessors"`
	BufferViews []struct {
		Buffer, ByteOffset, ByteLength, ByteStride int
	} `json:"bufferViews"`
	Buffers   []struct{ URI string } `json:"buffers"`
	Images    []struct{ URI string } `json:"images"`
	Textures  []struct{ Source int } `json:"textures"`
	Materials []struct {
		Name string `json:"name"`
		PBR  struct {
			BaseColorTexture *struct{ Index int } `json:"baseColorTexture"`
		} `json:"pbrMetallicRoughness"`
	} `json:"materials"`
	Meshes []struct {
		Name       string `json:"name"`
		Primitives []struct {
			Attributes map[string]int `json:"attributes"`
			Indices    *int           `json:"indices"`
			Material   *int           `json:"material"`
		} `json:"primitives"`
	} `json:"meshes"`
}

// Prim is one glTF primitive in glTF space (metres, Y up).
type Prim struct {
	MeshName, MatName, TexFile string
	Pos, Nrm                   []V3
	UV                         [][2]float64
	Joints                     [][4]int
	Weights                    [][4]float64
	Tri                        [][3]int
}

func compSize(t int) int {
	switch t {
	case 5120, 5121:
		return 1
	case 5122, 5123:
		return 2
	}
	return 4
}
func typeN(t string) int {
	switch t {
	case "SCALAR":
		return 1
	case "VEC2":
		return 2
	case "VEC3":
		return 3
	case "VEC4":
		return 4
	}
	return 16
}

func (g *gltfDoc) read(bufs [][]byte, ai int) ([][]float64, error) {
	if ai < 0 || ai >= len(g.Accessors) {
		return nil, fmt.Errorf("accessor %d out of range", ai)
	}
	a := g.Accessors[ai]
	bv := g.BufferViews[a.BufferView]
	n := typeN(a.Type)
	cs := compSize(a.ComponentType)
	stride := bv.ByteStride
	if stride == 0 {
		stride = n * cs
	}
	buf := bufs[bv.Buffer]
	base := bv.ByteOffset + a.ByteOffset
	out := make([][]float64, a.Count)
	for i := 0; i < a.Count; i++ {
		row := make([]float64, n)
		for k := 0; k < n; k++ {
			o := base + i*stride + k*cs
			if o+cs > len(buf) {
				return nil, fmt.Errorf("accessor %d reads past buffer", ai)
			}
			var v float64
			switch a.ComponentType {
			case 5120:
				v = float64(int8(buf[o]))
				if a.Normalized {
					v = math.Max(v/127, -1)
				}
			case 5121:
				v = float64(buf[o])
				if a.Normalized {
					v /= 255
				}
			case 5122:
				v = float64(int16(binary.LittleEndian.Uint16(buf[o:])))
				if a.Normalized {
					v = math.Max(v/32767, -1)
				}
			case 5123:
				v = float64(binary.LittleEndian.Uint16(buf[o:]))
				if a.Normalized {
					v /= 65535
				}
			case 5125:
				v = float64(binary.LittleEndian.Uint32(buf[o:]))
			default:
				v = float64(math.Float32frombits(binary.LittleEndian.Uint32(buf[o:])))
			}
			row[k] = v
		}
		out[i] = row
	}
	return out, nil
}

// LoadGLTF reads every primitive of a .gltf written by the Source 2 decompiler.
func LoadGLTF(path string) ([]*Prim, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var g gltfDoc
	if err := json.Unmarshal(raw, &g); err != nil {
		return nil, err
	}
	dir := filepath.Dir(path)
	bufs := make([][]byte, len(g.Buffers))
	for i, b := range g.Buffers {
		if bufs[i], err = os.ReadFile(filepath.Join(dir, b.URI)); err != nil {
			return nil, err
		}
	}
	var out []*Prim
	for _, m := range g.Meshes {
		short := m.Name
		if i := strings.LastIndex(short, "."); i >= 0 {
			short = short[i+1:]
		}
		for _, pr := range m.Primitives {
			p := &Prim{MeshName: short}
			if pr.Material != nil && *pr.Material < len(g.Materials) {
				mat := g.Materials[*pr.Material]
				p.MatName = strings.TrimSuffix(filepath.Base(strings.ReplaceAll(mat.Name, "\\", "/")), ".vmat")
				if bc := mat.PBR.BaseColorTexture; bc != nil && bc.Index < len(g.Textures) {
					if src := g.Textures[bc.Index].Source; src < len(g.Images) {
						p.TexFile = filepath.Join(dir, g.Images[src].URI)
					}
				}
			}
			pi, ok := pr.Attributes["POSITION"]
			if !ok || pr.Indices == nil {
				continue
			}
			pos, err := g.read(bufs, pi)
			if err != nil {
				return nil, err
			}
			for _, r := range pos {
				p.Pos = append(p.Pos, V3{r[0], r[1], r[2]})
			}
			if ni, ok := pr.Attributes["NORMAL"]; ok {
				nrm, err := g.read(bufs, ni)
				if err != nil {
					return nil, err
				}
				for _, r := range nrm {
					p.Nrm = append(p.Nrm, V3{r[0], r[1], r[2]})
				}
			}
			for len(p.Nrm) < len(p.Pos) {
				p.Nrm = append(p.Nrm, V3{0, 1, 0})
			}
			if ti, ok := pr.Attributes["TEXCOORD_0"]; ok {
				uv, err := g.read(bufs, ti)
				if err != nil {
					return nil, err
				}
				for _, r := range uv {
					p.UV = append(p.UV, [2]float64{r[0], r[1]})
				}
			}
			for len(p.UV) < len(p.Pos) {
				p.UV = append(p.UV, [2]float64{0, 0})
			}
			ji, okj := pr.Attributes["JOINTS_0"]
			wi, okw := pr.Attributes["WEIGHTS_0"]
			if okj && okw {
				js, err := g.read(bufs, ji)
				if err != nil {
					return nil, err
				}
				ws, err := g.read(bufs, wi)
				if err != nil {
					return nil, err
				}
				for i := range js {
					p.Joints = append(p.Joints, [4]int{int(js[i][0]), int(js[i][1]), int(js[i][2]), int(js[i][3])})
					p.Weights = append(p.Weights, [4]float64{ws[i][0], ws[i][1], ws[i][2], ws[i][3]})
				}
			}
			idx, err := g.read(bufs, *pr.Indices)
			if err != nil {
				return nil, err
			}
			for i := 0; i+2 < len(idx); i += 3 {
				p.Tri = append(p.Tri, [3]int{int(idx[i][0]), int(idx[i+1][0]), int(idx[i+2][0])})
			}
			out = append(out, p)
		}
	}
	return out, nil
}
