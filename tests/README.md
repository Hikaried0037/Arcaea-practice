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
