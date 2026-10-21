# 构建和验证 iOS r22

需要 Python 3.11+、Zig 0.15.2、Node.js；宿主 ARM64 测试还需 `python -m pip install -r source/requirements.txt`。UI 检查需 Playwright 及本机 Microsoft Edge，可设置 `PLAYWRIGHT_MODULE` 指向已安装模块。该工程通过 Zig 生成 ARM64 对象，再用受限确定性 Mach-O 链接器链接，不需要导出签名身份。

## 构建全曲包

在仓库根目录执行，路径中的占位值替换为实际路径：

```text
python tools/check.py --ipa /path/to/original.ipa --zig /path/to/zig --node /path/to/node
python source/patch_ios.py /path/to/original.ipa /path/to/ArcPrac-r22-Full-unsigned.ipa --zig /path/to/zig
```

全曲包不要加 `--sayonara-only`。该选项只用于单曲诊断包。输入必须为最初的 fix14 IPA；已打补丁的 r22 不能作为输入。脚本会检查原始主程序与插件哈希，拒绝不匹配的版本。

`tools/check.py` 从输入 IPA 提取当前测试所需的原始主程序和插件到被忽略的 `source/binaries/`，重建当前插件与汇编对象，并运行当前的原生/曲库/背景/迁移测试。可加 `--ui` 验证浏览器交互和布局，自动从 IPA 提取 UI 字体，仅留本地。报告写入被忽略的 `source/` 构建输出。没有旧 r12/r13 构建时明确跳过历史二进制复现，当前版本测试继续执行。`test_library_native.py SAMPLE_ZIP` 另需当时的特定用户样例，默认不执行，其原发布记录仍保留。

完整 IPA 构建后，需自行签名整个 app 及两个嵌入 dylib。使用原有签名账号及 Bundle ID 配置覆盖安装；首次打开曲库管理，待恢复保存后应用并重新载入。不会在仓库保存证书或预置描述文件。

宿主测试不执行 iOS dyld、UIKit/WKWebView、原生音频解码与实际游玩，仍需 iPad 实机确认。详细检查范围见各验证 JSON 的 scope 字段。
