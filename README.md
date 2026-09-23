# Lower Back Subcutaneous Lipoma 3D Clinical Visualization & Timeline

[![Vercel Deployment](https://img.shields.io/badge/Deploy-Vercel-black?style=flat&logo=vercel)](https://vercel.com)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black?style=flat&logo=three.js)](https://threejs.org/)
[![glTF 2.0](https://img.shields.io/badge/glTF-2.0-orange?style=flat)](https://www.khronos.org/gltf/)
[![Privacy: Zero PII](https://img.shields.io/badge/Privacy-Zero%20PII-brightgreen?style=flat)](#privacy--compliance)

An interactive, high-fidelity 3D medical visualization web platform and standalone glTF 2.0 3D models designed to visualize bilateral subcutaneous lipomas in the lower back (L5–S1 paramedian region), demonstrating their anatomical stratification relative to muscle, fascia, and bone, alongside longitudinal growth tracking between clinical ultrasound and MRI studies.

---

## 3D Models Included

1. **`lipoma-isolated.glb`**:
   - High-resolution standalone 3D meshes of just the bilateral lipomas.
   - Includes real-time 3D millimeter caliper vectors ($X \times Y \times Z$) and a 1 cm reference grid.
   - Ideal for isolation analysis, surgical pre-planning, or inspection in external 3D software (Blender, Windows 3D Viewer).

2. **`lower-back-anatomy-lipomas.glb`**:
   - Complete anatomical context featuring:
     - **Skeletal / Spine**: L1–L5 lumbar vertebrae, facet joints, narrowed L5–S1 disc space, sacrum, and iliac crests/pelvis.
     - **Musculature**: Deep erector spinae / multifidus muscle columns.
     - **Fascia**: Thoracolumbar fascia defining the posterior margin of the muscle compartment.
     - **Subcutaneous Layer**: Adipose tissue embedding the lipomas.
     - **Dermal Surface**: Translucent skin envelope with posterior midline anatomical reference furrow.
     - **Lipomas**: Paramedian subcutaneous lipomas positioned superficial to the thoracolumbar fascia.

3. **`generate_3d_models.py`**:
   - Standalone procedural Python script using the standard library (`struct` and `json`) to construct both binary glTF (`.glb`) files directly from clinical dimensions without third-party CAD dependencies.

---

## Clinical Longitudinal Timeline

Longitudinal data synthesized from diagnostic ultrasound and lumbar spine MRI evaluations:

| Parameter | Baseline Ultrasound (Jul 22, 2025) | Follow-up Ultrasound (May 14, 2026) | Interval Delta | Clinical Status |
| :--- | :--- | :--- | :--- | :--- |
| **Right Lipoma Dimensions** | $26 \times 10 \times 29\text{ mm}$ | $24 \times 12\text{ mm}$ (approx. $24 \times 12 \times 25\text{ mm}$) | $-7.7\%\text{ W}$, $+20\%\text{ D}$ | **Stable** ($\Delta V \approx -3.8\%$). Typical US measurement variation. |
| **Right Calculated Volume** | $3.95\text{ cm}^3$ | $3.80\text{ cm}^3$ | $-0.15\text{ cm}^3$ | Paramedian, superficial to thoracolumbar fascia. |
| **Left Lipoma Dimensions** | $39 \times 9 \times 20\text{ mm}$ | $32 \times 23\text{ mm}$ (approx. $32 \times 23 \times 20\text{ mm}$) | $-17.9\%\text{ W}$, **$+155.6\%\text{ D}$** | **Marked AP thickening** ($9\text{ mm} \to 23\text{ mm}$). |
| **Left Axial Area** | $2.76\text{ cm}^2$ | $5.78\text{ cm}^2$ | **$+109.4\%$** | Transverse expansion. |
| **Left Calculated Volume** | $3.68\text{ cm}^3$ | $7.72\text{ cm}^3$ | **$+4.04\text{ cm}^3$ ($+109.8\%$)** | Volume expansion $\approx \mathbf{+110\%}$. |
| **Lumbar MRI Correlation** | N/A | Superficial fat infiltration ($\sim 9 \times 2.3\text{ cm}$) at left flank/buttock margin. | N/A | Mild L5–S1 disc narrowing and facet arthrosis incorporated into spinal model. |

---

## Interactive Features

- **Three Display Modes**:
  - `Anatomical Context`: Full stratified anatomy with embedded lipomas.
  - `Isolated Lipomas`: Focused view of lipoma lobules with 3D calipers and 1 cm reference grid.
  - `Growth Ghost Overlay`: Semi-transparent wireframe of baseline 2025 volume superimposed inside the expanded 2026 solid mass.
- **Independent Layer Opacity Sliders**: Real-time transparency adjustment for Skin, Subcutaneous Fat, Fascia, Erector Spinae, and Spine/Pelvis.
- **Dynamic Axial Slicing Plane**: Hardware-accelerated GPU clipping plane (`localClippingEnabled = true`) allowing continuous horizontal slicing from L1 to the sacrum.
- **Camera Perspective Presets**: Posterior (Back), Lateral (Side profile), Axial (Cross-section), L5–S1 Close-up, and 3/4 Oblique.
- **3D Calipers & Screen Projection**: Calipers dynamically calculate screen coordinates via `vector.project(camera)` to keep measurement tags readable from any angle.
- **Asset Export**: Download isolated or anatomical `.glb` files and capture 4K PNG snapshots directly from the UI.

---

## Deploying to Vercel

This repository is pre-configured for zero-friction Vercel deployment:

1. Import this repository into [Vercel](https://vercel.com/new).
2. The project will automatically detect `vercel.json` and build using `node build.js`.
3. Output Directory is set to `dist`.
4. All `.glb` 3D files are served with the correct `Content-Type: model/gltf-binary` and CORS headers.

Alternatively, deploy using the Vercel CLI:
```bash
npm i -g vercel
vercel
```

---

## Running Locally

To run the application locally without any dependencies:

```bash
# Clone the repository
git clone https://github.com/ys-sites/lipoma.git
cd lipoma

# Start a local web server (Python)
python -m http.server 8080

# Or using Node.js
npx serve .
```

Open `http://localhost:8080` in any modern web browser.

---

## Privacy & Compliance

This repository contains **Zero Personal Identifying Information (PII)**:
- No patient names, initials, dates of birth, or identification numbers.
- No healthcare provider, radiologist, physician, or clinic names.
- Grounded strictly in objective anatomical measurements and anonymized clinical imaging findings.

---

## License

MIT License. Open for educational, clinical visualization, and research purposes.
