# Arcaea Practice · iOS r22 全曲包

本分支保存 iOS fix14 宿主的 r22 修复与 ArcLibrary 曲库插件源码。Android 最新源码保留在 [main 分支](https://github.com/Hikaried0037/Arcaea-practice/tree/main)。

完整 IPA 恢复原版 562 首歌曲、63 个曲包；保留练习面板、前后台/暂停、搭档、ETR/BYD 难度切换、自定义谱面及背景导入等已有修复。不会额外打入测试曲目；升级时保留已有导入内容。

- `source/`：当前生产源码、受限 Mach-O 链接器、修补脚本和回归测试；仅保留 r22 版本。
- `verification/`：r22 发布检查记录及本次源码导出检查。旧故障的复现描述属于回归证据，不是旧版交付。
- [构建与检查](BUILDING.md)、[安装与验证](INSTALL.md)、[详细实现与历史修复说明](source/README.md)。

这是特定 fix14 二进制布局的修补工程，不是完整游戏源码。构建需要自行提供哈希匹配的原始 IPA。仓库不包含游戏程序/歌曲/字体、IPA、签名材料、设备日志或个人测试附件。`source/previous_difficulty_r18.s` 是当前回归测试需要的旧故障源级对照，不是旧版安装包。

现有宿主回归与 IPA 完整性检查已通过；UIKit/Foundation 等系统接口在宿主测试中使用替代模型，不能视为 iPad 实机游玩验证。公开的原始验证记录保持原样，本次导出检查单独记录。

许可证沿用本仓库 MIT，仅适用于本仓库代码；外部游戏及资源不在该许可证范围内。
