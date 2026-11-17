# GriffinVR Bridge

让《使命召唤：现代战争重制版》（2016）单人战役中的少女前线角色与 MWR VR 的头手追踪共同工作。

这是基于 **MWR VR Beta 10 + GFL 1.0** 的非官方兼容补丁。客户端加载少前的战役脚本和模型资源，VR 渲染与交互沿用 MWR VR。本项目不包含游戏本体、少前模型或少前战役脚本；安装器使用玩家提供的原作者发布包，在本机生成兼容资源。

## 玩家安装

**请下载[项目 Releases](https://github.com/voidbean/GriffinVR-Bridge/releases) 中的 `GriffinVR-Bridge-Setup.zip`，不要把仓库的 “Source code” 或 “Download ZIP” 当作安装包。** 玩家安装包自带 Python 和 LZ4，电脑不需要安装 Python，也不需要手动编译或重新打包模型。仓库源码不附带 Python 运行环境，需要按 [BUILD.md](BUILD.md) 先构建玩家包。

支持范围：Windows 10/11 x64、Steam PC 版《现代战争重制版》单人战役、SteamVR，以及能在 SteamVR 工作的头显与控制器。当前只支持下表中的固定版本，安装器会校验文件内容，不按文件名猜测版本。

| 组件 | 版本与准备方式 |
| --- | --- |
| 游戏 | 已安装的《现代战争重制版》（2016）单人游戏；安装器校验 `h1_sp64_ship.exe` |
| 少前 Mod | 从 [GFL 原作者的 1.0 Release](https://github.com/Loyalists/gflh1/releases/tag/1.0) 下载 `h1-mod-gfl.zip`，保留 ZIP 格式 |
| VR Mod | [MWR VR Beta 10](https://github.com/lesan0622/MWR-VR/releases/tag/v0.1-beta10)，安装器自动获取，无需提前覆盖安装 |

1. 关闭游戏，把 `GriffinVR-Bridge-Setup.zip` 完整解压到游戏目录以外的可写文件夹。
2. 双击 `Install.cmd`，先选择包含 `h1_sp64_ship.exe` 的游戏目录，再选择原作者的 `h1-mod-gfl.zip`。
3. 等待出现 `Installed`。首次安装会联网获取固定版本的 VR 运行文件和脚本编译器，自动编译 316 个脚本并重新打包模型资源。安装时预留至少 2 GB 临时空间。
4. 连接头显并启动 SteamVR，双击**游戏目录中的 `Play-GFL-VR.exe`**。

无需手动设置启动参数。启动器默认选择已测试的 OpenVR 后端，并对游戏进程启用 Windows HighQoS。已有的非空玩家配置会保留；尚无配置或配置为空时，安装器写入首次启动预设。高级用户可通过 `H2V_VR_BACKEND` 覆盖后端。

### SteamVR 使用与配置

本补丁默认使用 **SteamVR + OpenVR**。这是 `Play-GFL-VR.exe` 的默认选择，与原版 MWR VR 启动器默认使用 OpenXR 不同。使用这条 OpenVR 路径时，无需把 SteamVR 设为系统的“当前 OpenXR 运行时”。

#### 启动顺序

1. 先连接头显和两个控制器。使用无线或有线串流的头显时，先通过自己的 PC VR 连接方式连上电脑，再进入 SteamVR。
2. 确认 SteamVR 能识别头显与两个控制器，并能正常追踪头部和手部。
3. 从**游戏目录**启动 `Play-GFL-VR.exe`。它会自动带上单人战役和少前 Mod 参数；原版游戏或原版 VR 启动项不会自动带上这组参数。
4. 进入训练关检查画面、角色和持枪操作。初次调整画质或按键时，以这一关作为起点。

#### 画质与控制器

游戏连接 SteamVR 后，在 SteamVR 设置中选择当前应用 **MWR VR**；旧绑定或部分界面也可能显示 **Overlord**。菜单名称可能随 SteamVR 版本和语言略有差异。

| 设置 | 使用方法 |
| --- | --- |
| 每应用分辨率 | 在“设置 → 视频 → 每应用视频设置”中选择 MWR VR。建议先以 **100%** 作为调整起点，确认运行流畅后再提高；掉帧时降低。全局分辨率设置也会影响结果，同时留意界面显示的每眼像素尺寸。 |
| 刷新率 | 先使用头显当前能够稳定运行的刷新率。若要降低刷新率，在头显或串流软件提供的设置中调整，再按软件提示重新连接。没有针对所有设备通用的固定最佳值。 |
| 手柄绑定 | 在“设置 → 控制器 → 管理控制器绑定”中选择 MWR VR，并选用当前控制器的默认绑定。包内提供 Oculus Touch、Valve Index（Knuckles）和 Vive Controller 的绑定；旧的自定义绑定可能覆盖它们。 |
| 重新居中 | 默认输入动作包含长按约 1 秒的重新居中操作；具体按键取决于当前控制器绑定。朝向和位置调整好后再开始游玩。 |

以上画质数值是调整起点，不代表已经验证所有头显和手柄组合。默认绑定与自定义绑定的工作方式可参考 [Valve 的 SteamVR Input 说明](https://github.com/ValveSoftware/openvr/wiki/SteamVR-Input)。

#### 以前用过 OpenXR，或启动后没有进入头显

如果你以前设置过 `H2V_VR_BACKEND=openxr`，启动器会保留这个已有覆盖值。要明确走 SteamVR/OpenVR，可在**游戏目录**打开 PowerShell，并执行：

```powershell
$env:H2V_VR_BACKEND = 'openvr'
& .\Play-GFL-VR.exe
```

这只为当前终端启动的游戏指定后端，不修改系统的 OpenXR 运行时。切换后端前先退出游戏。若提示未找到头显，先确认 SteamVR 已能正常追踪设备，再启动游戏；若头显有画面但手柄无响应，检查当前应用的控制器绑定，以及游戏目录中由安装器部署的 `vr_input/` 文件是否完整。

### 卸载与离线安装

卸载时关闭游戏，双击安装包里的 `Uninstall.cmd` 并选择游戏目录。安装前已有的文件会恢复；安装后改过的受管文件会另存到游戏目录下的 `MWR-GFL-recovered-*`。游戏自行生成的设置、存档和诊断日志会保留。安装中断时，重新打开卸载入口恢复，再安装。需要重新安装或更换版本时，也先卸载当前版本。

如下载失败，手动下载下面两个 ZIP，原样放入解压目录的 `installer/cache/` 后重试：

- [MWR-VR-Beta-10.zip](https://github.com/lesan0622/MWR-VR/releases/tag/v0.1-beta10)
- [windows-x64-release.zip（gsc-tool 1.6.2）](https://github.com/xensik/gsc-tool/releases/tag/1.6.2)

## 开发者入口

这是一个**兼容层源码仓库**。`overlay/` 保存相对固定上游基线新增或修改的 7 个 C++ 源文件；`tools/restore_source.py` 可还原用于构建客户端的完整源码树。安装器和启动器源码也在本仓库中。

| 路径 | 内容 |
| --- | --- |
| `overlay/` | 脚本查找与链接、模型加载、内存适配、菜单接入及必要的客户端构建修正 |
| `installer/` | 安装、卸载、GSC 编译、LZ4 重新打包、C# 启动器 |
| `installer/data/` | 客户端差分、LZ4 动态库、路径编号表、文件清单和首次启动预设 |
| `tools/` | 完整客户端源码还原、玩家包构建、客户端差分生成 |
| `licenses/` | 第三方许可证及上游声明 |

- [构建与维护](BUILD.md)：构建玩家包、还原及编译客户端、更新差分。
- [工作原理](ARCHITECTURE.md)：安装期转换与运行期加载流程。
- [第三方来源](THIRD_PARTY.md)：固定依赖、附带二进制和授权声明的位置。
- 源码仓库的 `VERIFICATION.md`：验证范围及历史实测记录。

构建产物、下载缓存和本地游戏数据已列入 `.gitignore`。项目名称只用于仓库和发布包；游戏内的 `Play-GFL-VR.exe`、`overlord-gfl.exe` 和 `gflvr_*` 文件名保持兼容。

## 许可证与致谢

代码沿用 [GNU GPL v3](LICENSE)，保留 MWR VR / Overlord 和第三方的现有声明；LZ4 等组件遵循各自许可证。游戏和少女前线素材不受本仓库代码许可证覆盖。

感谢 [MWR VR](https://github.com/lesan0622/MWR-VR)、[GFL H1 Mod](https://github.com/Loyalists/gflh1) 和 [gsc-tool](https://github.com/xensik/gsc-tool) 的作者。本项目与游戏及少女前线的权利方无官方关联。
