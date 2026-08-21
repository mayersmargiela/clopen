# 更新日志 / Changelog

本项目从首次公开发布开始记录真实变更，不回填未公开历史。

This project records real changes beginning with its initial public release. Unpublished history is not backfilled.

## [0.6.0] - 2026-08-21

### 中文

- 将主界面升级为 Liquid Glass 视觉系统，并统一组合编辑器、软件选择器、设置与托盘菜单的界面。
- 使用持久化原生 Qt 弹窗承载 `Ctrl+Shift+E` 快捷菜单，避免运行时创建 QML 弹窗的不稳定路径。
- 将快捷键检测改为后台物理按键轮询，并通过 Qt 队列信号回到 GUI 线程显示菜单。
- 保持 `%APPDATA%\Clopen\config.json` 配置兼容和会话级安全关闭边界。
- 增加 QML、运行链和 Windows 快捷键冒烟测试。

### English

- Upgraded the main interface to the Liquid Glass visual system and aligned the group editor, software picker, settings, and tray menu.
- Moved the `Ctrl+Shift+E` quick menu to a persistent native Qt popup, avoiding fragile runtime QML popup creation.
- Replaced shortcut registration with background physical-key polling and a queued Qt signal back to the GUI thread.
- Preserved `%APPDATA%\Clopen\config.json` compatibility and session-safe process-closing boundaries.
- Added QML, runtime-chain, and Windows hotkey smoke tests.

## [0.2.7] - 2026-08-13

### 中文

- 首次公开发布 Clopen Classic。
- 支持创建、编辑、搜索和运行软件组合。
- 支持 `Ctrl+Shift+E` 快捷菜单。
- 仅关闭本次由 Clopen 启动并登记的进程。
- 配置保存在本地 `%APPDATA%\Clopen\config.json`。

### English

- Initial public release of Clopen Classic.
- Create, edit, search, and run application groups.
- Open the quick menu with `Ctrl+Shift+E`.
- Close only processes started and registered by the current Clopen session.
- Store configuration locally at `%APPDATA%\Clopen\config.json`.
