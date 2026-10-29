# WoW 客户端窗口路线研究

本仓库保留父项目既有 Git 历史，当前只维护客户端窗口输入、截图、Lua 只读探针及对应 Python 驱动。

- Python：Windows 交互会话、输入和实验编排。
- Lua：游戏内只读观测与数据记录；普通插件不能因为改用 Lua 就绕过受保护动作限制。
- 纯网络独立项目：https://github.com/Wq5881898/wow-pure-network-research 。本地 `/pure-network/` 被忽略，不属于本仓库。

## 当前状态

本地 3.3.5a / Probehuman 已有分段移动、转向、反馈纠偏、逐帧及步行对照历史记录。它们不等于正式目标客户端验证，也不等于可靠的实时闭环。停止继续无边界的毫秒级输入实验；下一阶段先明确客户端自身的观测出口和完整小任务验收。

## 离线检查

```powershell
python -X utf8 scripts/client_offline_check.py
python -X utf8 scripts/probe_static_check.py
python -X utf8 scripts/probe_wotlk_static_check.py
git diff --check
```

上述命令不会运行游戏。`lab_*.py` 多数是会发送输入的实验脚本，不要作为测试批量执行；路径及交互会话须按本机核实。

## 恢复与备份

见 [发布与恢复审核](docs/客户端发布与恢复审核.md) 和 [27 项冲突清单](docs/client_restore_conflicts.json)。保留全部冲突原文件，11项格式异常未自动覆盖。JSON可解析不等于原始哈希完全验证。仓库内测试账号和游戏测试密码由用户明确授权公开，不代表其他凭据可提交。
