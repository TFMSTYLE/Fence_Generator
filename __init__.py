# SPDX-FileCopyrightText: 2025-2026 The French Monkey
# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Fence",
    "author": "The French Monkey",
    "version": (1, 0, 4),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Fence",
    "description": "Generate parametric fence",
    "category": "Add Mesh",
    "license": "GPL-3.0-or-later",
}

import bpy
import bmesh
import math
from mathutils import Vector, Matrix
from math import radians, tau
from bpy.props import EnumProperty, FloatProperty, IntProperty, BoolProperty

try:
    from . import relay_updater
except ImportError:  # the Addon Collection has its own updates
    relay_updater = None

# ------------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------------

def _new_mesh(name="Fence"):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def _bm_box(bm, sx, sy, sz, cx=0, cy=0, cz=0):
    x, y, z = sx * 0.5, sy * 0.5, sz * 0.5
    verts = [bm.verts.new((cx + dx, cy + dy, cz + dz)) for dx, dy, dz in (
        (-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)
    )]
    faces = [
        [verts[0],verts[1],verts[2],verts[3]],
        [verts[4],verts[7],verts[6],verts[5]],
        [verts[0],verts[4],verts[5],verts[1]],
        [verts[1],verts[5],verts[6],verts[2]],
        [verts[2],verts[6],verts[7],verts[3]],
        [verts[3],verts[7],verts[4],verts[0]],
    ]
    for f in faces:
        try: bm.faces.new(f)
        except ValueError: pass

def _bm_cyl(bm, r, h, seg=16, cx=0, cy=0, cz=0, axis='Z'):
    seg = max(8, int(seg)); a = tau / seg
    btm, top, hh = [], [], h * 0.5
    for i in range(seg):
        ang = i * a; x, y = math.cos(ang) * r, math.sin(ang) * r
        if axis == 'X':
            btm.append(bm.verts.new((cx - hh, cy + x, cz + y)))
            top.append(bm.verts.new((cx + hh, cy + x, cz + y)))
        elif axis == 'Y':
            btm.append(bm.verts.new((cx + x, cy - hh, cz + y)))
            top.append(bm.verts.new((cx + x, cy + hh, cz + y)))
        else:
            btm.append(bm.verts.new((cx + x, cy + y, cz - hh)))
            top.append(bm.verts.new((cx + x, cy + y, cz + hh)))
    bm.verts.ensure_lookup_table()
    for i in range(seg):
        try: bm.faces.new([btm[i], btm[(i+1)%seg], top[(i+1)%seg], top[i]])
        except ValueError: pass
    try:
        bm.faces.new(btm[::-1]); bm.faces.new(top)
    except ValueError: pass

def _bm_tube(bm, r_out, r_in, h, seg=16, cx=0, cy=0, cz=0, axis='Z'):
    seg = max(8, int(seg)); a = tau / seg; hh = h * 0.5
    ob, ot, ib, it = [], [], [], []
    for i in range(seg):
        ang = i * a; c, s = math.cos(ang), math.sin(ang)
        if axis == 'X':
            ob.append(bm.verts.new((cx - hh, cy + c*r_out, cz + s*r_out)))
            ot.append(bm.verts.new((cx + hh, cy + c*r_out, cz + s*r_out)))
            ib.append(bm.verts.new((cx - hh, cy + c*r_in, cz + s*r_in)))
            it.append(bm.verts.new((cx + hh, cy + c*r_in, cz + s*r_in)))
        else:
            ob.append(bm.verts.new((cx + c*r_out, cy + s*r_out, cz - hh)))
            ot.append(bm.verts.new((cx + c*r_out, cy + s*r_out, cz + hh)))
            ib.append(bm.verts.new((cx + c*r_in, cy + s*r_in, cz - hh)))
            it.append(bm.verts.new((cx + c*r_in, cy + s*r_in, cz + hh)))
    bm.verts.ensure_lookup_table()
    for i in range(seg):
        try: bm.faces.new([ob[i], ob[(i+1)%seg], ot[(i+1)%seg], ot[i]])
        except ValueError: pass
    for i in range(seg):
        try: bm.faces.new([it[i], it[(i+1)%seg], ib[(i+1)%seg], ib[i]])
        except ValueError: pass
    for i in range(seg):
        try:
            bm.faces.new([ib[i], ib[(i+1)%seg], ob[(i+1)%seg], ob[i]])
            bm.faces.new([ob[i], ob[(i+1)%seg], ot[(i+1)%seg], ot[i]])
        except ValueError: pass

# ------------------------------------------------------------------------
# Fence builders
# ------------------------------------------------------------------------

def _build_posts(bm, x0, x1, z0, height, step, style, post_w, post_d, post_r, post_hollow=False, post_hollow_thickness=0.01):
    xs = []
    n = max(1, int(round((x1 - x0) / max(0.001, step))))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * (i / n)
        xs.append(x)
        if style == 'METAL':
            if post_hollow and post_r > post_hollow_thickness * 2:
                _bm_tube(bm, post_r, post_r - post_hollow_thickness, height, 16, x, 0, z0 + height * 0.5)
            else:
                _bm_cyl(bm, post_r, height, 16, x, 0, z0 + height * 0.5)
        elif style == 'WOOD':
            _bm_box(bm, post_w, post_w, height, x, 0, z0 + height * 0.5)
        else:
            _bm_box(bm, post_d, post_d, height, x, 0, z0 + height * 0.5)
    return xs

def _build_rails_metal(bm, xL, xR, height, rails, rail_r, rail_type='ROUND', rail_hollow=False, rail_hollow_thickness=0.01):
    if rails < 1: return
    if rails == 1: zs = [height * 0.6]
    elif rails == 2: zs = [height * 0.3, height * 0.7]
    elif rails == 3: zs = [height * 0.25, height * 0.5, height * 0.75]
    else: zs = [height * 0.2, height * 0.4, height * 0.6, height * 0.8]
    L, center_x = abs(xR - xL), (xL + xR) / 2
    for z in zs:
        if rail_type == 'SQUARE':
            _bm_box(bm, L, rail_r * 2, rail_r * 2, center_x, 0, z)
        elif rail_type == 'FLAT':
            _bm_box(bm, L, rail_r * 3, rail_r * 0.5, center_x, 0, z)
        else:
            if rail_hollow and rail_r > rail_hollow_thickness * 2:
                _bm_tube(bm, rail_r, rail_r - rail_hollow_thickness, L, 12, center_x, 0, z, 'X')
            else:
                _bm_cyl(bm, rail_r, L, 12, center_x, 0, z, 'X')

def _build_rails_wood(bm, xL, xR, height, rail_h, rail_t, rail_profile='RECTANGULAR'):
    L, center_x = abs(xR - xL), (xL + xR) / 2
    z1, z2 = height * 0.3, height * 0.7
    if rail_profile == 'ROUNDED':
        _bm_cyl(bm, rail_h * 0.5, L, 12, center_x, 0, z1, 'X')
        _bm_cyl(bm, rail_h * 0.5, L, 12, center_x, 0, z2, 'X')
    else:
        _bm_box(bm, L, rail_t, rail_h, center_x, 0, z1)
        _bm_box(bm, L, rail_t, rail_h, center_x, 0, z2)

def _build_rails_stone(bm, xL, xR, height, thickness, pattern='SOLID'):
    L, center_x = abs(xR - xL), (xL + xR) / 2
    panel_h, z = height * 0.8, height * 0.4
    if pattern == 'BRICKS':
        brick_h, brick_gap = 0.15, 0.01
        rows = int(panel_h / (brick_h + brick_gap))
        for row in range(rows):
            z_pos = (row * (brick_h + brick_gap)) + brick_h * 0.5
            if row % 2:
                offset = brick_h * 1.25
                half_brick_x = xL + offset * 0.5
                if half_brick_x < xR:
                    _bm_box(bm, offset - brick_gap, thickness, brick_h - brick_gap, half_brick_x, 0, z_pos)
                current_x = xL + offset
                while current_x + brick_h * 1.25 <= xR:
                    brick_x = current_x + brick_h * 1.25
                    _bm_box(bm, brick_h * 2.5 - brick_gap, thickness, brick_h - brick_gap, brick_x, 0, z_pos)
                    current_x += brick_h * 2.5
                remaining = xR - current_x
                if remaining > brick_gap * 2:
                    _bm_box(bm, remaining - brick_gap, thickness, brick_h - brick_gap, current_x + remaining * 0.5, 0, z_pos)
            else:
                brick_w = brick_h * 2.5
                num_bricks = max(1, int(L / brick_w))
                actual_brick_w = L / num_bricks
                for b in range(num_bricks):
                    brick_x = xL + (b * actual_brick_w) + actual_brick_w * 0.5
                    _bm_box(bm, actual_brick_w - brick_gap, thickness, brick_h - brick_gap, brick_x, 0, z_pos)
    else:
        _bm_box(bm, L, thickness, panel_h, center_x, 0, z)

def _build_pickets_metal(bm, xL, xR, height, count, width, gap, profile='ROUND'):
    span = abs(xR - xL)
    n = min(count, max(1, int(span / (width + gap))))
    if n < 1: return
    step = span / n
    picket_h, z_base = height * 0.75, height * 0.15
    for i in range(n):
        x = xL + step * (i + 0.5)
        if profile == 'SQUARE':
            _bm_box(bm, width, width, picket_h, x, 0, z_base + picket_h * 0.5)
        elif profile == 'SPEAR':
            body_h, point_h = picket_h * 0.85, picket_h * 0.15
            _bm_cyl(bm, width * 0.5, body_h, 12, x, 0, z_base + body_h * 0.5)
            _bm_cyl(bm, width * 0.3, point_h, 8, x, 0, z_base + body_h + point_h * 0.5)
        else:
            _bm_cyl(bm, width * 0.5, picket_h, 12, x, 0, z_base + picket_h * 0.5)

def _build_pickets_wood(bm, xL, xR, height, count, width, gap, profile='FLAT'):
    span = abs(xR - xL)
    n = min(count, max(1, int(span / (width + gap))))
    if n < 1: return
    step = span / n
    picket_h, z_base, thickness = height * 0.75, height * 0.15, width * 0.5
    for i in range(n):
        x = xL + step * (i + 0.5)
        if profile == 'PYRAMID':
            body_h = picket_h * 0.8
            _bm_box(bm, width, thickness, body_h, x, 0, z_base + body_h * 0.5)
            pyramid_h, sections = picket_h * 0.2, 4
            for j in range(sections):
                section_h = pyramid_h / sections
                t = (j + 1) / sections
                scale = 1.0 - (t * 0.8)
                section_z = z_base + body_h + (j * section_h) + section_h * 0.5
                _bm_box(bm, width * scale, thickness * scale, section_h, x, 0, section_z)
        elif profile == 'ROUNDED':
            body_h = picket_h * 0.85
            _bm_box(bm, width, thickness, body_h, x, 0, z_base + body_h * 0.5)
            cap_h, cap_sections = picket_h * 0.15, 3
            for j in range(cap_sections):
                section_h = cap_h / cap_sections
                t = (j + 1) / cap_sections
                scale = math.sqrt(1.0 - t ** 2)
                section_z = z_base + body_h + (j * section_h) + section_h * 0.5
                _bm_box(bm, width * scale, thickness * scale, section_h, x, 0, section_z)
        else:
            _bm_box(bm, width, thickness, picket_h, x, 0, z_base + picket_h * 0.5)

def _rotate_gate_vertices(bm, gate_verts, hinge_x, hinge_y, angle_deg):
    if abs(angle_deg) < 0.01: return
    rad = radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    for v in gate_verts:
        x, y, z = v.co.x - hinge_x, v.co.y - hinge_y, v.co.z
        new_x, new_y = x * cos_a - y * sin_a, x * sin_a + y * cos_a
        v.co.x, v.co.y, v.co.z = new_x + hinge_x, new_y + hinge_y, z

def _build_gate(bm, xL, xR, height, frame_t, gate_type, with_pickets, fence_type, picket_width, picket_gap, props, open_angle=0.0):
    L = abs(xR - xL)
    vert_count_before = len(bm.verts)
    if fence_type == 'STONE':
        _build_stone_gate(bm, xL, xR, height, frame_t, gate_type, props.stone_thickness)
    elif fence_type == 'METAL':
        _build_metal_gate(bm, xL, xR, height, frame_t, gate_type, with_pickets, picket_width, picket_gap, props.metal_rails, props.rail_radius)
    else:
        if gate_type == 'DOUBLE':
            gap = 0.05
            gate_w = (L - gap) * 0.5
            _build_wood_gate(bm, xL, xL + gate_w, height, frame_t, with_pickets, picket_width, picket_gap, props.wood_rail_h, props.wood_rail_t)
            _build_wood_gate(bm, xR - gate_w, xR, height, frame_t, with_pickets, picket_width, picket_gap, props.wood_rail_h, props.wood_rail_t)
        else:
            _build_wood_gate(bm, xL, xR, height, frame_t, with_pickets, picket_width, picket_gap, props.wood_rail_h, props.wood_rail_t)
    if abs(open_angle) > 0.01:
        bm.verts.ensure_lookup_table()
        gate_verts = [bm.verts[i] for i in range(vert_count_before, len(bm.verts))]
        if gate_type == 'DOUBLE':
            center_x = (xL + xR) * 0.5
            left_verts = [v for v in gate_verts if v.co.x < center_x]
            right_verts = [v for v in gate_verts if v.co.x >= center_x]
            _rotate_gate_vertices(bm, left_verts, xL, 0, -open_angle)
            _rotate_gate_vertices(bm, right_verts, xR, 0, open_angle)
        else:
            _rotate_gate_vertices(bm, gate_verts, xL, 0, open_angle)

def _build_wood_gate(bm, xL, xR, height, frame_t, with_pickets, picket_width, picket_gap, rail_h, rail_t):
    L = abs(xR - xL)
    center_x = (xL + xR) / 2
    gate_h = height * 0.8
    _bm_box(bm, L, frame_t, frame_t, center_x, 0, gate_h)
    _bm_box(bm, L, frame_t, frame_t, center_x, 0, height * 0.1)
    _bm_box(bm, frame_t, frame_t, gate_h - height * 0.1, xL, 0, (gate_h + height * 0.1) * 0.5)
    _bm_box(bm, frame_t, frame_t, gate_h - height * 0.1, xR, 0, (gate_h + height * 0.1) * 0.5)
    diag_width = L - frame_t * 2
    diag_height = gate_h - height * 0.1 - frame_t * 2
    diag_len = math.sqrt(diag_width ** 2 + diag_height ** 2)
    diag_angle = math.degrees(math.atan2(diag_height, diag_width))
    diag_cx, diag_cy, diag_cz = center_x, -frame_t * 0.3, (gate_h + height * 0.1) * 0.5
    _bm_rotated_box(bm, diag_len, frame_t * 0.7, frame_t * 0.7, diag_cx, diag_cy, diag_cz, diag_angle)
    if with_pickets and L > picket_width * 2:
        inner_L = L - frame_t * 2
        n = max(1, int(inner_L / (picket_width + picket_gap)))
        step = inner_L / n
        picket_h = gate_h - height * 0.1 - frame_t * 2
        for i in range(n):
            x = xL + frame_t + step * (i + 0.5)
            _bm_box(bm, picket_width, picket_width * 0.5, picket_h, x, 0, (gate_h + height * 0.1) * 0.5)

def _build_metal_gate(bm, xL, xR, height, frame_t, gate_type, with_pickets, picket_width, picket_gap, metal_rails, rail_radius):
    L = abs(xR - xL)
    
    if gate_type == 'DOUBLE':
        gap = 0.05
        gate_w = (L - gap) * 0.5
        _build_single_metal_gate(bm, xL, xL + gate_w, height, frame_t, with_pickets, picket_width, picket_gap, metal_rails, rail_radius)
        _build_single_metal_gate(bm, xR - gate_w, xR, height, frame_t, with_pickets, picket_width, picket_gap, metal_rails, rail_radius)
    else:
        _build_single_metal_gate(bm, xL, xR, height, frame_t, with_pickets, picket_width, picket_gap, metal_rails, rail_radius)

def _build_single_metal_gate(bm, xL, xR, height, frame_t, with_pickets, picket_width, picket_gap, metal_rails, rail_radius):
    L = abs(xR - xL)
    center_x = (xL + xR) / 2
    gate_h, gate_bottom = height * 0.85, height * 0.05
    frame_r = frame_t * 0.5
    top_rail_h = gate_h * 0.95
    segments, curve_depth = 16, L * 0.08
    for i in range(segments):
        t1, t2 = i / segments, (i + 1) / segments
        x1, x2 = xL + L * t1, xL + L * t2
        z1 = top_rail_h + curve_depth * (1 - 4 * (t1 - 0.5) ** 2)
        z2 = top_rail_h + curve_depth * (1 - 4 * (t2 - 0.5) ** 2)
        seg_len = math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)
        seg_cx, seg_cz = (x1 + x2) * 0.5, (z1 + z2) * 0.5
        angle = math.degrees(math.atan2(z2 - z1, x2 - x1))
        _bm_rotated_cyl(bm, frame_r, seg_len, seg_cx, 0, seg_cz, angle)
    _bm_cyl(bm, frame_r, L, 12, center_x, 0, gate_bottom, 'X')
    left_top_z = top_rail_h + curve_depth * 0.75
    right_top_z = top_rail_h + curve_depth * 0.75
    _bm_cyl(bm, frame_r, left_top_z - gate_bottom, 12, xL, 0, (left_top_z + gate_bottom) * 0.5)
    _bm_cyl(bm, frame_r, right_top_z - gate_bottom, 12, xR, 0, (right_top_z + gate_bottom) * 0.5)
    peak_z = top_rail_h + curve_depth
    scroll_h = 0.15
    _bm_cyl(bm, frame_r * 1.2, scroll_h, 8, center_x, 0, peak_z + scroll_h * 0.5)
    sphere_r = frame_r * 1.8
    _bm_cyl(bm, sphere_r, sphere_r * 0.8, 8, center_x, 0, peak_z + scroll_h + sphere_r * 0.4)
    scroll_offset = L * 0.25
    for x_off in [-scroll_offset, scroll_offset]:
        scroll_x = center_x + x_off
        scroll_z = top_rail_h + curve_depth * (1 - 4 * ((x_off / L) - 0.5 if x_off < 0 else (x_off / L) + 0.5) ** 2)
        _bm_cyl(bm, frame_r * 0.8, 0.08, 6, scroll_x, 0, scroll_z + 0.04)
    if with_pickets and L > picket_width * 2:
        inner_L = L - frame_r * 4
        n = max(3, int(inner_L / (picket_width + picket_gap)))
        step = inner_L / n
        for i in range(n):
            t = (i + 0.5) / n
            x = xL + frame_r * 2 + step * (i + 0.5)
            curve_top = top_rail_h + curve_depth * (1 - 4 * (t - 0.5) ** 2)
            picket_h = curve_top - gate_bottom - frame_r * 3
            body_h = picket_h * 0.88
            _bm_cyl(bm, picket_width * 0.4, body_h, 8, x, 0, gate_bottom + frame_r + body_h * 0.5)
            point_h = picket_h * 0.12
            _bm_cyl(bm, picket_width * 0.25, point_h, 6, x, 0, gate_bottom + frame_r + body_h + point_h * 0.5)

def _build_stone_gate(bm, xL, xR, height, frame_t, gate_type, stone_thickness):
    L = abs(xR - xL)
    center_x = (xL + xR) / 2
    
    if gate_type == 'DOUBLE':
        gap = 0.1
        gate_w = (L - gap) * 0.5
        _build_single_stone_gate(bm, xL, xL + gate_w, height, frame_t, stone_thickness)
        _build_single_stone_gate(bm, xR - gate_w, xR, height, frame_t, stone_thickness)
    else:
        _build_single_stone_gate(bm, xL, xR, height, frame_t, stone_thickness)

def _build_single_stone_gate(bm, xL, xR, height, frame_t, stone_thickness):
    L = abs(xR - xL)
    center_x = (xL + xR) / 2
    gate_h = height * 0.7
    arch_top = gate_h
    
    pillar_w = 0.25
    pillar_h = height * 0.9
    _bm_box(bm, pillar_w, stone_thickness * 1.5, pillar_h, cx=xL + pillar_w * 0.5, cy=0, cz=pillar_h * 0.5)
    _bm_box(bm, pillar_w, stone_thickness * 1.5, pillar_h, cx=xR - pillar_w * 0.5, cy=0, cz=pillar_h * 0.5)
    
    arch_segments = 12
    arch_width = L - pillar_w  
    arch_height = arch_width * 0.4
    arch_thickness = stone_thickness * 1.2
    
    for i in range(arch_segments):
        angle1 = math.pi * (i / arch_segments)
        angle2 = math.pi * ((i + 1) / arch_segments)
        
        inner_r = arch_width * 0.5
        x1_in = center_x - math.cos(angle1) * inner_r
        z1_in = gate_h + math.sin(angle1) * arch_height
        x2_in = center_x - math.cos(angle2) * inner_r
        z2_in = gate_h + math.sin(angle2) * arch_height
        
        outer_r = inner_r + arch_thickness
        x1_out = center_x - math.cos(angle1) * outer_r
        z1_out = gate_h + math.sin(angle1) * (arch_height + arch_thickness * 0.5)
        x2_out = center_x - math.cos(angle2) * outer_r
        z2_out = gate_h + math.sin(angle2) * (arch_height + arch_thickness * 0.5)
        
        seg_cx = (x1_in + x2_in + x1_out + x2_out) * 0.25
        seg_cz = (z1_in + z2_in + z1_out + z2_out) * 0.25
        seg_w = abs(x2_in - x1_in) + 0.05
        seg_h = arch_thickness * 0.8
        
        _bm_box(bm, seg_w, stone_thickness * 1.2, seg_h, cx=seg_cx, cy=0, cz=seg_cz)
    
    _bm_box(bm, 0.18, stone_thickness * 1.3, 0.25, cx=center_x, cy=0, cz=gate_h + arch_height)

def _build_corner_section(bm, x_start, length, height, angle, props):
    rad = radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    style = props.fence_type

    if style == 'METAL':
        _bm_cyl(bm, props.post_radius, height, 16, x_start, 0, height * 0.5)
    elif style == 'WOOD':
        _bm_box(bm, props.post_w, props.post_w, height, x_start, 0, height * 0.5)
    else:
        _bm_box(bm, props.post_d, props.post_d, height, x_start, 0, height * 0.5)

    end_x, end_y = x_start + length * cos_a, length * sin_a

    if style == 'METAL':
        _bm_cyl(bm, props.post_radius, height, 16, end_x, end_y, height * 0.5)
    elif style == 'WOOD':
        _bm_box(bm, props.post_w, props.post_w, height, end_x, end_y, height * 0.5)
    else:
        _bm_box(bm, props.post_d, props.post_d, height, end_x, end_y, height * 0.5)

    if style == 'METAL':
        if props.metal_rails >= 1:
            if props.metal_rails == 1: zs = [height * 0.6]
            elif props.metal_rails == 2: zs = [height * 0.3, height * 0.7]
            elif props.metal_rails == 3: zs = [height * 0.25, height * 0.5, height * 0.75]
            else: zs = [height * 0.2, height * 0.4, height * 0.6, height * 0.8]
            for z in zs:
                for seg in range(8):
                    t1, t2 = seg / 8, (seg + 1) / 8
                    x1, y1 = x_start + (length * t1) * cos_a, (length * t1) * sin_a
                    x2, y2 = x_start + (length * t2) * cos_a, (length * t2) * sin_a
                    seg_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    seg_cx, seg_cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
                    _bm_rotated_cyl(bm, props.rail_radius, seg_len, seg_cx, seg_cy, z, angle)
        if props.use_pickets:
            n = min(props.picket_count, max(1, int(length / (props.picket_width + props.picket_gap))))
            picket_h, z_base = height * 0.75, height * 0.15
            for i in range(1, n):
                t = i / n
                x, y = x_start + (length * t) * cos_a, (length * t) * sin_a
                _bm_cyl(bm, props.picket_width * 0.5, picket_h, 12, x, y, z_base + picket_h * 0.5)

    elif style == 'WOOD':
        z1, z2 = height * 0.3, height * 0.7
        for seg in range(8):
            t1, t2 = seg / 8, (seg + 1) / 8
            x1, y1 = x_start + (length * t1) * cos_a, (length * t1) * sin_a
            x2, y2 = x_start + (length * t2) * cos_a, (length * t2) * sin_a
            seg_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            seg_cx, seg_cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
            _bm_rotated_box(bm, seg_len, props.wood_rail_t, props.wood_rail_h, seg_cx, seg_cy, z1, angle)
            _bm_rotated_box(bm, seg_len, props.wood_rail_t, props.wood_rail_h, seg_cx, seg_cy, z2, angle)
        if props.use_pickets:
            n = min(props.picket_count, max(1, int(length / (props.picket_width + props.picket_gap))))
            picket_h, z_base = height * 0.75, height * 0.15
            thickness = props.picket_width * 0.5
            for i in range(1, n):
                t = i / n
                x, y = x_start + (length * t) * cos_a, (length * t) * sin_a
                _bm_box(bm, props.picket_width, thickness, picket_h, x, y, z_base + picket_h * 0.5)

    else:
        panel_h, z = height * 0.8, height * 0.4
        for seg in range(6):
            t1, t2 = seg / 6, (seg + 1) / 6
            x1, y1 = x_start + (length * t1) * cos_a, (length * t1) * sin_a
            x2, y2 = x_start + (length * t2) * cos_a, (length * t2) * sin_a
            seg_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            seg_cx, seg_cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
            _bm_rotated_box(bm, seg_len, props.stone_thickness, panel_h, seg_cx, seg_cy, z, angle)

def _bm_rotated_box(bm, length, width, height, cx, cy, cz, angle_deg):
    rad = radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    hx, hy, hz = length * 0.5, width * 0.5, height * 0.5
    
    local_verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)
    ]
    
    verts = []
    for lx, ly, lz in local_verts:
        rx = lx * cos_a - ly * sin_a
        ry = lx * sin_a + ly * cos_a
        verts.append(bm.verts.new((cx + rx, cy + ry, cz + lz)))
    
    faces = [
        [verts[0], verts[1], verts[2], verts[3]],  # bottom
        [verts[4], verts[7], verts[6], verts[5]],  # top
        [verts[0], verts[4], verts[5], verts[1]],  # front
        [verts[1], verts[5], verts[6], verts[2]],  # right
        [verts[2], verts[6], verts[7], verts[3]],  # back
        [verts[3], verts[7], verts[4], verts[0]],  # left
    ]
    for face_verts in faces:
        try:
            bm.faces.new(face_verts)
        except ValueError:
            pass

def _bm_rotated_cyl(bm, radius, length, cx, cy, cz, angle_deg):
    rad = radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    seg = 12
    angle_step = tau / seg
    half_len = length * 0.5
    
    bottom_verts = []
    top_verts = []
    
    for i in range(seg):
        ang = i * angle_step
        r_y = math.cos(ang) * radius
        r_z = math.sin(ang) * radius
        
        lx1, ly1 = -half_len, r_y
        lx2, ly2 = half_len, r_y
        
        rx1 = lx1 * cos_a - ly1 * sin_a
        ry1 = lx1 * sin_a + ly1 * cos_a
        rx2 = lx2 * cos_a - ly2 * sin_a
        ry2 = lx2 * sin_a + ly2 * cos_a
        
        bottom_verts.append(bm.verts.new((cx + rx1, cy + ry1, cz + r_z)))
        top_verts.append(bm.verts.new((cx + rx2, cy + ry2, cz + r_z)))
    
    bm.verts.ensure_lookup_table()
    
    for i in range(seg):
        v1 = bottom_verts[i]
        v2 = bottom_verts[(i + 1) % seg]
        v3 = top_verts[(i + 1) % seg]
        v4 = top_verts[i]
        try:
            bm.faces.new([v1, v2, v3, v4])
        except ValueError:
            pass
    
    try:
        bm.faces.new(bottom_verts[::-1])
        bm.faces.new(top_verts)
    except ValueError:
        pass

# ------------------------------------------------------------------------
# Main generation function
# ------------------------------------------------------------------------

def generate_fence(context):
    props = context.scene.fgen_props
    obj = context.active_object

    is_update = (
        obj
        and obj.type == 'MESH'
        and "fence_generator" in obj
        and obj.select_get()  
    )

    if is_update:
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.clear()
    else:
        obj = _new_mesh("Fence")
        obj["fence_generator"] = True
        mesh = obj.data
        bm = bmesh.new()
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

    length, height, section_len, style = props.length, props.height, props.section_len, props.fence_type
    num_sections = max(1, int(length / section_len))
    actual_section = length / num_sections
    current_x = 0.0

    for sec in range(num_sections):
        x0, x1 = current_x, current_x + actual_section
        is_gate = props.has_gate and sec == props.gate_index and sec < num_sections

        if is_gate:
            if style == 'METAL':
                _bm_cyl(bm, props.post_radius, height, 16, x0, 0, height * 0.5)
                _bm_cyl(bm, props.post_radius, height, 16, x1, 0, height * 0.5)
            elif style == 'WOOD':
                _bm_box(bm, props.post_w, props.post_w, height, x0, 0, height * 0.5)
                _bm_box(bm, props.post_w, props.post_w, height, x1, 0, height * 0.5)
            else:
                _bm_box(bm, props.post_d, props.post_d, height, x0, 0, height * 0.5)
                _bm_box(bm, props.post_d, props.post_d, height, x1, 0, height * 0.5)

            gate_w = props.gate_width
            gate_center = (x0 + x1) * 0.5
            gate_left = gate_center - gate_w * 0.5
            gate_right = gate_center + gate_w * 0.5

            if abs(gate_left - x0) > 0.01:
                if style == 'METAL':
                    _build_rails_metal(bm, x0, gate_left, height, props.metal_rails, props.rail_radius,
                                       props.metal_rail_type, props.metal_hollow, props.metal_hollow_thickness)
                    if props.use_pickets:
                        _build_pickets_metal(bm, x0, gate_left, height, props.picket_count,
                                             props.picket_width, props.picket_gap, props.metal_picket_profile)
                elif style == 'WOOD':
                    _build_rails_wood(bm, x0, gate_left, height, props.wood_rail_h, props.wood_rail_t, props.wood_rail_profile)
                    if props.use_pickets:
                        _build_pickets_wood(bm, x0, gate_left, height, props.picket_count,
                                            props.picket_width, props.picket_gap, props.wood_picket_profile)
                else:
                    _build_rails_stone(bm, x0, gate_left, height, props.stone_thickness, props.stone_pattern)

            if abs(x1 - gate_right) > 0.01:
                if style == 'METAL':
                    _build_rails_metal(bm, gate_right, x1, height, props.metal_rails, props.rail_radius,
                                       props.metal_rail_type, props.metal_hollow, props.metal_hollow_thickness)
                    if props.use_pickets:
                        _build_pickets_metal(bm, gate_right, x1, height, props.picket_count,
                                             props.picket_width, props.picket_gap, props.metal_picket_profile)
                elif style == 'WOOD':
                    _build_rails_wood(bm, gate_right, x1, height, props.wood_rail_h, props.wood_rail_t, props.wood_rail_profile)
                    if props.use_pickets:
                        _build_pickets_wood(bm, gate_right, x1, height, props.picket_count,
                                            props.picket_width, props.picket_gap, props.wood_picket_profile)
                else:
                    _build_rails_stone(bm, gate_right, x1, height, props.stone_thickness, props.stone_pattern)

            _build_gate(bm, gate_left, gate_right, height, props.gate_frame_t, props.gate_type,
                        props.gate_with_pickets, style, props.picket_width, props.picket_gap, props,
                        props.gate_open_angle)
        else:
            post_xs = _build_posts(bm, x0, x1, 0, height, actual_section, style, props.post_w, props.post_d,
                                   props.post_radius, props.metal_hollow, props.metal_hollow_thickness)
            if len(post_xs) >= 2:
                for i in range(len(post_xs) - 1):
                    xL, xR = post_xs[i], post_xs[i + 1]
                    if style == 'METAL':
                        _build_rails_metal(bm, xL, xR, height, props.metal_rails, props.rail_radius,
                                           props.metal_rail_type, props.metal_hollow, props.metal_hollow_thickness)
                    elif style == 'WOOD':
                        _build_rails_wood(bm, xL, xR, height, props.wood_rail_h, props.wood_rail_t, props.wood_rail_profile)
                    else:
                        _build_rails_stone(bm, xL, xR, height, props.stone_thickness, props.stone_pattern)
                    if props.use_pickets:
                        if style == 'METAL':
                            _build_pickets_metal(bm, xL, xR, height, props.picket_count,
                                                 props.picket_width, props.picket_gap, props.metal_picket_profile)
                        elif style == 'WOOD':
                            _build_pickets_wood(bm, xL, xR, height, props.picket_count,
                                                props.picket_width, props.picket_gap, props.wood_picket_profile)
        current_x = x1

    if props.corner_turn:
        corner_length = min(props.section_len, props.length * 0.3)
        _build_corner_section(bm, current_x, corner_length, height, props.corner_angle, props)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------------------------
# Live Update
# ------------------------------------------------------------------------

def update_fence(self, context):
    props = context.scene.fgen_props
    if not props.live_update:
        return
        
    obj = context.active_object
    if obj and obj.type == 'MESH' and "fence_generator" in obj and obj.select_get():
        generate_fence(context)

# ------------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------------

class FGProperties(bpy.types.PropertyGroup):
    
    # Live update
    live_update: BoolProperty(name="Live Update", description="Automatically update fence when parameters change", default=False)

    # Fence base
    fence_type: EnumProperty(name="Fence Type", items=[('METAL',"Metal","Metal fence with round/square posts and rails"),('WOOD',"Wood","Wooden fence with rectangular posts and rails"),('STONE',"Stone","Stone fence with thick panels")], default='METAL', update=update_fence)
    length: FloatProperty(name="Total Length", default=10.0, min=0.5, max=100.0, subtype='DISTANCE', update=update_fence)
    height: FloatProperty(name="Height", default=1.8, min=0.3, max=5.0, subtype='DISTANCE', update=update_fence)
    section_len: FloatProperty(name="Section Length", default=2.0, min=0.5, max=10.0, subtype='DISTANCE', update=update_fence)

    # Metal
    post_radius: FloatProperty(name="Post Radius", default=0.04, min=0.01, max=0.2, subtype='DISTANCE', update=update_fence)
    metal_rails: IntProperty(name="Number of Rails", default=2, min=0, max=4, update=update_fence)
    rail_radius: FloatProperty(name="Rail Radius", default=0.02, min=0.005, max=0.1, subtype='DISTANCE', update=update_fence)
    metal_rail_type: EnumProperty(name="Rail Type", items=[('ROUND',"Round","Cylindrical rails"),('SQUARE',"Square","Square profile rails"),('FLAT',"Flat","Flat bar rails")], default='ROUND', update=update_fence)
    metal_hollow: BoolProperty(name="Hollow Metal", description="Make metal posts and rails hollow (tubes)", default=False, update=update_fence)
    metal_hollow_thickness: FloatProperty(name="Wall Thickness", default=0.004, min=0.001, max=0.05, subtype='DISTANCE', update=update_fence)
    metal_picket_profile: EnumProperty(name="Picket Profile", items=[('ROUND',"Round","Round pickets"),('SQUARE',"Square","Square pickets"),('SPEAR',"Spear","Spear-tip pickets")], default='ROUND', update=update_fence)

    # Wood
    post_w: FloatProperty(name="Post Width", default=0.1, min=0.02, max=0.3, subtype='DISTANCE', update=update_fence)
    wood_rail_h: FloatProperty(name="Rail Height", default=0.1, min=0.02, max=0.3, subtype='DISTANCE', update=update_fence)
    wood_rail_t: FloatProperty(name="Rail Thickness", default=0.03, min=0.01, max=0.1, subtype='DISTANCE', update=update_fence)
    wood_rail_profile: EnumProperty(name="Rail Profile", items=[('RECTANGULAR',"Rectangular","Rectangular rails"),('ROUNDED',"Rounded","Rounded/cylindrical rails")], default='RECTANGULAR', update=update_fence)
    wood_picket_profile: EnumProperty(name="Picket Style", items=[('FLAT',"Flat Top","Flat top pickets"),('PYRAMID',"Pyramid Top","Pyramid top pickets"),('ROUNDED',"Rounded Top","Rounded top pickets")], default='FLAT', update=update_fence)

    # Stone
    post_d: FloatProperty(name="Post Depth", default=0.3, min=0.1, max=0.8, subtype='DISTANCE', update=update_fence)
    stone_thickness: FloatProperty(name="Stone Panel Thickness", default=0.18, min=0.05, max=0.6, subtype='DISTANCE', update=update_fence)
    stone_pattern: EnumProperty(name="Stone Pattern", items=[('SOLID',"Solid","Solid stone wall"),('BRICKS',"Bricks","Brick pattern")], default='SOLID', update=update_fence)

    # Pickets
    use_pickets: BoolProperty(name="Use Vertical Pickets", default=False, update=update_fence)
    picket_count: IntProperty(name="Pickets (max)", default=10, min=1, max=100, update=update_fence)
    picket_width: FloatProperty(name="Picket Width", default=0.08, min=0.01, max=0.2, subtype='DISTANCE', update=update_fence)
    picket_gap: FloatProperty(name="Picket Gap", default=0.05, min=0.0, max=0.2, subtype='DISTANCE', update=update_fence)

    # Gate
    has_gate: BoolProperty(name="Add Gate", default=False, update=update_fence)
    gate_width: FloatProperty(name="Gate Width", default=1.2, min=0.5, max=5.0, subtype='DISTANCE', update=update_fence)
    gate_frame_t: FloatProperty(name="Gate Frame Thickness", default=0.06, min=0.02, max=0.2, subtype='DISTANCE', update=update_fence)
    gate_with_pickets: BoolProperty(name="Gate Infill Pickets", default=True, update=update_fence)
    gate_index: IntProperty(name="Gate Span Index", description="Which section to replace with a gate (0 = first section)", default=0, min=0, max=999, update=update_fence)
    gate_type: EnumProperty(name="Gate Type", items=[('SINGLE',"Single","Single gate panel"),('DOUBLE',"Double","Double gate (opens in middle)")], default='SINGLE', update=update_fence)
    gate_open_angle: FloatProperty(name="Gate Opening", description="Rotation angle to open the gate", default=0.0, min=-120.0, max=120.0, subtype='NONE', update=update_fence)

    # Corner
    corner_turn: BoolProperty(name="Add Corner", description="Add a corner turn at the end of the fence", default=False, update=update_fence)
    corner_angle: FloatProperty(name="Corner Angle", default=90.0, min=-180.0, max=180.0, subtype='ANGLE', update=update_fence)

# ------------------------------------------------------------------------
# Operators
# ------------------------------------------------------------------------

class FG_OT_generate(bpy.types.Operator):
    bl_idname = "fg.generate"
    bl_label = "Generate Fence"
    bl_description = "Create/Update a parametric fence"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        try:
            generate_fence(context)
            self.report({'INFO'}, "Fence generated successfully")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate fence: {str(e)}")
            return {'CANCELLED'}

class FG_OT_delete_fence(bpy.types.Operator):
    bl_idname = "fg.delete_fence"
    bl_label = "Delete Fence"
    bl_description = "Delete the selected fence object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH' or "fence_generator" not in obj:
            self.report({'WARNING'}, "No fence object selected")
            return {'CANCELLED'}
        
        bpy.data.objects.remove(obj, do_unlink=True)
        
        self.report({'INFO'}, "Fence deleted")
        return {'FINISHED'}
    
class FG_OT_reset_settings(bpy.types.Operator):
    bl_idname = "fg.reset_settings"
    bl_label = "Reset Settings"
    bl_description = "Reset all parameters to default values"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.fgen_props
        live_state = props.live_update  

        for prop_name, prop in props.bl_rna.properties.items():
            if not prop.is_readonly and prop.identifier != "rna_type":
                default_value = prop.default
                try:
                    setattr(props, prop.identifier, default_value)
                except Exception:
                    pass

        props.live_update = live_state

        if props.live_update:
            try:
                from bpy import context as ctx
                obj = ctx.active_object
                if obj and obj.type == "MESH" and "fence_generator" in obj:
                    generate_fence(ctx)
            except Exception as e:
                self.report({'WARNING'}, f"Live update failed: {e}")

        self.report({'INFO'}, "Fence Generator settings reset")
        return {'FINISHED'}

# ------------------------------------------------------------------------
# UI
# ------------------------------------------------------------------------

class VIEW3D_PT_fence_generator(bpy.types.Panel):
    bl_label = "Fence"
    bl_idname = "VIEW3D_PT_fence_generator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fence" 
    
    def draw(self, context):
        if relay_updater:
            relay_updater.draw(self.layout)
        layout = self.layout
        p = context.scene.fgen_props
        o = context.object

        layout.operator("fg.generate", text="Generate Fence", icon="LONGDISPLAY")

        row = layout.row(align=True)
        row.prop(p, "live_update", toggle=True)
        row.operator("fg.reset_settings", text="Reset", icon="LOOP_BACK")

        layout.separator(factor=0.5)

        layout.prop(p, "fence_type", expand=True)

        if p.fence_type == 'METAL':
            layout.row(align=True).prop(p, "metal_rail_type", expand=True)
        elif p.fence_type == 'WOOD':
            layout.row(align=True).prop(p, "wood_rail_profile", expand=True)
        else:
            layout.row(align=True).prop(p, "stone_pattern", expand=True)

        layout.separator(factor=0.5)

        col = layout.column(align=True)
        col.prop(p, "length", slider=True)
        col.prop(p, "height", slider=True)
        col.prop(p, "section_len", slider=True)

        layout.separator(factor=0.5)

        if p.fence_type == 'METAL':
            col = layout.column(align=True)
            col.prop(p, "post_radius", slider=True)
            col.prop(p, "metal_rails", slider=True)
            col.prop(p, "rail_radius", slider=True)

            col.separator(factor=0.5)
            col.prop(p, "metal_hollow", toggle=True)

            if p.metal_hollow:
                col.prop(p, "metal_hollow_thickness", slider=True)

        elif p.fence_type == 'WOOD':
            col = layout.column(align=True)
            col.prop(p, "post_w", slider=True)
            col.prop(p, "wood_rail_h", slider=True)
            col.prop(p, "wood_rail_t", slider=True)

        elif p.fence_type == 'STONE':
            col = layout.column(align=True)
            col.prop(p, "post_d", slider=True)
            col.prop(p, "stone_thickness", slider=True)

        if p.fence_type != 'STONE':
            layout.prop(p, "use_pickets", toggle=True)

            if p.use_pickets:
                sub = layout.column(align=True)

                if p.fence_type == 'METAL':
                    sub.row(align=True).prop(p, "metal_picket_profile", expand=True)
                else:
                    sub.row(align=True).prop(p, "wood_picket_profile", expand=True)

                sub.prop(p, "picket_count", slider=True)
                sub.prop(p, "picket_width", slider=True)
                sub.prop(p, "picket_gap", slider=True)

        layout.prop(p, "has_gate", toggle=True)

        if p.has_gate:
            sub = layout.column(align=True)

            sub.row(align=True).prop(p, "gate_type", expand=True)
            sub.prop(p, "gate_width", slider=True)
            sub.prop(p, "gate_frame_t", slider=True)
            sub.prop(p, "gate_with_pickets", toggle=True)
            sub.prop(p, "gate_index", slider=True)
            sub.prop(p, "gate_open_angle", slider=True)

        layout.prop(p, "corner_turn", toggle=True)

        if p.corner_turn:
            layout.prop(p, "corner_angle", slider=True)

        layout.separator(factor=0.5)

        if o and o.type == "MESH" and "fence_generator" in o and o.select_get():
            layout.operator("fg.delete_fence", text="Delete Fence", icon="TRASH")
            layout.separator(factor=0.3)
            layout.label(text=f"Editing: {o.name}", icon="LONGDISPLAY")
        else:
            layout.label(text="No fence selected", icon="INFO")

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

classes = (
    FGProperties,
    FG_OT_generate,
    FG_OT_delete_fence,
    FG_OT_reset_settings, 
    VIEW3D_PT_fence_generator, 
)

def register():
    if relay_updater:
        relay_updater.register("blender-fence")
    """Register addon classes and properties"""
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fgen_props = bpy.props.PointerProperty(type=FGProperties)

def unregister():
    if relay_updater:
        relay_updater.unregister()
    """Unregister addon classes and properties"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, 'fgen_props'):
        del bpy.types.Scene.fgen_props

if __name__ == "__main__":
    register()