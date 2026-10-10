package main

import (
	"fmt"
	"math"
	"sort"
	"strings"
)

// Converting a CS2 agent to Warband gear.
//
// The CS2 mesh is bound to CS2's skeleton in an A-pose; Warband needs it bound to skel_human in its own T-pose with
// different proportions. Every CS2 bone is assigned (a) the Warband bone that will animate it and (b) a transform
// that carries the bone's region from the CS2 bind pose to the Warband bind pose. A vertex is moved by the blend of
// its bones' transforms, then re-weighted to the Warband bones.

const srcToMetres = 0.0254

// srcToWB converts a Source-space point (inches; X forward, Y left, Z up) to Warband mesh space (metres; X right, Y forward, Z up).
func srcToWB(p V3) V3 { return V3{-p[1] * srcToMetres, p[0] * srcToMetres, p[2] * srcToMetres} }

// gltfToWB converts a decompiler glTF point (metres; X = Source Y, Y = Source Z, Z = Source X) to Warband mesh space.
func gltfToWB(p V3) V3 { return V3{-p[0], p[2], p[1]} }

type affine struct {
	A M3 // linear part
	R M3 // rotation part, for normals
	O V3 // source pivot
	T V3 // target pivot
}

func (a affine) apply(p V3) V3 { return a.T.Add(a.A.MulV(p.Sub(a.O))) }

// stretch returns R * (radial*I + (along-radial) d d^T): scale by `along` on unit axis d and `radial` across it, then rotate.
func stretch(R M3, d V3, along, radial float64) M3 {
	var s M3
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			s[i][j] = (along - radial) * d[i] * d[j]
			if i == j {
				s[i][j] += radial
			}
		}
	}
	return R.Mul(s)
}

type boneMap struct {
	wb  int    // Warband bone index that animates this CS2 bone
	cls string // transform class
}

var wbNames = []string{"abdomen", "thigh.L", "calf.L", "foot.L", "thigh.R", "calf.R", "foot.R", "spine", "thorax", "head",
	"shoulder.L", "upperarm.L", "forearm.L", "hand.L", "item.L", "shoulder.R", "upperarm.R", "forearm.R", "hand.R", "item.R"}

// direct CS2 bone -> (Warband bone name, transform class)
var directMap = map[string][2]string{
	"pelvis": {"abdomen", "torso"}, "spine_0": {"abdomen", "torso"}, "spine_1": {"spine", "torso"}, "spine_2": {"spine", "torso"},
	"spine_3": {"thorax", "torso"}, "neck_0": {"thorax", "torso"}, "head_0": {"head", "head"},
	"clavicle_L": {"shoulder.L", "torso"}, "arm_upper_L": {"upperarm.L", "upperarm.L"}, "arm_lower_L": {"forearm.L", "forearm.L"}, "hand_L": {"hand.L", "hand.L"},
	"clavicle_R": {"shoulder.R", "torso"}, "arm_upper_R": {"upperarm.R", "upperarm.R"}, "arm_lower_R": {"forearm.R", "forearm.R"}, "hand_R": {"hand.R", "hand.R"},
	"leg_upper_L": {"thigh.L", "thigh.L"}, "leg_lower_L": {"calf.L", "calf.L"}, "ankle_L": {"foot.L", "foot.L"}, "ball_L": {"foot.L", "foot.L"},
	"leg_upper_R": {"thigh.R", "thigh.R"}, "leg_lower_R": {"calf.R", "calf.R"}, "ankle_R": {"foot.R", "foot.R"}, "ball_R": {"foot.R", "foot.R"},
}

type Retarget struct {
	src   *SrcSkeleton
	wb    *WBSkeleton
	srcP  []V3 // CS2 bind joints in Warband space
	bones []boneMap
	xf    map[string]affine
	wbIdx map[string]int
	girth float64
}

func NewRetarget(src *SrcSkeleton, wb *WBSkeleton) (*Retarget, error) {
	r := &Retarget{src: src, wb: wb, xf: map[string]affine{}, wbIdx: map[string]int{}}
	for _, n := range wbNames {
		i := wb.Index(n)
		if i < 0 {
			return nil, fmt.Errorf("Warband skeleton has no bone %q", n)
		}
		r.wbIdx[n] = i
	}
	need := []string{"pelvis", "spine_3", "head_0", "arm_upper_L", "arm_lower_L", "hand_L", "arm_upper_R", "arm_lower_R", "hand_R",
		"leg_upper_L", "leg_lower_L", "ankle_L", "leg_upper_R", "leg_lower_R", "ankle_R"}
	for _, n := range need {
		if src.Index(n) < 0 {
			return nil, fmt.Errorf("CS2 skeleton has no bone %q (the game's player rig may have changed)", n)
		}
	}
	r.srcP = make([]V3, len(src.Pos))
	for i, p := range src.Pos {
		r.srcP[i] = srcToWB(p)
	}
	// bone assignment: direct names, twist helpers follow their base bone, fingers follow the hand, the rest follow their parent
	r.bones = make([]boneMap, len(src.Names))
	done := make([]bool, len(src.Names))
	var resolve func(i int) boneMap
	resolve = func(i int) boneMap {
		if done[i] {
			return r.bones[i]
		}
		done[i] = true
		name := src.Names[i]
		base := name
		if k := strings.Index(base, "_TWIST"); k >= 0 {
			base = base[:k]
		}
		if m, ok := directMap[base]; ok {
			r.bones[i] = boneMap{r.wbIdx[m[0]], m[1]}
		} else if strings.HasPrefix(name, "finger_") && strings.HasSuffix(name, "_L") {
			r.bones[i] = boneMap{r.wbIdx["hand.L"], "hand.L"}
		} else if strings.HasPrefix(name, "finger_") && strings.HasSuffix(name, "_R") {
			r.bones[i] = boneMap{r.wbIdx["hand.R"], "hand.R"}
		} else if p := src.Parent[i]; p >= 0 {
			r.bones[i] = resolve(p)
		} else {
			r.bones[i] = boneMap{r.wbIdx["abdomen"], "torso"}
		}
		return r.bones[i]
	}
	for i := range src.Names {
		resolve(i)
	}
	sp := func(n string) V3 { return r.srcP[src.Index(n)] }
	wp := func(n string) V3 { return wb.Pos[r.wbIdx[n]] }

	// limbs: carry the CS2 segment onto the Warband segment
	// CS2 agents stand about 1.98 m; Warband's skeleton about 1.75 m. Limb lengths follow the Warband bones, so
	// girth is scaled by the same overall ratio to keep CS2's proportions instead of a stocky figure.
	girth := (wp("head")[2] - wp("foot.L")[2]) / (sp("head_0")[2] - sp("ankle_L")[2])
	r.girth = girth
	limb := func(cls, s0, s1 string, t0, t1 V3, radial float64) affine {
		ds, dt := sp(s1).Sub(sp(s0)), t1.Sub(t0)
		R := RotBetween(ds, dt)
		a := affine{A: stretch(R, ds.Norm(), dt.Len()/ds.Len(), radial), R: R, O: sp(s0), T: t0}
		r.xf[cls] = a
		return a
	}
	footScale := wp("thigh.L")[2] / sp("leg_upper_L")[2]
	for _, s := range []string{"L", "R"} {
		ankleT := V3{wp("foot." + s)[0], wp("foot." + s)[1], sp("ankle_" + s)[2] * footScale}
		limb("thigh."+s, "leg_upper_"+s, "leg_lower_"+s, wp("thigh."+s), wp("calf."+s), girth)
		limb("calf."+s, "leg_lower_"+s, "ankle_"+s, wp("calf."+s), ankleT, girth)
		r.xf["foot."+s] = affine{A: stretch(Ident(), V3{0, 0, 1}, footScale, footScale), R: Ident(), O: sp("ankle_" + s), T: ankleT}
		limb("upperarm."+s, "arm_upper_"+s, "arm_lower_"+s, wp("upperarm."+s), wp("forearm."+s), girth)
		fa := limb("forearm."+s, "arm_lower_"+s, "hand_"+s, wp("forearm."+s), wp("hand."+s), girth)
		r.xf["hand."+s] = affine{A: stretch(fa.R, V3{0, 0, 1}, girth, girth), R: fa.R, O: sp("hand_" + s), T: wp("hand." + s)}
	}
	// head: rigid about the head pivot, slightly scaled
	headScale := girth
	r.xf["head"] = affine{A: stretch(Ident(), V3{0, 0, 1}, headScale, headScale), R: Ident(), O: sp("head_0"), T: wp("head")}
	return r, nil
}

// torso maps a CS2 rest position in the trunk to Warband rest space: heights are remapped piecewise-linearly through the
// hip, shoulder and head pivots, widths by the shoulder ratio.
func (r *Retarget) torso(p V3) V3 {
	sp := func(n string) V3 { return r.srcP[r.src.Index(n)] }
	wp := func(n string) V3 { return r.wb.Pos[r.wbIdx[n]] }
	zs := [3]float64{(sp("leg_upper_L")[2] + sp("leg_upper_R")[2]) / 2, (sp("arm_upper_L")[2] + sp("arm_upper_R")[2]) / 2, sp("head_0")[2]}
	zt := [3]float64{(wp("thigh.L")[2] + wp("thigh.R")[2]) / 2, (wp("upperarm.L")[2] + wp("upperarm.R")[2]) / 2, wp("head")[2]}
	var z float64
	switch {
	case p[2] <= zs[1]:
		z = zt[0] + (p[2]-zs[0])*(zt[1]-zt[0])/(zs[1]-zs[0])
	default:
		z = zt[1] + (p[2]-zs[1])*(zt[2]-zt[1])/(zs[2]-zs[1])
	}
	gx := math.Abs(wp("upperarm.L")[0]-wp("upperarm.R")[0]) / math.Abs(sp("arm_upper_L")[0]-sp("arm_upper_R")[0])
	// keep the trunk no wider than CS2 drew it: the shoulder joints sit slightly outside, which reads better than a broad chest
	gx = math.Min(math.Max(gx, r.girth), (1+r.girth)/2)
	gy := r.girth
	y := wp("abdomen")[1] + (p[1]-sp("pelvis")[1])*gy
	return V3{p[0] * gx, y, z}
}

// Vertex moves one bind-pose vertex (already in Warband space) and returns its new position, normal and Warband skin.
func (r *Retarget) Vertex(p, n V3, joints [4]int, weights [4]float64) (V3, V3, [4]int, [4]float64) {
	var np, nn V3
	acc := map[int]float64{}
	total := 0.0
	for k := 0; k < 4; k++ {
		w := weights[k]
		j := joints[k]
		if w <= 0 || j < 0 || j >= len(r.bones) {
			continue
		}
		bm := r.bones[j]
		var q, qn V3
		if bm.cls == "torso" {
			q, qn = r.torso(p), n
		} else {
			a := r.xf[bm.cls]
			q, qn = a.apply(p), a.R.MulV(n)
		}
		np = np.Add(q.Mul(w))
		nn = nn.Add(qn.Mul(w))
		acc[bm.wb] += w
		total += w
	}
	if total <= 0 {
		return r.torso(p), n, [4]int{r.wbIdx["abdomen"], -1, -1, -1}, [4]float64{1, 0, 0, 0}
	}
	np = np.Mul(1 / total)
	type bwt struct {
		b int
		w float64
	}
	var l []bwt
	for b, w := range acc {
		l = append(l, bwt{b, w})
	}
	sort.Slice(l, func(i, j int) bool {
		if l[i].w != l[j].w {
			return l[i].w > l[j].w
		}
		return l[i].b < l[j].b
	})
	if len(l) > 4 {
		l = l[:4]
	}
	sum := 0.0
	for _, e := range l {
		sum += e.w
	}
	ob := [4]int{-1, -1, -1, -1}
	var ow [4]float64
	for i, e := range l {
		ob[i], ow[i] = e.b, e.w/sum
	}
	return np, nn.Norm(), ob, ow
}

// meshBuilder collects triangles for one output mesh, re-indexing vertices.
type meshBuilder struct {
	m     *Mesh
	remap map[int]int
}

func newBuilder(name, material string) *meshBuilder {
	return &meshBuilder{m: &Mesh{Name: name, Material: material}, remap: map[int]int{}}
}

// AgentParts are the Warband meshes cut from one agent.
type AgentParts struct{ Body, Head, GloveL, GloveR, Boots []*Mesh }

// BuildAgent converts the third-person primitives of one agent. matFor returns the Warband material for a CS2 material (skinned or rigid).
func BuildAgent(prims []*Prim, rt *Retarget, outBase string, skip map[string]bool, matFor func(p *Prim, skinned bool) string) (*AgentParts, error) {
	headB, handL, handR := rt.wbIdx["head"], rt.wbIdx["hand.L"], rt.wbIdx["hand.R"]
	lower := []int{rt.wbIdx["calf.L"], rt.wbIdx["foot.L"], rt.wbIdx["calf.R"], rt.wbIdx["foot.R"]}
	type key struct{ part, mat string }
	builders := map[key]*meshBuilder{}
	var order []key
	weightOf := func(b [4]int, w [4]float64, bone int) float64 {
		s := 0.0
		for k := 0; k < 4; k++ {
			if b[k] == bone {
				s += w[k]
			}
		}
		return s
	}
	used := 0
	for _, p := range prims {
		if !strings.HasPrefix(p.MeshName, "thirdperson_") || skip[p.MatName] {
			continue
		}
		if len(p.Joints) != len(p.Pos) {
			return nil, fmt.Errorf("agent mesh %s/%s has no skin weights", p.MeshName, p.MatName)
		}
		used++
		n := len(p.Pos)
		pos, nrm := make([]V3, n), make([]V3, n)
		bones, wts := make([][4]int, n), make([][4]float64, n)
		for i := 0; i < n; i++ {
			pos[i], nrm[i], bones[i], wts[i] = rt.Vertex(gltfToWB(p.Pos[i]), gltfToWB(p.Nrm[i]), p.Joints[i], p.Weights[i])
		}
		isGloves := strings.Contains(p.MeshName, "gloves")
		for _, t := range p.Tri {
			part := "body"
			all := func(bone int) bool {
				for _, v := range t {
					if weightOf(bones[v], wts[v], bone) < 0.5 {
						return false
					}
				}
				return true
			}
			switch {
			case all(headB):
				part = "head"
			case isGloves && all(handL):
				part = "gloveL"
			case isGloves && all(handR):
				part = "gloveR"
			default:
				// shins and feet become the boots item, so Warband's own bare feet are never drawn
				boot := true
				for _, v := range t {
					w := 0.0
					for _, b := range lower {
						w += weightOf(bones[v], wts[v], b)
					}
					if w < 0.5 {
						boot = false
					}
				}
				if boot {
					part = "boots"
				}
			}
			k := key{part, p.MatName}
			b, ok := builders[k]
			if !ok {
				b = newBuilder("", matFor(p, part == "body" || part == "boots"))
				builders[k] = b
				order = append(order, k)
			}
			var tri [3]int
			for c, v := range t {
				ni, ok := b.remap[v+used<<24]
				if !ok {
					ni = len(b.m.Pos)
					b.remap[v+used<<24] = ni
					q, qn := pos[v], nrm[v]
					switch part {
					case "head":
						R := rt.wb.Rot[headB].T()
						q, qn = R.MulV(q.Sub(rt.wb.Pos[headB])), R.MulV(qn)
					case "gloveL":
						R := rt.wb.Rot[handL].T()
						q, qn = R.MulV(q.Sub(rt.wb.Pos[handL])), R.MulV(qn)
					case "gloveR":
						R := rt.wb.Rot[handR].T()
						q, qn = R.MulV(q.Sub(rt.wb.Pos[handR])), R.MulV(qn)
					}
					b.m.Pos = append(b.m.Pos, q)
					b.m.Nrm = append(b.m.Nrm, qn)
					b.m.UV = append(b.m.UV, p.UV[v])
					if part == "body" || part == "boots" {
						b.m.Bones = append(b.m.Bones, bones[v])
						b.m.Weights = append(b.m.Weights, wts[v])
					}
				}
				tri[c] = ni
			}
			b.m.Tri = append(b.m.Tri, tri)
		}
	}
	if used == 0 {
		return nil, fmt.Errorf("no third-person meshes found for %s", outBase)
	}
	out := &AgentParts{}
	names := map[string]string{"body": outBase + "_body", "head": outBase + "_head", "gloveL": outBase + "_glove_L", "gloveR": outBase + "_glove_R", "boots": outBase + "_boots"}
	count := map[string]int{}
	for _, k := range order {
		b := builders[k]
		if len(b.m.Tri) == 0 {
			continue
		}
		b.m.Name = names[k.part]
		if c := count[k.part]; c > 0 {
			b.m.Name = fmt.Sprintf("%s.%d", names[k.part], c)
		}
		count[k.part]++
		switch k.part {
		case "body":
			out.Body = append(out.Body, b.m)
		case "head":
			out.Head = append(out.Head, b.m)
		case "gloveL":
			out.GloveL = append(out.GloveL, b.m)
		case "gloveR":
			out.GloveR = append(out.GloveR, b.m)
		case "boots":
			out.Boots = append(out.Boots, b.m)
		}
	}
	if len(out.Body) == 0 || len(out.Head) == 0 || len(out.GloveL) == 0 || len(out.GloveR) == 0 || len(out.Boots) == 0 {
		return nil, fmt.Errorf("%s: could not cut body/head/gloves (body %d, head %d, left glove %d, right glove %d meshes)", outBase, len(out.Body), len(out.Head), len(out.GloveL), len(out.GloveR))
	}
	return out, nil
}
