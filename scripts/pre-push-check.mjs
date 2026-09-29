// pre-push-check.mjs — 推送前的机器化闸门（对应 R4：推送前过闸）
// 三道检查，任一不过即 exit 1：
//   ① 密钥/敏感信息扫描（含节点 IP、端口、token、私钥特征）
//      —— vendor/ 官方文件里的**已登记测试样例**可例外（见 adapter/vendor-exceptions.json），
//         未登记的新命中一律拦下。
//   ② 官方文件未改动（对照 LOCK.json 的 sha256）
//   ③ 自研 skill 的 frontmatter 契约（name/description/license/allowed-tools/version）
// 用法: node scripts/pre-push-check.mjs
import { readFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SELF_SRC = path.join(REPO, 'skills-src');
const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

async function walk(dir, base = dir, skip = new Set(['.git', 'node_modules'])) {
  const out = [];
  let entries;
  try { entries = await readdir(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    if (skip.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(p, base, skip));
    else out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out.sort();
}

const fail = [];
const noted = [];

// ── 例外清单
let exceptions = [];
try {
  exceptions = JSON.parse(await readFile(path.join(REPO, 'adapter', 'vendor-exceptions.json'), 'utf8')).exceptions || [];
} catch { /* 无例外文件即无例外 */ }
const isExcepted = (file, kind) => exceptions.some((x) => x.path === file && x.kind === kind);

// ── ① 密钥 / 敏感信息扫描
const SECRET_PATTERNS = [
  { kind: '① 密钥', re: /\bsk-[A-Za-z0-9]{16,}/g, why: 'OpenAI 风格密钥' },
  { kind: '① 密钥', re: /\b(api[_-]?key|apikey|secret|password|passwd)\s*[:=]\s*["']?[A-Za-z0-9\-_\.]{16,}/gi, why: '疑似硬编码凭据' },
  { kind: '① 密钥', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/g, why: '私钥' },
  // 只拦「公网 IP」——内网 10./172.16-31./192.168. 是文档里正当出现的
  { kind: '① 密钥', re: /\b(?!10\.)(?!192\.168\.)(?!172\.(?:1[6-9]|2\d|3[01])\.)(?:\d{1,3}\.){3}\d{1,3}\b/g, why: '公网 IP（节点登录信息不得入材料）' },
  { kind: '① 密钥', re: /\b(?:ssh|scp)\s+(-\S+\s+)*\S+@\S+/g, why: 'SSH/SCP 连接串（节点登录信息）' },
  // ⚠️ 2026-09-27 更正：端口号（含 9018）是赛事交付给我们的，可写进文档；
  //    只有「IP + 端口 + 用户名」凑齐才构成登录信息，所以这里不单拦端口。
];
// 文档里正当出现的占位/公开域名/内网段不算命中
const ALLOW_LINE = [
  /127\.0\.0\.1/, /0\.0\.0\.0/, /localhost/,
  /\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/, /192\.168\./, /172\.(?:1[6-9]|2\d|3[01])\./,
  /your[_-]?endpoint/i, /<[^>]*>/, /example\.com/i,
  /api\.stepfun\.com/, /api\.deepseek\.com/, /inference-api\.nvidia\.com/,
  // 环境变量注入是正确姿势，不是硬编码（2026-09-29 修正误报）
  /(api[_-]?key|apikey|secret|password|token)\s*[:=]\s*["']?(process\.env|fileEnv|getenv|os\.environ|window\.)/i,
  /\$\{[A-Za-z_][A-Za-z0-9_]{3,}\}/,
];

const files = await walk(REPO);
const TEXT_EXT = /\.(mjs|js|ts|json|md|sh|yaml|yml|txt|py|csv|tsv|html|css)$/i;
const textFiles = files.filter((f) => TEXT_EXT.test(f) && !/pre-push-check\.mjs$/.test(f));
let hits = 0, exceptedHits = 0;
for (const f of textFiles) {
  const text = await readFile(path.join(REPO, f), 'utf8').catch(() => '');
  for (const line of text.split(/\r?\n/)) {
    for (const p of SECRET_PATTERNS) {
      p.re.lastIndex = 0;
      if (!p.re.test(line)) continue;
      if (ALLOW_LINE.some((a) => a.test(line))) continue;
      if (isExcepted(f, p.kind)) { exceptedHits++; noted.push(`[例外] ${f} —— ${p.why}（已登记：官方测试样例）`); continue; }
      hits++;
      fail.push(`[① 密钥] ${f}: ${p.why} —— ${line.trim().slice(0, 110)}`);
    }
  }
}
console.log(`① 密钥扫描：扫了 ${textFiles.length} 个文本文件（仓库共 ${files.length} 个文件）· 命中 ${hits} 处 · 已登记例外 ${exceptedHits} 处`);
console.log(`   扫描根目录：${REPO}`);

// ── ② 官方文件未改动 + 自研技能完整性（LOCK.self）
let lockOk = 0, lockBad = 0, commit = '(无 LOCK.json)';
try {
  const lock = JSON.parse(await readFile(path.join(REPO, 'LOCK.json'), 'utf8'));
  commit = lock.commit;
  for (const [skill, entry] of Object.entries(lock.skills)) {
    const dir = path.join(REPO, 'vendor', 'nvidia-skills', skill);
    const have = await walk(dir);
    for (const [f, hash] of Object.entries(entry.files)) {
      if (!have.includes(f)) { lockBad++; fail.push(`[② 官方文件] 缺失 ${skill}/${f}`); continue; }
      if (sha256(await readFile(path.join(dir, f))) !== hash) { lockBad++; fail.push(`[② 官方文件] 被改动 ${skill}/${f}`); }
      else lockOk++;
    }
    for (const f of have) if (!(f in entry.files)) { lockBad++; fail.push(`[② 官方文件] 多出 ${skill}/${f}`); }
  }
  if (lock.self && lock.self.skills_src) {
    const want = lock.self.skills_src;
    const have = await walk(path.join(REPO, 'skills-src'));
    for (const [f, hash] of Object.entries(want)) {
      if (!have.includes(f)) { lockBad++; fail.push(`[② 自研] 缺失 skills-src/${f}`); continue; }
      if (sha256(await readFile(path.join(REPO, 'skills-src', f))) !== hash) { lockBad++; fail.push(`[② 自研] 被改动 skills-src/${f}`); }
      else lockOk++;
    }
    for (const f of have) if (!(f in want)) { lockBad++; fail.push(`[② 自研] 多出 skills-src/${f}（先跑 lock-self.mjs）`); }
  }
} catch (e) {
  lockBad++; fail.push(`[② 官方文件] 读不到 LOCK.json：${e.message}`);
}
console.log(`② 官方文件核对：${lockOk} 个一致 · ${lockBad} 个异常（LOCK @ ${String(commit).slice(0, 12)}）`);

// ── ③ 自研 skill frontmatter 契约
const REQUIRED = ['name', 'description', 'license', 'allowed-tools', 'version'];
const selfSkills = (await readdir(SELF_SRC, { withFileTypes: true }).catch(() => []))
  .filter((e) => e.isDirectory() && !e.name.startsWith('_')).map((e) => e.name);
let contractOk = 0;
const gaps = [];
for (const s of selfSkills) {
  const text = await readFile(path.join(SELF_SRC, s, 'SKILL.md'), 'utf8').catch(() => null);
  if (!text) { gaps.push(`${s}: 没有 SKILL.md`); continue; }
  const fm = (text.match(/^---\r?\n([\s\S]*?)\r?\n---/) || [])[1] || '';
  const miss = REQUIRED.filter((k) => !new RegExp(`^${k}\\s*:`, 'm').test(fm));
  if (miss.length) gaps.push(`${s}: 缺 ${miss.join(', ')}`);
  else contractOk++;
}
console.log(`③ 自研 skill 契约：${selfSkills.length} 个 skill · ${contractOk} 个完整`);
for (const g of gaps) noted.push(`[③ 待补] ${g}`);

// ── 结论
if (noted.length) {
  console.log('\n📌 备注（不拦，但要处理）：');
  for (const n of noted) console.log('  ' + n);
}
console.log('');
if (fail.length) {
  console.log(`❌ 闸门不通过：${fail.length} 项`);
  for (const f of fail) console.log('  ' + f);
  console.log('\n修完再推。绝不 --force、绝不 --no-verify。');
  process.exit(1);
}
console.log('✅ 三道闸全过，可以推送。');
