# 贡献指南 / Contributing

## 中文

感谢你帮助改进 Clopen。

1. 提交 Issue 前请先搜索现有 Issue 和 Discussions。
2. Bug 报告请包含 Windows 版本、Clopen 版本、复现步骤、预期结果和实际结果；请移除用户名、路径和软件列表等私人信息。
3. 功能建议应说明要解决的问题和使用场景。
4. Pull Request 应保持范围清晰，附测试；涉及进程关闭逻辑时，必须证明不会关闭用户手动启动的同名进程。
5. 代码、测试和文档变更应保持中英文用户文案一致。

本地检查：

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
python tools\release_selfcheck.py
```

参与即表示同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## English

Thank you for helping improve Clopen.

1. Search existing Issues and Discussions before opening a new Issue.
2. Bug reports should include the Windows version, Clopen version, reproduction steps, expected result, and actual result. Remove private information such as usernames, paths, and application lists.
3. Feature requests should explain the problem and use case.
4. Pull Requests should be narrowly scoped and include tests. Changes to process-closing logic must demonstrate that manually started processes with the same executable name remain untouched.
5. Keep Chinese and English user-facing text aligned when changing code, tests, or documentation.

Local checks:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
python tools\release_selfcheck.py
```

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report security issues privately as described in [SECURITY.md](SECURITY.md).
