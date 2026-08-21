# 维护者 / Maintainers

## 中文

### 主要维护者

- [Mayers Margiela](https://github.com/mayersmargiela) — 发起人和主要维护者。

主要维护职责包括产品方向、Issue 分类、测试验收、版本发布、安全边界和社区反馈处理。影响进程关闭边界的变更必须附带回归测试，证明不会关闭用户手动启动的同名进程。

### 维护原则

- 只记录真实公开的发布、Issue、反馈和修复，不回填或制造维护活动。
- Bug 修复应包含可复现问题、验证方法和对应测试。
- 发布前必须通过 Windows CI、发布自检、源码冒烟测试和打包后冒烟测试。
- 工具或 AI 可以协助编码、测试和审查；主要维护者对方向、验收和发布承担责任。

公开维护记录见 [`docs/maintenance/`](docs/maintenance/)。

## English

### Primary maintainer

- [Mayers Margiela](https://github.com/mayersmargiela) — founder and primary maintainer.

Primary responsibilities include product direction, issue triage, test acceptance, release management, safety boundaries, and community feedback. Changes affecting process-closing boundaries must include regression coverage proving that manually started processes with the same executable name remain untouched.

### Maintenance principles

- Record only real public releases, issues, feedback, and fixes; do not backfill or manufacture activity.
- Bug fixes should include a reproducible problem, a verification method, and corresponding tests.
- Releases must pass Windows CI, the release self-check, source smoke tests, and packaged smoke tests.
- Tools or AI may assist with coding, testing, and review; the primary maintainer remains responsible for direction, acceptance, and release decisions.

See [`docs/maintenance/`](docs/maintenance/) for the public maintenance record.
