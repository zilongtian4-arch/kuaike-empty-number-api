# 快客检测 空号检测 API 接口

[![官网](https://img.shields.io/badge/官网-kuaikejiance.com-1677ff)](https://kuaikejiance.com/)
[![接口文档](https://img.shields.io/badge/接口文档-api--docs-07875f)](https://kuaikejiance.com/api-docs)
[![License: MIT](https://img.shields.io/badge/示例代码-MIT-lightgrey)](LICENSE)

快客检测（[kuaikejiance.com](https://kuaikejiance.com/)）提供的空号检测接口：**空号检测、高级空号检测、实时空号检测**。标准 HTTPS + JSON，用任何编程语言都能调用。

本仓库提供接口说明和可以直接运行的示例代码（curl、Python、Node.js、Java、PHP、Go）。完整、最新的参数以官网 [接口文档](https://kuaikejiance.com/api-docs) 为准。

> English: HTTP/JSON API for detecting empty (disconnected) mainland China mobile numbers: batch check (empty / active / silent / risk) and real-time line status. Docs: https://kuaikejiance.com/api-docs

---

## 能做什么

| 接口 | 用途 | 返回 |
|---|---|---|
| 空号检测 | 批量筛空号，量大先整体筛一遍 | 实号、空号、沉默号、风险号、停机、未知 |
| 高级空号检测 | 逐个号码核验，检测结果更准确 | 实号、空号、沉默号、风险号、未知 |
| 实时空号检测 | 查号码此刻的状态 | 正常、空号、停机、关机、通话中、携号转网等 |

常见用法：短信群发前过滤空号、电销外呼前清洗号码、CRM 入库前自动检测、给自己的平台接入号码检测能力。

## 快速开始

1. 在 [快客检测](https://kuaikejiance.com/register) 免费注册，完成实名认证（新账号有测试额度）。
2. 登录后创建 API 密钥，或 [联系客服](https://kuaikejiance.com/contact) 开通接口。
3. 先查一下可用额度，确认密钥可用：

```bash
curl https://kuaikejiance.com/open/v1/balance \
  -H "Authorization: Bearer 您的密钥"
```

```json
{ "code": 0, "data": { "quota": 128500, "paidQuota": 100000, "giftQuota": 28500 } }
```

## 通用约定

- 接口地址统一以 `https://kuaikejiance.com/open/v1` 开头，全部使用 HTTPS，数据格式 JSON（UTF-8）。
- 每次请求在请求头带上 `Authorization: Bearer 您的密钥`。
- 成功时 `code` 为 `0`，结果在 `data` 里；失败时 `code` 不为 0，`message` 是中文原因。
- 号码放在 `phones` 数组里，只支持 **11 位中国大陆手机号**；带 `+86`、空格、短横线会自动去掉。
- `requestId`（可选，8~64 位字母、数字、下划线、短横线）：同一个编号重复提交只处理一次、只扣一次额度。网络超时不确定是否成功时，用同一个 `requestId` 重试即可。
- 每个密钥每秒最多 20 次请求，超过返回 HTTP 429，等 1 秒再试。
- 额度单位是“条”，每次调用实际扣了多少看返回里的 `chargedQuota`。

## 接口一览

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | `/balance` | 查询可用额度 |
| POST | `/empty/tasks` | 空号检测：提交任务（单次 2,000 ~ 200,000 个，去重后） |
| GET | `/empty/tasks/{taskId}` | 空号检测：查询进度和各类数量 |
| GET | `/empty/tasks/{taskId}/result?kind=empty` | 空号检测：取某一类号码 |
| POST | `/empty-plus/tasks` | 高级空号检测：提交任务（单次最多 200,000 个） |
| GET | `/empty-plus/tasks/{taskId}` | 高级空号检测：查询进度 |
| GET | `/empty-plus/tasks/{taskId}/result?kind=empty` | 高级空号检测：取某一类号码 |
| POST | `/realtime/check` | 实时检测：即查即回，单次 1 ~ 20 个 |
| POST | `/realtime/tasks` | 实时检测：批量任务，单次最多 100,000 个 |
| GET | `/realtime/tasks/{taskId}` | 实时检测：查询进度 |
| GET | `/realtime/tasks/{taskId}/result?offset=0&limit=1000` | 实时检测：分页取结果 |

每个接口的请求参数、返回字段和取值说明见 [docs/接口说明.md](docs/接口说明.md)。

## 示例：批量空号检测（提交 → 等待 → 取结果）

```bash
# 1. 提交
curl -X POST https://kuaikejiance.com/open/v1/empty/tasks \
  -H "Authorization: Bearer 您的密钥" \
  -H "Content-Type: application/json" \
  -d '{"phones": ["13800138000", "13912345678"], "requestId": "order-20260101-0001"}'
# 返回 data.taskId

# 2. 每 5~10 秒查一次进度，直到 status 为 done
curl https://kuaikejiance.com/open/v1/empty/tasks/任务编号 \
  -H "Authorization: Bearer 您的密钥"

# 3. 取空号
curl "https://kuaikejiance.com/open/v1/empty/tasks/任务编号/result?kind=empty" \
  -H "Authorization: Bearer 您的密钥"
```

完整的可运行代码：

| 语言 | 文件 |
|---|---|
| curl | [examples/curl/examples.sh](examples/curl/examples.sh) |
| Python 3 | [examples/python/kuaike_api.py](examples/python/kuaike_api.py) |
| Node.js 18+ | [examples/nodejs/kuaike-api.mjs](examples/nodejs/kuaike-api.mjs) |
| Java 11+ | [examples/java/KuaikeApiExample.java](examples/java/KuaikeApiExample.java) |
| PHP 7.4+ | [examples/php/kuaike_api.php](examples/php/kuaike_api.php) |
| Go 1.18+ | [examples/go/main.go](examples/go/main.go) |

所有示例都从环境变量 `KUAIKE_API_KEY` 读取密钥，不要把密钥写进代码或提交到仓库。

## 推荐用法

| 接口 | 每次提交多少号码 | 同时发几个请求 | 多久查一次进度 |
|---|---|---|---|
| 空号检测 | 5,000 ~ 100,000 个一批（最少 2,000，最多 200,000） | 1 ~ 2 个任务 | 每 5 ~ 10 秒 |
| 高级空号检测 | 5,000 ~ 50,000 个一批（最多 200,000） | 1 ~ 2 个任务 | 每 5 ~ 10 秒 |
| 实时检测（批量任务） | 1,000 ~ 20,000 个一批（最多 100,000） | 1 ~ 2 个任务 | 每 3 ~ 5 秒 |
| 实时检测（即查即回） | 1 ~ 20 个 | 不超过 5 个 | 不需要，直接返回 |

- 能批量就批量：把号码攒成一批再提交，比一个号码发一次请求快得多，也不会触发限速。
- 并发不用开高：批量任务提交后由平台并行检测，多开并发不会更快。
- 每次都带 `requestId`，超时重试不会重复扣额度。
- 即查即回建议把请求超时设为 30 秒；批量任务提交后立即返回，用“查询进度”接口等待完成。

## 常见问题

**支持国外号码、固话吗？** 目前只支持 11 位中国大陆手机号。

**没检测出结果会扣额度吗？** 高级空号检测的“未知”、实时检测的“未检出”和“暂不支持该号段”不扣额度。

**密钥泄露了怎么办？** 在网站上删除旧密钥、重新创建。密钥只在创建时显示一次，可以限制只允许指定 IP 调用。

**不想写代码可以用吗？** 可以。登录 [快客检测](https://kuaikejiance.com/) 网页版，上传 TXT、CSV、Excel 文件即可批量检测。

**价格？** 按条计费。参考价格见 [空号检测多少钱？怎么收费](https://kuaikejiance.com/help/konghao-jiance-zenme-shoufei/)，用量大可以 [联系客服](https://kuaikejiance.com/contact) 谈价。

## 使用规则

- 账号需提交实名认证并通过审核后才能使用，未满 18 周岁不可使用。
- 调用接口即表示您确认：对提交的号码拥有合法的处理依据，并遵守 [使用协议](https://kuaikejiance.com/terms) 和 [隐私政策](https://kuaikejiance.com/privacy)。

## 联系

- 官网：https://kuaikejiance.com/
- 接口文档：https://kuaikejiance.com/api-docs
- 帮助中心：https://kuaikejiance.com/help/
- 联系客服：https://kuaikejiance.com/contact

本仓库的示例代码以 MIT 协议开源，可以直接复制到您的项目里使用。
