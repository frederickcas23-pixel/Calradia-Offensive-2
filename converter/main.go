// cs2calradia-setup reads Counter-Strike 2 weapons, agents and sounds from the player's own CS2 install and writes
// them in Mount & Blade: Warband's formats into the mashup's module folder. Nothing from either game ships with the mod.
package main

import (
	"bufio"
	"embed"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"time"
)

const toolVersion = "0.1.0"

//go:embed sheets/assets.json sheets/sounds.json
var sheets embed.FS

type assetRow struct {
	ID, Kind, Vpk, Out, Orient string
	Scale                      float64
	Offset                     [3]float64
	SkipMaterials              []string `json:"skip_materials"`
	TexMax                     int      `json:"tex_max"`
	PreferMesh                 []string `json:"prefer_mesh"`
	Anchor                     *struct {
		Rear float64
		Top  *float64
	}
}
type soundRow struct {
	ID    string
	Files []string
}

var logw io.Writer = os.Stdout

func logf(f string, a ...any) { fmt.Fprintf(logw, time.Now().Format("15:04:05 ")+f+"\n", a...) }

func loadSheet(name string, into any) error {
	raw, err := sheets.ReadFile("sheets/" + name)
	if err != nil {
		return err
	}
	var doc struct{ Rows json.RawMessage }
	if err := json.Unmarshal(raw, &doc); err != nil {
		return err
	}
	return json.Unmarshal(doc.Rows, into)
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		return err
	}
	return out.Close()
}

// copyNative fills the module folder with the player's own Native module files (scenes, map, base resources),
// never replacing a file the mashup already provides.
func copyNative(native, module string) (int, error) {
	n := 0
	err := filepath.WalkDir(native, func(p string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(native, p)
		if d.IsDir() || strings.EqualFold(rel, "module.ini") {
			return nil
		}
		dst := filepath.Join(module, rel)
		if _, err := os.Stat(dst); err == nil {
			return nil
		}
		n++
		return copyFile(p, dst)
	})
	return n, err
}

var reIniKey = regexp.MustCompile(`^\s*([A-Za-z0-9_]+)\s*=`)

// writeModuleIni derives the module's module.ini from the player's Native one.
func writeModuleIni(native, module string) error {
	raw, err := os.ReadFile(filepath.Join(native, "module.ini"))
	if err != nil {
		return err
	}
	set := map[string]string{"display_wp_firearms": "1", "scan_module_sounds": "1", "scan_module_textures": "1"}
	seen := map[string]bool{}
	var out []string
	for _, line := range strings.Split(strings.ReplaceAll(string(raw), "\r\n", "\n"), "\n") {
		if strings.Contains(line, "load_mod_resource = cs2_assets") {
			continue
		}
		if m := reIniKey.FindStringSubmatch(line); m != nil {
			if v, ok := set[m[1]]; ok {
				line = m[1] + " = " + v
				seen[m[1]] = true
			}
		}
		out = append(out, line)
	}
	for k, v := range set {
		if !seen[k] {
			out = append(out, k+" = "+v)
		}
	}
	out = append(out, "load_mod_resource = cs2_assets", "")
	return os.WriteFile(filepath.Join(module, "module.ini"), []byte(strings.Join(out, "\r\n")), 0o644)
}

func runVRF(vrf string, args ...string) (string, error) {
	cmd := exec.Command(vrf, args...)
	hideWindow(cmd)
	out, err := cmd.CombinedOutput()
	return string(out), err
}

var reUnsafe = regexp.MustCompile(`[^a-z0-9_]+`)
var reHash = regexp.MustCompile(`_(psd|tga|png|vmat_g_[a-z]+)_[0-9a-f]{6,8}$`)

func texName(file string) string {
	b := strings.ToLower(strings.TrimSuffix(filepath.Base(file), filepath.Ext(file)))
	b = reHash.ReplaceAllString(b, "")
	b = reUnsafe.ReplaceAllString(b, "_")
	if len(b) > 48 {
		b = b[:48]
	}
	return "cs2_" + b
}

type converter struct {
	work, module string
	textures     map[string]string // dds name -> source png
	texMax       map[string]int
	mats         map[string]Material
	meshes       []*Mesh
}

func (c *converter) material(p *Prim, skinned bool, texMax int) (string, error) {
	if p.TexFile == "" {
		return "", fmt.Errorf("material %s has no colour texture", p.MatName)
	}
	if _, err := os.Stat(p.TexFile); err != nil {
		return "", fmt.Errorf("colour texture for %s was not exported (%s)", p.MatName, filepath.Base(p.TexFile))
	}
	tn := texName(p.TexFile)
	c.textures[tn] = p.TexFile
	c.texMax[tn] = texMax
	name, shader := tn+"_mat", "iron_shader_Instanced"
	if skinned {
		name, shader = tn+"_skin", "iron_shader_skin"
	}
	c.mats[name] = Material{Name: name, Shader: shader, Diffuse: tn, Flags: 1824, Specular: 16, RGB: [3]float64{5, 5, 5}}
	return name, nil
}

// canonical converts a decompiler glTF point to the weapon's own frame: (forward, up, right) in metres.
func canonical(orient string, p V3) V3 {
	if orient == "knife" { // CS2 knives are modelled blade-up
		return V3{p[1], -p[2], -p[0]}
	}
	return V3{p[2], p[1], -p[0]}
}

// toItemSpace converts a (forward, up, right) point to Warband's item-bone space for the given hold.
func toItemSpace(orient string, p V3) V3 {
	const h = 0.7071067811865476
	if orient == "pistol" { // like the native flintlock pistol: barrel on the X/Y diagonal, right side +Z
		return V3{h*p[0] - h*p[1], h*p[0] + h*p[1], p[2]}
	}
	return V3{-p[1], p[0], p[2]} // muskets, crossbows, daggers: forward +Y, top -X, right side +Z
}

func (c *converter) weapon(a assetRow, prims []*Prim) error {
	switch a.Orient {
	case "long", "pistol", "knife":
	default:
		return fmt.Errorf("%s: unknown orient %q", a.ID, a.Orient)
	}
	skip := map[string]bool{}
	for _, s := range a.SkipMaterials {
		skip[s] = true
	}
	var chosen []*Prim
	for _, want := range a.PreferMesh {
		for _, p := range prims {
			if p.MeshName == want && !skip[p.MatName] {
				chosen = append(chosen, p)
			}
		}
		if len(chosen) > 0 {
			break
		}
	}
	if len(chosen) == 0 {
		return fmt.Errorf("%s: none of the meshes %v were found in the model", a.ID, a.PreferMesh)
	}
	// grip anchor from the model's own extents, so a moved model origin in a CS2 update does not move the gun in the hand
	lo, hi := V3{1e9, 1e9, 1e9}, V3{-1e9, -1e9, -1e9}
	for _, p := range chosen {
		for _, v := range p.Pos {
			q := canonical(a.Orient, v)
			for k := 0; k < 3; k++ {
				lo[k], hi[k] = min(lo[k], q[k]), max(hi[k], q[k])
			}
		}
	}
	var grip V3
	if a.Anchor != nil {
		grip[0] = lo[0] + a.Anchor.Rear
		if a.Anchor.Top != nil {
			grip[1] = hi[1] - *a.Anchor.Top
		} else {
			grip[1] = (lo[1] + hi[1]) / 2
		}
		grip[2] = (lo[2] + hi[2]) / 2
	}
	off := V3{a.Offset[0], a.Offset[1], a.Offset[2]}
	byMat := map[string]*Mesh{}
	var order []string
	for _, p := range chosen {
		mat, err := c.material(p, false, a.TexMax)
		if err != nil {
			return fmt.Errorf("%s: %w", a.ID, err)
		}
		m, ok := byMat[mat]
		if !ok {
			m = &Mesh{Material: mat}
			byMat[mat] = m
			order = append(order, mat)
		}
		base := len(m.Pos)
		for i := range p.Pos {
			q := canonical(a.Orient, p.Pos[i]).Sub(grip).Mul(a.Scale)
			m.Pos = append(m.Pos, toItemSpace(a.Orient, q).Add(off))
			m.Nrm = append(m.Nrm, toItemSpace(a.Orient, canonical(a.Orient, p.Nrm[i])).Norm())
			m.UV = append(m.UV, p.UV[i])
		}
		for _, t := range p.Tri {
			m.Tri = append(m.Tri, [3]int{t[0] + base, t[1] + base, t[2] + base})
		}
	}
	for i, mat := range order {
		m := byMat[mat]
		m.Name = a.Out
		if i > 0 {
			m.Name = fmt.Sprintf("%s.%d", a.Out, i)
		}
		c.meshes = append(c.meshes, m)
		logf("  %s: %d vertices, %d triangles, material %s", m.Name, len(m.Pos), len(m.Tri), mat)
	}
	return nil
}

func (c *converter) agent(a assetRow, prims []*Prim, dataTxt string, wb *WBSkeleton) error {
	src, err := ParseSkeleton(dataTxt)
	if err != nil {
		return fmt.Errorf("%s: %w", a.ID, err)
	}
	rt, err := NewRetarget(src, wb)
	if err != nil {
		return fmt.Errorf("%s: %w", a.ID, err)
	}
	skip := map[string]bool{}
	for _, s := range a.SkipMaterials {
		skip[s] = true
	}
	var matErr error
	parts, err := BuildAgent(prims, rt, a.Out, skip, func(p *Prim, skinned bool) string {
		n, err := c.material(p, skinned, a.TexMax)
		if err != nil && matErr == nil {
			matErr = err
		}
		return n
	})
	if err != nil {
		return err
	}
	if matErr != nil {
		return fmt.Errorf("%s: %w", a.ID, matErr)
	}
	for _, l := range [][]*Mesh{parts.Body, parts.Head, parts.GloveL, parts.GloveR} {
		for _, m := range l {
			c.meshes = append(c.meshes, m)
			logf("  %s: %d vertices, %d triangles, material %s", m.Name, len(m.Pos), len(m.Tri), m.Material)
		}
	}
	return nil
}

func run() error {
	cs2 := flag.String("cs2", "", "Counter-Strike 2 install folder")
	game := flag.String("game", "", "Mount & Blade: Warband install folder")
	modName := flag.String("module", "Calradia Offensive", "module folder name under Modules")
	vrfPath := flag.String("vrf", "", "path to Source2Viewer-CLI (default: next to this program)")
	workDir := flag.String("work", "", "scratch folder (default: a temp folder)")
	doneFile := flag.String("done", "", "extra path to write the done marker to")
	force := flag.Bool("force", false, "convert even if already done")
	flag.Parse()
	if *cs2 == "" || *game == "" {
		return fmt.Errorf("both --cs2 and --game are required")
	}
	module := filepath.Join(*game, "Modules", *modName)
	native := filepath.Join(*game, "Modules", "Native")
	marker := filepath.Join(module, "cs2_setup_done.json")
	if err := os.MkdirAll(module, 0o755); err != nil {
		return fmt.Errorf("cannot write to %s: %w", module, err)
	}
	if lf, err := os.Create(filepath.Join(module, "cs2_setup.log")); err == nil {
		defer lf.Close()
		logw = io.MultiWriter(os.Stdout, lf)
	}
	logf("cs2calradia-setup %s on %s", toolVersion, runtime.GOOS)
	pak := filepath.Join(*cs2, "game", "csgo", "pak01_dir.vpk")
	if _, err := os.Stat(pak); err != nil {
		return fmt.Errorf("Counter-Strike 2 was not found at %s (missing game/csgo/pak01_dir.vpk)", *cs2)
	}
	if _, err := os.Stat(filepath.Join(native, "module.ini")); err != nil {
		return fmt.Errorf("Warband's Native module was not found at %s", native)
	}
	cs2Version := ""
	if inf, err := os.ReadFile(filepath.Join(*cs2, "game", "csgo", "steam.inf")); err == nil {
		sc := bufio.NewScanner(strings.NewReader(string(inf)))
		for sc.Scan() {
			if v, ok := strings.CutPrefix(sc.Text(), "PatchVersion="); ok {
				cs2Version = strings.TrimSpace(v)
			}
		}
	}
	if raw, err := os.ReadFile(marker); err == nil && !*force {
		var m map[string]string
		if json.Unmarshal(raw, &m) == nil && m["tool"] == toolVersion {
			logf("already set up (CS2 %s when converted); nothing to do", m["cs2"])
			return writeDone(*doneFile, raw)
		}
	}
	vrf := *vrfPath
	if vrf == "" {
		exe, _ := os.Executable()
		vrf = filepath.Join(filepath.Dir(exe), "Source2Viewer-CLI")
		if runtime.GOOS == "windows" {
			vrf += ".exe"
		}
	}
	if _, err := os.Stat(vrf); err != nil {
		return fmt.Errorf("the Source 2 decompiler is missing (%s)", vrf)
	}
	work := *workDir
	if work == "" {
		var err error
		if work, err = os.MkdirTemp("", "cs2calradia"); err != nil {
			return err
		}
		defer os.RemoveAll(work)
	}
	var assets []assetRow
	var sounds []soundRow
	if err := loadSheet("assets.json", &assets); err != nil {
		return err
	}
	if err := loadSheet("sounds.json", &sounds); err != nil {
		return err
	}

	logf("step 1/5: Warband base files")
	n, err := copyNative(native, module)
	if err != nil {
		return fmt.Errorf("copying Native module files: %w", err)
	}
	logf("  copied %d files from Native", n)
	if err := writeModuleIni(native, module); err != nil {
		return err
	}
	wb, err := LoadWBSkeleton(filepath.Join(*game, "CommonRes", "skeletons.brf"))
	if err != nil {
		return err
	}

	logf("step 2/5: reading models from Counter-Strike 2 %s", cs2Version)
	var paths []string
	for _, a := range assets {
		paths = append(paths, a.Vpk)
	}
	mdlDir := filepath.Join(work, "models")
	out, _ := runVRF(vrf, "-i", pak, "-f", strings.Join(paths, ","), "-o", mdlDir, "-d", "--gltf_export_format", "gltf", "--gltf_export_materials")
	os.WriteFile(filepath.Join(work, "vrf_models.log"), []byte(out), 0o644)

	c := &converter{work: work, module: module, textures: map[string]string{}, texMax: map[string]int{}, mats: map[string]Material{}}
	logf("step 3/5: converting meshes")
	for _, a := range assets {
		gl := filepath.Join(mdlDir, filepath.FromSlash(strings.TrimSuffix(a.Vpk, ".vmdl_c")+".gltf"))
		prims, err := LoadGLTF(gl)
		if err != nil {
			return fmt.Errorf("%s: could not read %s from your Counter-Strike 2 files (%v). The decompiler log is in %s", a.ID, a.Vpk, err, work)
		}
		switch a.Kind {
		case "weapon":
			err = c.weapon(a, prims)
		case "agent":
			data, _ := runVRF(vrf, "-i", pak, "-f", a.Vpk, "-b", "DATA")
			err = c.agent(a, prims, data, wb)
		default:
			err = fmt.Errorf("%s: unknown kind %q", a.ID, a.Kind)
		}
		if err != nil {
			return err
		}
	}

	logf("step 4/5: textures and sounds")
	texDir, sndDir, resDir := filepath.Join(module, "Textures"), filepath.Join(module, "Sounds"), filepath.Join(module, "Resource")
	for _, d := range []string{texDir, sndDir, resDir} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			return err
		}
	}
	var texNames []string
	for t := range c.textures {
		texNames = append(texNames, t)
	}
	sort.Strings(texNames)
	for _, t := range texNames {
		img, err := LoadRGBA(c.textures[t], c.texMax[t])
		if err != nil {
			return fmt.Errorf("texture %s: %w", t, err)
		}
		if err := WriteDDS(filepath.Join(texDir, t+".dds"), img); err != nil {
			return err
		}
	}
	logf("  wrote %d textures", len(texNames))
	var sndPaths []string
	for _, s := range sounds {
		sndPaths = append(sndPaths, s.Files...)
	}
	sndWork := filepath.Join(work, "sounds")
	out, _ = runVRF(vrf, "-i", pak, "-f", strings.Join(sndPaths, ","), "-o", sndWork, "-d")
	os.WriteFile(filepath.Join(work, "vrf_sounds.log"), []byte(out), 0o644)
	ns := 0
	for _, s := range sounds {
		for i, f := range s.Files {
			src := filepath.Join(sndWork, filepath.FromSlash(strings.TrimSuffix(f, ".vsnd_c")+".wav"))
			if err := ConvertWAV(src, filepath.Join(sndDir, fmt.Sprintf("%s_%d.wav", s.ID, i+1))); err != nil {
				return fmt.Errorf("sound %s: could not read %s from your Counter-Strike 2 files (%v)", s.ID, f, err)
			}
			ns++
		}
	}
	logf("  wrote %d sounds", ns)

	logf("step 5/5: writing Resource/cs2_assets.brf")
	var mats []Material
	var matNames []string
	for n := range c.mats {
		matNames = append(matNames, n)
	}
	sort.Strings(matNames)
	for _, n := range matNames {
		mats = append(mats, c.mats[n])
	}
	if err := WriteBRF(filepath.Join(resDir, "cs2_assets.brf"), texNames, mats, c.meshes); err != nil {
		return err
	}
	done, _ := json.Marshal(map[string]string{"tool": toolVersion, "cs2": cs2Version, "at": time.Now().UTC().Format(time.RFC3339)})
	if err := os.WriteFile(marker, done, 0o644); err != nil {
		return err
	}
	logf("done: %d meshes, %d materials, %d textures, %d sounds", len(c.meshes), len(mats), len(texNames), ns)
	return writeDone(*doneFile, done)
}

func writeDone(path string, data []byte) error {
	if path == "" {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

func main() {
	if err := run(); err != nil {
		logf("FAILED: %v", err)
		os.Exit(1)
	}
}
