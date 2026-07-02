# iDEAL2 Long Link Service

一个可自托管的 FastAPI + Web 前端项目，用于生成、管理和调试支付长链与支付二维码。它把长链生成、代理链路选择、CDK 次数管理、插队卡、二维码记录、值守端、支付方式检测和 API 调用封装成一个轻量面板，适合个人、团队或自动化系统部署使用。

## 核心功能

### 支付长链与二维码

- 生成可复制、可打开的支付长链。
- 将任意长链生成二维码，方便移动端扫码打开。
- 支持前端页面操作，也支持 HTTP API 调用。
- 支持后台任务队列，前端可以轮询任务进度。

### 多链路类型

- `hosted`：标准 `pay.openai.com` 长链。
- `iDEAL`：荷兰 iDEAL 链路。
- `PayPal`：PayPal 链路提取。
- `GoPay`：印尼 GoPay 链路提取。

### CDK 次数系统

- 创建 CDK。
- 给已有 CDK 增加次数。
- 查询 CDK 剩余次数、总次数、已使用次数。
- 可选绑定 QQ 或其他用户标识。
- 用户生成长链时可校验并扣减 CDK 次数。
- 任务失败时可按逻辑退回次数，避免误扣。

### 插队卡 / 优先级

- 创建插队卡。
- 给插队卡增加次数。
- 生成任务时可使用插队卡提升优先级。
- 适合多人共享部署时给特定用户优先处理。

### 值守端 / 多人抢单

- 内置值守端页面：`/admin/qr`。
- 值守员填写自己的值守名后，可以查看订单池和自己的订单。
- 支持随机抢单：从未认领、未支付、未过期的二维码记录中随机分配一单。
- 支持自动抢单：值守员当前没有未完成订单时，系统可自动从订单池分配。
- 支持手动认领、释放认领、按值守员隔离展示。
- 支持每 3 秒轮询订单池、队列状态和支付状态。
- 支持二维码放大查看，支付完成后自动更新状态。

### 代理链路调度

- 支持自定义代理。
- 支持默认后台代理。
- 支持前段代理、后段代理、approve 阶段代理。
- 支持 JP、NL、US、BR、ID 等地区预设。
- 支持代理出口检测，方便确认代理是否可用。
- 支持多策略并发/顺序测试，例如 JP→NL、NL→NL、US→US 等组合。

### 支付方式检测

- 一键检测当前账号/地区可用的支付方式。
- 支持 PayPal 国家轮询。
- 可用于调试不同代理出口、不同账单地区下的支付能力。

### 二维码记录与管理

- 保存已生成的长链记录。
- 查看最近生成的二维码记录。
- 可标记/领取记录，适合多人协作处理。
- 可刷新记录的支付状态。
- 可把指定任务生成的 iDEAL 长链保存为二维码记录。

### 诊断与排错

- 可选开启诊断输出。
- 记录关键请求阶段、代理阶段、支付阶段和错误摘要。
- 用于定位代理不可用、checkout 创建失败、Stripe 初始化失败、支付状态异常等问题。

## 适用场景

- 自己部署一个支付长链生成面板。
- 给团队或用户提供带 CDK 次数限制的自助工具。
- 用 API 接入机器人、后台系统、发卡系统或其他管理面板。
- 调试不同地区代理下的支付链路和支付方式。
- 将长链生成二维码并保存历史记录。
- 多人共享部署时，用 CDK 和插队卡控制使用量与优先级。
- 多个值守员同时处理二维码订单，自动分配、认领、释放和查看各自订单。

## 项目结构

```text
.
├── app.py                    # FastAPI 后端主程序，包含前台和值守端页面
├── public/
│   ├── index.html            # Web 前端页面
│   ├── ideal2-api-doc.md     # API 文档
│   └── api-docs.html         # API 文档 HTML 版本
├── data/
│   └── README.md             # 运行时数据目录说明
├── docs/
│   ├── CONFIGURATION.md      # 配置说明
│   └── SECURITY.md           # 安全与隐私检查
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```

## 快速开始：本地运行

要求：Python 3.10+。

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8791 --no-access-log
```

打开前台：

```text
http://127.0.0.1:8791/
```

打开值守端：

```text
http://127.0.0.1:8791/admin/qr
```

健康检查：

```text
http://127.0.0.1:8791/api/health
```

## 快速开始：Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
```

默认监听：

```text
http://127.0.0.1:8791/
```

## 常用配置

复制 `.env.example` 为 `.env`，按需填写：

| 变量 | 作用 |
|---|---|
| `OPENAI_PAY_DEFAULT_PROXY` | 默认出口代理，留空则不使用默认代理。 |
| `OPENAI_PAY_PROVIDER_PROXY` | Provider 阶段代理，适合需要第二阶段切换出口的链路。 |
| `OPENAI_PAY_GOPAY_PROVIDER_PROXY` | GoPay Provider 阶段代理。 |
| `OPENAI_PAY_711_REFRESH_URLS` | 代理刷新 URL JSON，例如按国家/地区刷新代理会话。 |
| `OPENAI_PAY_STRIPE_PUBLISHABLE_KEY` | Stripe Publishable Key，占位值需要自行替换。 |
| `ICLOUD_MAIL_LOOKUP_URL` | 可选邮箱查询接口。 |
| `ICLOUD_MAIL_API_KEY` | 可选邮箱接口密钥。 |
| `ICLOUD_MAIL_PURCHASE_URL` | 前端提示用户购买/获取邮箱的链接。 |
| `OPENAI_PAY_QUEUE_TASK_INTERVAL_SECONDS` | 后台队列任务执行间隔。 |
| `OPENAI_PAY_VIRTUAL_QUEUE_MIN` / `OPENAI_PAY_VIRTUAL_QUEUE_MAX` | 前端展示队列范围。 |

更多说明见 [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)。

## 常用 API 示例

### 健康检查

```bash
curl "http://127.0.0.1:8791/api/health"
```

### 创建 CDK

CDK 创建接口只允许服务器本机调用，适合在服务器后台、管理脚本或内网管理面板中使用。

```bash
curl -X POST "http://127.0.0.1:8791/api/cdk/create" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "CDK-XXXX-XXXX-XXXX",
    "total": 10,
    "qq": ""
  }'
```

字段说明：

| 字段 | 说明 |
|---|---|
| `code` | CDK 码。不存在则创建，已存在则增加次数。 |
| `total` | 本次新增次数。 |
| `qq` | 可选绑定用户标识。 |

### 查询 CDK 状态

```bash
curl "http://127.0.0.1:8791/api/cdk/status?code=CDK-XXXX-XXXX-XXXX"
```

返回内容包含总次数、剩余次数、已用次数、绑定状态等信息。

### 创建插队卡

插队卡创建接口同样只允许服务器本机调用。

```bash
curl -X POST "http://127.0.0.1:8791/api/priority-card/create" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "PRIORITY-XXXX-XXXX",
    "total": 5,
    "qq": ""
  }'
```

### 创建 iDEAL 提链任务

```bash
curl -X POST "http://127.0.0.1:8791/api/extract/ideal" \
  -H "Content-Type: application/json" \
  -d '{
    "accessToken": "<your-access-token>",
    "cdkCode": "CDK-XXXX-XXXX-XXXX",
    "checkoutProxyRegion": "JP",
    "providerProxyRegion": "NL"
  }'
```

### 查询任务状态

```bash
curl "http://127.0.0.1:8791/api/extract/ideal/<job_id>"
```

### 保存任务二维码记录

当任务已经生成 iDEAL 长链后，可以把该任务保存到二维码记录池，供值守端处理。

```bash
curl -X POST "http://127.0.0.1:8791/api/qr-records/from-job/<job_id>"
```

### 生成二维码

```text
http://127.0.0.1:8791/api/qr?text=<url-encoded-long-url>
```

### 查看二维码记录 / 订单池

```bash
curl "http://127.0.0.1:8791/api/qr-records?limit=80&refresh=1"
```

### 值守员随机抢单

```bash
curl -X POST "http://127.0.0.1:8791/api/qr-records/grab" \
  -H "Content-Type: application/json" \
  -d '{
    "watcher": "值守员A"
  }'
```

### 认领或释放二维码记录

认领：

```bash
curl -X POST "http://127.0.0.1:8791/api/qr-records/123/watcher" \
  -H "Content-Type: application/json" \
  -d '{
    "watcher": "值守员A",
    "action": "claim"
  }'
```

释放：

```bash
curl -X POST "http://127.0.0.1:8791/api/qr-records/123/watcher" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "release"
  }'
```

### 测试代理链路

```bash
curl -X POST "http://127.0.0.1:8791/api/proxy-chain-test" \
  -H "Content-Type: application/json" \
  -d '{
    "proxy": "http://proxy.example.com:8080",
    "link_type": "ideal",
    "checkoutProxyRegion": "JP",
    "providerProxyRegion": "NL"
  }'
```

完整接口说明见 [`public/ideal2-api-doc.md`](public/ideal2-api-doc.md)。

## 值守端使用流程

1. 打开 `http://127.0.0.1:8791/admin/qr`。
2. 输入自己的值守名。
3. 页面会自动轮询订单池、我的订单、我的已支付数量和队列状态。
4. 点击“自动抢单”或等待系统自动分配订单。
5. 点击二维码查看大图，扫码处理。
6. 支付状态会自动刷新；已支付、过期、失败或取消的订单会从可抢订单池中排除。
7. 如果抢错单，可以释放认领，让订单回到订单池。

## 数据与隐私

- 用户输入的 Access Token / session JSON 不应写入仓库。
- 运行时数据库位于 `data/`，默认已通过 `.gitignore` 排除。
- CDK、插队卡、二维码记录和值守认领信息都保存在运行时数据库中。
- 诊断输出位于 `run-output/`，默认已通过 `.gitignore` 排除。
- `.env`、代理地址、API Key、CDK 数据库和日志都不要提交到公开仓库。

## 开源发布前检查

```bash
git status --ignored
grep -RInE "(password|secret|token|authorization|cookie|proxy|sk_live_|xox[baprs]-|ghp_|github_pat_)" .
```

确认输出里没有真实 Token、代理账号密码、私有域名、数据库、日志或支付长链后再发布。

## 常见问题

### 1. 前端可以打开，但 API 请求失败？

先确认后端进程是否启动，并访问：

```text
http://127.0.0.1:8791/api/health
```

### 2. 代理测试失败？

先确认 `.env` 或前端输入的代理地址格式正确，服务器能访问代理出口，并且目标地区与前端选择一致。

### 3. CDK 一直显示无效？

CDK 数据存在 `data/cdk.sqlite3` 中。首次部署后需要先调用 `/api/cdk/create` 创建 CDK，或者通过你自己的管理面板写入 CDK。

### 4. 插队卡没有生效？

确认已经通过 `/api/priority-card/create` 创建插队卡，并且前端或 API 请求中填写了对应插队卡码。

### 5. 值守端没有订单？

先确认已经生成并保存了二维码记录。可以通过 `/api/qr-records/from-job/<job_id>` 保存任务结果，或通过前端生成完成后保存记录。订单已支付、过期、失败、取消或已被其他值守员认领时，不会出现在可抢订单池中。

### 6. Docker 启动后没有保留数据？

确认 `docker-compose.yml` 中挂载了：

```yaml
volumes:
  - ./data:/app/data
```

这样容器重启后 CDK、插队卡、二维码记录和值守认领信息才会保留。

## License

请按你的仓库实际授权方式补充 License，例如 MIT、Apache-2.0 或私有授权。

---

<!-- project-footer:start -->
<p align="center">
  <a href="https://github.com/chixiaotao-Exm/ideal_links_Service" target="_blank" rel="noopener noreferrer">
    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="20" height="20" alt="GitHub" />
    ideal_links_Service
  </a>
</p>
<!-- project-footer:end -->
