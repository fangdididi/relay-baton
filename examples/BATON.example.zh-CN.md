---
baton: 1
written_at: 2026-10-22T14:20:00Z
written_by: cursor（结算页布局会话）
for: any
lane: main
tension: stable
stamp_branch: fix/checkout-375
stamp_head: 7a0c3d15e2b9
stamp_dirty: src/pages/checkout/index.vue
---
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

# 如果-那么
- 如果改完仍有滚动：检查优惠券弹窗的 min-width。
- 如果吸底按钮被遮住：是底部安全区，不是这次的改动造成的。

# 禁区
- 不要升级支付 SDK；不要改 app.json 的全局样式。

# 死路
- 全局加 overflow-x: hidden：滚动没了，但吸底按钮的阴影被裁掉，用户否决了。

# 待解问题
- 需要兼容 320px 吗？问用户。
