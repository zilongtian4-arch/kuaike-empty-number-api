#!/usr/bin/env bash
# 快客检测 空号检测 API 示例（curl）
# 用法：export KUAIKE_API_KEY=您的密钥 && bash examples.sh
# 接口文档：https://kuaikejiance.com/api-docs
set -eu
BASE="${KUAIKE_API_BASE:-https://kuaikejiance.com/open/v1}"
AUTH="Authorization: Bearer ${KUAIKE_API_KEY:?请先设置 KUAIKE_API_KEY}"

echo "== 查询额度"
curl -s "$BASE/balance" -H "$AUTH"; echo

echo "== 实时检测（即查即回，1~20 个号码）"
curl -s -X POST "$BASE/realtime/check" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"phones": ["13800138000"], "requestId": "demo-realtime-0001"}'; echo

# == 空号检测（一批至少 2,000 个号码；这里演示接口用法）
# 1. 提交，返回 data.taskId
#   curl -s -X POST "$BASE/empty/tasks" -H "$AUTH" -H "Content-Type: application/json" \
#     -d '{"phones": ["13800138000", "..."], "requestId": "order-20260101-0001"}'
# 2. 每 5~10 秒查一次进度，直到 status 为 done
#   curl -s "$BASE/empty/tasks/任务编号" -H "$AUTH"
# 3. 取某一类号码：active 实号 / empty 空号 / silent 沉默号 / risk 风险号 / stopped 停机 / unknown 未知
#   curl -s "$BASE/empty/tasks/任务编号/result?kind=empty" -H "$AUTH"
#
# 高级空号检测把地址里的 /empty/ 换成 /empty-plus/ 即可。
