[![License](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](https://www.gnu.org/licenses/gpl-3.0)

# 🎵 Bilibili-gadget

一个功能丰富的B站工具包，支持音频下载、用户管理、批量操作等功能。

## ✨ 主要功能

- **音频下载**: 支持下载B站视频音频并转换为MP3格式
- **多分P支持**: 支持多分P视频的批量下载
- **格式转换**: 自动转换音频格式，支持高质量MP3输出
- **进度显示**: 实时显示下载和转换进度
- **错误重试**: 智能重试机制，提高下载成功率
- **Cookie管理**: 支持多种Cookie格式导入

## 🚀 快速开始

### 环境要求

- Python 3.7+
- yt-dlp
- ffmpeg (用于音频格式转换)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 准备Cookies

1. 在浏览器中登录B站
2. 复制cookies并保存为 `cookies.txt` 文件
3. 支持多种格式：Netscape、JSON、直接复制等

### 使用方法

#### 推荐使用Pro版 (最新优化版)
```bash
python bilibili_audio_downloader_pro.py
```

#### 或使用v14.0 (功能完整版)
```bash
python 14.0bilibili_audio_dl.py
```

## 📁 文件结构

```
├── bilibili_audio_downloader_pro.py   # Pro版 (最新优化版)
├── 14.0bilibili_audio_dl.py           # 功能完整版本
├── 1.0bilibili_audio_dl.py            # 早期版本
├── config.json                        # 配置文件
├── requirements.txt                   # 依赖列表
├── cookies.txt                        # Cookies文件
├── INSTALL.md                         # 详细安装指南
├── VERSION_COMPARISON.md              # 版本对比说明
└── 音频/                              # 默认下载目录
```

> 💡 **版本选择疑惑？** 查看 [VERSION_COMPARISON.md](VERSION_COMPARISON.md) 了解详细对比

## 🔧 配置说明

编辑 `config.json` 文件可以自定义：

- 下载路径
- 音频质量
- 网络超时
- 重试次数
- 日志级别

## 📝 版本更新

### Pro版 (推荐)
- ✅ 重构代码架构，使用面向对象设计
- ✅ 改进错误处理和日志记录
- ✅ 修复ffmpeg进度条不准确问题
- ✅ 优化Cookie管理
- ✅ 添加配置文件支持
- ✅ 改进下载重试机制

### v14.0 (已修复)
- ✅ 修复中文编码问题
- ✅ 添加重试机制
- ✅ 改进进度条显示
- ✅ 增强错误处理

## ⚠️ 注意事项

1. 请确保Cookie信息有效且包含必要字段
2. 需要安装ffmpeg才能进行音频格式转换  
3. 遵守B站相关使用条款
4. 仅用于个人学习和研究用途

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

本项目基于 GPLv3 许可证开源。
