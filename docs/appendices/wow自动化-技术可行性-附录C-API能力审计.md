# 附录 C：Forever 插件 API 静态能力审计

版本：2026-09-22 校准版

**数据源**：`github.com/Ketho/wow-ui-source-forever` 的 `forever` 分支镜像，以及项目归档的 `sources/forever_dumps/`。  
**工具**：`scripts/api_lint.py`。  
**结果**：`results/api_lint.json`、`results/api_lint_report.md`。

> 这些文件看起来是客户端生成的 API 文档在第三方 GitHub 镜像中的副本，适合做名称、参数和静态标记审计；它们不是本项目直接从已安装 Forever 客户端提取的运行时证据。镜像存在、API 被列出或未标某个 guard，都不证明第三方 addon 真机可调用、值可读、动作发生或用途获准。

## 一、审计结果

当前 manifest 检查结果：

| 类别 | 结果 | 解释 |
|---|---:|---|
| API | 47/47 OK | 预期名称和静态签名在归档转储中匹配 |
| 事件 | 8/8 OK | 预期事件名存在 |
| 枚举假设 | 2/3 OK | G6 预期的四个采集交互成员不存在 |

lint 故意以退出码 1 报告 G6 的失败假设，避免被绿色总数掩盖。

## 二、Secret Values 静态表面

归档中存在 Secret Aspect、Secret Predicate、Secret Wrapper 和相关 API 文档。predicate 名称覆盖受限地图、PvP、战斗、生命/能量、光环、冷却、施法、身份、威胁和其他状态。

这只能确认 Forever 文档面包含 Secret Values 机制。不能仅按 predicate 名称推断：

- 普通开放世界一定不启用限制；
- 某个未列出的函数返回一定可读；
- `Should*BeSecret=false` 等于调用成功或用途获准；
- Secret Values 是唯一限制机制。

运行时记录模型将调用状态、值状态、限制事件和实际世界状态分列保存。

## 三、位置 API 候选

`MapDocumentation.lua` 中列出 `C_Map.GetPlayerMapPosition`，其静态定义包括：

```lua
{
  Name = "GetPlayerMapPosition",
  Type = "Function",
  SecretArguments = "AllowedWhenUntainted",
  Documentation = { "Only works for the player and party members." },
  Arguments = {
    { Name = "uiMapID", Type = "number", Nilable = false },
    { Name = "unitToken", Type = "UnitToken", Nilable = false }
  },
  Returns = {
    { Name = "position", Type = "vector2", Mixin = "Vector2DMixin", Nilable = true }
  }
}
```

静态观察：

- 返回值本身是 `Nilable=true`。
- 文档只承诺 player 和 party members，不提供敌人集合或敌人位置。
- 归档的 Map 文档没有给该函数标 `SecretReturns`，predicate 转储也未直接点名它。
- `SecretArguments` 描述参数接受条件，不能反向证明返回值可读。

因此唯一当前结论是“存在值得测的坐标候选”。G3 要测非空率、SECRET/NIL/ERROR/FORBIDDEN、采样缺口和静止抖动；未真机前不称为位置来源。

## 四、运行时自查候选

`SecretPredicateAPIDocumentation.lua` 列出 `C_Secrets` 相关函数，例如：

- `HasSecretRestrictions`
- `ShouldUnitHealthMaxBeSecret`
- `ShouldUnitPowerBeSecret` / `ShouldUnitPowerMaxBeSecret`
- `ShouldAurasBeSecret` / `ShouldUnitAuraIndexBeSecret`
- `ShouldUnitSpellCastBeSecret`
- `ShouldUnitThreatStateBeSecret` / `ShouldUnitThreatValuesBeSecret`

这些函数可作为运行时对照信号，但 `false` 本身不表示可以自动执行或导出。自查返回、实际值、受限事件和场景标签是不同观察。

## 五、其他静态候选

- `C_AssistedCombat`：只证明接口表面存在，第三方返回和语义归 G7。
- `C_RestrictedActions` 与 Addon/Macro Blocked/Forbidden 事件：用于记录限制状态；没有事件不证明成功。
- Unit、冷却、光环、战斗日志、容器、拾取和 NPC 交互接口：各自具有不同参数、secret 标记和场景边界，不能合并成“闭环已具备”。
- `TargetNearestEnemy` / `AttackTarget`：动作名称存在不等于敌人集合感知，也不等于实际动作可以由拟议通道触发。

## 六、被否定的 G6 假设

`Enum.PlayerInteractionType` 的 81 个归档成员中没有：

- `Herbalism`
- `Mining`
- `Skinning`
- `GameObjectLoot`

因此旧方案不能用这四个成员识别采集状态。项目尚未找到有可追溯依据的替代枚举；“成员不存在”也不等于“采集绝对不可观察”。

## 七、运行时未知项

静态候选可按以下主题形成独立观察：

- build、addon 安全与限制状态；
- 玩家位置；
- 玩家手工选择目标后的 Unit 状态；
- Assisted Combat 返回；
- 候选数据路径；
- 外部输入、限制事件和动作效果。

主题列表不规定执行顺序，也不把读取实验和动作实验合并为同一个结论。

## 八、证据限制

- GitHub 镜像可能与具体安装 build 不一致；目标 build 和对应文档尚未取得。
- 文档未标 guard 不是运行时许可证明。
- API corpus 不能描述所有 taint、combat lockdown、restricted map、Beta 开关或服务端策略。
- 本附录不判断法律合规、检测概率、产品价值或商业可行性。
