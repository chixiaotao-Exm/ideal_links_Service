# GitHub 发布与维护指南

这个文件给仓库维护者使用，普通用户只需要看 `README.md`。

## 首次发布

```bash
git init
git add .
git status
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

## 发布前检查清单

```bash
git status --ignored
grep -RInE "(password|secret|token|authorization|cookie|proxy|sk_live_|xox[baprs]-|ghp_|github_pat_)" .
```

确认：

- `.env` 没有被提交。
- `access_token.txt` 没有被提交。
- `data/*.sqlite*` 没有被提交。
- `run-output/`、日志、诊断文件没有被提交。
- 文档里只有 `example.com`、`<redacted>`、`REPLACE_WITH...` 这类占位值。
- README 面向用户介绍功能、用途、配置和部署，不包含你的私有服务器信息。

## Release 附件建议

如果要在 GitHub Release 上传压缩包：

- Windows 用户优先下载 `.zip`
- Linux/macOS/服务器用户优先下载 `.tar.gz`

两个包应来自同一个项目目录，内容保持一致。

---

<!-- project-footer:start -->
<p align="center">
  <a href="https://github.com/chixiaotao-Exm/ideal_links_Service" target="_blank" rel="noopener noreferrer">
    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="20" height="20" alt="GitHub" />
    ideal_links_Service
  </a>
</p>
<!-- project-footer:end -->
