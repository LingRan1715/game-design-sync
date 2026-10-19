# Game Design Sync · 游戏策划与实现联动

[![Tests](https://github.com/LingRan1715/game-design-sync/actions/workflows/tests.yml/badge.svg)](https://github.com/LingRan1715/game-design-sync/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Codex skill and Python tools for keeping Unreal Engine design documents, balance tables, and implementation in sync.

把 **Markdown 策划案 ↔ Excel/CSV 配表 ↔ UE DataTable / C++ / 蓝图** 接入同一个持续开发流程。从任意一侧发起更改，定位相关规则、数据、实现与验收场景，再完成同步和验证。

## 能做什么

| 工作 | 处理方式 |
|---|---|
| 改数值或内容记录 | 比较上次一致基线，双向同步 Markdown 受管 JSON 块、CSV、普通 XLSX 数据页和 JSON |
| 多侧同时编辑 | 合并不同字段；同字段分歧、删除与修改并存时报告冲突，不覆盖源文件 |
| 修改玩法规则 | Agent 沿 feature ID 与文件映射联动修改规则、代码/蓝图和验收场景 |
| UE 表内调参 | 编辑器导出已有 DataTable，与策划/表合并后导入并回读比对 |
| 检查漂移 | 数据 check + 关联文件 hash 扫描；类型、范围、枚举、唯一性和跨表引用校验 |
| 同步失败 | 恢复 apply 前文件和基线；中断事务可按日志恢复 |

文件同步、UE 资产回读、游戏行为验证分别报告。当前测试包含合成样本和模拟 UE 接口，**尚未完成真实 UE 项目的编译或 PIE 验证**。蓝图节点需要编辑器工具；本工具不直接修改资产二进制。Skill 被调用时工作，不包含常驻文件监听服务。

## 安装与调用

需要 Python 3.10+。核心 CSV/JSON/Markdown 工具仅使用标准库；原生 XLSX 支持额外安装 `openpyxl`。

Windows PowerShell 安装示例（默认技能目录；自定义 CODEX_HOME 时请调整目标路径）：

```powershell
git clone https://github.com/LingRan1715/game-design-sync.git "$env:USERPROFILE/.codex/skills/game-design-sync"
```

目标目录已存在时请复用现有副本，不覆盖项目文件。在项目聊天中调用：

> 使用 $game-design-sync，接入当前 UE 项目的 Markdown 策划案、Excel/CSV 和实际 DataTable，建立到 C++/蓝图及验收场景的映射，先检查漂移再完成联动。

接入后：

> 使用 $game-design-sync，把火球伤害改为 120，同步策划、配表和 UE，并验证实际效果。

> 使用 $game-design-sync，我在 UE 表里调整了冷却，把策划和配表同步回来。

## 试用与项目接入

- [五分钟双向同步演示](assets/starter/接入说明.md)：复制合成技能表，演示伤害 100 → 120，以及冷却 2 → 3 秒的反向传播。
- [技能入口](SKILL.md)：触发范围、两类同步和完成标准。
- [项目工作流](references/workflow.md)：feature 映射、AGENTS.md 接入片段、保存事件/CI、恢复边界。
- [数据契约](references/data-contract.md)：清单、格式支持、三方合并、事务、迁移与退出码。
- [Unreal 接入](references/unreal.md)：编辑器插件、DataTable 双向桥接和实际项目验证。

最小命令（将路径替换为当前项目路径）：

```powershell
python scripts/design_sync.py init --manifest <project>/design-sync.json
python scripts/design_sync.py plan --manifest <project>/design-sync.json
python scripts/design_sync.py apply --manifest <project>/design-sync.json
python scripts/design_sync.py check --manifest <project>/design-sync.json
python scripts/impact_scan.py check --manifest <project>/design-links.json
```

`init` 只在首次各侧一致时建立基线。语义修改经 agent 复核、实现验证后才运行 `impact_scan.py acknowledge`；该命令不会验证玩法。实际 UE 项目需配置引擎路径、表资产、结构与编译/行为检查。复杂 Excel 公式页、宏、DataAsset、CurveTable 等需要项目适配器。

## 开发与测试

```powershell
python -m pip install -r requirements-dev.txt
python scripts/test_design_sync.py
```

回归测试全部使用隔离临时目录，不启动真实 Unreal Editor，覆盖双向传播、冲突、XLSX、字段/引用校验、迁移、回滚、中断恢复和模拟桥接。CI 在 Windows/Linux 与 Python 3.10/3.14 上运行同一测试集。

项目内的数据同步 `check` 仅检查文件漂移，不执行任意项目命令；实际编译和行为验收需独立配置。

## 开源

采用 [MIT License](LICENSE)。欢迎通过 Issue 或 Pull Request 提交修复和适配；贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。所有附带游戏数据均为合成示例，不包含 Unreal Engine 源码或商业游戏资产。
