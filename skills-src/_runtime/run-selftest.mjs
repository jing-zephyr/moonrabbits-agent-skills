// 适配层自检 —— 跑一次真实调用，验证 key / 端点 / max_tokens 坑处理
import { selfTest, chat, CONFIG } from './stepfun.mjs'

console.log('===== ① 配置自检 =====')
const r = await selfTest()
console.log(JSON.stringify(r, null, 2))

console.log('\n===== ② 验证"推理模型 max_tokens 坑"的处理 =====')
// 故意给很小的 max_tokens（16）——不重试时会拿到空 content
const tiny = await chat({
  messages: [{ role: 'user', content: '用一句话说明什么是 Agent Skills。' }],
  maxTokens: 16,
  retryOnEmpty: false,
})
console.log('  max_tokens=16 且不重试 → content 长度 =', tiny.content.length, '｜ reasoning 长度 =', tiny.reasoning.length, tiny.content ? '（意外：有内容）' : '（符合预期：content 为空）')

const fixed = await chat({
  messages: [{ role: 'user', content: '用一句话说明什么是 Agent Skills。' }],
  maxTokens: 16,          // 给 16
  retryOnEmpty: true,     // 让模块自动放大重试
})
console.log('  同一请求 + 自动重试 → content 长度 =', fixed.content.length, '｜ 是否触发重试 =', fixed.retried)
console.log('  回复:', fixed.content.slice(0, 80))

console.log('\n===== ③ 端点确认 =====')
console.log('  当前端点:', CONFIG.baseUrl, '（step_plan = 走订阅额度）')
console.log('  模型:', CONFIG.defaultModel)
