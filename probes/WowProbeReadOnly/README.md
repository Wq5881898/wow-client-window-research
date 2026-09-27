# WowProbeReadOnly

只读能力探针源码。本机无 WoW，**未加载、未运行**。不是 bot，默认 `DefaultState: disabled`。

## 做什么

`/wowprobe once [scene]` 对下列对象各记一条四维记录：build/限制、时间、位置、`player`/`target` 的 Unit 与 secret 谓词、Assisted Combat 四函数。另计数软目标与限制事件。

`SavedVariables: WowProbe_Report` 只写分类和可持久化的非 secret 标量。secret 值不入库。不记录角色名、GUID、服务器。

## 不做什么

不调用：选目标、攻击、施法、移动、跳跃、Interact、发聊天、改 tracking。目标必须由玩家手工选定。

## 使用

1. 把 `Interface` 改成目标 Forever build 的 interfaceVersion。
2. 拷到客户端 `Interface/AddOns/WowProbeReadOnly/`，在插件列表里手动启用。
3. 登录后 `/wowprobe once outdoor_still`，手工选目标后再 `/wowprobe once target_selected`。
4. reload 或退出后，看 WTF SavedVariables 里是否出现上一轮 `logout_seen`。内存赋值不等于文件已写盘。

`## Interface: 160001` 是占位，不是已核对的 Forever 接口号。
