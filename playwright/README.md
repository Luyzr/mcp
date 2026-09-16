# Playwright MCP 插件服务

目标主机：<mcp-host>。安装根目录：/mnt/mcp/playwright。

## 版本与运行方式

- 官方 npm 包 @playwright/mcp 0.0.81，精确依赖和完整性值记录在 package-lock.json。
- Chromium Headless Shell 154.0.8037.0 / revision 1244，保存在 browsers/。
- playwright-mcp.service：独立非 root 用户，启用 Chromium sandbox，<loopback-address>:<port> 内部后端。
- playwright-mcp-auth.service：<loopback-address>:<port>/mcp，Bearer 鉴权入口。
- playwright-tunnel.service：OpenAI Secure MCP Tunnel；健康检查 <loopback-address>:<port>。
- 后端及鉴权服务已启用开机自启；隧道已配置并启用开机自启，Tunnel 名称为 playwright。
- 浏览器按连接隔离，关闭浏览器后登录状态丢失；截图等结果位于 output/，自动输出上限配置为 256 MiB。
- 插件具备 33 个工具，包括导航、点击、填写、快照、截图、PDF 等。具体定义见 local-deploy/tools.json。
- 未修改 Codex 配置。两个客户端统一通过插件接入。

## 完成 OpenAI 插件接入

1. 打开 https://platform.openai.com/settings/organization/tunnels 创建 Playwright 专用隧道，关联使用插件的 ChatGPT 工作区。不要复用其他 MCP 服务正在使用的 Tunnel ID。
2. 在本地终端执行（runtime API key 隐藏输入，不要粘贴到聊天）：

```sh
ssh -t <mcp-host> python3 /mnt/mcp/playwright/local-deploy/configure-tunnel.py
```

3. 确认隧道 ready（首次连接可能需稍候）：

```sh
ssh <mcp-host> 'curl -fsS http://<loopback-address>:<port>/readyz'
```

4. 在 ChatGPT 插件页面创建开发者模式应用，名称 Playwright，Connection 选择 Tunnel，并选择新 Tunnel ID。由隧道注入本地 Bearer，无需在插件配置中复制本地凭据。
5. 在目标客户端启用插件，并测试“打开 https://example.com，读取标题并截图”。插件是否可见取决于账户、工作区关联和开发者模式权限。

官方文档：https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
上游：https://github.com/microsoft/playwright-mcp

## 运维与验证

```sh
ssh <mcp-host> 'systemctl status playwright-mcp playwright-mcp-auth playwright-tunnel --no-pager'
ssh <mcp-host> 'journalctl -u playwright-mcp -u playwright-mcp-auth -u playwright-tunnel -n 50 --no-pager'
ssh <mcp-host> 'node /mnt/mcp/playwright/local-deploy/smoke-test.mjs'
```

验证覆盖：未鉴权/错误凭据返回 401、MCP initialize、tools/list、真实 HTTPS 导航、浏览器点击、DOM 快照、截图、关闭和会话终止。结果见 local-deploy/validation.log。隧道已连接 OpenAI 控制面，启动探测及 /readyz 正常；用户界面的插件调用仍需在目标客户端验证。2026-09-15 修复鉴权代理未立即发送 SSE 响应头导致隧道探测超时的问题，并增加 2 秒内收到流式响应头的回归检查。

配置在 local-deploy/，systemd 单元同步安装至 /etc/systemd/system/。修改单元后需要复制并 systemctl daemon-reload。mcp-authorization 为 root:playwright-mcp-auth 0640；tunnel.env 创建为 root 0600；浏览器用户无法读取这些凭据。

## 重建依赖

在根目录执行 npm ci，再运行：

```sh
PLAYWRIGHT_BROWSERS_PATH=/mnt/mcp/playwright/browsers node node_modules/playwright/cli.js install --with-deps chromium --only-shell
```

升级时需同时核对 config.json 的浏览器 executablePath，并重新运行验证。
