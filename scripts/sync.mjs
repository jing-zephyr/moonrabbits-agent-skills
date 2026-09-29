// sync.mjs — 从本地官方快照，把选定 skill 冻结进 vendor/，并生成 LOCK.json
// 纪律：官方文件一个字节都不改（改了就签名失效）。本脚本只做「复制 + 记账 + 校验」。
// 用法：
//   node scripts/sync.mjs --from <解包后的官方快照根目录> [--apply]
//   不带 --apply = 只预演（dry-run），不改任何文件
import { readFile, writeFile, mkdir, cp, readdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const VENDOR = path.join(REPO, 'vendor', 'nvidia-skills');
const LOCK = path.join(REPO, 'LOCK.json');

// ── 选定的官方 skill（第一档主链路 + 第二档元技能）；依据见 Skill3-资源筛选与落地-20260926.md
const PICKED = [
  'tao-generate-image-grounding',
  'tao-generate-referring-expressions',
  'nvidia-skill-finder',
  'skill-card-generator',
];

const EXPECT_COMMIT = 'd8519c57da6db5d9bea274ec1724a4a7a56a3dee';

function arg(name, def = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : def;
}
const APPLY = process.argv.includes('--apply');
const FROM = arg('from');

if (!FROM) {
  console.error('用法: node scripts/sync.mjs --from <官方快照根目录> [--apply]');
  process.exit(2);
}

const SKILLS_ROOT = path.join(FROM, 'skills');
try {
  await stat(SKILLS_ROOT);
} catch {
  console.error(`找不到 ${SKILLS_ROOT}。--from 应指向解包后的 skills-<commit>/ 目录。`);
  process.exit(2);
}

// 校验上游 commit（目录名形如 skills-<sha>）
const topName = path.basename(FROM);
const m = topName.match(/skills-([0-9a-f]{40})/);
const commit = m ? m[1] : '(未知)';
if (m && commit !== EXPECT_COMMIT) {
  console.error(`⚠️ 上游 commit 不符：期望 ${EXPECT_COMMIT}，实际 ${commit}`);
  console.error('   若确认要换版本，请同时更新本脚本的 EXPECT_COMMIT 与所有材料的 commit 口径。');
  process.exit(3);
}

async function walk(dir, base = dir) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(p, base));
    else out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out.sort();
}
const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

// 读取许可信息（来自 catalog 扫描产物；缺则标 unknown，不猜）
let licenseByName = {};
try {
  const tsv = await readFile(path.join(REPO, '..', '_catalog-scan', 'official-skills-index.tsv'), 'utf8');
  const rows = tsv.split(/\r?\n/).slice(1).filter(Boolean);
  for (const r of rows) {
    const c = r.split('\t');
    licenseByName[c[0]] = c[2] || 'unknown';
  }
} catch { /* 允许缺失 */ }

const lock = {
  upstream: 'github.com/NVIDIA/skills',
  commit: m ? commit : EXPECT_COMMIT,
  captured_at: new Date().toISOString().slice(0, 10),
  policy: '官方文件逐字复制，永不修改；环境差异一律放 adapter/',
  skills: {},
};

console.log(`上游: ${lock.upstream} @ ${lock.commit}`);
console.log(`模式: ${APPLY ? 'APPLY（会写文件）' : 'DRY-RUN（只预演）'}`);
console.log('');

let totalBytes = 0;
for (const name of PICKED) {
  const src = path.join(SKILLS_ROOT, name);
  try {
    await stat(src);
  } catch {
    console.error(`❌ 官方目录里没有 ${name} —— 停下，不猜。`);
    process.exit(4);
  }
  const files = await walk(src);
  const entry = { license: licenseByName[name] || 'unknown', files: {} };
  for (const f of files) {
    const buf = await readFile(path.join(src, f));
    entry.files[f] = sha256(buf);
    totalBytes += buf.length;
  }
  lock.skills[name] = entry;
  // 必备治理产物自检（官方规矩：缺一件，流水线拒收）
  const missing = ['SKILL.md', 'skill-card.md', 'skill.oms.sig'].filter((k) => !(k in entry.files));
  const evalsOk = Object.keys(entry.files).some((k) => k.startsWith('evals/') || k.startsWith('eval/'));
  console.log(`${name}`);
  console.log(`  文件 ${files.length} 个 · ${Object.values(entry.files).length ? '' : ''}许可 ${entry.license}`);
  console.log(`  治理产物: SKILL.md=${'SKILL.md' in entry.files ? 'Y' : 'N'} skill-card=${'skill-card.md' in entry.files ? 'Y' : 'N'} 签名=${'skill.oms.sig' in entry.files ? 'Y' : 'N'} evals=${evalsOk ? 'Y' : 'N'}`);
  if (missing.length) console.log(`  ⚠️ 缺: ${missing.join(', ')}`);

  if (APPLY) {
    const dst = path.join(VENDOR, name);
    await mkdir(path.dirname(dst), { recursive: true });
    await cp(src, dst, { recursive: true });
  }
}

if (APPLY) {
  await writeFile(LOCK, JSON.stringify(lock, null, 2) + '\n', 'utf8');
  console.log(`\n✅ 已写入 LOCK.json（${Object.keys(lock.skills).length} 个 skill，共 ${totalBytes} 字节）`);
  console.log(`✅ 官方原文已冻结到 ${path.relative(REPO, VENDOR)}`);
} else {
  console.log(`\n（预演完成，未写任何文件。加 --apply 才真正执行）`);
  console.log(`预计冻结 ${Object.keys(lock.skills).length} 个 skill · ${totalBytes} 字节`);
}
