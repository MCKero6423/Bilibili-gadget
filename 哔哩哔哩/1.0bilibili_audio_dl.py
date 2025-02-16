import json
import os
import subprocess
from typing import Dict
from tqdm import tqdm
import re

def convert_browser_cookies(browser_cookies: list) -> Dict:
    """转换浏览器导出的cookies格式为简单的键值对"""
    essential_cookies = {}
    required_keys = ['SESSDATA', 'bili_jct', 'DedeUserID']
    
    for cookie in browser_cookies:
        if cookie['name'] in required_keys:
            essential_cookies[cookie['name']] = cookie['value']
    
    return essential_cookies

def load_cookies_from_file() -> Dict:
    """从文件加载cookies"""
    cookie_files = ['cookies.txt', 'bilibili_cookies.json']
    required_keys = ['SESSDATA', 'bili_jct', 'DedeUserID']
    
    for cookie_file in cookie_files:
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = {}
                    # 逐行读取文件
                    for line in f:
                        line = line.strip()
                        # 跳过空行和注释行（但不跳过#HttpOnly_开头的行）
                        if not line or (line.startswith('#') and not line.startswith('#HttpOnly_')):
                            continue
                            
                        try:
                            # 处理HttpOnly标记
                            if line.startswith('#HttpOnly_'):
                                line = line[9:]  # 移除'#HttpOnly_'前缀
                            
                            # 分割字段并移除可能的空字段
                            fields = [f for f in line.split('\t') if f]
                            if len(fields) >= 7:
                                name = fields[5]
                                value = fields[6]
                                if name in required_keys:
                                    # 对于SESSDATA，需要处理URL编码
                                    if name == 'SESSDATA' and '%2C' in value:
                                        value = value.replace('%2C', ',')
                                    cookies[name] = value
                                    print(f"找到cookie: {name}")  # 调试信息
                        except Exception as e:
                            print(f"警告: 解析行 '{line}' 时出错: {str(e)}")
                            continue
                    
                    # 检查是否找到所有必需的cookies
                    if all(key in cookies for key in required_keys):
                        print(f"已从 {cookie_file} 加载cookies")
                        return cookies
                    else:
                        missing = [key for key in required_keys if key not in cookies]
                        print(f"警告: {cookie_file} 中缺少以下cookie字段: {', '.join(missing)}")
            except Exception as e:
                print(f"警告: 读取 {cookie_file} 时出错: {str(e)}")
    return {}

def parse_cookie_string(cookie_str: str) -> Dict:
    """解析浏览器直接复制的cookie字符串"""
    cookies = {}
    required_keys = ['SESSDATA', 'bili_jct', 'DedeUserID']
    
    try:
        # 分割cookie字符串
        cookie_pairs = cookie_str.split(';')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.strip().split('=', 1)
                if name in required_keys:
                    cookies[name] = value
    except Exception:
        return {}
    
    return cookies

def get_cookies_from_user() -> Dict:
    """获取用户输入的cookies"""
    print("请输入B站cookies (支持JSON格式、浏览器导出格式或直接复制的cookie字符串):")
    cookies_str = input().strip()
    
    # 首先尝试解析为JSON
    try:
        cookies_data = json.loads(cookies_str)
        if isinstance(cookies_data, list):
            cookies = convert_browser_cookies(cookies_data)
        else:
            cookies = cookies_data
    except json.JSONDecodeError:
        # 如果不是JSON，尝试解析为cookie字符串
        cookies = parse_cookie_string(cookies_str)
    
    # 验证必要的cookie字段
    if all(key in cookies for key in ['SESSDATA', 'bili_jct', 'DedeUserID']):
        return cookies
    else:
        print("Cookie缺少必要字段！需要SESSDATA、bili_jct和DedeUserID")
        return {}

def save_cookies(cookies: Dict):
    """保存cookies为Netscape格式"""
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        # 写入Netscape cookies文件头
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
        f.write("# This is a generated file!  Do not edit.\n\n")
        
        # 为每个cookie写入Netscape格式的行
        for name, value in cookies.items():
            # 特殊处理SESSDATA，添加HttpOnly和Secure标记
            if name == 'SESSDATA':
                f.write(f"#HttpOnly_.bilibili.com\tTRUE\t/\tTRUE\t1735689600\t{name}\t{value}\n")
            else:
                f.write(f".bilibili.com\tTRUE\t/\tFALSE\t1735689600\t{name}\t{value}\n")
    
    print(f"cookies已保存到cookies.txt，包含以下字段：{', '.join(cookies.keys())}")

def find_ffmpeg() -> str:
    """查找ffmpeg可执行文件的路径"""
    try:
        # 直接检查系统是否能执行ffmpeg命令
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            print("找到系统ffmpeg")
            return 'ffmpeg'  # 直接返回命令名称
    except Exception:
        pass

    # 如果直接执行失败，尝试完整路径
    ffmpeg_path = r'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
    if os.path.isfile(ffmpeg_path):
        print(f"找到ffmpeg: {ffmpeg_path}")
        return ffmpeg_path

    print("警告：未找到ffmpeg，请确保ffmpeg已正确安装并添加到系统PATH中")
    return ''

def convert_to_mp3(input_file: str) -> bool:
    """将音频文件转换为MP3格式"""
    if not os.path.exists(input_file):
        print(f"错误：找不到文件 {input_file}")
        return False
    
    output_file = os.path.splitext(input_file)[0] + '.mp3'
    
    try:
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-acodec', 'libmp3lame',
            '-q:a', '0',  # 最高质量
            '-threads', '4',  # 使用4个线程
            '-progress', 'pipe:1',  # 输出进度信息到stdout
            '-nostats',  # 不输出额外统计信息
            output_file
        ]
        
        print(f"正在转换为MP3: {os.path.basename(input_file)}")
        
        # 创建进度条
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
            
            # 读取并更新进度
            last_percent = 0
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                # 从输出中提取时间信息
                if line.startswith('out_time_ms='):
                    time_ms = int(line.split('=')[1])
                    # 假设每秒处理速度相同，使用已处理时间估算进度
                    percent = min(100, max(0, int(time_ms / 10000000)))  # 假设平均时长100秒
                    
                    # 更新进度条
                    if percent > last_percent:
                        pbar.update(percent - last_percent)
                        last_percent = percent
            
            # 确保进度条到达100%
            if last_percent < 100:
                pbar.update(100 - last_percent)
        
        # 检查转换结果
        if process.returncode == 0:
            print(f"\n转换完成：{os.path.basename(output_file)}")
            # 询问是否删除原始文件
            if input("是否删除原始音频文件？(y/n): ").lower() == 'y':
                os.remove(input_file)
                print("原始文件已删除")
            return True
        else:
            error = process.stderr.read()
            print(f"转换失败！错误信息：\n{error}")
            return False
            
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}")
        return False

def download_audio(url: str, cookies: Dict):
    """下载音频"""
    save_cookies(cookies)
    
    try:
        cmd = [
            'yt-dlp',
            '--cookies', 'cookies.txt',
            '-f', 'ba',
            '--no-playlist',
            '--no-check-certificates',
            '--progress',
            '--newline',
        ]
        
        cmd.append(url)
        
        print("开始下载音频...")
        
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
        total_size = None
        
        # 用于解析下载进度的正则表达式
        progress_pattern = re.compile(r'\[download\]\s+(\d+\.\d+)%\s+of\s+(\d+\.\d+)([KMG])iB\s+at\s+.*?ETA\s+(.*)')
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output:
                output = output.strip()
                
                # 获取文件名
                if '[download] Destination:' in output:
                    downloaded_file = output.split('[download] Destination:', 1)[1].strip()
                elif 'has already been downloaded' in output:
                    downloaded_file = output.split('[download] ', 1)[1].split(' has already', 1)[0].strip()
                
                # 解析进度信息
                match = progress_pattern.search(output)
                if match:
                    percentage, size, unit, eta = match.groups()
                    
                    # 计算总大小（转换为字节）
                    if total_size is None:
                        multiplier = {'K': 1024, 'M': 1024**2, 'G': 1024**3}
                        total_size = int(float(size) * multiplier[unit])
                        # 创建进度条
                        pbar = tqdm(
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            desc="下载进度",
                            ncols=80,
                            bar_format='{desc}: {percentage:3.1f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                        )
                    
                    # 更新进度条
                    if pbar:
                        current = int(total_size * float(percentage) / 100)
                        pbar.n = current
                        pbar.refresh()
                
                # 其他输出信息
                elif not output.startswith('[download]'):
                    print(output)
        
        # 关闭进度条
        if pbar:
            pbar.close()
        
        # 检查下载结果
        if process.returncode == 0:
            print("\n下载完成！")
            
            if downloaded_file and os.path.exists(downloaded_file):
                print(f"找到音频文件: {downloaded_file}")
                if input("是否转换为MP3格式？(y/n): ").lower() == 'y':
                    if find_ffmpeg():
                        convert_to_mp3(downloaded_file)
                    else:
                        print("未找到ffmpeg，无法转换为MP3格式")
            else:
                print(f"警告：无法找到下载的文件")
                m4a_files = [f for f in os.listdir('.') if f.endswith('.m4a')]
                if m4a_files:
                    print(f"在当前目录找到以下.m4a文件：")
                    for i, file in enumerate(m4a_files, 1):
                        print(f"{i}. {file}")
                    choice = input("请选择要转换的文件编号（输入q取消）：")
                    if choice.isdigit() and 1 <= int(choice) <= len(m4a_files):
                        if find_ffmpeg():
                            convert_to_mp3(m4a_files[int(choice)-1])
                        else:
                            print("未找到ffmpeg，无法转换为MP3格式")
        else:
            error = process.stderr.read()
            print(f"下载失败！错误信息：\n{error}")
            
    except FileNotFoundError:
        print("错误：请先安装 yt-dlp")
        print("可以使用以下命令安装：")
        print("pip install yt-dlp")
    except Exception as e:
        print(f"发生错误: {str(e)}")

def main():
    # 先尝试从文件加载cookies
    cookies = load_cookies_from_file()
    
    # 如果没有找到有效的cookies文件，则请求用户输入
    if not cookies:
        cookies = get_cookies_from_user()
        if not cookies:
            return
        # 保存用户输入的cookies
        save_cookies(cookies)
    
    while True:
        print("\n请输入B站视频URL (输入q退出):")
        url = input().strip()
        
        if url.lower() == 'q':
            break
            
        if not url.startswith(('https://www.bilibili.com', 'https://b23.tv')):
            print("请输入有效的B站视频链接！")
            continue
            
        download_audio(url, cookies)

if __name__ == "__main__":
    main() 