# Forever 能力探针设计记录

更新：2026-09-23  
性质：一次性测量仪器的数据模型和候选组，不是产品代码、固定阶段或验收 gate。

## 一、目的

探针用于把静态 API 候选转为按 build、场景和失败类型可复查的运行时观察。项目尚未在 WoW 客户端加载或执行这些探针。

## 二、四维结果模型

```text
call_status  = RETURNED | ERROR
value_status = OK | NIL | SECRET | NOT_APPLICABLE
event_status = NONE | BLOCKED | FORBIDDEN | RESTRICTION_CHANGED
effect       = OBSERVED | NOT_OBSERVED | NOT_APPLICABLE
```

采用四列的原因是：调用返回、值可访问、限制事件和真实世界效果并非同一事实。NIL 不等于 false；无事件不等于动作成功；返回非空也不等于实际效果或授权。

## 三、候选探针组

| 组 | 内容 | 当前依据 |
|---|---|---|
| G1 | build、addon security、Beta/限制状态和事件 | 静态 API/事件表面存在 |
| G2 | `C_SystemTime`、OnUpdate 和时间对表 | 静态候选，未运行 |
| G3 | 玩家地图 ID 与地图坐标 | `C_Map` 文档候选，未运行 |
| G4 | Unit API 与 secret predicates | 多类 marker，未运行 |
| G5 | 目标动作与外部输入 | 动作表面和独立单键仪器 |
| G6 | 采集/拾取 | 旧四 enum 成员假设已失败；仍有其他接口表面 |
| G7 | Assisted Combat 返回 | 三个读取候选和事件表面 |
| G8 | SavedVariables、聊天、屏显等数据路径 | 候选机制，未运行 |
| G9 | minimap 半径、tracking 和事件 | 静态候选 |
| G10 | addon profiler 指标 | 静态候选 |

组号只用于引用，不规定执行顺序。

## 四、记录契约

```text
probe_id, sequence, build, scene, monotonic_time,
api, args_shape, call_status, value_status, value_type,
event_status, effect, error_text, note
```

`args_shape` 用于记录参数类型和非敏感常量。原始记录可以追加保存，再由程序生成汇总。外层 table 和内部字段需要分别记录可访问性，以避免把“对象存在”误记为“内容可读”。

示例：

```lua
WoWProbe_Report = {
  meta = { build = "...", startedAt = "...", mapID = "..." },
  records = {
    {
      probe_id = "G3.position.outdoor",
      sequence = 1,
      scene = "outdoor_still",
      api = "C_Map.GetPlayerMapPosition",
      args_shape = { "number", "player" },
      call_status = "RETURNED",
      value_status = "NIL",
      event_status = "NONE",
      effect = "NOT_APPLICABLE",
    },
  },
}
```

示例值不是预期结果。

## 五、仪器完整性属性

现有设计包含以下防误报属性：

- 每个 API 调用隔离记录。
- secret 值不进入普通算术、比较、索引或持久化路径。
- SavedVariables 内存赋值与 reload/logout 后文件持久化分开记录。
- 屏显、聊天和 SavedVariables 分开记录。
- 采样频率从时间戳计算。
- 新 run ID 不覆盖历史失败记录。
- 仪器错误、持续输出和身份信息属于记录污染，发生时结束该次采集。

这些是测量实现属性，不是研究路线规则。

## 六、静态对账

```powershell
python scripts/api_lint.py
```

当前结果：API `47/47`、事件 `8/8`、enum 假设 `2/3`。G6 的四个预期 `Enum.PlayerInteractionType` 成员不存在，因此当前退出码为 1。

lint 检查归档生成文档中的名称、参数数和 enum 假设，不检查 Lua 语法、客户端加载、运行时值、动作效果或授权。目标 build 与当前镜像是否一致尚未确认。

## 七、样本与指标

旧设计曾规定 10 分钟、30 个样本、100 条出口记录、99% 和 500 ms 等门槛。这些数值没有经验基线，已撤销为项目规则。

位置可以记录有效值比例、NIL/SECRET/ERROR、间隔、最长缺口和静止抖动；数据路径可以记录发送/到达序号、丢失、重复、乱序和延迟分布；状态 API 可以记录场景一致性。实际样本数和时长属于每次实验的参数和结果。
