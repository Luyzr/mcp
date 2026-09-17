# MCP 服务集合

[English](README_EN.md)

本私有仓库管理六组 MCP 服务的源码、部署配置、验证脚本和插件素材。服务运行在 Linux 服务器，由 systemd 管理，统一通过 **OpenAI Secure MCP Tunnel** 接入。Obsidian 笔记单独保存在 [obsidian_library](https://github.com/Luyzr/obsidian_library)，不与服务代码混放。

## 服务

| 服务 | 版本 | 用途 | 目录 |
| --- | --- | --- | --- |
| 小红书 | `xiaohongshu-mcp v2.5.0` | 搜索、阅读和管理小红书内容 | [xiaohongshu](xiaohongshu/) |
| 高德地图 | `@amap-lbs/amap-gui 1.0.3` | 地点搜索和路线规划 | [gaode](gaode/) |
| Playwright | `@playwright/mcp 0.0.81` | 浏览器操作与网页验证 | [playwright](playwright/) |
| Firecrawl | `firecrawl-mcp 3.24.1` | 网页搜索、抓取与内容提取 | [firecrawl](firecrawl/) |
| 飞猪 | `@fly-ai/flyai-cli 1.0.16` | 出行信息搜索 | [flypig](flypig/) |
| Obsidian | `obsidian-remote-mcp 2.1.0` | 笔记读写、搜索、链接和标签管理 | [obsidian](obsidian/) |

版本为仓库当前部署记录，不代表上游最新版本。

## 部署与访问

- 代码根目录：`/mnt/mcp`，Git 分支为 `main`。
- 每项 MCP 使用独立 systemd 服务和 tunnel；部分服务另有认证代理或 GUI 单元。
- tunnel 从服务器主动建立出站连接，MCP 后端保留本地认证；客户端无需通过 Tailscale 地址访问 MCP。
- tunnel 的 `live` / `ready` 表示隧道健康；连接器接入后仍应验证真实工具调用。
- 服务器服务清单及恢复记录：`/mnt/codex/SERVER_INVENTORY.md`。

各服务的配置与验证方法见对应目录，Obsidian 详见 [部署说明](obsidian/local-deploy/README.md)。

## Obsidian 知识库

- 源码：`/mnt/mcp/obsidian`；知识库：`/data/obsidian_library`。
- 知识库 GitHub 仓库：[Luyzr/obsidian_library](https://github.com/Luyzr/obsidian_library)，分支 `master`。
- `obsidian-mcp.service` 提供授权笔记操作；`obsidian-tunnel.service` 提供统一隧道访问。
- `obsidian-git-sync.timer` **每分钟整分触发双向同步**：提交服务器改动、拉取远端更新、合并并推送。开机自启，错过的触发会在恢复后补执行。
- 合并先在临时工作区验证。有远端更新时短暂停止 MCP 与 tunnel，结束后恢复原本运行的服务；只有本地推送时不暂停。
- 冲突保留双方提交及原始笔记，记录 `blocked`，等待人工解决；网络故障下一分钟重试。不强制推送或覆盖笔记。
- 同步遵循 `.gitignore`，范围是 GitHub 与服务器知识库。Mac/iPhone 的 Obsidian Vault 需要自行配置客户端同步。

插件名称、描述和 **256×256、低于 10 KB 的 PNG 图标**见 [branding](obsidian/local-deploy/branding/)。

## 运维

在服务器上执行：

```sh
systemctl is-active obsidian-mcp obsidian-tunnel obsidian-git-sync.timer
systemctl list-timers obsidian-git-sync.timer --no-pager
cat /var/lib/obsidian-git-sync/status.json
journalctl -u obsidian-git-sync.service --no-pager -n 30
```

同步服务是 oneshot，两次运行之间显示 `inactive` 属于正常现象；应检查 timer、最近执行结果和状态文件。`synced` 表示该轮验证时本地提交与远端一致，不保证编辑或网络故障期间实时一致。

## 凭据与版本管理

API Key、MCP Bearer 授权、SSH 私钥、Cookie、登录会话及实际凭据配置仅保留在服务器受限文件中，不进入 Git。依赖目录、虚拟环境、缓存、运行时数据及 tunnel 运行文件也不应提交。不要将敏感连接信息或凭据复制到文档、日志和插件素材。

服务代码由人工审查后提交至本仓库；每分钟自动同步只用于知识库，不自动提交本仓库的代码改动。

## 更新流程

1. 在部署服务器检查 `git status`，保留其他未提交工作。
2. 修改目标服务，执行相关测试并核对实际服务状态。
3. 涉及服务增删、部署或启动方式变化时，同步更新服务器清单。
4. 检查暂存区不含凭据、运行数据及无关改动，再提交到 `main` 并推送。
