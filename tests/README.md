# 测试

`LibraryRegression.java`：JSON 格式、字段顺序、未知字段保留、歌曲/曲包/分类的删除、移动、撤销所需目录操作，以及封面裁剪几何。没有外部目录数据时执行 31 项；另外提供两版原始 packlist 时执行 113 项。

`PackCoverRegression.java`：默认封面、三种原生路径、版本图片映射、迁移幂等性、非法路径、布局几何，共 67 项。需要 Android graphics 运行时，必须在正常应用 instrumentation 中运行；普通桌面 JVM 或独立 app_process 不适合执行 Bitmap/字体测试。

`LibraryTestRunner.java` 为壳子版 instrumentation 入口。运行前需准备对应的目标 APK 和匹配签名，编译目标版本插件及测试 Java，使用 D8 生成测试 DEX，并用本目录 AndroidManifest.xml 打包测试 APK。将自行提供的两版原始 packlist 放在测试设备 `/data/local/tmp/full-packlist.json` 与 `/data/local/tmp/shell-packlist.json`。安装测试 APK 后执行：

```text
adb -s <test-device-serial> shell am instrument -w moe.practice.regression/moe.practice.LibraryTestRunner
```

测试会在目标应用内部创建临时封面目录；应使用可丢弃的模拟器实例。目标应用的签名材料不随仓库发布。

`ArchiveRegression.java` 和 `MetadataRegression.java` 保留 ZIP/AFF/背景与作者元数据回归。前者需要自行准备含 AFF、音乐、曲绘和元数据的测试 ZIP；仓库不包含实际歌曲资源。

`transport_test.cpp` 是不依赖 Android 的时钟与三秒预备阶段测试：

```text
c++ -std=c++17 tests/transport_test.cpp -o transport-test
./transport-test
```

详细已有验证范围见上级 VALIDATION.md。发布隐私扫描不能代替功能回归。

隐私扫描器使用合成数据执行 10 项检查，包括令牌、私钥、个人路径、邮箱和签名库类型的拒绝，以及正常文档/摘要/匿名邮箱的放行：

```text
python tests/privacy_test.py
python privacy_check.py
```

## offset 与倍速

`offset_test.cpp` 可直接在桌面 C++17 环境执行。它包含正负设备 offset、非零 AFF AudioOffset、全部 0.01 倍速档位、重复应用防二次缩放、暂停、跳转及三秒预备验证。

没有桌面 C++ 编译器时，可以用 Android NDK 把测试编译成 ARM64 共享库，并在安装了 `unicorn`、`pyelftools` 的 Python 环境运行：

```text
clang++ --target=aarch64-linux-android24 -shared -fPIC -O2 -std=c++17 -fno-math-errno -DARC_TIMING_EMULATED -nostdlib tests/offset_test.cpp -o timing-test.so
python tests/native_clock_test.py --helpers timing-test.so --full full-game.so --shell shell-game.so
python tests/compiled_clock_test.py --full-plugin full-plugin.so --shell-plugin shell-plugin.so --full-game full-game.so --shell-game shell-game.so
```

游戏库需自行从支持的 APK 提取；插件库使用 build.py 的最终编译产物。模拟测试不会播放实际音频，也不代表已完成实机延迟测量。

## 实际音频渲染

`audio_render_test.cpp` 调用 APK 使用的生产渲染函数。桌面 C++17 编译器需一并编译 third_party/soundtouch/source/SoundTouch 下的 cpp 文件，包含 third_party/soundtouch/include 目录，并定义 SOUNDTOUCH_DISABLE_X86_OPTIMIZATIONS。GCC/Clang 桌面测试还可定义 ANDROID，以跳过上游 configure 生成头文件的依赖；不影响此处浮点处理逻辑。

编译得到 audio-render-test 后，Python 测试需要 numpy：

```text
python tests/audio_quality_test.py --renderer ./audio-render-test --report audio-quality-regression.json
```

测试包含 12 组代表性倍率/音高模式、时长、音高、立体声、有限数值及保持原调时的 18 kHz 高频成分。同时检查全部 100 个加速档位的 500 个短起音，要求不丢失且起音误差小于 25 ms。合成测量不能证明所有歌曲的主观听感与原速完全一致。

音频依赖随源码提供：Signalsmith Stretch、Signalsmith Linear（MIT）及 SoundTouch（LGPL-2.1-or-later）。宿主音频测试额外包含 third_party/signalsmith-stretch 与 third_party/signalsmith-linear/include 两个头文件搜索目录；Android build.py 已配置这些目录。

## 高刷新率时间步进

用 C++17 编译并运行 playback_sync_test.cpp，调用生产的 native/playback_sync.h；涵盖 150 组刷新率/倍率/漂移及恢复/无音乐位置场景。

compiled_sync_test.py 的参数与 compiled_clock_test.py 相同，使用最终两版插件 SO 与原游戏 SO。测试执行真实 ARM64 时钟钩子，以 144 Hz 驱动并模拟量化的音乐位置，检查谱面时间不重复、不倒退及查询次数；--baseline 用于测量旧版，而不要求旧版满足平滑断言。它不测量 GPU 或实体显示帧率。

compiled_settings_test.py 参数同 compiled_clock_test.py，执行最终插件 ARM64 钩子读取模拟的活动原生设置，检查两条设置模式、全部 176 个倍率、连续切换、编辑及设置不可回写。每版 7400 组。offset_test.cpp 增补 10580 项显式设置基准检查。


## 解码起点与缓存

`decoded_cache_test.py` 检查实际 FMOD 生成的合成测试缓存：完整 PCM 帧数、采样率与第一个音乐脉冲是否保留。测试需要 numpy。42 秒、48 kHz 测试源的第一个脉冲在第 5 秒，左右声道应预先按测试方法生成；不要拿任意歌曲代替此固定 fixture。

```text
python tests/decoded_cache_test.py --cache fixture-tempo.wav --rate 0.5 --source-seconds 42 --sample-rate 48000 --report decoded-cache.json
```

实际混音测量方法、旧版对比及限制见 AUDIO_ORIGIN_FIX.md。缓存测试只核验解码完整性，不代替音乐与判定混音对齐测量。

可用 `python tests/audio_origin_fixture.py fixture-output` 生成测试源、对应 AFF 与右声道参考点击声。该脚本只生成原创合成信号。
