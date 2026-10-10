package main

import "math"

type V3 [3]float64
type M3 [3][3]float64 // row-major

func (a V3) Add(b V3) V3      { return V3{a[0] + b[0], a[1] + b[1], a[2] + b[2]} }
func (a V3) Sub(b V3) V3      { return V3{a[0] - b[0], a[1] - b[1], a[2] - b[2]} }
func (a V3) Mul(s float64) V3 { return V3{a[0] * s, a[1] * s, a[2] * s} }
func (a V3) Dot(b V3) float64 { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] }
func (a V3) Len() float64     { return math.Sqrt(a.Dot(a)) }
func (a V3) Cross(b V3) V3 {
	return V3{a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]}
}
func (a V3) Norm() V3 {
	l := a.Len()
	if l < 1e-12 {
		return V3{0, 0, 1}
	}
	return a.Mul(1 / l)
}

func Ident() M3 { return M3{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}} }
func (m M3) MulV(v V3) V3 {
	return V3{m[0][0]*v[0] + m[0][1]*v[1] + m[0][2]*v[2], m[1][0]*v[0] + m[1][1]*v[1] + m[1][2]*v[2], m[2][0]*v[0] + m[2][1]*v[1] + m[2][2]*v[2]}
}
func (m M3) Mul(n M3) M3 {
	var r M3
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			r[i][j] = m[i][0]*n[0][j] + m[i][1]*n[1][j] + m[i][2]*n[2][j]
		}
	}
	return r
}
func (m M3) T() M3 {
	return M3{{m[0][0], m[1][0], m[2][0]}, {m[0][1], m[1][1], m[2][1]}, {m[0][2], m[1][2], m[2][2]}}
}
func (m M3) Col(j int) V3 { return V3{m[0][j], m[1][j], m[2][j]} }

// QuatM3 converts an (x,y,z,w) quaternion to a rotation matrix.
func QuatM3(q [4]float64) M3 {
	x, y, z, w := q[0], q[1], q[2], q[3]
	return M3{
		{1 - 2*(y*y+z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)},
		{2 * (x*y + z*w), 1 - 2*(x*x+z*z), 2 * (y*z - x*w)},
		{2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2*(x*x+y*y)},
	}
}

// RotBetween returns the smallest rotation taking unit vector a onto unit vector b.
func RotBetween(a, b V3) M3 {
	a, b = a.Norm(), b.Norm()
	v := a.Cross(b)
	c := a.Dot(b)
	if c > 1-1e-9 {
		return Ident()
	}
	if c < -1+1e-9 {
		// 180 degrees about any axis perpendicular to a
		p := a.Cross(V3{1, 0, 0})
		if p.Len() < 1e-6 {
			p = a.Cross(V3{0, 1, 0})
		}
		p = p.Norm()
		return M3{
			{2*p[0]*p[0] - 1, 2 * p[0] * p[1], 2 * p[0] * p[2]},
			{2 * p[0] * p[1], 2*p[1]*p[1] - 1, 2 * p[1] * p[2]},
			{2 * p[0] * p[2], 2 * p[1] * p[2], 2*p[2]*p[2] - 1},
		}
	}
	k := 1 / (1 + c)
	vx := M3{{0, -v[2], v[1]}, {v[2], 0, -v[0]}, {-v[1], v[0], 0}}
	vx2 := vx.Mul(vx)
	r := Ident()
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			r[i][j] += vx[i][j] + vx2[i][j]*k
		}
	}
	return r
}

// AxisAngle is a rotation of ang radians about unit axis k.
func AxisAngle(k V3, ang float64) M3 {
	k = k.Norm()
	s, c := math.Sin(ang), math.Cos(ang)
	t := 1 - c
	return M3{
		{t*k[0]*k[0] + c, t*k[0]*k[1] - s*k[2], t*k[0]*k[2] + s*k[1]},
		{t*k[0]*k[1] + s*k[2], t*k[1]*k[1] + c, t*k[1]*k[2] - s*k[0]},
		{t*k[0]*k[2] - s*k[1], t*k[1]*k[2] + s*k[0], t*k[2]*k[2] + c},
	}
}
