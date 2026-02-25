使用说明 (Usage)
主要是转化桌面版v2rayN生成的节点生成可以让Hiddify识别的二维码，默认TUIC的二维码Hiddify无法识别。v2rayN7.16.9,Hiddify1.22安卓版测试正常。适合自己建立节点自己用。
中文说明
使用步骤
下载二进制文件自己用，或者下载py代码自己安装依赖自己用
依赖说明

qrcode — 用于生成二维码

pillow — 图像处理支持

pyperclip — 读取系统剪切板内容


打开 v2rayN

在节点上 右键 → 导出分享链接 → 复制到剪切板（ctrl+C）

打开本工具（运行 Python 脚本或可执行文件）

工具会自动读取剪切板内容并完成转换

自动生成可供 Hiddify 使用的二维码

整个过程：

✅ 完全本地运行

✅ 不依赖任何网络请求

✅ 不上传任何数据

✅ 不保存用户配置

工作原理

本工具会：

读取剪切板中的 V2Ray 分享链接（TUIC/vmess / vless / trojan）主要是TUIC,必须转换才能识别

解析并重构为 Hiddify 兼容格式

本地生成二维码图像

所有操作均在本地执行，不涉及外部服务器。

English Instructions
How to Use

Open v2rayN

Right-click a node → Export Share Link → Copy to Clipboard

Launch this tool

The program automatically reads the clipboard

A Hiddify-compatible QR code will be generated locally

Security Notice

✅ Fully offline operation

✅ No internet connection required

✅ No data upload

✅ No configuration storage

All parsing and QR code generation are performed locally.
