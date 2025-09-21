# 🚀 Bilibili工具安装和使用指南

## 快速安装

### 1. 检查Python环境
```bash
python --version  # 需要Python 3.7或更高版本
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 安装额外工具

#### 安装yt-dlp (必需)
```bash
pip install yt-dlp
```

#### 安装FFmpeg (用于音频转换)
- **Windows**: 从 https://ffmpeg.org 下载并添加到PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` 或 `sudo yum install ffmpeg`

## 准备Cookies

### 方法1: 浏览器复制 (推荐)
1. 登录 bilibili.com
2. 按F12打开开发者工具
3. 切换到"Network"标签
4. 刷新页面
5. 找到任意请求，复制Cookie值
6. 保存到 `cookies.txt` 文件

### 方法2: 使用浏览器扩展
1. 安装Cookie导出扩展
2. 导出bilibili.com的cookies
3. 保存为 `cookies.txt` (Netscape格式)

### 方法3: 手动格式
创建 `cookies.txt` 文件，内容格式：
```
# Netscape HTTP Cookie File
.bilibili.com	TRUE	/	FALSE	1735689600	SESSDATA	你的SESSDATA值
.bilibili.com	TRUE	/	FALSE	1735689600	bili_jct	你的bili_jct值
.bilibili.com	TRUE	/	FALSE	1735689600	DedeUserID	你的DedeUserID值
```

## 使用方法

## 使用方法

### 推荐使用Pro版 (最新优化版)
```bash
python bilibili_audio_downloader_pro.py
```

### 或使用v14.0 (功能完整版)
```bash
python 14.0bilibili_audio_dl.py
```

## 功能演示

### 下载单个视频音频
1. 启动程序
2. 选择"下载音频"
3. 输入BV号或完整URL
4. 等待下载完成
5. 选择是否转换为MP3

### 下载多P视频
1. 输入多P视频的URL
2. 程序会显示分P列表
3. 选择要下载的分P (支持范围选择)
4. 批量下载

### 示例URL格式
```
BV1234567890
https://www.bilibili.com/video/BV1234567890
https://www.bilibili.com/video/BV1234567890?p=2
https://b23.tv/BV1234567890
```

## 配置自定义

编辑 `config.json` 文件：

```json
{
    "download": {
        "folder": "音频",           // 下载文件夹
        "quality": "ba[ext=m4a]/ba", // 音频质量
        "auto_convert_mp3": true,    // 自动转换MP3
        "timeout": 30               // 超时时间
    },
    "ffmpeg": {
        "threads": 4,              // 转换线程数
        "quality_preset": "0"      // 质量预设(0最高)
    }
}
```

## 常见问题

### 1. Cookie失效
- 重新登录bilibili.com并更新cookies
- 检查SESSDATA、bili_jct、DedeUserID是否完整

### 2. 下载失败
- 检查网络连接
- 确保视频链接正确
- 查看日志文件 `bilibili_tool.log`

### 3. FFmpeg转换失败
- 确保FFmpeg已正确安装
- 检查音频文件是否存在且未损坏

### 4. 中文路径问题
- 程序已支持中文路径
- 如遇问题，尝试使用英文路径

## 高级技巧

### 批量下载
1. 创建 `bvid.txt` 文件
2. 每行写一个BV号
3. 使用批量下载功能

### 自定义输出格式
修改yt-dlp参数:
```python
'-o', '%(uploader)s - %(title)s.%(ext)s'  # 作者 - 标题.扩展名
```

### 使用代理
添加代理参数:
```python
'--proxy', 'http://127.0.0.1:8080'
```

## 性能优化

- 使用SSD存储提高转换速度
- 调整FFmpeg线程数匹配CPU核心数
- 在网络良好时增加并发下载数

## 安全提示

- 定期更新Cookie信息
- 不要在公共场所使用
- 遵守B站使用条款
- 仅用于个人学习研究

---

💡 **提示**: 如遇到问题，请查看 `bilibili_tool.log` 日志文件获取详细错误信息。
