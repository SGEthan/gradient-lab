# Gradient Lab

100 道原创 ML coding 练习，覆盖 9 个专题。可在 Mac 上用 Python、NumPy 和 PyTorch 练习，也可在 GitHub Pages 上使用 Python 和 NumPy。

## 开始练习

双击「启动.command」，或在终端运行同名文件。浏览器会打开 http://127.0.0.1:8765。第一次安装 NumPy 和 PyTorch 需要联网，依赖装好后可以离线练习。启动器所在的终端窗口保持打开即可，按 Ctrl+C 可以停止该次启动的服务。

- **运行**执行两个公开测试。编辑器内按 ⌘+Enter 也可以运行。
- **提交**执行全部测试，全部通过后计入进度。编辑器内按 ⌘+Shift+Enter 也可以提交。
- 代码草稿和通过记录保存在当前浏览器。以后用相同的浏览器打开同一个地址即可继续。
- 左侧按题名或运行环境过滤。参考解法可以在题目面板里展开。
- 可组合筛选运行环境、专题和难度。

## 本地判题

服务绑定到 IPv4 回环地址。每次提交在单独的 Python 进程和临时目录里执行，超时为 15 秒。Mac 判题进程使用系统的 sandbox-exec，禁用网络并限制对用户文件的读写。此应用设计用于本机个人练习。

如果端口 8765 被其他服务占用，可以在终端为启动脚本设置 GRADIENT_LAB_PORT。换端口后浏览器会视为不同的存储来源。

原始题目位于 `problems.py`，新增题目、参考解法和用例按专题放在 `sets/`。网页代码位于 `static/`。

## GitHub Pages

[打开网页版](https://sgethan.github.io/gradient-lab/)

用 Python 3.10 或更高版本运行 `python3 build_pages.py` 生成 `docs/`，再将 GitHub Pages 的发布来源设为主分支的 `/docs`。

网页版首次判题时从站点加载随构建发布的 Pyodide 环境，并在浏览器 Web Worker 中执行代码。6 道原生 PyTorch 题在网页版使用同主题 NumPy 版本。两种入口按各自的浏览器地址保存草稿和进度。
