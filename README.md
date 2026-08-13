# Clopen

[中文](#中文) · [English](#english)

## 中文

Clopen 是一个面向 Windows 的软件组合启动器。你可以把工作、创作或游戏需要的软件保存为组合，一次打开，并只关闭本次由 Clopen 启动且登记成功的进程。

### Classic v0.2.7

- 创建、编辑和运行软件组合。
- 搜索本机已安装软件并添加到组合。
- 使用 `Ctrl+Shift+E` 打开快捷菜单。
- 会话级安全关闭：只处理本次由 Clopen 启动并记录的进程。
- 配置保存在 `%APPDATA%\Clopen\config.json`，不上传软件列表或配置。

### 安全边界

Clopen 不按进程名全局结束进程，也不会把用户手动启动的同名程序当作本次会话进程。浏览器复用实例、文件、文件夹和 UWP 应用默认不保证可由 Clopen 关闭。Clopen 不会在没有用户快捷键操作时主动弹出快捷菜单。

### 系统支持

- Windows 11：首发验证平台。
- Windows 10：尚未完成正式实测，仅尽力支持。

### 从源码运行

需要 Python 3.11 或更高版本。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\clopen.exe
```

运行测试：

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 隐私与许可

Clopen 在本地运行。详情见 [PRIVACY.md](PRIVACY.md)。项目采用 [MIT License](LICENSE)，第三方组件许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## English

Clopen is a Windows application-group launcher. Save the apps you need for work, creation, or gaming, open them together, and close only the processes that Clopen started and registered during the current session.

### Classic v0.2.7

- Create, edit, and run application groups.
- Search installed applications and add them to a group.
- Open the quick menu with `Ctrl+Shift+E`.
- Session-safe closing: only processes started and recorded by the current Clopen session are handled.
- Configuration stays at `%APPDATA%\Clopen\config.json`; application lists and settings are not uploaded.

### Safety boundaries

Clopen does not terminate processes globally by executable name and does not treat a manually started process with the same name as part of the current session. Reused browser instances, files, folders, and UWP apps are not guaranteed to be controllable by Clopen. The quick menu is not shown unless the user invokes its shortcut.

### System support

- Windows 11: primary verified release platform.
- Windows 10: not formally tested yet; best-effort support only.

### Run from source

Python 3.11 or newer is required.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\clopen.exe
```

Run tests:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Privacy and licensing

Clopen runs locally. See [PRIVACY.md](PRIVACY.md) for details. The project is distributed under the [MIT License](LICENSE); third-party licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
