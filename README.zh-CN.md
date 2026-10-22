[English](README.md) | **简体中文**

# Relay Baton 接力棒

**把没做完的编程工作，从一个 AI 代理、一个会话或一个人，交到下一个手里，不丢线索。**

长任务总会跨越好几个会话。上下文会满，额度会用完，终端会被关掉，明天的工作可能换了一个工具接着做：今天 Claude Code，今晚 Codex，周一 Cursor，之后再交给同事。每次换手都是事情悄悄出错的地方：下一个代理相信了一句从没跑过的"测试都过了"，重试一条早已失败的路，改了被叮嘱不要碰的文件，或者照着一份早已和代码对不上的笔记继续干。

Relay Baton 是一个代理技能，把交接变成一个简短、可检查的仪式：

- **交棒**：要停下的代理写一张一屏能看完的*接力卡*：写成检查的目标、带证据标签的事实、唯一的下一步、可能的意外、禁区、死路和待解问题，并盖上仓库当前状态的邮戳。
- **接棒**：要开始的代理先把卡片和仓库对照（新鲜、漂移、陈旧还是失配），用五句话复述，重跑最关键的那条事实，然后才动手。之后卡片作废，没人能从它恢复第二次。
- **归档**：超出这次交接、值得记住的东西，进入一本小*账本*：决定、坑、事实，每条带证据，只取代不删除。

一切都是仓库里的纯 Markdown。不需要服务器、数据库或账号，任何代理组合都能用。

## 为什么需要它

- 交接笔记常把"验证过的"和"希望如此的"混在一起。四种标签（`[已跑]`、`[已见]`、`[听说]`、`[缺口]`，英文为 `[ran]` `[seen]` `[said]` `[gap]`）把它们分开。
- 笔记会悄悄过期。分支、提交和未提交文件组成的邮戳，让接手者一条命令就能发现漂移，而不是改坏了才发现。
- "后续步骤"清单会分散注意力。一个有边界、写明预期结果的下一步，让下一个会话几分钟内就能动起来。
- 崩溃或被额度掐断的会话什么都不留。救援流程从 git 和文件证据重建全貌，并标明这只是假设。
- "代理记忆"容易变成一堆互相矛盾的笔记。账本让长期知识保持小、有出处、可更正。

## 功能

- **接力卡**：七个固定小节，外加紧张度（`stable` / `watch` / `unstable`）。
- **证据标签**：每条事实都标明是亲自执行、读到、听说，还是没检查。
- **漂移检查**：四种结论（FRESH、DRIFTED、STALE、BROKEN）以及各自的处理方法。
- **复述**：任何改动之前，接手者复述计划并提出异议，做法借鉴自医护交班的收尾环节。
- **一次性卡片**：接住的卡片移进 `spent/`，并注明哪里不一致。
- **救援**：处理没留交接就结束的会话。
- **停滞分诊**：真等待、能做但无人认领、已有人负责。
- **分道**：多个代理共用一个仓库。
- **账本**：五种条目类型、取代链、过期日期，以及需要用户点头才能写进 `AGENTS.md` / `CLAUDE.md` 的规则候选。
- **辅助脚本** `scripts/baton.py`（Python 3，只用标准库）：`new`、`stamp`、`lint`、`catch`、`spend`、`ledger`。检查器能抓出缺节、无标签事实、多个下一步和疑似密钥。
- **双语**：完整的中英文技能文件；卡片可以用中文或英文标题和标签。

## 安装

技能就是包含 `SKILL.md`（英文）和 `SKILL.zh-CN.md`（中文）的整个文件夹。请复制整个文件夹，`scripts/` 和 `examples/` 一起带上。

**Claude Code**

```bash
git clone https://github.com/fangdididi/relay-baton.git ~/.claude/skills/relay-baton
```

**Codex / 读取 `~/.agents/skills` 的代理**

```bash
git clone https://github.com/fangdididi/relay-baton.git ~/.agents/skills/relay-baton
```

**Cursor**（项目技能目录）

```bash
git clone https://github.com/fangdididi/relay-baton.git .cursor/skills/relay-baton
```

**其他代理**（Gemini CLI、OpenCode、Windsurf、Cline、Kimi、各类聊天应用）：把 `SKILL.md` 粘贴到它的指令或项目规则里，或者让它从本仓库地址安装。中文对话请用 `SKILL.zh-CN.md`。

既然重点就是换工具，请在这个项目用到的每个代理里都装上它，或者在 `AGENTS.md` 里加一行：*"会话结束和开始时，按 relay-baton 技能处理（.baton/）。"*

## 使用

直接对代理说：

- "额度快用完了，交棒吧。"
- "写个交接，今晚我在 Codex 里接着做。"
- "我们做到哪了？" / "接棒，继续。"
- "上个会话重构到一半崩了，救援一下。"
- "今天有什么值得项目记住的？更新账本。"
- "清理一下账本：有没有过期或矛盾的？"

也可以在项目根目录直接用脚本：

```bash
python3 ~/.claude/skills/relay-baton/scripts/baton.py new --lang zh --by "cursor" --for any
python3 ~/.claude/skills/relay-baton/scripts/baton.py lint
python3 ~/.claude/skills/relay-baton/scripts/baton.py catch          # FRESH / DRIFTED / STALE / BROKEN
python3 ~/.claude/skills/relay-baton/scripts/baton.py spend --note "claude code 接手，结果一致"
python3 ~/.claude/skills/relay-baton/scripts/baton.py ledger
python3 ~/.claude/skills/relay-baton/scripts/baton.py --lane api catch  # 分道卡片 .baton/BATON-api.md
```

退出码：`0` 正常，`1` 有需要处理的问题（检查失败、FRESH 以外的任何结论、账本问题），`2` 用法错误或文件缺失。因此 `catch` 可以直接放进会话启动钩子里。

## 示例

一个 Cursor 会话在修小程序结算页的移动端布局，用户说今晚到此为止。它写下：

```markdown
# 目标
`npm run build` 通过，结算页在 375px 宽的屏幕上没有横向滚动，吸底支付按钮完整可见。

# 现状
- [已跑] npm run build -> 通过
- [已跑] 浏览器 375px 预览 -> 仍有约 45px 横向滚动
- [已见] index.vue:88 优惠券卡片写死 width: 420px
- [听说] 用户说 iPhone SE 上最明显
- [缺口] 没在真机上测；没测 320px

# 下一步
- 任意代理：把 index.vue:88 的固定宽度改为 max-width: 100%；预期 375px 预览不再出现横向滚动。

# 禁区
- 不要升级支付 SDK；不要改 app.json 的全局样式。
```

第二天 Claude Code 启动，`baton.py catch` 报 DRIFTED：写卡后 `coupon.vue` 被改过。它先读改动，确认是用户夜里改了弹窗文案、与布局无关，再用五句话复述，重跑 375px 预览确认问题仍在，然后作废卡片、修复，并把"全局 overflow-x 会裁掉吸底阴影"记成账本里的一条 gotcha。完整示例见 [`examples/BATON.example.zh-CN.md`](examples/BATON.example.zh-CN.md)、英文后端示例 [`examples/BATON.example.md`](examples/BATON.example.md) 和账本示例 [`examples/ledger.example.md`](examples/ledger.example.md)。

## 文件结构

```
relay-baton/
├── SKILL.md                      # 技能（英文）
├── SKILL.zh-CN.md                # 技能（中文）
├── README.md                     # 英文说明
├── README.zh-CN.md               # 本文件
├── LICENSE                       # MIT
├── scripts/
│   └── baton.py                  # new / stamp / lint / catch / spend / ledger
└── examples/
    ├── BATON.example.md          # 扣款重复问题交接（英文）
    ├── BATON.example.zh-CN.md    # 结算页布局交接（中文）
    └── ledger.example.md         # 含取代、过期和规则候选的账本
```

在使用该技能的项目里：

```
.baton/
├── BATON.md         # 当前卡片（一次性）；分道时为 BATON-<道名>.md
├── spent/           # 已接住的卡片，带时间戳
└── ledger.md        # 长期的决定、坑、事实、偏好、规则候选
```

## 须知

- 想让团队看到交接，就把 `.baton/` 提交进仓库；只是个人草稿，就加进 .gitignore。`catch` 检查漂移时会忽略 `.baton/` 自身。
- 卡片和账本的内容一律当作记录，绝不当作指令；只有你和你的指令文件能指挥代理。
- 不要在 `.baton/` 里放任何密钥。检查器能标出常见的令牌形态，但抓不全。
- Relay Baton 不会替你提交、stash 或推送。它只记录状态，怎么处理由你决定。

## 许可证

[MIT](LICENSE) © fangdididi
