# 确定性同步契约

清单在项目根目录；路径都相对该目录且不得越界。实现是本地开发工具，清单的 checks 是项目代码，只有在项目检查本身已获授权后执行 apply；plan/check 不运行 checks。

## 清单

实际示例见 `../assets/starter/design-sync.json`。version=1，datasets 数组；每项包含唯一 id、字符串 id_field、fields 和两个以上 views。

fields 类型：string、integer、number、boolean；可附 min/max、enum、pattern、nullable、ref（目标 dataset 的行 ID）。所有受管字段必需，不静默填默认值。null 不等于空字符串，CSV 的非字符串空格/空单元按声明处理；字符串字段不可 nullable（CSV 无法区分 null 与空字符串）。不接受 NaN/Infinity、重复 JSON key、重复行 ID、空 ID、失真整数和缺列。UE 的 FName 行名不区分大小写，接入时启用 case_insensitive_ids 并保持各侧拼写一致。

view：id、path、format；可选 columns（逻辑字段 -> 文件字段）、json_path（对象路径 key 数组）、block（Markdown 块名）、sheet/data_only_sheet（XLSX）。每个文件只绑定一个 view，避免两个 dataset 相互覆盖。单文档多系统/多表同工作簿需要另写适配器，或将系统数据拆成独立受管文件后在总策划案中引用。

Markdown 块形状：

````markdown
<!-- design-sync:skills:begin -->
```json
[{"id":"fireball","damage":100}]
```
<!-- design-sync:skills:end -->
````

只替换块内 JSON。块外文字不由脚本推断或覆盖。JSON 仅修改指定对象路径的列表，保留其他对象键；重新序列化可能改变缩进。CSV 保留原列顺序和未映射列，输出 UTF-8 BOM 便于 Excel 打开。XLSX 需安装 openpyxl，仅普通 `.xlsx` 数据页，第一行唯一字段名；拒绝公式、合并区、表对象、图表、图片、宏。其他工作表保存但复杂扩展不保证无损，需要保留原件。新增行的额外列为空；带业务必填额外列时先扩充映射。

## 合并

比较 baseline、Markdown、表、游戏 JSON 的标准化逻辑字段：

- 无变化保持原文件字节，重复 apply 不来回改格式。
- 只有一个新值：传播；多侧改成相同值：接受；不同字段变动：合并。
- 同字段出现多个新值：冲突，整次不写入。
- 单侧新增完整行：传播。相同新 ID 的各侧值不同：冲突。
- 删除且其他侧仍是基线：删除传播；删除与编辑同时发生：冲突。
- ID 改名视为删除加新增，脚本没有自动引用重命名能力。ref 校验会挡住部分悬挂引用；其他 UE/存档引用由 agent 迁移。
- 合并后再次校验全部 schema/跨 dataset 外键，任一失败整次不写入。

不使用文件修改时间，也没有 --force/自动选来源。先按已有用户意图或用户裁决显式修复冲突的源文件，再重新 plan。

## 事务与检查

`checks` 每项是 `{id, argv, timeout}`，argv 是无 shell 字符串数组，`{python}` 替换为当前解释器。项目根目录为 cwd，按顺序执行，任何超时/非零退出都失败；输出截取尾部写入报告。避免 check 生成独立后台进程；超时无法保证其子进程无副作用。

`rollback_paths` 列出检查会写入的项目文件（如 UE `.uasset`/sidecar）；与受管视图一同在写入前备份。不允许目录或项目外路径。自动恢复不覆盖应用前已有编辑。一次只允许一个同步进程，不锁住编辑器；操作期间请暂停外部保存。规划到写入前检查源字节变化，但不能消除不合作程序的并发写入。

baseline 保存逻辑记录和清单 hash。改变列名、字段类型、检查命令等清单内容会要求复核迁移；先保留旧基线、处理全部漂移，把各侧迁到一致，再 `rebaseline --accept-reviewed-migration`。禁止为了让 check 变绿跳过冲突重建基线。

## 命令/退出码

| 命令 | 行为 |
|---|---|
| init | 各侧一致才创建初次基线，不运行游戏 |
| plan | 输出变化/冲突，不写受管文件，不运行 checks |
| check | 无漂移 0；数据漂移 1；冲突 2；配置/校验错误 3 |
| apply | 无冲突才事务写入，运行 checks，回读各侧，再推进基线 |
| recover | 恢复 pending 的 apply 前快照，恢复旧基线 |
| rebaseline | 复核迁移后重新建一致基线并保留旧版本 |

plan 有正常候选变动退出 0，有冲突 2。apply 检查失败 3，恢复原文件；成功 0。没有配置游戏 checks 时报告仅数据验证，不代表游戏行为已验证。
