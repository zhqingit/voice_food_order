import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const pkgRoot = path.resolve(__dirname, '..');
const src = path.resolve(pkgRoot, 'src', 'styles.css');
const distDir = path.resolve(pkgRoot, 'dist');
const dest = path.resolve(distDir, 'styles.css');

await fs.mkdir(distDir, { recursive: true });
await fs.copyFile(src, dest);
