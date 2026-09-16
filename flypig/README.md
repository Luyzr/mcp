# Flypig MCP

这是一个对官方 FlyAI CLI 的轻量 MCP 封装。它让 ChatGPT、Codex 或其他 MCP 客户端通过结构化工具查询飞猪旅行数据，同时继续使用现有的 Playwright MCP 做页面核价、Firecrawl MCP 抓取政策与规则。

```text
ChatGPT / Codex
├── Flypig MCP → FlyAI CLI → 飞猪搜索数据
├── Playwright MCP → 预订页二次核价、同价库存、行李和退改核验
└── Firecrawl MCP → 航司及平台政策抓取
```

## 当前实现

- 官方 CLI 固定为 `@fly-ai/flyai-cli@1.0.16`，Node.js 依赖写入 lockfile。
- MCP 使用 Streamable HTTP：`http://<loopback-address>:<port>/mcp`。
- 仅监听回环地址；除 `/healthz` 外都要求本地 Bearer token。
- 所有查询都通过参数数组启动 CLI，不执行 shell，也不开放任意命令入口。
- 限制并发数、运行时长、输入长度和输出大小；错误中会脱敏 `FLYAI_API_KEY`。
- 所有业务工具都标记为只读，并明确提示对库存、价格、行李和退改做预订页复核。

## MCP 工具

| 工具 | 用途 |
|---|---|
| `flypig_status` | 检查适配器、CLI 版本和个人 API Key 是否已配置 |
| `flypig_help` | 查看已安装 CLI 的当前帮助 |
| `flypig_keyword_search` | 跨品类关键词搜索；对应 CLI `keyword-search`，兼容别名 `fliggy-fast-search` |
| `flypig_ai_search` | 复杂自然语言旅行需求搜索 |
| `flypig_search_flight` | 结构化机票搜索 |
| `flypig_search_train` | 结构化火车票搜索 |
| `flypig_search_hotel` | 酒店搜索 |
| `flypig_search_poi` | 景点与活动搜索 |
| `flypig_search_marriott_hotel` | 万豪酒店搜索 |
| `flypig_search_marriott_package` | 万豪套餐搜索 |

## 安装和启动

```bash
sudo /mnt/mcp/flypig/local-deploy/install.sh
curl http://<loopback-address>:<port>/healthz
systemctl status flypig-mcp.service
```

安装脚本会把锁定的 Python 依赖装入项目内隔离目录 `.python`、生成本地 MCP Bearer token、安装 systemd unit，并完成 MCP 初始化和工具发现测试。

## 配置 FlyAI API Key（可选但建议）

官方 CLI 1.0.16 在没有个人 Key 时也能使用内置默认访问。个人 Key 可用于增强结果或额度。不要把 Key 写进命令历史；使用隐藏输入脚本：

```bash
ssh -t <mcp-host> python3 /mnt/mcp/flypig/local-deploy/configure-api-key.py
```

密钥只保存在 `local-deploy/keys.env`，权限为 `0600`，由 systemd 注入 `FLYAI_API_KEY`。

## 接入 ChatGPT / Codex

要从 OpenAI 产品调用这台机器上的私有服务，为 Flypig 新建一个独立 Secure MCP Tunnel，不要复用 Playwright 或 Firecrawl 的 tunnel ID：

```bash
ssh -t <mcp-host> python3 /mnt/mcp/flypig/local-deploy/configure-tunnel.py
curl http://<loopback-address>:<port>/readyz
```

然后在 ChatGPT Plugins 中新建 developer-mode app，连接方式选择 **Tunnel**，并选择该 Flypig tunnel。需要提前把 tunnel 关联到目标 ChatGPT workspace 和 Codex 使用的 Platform organization。

本机 MCP 客户端也可以直接连接 `http://<loopback-address>:<port>/mcp`，并把 `local-deploy/mcp-authorization` 的整行内容作为 `Authorization` 请求头。

官方说明：<https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>

FlyAI 官方项目与 API Key 入口：<https://github.com/alibaba-flyai/flyai-skill>、<https://open.fly.ai>

## 推荐调用流程

用户请求：

> 查 2026-09-25 上海到丽江，2 个成人，13:00 前落地，必须每人 20kg 行李。

建议编排：

1. 调 `flypig_ai_search`，把日期、人数、到达时间和行李要求完整放进 `query`。
2. 调 `flypig_search_flight(origin="上海", destination="丽江", dep_date="2026-09-25", arr_hour_end=13)` 得到结构化候选。
3. 对候选预订链接调用 Playwright，核实两张同价库存、每位 20kg 行李、含税总价与退改规则。
4. 如需航司或平台政策原文，再调用 Firecrawl 抓取并引用。

FlyAI 的结构化机票命令没有“成人数量”和“行李额”参数，因此这两项不能只凭搜索结果判定，必须在后续预订页中确认。

## 运维

```bash
PYTHONPATH=/mnt/mcp/flypig/.python /mnt/mcp/flypig/local-deploy/smoke-test.py
journalctl -u flypig-mcp.service -n 100 --no-pager
systemctl restart flypig-mcp.service
```

Tunnel 配置完成后还可以查看：

```bash
systemctl status flypig-tunnel.service
curl http://<loopback-address>:<port>/healthz
curl http://<loopback-address>:<port>/readyz
```
