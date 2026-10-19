---
name: game-design-sync
description: "整合 Unreal Engine 项目的 Markdown 策划案、Excel/CSV 配表、DataTable 与 C++/蓝图实现；当用户改策划、改数值、改玩法或检查文档与游戏是否一致时，执行双向影响分析、数据同步、实现修改和验证。适用于持续开发联动，不替代单纯写文案或游戏体验评测。"
license: MIT
---

# 游戏策划与实现联动

让同一项玩法在策划案、配表和 UE 实现里保持一致。用户从任意一侧发起更改，沿映射找到其余受影响产物，完成更改与验证后再关闭任务。

## 先识别项目和改动

- 读项目 AGENTS.md、`.uproject`、现有策划目录、表结构、数据加载链路和版本管理状态。保留现有路径、格式及用户未提交的工作，不先造另一套策划体系。
- 找 `design-sync.json` 和 `design-links.json`；没有时按 [接入与工作流](references/workflow.md) 建立最小映射，先接一个真实系统。工作区没有项目时只提供模板/示例，不声称已接入 UE。
- 确定改动是数值/内容记录、玩法逻辑、结构迁移，还是仅格式/表述；评估对应的文档、表、资源、代码、测试及兼容性影响。
- 新功能按“需求与玩家行为 -> 系统规则 -> 字段/表结构 -> 配表 -> UE 实现 -> 行为验收”推进；每步复用同一 feature ID。用户需要完整概念或正式立项案且相关技能可用时，可借助 game-concept-architect / game-design-proposal-writer，局部改动不强制重写整案。
- 用户已明确的更改直接执行。只有互斥设计决定、无法判断意图的冲突、或超出原任务的不可逆行为才需要用户决策；先把可独立完成的部分做好。

## 两条同步路径

**结构化数据**：读 [数据同步契约](references/data-contract.md)，用 `scripts/design_sync.py` 比较基线、各视图和候选结果。支持标记 JSON 块的 Markdown、CSV、普通 XLSX 数据页和 JSON；列别名把策划命名与 UE 导出字段连接起来。任何一侧的有效字段变化均可传播，互不冲突的不同字段可合并。

**规则与实现**：读 `design-links.json` 的 feature ID、规则锚点、代码/蓝图/资源位置与验收场景，结合实际 diff 做语义修改。脚本不会把自然语言自动编译成玩法，也不会编辑 `.uasset` 二进制。没有编辑器工具时完成文本和代码部分，明确留下实际资源修改/验证项；不能把操作说明冒充修改结果。

遇到 UE 资源读写，读 [UE 接入](references/unreal.md)。可用 `scripts/ue_bridge.py` 调用编辑器导出或回填**已有 DataTable**，再做回读比对。DataAsset、CurveTable、GameplayEffect、蓝图节点需要对应的项目适配，不能当成 DataTable 覆盖。

## 每次更改的闭环

1. 读取当前 diff 和同步报告，记录起点、稳定 ID、预期玩家行为与验收场景。先保存用户已有修改的原样快照；不要用 `git reset/checkout` 清理。
2. 对 UE 数据先保存编辑器中的修改，再导出与 `design_sync.py plan`。已接入且 JSON 无本地未同步修改时可直接 `ue_bridge.py pull`；JSON 有待 push 修改时导出到临时位置比较，不覆盖它。没有最新导出，不把旧 JSON 当成游戏当前状态。
3. 冲突按字段解决：展示基线、各侧值和设计影响；不可按修改时间、文件优先级或“文档永远正确”覆盖。删除与修改、ID 改名、结构迁移也需要明确处理。
4. 按用户意图同时改策划规则、配表、UE 实现、引用和验收场景。ID 改名要迁移引用/存档；改变行结构要先编译 UStruct，不能仅加表列。
5. 数据部分 `apply`：先校验类型、范围、枚举、外键和唯一性，再写文件，运行项目已配置的检查。失败还原这次同步前的文件，保留原始编辑；同步基线只在成功后推进。
6. 检查 UE DataTable 回读、真实加载位置、相关 C++/蓝图编译，以及最小 PIE/Automation 行为测试。数值变化至少确认运行时使用的新值，不能只比较文件。无引擎时只报告“文件同步通过，UE 未验证”。
7. 更新规则锚点、实现映射和项目变更记录。`impact_scan.py check` 无未处理语义变动、`design_sync.py check` 无数据漂移且验收已完成后，才确认一致。

## 策划和配表产物

- 系统策划至少写：目标体验、玩家操作、规则/公式、输入输出、状态与边界、配置字段和单位、实现锚点、验收示例。只写本次系统所需内容，不把局部改动扩成完整立项案。
- 每条重要规则有稳定 `feature_id`，每条配置有稳定行 ID。区分设计目标、已实现行为和待验证假设；从代码反推意图时标注推断，不能把偶发 bug 写成设计目标。
- 表字段声明类型、单位、默认/空值语义、范围、引用和 UE 属性名。秒/毫秒、百分比/倍率、行名/显示名转换只能按显式规则处理。
- 表中的公式、策划说明区和运行时数据各自保留职责；普通 XLSX 数据页可直接同步，含公式/宏/图表的工作簿走项目适配或已有表格技能。不能为了同步把公式覆盖成常数。
- 同一条规则的数值在 Markdown 的受管块中引用。块外散文出现重复数值时，AI 也要更新或改成引用；文件脚本不会自动理解散文。

## 运行入口

所有脚本路径相对于本 skill；`--manifest` 指向项目根目录中的清单。Python 3.10+；CSV/JSON/Markdown 与检查器仅用标准库，XLSX 额外需要 `openpyxl`。

```powershell
python <skill>/scripts/design_sync.py init --manifest <project>/design-sync.json
python <skill>/scripts/design_sync.py plan --manifest <project>/design-sync.json
python <skill>/scripts/design_sync.py apply --manifest <project>/design-sync.json
python <skill>/scripts/design_sync.py check --manifest <project>/design-sync.json
python <skill>/scripts/impact_scan.py check --manifest <project>/design-links.json
```

`init` 仅在初次各侧数据一致时建基线，不会选择哪一侧获胜。语义更改完成并验证后才用 `impact_scan.py acknowledge` 确认已复核的内容。命令参数、冲突、恢复及退出码见 [数据同步契约](references/data-contract.md)。

新项目可复制 `assets/starter/`；保留该项目自己的基线，不复制别的项目的 `.design-sync/`。`assets/starter/接入说明.md` 提供中文使用示例和最短演示。

## 触发与完成标准

Skill 在 agent 被调用时工作，不会自行成为常驻文件监听器。用户要求持续联动时，把 [工作流](references/workflow.md) 中的联动规则合入实际项目的 AGENTS.md（保留已有内容），让后续实现任务执行闭环。用户手工或外部工具编辑后，下次调用/CI 先跑两个 `check`。若需要无人值守、保存即同步，先在实际项目中配置保存事件或 CI；只让确定性的字段映射自动写入，语义变动和冲突交给 agent，不假称已安装后台服务。

交付时用简短中文说明：改了哪些规则与文件、传播方向、冲突处置、实际验证结果、UE 未完成项（如有）、如何恢复。文件一致、UE 资源一致和游戏行为通过是三个不同证据，分别报告。
