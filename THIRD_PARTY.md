# 第三方来源与许可证

本项目保留现有 GPLv3 代码许可和上游声明。项目更名不改变各组件的来源与归属。以下是源码与安装器实际使用的固定基线。

| 组件 | 来源与版本 | 本仓库中的形式 |
| --- | --- | --- |
| MWR VR / Overlord | [lesan0622/MWR-VR v0.1-beta10](https://github.com/lesan0622/MWR-VR/releases/tag/v0.1-beta10) | `overlay/` 中的 7 个新增或修改源文件，以及 `installer/data/client.bsdiff`；完整源码通过固定上游源码包还原 |
| GFL H1 Mod | [Loyalists/gflh1 1.0](https://github.com/Loyalists/gflh1/releases/tag/1.0) | 不随仓库或玩家包分发；由玩家提供原始 ZIP |
| gsc-tool | [xensik/gsc-tool 1.6.2](https://github.com/xensik/gsc-tool/releases/tag/1.6.2) | 安装时下载；仅五项 H1 路径编号表保存在 `installer/data/h1-paths.txt`，保留 GPLv3 来源声明 |
| LZ4 | [lz4/lz4 1.9.4](https://github.com/lz4/lz4/releases/tag/v1.9.4) | `installer/data/liblz4.dll`；来自 Anaconda defaults 的 win-64 `lz4-c 1.9.4 h2bbff1b_1`；BSD 2-Clause 声明位于 `licenses/LZ4.txt` |
| CPython | [Python 3.13.5](https://www.python.org/downloads/release/python-3135/) | 构建玩家包时加入官方 Windows x64 嵌入包；不进入源码仓库；原包许可证保留为 `installer/runtime/LICENSE.txt` |
| bsdiff4 | 1.2.6 | 仅开发者重新生成客户端差分时使用，不随仓库或玩家包附带；玩家安装器使用本仓库的 `installer/delta.py` 应用差分 |

固定的下载版本与 SHA-256 位于 `installer/payload.py`、`tools/package.py` 和 `tools/restore_source.py`。`client.bsdiff` 是客户端二进制差分，不是游戏本体补丁；生成它所需的源码还原和构建步骤见 [BUILD.md](BUILD.md)。

`licenses/MWR-VR-NOTICES.md` 和 `licenses/MWR-VR-provenance.md` 原样保留上游记录。其中提到的 `deps/`、`data/`、`THIRD_PARTY_NOTICES.md` 等路径属于还原后的完整上游源码树，不表示这些文件都打包在本兼容层仓库里。还原源码时应一并保留其原始声明。

本仓库不包含商业游戏文件、GFL 模型、GFL 源脚本、玩家配置或存档；`first-run.cfg` 是安装器随附的首次启动预设。游戏、少女前线及其他第三方素材的权利归各自权利人，根目录的代码许可证不覆盖这些素材。
