# 安全与隐私检查

公开仓库不应该包含任何真实运行环境数据。维护者在提交或发布前，请确认以下内容只存在于服务器本地或私有环境变量中。

## 禁止提交

- Access Token / session JSON
- `.env` 和任何真实环境变量文件
- 代理地址中的账号、密码、会话 ID
- API Key、Webhook Secret、Cookie、Authorization Header
- `data/*.sqlite*` 数据库
- `run-output/` 诊断输出
- `*.log` 日志
- 真实支付长链、订单号、二维码内容
- 私有域名、服务器 IP、SSH 配置

## 推荐做法

- 公开仓库只保留 `.env.example`。
- 所有真实配置放在 `.env`、系统环境变量或部署平台 Secret 中。
- 数据库和诊断文件放在运行时目录，不纳入 Git。
- 对外展示截图前，先遮盖 Token、代理、邮箱、订单号、支付链接。

## 快速扫描

```bash
grep -RInE "(password|secret|token|authorization|cookie|proxy|sk_live_|xox[baprs]-|ghp_|github_pat_)" .
```

这个扫描会有一些正常命中，例如 `.env.example`、README 中的变量名。重点检查命中行里是否出现真实值。

---

<!-- project-footer:start -->
<p align="center">
  <a href="https://github.com/chixiaotao-Exm/ideal_links_Service" target="_blank" rel="noopener noreferrer">
    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="20" height="20" alt="GitHub" />
    ideal_links_Service
  </a>
</p>
<!-- project-footer:end -->
