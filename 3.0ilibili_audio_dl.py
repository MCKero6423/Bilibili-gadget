import json
import os
import subprocess
from typing import Dict
from tqdm import tqdm
import re
import requests
import time

def convert_browser_cookies(browser_cookies: list) -> Dict:
    """转换浏览器导出的cookies格式为简单的键值对"""
    cookies = {}
    
    for cookie in browser_cookies:
        if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
            cookies[cookie['name']] = cookie['value']
    
    return cookies

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
                            cookies = convert_browser_cookies(json_data)
                        elif isinstance(json_data, dict):
                            cookies = json_data
                    except json.JSONDecodeError:
                        # 如果不是JSON，尝试作为Netscape格式或普通cookie字符串解析
                        if content.startswith('# Netscape HTTP Cookie File'):
                            # Netscape格式
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
                        else:
                            # 尝试作为普通cookie字符串解析
                            cookies = parse_cookie_string(content)

                    if cookies:
                        print(f"已从 {cookie_file} 加载cookies:")
                        for name, value in cookies.items():
                            print(f"找到cookie: {name}")
                        return cookies
                    else:
                        print(f"警告: 无法从 {cookie_file} 加载有效的cookies")

            except Exception as e:
                print(f"警告: 读取 {cookie_file} 时出错: {str(e)}")
    return {}

def parse_cookie_string(cookie_str: str) -> Dict:
    """解析浏览器直接复制的cookie字符串"""
    cookies = {}
    
    try:
        # 处理URL编码
        def decode_value(value):
            # 处理特殊的URL编码字符
            replacements = {
                '%2C': ',',
                '%2F': '/',
                '%3A': ':',
                '%2B': '+',
                '%3D': '=',
                '%3B': ';'
            }
            for encoded, decoded in replacements.items():
                value = value.replace(encoded, decoded)
            return value
        
        # 分割cookie字符串
        cookie_pairs = cookie_str.split(';')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.strip().split('=', 1)
                name = name.strip()
                value = decode_value(value.strip())
                cookies[name] = value
                
        # 如果cookies非空，打印找到的cookie数量
        if cookies:
            print(f"字符串中解析出 {len(cookies)} 个cookies")
            
    except Exception as e:
        print(f"解析cookie字符串时出错: {str(e)}")
        return {}
    
    return cookies

def get_cookies_from_user() -> Dict:
    """获取用户输入的cookies"""
    print("请输入B站cookies (支持JSON格式、浏览器导出格式或直接复制的cookie字符串):")
    cookies_str = input().strip()
    
    # 首先尝试解析JSON
    try:
        cookies_data = json.loads(cookies_str)
        if isinstance(cookies_data, list):
            cookies = convert_browser_cookies(cookies_data)
        else:
            cookies = cookies_data
    except json.JSONDecodeError:
        # 如果不是JSON，尝试解析为cookie字符串
        cookies = parse_cookie_string(cookies_str)
    
    # 检查是否获取到cookies
    if cookies:
        print("成功获取到以下cookies:")
        for name in cookies.keys():
            print(f"- {name}")
        return cookies
    else:
        print("未能获取到有效的cookies")
        return {}

def save_cookies(cookies: Dict):
    """保存cookies为Netscape格式"""
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
        f.write("# This is a generated file!  Do not edit.\n\n")
        
        # 为所有cookie写入Netscape格式的行
        for name, value in cookies.items():
            # 某些特殊cookie需要特殊处理
            if name in ['SESSDATA']:
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
            
            # 读取并更新进
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
            choice = input("是否删除原始音频文件？(y/n) [y]: ").lower()
            if not choice or choice == 'y':  # 直接回车或输入y都删除
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

def get_user_info(cookies: Dict) -> None:
    """获取并显示用户信息"""
    print("\n" + "="*50)
    print("# 用户信息")
    print("="*50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 获取用户基本信息
        myinfo_url = 'http://api.bilibili.com/x/space/myinfo'
        myinfo_resp = requests.get(myinfo_url, cookies=cookies, headers=headers)
        myinfo_data = myinfo_resp.json()
        
        user_id = None
        if myinfo_data['code'] == 0:
            user_data = myinfo_data['data']
            user_id = user_data['mid']  # 获取用户ID
            print(f"用户名: {user_data['name']}")
            print(f"用户ID: {user_id}")
            print(f"等级: LV{user_data['level']}")
            print(f"会员类型: {'大会员' if user_data['vip']['status'] == 1 else '普通用户'}")
            print(f"性别: {user_data['sex']}")
            print(f"签名: {user_data['sign']}")
            
            # 获取关注和粉丝数
            if user_id:
                stat_url = f'https://api.bilibili.com/x/relation/stat?vmid={user_id}'
                stat_resp = requests.get(stat_url, headers=headers)
                stat_data = stat_resp.json()
                
                if stat_data['code'] == 0:
                    stat_info = stat_data['data']
                    print(f"关注数: {stat_info['following']}")
                    print(f"粉丝数: {stat_info['follower']}")
        
        # 获取硬币数
        coin_url = 'http://account.bilibili.com/site/getCoin'
        coin_resp = requests.get(coin_url, cookies=cookies, headers=headers)
        coin_data = coin_resp.json()
        
        if coin_data['code'] == 0:
            print(f"硬币数: {coin_data['data']['money']}")
        
        # 获取今日投币经验
        coin_exp_url = 'https://api.bilibili.com/x/web-interface/coin/today/exp'
        coin_exp_resp = requests.get(coin_exp_url, cookies=cookies, headers=headers)
        coin_exp_data = coin_exp_resp.json()
        
        if coin_exp_data['code'] == 0:
            today_exp = coin_exp_data['data']
            max_coin_exp = 50  # B站每日投币多获得50经验
            print(f"今日投币经验: {today_exp}/{max_coin_exp}")
            remaining_coins = (max_coin_exp - today_exp) // 10  # 每个硬币获得10经验
            if remaining_coins > 0:
                print(f"今日还可投币: {remaining_coins}个")
        
        # 获取登录信息
        nav_url = 'https://api.bilibili.com/x/web-interface/nav'
        nav_resp = requests.get(nav_url, cookies=cookies, headers=headers)
        nav_data = nav_resp.json()
        
        if nav_data['code'] == 0:
            nav_info = nav_data['data']
            print(f"当前登录状态: {'已登录' if nav_info['isLogin'] else '未登录'}")
            if nav_info['isLogin']:
                print(f"邮箱: {nav_info['email']}")
                print(f"硬币余额: {nav_info['money']}")
                print(f"B币余额: {nav_info['wallet']['bcoin_balance']}")
                
    except Exception as e:
        print(f"获取用户信息时出错: {str(e)}")
    
    print("="*50 + "\n")

def extract_bvid_from_file(filename: str) -> list:
    """从文件中取URL并提取BV号"""
    bvids = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url:
                    # 使用正则表达式匹配BV号
                    match = re.search(r'BV[a-zA-Z0-9]{10}', url)
                    if match:
                        bvid = match.group()
                        bvids.append(bvid)
    except Exception as e:
        print(f"读取文件出错: {str(e)}")
    return bvids

def batch_coin(cookies: Dict) -> None:
    """批量投币功能"""
    print("\n" + "="*50)
    print("# 批量投币")
    print("="*50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 先检查今日投币情况
        coin_exp_url = 'https://api.bilibili.com/x/web-interface/coin/today/exp'
        coin_exp_resp = requests.get(coin_exp_url, cookies=cookies, headers=headers)
        coin_exp_data = coin_exp_resp.json()
        
        if coin_exp_data['code'] == 0:
            today_exp = coin_exp_data['data']
            max_coin_exp = 50
            remaining_coins = (max_coin_exp - today_exp) // 10
            
            if remaining_coins <= 0:
                print("今日已完成投币任务！")
                return
                
            print(f"今日还可投币: {remaining_coins}个")
            
            # 检查bvid.txt文件是否存在
            if not os.path.exists('bvid.txt'):
                print("错误：找不到bvid.txt文件！")
                print("请创建bvid.txt文件并在其中每行写入一个视频链接")
                return
            
            # 从文件中读取并提取BV号
            bvids = extract_bvid_from_file('bvid.txt')
            
            if not bvids:
                print("错误：无法从文件中提取有效的BV号！")
                return
            
            print(f"从文件中提取到 {len(bvids)} 个BV号:")
            for bvid in bvids:
                print(f"- {bvid}")
            
            # 询问是否继续投币
            choice = input("\n是否开始批量投币？(y/n) [y]: ").lower()
            if not choice or choice == 'y':  # 直接回车或输入y都继续
                # 获取csrf令牌
                csrf = cookies.get('bili_jct')
                if not csrf:
                    print("错误：无法获取csrf令牌！")
                    return
                
                # 投币API
                coin_url = 'https://api.bilibili.com/x/web-interface/coin/add'
                
                # 创建进度条
                with tqdm(total=min(remaining_coins, len(bvids)), desc="投币进度") as pbar:
                    for bvid in bvids:
                        if remaining_coins <= 0:
                            print("\n今日投币任务已完成！")
                            break
                        
                        # 构造请求数据
                        data = {
                            'bvid': bvid,
                            'multiply': 1,  # 投1个币
                            'select_like': 1,  # 同时点赞
                            'csrf': csrf
                        }
                        
                        try:
                            # 发送投币请求
                            response = requests.post(coin_url, data=data, cookies=cookies, headers=headers)
                            result = response.json()
                            
                            if result['code'] == 0:
                                print(f"\n成功给视频 {bvid} 投币")
                                remaining_coins -= 1
                                pbar.update(1)
                            else:
                                print(f"\n给视频 {bvid} 投币失败：{result['message']}")
                                print("停止投币操作")
                                break  # 投币失败就停止
                            
                            # 添加延时，避免请求过快
                            time.sleep(2)
                            
                        except Exception as e:
                            print(f"\n投币过程出错: {str(e)}")
                            print("停止投币操作")
                            break  # 出错也停止
                
                print("\n批量投币完成！")
                
                # 获取当前硬币数
                nav_url = 'https://api.bilibili.com/x/web-interface/nav'
                nav_resp = requests.get(nav_url, cookies=cookies, headers=headers)
                nav_data = nav_resp.json()
                
                if nav_data['code'] == 0:
                    current_coins = nav_data['data']['money']
                    print(f"当前剩余硬币数: {current_coins}")
            
    except Exception as e:
        print(f"批量投币时出错: {str(e)}")
    
    print("="*50 + "\n")

def show_menu() -> str:
    """显示功能菜单"""
    print("\n" + "="*50)
    print("B站工具箱")
    print("="*50)
    print("1. 批量点赞 (默认)")
    print("2. 批量投币")
    print("3. 下载视频音频")
    print("4. 获取视频BV号")
    print("5. 查看用户信息")
    print("6. 退出程序")
    print("="*50)
    
    choice = input("请选择功能 (1-6) [1]: ").strip()
    if not choice:  # 如果直接回车，返回默认值'1'
        return '1'
    if choice in ['1', '2', '3', '4', '5', '6']:
        return choice
    print("无效的选择，使用默认选项1")
    return '1'

def extract_bvid(url: str) -> str:
    """从URL中提取BV号"""
    # 匹配BV号的正则表达式
    bv_pattern = r'BV[a-zA-Z0-9]{10}'
    match = re.search(bv_pattern, url)
    if match:
        return match.group()
    return ''

def get_video_bvids() -> None:
    """获取视频BV号并保存到文件"""
    bvids = []
    print("请输入B站视频URL，每行一个，输入q结束：")
    while True:
        url = input().strip()
        if url.lower() == 'q':
            break
            
        if not url.startswith(('https://www.bilibili.com', 'https://b23.tv')):
            print("请输入有效的B站视频链接！")
            continue
            
        bvid = extract_bvid(url)
        if bvid:
            bvids.append(bvid)
            print(f"已添加: {bvid}")
        else:
            print("无法从URL中提取BV号！")
    
    if bvids:
        with open('bvid.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(bvids))
        print(f"已保存 {len(bvids)} 个BV号到 bvid.txt")

def batch_like(cookies: Dict) -> None:
    """批量点赞功能"""
    print("\n" + "="*50)
    print("# 批量点赞")
    print("="*50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 检查bvid.txt文件是否存在
        if not os.path.exists('bvid.txt'):
            print("错误：找不到bvid.txt文件！")
            print("请创建bvid.txt文件并在其中每行写入一个视频链接")
            return
        
        # 从文件中读取并提取BV号
        bvids = extract_bvid_from_file('bvid.txt')
        
        if not bvids:
            print("错误：无法从文件中提取有效的BV号！")
            return
        
        print(f"从文件中提取到 {len(bvids)} 个BV号:")
        for bvid in bvids:
            print(f"- {bvid}")
        
        # 询问是否继续点赞
        choice = input("\n是否开始批量点赞？(y/n) [y]: ").lower()
        if not choice or choice == 'y':  # 直接回车或输入y都继续
            # 获取csrf令牌
            csrf = cookies.get('bili_jct')
            if not csrf:
                print("错误：无法获取csrf令牌！")
                return
            
            # 点赞API
            like_url = 'https://api.bilibili.com/x/web-interface/archive/like'
            
            # 创建进度条
            with tqdm(total=len(bvids), desc="点赞进度") as pbar:
                for bvid in bvids:
                    # 构造请求数据
                    data = {
                        'bvid': bvid,
                        'like': 1,  # 1表示点赞，2表示取消点赞
                        'csrf': csrf
                    }
                    
                    try:
                        # 发送点赞请求
                        response = requests.post(like_url, data=data, cookies=cookies, headers=headers)
                        result = response.json()
                        
                        if result['code'] == 0:
                            print(f"\n成功给视频 {bvid} 点赞")
                            pbar.update(1)
                        else:
                            print(f"\n给视频 {bvid} 点赞失败：{result['message']}")
                            print("停止点赞操作")
                            break  # 点赞失败就停止
                        
                        # 添加延时，避免请求过快
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"\n点赞过程出错: {str(e)}")
                        print("停止点赞操作")
                        break  # 出错也停止
            
            print("\n批量点赞完成！")
            
    except Exception as e:
        print(f"批量点赞时出错: {str(e)}")
    
    print("="*50 + "\n")

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
    
    # 获取并显示用户信息
    get_user_info(cookies)
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            # 批量点赞
            batch_like(cookies)
        
        elif choice == '2':
            # 批量投币
            batch_coin(cookies)
        
        elif choice == '3':
            # 下载视频音频
            while True:
                print("\n请输入B站视频URL (输入q返回主菜单):")
                url = input().strip()
                
                if url.lower() == 'q':
                    break
                    
                if not url.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                    print("请输入有效的B站视频链接！")
                    continue
                    
                download_audio(url, cookies)
        
        elif choice == '4':
            # 获取视频BV号
            get_video_bvids()
        
        elif choice == '5':
            # 查看用户信息
            get_user_info(cookies)
        
        elif choice == '6':
            print("\n感谢使用！再见！")
            break

if __name__ == "__main__":
    main() 