const fs = require('fs');
const path = require('path');

const srcDir = __dirname;
const distDir = path.join(srcDir, 'dist');

console.log('--- Starting Vercel Build for Lower Back Lipoma 3D Visualization ---');

// Ensure dist directory exists
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Assets to copy into dist
const assetsToCopy = [
  'index.html',
  'lower-back-3d-web.glb',
  'model-info.json',
  'meshopt_decoder.js',
  'lower-back-3d-detail.html',
  'lower-back-3d.glb',
  'lower-back-lipomas-anatomy.glb',
  'lower-back-lipomas-anatomy.html',
  'lower-back-lipomas-3d.html',
  'lipoma-isolated.glb',
  'lower-back-anatomy-lipomas.glb',
  'lower-back-lipomas-3d.glb',
  'ct-atlas.jpg',
  'generate_3d_models.py',
  'favicon.svg'
];

let copiedCount = 0;
assetsToCopy.forEach(fileName => {
  const srcPath = path.join(srcDir, fileName);
  const destPath = path.join(distDir, fileName);

  if (fs.existsSync(srcPath)) {
    fs.copyFileSync(srcPath, destPath);
    const stats = fs.statSync(destPath);
    console.log(`[OK] Copied ${fileName} (${(stats.size / 1024).toFixed(1)} KB) -> dist/${fileName}`);
    copiedCount++;
  } else {
    console.warn(`[SKIP] File not found: ${fileName}`);
  }
});

console.log(`--- Build complete: ${copiedCount} assets copied to dist/ ---`);
