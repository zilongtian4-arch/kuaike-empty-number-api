// 快客检测 空号检测 API 示例（Node.js 18+，无需安装依赖）
// 用法：
//   export KUAIKE_API_KEY=您的密钥
//   node kuaike-api.mjs balance
//   node kuaike-api.mjs empty numbers.txt         # 空号检测（每行一个号码，至少 2000 个）
//   node kuaike-api.mjs realtime 13800138000      # 实时检测，即查即回
// 接口文档：https://kuaikejiance.com/api-docs
import { readFileSync, writeFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';

const BASE = process.env.KUAIKE_API_BASE || 'https://kuaikejiance.com/open/v1';
const KEY = process.env.KUAIKE_API_KEY;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function call(method, path, body, retries = 3) {
  for (let attempt = 0; ; attempt++) {
    let res, json;
    try {
      res = await fetch(BASE + path, {
        method,
        headers: { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(30000),
      });
      json = await res.json().catch(() => ({ code: res.status, message: res.statusText }));
    } catch (e) {
      if (attempt < retries) { await sleep(1000 * 2 ** attempt); continue; } // 同一个 requestId 重试不会重复扣额度
      throw new Error(`网络异常：${e.message}`);
    }
    if ((res.status === 429 || res.status >= 500) && attempt < retries) { await sleep(1000 * (attempt + 1)); continue; }
    if (!res.ok || json.code !== 0) throw new Error(`HTTP ${res.status} code=${json.code} ${json.message || ''}`);
    return json.data;
  }
}

export const balance = () => call('GET', '/balance');
export const submit = (phones, kind = 'empty', requestId = randomUUID()) =>
  call('POST', `/${kind}/tasks`, { phones, requestId }).then((d) => d.taskId);
export const task = (taskId, kind = 'empty') => call('GET', `/${kind}/tasks/${taskId}`);
export const result = (taskId, which, kind = 'empty') =>
  call('GET', `/${kind}/tasks/${taskId}/result?kind=${which}`).then((d) => d.phones);
export const realtimeCheck = (phones, requestId = randomUUID()) => call('POST', '/realtime/check', { phones, requestId });

export async function wait(taskId, kind = 'empty', intervalMs = 8000) {
  for (;;) {
    const t = await task(taskId, kind);
    console.error(`  进度 ${t.done}/${t.total}  状态 ${t.status}`);
    if (t.status === 'done' || t.status === 'failed') return t;
    await sleep(intervalMs);
  }
}

async function main() {
  if (!KEY) throw new Error('请先设置 KUAIKE_API_KEY');
  const [cmd, ...args] = process.argv.slice(2);
  if (cmd === 'balance') console.log(await balance());
  else if (cmd === 'empty' || cmd === 'empty-plus') {
    const phones = readFileSync(args[0], 'utf8').split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
    const taskId = await submit(phones, cmd);
    console.error('已提交，任务编号', taskId);
    const t = await wait(taskId, cmd);
    console.log(JSON.stringify(t, null, 2));
    if (t.status === 'done') {
      for (const [which, n] of Object.entries(t.counts || {})) {
        if (!n) continue;
        const out = `${taskId}_${which}.txt`;
        writeFileSync(out, (await result(taskId, which, cmd)).join('\n') + '\n');
        console.error(`  ${which}：${n} 个 → ${out}`);
      }
    }
  } else if (cmd === 'realtime') console.log(JSON.stringify(await realtimeCheck(args), null, 2));
  else console.log('用法：node kuaike-api.mjs balance | empty <文件> | empty-plus <文件> | realtime <号码...>');
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => { console.error('调用失败：', e.message); process.exit(1); });
}
