package main

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// The decompiler prints a model's DATA block as KV3 text. Only the bind skeleton is needed from it.

func kvArrayBody(txt, key string) (string, error) {
	re := regexp.MustCompile(`\b` + regexp.QuoteMeta(key) + `\s*=\s*\[`)
	loc := re.FindStringIndex(txt)
	if loc == nil {
		return "", fmt.Errorf("key %s not found", key)
	}
	depth := 1
	i := loc[1]
	for i < len(txt) && depth > 0 {
		switch txt[i] {
		case '[':
			depth++
		case ']':
			depth--
		}
		i++
	}
	if depth != 0 {
		return "", fmt.Errorf("key %s: unterminated array", key)
	}
	return txt[loc[1] : i-1], nil
}

var reStr = regexp.MustCompile(`"([^"]*)"`)
var reRow = regexp.MustCompile(`\[([^\[\]]*)\]`)

func parseFloats(s string) []float64 {
	var out []float64
	for _, f := range strings.FieldsFunc(s, func(r rune) bool { return r == ',' || r == ' ' || r == '\n' || r == '\t' || r == '\r' }) {
		if v, err := strconv.ParseFloat(f, 64); err == nil {
			out = append(out, v)
		}
	}
	return out
}

// SrcSkeleton is a CS2 model's bind pose in Source space (inches, X forward, Y left, Z up).
type SrcSkeleton struct {
	Names  []string
	Parent []int
	Pos    []V3 // world bind position per bone
	Rot    []M3 // world bind rotation per bone
}

func ParseSkeleton(dataTxt string) (*SrcSkeleton, error) {
	i := strings.Index(dataTxt, "m_modelSkeleton")
	if i < 0 {
		return nil, fmt.Errorf("m_modelSkeleton not found")
	}
	sk := dataTxt[i:]
	nb, err := kvArrayBody(sk, "m_boneName")
	if err != nil {
		return nil, err
	}
	pb, err := kvArrayBody(sk, "m_nParent")
	if err != nil {
		return nil, err
	}
	posb, err := kvArrayBody(sk, "m_bonePosParent")
	if err != nil {
		return nil, err
	}
	rotb, err := kvArrayBody(sk, "m_boneRotParent")
	if err != nil {
		return nil, err
	}
	s := &SrcSkeleton{}
	for _, m := range reStr.FindAllStringSubmatch(nb, -1) {
		s.Names = append(s.Names, m[1])
	}
	for _, v := range parseFloats(pb) {
		s.Parent = append(s.Parent, int(v))
	}
	var lp []V3
	var lr []M3
	for _, m := range reRow.FindAllStringSubmatch(posb, -1) {
		f := parseFloats(m[1])
		if len(f) == 3 {
			lp = append(lp, V3{f[0], f[1], f[2]})
		}
	}
	for _, m := range reRow.FindAllStringSubmatch(rotb, -1) {
		f := parseFloats(m[1])
		if len(f) == 4 {
			lr = append(lr, QuatM3([4]float64{f[0], f[1], f[2], f[3]}))
		}
	}
	n := len(s.Names)
	if n == 0 || len(s.Parent) != n || len(lp) != n || len(lr) != n {
		return nil, fmt.Errorf("skeleton arrays disagree: %d names, %d parents, %d positions, %d rotations", n, len(s.Parent), len(lp), len(lr))
	}
	s.Pos = make([]V3, n)
	s.Rot = make([]M3, n)
	for b := 0; b < n; b++ {
		p := s.Parent[b]
		if p < 0 {
			s.Pos[b], s.Rot[b] = lp[b], lr[b]
		} else {
			if p >= b {
				return nil, fmt.Errorf("bone %d has parent %d after it", b, p)
			}
			s.Pos[b] = s.Pos[p].Add(s.Rot[p].MulV(lp[b]))
			s.Rot[b] = s.Rot[p].Mul(lr[b])
		}
	}
	return s, nil
}

func (s *SrcSkeleton) Index(name string) int {
	for i, n := range s.Names {
		if n == name {
			return i
		}
	}
	return -1
}
