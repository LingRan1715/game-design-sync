# 技能系统（合成示例）

这是同步演示，不代表已存在的游戏实现。单位：damage 为生命值，cooldown 为秒。

## skill.fireball

玩家按下施放键时，如果技能启用且未处于冷却，就发射一枚火球；命中目标后造成表中 damage 数值的伤害，并按 cooldown 进入冷却。具体输入绑定、命中方式、冷却开始时点及多人权威规则，接入真实项目时由现有实现和用户意图确定。

数值以受管块为准，正文不重复写死。稳定 ID 不作为显示名称使用。没有目标、重复输入、技能禁用、冷却尚未结束等情况须在真实项目补充验收。

<!-- design-sync:skills:begin -->
```json
[
  {"id": "fireball", "damage": 100, "cooldown": 2.0, "enabled": true}
]
```
<!-- design-sync:skills:end -->

实现锚点：示例为 GameData/skills.json 和 Tests/check_runtime_data.py；真实项目请填写行结构、DataTable 路径、数据读取组件或蓝图函数。

验收：双向数值传播后所有视图的同一行字段一致。UE 接入后另验实际施放、命中、冷却及禁用场景。
