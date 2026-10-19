# Unreal Engine 接入

## 支持范围与准备

桥接处理已有、行结构已编译的 DataTable，内容目录中的 /Game 路径；不创建资产、不改 UStruct、不编辑蓝图节点或 DataAsset。仅在编辑器中执行 Python，不作为运行时玩法脚本。启用项目的 Python Editor Script Plugin 和 Editor Scripting Utilities 后重启。本文按 Epic 的 [编辑器 Python 入口](https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python)、[DataTableFunctionLibrary API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/DataTableFunctionLibrary?application_version=5.6) 和 [EditorAssetLibrary API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorAssetLibrary?application_version=5.6) 编写；实际引擎版本要做一次项目级回读验证。

先确认游戏真正读取的是哪个 DataTable、哪个行 ID、是否有蓝图/CDO/实例默认值覆盖，以及是否还有服务端/存档覆盖。字段映射用引擎**实际导出的名称**，不能猜显示名等于 UPROPERTY 名。bridge 对导入后的完整 JSON 做回读比较（浮点容差 1e-6）；不兼容的枚举、嵌套结构、软对象路径等会拒绝，而不是静默丢字段。

不要手改 `.uasset`。无界面桥接使用独立编辑器进程：**先保存并关闭该项目的交互编辑器**，确保源控制允许写资产；否则缓存及并发保存可能覆盖结果。若已有可靠的编辑器连接，可在该连接中执行等价操作并验证，不额外启动同项目进程。

## 双向数据链

1. 修改 UE 侧时：保存资产 -> pull 到 JSON -> plan -> 解决冲突 -> apply 到 Markdown/Excel/CSV -> push 合并后的数据 -> 回读 -> 编译/PIE。
2. 修改策划/表时：先 pull 最新 UE 状态（不动尚未保存的策划/表）-> plan 合并 -> apply -> push -> 回读 -> 编译/PIE。
3. **有尚未 push 的 JSON 改动时，不直接 pull 覆盖它。**先保留 JSON 原件，导出到单独临时路径比较；确定合并结果后再替换 view。pull 仅是导出工具，本身不执行三方合并。正常工作流每次 apply 后应立即 push 成功，避免这种悬挂状态。

```powershell
python <skill>/scripts/ue_bridge.py pull --engine <UE>/Engine/Binaries/Win64/UnrealEditor-Cmd.exe --project <project>/MyGame.uproject --bindings <project>/ue-bindings.json
python <skill>/scripts/design_sync.py plan --manifest <project>/design-sync.json
python <skill>/scripts/design_sync.py apply --manifest <project>/design-sync.json
python <skill>/scripts/ue_bridge.py push --engine <UE>/Engine/Binaries/Win64/UnrealEditor-Cmd.exe --project <project>/MyGame.uproject --bindings <project>/ue-bindings.json
```

路径含空格时按所在 shell 引用。绑定结构见 starter 的 ue-bindings.example.json。host Python 不需安装 unreal 模块；它用独立 request/token 调用内置编辑器 Python，并检查进程返回值和成功回执，避免只看退出码。pull 的全部导出成功后才写 JSON；push 中任一表失败会恢复这批磁盘资产快照。桥接不等于游戏测试。独立 bridge 进程被强制终止时，内存备份无法自动恢复；正式项目用下面的外层事务并保留资产版本管理。

## 把导入放进同步事务

推荐将 push 设为 design-sync.json 的第一条 check，后面再放项目验证命令；把对应 `.uasset` 和已存在的 `.uexp/.ubulk`（如有）列入 rollback_paths。外层 apply 才能把文本、基线、资产放进同一可恢复事务。不要将 pull 设为 check，它会反向覆盖候选数据。

```json
{
  "rollback_paths": ["Content/Data/DT_Skills.uasset"],
  "checks": [
    {
      "id": "ue-datatable-push-roundtrip",
      "argv": ["{python}", "<skill-root>/scripts/ue_bridge.py", "push", "--engine", "<engine-root>/Engine/Binaries/Win64/UnrealEditor-Cmd.exe", "--project", "MyGame.uproject", "--bindings", "ue-bindings.json"],
      "timeout": 360
    }
  ]
}
```

这是配置片段，须将 `<skill-root>` 和 `<engine-root>` 替换为实际绝对路径，不直接运行示例；这些占位符不会由脚本展开。外层 timeout 应大于 bridge 的 300 秒默认超时。检查不修改同步 JSON；校验器若改变受管记录，apply 会拒绝并回滚。导入检查只是第一层；按项目实际补相关 C++ build、蓝图 compile、Automation/PIE。没有这些检查时，最终明确游戏行为未验证。

## 规则与实现

- 新增字段：同步 schema、Excel 列、UStruct UPROPERTY、序列化/默认值、蓝图引用与数据迁移，再回读。反射结构改变按项目构建流程完整编译，不只依赖 Live Coding。
- 规则变化：用 feature 映射定位 C++ 类/函数或 Blueprint 资源/Graph/函数，改输入、条件、状态、输出和边界；不能仅在表里添加一段描述。
- Blueprint 若无编辑器/蓝图工具，报告受阻的具体图与验收步骤，不把说明写完称为实现。工具具备时按项目图编辑流程改节点、编译、保存、复验。
- 构建与测试命令从现有脚本/CI/目标设置推导，不臆造 Editor target、测试过滤器或关卡路径。运行时日志应证明正确资产/行被加载。
- 联机规则涉及权威端、复制、RPC 和客户端表现时，分别检查服务端真实值与客户端显示；不要把客户端表改动当作权威玩法已改变。
