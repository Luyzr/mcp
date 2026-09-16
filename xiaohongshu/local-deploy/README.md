# 小红书 MCP 当前部署

主机：<mcp-host>；目录：/mnt/mcp/xiaohongshu。
服务：xiaohongshu-mcp、xiaohongshu-tunnel，均已启用开机启动。
OpenAI 由本机直接连接，无 control-plane 代理或 HTTP(S)_PROXY 环境变量。
原隧道 ID：tunnel_6aa77887a03081918e94dba09dd12a49，ChatGPT App 无需重新配置。

验证：7 个程序与配置文件 SHA256 一致；Git 完整性检查通过；18 个 MCP 工具可发现；
/readyz 返回 HTTP 200 ready；momo 登录状态保持；凭据文件权限 0600。

常用命令：
```bash
systemctl status xiaohongshu-mcp xiaohongshu-tunnel
python3 /mnt/mcp/xiaohongshu/local-deploy/xhs.py status
python3 /mnt/mcp/xiaohongshu/local-deploy/xhs.py qrcode
curl --noproxy '*' http://<loopback-address>:<port>/readyz
```

旧主机 100.103.171.125 上的两个服务已停止并取消开机启动，目录暂留作回退备份。
若回退，应先停止新主机两个服务，避免同一隧道与账号同时运行。
