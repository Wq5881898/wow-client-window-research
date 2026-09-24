# 附录 B：条款与历史反作弊原文知识库

更新：2026-09-23  
性质：区分现行公开合同、历史合同、判决事实和未知项；不是法律意见。

## 一、证据目录

| 材料 | 时间与来源 | 可证明内容 |
|---|---|---|
| Blizzard EULA | 页面标注 `LAST REVISED March 21, 2024`；2026-09-22 官方页抓取 | 当前归档的公开合同文字 |
| WoW UI Add-On Development Policy | Blizzard 官方论坛仍公开；正文源自 2009 | 官方页面中的 addon 政策文字 |
| Forever 公告与官方员工帖 | 2026-09-17 官方来源 | 公开 Beta 公告内容 |
| WoW Terms of Use | 2010 历史存档 | MDY 同期合同背景 |
| Blizzard EULA | 2019 历史存档 | 合同文字演变 |
| Anti-Cheating Agreement | 最后更新 2016-02-03；2019 存档 | 历史公开反作弊声明 |
| MDY | 629 F.3d 928 (9th Cir. 2010)，含 2011 修正令 | 特定事实、法域和请求权下的判例 |

完整 URL、日期、字节数、SHA-256、提取方法和限制见取证记录。`EULA_2026-09_raw.html` 和 `Blizzard_EULA_2026-09_现行版_纯文本.txt` 是损坏响应；项目保留它们用于追溯，当前可读文本是 `Blizzard_EULA_2024-03-21_抓取于2026-09-22_纯文本.txt`。

## 二、现行公开 EULA 短引文

### Bot

> "bots; i.e. any code and/or software, not expressly authorized by Blizzard, that allows the automated control of a Game, or any other feature of the Platform, e.g. the automated control of a character in a Game;"

该文字与固定目标打怪、自动移动和其他角色自动控制直接相关。接口或输入技术本身没有回答 `expressly authorized` 状态。

### Data Mining

> "Use any unauthorized process or software that intercepts, collects, reads, or 'mines' information generated or stored by the Platform; provided, however, that Blizzard may, at its sole and absolute discretion, allow the use of certain third-party user interfaces."

该文字与 addon、SavedVariables、屏显、截图和其他外部观察路径相关，但没有逐项给出本项目事实下的结论。

### Unauthorized Connections

> "Facilitate, create or maintain any unauthorized connection to the Platform ... using third-party programs or tools not expressly authorized by Blizzard."

具体连接和工具的适用情况在项目中没有个案书面答复。

### Beta 与监控

归档文本还包含 Beta eligibility/confidentiality、系统信息、通信监控、Beta 数据变化和 `Consent to Monitor` 条款。公开公告未列专项条款，客户端流程尚未检查。

## 三、公开 Add-On Policy

2009 来源的官方政策页正文包括：

- add-ons 免费分发；
- 不设付费 premium 功能或以付费换取访问；
- 代码可见；
- 游戏内不展示广告或捐赠请求；
- 遵守 WoW ToU/EULA，Blizzard 可禁用 addon 功能。

这些是页面文字。页面没有单独回答 2026 Forever、付费内容服务、外部数据路径或自动控制的具体情况。

## 四、历史 Anti-Cheating Agreement

2016 历史文本在 unauthorized third-party program 定义中提到未获明确授权的 software/code/method，包括某些 addon/mod，并列举 botting、未获允许的 UI/体验改变和信息收集。

文本描述当时工具对以下对象做 limited scans：

1. 游戏占用的 RAM；
2. 游戏进程及附加的第三方代码；
3. Windows process list；
4. Windows handles list。

该枚举是历史事实，不是 Forever 当前检测面的完整清单，也不能反向证明未列技术获准或不可检测。

## 五、历史合同与 MDY

2010 WoW Terms of Use 限制 bots、unauthorized third-party software、读取 RAM 的 data mining、客户端修改和 unauthorized connections。2019 EULA 将 data mining 表述扩展到收集、读取或挖掘 Platform 生成或存储的信息。

MDY 的第九巡回结果撤销部分地区法院结论，维持 §1201(a)(2) 责任并保留相关永久禁令。案件涉及 Glider 检测规避和商业销售。该案件可形成历史风险先验，但没有决定当前 Forever 技术实现、个案授权、处罚概率或其他法域结论。

## 六、有范围的负面检索

- 本轮审阅的 Forever 公开公告和官方员工帖中未找到专项条款链接。
- 所做精确短语检索中未找到 Blizzard 官方 `macro substitute/macro manager` 文字。

这两项只描述已审阅来源中的检索结果。

## 七、用户决定与证据状态

用户于 2026-09-22 决定自行承担个人账号技术实验的处罚风险，个人实验不等待 15C。这是用户风险选择，不是 Blizzard 授权、免责或低风险结论。

发布、分发、招募其他账号测试和商业化尚未发生；项目也没有对应的 Blizzard 书面说明或专业意见。高风险技术可以作为非操作性预研候选，尚未实施。
