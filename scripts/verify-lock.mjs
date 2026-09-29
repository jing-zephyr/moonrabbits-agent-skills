// verify-lock.mjs — 核对 vendor/ 里的官方文件有没有被手改
// 三种情况都会报出来：内容不符 / 多出文件 / 文件缺失。任一即 exit 1（R4：绝不绕过）。
// 用法: node scripts/verify-lock.mjs
import { readFile, readdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const VENDOR = path.join(REPO, 'vendor', 'nvidia-skills');
const LOCK = path.join(REPO, 'LOCK.json');

const lock = JSON.parse(await readFile(LOCK, 'utf8'));
const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

async function walk(dir, base = dir) {
  const out = [];
  let entries;
  try { entries = await readdir(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(p, base));
    else out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out.sort();
}

console.log(`LOCK: ${lock.upstream} @ ${lock.commit}  (captured ${lock.captured_at})`);
console.log(`比对目录: ${path.relative(REPO, VENDOR)}`);
console.log('');

let checked = 0, mismatch = 0, extra = 0, missing = 0;
const problems = [];

for (const [skill, entry] of Object.entries(lock.skills)) {
  const dir = path.join(VENDOR, skill);
  const want = entry.files;
  const have = await walk(dir);

  for (const [f, hash] of Object.entries(want)) {
    checked++;
    if (!have.includes(f)) { missing++; problems.push(`MISSING  ${skill}/${f}`); continue; }
    const got = sha256(await readFile(path.join(dir, f)));
    if (got !== hash) { mismatch++; problems.push(`MODIFIED ${skill}/${f}\n          期望 ${hash}\n          实际 ${got}`); }
  }
  for (const f of have) {
    if (!(f in want)) { extra++; problems.push(`EXTRA    ${skill}/${f}  ← 不在 LOCK 里（可能被新增或上游换了版本）`); }
  }
  console.log(`${mismatch || extra || missing ? ' ' : '✓'} ${skill}: ${Object.keys(want).length} 个文件已核对`);
}

// ── 自研 skills-src 完整性（LOCK.self 段，2026-09-29 起）
const SELF = path.join(REPO, 'skills-src');
if (lock.self && lock.self.skills_src) {
  const want = lock.self.skills_src;
  const have = await walk(SELF);
  let sBad = 0;
  for (const [f, hash] of Object.entries(want)) {
    checked++;
    if (!have.includes(f)) { missing++; sBad++; problems.push(`SELF MISSING  skills-src/${f}`); continue; }
    const got = sha256(await readFile(path.join(SELF, f)));
    if (got !== hash) { mismatch++; sBad++; problems.push(`SELF MODIFIED skills-src/${f}\n          期望 ${hash}\n          实际 ${got}`); }
  }
  for (const f of have) {
    if (!(f in want)) { extra++; sBad++; problems.push(`SELF EXTRA skills-src/${f}  ← 不在 LOCK.self 里（先跑 node scripts/lock-self.mjs）`); }
  }
  console.log(`${sBad ? ' ' : '✓'} skills-src(自研): ${Object.keys(want).length} 个文件已核对`);
} else {
  console.log('ℹ 未发现 LOCK.self 段 —— 先跑 node scripts/lock-self.mjs 锁入自研技能');
}

console.log('');
console.log(`核对文件数: ${checked}  ·  内容不符: ${mismatch}  ·  多出: ${extra}  ·  缺失: ${missing}`);

if (problems.length) {
  console.log('\n❌ 不通过。明细：');
  for (const p of problems) console.log('  ' + p);
  console.log('\n文件被改动 = 完整性失效。请还原，或把改动移到 adapter/ 与自研 skill。');
  process.exit(1);
}
console.log('\n✅ OK, 0 mismatch —— 官方原文与自研技能自冻结以来一个字节都没动。');
