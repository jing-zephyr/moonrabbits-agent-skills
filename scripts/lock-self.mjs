// lock-self.mjs —— 把自研 skills-src 的逐文件 sha256 锁进 LOCK.json["self"]
// 用法: node scripts/lock-self.mjs
// 铁律: 只新增/更新 self 段，不动 vendor 段与官方任何文件。
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SKILLS = path.join(REPO, 'skills-src');
const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

async function walk(dir, base = dir) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(p, base));
    else out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out.sort();
}

const files = await walk(SKILLS);
const self = {};
for (const f of files) self[f] = sha256(await readFile(path.join(SKILLS, f)));

const lockPath = path.join(REPO, 'LOCK.json');
const lock = JSON.parse(await readFile(lockPath, 'utf8'));
lock.self = { skills_src: self, captured_at: new Date().toISOString() };
await writeFile(lockPath, JSON.stringify(lock, null, 2) + '\n', 'utf8');
console.log(`LOCK.json["self"] 已写入：${Object.keys(self).length} 个文件`);
