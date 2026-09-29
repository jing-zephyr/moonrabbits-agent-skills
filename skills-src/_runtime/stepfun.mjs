// stepfun.mjs —— StepFun（阶跃星辰）适配层
// 设计目标：**换模型只改 3 个值**（baseUrl / model / apiKey）；把实测踩到的坑固化进代码。
//
// 实测结论（2026-09-23，本机验证）：
//   1) 两个端点都可用：
//        · https://api.stepfun.com/v1            （标准 / 按量）
//        · https://api.stepfun.com/step_plan/v1  （**订阅额度**，Step Plan Pro 走这个）
//   2) `step-5-preview` 是【推理模型】：
//        · max_tokens 给太小（如 16）→ content 为空，token 全被 reasoning 吃掉
//        · **必须 max_tokens ≥ 256**（本模块默认 1024），并内置"空了就重试放大"逻辑
//   3) 返回的 message 里同时有 `content`（答案）与 `reasoning` / `reasoning_content`（思考链）
//        → 可据此做"可解释的可信生成"
//
// 密钥来源（按优先级）：
//   1) 环境变量 process.env.STEPFUN_API_KEY（推荐，永不落盘）
//   2) 由 STEPFUN_ENV_FILES 指定的库外文件（分号分隔的绝对路径列表，默认空 = 不读任何文件）
// ⚠️ 公开仓不携带任何本机路径；密钥文件路径只由使用者自己注入。
// ⚠️ 本模块**永不打印密钥**。

import { readFileSync, existsSync } from 'node:fs'

const ENV_CANDIDATES = (process.env.STEPFUN_ENV_FILES || '')
  .split(';')
  .map((s) => s.trim())
  .filter(Boolean)

function readEnvFile() {
  const out = {}
  for (const p of ENV_CANDIDATES) {
    if (!existsSync(p)) continue
    let txt = ''
    try { txt = readFileSync(p, 'utf8') } catch { continue }
    for (const line of txt.split(/\r?\n/)) {
      const t = line.trim()
      if (!t || t.startsWith('#')) continue
      const i = t.indexOf('=')
      if (i < 0) continue
      const k = t.slice(0, i).trim()
      if (!out[k]) out[k] = t.slice(i + 1).trim()
    }
  }
  return out
}

const fileEnv = readEnvFile()

export const CONFIG = {
  // 订阅额度优先走 step_plan；如需按量，把 ENDPOINT 换成 '/v1'
  baseUrl: process.env.STEPFUN_BASE_URL || fileEnv.STEPFUN_BASE_URL || 'https://api.stepfun.com/step_plan/v1',
  apiKey: process.env.STEPFUN_API_KEY || fileEnv.STEPFUN_API_KEY || '',
  defaultModel: process.env.STEPFUN_MODEL || 'step-5-preview',
  // 推理模型必须给足；缺省 1024
  defaultMaxTokens: Number(process.env.STEPFUN_MAX_TOKENS || 1024),
  timeoutMs: Number(process.env.STEPFUN_TIMEOUT_MS || 120000),
}

export function hasKey() { return Boolean(CONFIG.apiKey) }

/** 掩码显示（只用于自检输出，不泄露完整 key） */
export function maskKey(k = CONFIG.apiKey) {
  if (!k) return '(未配置)'
  return k.slice(0, 4) + '***' + k.slice(-3) + ' (len=' + k.length + ')'
}

async function post(path, body) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), CONFIG.timeoutMs)
  try {
    const r = await fetch(CONFIG.baseUrl + path, {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + CONFIG.apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })
    const text = await r.text()
    let json = null
    try { json = JSON.parse(text) } catch { /* 非 JSON */ }
    if (!r.ok) {
      const msg = json && json.error ? (json.error.message || JSON.stringify(json.error)) : text.slice(0, 300)
      const err = new Error('StepFun HTTP ' + r.status + ': ' + msg)
      err.status = r.status
      throw err
    }
    return json
  } finally {
    clearTimeout(timer)
  }
}

/**
 * 对话（文本 / 图文）
 * @returns {{content:string, reasoning:string, usage:object|null, model:string, retried:boolean}}
 */
export async function chat({
  messages,
  model = CONFIG.defaultModel,
  maxTokens = CONFIG.defaultMaxTokens,
  temperature,
  retryOnEmpty = true,
}) {
  const build = (mt) => {
    const body = { model, messages, max_tokens: mt }
    if (temperature != null) body.temperature = temperature
    return body
  }

  let json = await post('/chat/completions', build(maxTokens))
  let retried = false
  let msg = (json && json.choices && json.choices[0] && json.choices[0].message) || {}
  let content = msg.content || ''

  // ⚠️ 实测坑：推理模型在 max_tokens 太小时会把额度全花在 reasoning 上 → content 为空
  if (!content && retryOnEmpty) {
    retried = true
    const bigger = Math.max(maxTokens * 4, 1024)
    json = await post('/chat/completions', build(bigger))
    msg = (json && json.choices && json.choices[0] && json.choices[0].message) || {}
    content = msg.content || ''
  }

  return {
    content,
    reasoning: msg.reasoning || msg.reasoning_content || '',
    usage: json.usage || null,
    model: json.model || model,
    retried,
  }
}

/** 视觉：把本地图片转成 data URL 放进 messages（OpenAI 兼容多模态格式） */
export function imagePart(localPath, mime = 'image/jpeg') {
  const b64 = readFileSync(localPath).toString('base64')
  return { type: 'image_url', image_url: { url: 'data:' + mime + ';base64,' + b64 } }
}

/** 便捷：单轮文本问答 */
export async function ask(text, opts = {}) {
  return chat({ messages: [{ role: 'user', content: text }], ...opts })
}

/** 便捷：图文问答 */
export async function askWithImage(text, localPath, opts = {}) {
  return chat({
    messages: [{ role: 'user', content: [{ type: 'text', text }, imagePart(localPath)] }],
    ...opts,
  })
}

// ─────────────────────────────────────────────────────────────
// 以下为**待验证**能力（本轮未实测，接口形状按 OpenAI 兼容约定写，用前先跑一次）
// ─────────────────────────────────────────────────────────────

/**
 * 语音合成（TTS）—— ⏳ 待验证
 * 参考模型：stepaudio-3-tts / stepaudio-2.5-tts / step-tts-2
 */
export async function tts({ text, model = 'stepaudio-3-tts', voice, format = 'mp3' }) {
  const r = await fetch(CONFIG.baseUrl + '/audio/speech', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + CONFIG.apiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, input: text, voice, response_format: format }),
  })
  if (!r.ok) throw new Error('TTS HTTP ' + r.status + ': ' + (await r.text()).slice(0, 300))
  return Buffer.from(await r.arrayBuffer())
}

/**
 * 语音识别（ASR）—— ⏳ 待验证
 * 参考模型：stepaudio-3-asr-max / step-asr-1.1
 */
export async function asr({ localPath, model = 'stepaudio-3-asr-max', language = 'zh' }) {
  const form = new FormData()
  form.append('model', model)
  form.append('language', language)
  form.append('file', new Blob([readFileSync(localPath)]), localPath.split(/[\\/]/).pop())
  const r = await fetch(CONFIG.baseUrl + '/audio/transcriptions', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + CONFIG.apiKey },
    body: form,
  })
  if (!r.ok) throw new Error('ASR HTTP ' + r.status + ': ' + (await r.text()).slice(0, 300))
  return r.json()
}

/** 自检：打印配置与一次冒烟调用 */
export async function selfTest() {
  const out = {
    endpoint: CONFIG.baseUrl,
    key: maskKey(),
    model: CONFIG.defaultModel,
    maxTokens: CONFIG.defaultMaxTokens,
  }
  if (!hasKey()) return { ...out, ok: false, error: '未配置 STEPFUN_API_KEY' }
  try {
    const r = await ask('只回复两个字：通了', { maxTokens: 256 })
    return { ...out, ok: true, reply: r.content, reasoningChars: r.reasoning.length, usage: r.usage, retried: r.retried }
  } catch (e) {
    return { ...out, ok: false, error: String(e.message) }
  }
}
