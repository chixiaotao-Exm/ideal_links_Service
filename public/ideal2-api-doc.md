# iDEAL2 API 文档

本文档面向希望通过 HTTP API 集成本项目的开发者。你可以创建 iDEAL 提链任务、轮询任务状态、生成二维码、管理 QR 记录，并把这些能力接入自己的机器人、面板或后台系统。

基础地址：

```text
http://127.0.0.1:8791
```

## 1. 创建 iDEAL 提链任务

### 请求

```http
POST /api/extract/ideal
Content-Type: application/json
```

完整地址：

```text
http://127.0.0.1:8791/api/extract/ideal
```

### 请求参数

```json
{
  "accessToken": "ChatGPT Access Token",
  "cdkCode": "CDK-XXXX-XXXX-XXXX"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `accessToken` | string | 是 | ChatGPT Access Token |
| `cdkCode` | string | 是 | CDK，必须有剩余次数 |

### 请求示例

```bash
curl -X POST "http://127.0.0.1:8791/api/extract/ideal" \
  -H "Content-Type: application/json" \
  -d '{
    "accessToken": "eyJhbGciOi...",
    "cdkCode": "CDK-XXXX-XXXX-XXXX"
  }'
```

### 成功返回示例

```json
{
  "ok": true,
  "job_id": "0123456789abcdef0123456789abcdef",
  "status": "queued",
  "queue_position": 0,
  "queue_size": 17,
  "created_at": 1782740326,
  "created_at_iso": "2026-06-29T13:38:46+00:00"
}
```

| 字段 | 说明 |
|---|---|
| `ok` | 是否创建成功 |
| `job_id` | 任务 ID，后续轮询使用 |
| `status` | 任务状态 |
| `queue_position` | 当前排队位置 |
| `queue_size` | 当前队列数量 |
| `created_at` | 任务创建时间戳 |
| `created_at_iso` | ISO 格式创建时间 |

---

## 2. 查询任务状态 / 支付状态

### 请求

```http
GET /api/extract/ideal/{job_id}
```

完整地址示例：

```text
http://127.0.0.1:8791/api/extract/ideal/0123456789abcdef0123456789abcdef
```

### 请求示例

```bash
curl "http://127.0.0.1:8791/api/extract/ideal/0123456789abcdef0123456789abcdef"
```

建议前端每 `3 秒` 轮询一次。

### 等待中返回示例

```json
{
  "ok": true,
  "failed": false,
  "job_id": "0123456789abcdef0123456789abcdef",
  "task_status": "running",
  "queue_position": 0,
  "queue_size": 17,
  "long_url": "",
  "payment_status": "pending",
  "payment_label": "等待生成",
  "remaining_seconds": 0,
  "remaining_text": "--:--"
}
```

### 成功返回示例

```json
{
  "ok": true,
  "failed": false,
  "job_id": "0123456789abcdef0123456789abcdef",
  "task_status": "done",
  "long_url": "https://pay.ideal.nl/transactions/<redacted>?sig=<redacted>",
  "payment_status": "pending",
  "payment_label": "等待支付",
  "payment_view": "INITIAL_VIEW",
  "remaining_seconds": 815,
  "remaining_text": "13:35",
  "expires_at": 1782741226
}
```

### 已支付返回示例

```json
{
  "ok": true,
  "failed": false,
  "job_id": "0123456789abcdef0123456789abcdef",
  "task_status": "done",
  "long_url": "https://pay.ideal.nl/transactions/<redacted>?sig=<redacted>",
  "payment_status": "paid",
  "payment_label": "已支付",
  "payment_view": "CONFIRMED_VIEW",
  "remaining_seconds": 500,
  "remaining_text": "08:20"
}
```

### 失败返回示例

```json
{
  "ok": false,
  "failed": true,
  "job_id": "0123456789abcdef0123456789abcdef",
  "task_status": "error",
  "error": "checkout create failed: Billing country must match request country.",
  "last_error_step": {
    "time": "21:39:54",
    "name": "创建 ChatGPT checkout",
    "status": "fail",
    "detail": "Billing country must match request country."
  },
  "long_url": "",
  "payment_status": "pending",
  "payment_label": "等待生成"
}
```

---

## 3. 任务状态说明

| `task_status` | 说明 |
|---|---|
| `queued` | 排队中 |
| `running` | 正在提取 |
| `done` | 提取成功 |
| `error` | 提取失败 |

---

## 4. 支付状态说明

| `payment_status` | 说明 |
|---|---|
| `pending` | 等待支付 / 等待生成 |
| `paid` | 已支付 |
| `failed` | 支付失败 |
| `cancelled` | 已取消 |
| `expired` | 已过期 |
| `unsupported` | 非 iDEAL 链接，无法检测 |

---

## 5. 二维码生成方式

轮询任务接口成功后，会返回 `long_url`：

```json
{
  "task_status": "done",
  "long_url": "https://pay.ideal.nl/transactions/<redacted>?sig=<redacted><redacted-ideal-token>?sig=..."
}
```

前端需要把 `long_url` 进行 URL 编码，然后拼接到二维码接口：

```text
http://127.0.0.1:8791/api/qr?text=URL编码后的long_url
```

### JavaScript 示例

```js
const longUrl = data.long_url

const qrUrl =
  "http://127.0.0.1:8791/api/qr?text=" +
  encodeURIComponent(longUrl)
```

页面显示：

```html
<img src="二维码地址" />
```

完整示例：

```js
if (data.task_status === "done" && data.long_url) {
  const qrUrl =
    "http://127.0.0.1:8791/api/qr?text=" +
    encodeURIComponent(data.long_url)

  document.querySelector("#qr").src = qrUrl
}
```

### 示例二维码地址

假设 `long_url` 是：

```text
https://pay.ideal.nl/transactions/<redacted>?sig=<redacted><redacted-ideal-token>?sig=<redacted-signature>
```

拼接后的二维码地址是：

```text
http://127.0.0.1:8791/api/qr?text=<url-encoded-long_url><redacted-ideal-token>%3Fsig%3D<redacted-signature>
```

### 注意

二维码接口生成的不是普通网页二维码，后端会自动解析 iDEAL 长链内部的真实支付二维码内容。

前端只需要传 `long_url`，不要自己打开长链，也不要自己解析里面的二维码。

---

## 6. 前端推荐流程

```text
1. 用户提交 accessToken + cdkCode
2. POST /api/extract/ideal 创建任务
3. 拿到 job_id
4. 每 3 秒 GET /api/extract/ideal/{job_id}
5. task_status = done 时展示 long_url / 二维码
6. payment_status = pending 时显示等待支付
7. payment_status = paid 时显示已支付
8. task_status = error 时显示 error 错误信息
```

---

## 7. PowerShell 测试示例

```powershell
$body = @{
  accessToken = "你的AT"
  cdkCode = "CDK-XXXX-XXXX-XXXX"
} | ConvertTo-Json

$r = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8791/api/extract/ideal" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$r

Start-Sleep -Seconds 3

Invoke-RestMethod "http://127.0.0.1:8791/api/extract/ideal/$($r.job_id)"
```

---

## 8. 二维码后台多用户抢单接口

### 随机抢单

```http
POST /api/qr-records/grab
Content-Type: application/json
```

完整地址：

```text
http://127.0.0.1:8791/api/qr-records/grab
```

请求参数：

```json
{
  "watcher": "值守员A"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `watcher` | string | 是 | 当前值守员名称 |

说明：

```text
后端会从当前未认领、未支付、未过期、未失败、未取消的订单池里随机分配一个订单。
不是固定抢第一个订单。
```

成功返回：

```json
{
  "ok": true,
  "record": {
    "id": 1,
    "created_at": 1782742000,
    "job_id": "abc123",
    "qq": "190****049",
    "remaining": 998,
    "total": 999,
    "long_url": "https://pay.ideal.nl/transactions/<redacted>?sig=<redacted>",
    "status": "pending",
    "expires_at": 1782742900,
    "email_tag": "example",
    "watcher": "值守员A",
    "watcher_at": 1782742100
  }
}
```

没有可抢订单：

```json
{
  "ok": false,
  "detail": "当前没有可抢订单"
}
```

---

### 认领 / 释放指定订单

```http
POST /api/qr-records/{record_id}/watcher
Content-Type: application/json
```

认领请求：

```json
{
  "action": "claim",
  "watcher": "值守员A"
}
```

释放请求：

```json
{
  "action": "release"
}
```

成功返回：

```json
{
  "ok": true,
  "id": 1,
  "watcher": "值守员A",
  "watcher_at": 1782742100
}
```

---

### 获取二维码订单池记录

```http
GET /api/qr-records?limit=200&refresh=1
```

完整地址：

```text
http://127.0.0.1:8791/api/qr-records?limit=200&refresh=1
```

返回字段中新增：

| 字段 | 说明 |
|---|---|
| `watcher` | 当前认领该订单的值守员，空表示还在订单池 |
| `watcher_at` | 认领时间戳 |
| `display_status` | 后台展示状态 |
| `deduped` | 是否为重复邮箱订单 |

前端多用户隔离建议：

```text
1. 每个值守员先填写 watcher 名称。
2. 页面每 3 秒请求 /api/qr-records?limit=200&refresh=1。
3. 前端只展示 watcher 为空 或 watcher 等于当前值守员的订单。
4. 点击“随机抢单”调用 /api/qr-records/grab。
5. 点击二维码放大时，可以调用 /api/qr-records/{id}/watcher 自动认领。
6. 支付完成后，后台状态会变成 paid，前端可自动关闭放大二维码。
```

---

<!-- project-footer:start -->
<p align="center">
  <a href="https://github.com/chixiaotao-Exm/ideal_links_Service" target="_blank" rel="noopener noreferrer">
    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="20" height="20" alt="GitHub" />
    ideal_links_Service
  </a>
</p>
<!-- project-footer:end -->
