# 构建说明

## 环境

Python 3.11+、JDK 17、Android API 35、build-tools 35.0.0、NDK r29。Windows 为本次验证环境；脚本也提供 Linux/macOS 工具路径选择，但尚未在这两个系统执行验证。

设置 `JAVA_HOME`、`ANDROID_HOME`（或 `ANDROID_SDK_ROOT`），NDK 位于 SDK 的 `ndk/29.0.14206865` 时可以自动查找；其他位置通过 `--ndk` 或 `ANDROID_NDK_HOME` 指定。非标准 SDK 目录可分别传入 `--android-jar`、`--build-tools`。

## 仅编译插件

```powershell
python build.py --variant shell --compile-only
python build.py --variant full --compile-only
python build.py --variant arc701 --compile-only
```

产物在 `out/shell`、`out/full`、`out/arc701`，包含 `libarcpractice.so`、Java 字节码和 DEX。此模式无需 APK 或签名密钥。

## 重打包

输入必须是已经带练习插件的对应 APK：壳子 r3（也支持 r2）或一体 r10（也支持 r9）。未注入插件的原版 APK 不适用于此增量构建器。脚本保留包名和其他 DEX，只替换壳子 `classes3.dex` / 一体 `classes4.dex` 与 `libarcpractice.so`。

```powershell
# 先生成可核验但不可直接安装的未签名产物
python build.py --variant shell --base-apk ./inputs/shell.apk --unsigned

# 将签名密码安全地设置到 ARCPRACTICE_SIGNING_PASS 环境变量后执行
python build.py --variant shell --base-apk ./inputs/shell.apk --keystore ./private/signing.p12 --key-alias enhanced
python build.py --variant full --base-apk ./inputs/full.apk --keystore ./private/signing.p12 --key-alias enhanced
```

密码通过 Java `env:` 参数读取，不写入命令行或构建报告。密钥与密码由构建者自行保管。覆盖安装必须使用原应用的同一签名；仓库不提供发布签名。

重打包前会核对游戏原生库 SHA-256 及插件 DEX 布局。完成后会验证所有 ZIP 条目 CRC、资源条目保留情况、插件文件一致性、16KB 对齐和签名，并生成 `verification.json`。原生钩子启动时还会检查目标指令序言；不支持的构建不会继续安装钩子。

本仓库只提供增量构建所需源码，不包含游戏 APK、音乐、曲绘、谱面、游戏字体、SDK、NDK 或任何密钥。测试数据见 [tests/README.md](tests/README.md)。

## 音频库

build.py 会编译随源码提供的 Signalsmith Stretch / Linear 与 SoundTouch 2.4.1，不需要下载额外音频预编译库；可以更改或替换其源码后重新链接插件。许可与固定版本见 THIRD_PARTY_NOTICES.md。当前 r4/r11 及后续兼容 APK 也可作为基底，判断依据是原生库摘要与插件 DEX 布局。

音频依赖随源码提供：Signalsmith Stretch、Signalsmith Linear（MIT）及 SoundTouch（LGPL-2.1-or-later）。宿主音频测试额外包含 third_party/signalsmith-stretch 与 third_party/signalsmith-linear/include 两个头文件搜索目录；Android build.py 已配置这些目录。


## Arc701 7.0.1c

已注入版使用 `build.py --variant arc701` 增量构建，目标为 classes3.dex。首次为未注入的指定原 APK 构建，使用 `inject_arc701.py`，额外传入 Apktool 3.0.3 的 jar 路径；该工具会检查原生库摘要、修改外置资源引导及两个绘制分支，再调用同一个 build.py。

```text
python inject_arc701.py --base-apk ./inputs/Arcaea.apk --apktool ./tools/apktool.jar --java-home ./tools/jdk-17 --output ./out --ndk ./tools/ndk-r29 --build-tools ./tools/build-tools-35 --android-jar ./tools/android-35/android.jar --keystore ./private/signing.p12
```

签名密码仍通过 ARCPRACTICE_SIGNING_PASS 环境变量传递。输出包名 moe.low.Arc701.practice，继续使用原 Arc701 外置目录。初始注入保留原始 resources.arsc 的资源 ID，仅调整包名；不使用 Apktool 重建后的资源表替换游戏资源。
