# 附录 G：在线端点测量与离线契约

更新：2026-09-23  
脚本：`scripts/lat.py`、`scripts/lat2.py`、`scripts/lat3.py`、`scripts/lat4.py`  
结果：`results/lat_result.json`、`results/lat_result2.json`、`results/lat_stream.json`

`scripts/lat.py`、`lat2.py` 和 `lat3.py` 是保留具体测试端点及模型名的历史专用仪器；其中的服务商、host、模型和环境变量名称用于解释已有样本，不表示当前运行环境配置。`scripts/lat4.py` 是后续复测用的参数化仪器，只从项目外读取 `LAT_BASE_URL`、`LAT_MODEL` 和 `LAT_API_KEY`。

## 一、实际测量

网络握手覆盖 4 个公开服务域名，少量样本为：

- TCP：77.5–6382.9 ms。
- TLS 全握手：168.5–6656.4 ms。
- 一次有效 JSON 响应：25,197 ms，completion 26 tokens。
- 两次流式请求 TTFB：18,269 ms 和 20,441 ms，内容均一次到齐。
- 另一个入口约 5.8–6.0 s 后返回空 content，原因未独立确认。
- 另见两次 HTTP 429 和若干 401/403/404；失败入口没有形成有效推理样本。

这些是单机、单网络和少量请求的实际结果。项目结果不包含凭据。

## 二、由样本支持的判断

- 已取得有效响应的样本处于秒到数十秒量级。
- 在需要亚秒级或稳定及时响应的控制问题上，所测端点当前样本不满足这种时间特性。
- 延迟没有被严格分解为排队、推理、网关和网络传输。
- 样本不覆盖所有服务商、模型、地区或付费等级。
- 样本不回答数据上传的合同范围、隐私处理或动作效果。

因此，“所测端点不适合作为低延迟热循环”是有数据支持的架构判断；“所有在线 AI 都无价值”没有数据支持。异步分析是否有价值尚未测试。

## 三、合成契约

以下 schema 属于 `bot_sim.py` 的合成模型：

```json
{
  "map": "synthetic",
  "x": 41.2,
  "y": 63.7,
  "combat": true,
  "target": "synthetic-target",
  "texists": true,
  "tdist": 7.3,
  "tdir": "N",
  "hpr": 0.62,
  "potionReady": true,
  "cd": {"Chop": 0},
  "stuck": false
}
```

`x/y`、`tdist`、`tdir`、`hpr`、`potionReady`、冷却和 `stuck` 都是 modeled observations，不是 Forever 已确认字段。

当前代码实现了结构检查、动作白名单、状态版本、过期检查、请求 ID、失败记录和 relevance hash。策略通过 `Snap` 读取观测，不直接读取隐藏 `World`。这些是代码事实；检查是否完整、字段是否真机可得仍未知。

## 四、尚未验证

- 本地观察字段在目标客户端中的来源和误差。
- 在线异步分析能否带来实际收益。
- 截图或状态上传的适用范围和数据处理条件。
- 其他端点在明确用例下的延迟、质量和成本。
- 在线输出与真实输入之间的任何有效映射。
