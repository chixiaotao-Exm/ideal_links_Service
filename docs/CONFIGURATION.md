# 配置说明

本项目通过环境变量配置代理、队列、支付参数和外部接口。推荐复制 `.env.example` 为 `.env`，只在服务器本地保存真实配置。

## 基础配置

| 变量 | 默认值 | 说明 |
|---|---:|---|
| `OPENAI_PAY_QUEUE_TASK_INTERVAL_SECONDS` | `30` | 后台队列任务间隔。 |
| `OPENAI_PAY_VIRTUAL_QUEUE_MIN` | `2` | 前端展示的最小虚拟排队数。 |
| `OPENAI_PAY_VIRTUAL_QUEUE_MAX` | `17` | 前端展示的最大虚拟排队数。 |
| `OPENAI_PAY_CHECKOUT_ATTEMPTS` | `5` | checkout 创建重试次数。 |
| `OPENAI_PAY_STRIPE_INIT_ATTEMPTS` | `3` | Stripe 初始化重试次数。 |
| `OPENAI_PAY_PROXY_REGION_CHECK_ATTEMPTS` | `2` | 代理地区校验重试次数。 |

## 代理配置

| 变量 | 说明 |
|---|---|
| `OPENAI_PAY_DEFAULT_PROXY` | 默认代理。前端不填代理时使用。 |
| `OPENAI_PAY_PROVIDER_PROXY` | Provider 阶段代理。 |
| `OPENAI_PAY_GOPAY_PROVIDER_PROXY` | GoPay Provider 阶段代理。 |
| `OPENAI_PAY_711_REFRESH_URLS` | 代理刷新 URL JSON。 |

代理格式示例：

```text
http://proxy.example.com:8080
socks5://proxy.example.com:1080
```

如果代理需要账号密码，请只写在服务器 `.env` 或系统环境变量里，不要写进 README、Issue、PR 或截图。

`OPENAI_PAY_711_REFRESH_URLS` 示例：

```json
{"JP":"https://proxy-provider.example/refresh?region=JP","NL":"https://proxy-provider.example/refresh?region=NL"}
```

## 邮箱接口配置

| 变量 | 说明 |
|---|---|
| `ICLOUD_MAIL_LOOKUP_URL` | 可选邮箱查询接口。 |
| `ICLOUD_MAIL_API_KEY` | 可选邮箱接口密钥。 |
| `ICLOUD_MAIL_PURCHASE_URL` | 前端展示的购买/获取邮箱链接。 |

## Stripe 配置

| 变量 | 说明 |
|---|---|
| `OPENAI_PAY_STRIPE_PUBLISHABLE_KEY` | Stripe Publishable Key。公开仓库中只保留占位值，部署时自行填写。 |
| `OPENAI_PAY_PAYPAL_STRIPE_RUNTIME_VERSION` | PayPal 链路使用的 Stripe runtime version。 |

## CDK 与插队卡

CDK 和插队卡数据保存在 `data/cdk.sqlite3`。请确保部署时保留 `data/` 目录，Docker 部署时保留 volume 挂载。

- `/api/cdk/create`：创建 CDK 或增加 CDK 次数，仅允许服务器本机调用。
- `/api/cdk/status`：查询 CDK 状态。
- `/api/priority-card/create`：创建插队卡或增加插队卡次数，仅允许服务器本机调用。

## 不要提交的文件

- `.env`
- `access_token.txt`
- `data/*.sqlite*`
- `run-output/`
- `*.log`
- 真实代理配置、API Key、Access Token、session JSON、CDK 数据、支付长链

---

<!-- project-footer:start -->
<p align="center">
  <a href="https://github.com/chixiaotao-Exm/ideal_links_Service" target="_blank" rel="noopener noreferrer">
    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="20" height="20" alt="GitHub" />
    ideal_links_Service
  </a>
</p>
<!-- project-footer:end -->
