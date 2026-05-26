import fs from 'fs';
import path from 'path';

function copyDir(src, dest) {
    fs.mkdirSync(dest, { recursive: true });
    let entries = fs.readdirSync(src, { withFileTypes: true });

    for (let entry of entries) {
        let srcPath = path.join(src, entry.name);
        let destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            copyDir(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

const targetDir = path.resolve('public');

// Priority: bolamistis (main app) -> mockup-sandbox
const bolamistisDir = path.resolve('artifacts/bolamistis/dist/public');
const mockupDir = path.resolve('artifacts/mockup-sandbox/dist');

if (fs.existsSync(bolamistisDir)) {
    console.log(`[Vercel] Copying bolamistis build from ${bolamistisDir} to ${targetDir}...`);
    if (fs.existsSync(targetDir)) {
        fs.rmSync(targetDir, { recursive: true, force: true });
    }
    copyDir(bolamistisDir, targetDir);
    console.log('[Vercel] Build copied successfully!');
} else if (fs.existsSync(mockupDir)) {
    console.log(`[Vercel] Copying mockup-sandbox build from ${mockupDir} to ${targetDir}...`);
    if (fs.existsSync(targetDir)) {
        fs.rmSync(targetDir, { recursive: true, force: true });
    }
    copyDir(mockupDir, targetDir);
    console.log('[Vercel] Build copied successfully!');
} else {
    console.error('[Vercel] Warning: No build output directories found to copy!');
}
