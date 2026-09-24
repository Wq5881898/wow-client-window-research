# 附录 F：Aura、Cooldown 与 Combat Log 静态审计

版本：2026-09-22 校准版  
数据源：项目归档的 `UnitAuraDocumentation.lua`、`SpellDocumentation.lua`、`FrameAPICooldownDocumentation.lua`、`CombatLogDocumentation.lua`、`CombatLogSecureDocumentation.lua`、`SpellBookDocumentation.lua`，以及 Warcraft Wiki Secret Values 语义说明。

> 本附录只记录静态 marker 和仪器设计约束。第三方镜像文档不是目标客户端的运行时结果；“未标 guard”不等于开放世界可用、payload 可读或用途获准。

## 一、术语

| 术语 | 含义 |
|---|---|
| Aura | 单位上的持续效果，包括 buff、debuff、DoT 或控制效果 |
| Cooldown/CD | 技能使用后的等待期；charges 是独立的层数/回充机制 |
| GCD | 多个技能共享的公共冷却；具体值和事件时序需要目标客户端测量 |
| Nameplate | 世界对象上方的名字/状态界面；可能提供视觉候选，不保证始终可见或准确 |
| Cast bar | 施法进度界面；可作为候选观测，是否需要 OCR/模板未定 |
| ADD | 战斗中出现额外敌人；当前未找到完整敌人集合 API，视觉也尚未验证 |

## 二、关键 marker

| marker | 静态含义 | 记录要求 |
|---|---|---|
| `SecretReturns` | 文档声明返回 secret | 不做普通值运算；记录 SECRET |
| `SecretContents` / `SecretAura` | 容器内容或 aura 结构可能为 secret | 不能因外层 table 存在就判可用 |
| `SecretPayloads` | 事件 payload 可能包含 secret | 事件到达与 payload 可读分开 |
| `SecretWhen*` | 条件 predicate | 记录场景与 predicate 对照，不预推结果 |
| `Requires*` | 访问前置条件 | NIL 与 ERROR/SECRET 分开 |
| `MayReturnNothing` | 允许无返回 | NIL 不是成功，也不自动等于 false |
| `SecretArguments` | 参数接受规则 | 不用于推断返回值 |

Secret 值作为 SavedVariables table key 会涉及受限操作；项目尚未运行持久化实验，也没有具体出口范围的运行时记录。

## 三、Aura 候选

转储显示部分 aura 函数带 `SecretWhenUnitAuraRestricted`、`SecretAura` 或 `SecretContents`，另有一些函数未声明相同 guard。

当前只能提出问题：

- 指定 token 的 aura 查询是否调用成功；
- 外层 table、每个元素和字段分别是否可访问；
- combat/地图/PvP 状态变化时结果如何变化；
- `C_Secrets` predicate 与实际值状态是否一致。

不能从静态分组推出“开放世界 DoT/CC 可读”或用 aura 直接构造循环。

## 四、Cooldown 与 spell 候选

静态样本：

| API | 标记摘要 | 边界 |
|---|---|---|
| `C_Spell.GetSpellCooldown` | Cooldown 条件 predicate；可能找不到 spell | 待 G4/后续范围验证 |
| `C_Spell.GetSpellCooldownDuration` | `MayReturnNothing`、参数标记 | 未见同一返回 guard 不等于值可用 |
| `C_Spell.GetSpellCharges` | Cooldown 条件 predicate | charge 数量单独验证 |
| `IsSpellKnown` 等 | 未见相同 secret 返回标记 | 只说明静态表面 |
| `Cooldown:*` frame API | UI 控件接口 | 不能当作游戏内部技能冷却数据源 |

“一律使用某两个 API 就能防止进本失效”的实现结论没有静态依据。Cooldown 若进入运行时研究，需要分别记录 API、场景和值状态；项目目前没有对应样本或门槛。

## 五、Combat Log 候选

`CombatLogDocumentation.lua` 与 `CombatLogSecureDocumentation.lua` 列出事件、过滤、条目访问和 `IsCombatLogRestricted` 等表面。

静态未见某类 guard 不能证明整个日志族或所有 payload 可读。命中、伤害、死亡和施法结果的事件到达、字段可访问性和真实世界一致性仍是不同的运行时未知项。`IsCombatLogRestricted=false` 也不描述 payload 本身或授权。

## 六、仪器规则

这些属性用于减少测量代码误报，不构成产品运行时设计：

1. 对每个 API 单独记录 OK、NIL、SECRET、ERROR、FORBIDDEN。
2. predicate、自查返回、事件和实际值分列保存。
3. 对 table 外层与字段分别做可访问性检查，不迭代不可访问对象。
4. 只用仪器生成的常量/序号作为 table key；secret 值不持久化。
5. NIL 进入 `UNKNOWN` 记录，不自动转换为“没有 aura”“技能就绪”或“目标死亡”。
6. 仪器错误、持续输出、身份信息或客户端异常会污染该次采集。

## 七、当前未知项

Aura、Cooldown、Combat Log、外部输入、施法、打断、攻击和移动都没有目标客户端样本。现有静态材料没有规定这些主题的固定执行顺序、样本量或停止条件。
