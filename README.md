# WoW 客户端窗口路线研究

本仓库保留父项目既有 Git 历史，当前只维护客户端窗口输入、截图、Lua 只读探针及对应 Python 驱动。

- Python：Windows 交互会话、输入和实验编排。
- Lua：游戏内只读观测与数据记录；普通插件不能因为改用 Lua 就绕过受保护动作限制。
- 纯网络独立项目：https://github.com/Wq5881898/wow-pure-network-research 。本地 `/pure-network/` 被忽略，不属于本仓库。

## 当前状态

更新：2026-11-05。当前操作入口为[客户端实验指导手册](docs/客户端实验指导手册.md)。本地 3.3.5a 已有实时像素观测、外部输入、单目标战斗、低血撤退、正常跑尸、重登复核及练级实机记录；Probehuman 已有升到4级的历史记录，实时等级、生命和位置须重新读取。

本轮审阅已确认墓地锚点、目标消失判击杀、失联异常出口和整链结果绑定存在缺口；历史 `ACCEPTED` / `RECOVERED` 标签不独立证明可靠撤离或全部任务后置条件成立。详见[综合审阅](docs/客户端路线综合审阅_2026-11-05.md)和[验证分工](docs/文档审阅验证任务分工_2026-11-05.md)。当前优先收紧判据并完成附近商人的确定交易；小地图方向与光标认名已有样本，自主找到商人、卖灰装和修理仍待验证。停止无边界的毫秒级输入实验。

3.3.5a 是本地基线；现代 Forever 的 Secret Values、Assisted Combat 等能力仍没有目标客户端运行时证明。最终目标是否调整尚待明确。

## 问题知识库

测试排障先查[客户端自动化问题知识库](docs/client-kb/README.md)：按现象检索16个问题编号，包含排查顺序、最小验证、成熟源码参照、版本限制和验证账本。新结果按[验证记录模板](docs/client-kb/07_验证记录与维护.md)回填，避免重复实验或把作者声明当成本机通过。

## 离线检查

```powershell
python -X utf8 scripts/client_offline_check.py
python -X utf8 scripts/probe_static_check.py
python -X utf8 scripts/probe_wotlk_static_check.py
python -B -X utf8 -m unittest discover -s scripts -p "test_client*.py"
git diff --check
```

上述命令不会运行游戏。`lab_*.py` 多数是会发送输入的实验脚本，不要作为测试批量执行；路径及交互会话须按本机核实。

[观测任务说明](docs/客户端下一阶段_观测任务与历史缺口.md)保留2026-10-29低频任务与历史缺口说明。`client_snapshot_task.py` 是该场景的离线验收器；当前实时观测由 `WowProbeLive.lua` 和 `client_live_state.py` 提供，两者用途不同。

## 恢复与备份

见 [发布与恢复审核](docs/客户端发布与恢复审核.md) 和 [27 项冲突清单](docs/client_restore_conflicts.json)。保留全部冲突原文件，11项格式异常未自动覆盖。JSON可解析不等于原始哈希完全验证。仓库内测试账号和游戏测试密码由用户明确授权公开，不代表其他凭据可提交。
