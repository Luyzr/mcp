# MCP 服务集合

[English](README_EN.md)

本私有仓库纳管多项 MCP 服务的源码、部署模板和必要的离线文件。主机地址、监听地址、端口和凭据属于部署环境配置，不进入 Git。

## 服务

| 服务 | 版本 | 目录 |
|---|---|---|
| 小红书 | `xiaohongshu-mcp v2.5.0` | [`xiaohongshu/`](xiaohongshu/) |
| 高德地图 | `@amap-lbs/amap-gui 1.0.3` | [`gaode/`](gaode/) |
| Playwright | `@playwright/mcp 0.0.81` | [`playwright/`](playwright/) |
| Firecrawl | `firecrawl-mcp 3.24.1` | [`firecrawl/`](firecrawl/) |
| 飞猪 | `@fly-ai/flyai-cli 1.0.16` | [`flypig/`](flypig/) |

## 安全

以下内容只保留在部署主机本地：

- 主机 IP、监听地址、端口映射和网络拓扑
- `.env`、`ports.env`、`*.keys.env`、`*.service.env`、`*.tunnel.env`
- MCP Bearer 授权文件、API Key、Cookie 和登录会话
- 依赖目录、虚拟环境、构建输出、浏览器数据和运行时缓存

仓库中的部署文件是模板，地址和端口使用环境变量或占位符。部署前应在未纳管的本地配置中赋值，禁止把实际值写回源码、文档或提交历史。

## 运维

服务由 systemd 管理。通用检查命令：

```sh
ssh <mcp-host> 'systemctl --type=service --state=running --no-pager'
```

各服务的配置、验证和故障排查方法见对应目录的 README 或 `local-deploy/README.md`。

## 更新流程

1. 在部署主机验证服务改动。
2. 确认 `git status` 不包含地址、端口、凭据、Cookie、缓存或生成物。
3. 运行对应 smoke test 并检查 systemd 状态。
4. 提交到 `main` 并推送至 `origin`。
