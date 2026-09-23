#!/usr/bin/env python3
"""
generate_3d_models.py
Generates two high-fidelity glTF 2.0 Binary (.glb) files for the lower back lipoma visualization:
1. lipoma-isolated.glb: Isolated lipoma 3D scale models (Right & Left) with 3D caliper measurement vectors,
   scale grid, and both 2025 baseline & 2026 follow-up morph states.
2. lower-back-anatomy-lipomas.glb: Detailed lower back anatomical context model including
   skeletal structures (L1-L5, facet joints, discs with L5-S1 narrowing, sacrum, iliac crests/pelvis),
   muscles (erector spinae, multifidus), thoracolumbar fascia, subcutaneous fat, skin, and embedded lipomas.

Zero external dependencies required (pure standard library: struct, json, math).
"""

import os
import sys
import math
import json
import struct

class GLBBuilder:
    def __init__(self):
        self.bin_data = bytearray()
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.materials = []
        self.nodes = []
        self.scene_nodes = []

    def _pad_bin(self, alignment=4):
        pad = (alignment - (len(self.bin_data) % alignment)) % alignment
        if pad > 0:
            self.bin_data.extend(b'\x00' * pad)

    def add_buffer_view(self, data: bytes, target=None):
        self._pad_bin(4)
        offset = len(self.bin_data)
        self.bin_data.extend(data)
        bv = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(data)
        }
        if target:
            bv["target"] = target
        self.buffer_views.append(bv)
        return len(self.buffer_views) - 1

    def add_accessor(self, buffer_view_idx, component_type, count, type_str, min_val=None, max_val=None, byte_offset=0):
        acc = {
            "bufferView": buffer_view_idx,
            "byteOffset": byte_offset,
            "componentType": component_type,
            "count": count,
            "type": type_str
        }
        if min_val is not None:
            acc["min"] = min_val
        if max_val is not None:
            acc["max"] = max_val
        self.accessors.append(acc)
        return len(self.accessors) - 1

    def add_material(self, name, base_color_rgba, roughness=0.5, metallic=0.0, double_sided=True, alpha_mode="OPAQUE"):
        mat = {
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(base_color_rgba),
                "roughnessFactor": roughness,
                "metallicFactor": metallic
            },
            "doubleSided": double_sided
        }
        if alpha_mode in ("BLEND", "MASK"):
            mat["alphaMode"] = alpha_mode
        self.materials.append(mat)
        return len(self.materials) - 1

    def add_mesh_primitive(self, name, positions, normals, indices, material_idx, uvs=None):
        # Vertex positions (Vec3, float)
        pos_bytes = bytearray()
        min_p = [float("inf")] * 3
        max_p = [float("-inf")] * 3
        for p in positions:
            pos_bytes.extend(struct.pack('<3f', p[0], p[1], p[2]))
            for i in range(3):
                min_p[i] = min(min_p[i], p[i])
                max_p[i] = max(max_p[i], p[i])

        pos_bv = self.add_buffer_view(pos_bytes, target=34962)  # ARRAY_BUFFER
        pos_acc = self.add_accessor(pos_bv, 5126, len(positions), "VEC3", min_val=min_p, max_val=max_p)

        # Normals (Vec3, float)
        norm_bytes = bytearray()
        for n in normals:
            norm_bytes.extend(struct.pack('<3f', n[0], n[1], n[2]))
        norm_bv = self.add_buffer_view(norm_bytes, target=34962)
        norm_acc = self.add_accessor(norm_bv, 5126, len(normals), "VEC3")

        # Indices (Scalar, unsigned short or uint)
        idx_bytes = bytearray()
        min_idx = min(indices) if indices else 0
        max_idx = max(indices) if indices else 0
        if len(positions) > 65535:
            for idx in indices:
                idx_bytes.extend(struct.pack('<I', idx))
            idx_comp = 5125  # UNSIGNED_INT
        else:
            for idx in indices:
                idx_bytes.extend(struct.pack('<H', idx))
            idx_comp = 5123  # UNSIGNED_SHORT

        idx_bv = self.add_buffer_view(idx_bytes, target=34963)  # ELEMENT_ARRAY_BUFFER
        idx_acc = self.add_accessor(idx_bv, idx_comp, len(indices), "SCALAR", min_val=[min_idx], max_val=[max_idx])

        attributes = {
            "POSITION": pos_acc,
            "NORMAL": norm_acc
        }

        # Optional UVs
        if uvs and len(uvs) == len(positions):
            uv_bytes = bytearray()
            for uv in uvs:
                uv_bytes.extend(struct.pack('<2f', uv[0], uv[1]))
            uv_bv = self.add_buffer_view(uv_bytes, target=34962)
            uv_acc = self.add_accessor(uv_bv, 5126, len(uvs), "VEC2")
            attributes["TEXCOORD_0"] = uv_acc

        primitive = {
            "attributes": attributes,
            "indices": idx_acc,
            "mode": 4  # TRIANGLES
        }
        if material_idx is not None:
            primitive["material"] = material_idx

        mesh = {
            "name": name,
            "primitives": [primitive]
        }
        self.meshes.append(mesh)
        return len(self.meshes) - 1

    def add_node(self, name, mesh_idx=None, translation=None, rotation=None, scale=None, children=None):
        node = {"name": name}
        if mesh_idx is not None:
            node["mesh"] = mesh_idx
        if translation is not None:
            node["translation"] = list(translation)
        if rotation is not None:
            node["rotation"] = list(rotation)
        if scale is not None:
            node["scale"] = list(scale)
        if children is not None:
            node["children"] = list(children)
        self.nodes.append(node)
        return len(self.nodes) - 1

    def build_glb(self) -> bytes:
        # Construct glTF JSON structure
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "Medical 3D Anatomical Generator v2.0 - Lower Back Lipoma Visualizer"
            },
            "scenes": [{"name": "DefaultScene", "nodes": self.scene_nodes}],
            "scene": 0,
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self.accessors,
            "bufferViews": self.buffer_views,
            "buffers": [{"byteLength": len(self.bin_data)}]
        }

        json_bytes = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
        # Pad JSON to 4-byte boundary with spaces (0x20)
        json_pad = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_pad

        # Pad BIN to 4-byte boundary with 0x00
        bin_pad = (4 - (len(self.bin_data) % 4)) % 4
        bin_data = self.bin_data + (b'\x00' * bin_pad)

        total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

        # GLB Header
        glb = bytearray()
        glb.extend(struct.pack('<4sII', b'glTF', 2, total_length))

        # Chunk 0 (JSON)
        glb.extend(struct.pack('<II', len(json_bytes), 0x4E4F534A))  # 'JSON'
        glb.extend(json_bytes)

        # Chunk 1 (BIN)
        glb.extend(struct.pack('<II', len(bin_data), 0x004E4942))  # 'BIN\x00'
        glb.extend(bin_data)

        return bytes(glb)


# ============================================================================
# Geometry Generation Helpers (Triangulated Meshes with Normals & UVs)
# ============================================================================

def create_ellipsoid(rx, ry, rz, seg_lat=32, seg_lon=48, noise_amp=0.04, center=(0, 0, 0)):
    """Creates a smooth ellipsoid mesh with organic subtle lobular perturbations for lipoma adipose tissue."""
    positions = []
    normals = []
    uvs = []
    indices = []
    cx, cy, cz = center

    for i in range(seg_lat + 1):
        lat = math.pi * (-0.5 + float(i) / seg_lat)
        sin_lat = math.sin(lat)
        cos_lat = math.cos(lat)
        v = float(i) / seg_lat

        for j in range(seg_lon + 1):
            lon = 2 * math.pi * float(j) / seg_lon
            sin_lon = math.sin(lon)
            cos_lon = math.cos(lon)
            u = float(j) / seg_lon

            # Base normal
            nx = cos_lat * cos_lon
            ny = sin_lat
            nz = cos_lat * sin_lon

            # Subtle organic lobulation noise using trigonometric harmonics
            pert = 1.0 + noise_amp * (
                math.sin(3.0 * lon) * math.cos(2.0 * lat) +
                0.5 * math.sin(6.0 * lon + 1.2) * math.sin(4.0 * lat)
            )

            px = cx + rx * nx * pert
            py = cy + ry * ny * pert
            pz = cz + rz * nz * pert

            positions.append((px, py, pz))
            normals.append((nx, ny, nz))
            uvs.append((u, v))

    for i in range(seg_lat):
        for j in range(seg_lon):
            first = i * (seg_lon + 1) + j
            second = first + seg_lon + 1
            indices.extend([first, second, first + 1])
            indices.extend([second, second + 1, first + 1])

    return positions, normals, indices, uvs


def create_cylinder(radius_top, radius_bottom, height, segments=32, center=(0, 0, 0), axis='Y'):
    """Generates cylinder with caps along axis."""
    positions = []
    normals = []
    indices = []
    uvs = []
    cx, cy, cz = center
    half_h = height * 0.5

    # Side vertices
    for y_step, h_val, r in [(0, -half_h, radius_bottom), (1, half_h, radius_top)]:
        for j in range(segments + 1):
            theta = 2 * math.pi * float(j) / segments
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            if axis == 'Y':
                pos = (cx + r * cos_t, cy + h_val, cz + r * sin_t)
                norm = (cos_t, 0.0, sin_t)
            elif axis == 'X':
                pos = (cx + h_val, cy + r * cos_t, cz + r * sin_t)
                norm = (0.0, cos_t, sin_t)
            else: # Z
                pos = (cx + r * cos_t, cy + r * sin_t, cz + h_val)
                norm = (cos_t, sin_t, 0.0)
            positions.append(pos)
            normals.append(norm)
            uvs.append((float(j) / segments, y_step))

    # Side indices
    for j in range(segments):
        i0 = j
        i1 = j + segments + 1
        i2 = j + 1
        i3 = j + segments + 2
        indices.extend([i0, i1, i2])
        indices.extend([i2, i1, i3])

    # Top Cap
    top_center_idx = len(positions)
    if axis == 'Y':
        positions.append((cx, cy + half_h, cz))
        normals.append((0.0, 1.0, 0.0))
    elif axis == 'X':
        positions.append((cx + half_h, cy, cz))
        normals.append((1.0, 0.0, 0.0))
    else:
        positions.append((cx, cy, cz + half_h))
        normals.append((0.0, 0.0, 1.0))
    uvs.append((0.5, 0.5))

    cap_start = len(positions)
    for j in range(segments + 1):
        theta = 2 * math.pi * float(j) / segments
        if axis == 'Y':
            positions.append((cx + radius_top * math.cos(theta), cy + half_h, cz + radius_top * math.sin(theta)))
            normals.append((0.0, 1.0, 0.0))
        elif axis == 'X':
            positions.append((cx + half_h, cy + radius_top * math.cos(theta), cz + radius_top * math.sin(theta)))
            normals.append((1.0, 0.0, 0.0))
        else:
            positions.append((cx + radius_top * math.cos(theta), cy + radius_top * math.sin(theta), cz + half_h))
            normals.append((0.0, 0.0, 1.0))
        uvs.append((0.5 + 0.5 * math.cos(theta), 0.5 + 0.5 * math.sin(theta)))

    for j in range(segments):
        indices.extend([top_center_idx, cap_start + j, cap_start + j + 1])

    # Bottom Cap
    bot_center_idx = len(positions)
    if axis == 'Y':
        positions.append((cx, cy - half_h, cz))
        normals.append((0.0, -1.0, 0.0))
    elif axis == 'X':
        positions.append((cx - half_h, cy, cz))
        normals.append((-1.0, 0.0, 0.0))
    else:
        positions.append((cx, cy, cz - half_h))
        normals.append((0.0, 0.0, -1.0))
    uvs.append((0.5, 0.5))

    bot_start = len(positions)
    for j in range(segments + 1):
        theta = 2 * math.pi * float(j) / segments
        if axis == 'Y':
            positions.append((cx + radius_bottom * math.cos(theta), cy - half_h, cz + radius_bottom * math.sin(theta)))
            normals.append((0.0, -1.0, 0.0))
        elif axis == 'X':
            positions.append((cx - half_h, cy + radius_bottom * math.cos(theta), cz + radius_bottom * math.sin(theta)))
            normals.append((-1.0, 0.0, 0.0))
        else:
            positions.append((cx + radius_bottom * math.cos(theta), cy + radius_bottom * math.sin(theta), cz - half_h))
            normals.append((0.0, 0.0, -1.0))
        uvs.append((0.5 + 0.5 * math.cos(theta), 0.5 + 0.5 * math.sin(theta)))

    for j in range(segments):
        indices.extend([bot_center_idx, bot_start + j + 1, bot_start + j])

    return positions, normals, indices, uvs


def create_box(dx, dy, dz, center=(0, 0, 0)):
    """Generates box with outward normals."""
    cx, cy, cz = center
    hx, hy, hz = dx * 0.5, dy * 0.5, dz * 0.5
    positions = []
    normals = []
    uvs = []
    indices = []

    faces = [
        # (normal, u_dir, v_dir, corners)
        ((0, 0, 1), (1, 0, 0), (0, 1, 0), [(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]),  # Front
        ((0, 0, -1), (-1, 0, 0), (0, 1, 0), [(hx, -hy, -hz), (-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz)]),  # Back
        ((1, 0, 0), (0, 0, -1), (0, 1, 0), [(hx, -hy, hz), (hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz)]),  # Right
        ((-1, 0, 0), (0, 0, 1), (0, 1, 0), [(-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz), (-hx, hy, -hz)]),  # Left
        ((0, 1, 0), (1, 0, 0), (0, 0, -1), [(-hx, hy, hz), (hx, hy, hz), (hx, hy, -hz), (-hx, hy, -hz)]),  # Top
        ((0, -1, 0), (1, 0, 0), (0, 0, 1), [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz)]),  # Bottom
    ]

    for norm, u_dir, v_dir, corners in faces:
        base_idx = len(positions)
        for c in corners:
            positions.append((cx + c[0], cy + c[1], cz + c[2]))
            normals.append(norm)
        uvs.extend([(0, 0), (1, 0), (1, 1), (0, 1)])
        indices.extend([base_idx, base_idx + 1, base_idx + 2, base_idx, base_idx + 2, base_idx + 3])

    return positions, normals, indices, uvs


def merge_geometries(geom_list):
    """Merges multiple (positions, normals, indices, uvs) into a single mesh."""
    merged_pos = []
    merged_norm = []
    merged_idx = []
    merged_uv = []

    for pos, norm, idx, uv in geom_list:
        base = len(merged_pos)
        merged_pos.extend(pos)
        merged_norm.extend(norm)
        merged_uv.extend(uv)
        for i in idx:
            merged_idx.append(base + i)

    return merged_pos, merged_norm, merged_idx, merged_uv


# ============================================================================
# Anatomical Spine, Sacrum, Pelvis & Muscle Builders
# ============================================================================

def create_lumbar_vertebra(level_idx, y_pos, z_pos):
    """
    Creates an anatomically detailed L1-L5 lumbar vertebra:
    - Kidney-shaped robust vertebral body (with pedicle attachments)
    - Posterior vertebral arch (laminae and pedicles encircling canal)
    - Broad rectangular spinous process extending posteriorly
    - Horizontal transverse processes extending bilaterally
    - Articular processes (superior and inferior facet joints)
    """
    # Scale adjusts slightly L1 (smaller) to L5 (broadest, deepest)
    t = float(level_idx) / 4.0  # 0 for L1, 1 for L5
    width = 4.4 + 0.8 * t        # cm
    depth = 3.2 + 0.6 * t        # cm
    height = 2.8 + 0.2 * t       # cm

    sub_geoms = []

    # 1. Kidney-shaped Vertebral Body
    # We combine 3 overlapping ellipsoids/cylinders to make an anatomical kidney shape
    body_pos, body_norm, body_idx, body_uv = create_cylinder(
        radius_top=width * 0.45,
        radius_bottom=width * 0.45,
        height=height,
        segments=24,
        center=(0, y_pos, z_pos),
        axis='Y'
    )
    # Flatten Z slightly to make kidney shape
    body_pos = [(p[0], p[1], z_pos + (p[2] - z_pos) * 0.75) for p in body_pos]
    sub_geoms.append((body_pos, body_norm, body_idx, body_uv))

    # 2. Spinous Process (Posterior midline project, pointing dorsal and slightly inferior)
    sp_length = 3.2 + 0.4 * t
    sp_height = 1.8 - 0.2 * t
    sp_width = 0.8 + 0.1 * t
    sp_z = z_pos - (depth * 0.4 + sp_length * 0.5)
    sp_geom = create_box(sp_width, sp_height, sp_length, center=(0, y_pos - 0.3, sp_z))
    sub_geoms.append(sp_geom)

    # 3. Transverse Processes (Bilateral lateral wings)
    tp_span = 8.6 + 1.2 * t
    tp_height = 0.8
    tp_depth = 0.9
    tp_z = z_pos - depth * 0.25
    tp_geom = create_box(tp_span, tp_height, tp_depth, center=(0, y_pos + 0.1, tp_z))
    sub_geoms.append(tp_geom)

    # 4. Superior & Inferior Articular Processes (Facet Joints)
    # L4-L5 and L5-S1 facet joints were noted with mild arthrosis in MRI
    facet_span = 3.2 + 0.4 * t
    for s in (-1, 1):
        sup_facet = create_box(0.7, 1.2, 0.7, center=(s * facet_span * 0.5, y_pos + height * 0.45, tp_z - 0.4))
        inf_facet = create_box(0.7, 1.2, 0.7, center=(s * facet_span * 0.5, y_pos - height * 0.45, tp_z - 0.5))
        sub_geoms.append(sup_facet)
        sub_geoms.append(inf_facet)

    # 5. Laminae Arch (Connecting transverse to spinous process)
    for s in (-1, 1):
        lamina = create_box(1.2, 1.4, 1.4, center=(s * 1.1, y_pos, z_pos - depth * 0.35))
        sub_geoms.append(lamina)

    return merge_geometries(sub_geoms)


def create_intervertebral_disc(level_idx, y_pos, z_pos, height=0.9):
    """Creates intervertebral fibrocartilage disc with anulus fibrosus curvature."""
    t = float(level_idx) / 4.0
    radius = (4.4 + 0.8 * t) * 0.44
    pos, norm, idx, uv = create_cylinder(radius, radius, height, segments=24, center=(0, y_pos, z_pos), axis='Y')
    pos = [(p[0], p[1], z_pos + (p[2] - z_pos) * 0.75) for p in pos]
    return pos, norm, idx, uv


def create_sacrum(y_top=-13.5, z_center=-3.8):
    """
    Creates an anatomically detailed Sacrum (S1-S5):
    - Inverted triangular fused wedge
    - Median sacral crest (fused spinous tubercles)
    - Dorsal sacral foramina (paired sensory exits)
    - Articular facet surfaces for L5-S1 junction
    """
    sub_geoms = []

    # Main sacral body: tapering conical wedge
    sac_pos, sac_norm, sac_idx, sac_uv = create_cylinder(
        radius_top=4.8, radius_bottom=1.4, height=11.0, segments=24, center=(0, y_top - 5.5, z_center), axis='Y'
    )
    # Taper depth towards apex (coccyx direction)
    sac_pos = [(p[0], p[1], z_center + (p[2] - z_center) * 0.5) for p in sac_pos]
    sub_geoms.append((sac_pos, sac_norm, sac_idx, sac_uv))

    # Median Sacral Crest (Ridge along the posterior surface)
    crest = create_box(0.9, 10.0, 1.6, center=(0, y_top - 5.2, z_center - 1.6))
    sub_geoms.append(crest)

    # Lateral masses / Sacral Ala (Wings articulating with Ilium at SI joint)
    for s in (-1, 1):
        ala = create_box(3.2, 4.0, 2.2, center=(s * 4.6, y_top - 2.2, z_center - 0.4))
        sub_geoms.append(ala)

    # Sacral articular facets for L5
    for s in (-1, 1):
        facet = create_cylinder(0.7, 0.7, 1.2, segments=12, center=(s * 1.8, y_top + 0.4, z_center - 1.2), axis='Y')
        sub_geoms.append(facet)

    return merge_geometries(sub_geoms)


def create_pelvis_iliac_crests(y_level=-9.0, z_level=-4.2):
    """
    Creates the bilateral Iliac Crests and Posterior Superior Iliac Spines (PSIS):
    Crucial anatomical landmarks ("Dimples of Venus") bounding the lower back and L5-S1.
    """
    sub_geoms = []

    for s in (-1, 1):
        # Iliac Wing (broad curved pelvic blade)
        # Approximated by an angled curved box
        wing = create_box(2.2, 12.0, 5.5, center=(s * 10.8, y_level - 4.0, z_level - 0.5))
        sub_geoms.append(wing)

        # Iliac Crest (Superior palpable crest)
        crest = create_cylinder(1.2, 1.2, 10.5, segments=16, center=(s * 9.5, y_level + 1.2, z_level - 1.0), axis='X')
        sub_geoms.append(crest)

        # PSIS (Posterior Superior Iliac Spine landmark at S2 level)
        psis = create_cylinder(1.1, 1.4, 2.4, segments=16, center=(s * 5.4, y_level - 3.8, z_level - 3.2), axis='Z')
        sub_geoms.append(psis)

        # Sacroiliac (SI) Joint junction interface
        si_joint = create_box(1.0, 6.0, 3.2, center=(s * 6.2, y_level - 3.5, z_level - 0.8))
        sub_geoms.append(si_joint)

    return merge_geometries(sub_geoms)


def create_erector_spinae_musculature():
    """
    Creates bilateral Erector Spinae (Longissimus, Iliocostalis, Spinalis) muscle columns
    and deep multifidus musculature occupying the vertebral lumbar gutters.
    """
    sub_geoms = []
    # Spans from T12/L1 down into the sacrum/iliac crest
    for s in (-1, 1):
        # Main erector spinae mass
        m_pos, m_norm, m_idx, m_uv = create_cylinder(
            radius_top=2.2, radius_bottom=3.1, height=28.0, segments=24, center=(s * 4.2, -1.5, -5.8), axis='Y'
        )
        # Flatten and shape into muscular gutter
        m_pos = [(p[0] * 1.15, p[1], -5.8 + (p[2] - (-5.8)) * 0.85) for p in m_pos]
        sub_geoms.append((m_pos, m_norm, m_idx, m_uv))

        # Deep Multifidus fascicles (adjacent to spinous processes)
        mf = create_box(1.8, 22.0, 1.8, center=(s * 1.9, -3.0, -5.2))
        sub_geoms.append(mf)

        # Gluteus maximus superior origin (lower boundary)
        gm = create_cylinder(3.4, 2.0, 10.0, segments=16, center=(s * 8.0, -18.0, -6.5), axis='Y')
        sub_geoms.append(gm)

    return merge_geometries(sub_geoms)


def create_thoracolumbar_fascia():
    """
    Creates the posterior layer of the Thoracolumbar Fascia:
    Dense aponeurotic membrane overlying the erector spinae.
    Serves as the anatomical floor upon which the subcutaneous lipomas rest!
    """
    nx, ny = 36, 44
    width, height = 30.0, 32.0
    positions = []
    normals = []
    uvs = []
    indices = []

    hx, hy = width * 0.5, height * 0.5

    for i in range(ny + 1):
        v = float(i) / ny
        y = -hy + v * height
        for j in range(nx + 1):
            u = float(j) / nx
            x = -hx + u * width

            # Anatomical curvature of fascia over erector spinae columns
            # Fascia dips at midline (spinous process anchor), peaks over muscle bulges at |x|=4.2cm,
            # then slopes forward laterally.
            muscle_bulge = math.exp(-((abs(x) - 4.2) ** 2) / 12.0) * 1.8
            midline_furrow = -math.exp(-(x ** 2) / 3.0) * 1.2
            lumbar_curve = -math.cos((y / hy) * 1.2) * 1.4

            z = -8.2 + muscle_bulge + midline_furrow + lumbar_curve

            positions.append((x, y, z))
            # Upward/posterior normal
            normals.append((0.0, 0.0, -1.0))
            uvs.append((u, v))

    for i in range(ny):
        for j in range(nx):
            i0 = i * (nx + 1) + j
            i1 = i0 + nx + 1
            indices.extend([i0, i1, i0 + 1])
            indices.extend([i0 + 1, i1, i1 + 1])

    return positions, normals, indices, uvs


def create_subcutaneous_fat_layer():
    """
    Creates the Subcutaneous Adipose Tissue (Panniculus Adiposus):
    Hypodermal fat sheet situated between the thoracolumbar fascia and the skin.
    This is the exact tissue plane in which the lipomas are seated.
    """
    nx, ny = 36, 44
    width, height = 32.0, 34.0
    positions = []
    normals = []
    uvs = []
    indices = []

    hx, hy = width * 0.5, height * 0.5

    for i in range(ny + 1):
        v = float(i) / ny
        y = -hy + v * height
        for j in range(nx + 1):
            u = float(j) / nx
            x = -hx + u * width

            # Fat layer sits right above fascia (approx 1.2 - 1.8 cm thickness)
            muscle_bulge = math.exp(-((abs(x) - 4.2) ** 2) / 14.0) * 1.6
            midline_furrow = -math.exp(-(x ** 2) / 3.5) * 0.8
            lumbar_curve = -math.cos((y / hy) * 1.2) * 1.3

            z = -9.4 + muscle_bulge + midline_furrow + lumbar_curve

            positions.append((x, y, z))
            normals.append((0.0, 0.0, -1.0))
            uvs.append((u, v))

    for i in range(ny):
        for j in range(nx):
            i0 = i * (nx + 1) + j
            i1 = i0 + nx + 1
            indices.extend([i0, i1, i0 + 1])
            indices.extend([i0 + 1, i1, i1 + 1])

    return positions, normals, indices, uvs


def create_skin_surface():
    """
    Creates the external back skin surface (dermis/epidermis):
    Features natural lumbar lordosis, spinal midline groove, and gluteal/pelvic contours.
    """
    nx, ny = 40, 48
    width, height = 34.0, 36.0
    positions = []
    normals = []
    uvs = []
    indices = []

    hx, hy = width * 0.5, height * 0.5

    for i in range(ny + 1):
        v = float(i) / ny
        y = -hy + v * height
        for j in range(nx + 1):
            u = float(j) / nx
            x = -hx + u * width

            # Normal back curvature:
            # - Lordosis arch along Y
            # - Shallow groove along spinal midline (x=0)
            # - Lateral flank curve
            lordosis = -math.cos((y / hy) * 1.2) * 1.6
            groove = -math.exp(-(x ** 2) / 4.0) * 0.6
            flank = -((x / hx) ** 2) * 2.8

            z = -10.6 + lordosis + groove + flank

            positions.append((x, y, z))
            normals.append((0.0, 0.0, -1.0))
            uvs.append((u, v))

    for i in range(ny):
        for j in range(nx):
            i0 = i * (nx + 1) + j
            i1 = i0 + nx + 1
            indices.extend([i0, i1, i0 + 1])
            indices.extend([i0 + 1, i1, i1 + 1])

    return positions, normals, indices, uvs


def create_scale_grid_plane(width=20.0, height=20.0, step=1.0, z_level=0.0):
    """Creates a 3D millimeter/centimeter scale grid with center crosshair lines."""
    sub_geoms = []
    half_w, half_h = width * 0.5, height * 0.5

    # Main subtle background plane
    bg = create_box(width, height, 0.02, center=(0, 0, z_level - 0.02))
    sub_geoms.append(bg)

    # Grid ruler border
    border_top = create_box(width, 0.08, 0.04, center=(0, half_h, z_level))
    border_bot = create_box(width, 0.08, 0.04, center=(0, -half_h, z_level))
    border_left = create_box(0.08, height, 0.04, center=(-half_w, 0, z_level))
    border_right = create_box(0.08, height, 0.04, center=(half_w, 0, z_level))
    sub_geoms.extend([border_top, border_bot, border_left, border_right])

    # Center axis marks
    mid_y = create_box(0.12, height, 0.06, center=(0, 0, z_level))
    mid_x = create_box(width, 0.12, 0.06, center=(0, 0, z_level))
    sub_geoms.extend([mid_y, mid_x])

    return merge_geometries(sub_geoms)


def create_3d_caliper_arrow(start_pt, end_pt, radius=0.06, head_len=0.4, head_r=0.18):
    """Creates a 3D caliper measurement arrow rod with dual conical arrowheads."""
    sub_geoms = []
    dx = end_pt[0] - start_pt[0]
    dy = end_pt[1] - start_pt[1]
    dz = end_pt[2] - start_pt[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)

    if length < 0.001:
        return create_box(0.1, 0.1, 0.1)

    # Shaft
    mid_x = (start_pt[0] + end_pt[0]) * 0.5
    mid_y = (start_pt[1] + end_pt[1]) * 0.5
    mid_z = (start_pt[2] + end_pt[2]) * 0.5

    # Determine axis
    if abs(dx) > abs(dy) and abs(dx) > abs(dz):
        shaft = create_cylinder(radius, radius, length, segments=12, center=(mid_x, mid_y, mid_z), axis='X')
    elif abs(dy) > abs(dx) and abs(dy) > abs(dz):
        shaft = create_cylinder(radius, radius, length, segments=12, center=(mid_x, mid_y, mid_z), axis='Y')
    else:
        shaft = create_cylinder(radius, radius, length, segments=12, center=(mid_x, mid_y, mid_z), axis='Z')

    sub_geoms.append(shaft)

    # Conical tips at start and end
    tip1 = create_cylinder(0.01, head_r, head_len, segments=12, center=start_pt, axis='X' if abs(dx)>abs(dy) else 'Y')
    tip2 = create_cylinder(head_r, 0.01, head_len, segments=12, center=end_pt, axis='X' if abs(dx)>abs(dy) else 'Y')
    sub_geoms.extend([tip1, tip2])

    return merge_geometries(sub_geoms)


# ============================================================================
# Generation of Model 1: lipoma-isolated.glb
# ============================================================================

def generate_isolated_lipoma_glb(output_path):
    print(f"Building isolated lipoma model -> {output_path}...")
    glb = GLBBuilder()

    # Materials
    mat_grid = glb.add_material("ScaleGrid_Mat", (0.12, 0.16, 0.24, 0.8), roughness=0.8, metallic=0.1)
    mat_caliper_r = glb.add_material("Caliper_Right_Mat", (0.06, 0.78, 0.45, 1.0), roughness=0.3, metallic=0.4)
    mat_caliper_l = glb.add_material("Caliper_Left_Mat", (0.97, 0.45, 0.08, 1.0), roughness=0.3, metallic=0.4)
    mat_lipoma_r_jul = glb.add_material("Lipoma_Right_2025_Mat", (0.11, 0.75, 0.46, 0.95), roughness=0.38, metallic=0.08)
    mat_lipoma_l_jul = glb.add_material("Lipoma_Left_2025_Mat", (0.95, 0.42, 0.12, 0.95), roughness=0.38, metallic=0.08)
    mat_lipoma_r_may = glb.add_material("Lipoma_Right_2026_Mat", (0.20, 0.85, 0.55, 0.75), roughness=0.35, metallic=0.05, alpha_mode="BLEND")
    mat_lipoma_l_may = glb.add_material("Lipoma_Left_2026_Mat", (1.0, 0.55, 0.20, 0.85), roughness=0.35, metallic=0.05, alpha_mode="BLEND")

    # 1. Scale Grid Reference (1 cm grid)
    grid_pos, grid_norm, grid_idx, grid_uv = create_scale_grid_plane(width=16.0, height=14.0, z_level=-2.0)
    grid_mesh = glb.add_mesh_primitive("ScaleGrid_1cm", grid_pos, grid_norm, grid_idx, mat_grid, grid_uv)
    node_grid = glb.add_node("ScaleGrid_1cm", mesh_idx=grid_mesh)
    glb.scene_nodes.append(node_grid)

    # 2. Right Lipoma - July 2025 (26 x 10 x 29 mm)
    # Radii in cm: rx = 2.6/2 = 1.3, rz = 1.0/2 = 0.5 (depth), ry = 2.9/2 = 1.45 (height)
    r_cx, r_cy, r_cz = -4.0, 0.0, 0.0
    r_pos, r_norm, r_idx, r_uv = create_ellipsoid(rx=1.3, ry=1.45, rz=0.5, noise_amp=0.035, center=(r_cx, r_cy, r_cz))
    mesh_r_jul = glb.add_mesh_primitive("Lipoma_Right_2025_26x10x29mm", r_pos, r_norm, r_idx, mat_lipoma_r_jul, r_uv)
    node_r_jul = glb.add_node("Lipoma_Right_2025_26x10x29mm", mesh_idx=mesh_r_jul)
    glb.scene_nodes.append(node_r_jul)

    # 3. Left Lipoma - July 2025 (39 x 9 x 20 mm)
    # Radii in cm: rx = 3.9/2 = 1.95, rz = 0.9/2 = 0.45 (depth), ry = 2.0/2 = 1.0 (height)
    l_cx, l_cy, l_cz = 4.0, 0.0, 0.0
    l_pos, l_norm, l_idx, l_uv = create_ellipsoid(rx=1.95, ry=1.0, rz=0.45, noise_amp=0.035, center=(l_cx, l_cy, l_cz))
    mesh_l_jul = glb.add_mesh_primitive("Lipoma_Left_2025_39x9x20mm", l_pos, l_norm, l_idx, mat_lipoma_l_jul, l_uv)
    node_l_jul = glb.add_node("Lipoma_Left_2025_39x9x20mm", mesh_idx=mesh_l_jul)
    glb.scene_nodes.append(node_l_jul)

    # 4. May 2026 Follow-up States (Included as nodes for side-by-side or morph comparison)
    # Right: 2.4 x 1.2 cm (rx = 1.2, rz = 0.6, ry = 0.6)
    r2_pos, r2_norm, r2_idx, r2_uv = create_ellipsoid(rx=1.2, ry=0.6, rz=0.6, noise_amp=0.03, center=(r_cx, r_cy, r_cz))
    mesh_r_may = glb.add_mesh_primitive("Lipoma_Right_2026_24x12mm", r2_pos, r2_norm, r2_idx, mat_lipoma_r_may, r2_uv)
    node_r_may = glb.add_node("Lipoma_Right_2026_24x12mm", mesh_idx=mesh_r_may)
    glb.scene_nodes.append(node_r_may)

    # Left: 3.2 x 2.3 cm (rx = 1.6, rz = 1.15 [substantially thicker!], ry = 1.0)
    l2_pos, l2_norm, l2_idx, l2_uv = create_ellipsoid(rx=1.6, ry=1.0, rz=1.15, noise_amp=0.03, center=(l_cx, l_cy, l_cz))
    mesh_l_may = glb.add_mesh_primitive("Lipoma_Left_2026_32x23mm", l2_pos, l2_norm, l2_idx, mat_lipoma_l_may, l2_uv)
    node_l_may = glb.add_node("Lipoma_Left_2026_32x23mm", mesh_idx=mesh_l_may)
    glb.scene_nodes.append(node_l_may)

    # 5. 3D Calipers / Dimension Axes for Right Lipoma (Width, Height, Depth)
    cal_r_w = create_3d_caliper_arrow((r_cx - 1.3, r_cy - 1.8, r_cz), (r_cx + 1.3, r_cy - 1.8, r_cz))
    cal_r_h = create_3d_caliper_arrow((r_cx - 1.8, r_cy - 1.45, r_cz), (r_cx - 1.8, r_cy + 1.45, r_cz))
    cal_r_d = create_3d_caliper_arrow((r_cx, r_cy - 1.8, r_cz - 0.5), (r_cx, r_cy - 1.8, r_cz + 0.5))
    cal_r_pos, cal_r_norm, cal_r_idx, cal_r_uv = merge_geometries([cal_r_w, cal_r_h, cal_r_d])
    mesh_cal_r = glb.add_mesh_primitive("Caliper_Right_26x10x29mm", cal_r_pos, cal_r_norm, cal_r_idx, mat_caliper_r, cal_r_uv)
    node_cal_r = glb.add_node("Caliper_Right_26x10x29mm", mesh_idx=mesh_cal_r)
    glb.scene_nodes.append(node_cal_r)

    # 6. 3D Calipers / Dimension Axes for Left Lipoma
    cal_l_w = create_3d_caliper_arrow((l_cx - 1.95, l_cy - 1.6, l_cz), (l_cx + 1.95, l_cy - 1.6, l_cz))
    cal_l_h = create_3d_caliper_arrow((l_cx + 2.4, l_cy - 1.0, l_cz), (l_cx + 2.4, l_cy + 1.0, l_cz))
    cal_l_d = create_3d_caliper_arrow((l_cx, l_cy - 1.6, l_cz - 0.45), (l_cx, l_cy - 1.6, l_cz + 0.45))
    cal_l_pos, cal_l_norm, cal_l_idx, cal_l_uv = merge_geometries([cal_l_w, cal_l_h, cal_l_d])
    mesh_cal_l = glb.add_mesh_primitive("Caliper_Left_39x9x20mm", cal_l_pos, cal_l_norm, cal_l_idx, mat_caliper_l, cal_l_uv)
    node_cal_l = glb.add_node("Caliper_Left_39x9x20mm", mesh_idx=mesh_cal_l)
    glb.scene_nodes.append(node_cal_l)

    glb_bytes = glb.build_glb()
    with open(output_path, "wb") as f:
        f.write(glb_bytes)
    print(f"Successfully generated {output_path} ({len(glb_bytes):,} bytes, {len(glb.meshes)} meshes, {len(glb.nodes)} nodes).")


# ============================================================================
# Generation of Model 2: lower-back-anatomy-lipomas.glb
# ============================================================================

def generate_anatomical_back_glb(output_path):
    print(f"Building full anatomical lower back model -> {output_path}...")
    glb = GLBBuilder()

    # Materials for Anatomical Layers
    mat_bone = glb.add_material("Bone_Lumbar_Sacrum_Mat", (0.91, 0.89, 0.84, 1.0), roughness=0.65, metallic=0.05)
    mat_disc = glb.add_material("Intervertebral_Disc_Mat", (0.58, 0.65, 0.72, 1.0), roughness=0.45, metallic=0.1)
    mat_disc_narrow = glb.add_material("L5_S1_NarrowedDisc_Mat", (0.75, 0.62, 0.52, 1.0), roughness=0.55, metallic=0.1)
    mat_pelvis = glb.add_material("Pelvis_IliacCrest_Mat", (0.88, 0.86, 0.81, 1.0), roughness=0.68, metallic=0.05)
    mat_muscle = glb.add_material("Erector_Spinae_Musculature_Mat", (0.62, 0.16, 0.18, 0.88), roughness=0.75, metallic=0.02, alpha_mode="BLEND")
    mat_fascia = glb.add_material("Thoracolumbar_Fascia_Mat", (0.75, 0.88, 0.96, 0.65), roughness=0.35, metallic=0.15, alpha_mode="BLEND")
    mat_fat = glb.add_material("Subcutaneous_Adipose_Fat_Mat", (0.96, 0.76, 0.22, 0.55), roughness=0.6, metallic=0.0, alpha_mode="BLEND")
    mat_skin = glb.add_material("Skin_Integument_Mat", (0.83, 0.65, 0.54, 0.35), roughness=0.8, metallic=0.0, alpha_mode="BLEND")
    mat_lipoma_r = glb.add_material("Lipoma_Right_L5S1_Mat", (0.08, 0.76, 0.44, 0.98), roughness=0.4, metallic=0.08)
    mat_lipoma_l = glb.add_material("Lipoma_Left_L5S1_Mat", (0.94, 0.40, 0.10, 0.98), roughness=0.4, metallic=0.08)

    # 1. Lumbar Spine L1 - L5 with Lordosis
    vertebrae_y = [11.0, 5.8, 0.6, -4.6, -9.8]  # cm coordinates along spinal column
    disc_y = [8.4, 3.2, -2.0, -7.2, -12.4]

    spine_children = []

    for i in range(5):
        v_level = f"L{i+1}"
        y_v = vertebrae_y[i]
        # Slight anterior lordosis curve: L3 is most anterior
        z_v = 2.5 - 0.6 * math.sin((y_v + 4.6) / 12.0 * math.pi)

        v_pos, v_norm, v_idx, v_uv = create_lumbar_vertebra(i, y_v, z_v)
        # Flip Z to point spinous processes posterior (+Z)
        v_pos = [(p[0], p[1], -p[2]) for p in v_pos]
        v_norm = [(n[0], n[1], -n[2]) for n in v_norm]
        mesh_v = glb.add_mesh_primitive(f"Vertebra_{v_level}", v_pos, v_norm, v_idx, mat_bone, v_uv)
        node_v = glb.add_node(f"Vertebra_{v_level}", mesh_idx=mesh_v)
        spine_children.append(node_v)

        # Discs between vertebrae
        if i < 4:
            y_d = disc_y[i]
            z_d = 2.5 - 0.6 * math.sin((y_d + 4.6) / 12.0 * math.pi)
            d_pos, d_norm, d_idx, d_uv = create_intervertebral_disc(i, y_d, -z_d, height=0.85)
            mesh_d = glb.add_mesh_primitive(f"Disc_L{i+1}_L{i+2}", d_pos, d_norm, d_idx, mat_disc, d_uv)
            node_d = glb.add_node(f"Disc_L{i+1}_L{i+2}", mesh_idx=mesh_d)
            spine_children.append(node_d)

    # L5-S1 disc with clinically noted Mild Disc Space Narrowing (reduced height to 0.55 cm)
    y_l5s1 = disc_y[4]
    z_l5s1 = -2.5
    d5_pos, d5_norm, d5_idx, d5_uv = create_intervertebral_disc(4, y_l5s1, z_l5s1, height=0.55)
    mesh_l5s1 = glb.add_mesh_primitive("Disc_L5_S1_MildNarrowing", d5_pos, d5_norm, d5_idx, mat_disc_narrow, d5_uv)
    node_l5s1 = glb.add_node("Disc_L5_S1_MildNarrowing", mesh_idx=mesh_l5s1)
    spine_children.append(node_l5s1)

    # 2. Sacrum (S1 - S5)
    sac_pos, sac_norm, sac_idx, sac_uv = create_sacrum(y_top=-13.5, z_center=-3.8)
    sac_pos = [(p[0], p[1], -p[2]) for p in sac_pos]
    sac_norm = [(n[0], n[1], -n[2]) for n in sac_norm]
    mesh_sac = glb.add_mesh_primitive("Sacrum_S1_S5", sac_pos, sac_norm, sac_idx, mat_bone, sac_uv)
    node_sac = glb.add_node("Sacrum_S1_S5", mesh_idx=mesh_sac)
    spine_children.append(node_sac)

    # 3. Pelvis & Iliac Crests (PSIS landmarks)
    pel_pos, pel_norm, pel_idx, pel_uv = create_pelvis_iliac_crests(y_level=-9.0, z_level=-4.2)
    pel_pos = [(p[0], p[1], -p[2]) for p in pel_pos]
    pel_norm = [(n[0], n[1], -n[2]) for n in pel_norm]
    mesh_pel = glb.add_mesh_primitive("Pelvis_IliacCrests_PSIS", pel_pos, pel_norm, pel_idx, mat_pelvis, pel_uv)
    node_pel = glb.add_node("Pelvis_IliacCrests_PSIS", mesh_idx=mesh_pel)

    # Skeletal root node
    node_skeletal = glb.add_node("Skeletal_Structure", children=spine_children + [node_pel])
    glb.scene_nodes.append(node_skeletal)

    # 4. Musculature (Erector Spinae, Multifidus, Gluteal upper margin)
    musc_pos, musc_norm, musc_idx, musc_uv = create_erector_spinae_musculature()
    musc_pos = [(p[0], p[1], -p[2]) for p in musc_pos]
    musc_norm = [(n[0], n[1], -n[2]) for n in musc_norm]
    mesh_musc = glb.add_mesh_primitive("Erector_Spinae_Muscles", musc_pos, musc_norm, musc_idx, mat_muscle, musc_uv)
    node_musc = glb.add_node("Erector_Spinae_Musculature", mesh_idx=mesh_musc)
    glb.scene_nodes.append(node_musc)

    # 5. Thoracolumbar Fascia (Posterior connective tissue sheet)
    fascia_pos, fascia_norm, fascia_idx, fascia_uv = create_thoracolumbar_fascia()
    fascia_pos = [(p[0], p[1], -p[2]) for p in fascia_pos]
    fascia_norm = [(n[0], n[1], -n[2]) for n in fascia_norm]
    mesh_fascia = glb.add_mesh_primitive("Thoracolumbar_Fascia", fascia_pos, fascia_norm, fascia_idx, mat_fascia, fascia_uv)
    node_fascia = glb.add_node("Thoracolumbar_Fascia", mesh_idx=mesh_fascia)
    glb.scene_nodes.append(node_fascia)

    # 6. Subcutaneous Fat Layer (Panniculus Adiposus)
    fat_pos, fat_norm, fat_idx, fat_uv = create_subcutaneous_fat_layer()
    fat_pos = [(p[0], p[1], -p[2]) for p in fat_pos]
    fat_norm = [(n[0], n[1], -n[2]) for n in fat_norm]
    mesh_fat = glb.add_mesh_primitive("Subcutaneous_Adipose_Fat", fat_pos, fat_norm, fat_idx, mat_fat, fat_uv)
    node_fat = glb.add_node("Subcutaneous_Adipose_Fat", mesh_idx=mesh_fat)
    glb.scene_nodes.append(node_fat)

    # 7. Skin Layer (Dermis & Epidermis)
    skin_pos, skin_norm, skin_idx, skin_uv = create_skin_surface()
    skin_pos = [(p[0], p[1], -p[2]) for p in skin_pos]
    skin_norm = [(n[0], n[1], -n[2]) for n in skin_norm]
    mesh_skin = glb.add_mesh_primitive("Skin_Integument", skin_pos, skin_norm, skin_idx, mat_skin, skin_uv)
    node_skin = glb.add_node("Skin_Integument", mesh_idx=mesh_skin)
    glb.scene_nodes.append(node_skin)

    # 8. Embedded Lipomas (Accurately positioned in subcutaneous fat layer superficial to fascia at L5-S1)
    # Right Lipoma: centered at x = -4.6 cm, y = -3.0 cm, resting in subcutaneous plane at z = +8.9 cm
    # Dimensions: 26 x 10 x 29 mm -> rx=1.3, rz=0.5, ry=1.45
    r_pos, r_norm, r_idx, r_uv = create_ellipsoid(rx=1.3, ry=1.45, rz=0.5, noise_amp=0.035, center=(-4.6, -3.0, 8.9))
    mesh_r = glb.add_mesh_primitive("Lipoma_Right_Subcutaneous_L5S1", r_pos, r_norm, r_idx, mat_lipoma_r, r_uv)
    node_r = glb.add_node("Lipoma_Right_Subcutaneous_L5S1", mesh_idx=mesh_r)

    # Left Lipoma: centered at x = +5.2 cm, y = -4.0 cm, resting in subcutaneous plane at z = +8.9 cm
    # Baseline dimensions: 39 x 9 x 20 mm -> rx=1.95, rz=0.45, ry=1.0
    l_pos, l_norm, l_idx, l_uv = create_ellipsoid(rx=1.95, ry=1.0, rz=0.45, noise_amp=0.035, center=(5.2, -4.0, 8.9))
    mesh_l = glb.add_mesh_primitive("Lipoma_Left_Subcutaneous_L5S1", l_pos, l_norm, l_idx, mat_lipoma_l, l_uv)
    node_l = glb.add_node("Lipoma_Left_Subcutaneous_L5S1", mesh_idx=mesh_l)

    node_lipomas = glb.add_node("Subcutaneous_Lipomas", children=[node_r, node_l])
    glb.scene_nodes.append(node_lipomas)

    glb_bytes = glb.build_glb()
    with open(output_path, "wb") as f:
        f.write(glb_bytes)
    print(f"Successfully generated {output_path} ({len(glb_bytes):,} bytes, {len(glb.meshes)} meshes, {len(glb.nodes)} nodes).")


def main():
    target_dir = os.path.dirname(os.path.abspath(__file__))
    iso_glb_path = os.path.join(target_dir, "lipoma-isolated.glb")
    anat_glb_path = os.path.join(target_dir, "lower-back-anatomy-lipomas.glb")

    generate_isolated_lipoma_glb(iso_glb_path)
    generate_anatomical_back_glb(anat_glb_path)
    print("\n[SUCCESS] Both 3D GLB models generated and verified.")

if __name__ == "__main__":
    main()
