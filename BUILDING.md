# 从源码构建

此工程针对 Infinity 7.0.1f 的特定 ARM64 原生库。请自行准备匹配的原始 APK；原生库哈希不匹配时脚本会停止。分享包内的改包不能作为原始输入。

## 环境

在 Windows PowerShell 5.1 或以上运行，准备以下工具：

- Python 3.11 或以上，放入 PATH；脚本只使用 Python 标准库。
- JDK 21，设置 `JAVA_HOME`，或用 `-JavaHome` 指定安装目录。
- Android SDK，设置 `ANDROID_HOME` 或 `ANDROID_SDK_ROOT`，或用 `-AndroidSdk` 指定。
- SDK Platform `android-35`、Build Tools `35.0.0`、NDK `29.0.14206865`。
- Apktool `3.0.3` 的 JAR 文件，放到自行选择的位置。

解压源码 ZIP 后，目录应包含 `practice/build.ps1`。在解压位置运行，替换下例的输入 APK 和 Apktool 路径：

```powershell
& .\practice\build.ps1 `
  -SourceApk '.\inputs\original.apk' `
  -ApktoolJar '.\tools\apktool_3.0.3.jar'
```

若未设置环境变量，追加 `-AndroidSdk '你的 SDK 目录' -JavaHome '你的 JDK 目录'`。还可用 `-Python` 指定 Python 可执行文件；版本参数为 `-NdkVersion`、`-BuildToolsVersion` 和 `-AndroidPlatform`。

先追加 `-ValidateOnly` 可检查工具路径和输入原生库，不生成安装包。完整构建输出默认为源码目录旁的 `output/`；用 `-OutputDir` 可指定其他目录。中间产物保存在 `practice/build/`，输入 APK 不会被改写。

## 签名与后续更新

第一次构建默认生成自己的签名密钥 `practice/build/practice.p12`，随机密码保存在同目录的 `.keystore-password`。两者应妥善保留，后续更新使用同一密钥；不要放入公开分享包或源码仓库。

使用已有密钥时，可传入 `-KeyStore`、`-KeyAlias` 和 `-KeyStorePasswordFile`。也可在运行前自行设置 `ARCPRACTICE_KEYSTORE_PASS`；脚本通过进程环境向签名工具传递密码。

源码包不包含分享版的签名私钥。自行构建的 APK 使用自己的签名，不能直接覆盖已安装的分享版。建议追加 `-PackageName moe.inf.arc.practice.custom` 使用另一包名并存，避免为了换签名丢失现有存档。

## 验证与测试包

构建脚本会执行原生库版本检查、签名校验和 ZIP / 原生库对齐检查。完整包还可执行资源一致性检查：

```powershell
python .\practice\verify_package.py `
  '.\inputs\original.apk' `
  '.\output\Arcaea-Infinity-7.0.1f-Practice-standalone-full.apk' `
  --package-name moe.inf.arc.practice
```

自定义包名时同步修改最后的参数。该检查针对完整包，不适用于音频经过替换的测试包。

追加 `-TestOnly` 可构建较小的模拟器测试包，部分未测试歌曲音频会替换成 `support/test-silence.ogg` 中的生成静音。测试包仅用于调试，应分享完整包给普通使用者。

本工程没有修改游戏原生库文件，但使用固定地址注入钩子。更换游戏版本需要重新分析，不能只修改版本名或移除哈希校验。
