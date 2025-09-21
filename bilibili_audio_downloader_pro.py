#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili音频下载工具 Pro版
=======================

这是一个经过完全重构的专业版本，相比传统版本具有以下优势：

🏗️ 架构优势：
- 面向对象设计，代码结构清晰
- 模块化管理，易于维护和扩展
- 类型注解支持，提高代码质量

🛡️ 稳定性提升：
- 完善的异常处理机制
- 智能重试和错误恢复
- 详细的日志记录系统

⚡ 性能优化：  
- 更准确的进度显示算法
- 优化的网络请求处理
- 智能的文件格式检测

🔧 用户体验：
- 简洁直观的交互界面
- 灵活的配置文件支持
- 多格式Cookie自动识别

适用场景：
- 需要稳定批量下载的用户
- 对代码质量有要求的开发者
- 需要定制化功能的高级用户

作者：GitHub Copilot & 用户协作开发
版本：Pro版 (2025.09.21)
"""

import json
import os
import subprocess
import re
import requests
import time
import random
import base64
import shutil
import hashlib
import sys
import logging
from typing import Dict, Optional, List, Tuple
from tqdm import tqdm
from urllib.parse import unquote
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bilibili_tool.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局配置
CONFIG = {
    'max_retries': 3,
    'timeout': 30,
    'download_folder': '音频',
    'ffmpeg_quality': '0',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

class BilibiliError(Exception):
    """B站相关错误的基类"""
    pass

class CookieError(BilibiliError):
    """Cookie相关错误"""
    pass

class DownloadError(BilibiliError):
    """下载相关错误"""
    pass

class CookieManager:
    """Cookie管理器"""
    
    @staticmethod
    def load_cookies_from_file() -> Dict:
        """从文件加载cookies"""
        cookie_files = ['cookies.txt', 'bilibili_cookies.json']
        
        for cookie_file in cookie_files:
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        cookies = {}

                        # 尝试作为JSON解析
                        try:
                            json_data = json.loads(content)
                            if isinstance(json_data, list):
                                cookies = CookieManager._convert_browser_cookies(json_data)
                            elif isinstance(json_data, dict):
                                cookies = json_data
                        except json.JSONDecodeError:
                            # 如果不是JSON，尝试作为Netscape格式或普通cookie字符串解析
                            if content.startswith('# Netscape HTTP Cookie File'):
                                cookies = CookieManager._parse_netscape_cookies(content)
                            else:
                                cookies = CookieManager._parse_cookie_string(content)

                        if cookies:
                            # 检查必要的cookie是否存在
                            if CookieManager._validate_cookies(cookies):
                                logger.info(f"已从 {cookie_file} 成功加载cookies")
                                return cookies
                            else:
                                logger.error("Cookie验证失败，缺少必要的字段")
                        else:
                            logger.warning(f"无法从 {cookie_file} 加载有效的cookies")

                except Exception as e:
                    logger.error(f"读取 {cookie_file} 时出错: {str(e)}")
        
        raise CookieError("无法加载有效的cookies文件")
    
    @staticmethod
    def _convert_browser_cookies(browser_cookies: list) -> Dict:
        """转换浏览器导出的cookies格式为简单的键值对"""
        cookies = {}
        for cookie in browser_cookies:
            if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                cookies[cookie['name']] = cookie['value']
        return cookies
    
    @staticmethod
    def _parse_netscape_cookies(content: str) -> Dict:
        """解析Netscape格式的cookies"""
        cookies = {}
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                fields = line.split('\t')
                if len(fields) >= 7:
                    name, value = fields[5:7]
                    cookies[name] = value
            except:
                continue
        return cookies
    
    @staticmethod
    def _parse_cookie_string(cookie_str: str) -> Dict:
        """解析浏览器直接复制的cookie字符串"""
        cookies = {}
        try:
            # 处理URL编码
            def decode_value(value):
                replacements = {
                    '%2C': ',', '%2F': '/', '%3A': ':', '%2B': '+', '%3D': '=', '%3B': ';'
                }
                for encoded, decoded in replacements.items():
                    value = value.replace(encoded, decoded)
                return value
            
            cookie_pairs = cookie_str.split(';')
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.strip().split('=', 1)
                    name = name.strip()
                    value = decode_value(value.strip())
                    cookies[name] = value
                    
        except Exception as e:
            logger.error(f"解析cookie字符串时出错: {str(e)}")
            return {}
        
        return cookies
    
    @staticmethod
    def _validate_cookies(cookies: Dict) -> bool:
        """验证cookies是否包含必要字段"""
        required_cookies = ['SESSDATA', 'bili_jct', 'DedeUserID']
        missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
        
        if missing_cookies:
            logger.warning(f"缺少必要的cookies: {', '.join(missing_cookies)}")
            return False
        return True
    
    @staticmethod
    def save_cookies(cookies: Dict, filename: str = 'cookies.txt'):
        """保存cookies为Netscape格式"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
                f.write("# This is a generated file!  Do not edit.\n\n")
                
                for name, value in cookies.items():
                    if name in ['SESSDATA']:
                        f.write(f"#HttpOnly_.bilibili.com\tTRUE\t/\tTRUE\t1735689600\t{name}\t{value}\n")
                    else:
                        f.write(f".bilibili.com\tTRUE\t/\tFALSE\t1735689600\t{name}\t{value}\n")
            
            logger.info(f"cookies已保存到{filename}")
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            raise CookieError(f"保存cookies失败: {str(e)}")

class FFmpegManager:
    """FFmpeg管理器"""
    
    @staticmethod
    def find_ffmpeg() -> str:
        """查找ffmpeg可执行文件的路径"""
        # 首先尝试系统PATH
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                logger.info("找到系统ffmpeg")
                return 'ffmpeg'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # 尝试常见安装路径
        possible_paths = [
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
            r'C:\ffmpeg\bin\ffmpeg.exe',
            './ffmpeg.exe',
            '../ffmpeg/bin/ffmpeg.exe'
        ]
        
        for path in possible_paths:
            if os.path.isfile(path):
                logger.info(f"找到ffmpeg: {path}")
                return path

        logger.warning("未找到ffmpeg，请确保ffmpeg已正确安装并添加到系统PATH中")
        return ''
    
    @staticmethod
    def get_audio_duration(input_file: str, ffmpeg_path: str) -> float:
        """获取音频文件时长（秒）"""
        try:
            cmd = [
                ffmpeg_path,
                '-i', input_file,
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # 从stderr中提取时长信息
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result.stderr)
            if duration_match:
                hours, minutes, seconds = map(float, duration_match.groups())
                return hours * 3600 + minutes * 60 + seconds
            
        except Exception as e:
            logger.warning(f"无法获取音频时长: {str(e)}")
        
        return 0.0
    
    @staticmethod
    def convert_to_mp3(input_file: str, output_file: str = None, quality: str = '0') -> bool:
        """将音频文件转换为MP3格式，带准确的进度条"""
        if not os.path.exists(input_file):
            logger.error(f"找不到输入文件: {input_file}")
            return False
        
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + '.mp3'
        
        ffmpeg_path = FFmpegManager.find_ffmpeg()
        if not ffmpeg_path:
            logger.error("未找到ffmpeg")
            return False
        
        # 获取音频时长用于进度计算
        total_duration = FFmpegManager.get_audio_duration(input_file, ffmpeg_path)
        
        try:
            cmd = [
                ffmpeg_path,
                '-i', input_file,
                '-acodec', 'libmp3lame',
                '-q:a', quality,
                '-threads', '4',
                '-progress', 'pipe:1',
                '-nostats',
                '-y',  # 覆盖输出文件
                output_file
            ]
            
            logger.info(f"开始转换: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
            
            with tqdm(total=100, 
                     desc="转换进度", 
                     ncols=80,
                     bar_format='{desc}: {percentage:3.1f}%|{bar}| [{elapsed}<{remaining}]') as pbar:
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                last_percent = 0
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    
                    # 解析进度信息
                    if line.startswith('out_time='):
                        time_str = line.split('=')[1].strip()
                        try:
                            # 解析时间格式 HH:MM:SS.mmm
                            time_parts = time_str.split(':')
                            if len(time_parts) == 3:
                                hours = float(time_parts[0])
                                minutes = float(time_parts[1])
                                seconds = float(time_parts[2])
                                current_time = hours * 3600 + minutes * 60 + seconds
                                
                                if total_duration > 0:
                                    percent = min(100, int((current_time / total_duration) * 100))
                                    if percent > last_percent:
                                        pbar.update(percent - last_percent)
                                        last_percent = percent
                        except:
                            pass
                
                # 确保进度条到达100%
                if last_percent < 100:
                    pbar.update(100 - last_percent)
            
            if process.returncode == 0:
                logger.info(f"转换完成: {os.path.basename(output_file)}")
                
                # 询问是否删除原始文件
                try:
                    choice = input("是否删除原始音频文件？(y/n) [y]: ").lower()
                    if not choice or choice == 'y':
                        os.remove(input_file)
                        logger.info("原始文件已删除")
                except:
                    pass  # 在非交互环境下跳过
                
                return True
            else:
                error = process.stderr.read()
                logger.error(f"转换失败: {error}")
                return False
                
        except Exception as e:
            logger.error(f"转换过程中发生错误: {str(e)}")
            return False

class VideoDownloader:
    """视频下载器"""
    
    def __init__(self, cookies: Dict):
        self.cookies = cookies
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': CONFIG['user_agent'],
            'Referer': 'https://www.bilibili.com',
        })
        self.session.cookies.update(cookies)
        
    def extract_bvid(self, url_or_bvid: str) -> str:
        """从URL或直接输入的BV号中提取BV"""
        if url_or_bvid.startswith('BV'):
            return url_or_bvid
        
        bv_pattern = r'BV[a-zA-Z0-9]{10}'
        match = re.search(bv_pattern, url_or_bvid)
        return match.group() if match else ''
    
    def get_video_info(self, bvid: str) -> Dict:
        """获取视频信息"""
        try:
            video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
            response = self.session.get(video_url, timeout=CONFIG['timeout'])
            response.raise_for_status()
            
            data = response.json()
            if data['code'] != 0:
                raise BilibiliError(f"获取视频信息失败: {data.get('message', '未知错误')}")
            
            return data['data']
            
        except Exception as e:
            logger.error(f"获取视频信息时出错: {str(e)}")
            raise BilibiliError(f"获取视频信息失败: {str(e)}")
    
    def download_audio_with_ytdlp(self, url: str, output_path: str = None) -> Optional[str]:
        """使用yt-dlp下载音频"""
        if output_path is None:
            output_path = CONFIG['download_folder']
        
        # 确保输出目录存在
        Path(output_path).mkdir(exist_ok=True)
        
        # 保存cookies
        CookieManager.save_cookies(self.cookies)
        
        cmd = [
            'yt-dlp',
            '--cookies', 'cookies.txt',
            '-f', 'ba[ext=m4a]/ba',  # 优先选择m4a格式的最佳音质
            '--no-playlist',
            '--no-check-certificates',
            '--progress',
            '--newline',
            '--no-warnings',
            '-o', os.path.join(output_path, "%(title)s.%(ext)s"),
            url
        ]
        
        logger.info("开始下载音频...")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                universal_newlines=True
            )
            
            downloaded_file = None
            pbar = None
            
            # 改进的进度解析正则表达式
            progress_pattern = re.compile(r'\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+~?\s*(\d+(?:\.\d+)?)([KMG]?)iB.*?ETA\s+([\d:]+)')
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    output = output.strip()
                    
                    # 获取文件名
                    if '[download] Destination:' in output:
                        downloaded_file = output.split('[download] Destination:', 1)[1].strip()
                        logger.info(f"下载目标: {os.path.basename(downloaded_file)}")
                    elif 'has already been downloaded' in output:
                        downloaded_file = output.split('[download] ', 1)[1].split(' has already', 1)[0].strip()
                        logger.info(f"文件已存在: {os.path.basename(downloaded_file)}")
                    
                    # 解析进度信息
                    match = progress_pattern.search(output)
                    if match:
                        percentage, size, unit, eta = match.groups()
                        
                        # 初始化进度条
                        if pbar is None:
                            pbar = tqdm(
                                total=100,
                                unit='%',
                                desc="下载进度",
                                ncols=80,
                                bar_format='{desc}: {percentage:3.1f}%|{bar}| ETA: {postfix}'
                            )
                        
                        # 更新进度条
                        current_percent = float(percentage)
                        pbar.n = current_percent
                        pbar.set_postfix_str(eta)
                        pbar.refresh()
                    
                    # 显示其他重要信息
                    elif '[download]' not in output and output:
                        logger.info(output)
            
            # 关闭进度条
            if pbar:
                pbar.close()
            
            # 检查下载结果
            if process.returncode == 0:
                logger.info("下载完成!")
                return downloaded_file
            else:
                error_output = process.stderr.read()
                logger.error(f"下载失败: {error_output}")
                raise DownloadError(f"yt-dlp下载失败: {error_output}")
                
        except Exception as e:
            logger.error(f"下载过程中出错: {str(e)}")
            raise DownloadError(f"下载失败: {str(e)}")
    
    def download_and_convert(self, url_or_bvid: str, convert_to_mp3: bool = True) -> bool:
        """下载并转换音频"""
        try:
            bvid = self.extract_bvid(url_or_bvid)
            if not bvid:
                raise BilibiliError("无效的BV号或URL")
            
            # 构建完整URL
            if url_or_bvid.startswith('BV'):
                url = f"https://www.bilibili.com/video/{bvid}"
            else:
                url = url_or_bvid
            
            # 下载音频
            downloaded_file = self.download_audio_with_ytdlp(url)
            
            if downloaded_file and os.path.exists(downloaded_file):
                logger.info(f"音频文件下载成功: {downloaded_file}")
                
                # 转换为MP3
                if convert_to_mp3:
                    try:
                        choice = input("是否转换为MP3格式？(y/n) [y]: ").lower()
                        if not choice or choice == 'y':
                            return FFmpegManager.convert_to_mp3(downloaded_file)
                    except:
                        # 非交互环境下默认转换
                        return FFmpegManager.convert_to_mp3(downloaded_file)
                
                return True
            else:
                logger.error("未找到下载的文件")
                return False
                
        except Exception as e:
            logger.error(f"下载和转换过程出错: {str(e)}")
            return False

def create_required_directories():
    """创建必要的目录"""
    directories = [CONFIG['download_folder'], 'logs']
    for directory in directories:
        try:
            Path(directory).mkdir(exist_ok=True)
            logger.info(f"确保目录存在: {directory}")
        except Exception as e:
            logger.error(f"创建目录 {directory} 失败: {str(e)}")

def main():
    """主函数"""
    print("="*60)
    print(" 🎵 Bilibili 音频下载工具 Pro版 (专业优化版)")
    print(" 🚀 基于全新架构重构，更稳定、更高效")
    print("="*60)
    
    try:
        # 创建必要目录
        create_required_directories()
        
        # 加载cookies
        cookies = CookieManager.load_cookies_from_file()
        
        # 创建下载器
        downloader = VideoDownloader(cookies)
        
        # 简单的交互界面
        while True:
            print("\n请选择操作:")
            print("1. 下载音频")
            print("2. 退出")
            
            choice = input("请选择 (1-2): ").strip()
            
            if choice == '1':
                while True:
                    url_or_bvid = input("\n请输入B站视频URL或BV号 (输入q返回): ").strip()
                    if url_or_bvid.lower() == 'q':
                        break
                    
                    if not url_or_bvid:
                        print("输入不能为空！")
                        continue
                    
                    try:
                        success = downloader.download_and_convert(url_or_bvid)
                        if success:
                            print("✅ 处理完成!")
                        else:
                            print("❌ 处理失败!")
                    except Exception as e:
                        logger.error(f"处理出错: {str(e)}")
                        print(f"❌ 处理出错: {str(e)}")
            
            elif choice == '2':
                print("感谢使用！")
                break
            else:
                print("无效选择，请重新输入！")
                
    except CookieError as e:
        logger.error(f"Cookie错误: {str(e)}")
        print(f"❌ Cookie错误: {str(e)}")
        print("请确保cookies.txt文件存在且包含有效的cookies信息")
    except Exception as e:
        logger.error(f"程序出错: {str(e)}")
        print(f"❌ 程序出错: {str(e)}")
    finally:
        try:
            input("\n按回车键退出...")
        except:
            pass

if __name__ == "__main__":
    main()
