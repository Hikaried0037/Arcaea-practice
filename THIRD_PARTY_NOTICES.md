# 第三方组件

插件自身代码采用根目录 LICENSE 中的 MIT 许可。

## SoundTouch 2.4.1

Copyright © Olli Parviainen。按 LGPL-2.1-or-later 许可使用。

- 官方项目：https://codeberg.org/soundtouch/soundtouch
- 固定提交：0047e0b1ecfceb041348579119bf79b73a322a3a
- 完整许可：third_party/soundtouch/COPYING.TXT
- 本次使用的完整库源码及逐文件摘要：third_party/soundtouch/UPSTREAM.json

本项目包含未修改的 SoundTouch 库源文件，并提供调用代码及可重建/重链接插件的 build.py；不使用预编译黑盒音频库。静态链接不改变库自身的 LGPL 许可。可使用自己的签名重新构建、安装修改后的插件 APK。游戏文件与私有发布签名不包含在源码包内。

third_party 下原作者的公开联系信息属于组件署名。隐私扫描只对摘要匹配的原始文件允许此类署名；个人目录、凭据与本地秘密比较仍然检查。

## Signalsmith Stretch 1.3.2 / Signalsmith Linear

两者采用 MIT 许可，版权及完整许可分别见 `third_party/signalsmith-stretch/LICENSE.txt` 和 `third_party/signalsmith-linear/LICENSE.txt`。

- Stretch 官方项目：https://github.com/Signalsmith-Audio/signalsmith-stretch
- Stretch 固定提交：a670068d9aeb64913331d5cc29337b19a457a7df
- Linear 官方项目：https://github.com/Signalsmith-Audio/linear
- Linear 固定提交：146b26f91b48835d665fa0498d64d9617818d27a

原始头文件未修改，逐文件摘要见各目录 UPSTREAM.json。保持原调模式使用 Stretch 的频谱处理，Linear 提供 FFT/STFT。调用与慢速级联代码位于 native/audio_quality.h。
