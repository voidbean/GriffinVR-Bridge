# 构建和维护

下文面向开发者。玩家使用自带 Python 的安装包，不需要以下开发环境。所有命令都从本仓库根目录开始；依赖可以放在其他位置，并在命令中传入对应路径。

## 构建玩家安装包

这一步使用仓库附带的已验证客户端差分，不需要先编译 C++。

要求 Windows x64、Python 3.13.5，以及 Windows 的 .NET Framework 4.x C# 编译器。`tools/package.py` 使用 `%WINDIR%/Microsoft.NET/Framework64/v4.0.30319/csc.exe` 构建启动器，无需单独安装 .NET SDK。

1. 下载 [CPython 3.13.5 Windows x64 嵌入包](https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip)，保留 ZIP。
2. 运行：

```powershell
python tools/package.py --python-embed python-3.13.5-embed-amd64.zip --output dist/GriffinVR-Bridge-Setup.zip
```

打包器校验嵌入包 SHA-256，编译 `installer/Play-GFL-VR.cs`，把 Python 运行环境、安装代码、许可证和必要数据打成玩家 ZIP。安装器运行时还会下载并校验固定版本的 VR 文件和 GSC 编译器；离线缓存方法见 [README.md](README.md)。

`dist/` 不进入 Git。发布时把生成的 ZIP 作为仓库 Release 的附件上传；默认的 “Source code” ZIP 是源码，不是玩家安装包。需要校验值时运行：

```powershell
Get-FileHash dist/GriffinVR-Bridge-Setup.zip -Algorithm SHA256
```

## 还原完整客户端源码

基线为 [MWR VR v0.1-beta10 完整源码发布包](https://github.com/lesan0622/MWR-VR/releases/download/v0.1-beta10/MWR-VR-Beta-10-source.zip)，内含对应依赖。还原工具校验包的 SHA-256，再叠加本仓库的 7 个 C++ 源文件。目标目录必须尚不存在。

```powershell
python tools/restore_source.py MWR-VR-Beta-10-source.zip work/client
```

`work/client/` 是完整构建目录，不应提交到这个兼容层仓库。上游许可证、依赖声明和原有资源说明随上游源码保留。

## 重新编译客户端

需要 Windows x64、Visual Studio 2022 C++ 桌面工作负载、Windows SDK。上游完整项目还使用 Python、Node.js 24、npm 和 CMake；具体生成步骤与依赖按还原后源码中的 README 执行。

在 **x64 Native Tools Command Prompt for VS 2022** 中进入还原目录：

```bat
cd work\client
tools\premake5.exe vs2022
msbuild build\overlord.sln /t:client /m:2 /p:Configuration=Release /p:Platform=x64
```

输出为 `work/client/build/bin/x64/Release/overlord.exe`。安装器应用差分后使用的名称是 `overlord-gfl.exe`。构建环境、调试信息和时间戳可能改变文件哈希；仓库中的差分对应既有实测构建，不能假定重新编译后的文件逐字节相同。

## 修改兼容代码后更新发布包

1. 在 `overlay/` 中修改相应文件，再还原到新的构建目录；如果直接修改了 `work/client/`，把最终改动同步回对应的 `overlay/` 文件。
2. 编译客户端并完成相关游戏验证。
3. 下载固定的 [MWR-VR-Beta-10.zip](https://github.com/lesan0622/MWR-VR/releases/tag/v0.1-beta10)。在开发环境安装 `bsdiff4==1.2.6`，然后从本仓库根目录生成差分：

```powershell
python -m pip install bsdiff4==1.2.6
python tools/make_delta.py MWR-VR-Beta-10.zip work/client/build/bin/x64/Release/overlord.exe installer/data/client.bsdiff
```

4. 将工具输出的客户端 SHA-256 更新到 `installer/payload.py` 的 `CLIENT`，将补丁 SHA-256 更新到同文件中 `verify(delta_file, ...)` 的值。
5. 重建玩家安装包，执行安装、进关和卸载验证。仅构建玩家 ZIP 不需要安装 `bsdiff4`。

## 验证范围

发布前至少检查：

- 使用玩家包自带的解释器完成安装，不依赖系统 Python。
- 从指定 GFL 1.0 ZIP 生成 316 个脚本、模型资源和客户端；最终内容通过安装器中的固定哈希校验。
- 测试已有配置保留、原文件备份与恢复，以及安装后修改文件的保留。
- 启动 `Play-GFL-VR.exe`，实际进关，并在头显中检查少前角色、双眼画面与控制器交互；仅验证 ZIP 能生成不能替代游戏验证。
- 确认发布内容仅为预期源码或玩家包，不包含本地游戏资源、GFL 原包、存档、日志、调试转储、下载缓存或凭据。

现有验证记录位于源码仓库的 `VERIFICATION.md`。依赖来源与许可证位置见 [THIRD_PARTY.md](THIRD_PARTY.md)。
