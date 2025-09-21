import json
import os
import subprocess
from typing import Dict
from tqdm import tqdm
import re
import requests
import time
import logging  # 添加日志模块
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='error.log'
)

def convert_browser_cookies(browser_cookies: list) -> Dict:
    """转换浏览器导出的cookies格式为简单的键值对"""
    cookies = {}
    
    for cookie in browser_cookies:
        if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
            cookies[cookie['name']] = cookie['value']
    
    return cookies

def load_cookies_from_file() -> Dict:
    """从文件加载cookies"""
    cookie_files = ['cookies.txt', 'bilibili_cookies.json']  # 直接从当前目录读取
    
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
                        # ���查必要的cookie是否存在
                        required_cookies = ['SESSDATA', 'bili_jct', 'DedeUserID']
                        missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
                        
                        if missing_cookies:
                            print(f"警告: 缺少必要的cookies: {', '.join(missing_cookies)}")
                            print("这些cookie是必需的，否则某些功能可能无法正常工作")
                            print("请确保你的cookies.txt中包含这些必要的cookie")
                            return {}
                            
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
            # 处理特殊的URL�����码字符
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
    with open('cookies.txt', 'w', encoding='utf-8') as f:  # 直接保存到当前目录
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

    print("警告：未找到ffmpeg，请确保ffmpeg已正确安装添加到系统PATH中")
    return ''

def convert_to_mp3(input_file: str) -> bool:
    """将音频文件转换为MP3格式"""
    if not os.path.exists(input_file):
        print(f"错误：找不到文件 {input_file}")
        return False
    
    output_file = os.path.splitext(input_file)[0] + '.mp3'
    
    try:
        # 构建ffmpeg�����令
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-acodec', 'libmp3lame',
            '-q:a', '0',  # 最高质量
            '-threads', '4',  # 使��������������4个线程
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
                    
                    # 更进度条
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

def download_audio(url_or_bvid: str, cookies: Dict):
    """下载音频"""
    save_cookies(cookies)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 获取视频BV号并显示信息
        bvid = extract_bvid(url_or_bvid)
        if bvid:
            pages = get_video_info(bvid, headers, show_info=False)  # 添加参数控制是否显示信息
            if len(pages) > 1:
                choice = input("\n是否显示分P列表？(y/n) [n]: ").lower()
                if choice == 'y':
                    print("\n分P列表:")
                    # 显示视频基本信息
                    get_video_info(bvid, headers, show_info=True)  # 此时显示完整信息
                    # 显示分P信息
                    for page in pages:
                        duration_min = page['duration'] // 60
                        duration_sec = page['duration'] % 60
                        print(f"{page['page']}. {page['part']} ({duration_min}分{duration_sec}秒)")
                
                print("\n请输入要下载的分P编号（用空格分隔，例如：1 3 5）")
                print("支持择（例如：1-5 7 9-11）")
                choice = input("请选择 [1]: ").strip()
                
                # 如果直接回车，默认下载第一P
                if not choice:
                    choice = "1"
                
                # 解析选择的分P
                selected_pages = set()
                for part in choice.split():
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        selected_pages.update(range(start, end + 1))
                    else:
                        selected_pages.add(int(part))
                
                # 过滤无效的分P编号
                valid_pages = sorted([p for p in selected_pages if 1 <= p <= len(pages)])
                
                if valid_pages:
                    print(f"\n将下载以下分P: {', '.join(map(str, valid_pages))}")
                    for page_num in valid_pages:
                        page = pages[page_num - 1]
                        page_url = f"https://www.bilibili.com/video/{bvid}?p={page_num}"
                        print(f"\n开始下载P{page_num}: {page['part']}")
                        download_single_audio(page_url, cookies)
                else:
                    print("未选择有效的分P编号，将下载P1")
                    download_single_audio(url_or_bvid, cookies)
            else:
                # 单P视频直接下载
                download_single_audio(url_or_bvid, cookies)
        else:
            print("请输入有效的B站频链接或BV号！")
    except Exception as e:
        print(f"下��过程出错: {str(e)}")

def get_user_info(cookies: Dict) -> None:
    """获取并示用户信息"""
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
            max_coin_exp = 50  # B站��日投币��获��50验
            print(f"今日投币经验: {today_exp}/{max_coin_exp}")
            remaining_coins = (max_coin_exp - today_exp) // 10  # 每个硬币��得10经验
            if remaining_coins > 0:
                print(f"还可投: {remaining_coins}个")
        
        # 获取登��信息
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
        print(f"获取用户信息出错: {str(e)}")
    
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
                print("错误：��不到bvid.txt文件！")
                print("请创建bvid.txt文件并在其中每行写入一个视频链接")
                return
            
            # 从文件中读取��取BV号
            bvids = extract_bvid_from_file('bvid.txt')
            
            if not bvids:
                print("错误：无法从文件中提取效的BV号！")
                return
            
            print(f"从文件中提取到 {len(bvids)} 个BV号:")
            # 获取每个视频的信息
            for bvid in bvids:
                get_video_info(bvid, headers)
            
            # 询问是否继续投币
            choice = input("\n是否开始批量投币？(y/n) [y]: ").lower()
            if not choice or choice == 'y':  # 直接回车或输入y都继续
                # 获取csrf令牌
                csrf = cookies.get('bili_jct')
                if not csrf:
                    print("错误：无法获取csrf令牌！")
                    return
                
                # 投API
                coin_url = 'https://api.bilibili.com/x/web-interface/coin/add'
                
                # 创建进度条
                with tqdm(total=min(remaining_coins, len(bvids)), desc="投币进度") as pbar:
                    for bvid in bvids:
                        if remaining_coins <= 0:
                            print("\n今日投币任务完成！")
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
    print("6. bv转av")
    print("7. 获取视频弹幕")
    print("8. 发送视频弹幕")
    print("9. 获取视频热评")
    print("10. 直播功能")
    print("11. 退出程序")
    print("="*50)
    
    choice = input("请选择功能 (1-11) [1]: ").strip()
    if not choice:
        return '1'
    if choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11']:
        return choice
    print("无效的选择，使用默认选项1")
    return '1'

def show_live_menu() -> str:
    """显示直播功能子菜单"""
    print("\n" + "="*50)
    print("直播功能")
    print("="*50)
    print("1. 获取直播间信息")
    print("2. 获取用户直播状态")
    print("3. 获取主播信息")
    print("4. 获取多个直播间信息")
    print("5. 批量查询直播状态")
    print("6. 获取直播间历史弹幕")
    print("7. 获取直播间播放信息")
    print("8. 获取直播间主播详情")
    print("9. 返回主菜单")
    print("="*50)
    
    choice = input("请选择功能 (1-9) [1]: ").strip()
    if not choice:
        return '1'
    if choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
        return choice
    print("无效的选择，使用默认选项1")
    return '1'

def extract_bvid(url_or_bvid: str) -> str:
    """从URL或直接输入的BV��中提取BV"""
    # 如果直接输入的是BV号
    if url_or_bvid.startswith('BV'):
        return url_or_bvid
    
    # 否则从URL中提取
    bv_pattern = r'BV[a-zA-Z0-9]{10}'
    match = re.search(bv_pattern, url_or_bvid)
    if match:
        return match.group()
    return ''

def get_video_bvids() -> None:
    """获取视频BV号并保存到文件"""
    bvids = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    print("请输入B站视频URL���BV号，每行一���，输入q��束：")
    while True:
        input_text = input().strip()
        if input_text.lower() == 'q':
            break
            
        # 如果输入的是BV号
        if input_text.startswith('BV'):
            bvid = input_text
            bvids.append(bvid)
            get_video_info(bvid, headers)
            continue
            
        # 如果输入的是URL
        if not input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
            print("请输入有效的B站视频链或BV号！")
            continue
            
        bvid = extract_bvid(input_text)
        if bvid:
            bvids.append(bvid)
            get_video_info(bvid, headers)
        else:
            print("无法从URL中提���BV号！")
    
    if bvids:
        with open('bvid.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(bvids))
        print(f"已保存 {len(bvids)} 个BV号到 bvid.txt")

def get_video_info(bvid: str, headers: dict, show_info: bool = True) -> list:
    """获取并显示视频信息"""
    try:
        video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        response = requests.get(video_url, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            info = data['data']
            if show_info:  # 只在需要时显示信息
                print(f"\n视频信息 - {bvid}:")
                print(f"标题: {info['title']}")
                print(f"UP主: {info['owner']['name']}")
                print(f"播放量: {info['stat']['view']}")
                print(f"点赞数: {info['stat']['like']}")
                print(f"投币数: {info['stat']['coin']}")
                print(f"收藏数: {info['stat']['favorite']}")
                print(f"分享数: {info['stat']['share']}")
                # 获取并显示评论数
                comment_count = get_comment_count(bvid)
                print(f"评论数: {comment_count}")
                print(f"发布时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info['pubdate']))}")
                print(f"视频简介: {info['desc'][:100]}..." if len(info['desc']) > 100 else f"视频简介: {info['desc']}")
                print("-" * 50)
            
            # 返回分P信息，供下载功能使用
            return info.get('pages', [])
    except Exception as e:
        print(f"获取视频 {bvid} 信息失败: {str(e)}")
    return []

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
        # 检查bvid.txt文件是��存在
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
        # 获取每个视频的信息
        for bvid in bvids:
            get_video_info(bvid, headers)
        
        # 询问是否继续点赞
        choice = input("\n是否开始批量点赞？(y/n) [y]: ").lower()
        if not choice or choice == 'y':
            # 获csrf令牌
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
                        'like': 1,  # 1表示点赞，2表示取消��赞
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
                            print(f"\n给频 {bvid} 点赞失败{result['message']}")
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

def download_single_audio(url: str, cookies: Dict):
    """下载单个音频"""
    try:
        cmd = [
            'yt-dlp',
            '--cookies', 'cookies.txt',  # 直接使用当前目���的cookies.txt
            '-f', 'ba',
            '--no-playlist',
            '--no-check-certificates',
            '--progress',
            '--newline',
            '-o', os.path.join("音频", "%(title)s.%(ext)s"),  # 指定下载路径
            url
        ]
        
        print("开���下载音频...")
        
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
        
        # 用于解析����载进度的正则表达式
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
        
        # 查下载结果
        if process.returncode == 0:
            print("\n下载完成！")
            
            if downloaded_file and os.path.exists(downloaded_file):
                print(f"找到音频文件: {downloaded_file}")
                if input("是否转换为MP3格式？(y/n) [y]: ").lower() in ['', 'y']:
                    if find_ffmpeg():
                        convert_to_mp3(downloaded_file)
                    else:
                        print("未找到ffmpeg，无法转换为MP3��式")
            else:
                print(f"警告：无法找到下载的文件")
                m4a_files = [f for f in os.listdir('.') if f.endswith('.m4a')]
                if m4a_files:
                    print(f"在当前目录找到以下.m4a文件：")
                    for i, file in enumerate(m4a_files, 1):
                        print(f"{i}. {file}")
                    choice = input("请选择要转换的文件编号（输入q取消）[1]: ")
                    if not choice:
                        choice = '1'
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
        print(f"发生误: {str(e)}")

def create_required_directories():
    """创建程序所需的文件夹"""
    required_dirs = [
        "弹幕",                    # 存放视频弹幕文件
        os.path.join("弹幕", "直播弹幕"),  # 存放直播弹幕文件
        "评论",                    # 存放评论文件
        "音频",                    # 存放下载的音频文件
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"创建文件夹: {directory}")
            except Exception as e:
                print(f"创建文件夹 {directory} 时出错: {str(e)}")

def main():
    """主程序入口"""
    try:
        # 创建必要的文件夹
        create_required_directories()
        
        # 加载cookies
        cookies = load_cookies_from_file()
        if not cookies:
            print("错误：无法从cookies.txt加载有效的cookies")
            return
        
        # 获取并显示用户信息
        get_user_info(cookies)
        
        # 创建LiveRoom实例
        live_room = LiveRoom()
        
        while True:
            try:
                choice = show_menu()
                
                if choice == '1':
                    batch_like(cookies)
                elif choice == '2':
                    batch_coin(cookies)
                elif choice == '3':
                    # 下载视频音频
                    while True:
                        print("\n请输入B站视频URL或BV号 (输入q返回主菜单):")
                        input_text = input().strip()
                        
                        if input_text.lower() == 'q':
                            break
                            
                        if input_text.startswith('BV'):
                            download_audio(input_text, cookies)
                            continue
                            
                        if not input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                            print("请输入有效的B站视频链接或BV号！")
                            continue
                            
                        download_audio(input_text, cookies)
                elif choice == '4':
                    get_video_bvids()
                elif choice == '5':
                    get_user_info(cookies)
                elif choice == '6':
                    bvid = input("请输入BV号: ").strip()
                    if bvid.startswith('BV'):
                        av_number = bv_to_av(bvid)
                        print(f"对应AV号是: {av_number}")
                    else:
                        print("请输入有效的BV号！")
                elif choice == '7':
                    # 获取视频弹幕
                    input_text = input("请输入视频URL或BV号: ").strip()
                    bvid = extract_bvid(input_text)
                    if bvid:
                        try:
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                'Referer': 'https://www.bilibili.com',
                            }
                            video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
                            response = requests.get(video_url, headers=headers)
                            data = response.json()
                            if data['code'] == 0:
                                cid = data['data']['cid']
                                segment = input("请输入要获取第几个6分钟段的弹幕 (1-n) [1]: ").strip()
                                if not segment:
                                    segment = "1"
                                if segment.isdigit():
                                    get_danmaku(cid, bvid, int(segment))
                                else:
                                    print("请输入有效的数字！")
                            else:
                                print(f"获取视频信息失败：{data['message']}")
                        except Exception as e:
                            print(f"获取弹幕时��错: {str(e)}")
                    else:
                        print("无法识别BV号！")
                elif choice == '8':
                    # 发送视频弹幕
                    bvid = input("请输入视频BV号: ").strip()
                    msg = input("请输入弹幕内容: ")
                    progress = int(input("请输入弹幕出现时间（毫秒）: "))
                    color = int(input("请输入弹幕颜色（十进制RGB888）: "))
                    fontsize = int(input("请输入弹幕字号（12-64）: "))
                    mode = int(input("请输入弹幕类型（1普通/4底部/5顶部/7高级/9BAS）: "))
                    cookies = get_cookies_from_user()
                    send_danmaku(bvid, msg, progress, color, fontsize, mode, cookies)
                elif choice == '9':
                    # 获取视频热评
                    input_text = input("请输入视频URL或BV号: ").strip()
                    bvid = extract_bvid(input_text)
                    if bvid:
                        ps = input("请输入每页显示的评论数 (1-49) [20]: ").strip()
                        if not ps:
                            ps = "20"
                        if ps.isdigit() and 1 <= int(ps) <= 49:
                            get_hot_comments(bvid, int(ps))
                        else:
                            print("请输入有效的数字！")
                    else:
                        print("无法识别BV号！")
                elif choice == '10':
                    # 直播功能
                    while True:
                        live_choice = show_live_menu()
                        if live_choice == '9':
                            break
                        # ... 其他直播功能的处理 ...
                elif choice == '11':
                    print("\n感谢使用！再见！")
                    break
                    
            except Exception as e:
                print(f"\n执行功能时出错: {str(e)}")
                logging.error(f"功能执行错误: {str(e)}", exc_info=True)
                input("\n按回车继续...")
                
    except Exception as e:
        print(f"主程序运行出错: {str(e)}")
        logging.error(f"主程序错误: {str(e)}", exc_info=True)

def bv_to_av(bvid: str) -> str:
    """将BV号转换为AV号"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 使用B站API获取视信息
        video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        response = requests.get(video_url, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            # 从返回数据中获取aid（AV号）
            av_number = data['data']['aid']
            return str(av_number)  # 直接返回数字部分
        else:
            print(f"获取AV号失败：{data['message']}")
            return ""
            
    except Exception as e:
        print(f"转换过程出错: {str(e)}")
        return ""

def get_color_name(hex_color: str) -> str:
    """将十六进制颜色代码转换为颜色名称"""
    # 常见B站弹幕颜色映射
    color_map = {
        '#ffffff': '白色',
        '#000000': '黑色',
        '#ff0000': '红色',
        '#00ff00': '绿色',
        '#0000ff': '蓝色',
        '#ffff00': '黄色',
        '#ff7600': '橙色',
        '#ff00ff': '粉色',
        '#00ffff': '青色',
        '#64c8ff': '浅蓝',
        '#ff8080': '浅红',
        '#66ccff': '天蓝',
        '#ff69b4': '粉红',
        '#ff69b4': '热粉红',
        '#98fb98': '浅绿',
        '#ffa500': '橙色',
        '#f0e68c': '卡其色',
        '#87ceeb': '天蓝色',
        '#dda0dd': '梅红色',
        '#ff7f50': '珊瑚色',
    }
    return color_map.get(hex_color.lower(), hex_color)

def get_danmaku(cid: str, bvid: str, segment_index: int = 1) -> None:
    """获取视频弹幕"""
    try:
        import google.protobuf.text_format as text_format
        from bilibili.community.service.dm.v1 import dm_pb2 as Danmaku
    except ImportError:
        print("错误：缺少必要的库，请先安装：")
        print("pip install protobuf")
        print("同需要编译proto文件生成dm_pb2.py")
        return

    url = 'https://api.bilibili.com/x/v2/dm/web/seg.so'
    params = {
        'type': 1,              # 弹幕类型
        'oid': cid,            # 视频cid
        'segment_index': segment_index  # 弹幕分段
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com'
    }

    try:
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            danmaku_seg = Danmaku.DmSegMobileReply()
            danmaku_seg.ParseFromString(resp.content)
            
            # 存储弹幕内容
            danmaku_list = []
            
            print(f"\n获取��� {len(danmaku_seg.elems)} 条弹幕:")
            print("-" * 50)
            
            for elem in danmaku_seg.elems:
                # 计算时间
                seconds = elem.progress / 1000
                minutes = int(seconds / 60)
                seconds = int(seconds % 60)
                
                # 获取弹幕类型
                mode_types = {
                    1: "普通弹幕",
                    2: "普通弹幕",
                    3: "普通弹幕",
                    4: "底部弹幕",
                    5: "顶部弹幕",
                    6: "逆向弹��",
                    7: "高级弹幕",
                    8: "码弹幕",
                    9: "BAS弹幕"
                }
                mode_type = mode_types.get(elem.mode, "未知类型")
                
                # 转换颜色为十进制并获取颜色名称
                hex_color = f"#{elem.color:06x}"
                color_name = get_color_name(hex_color)
                
                # 构建弹幕信息
                danmaku_info = (
                    f"时间: {minutes:02d}:{seconds:02d}\n"
                    f"内容: {elem.content}\n"
                    f"类型: {mode_type}\n"
                    f"颜色: {color_name} ({hex_color})\n"
                    f"字号: {elem.fontsize}\n"
                    f"发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(elem.ctime))}\n"
                    f"{'-' * 50}"
                )
                
                # 打印到控制台
                print(danmaku_info)
                
                # 添加到列表
                danmaku_list.append(danmaku_info)
            
            # 询问是否保存到文件
            if danmaku_list:
                choice = input("\n是否保存弹幕到本文件？(y/n) [y]: ").lower()
                if not choice or choice == 'y':
                    # 创建弹幕文件夹（如果不存在）
                    danmaku_dir = "弹幕"
                    if not os.path.exists(danmaku_dir):
                        os.makedirs(danmaku_dir)
                    
                    # 生成文件名（BV号 + 当前时间 + 弹幕后缀��
                    filename = f"{bvid} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 弹幕.txt"
                    # 完整的文件路径
                    filepath = os.path.join(danmaku_dir, filename)
                    
                    # 保存到文件
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(danmaku_list))
                        print(f"弹幕已保存到文件: {filepath}")
                    except Exception as e:
                        print(f"保存文件时出错: {str(e)}")
                
        else:
            print(f"获取弹幕失败: HTTP {resp.status_code}")
            
    except Exception as e:
        print(f"获取弹幕时出错: {str(e)}")

def get_comment_count(bvid: str) -> int:
    """获取视频评论总数"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 首先获取视频aid
        video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        response = requests.get(video_url, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            aid = data['data']['aid']
            
            # 然后获取评论总数
            count_url = 'https://api.bilibili.com/x/v2/reply/count'
            params = {
                'type': 1,  # 视频评论区
                'oid': aid  # 视频aid
            }
            
            count_response = requests.get(count_url, params=params, headers=headers)
            count_data = count_response.json()
            
            if count_data['code'] == 0:
                return count_data['data']['count']
            else:
                print(f"获取评数失败：{count_data['message']}")
                return 0
        else:
            print(f"获取视频信息失败：{data['message']}")
            return 0
            
    except Exception as e:
        print(f"获取评论数时出错: {str(e)}")
        return 0

def get_hot_comments(bvid: str, ps: int = 20, pn: int = 1) -> None:
    """获取视频热门评论"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 首先取视频aid
        video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        response = requests.get(video_url, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            aid = data['data']['aid']
            
            # 获取热评
            hot_url = 'https://api.bilibili.com/x/v2/reply/hot'
            params = {
                'type': 1,  # 视频评论区
                'oid': aid,  # 视频aid
                'ps': ps,    # 每页评论数
                'pn': pn     # 页码
            }
            
            hot_response = requests.get(hot_url, params=params, headers=headers)
            hot_data = hot_response.json()
            
            if hot_data['code'] == 0:
                # 检查data字段是否存在
                if 'data' not in hot_data or hot_data['data'] is None:
                    print("该视频暂无热评")
                    return
                    
                # 检查replies字段是否存在
                if 'replies' not in hot_data['data'] or not hot_data['data']['replies']:
                    print("该视频暂无热评")
                    return
                    
                page_info = hot_data['data'].get('page', {'acount': 0})
                replies = hot_data['data']['replies']
                
                print(f"\n获取到 {len(replies)} 条热门评论（总评论数：{page_info.get('acount', 0)}）:")
                print("="*50)
                
                for reply in replies:
                    # 获取评论者信息
                    member = reply['member']
                    username = member['uname']  # 用户名
                    user_level = member['level_info']['current_level']  # 用户等级
                    user_id = member['mid']  # 用户ID
                    
                    # 获取评论内容
                    content = reply['content']['message']
                    # 获取点赞数
                    like_count = reply['like']
                    # 获取回复数
                    reply_count = reply['rcount']
                    # 获取发布时间
                    ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reply['ctime']))
                    
                    print(f"评论者: {username} (UID: {user_id})")
                    print(f"用户等级: {user_level}")
                    print(f"点赞数: {like_count}")
                    print(f"回复数: {reply_count}")
                    print(f"发布时间: {ctime}")
                    print(f"评论内容: {content}")
                    print("-"*50)
                
                # 询问是否保存到文件
                choice = input("\n是否保存热评到文本文件？(y/n) [y]: ").lower()
                if not choice or choice == 'y':
                    # 创建评论文件夹（如果不存在）
                    comment_dir = "评论"
                    if not os.path.exists(comment_dir):
                        os.makedirs(comment_dir)
                    
                    # 生成文件名（BV号 + 当前时间 + ��论后缀）
                    filename = f"{bvid} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 评论.txt"
                    # 完整��文件路径
                    filepath = os.path.join(comment_dir, filename)
                    
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(f"视频热门评论（总评论数：{page_info.get('acount', 0)}）\n")
                            f.write("="*50 + "\n")
                            for reply in replies:
                                member = reply['member']
                                f.write(f"评论者: {member['uname']} (UID: {member['mid']})\n")
                                f.write(f"用户等级: {member['level_info']['current_level']}\n")
                                f.write(f"点赞数: {reply['like']}\n")
                                f.write(f"回复数: {reply['rcount']}\n")
                                f.write(f"发布时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reply['ctime']))}\n")
                                f.write(f"评论内容: {reply['content']['message']}\n")
                                f.write("-"*50 + "\n")
                        print(f"热评已保存到文件: {filepath}")
                    except Exception as e:
                        print(f"保存文件时出错: {str(e)}")
            else:
                print(f"获取热评失败：{hot_data['message']}")
        else:
            print(f"获取��频信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取热评时出错: {str(e)}")
        print("请确保视频存在且有评论权限")

def get_ip_location():
    """获取IP地理位置信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        while True:
            print("\n请选择查询方式：")
            print("1. 查询当前IP")
            print("2. 查询指定IP")
            print("3. 返回主菜单")
            
            choice = input("请选择 [1]: ").strip()
            if not choice:
                choice = "1"
                
            if choice == "1":
                # 查询当前IP
                url = 'https://api.bilibili.com/x/web-interface/zone'
                response = requests.get(url, headers=headers)
                data = response.json()
                
            elif choice == "2":
                # 查询指定IP
                ip = input("请输入要查询的IP地址: ").strip()
                url = 'https://api.live.bilibili.com/ip_service/v1/ip_service/get_ip_addr'
                params = {'ip': ip}
                response = requests.get(url, params=params, headers=headers)
                data = response.json()
                
            elif choice == "3":
                break
            else:
                print("无效的选择！")
                continue
            
            if data['code'] == 0:
                ip_info = data['data']
                print("\nIP地理位置信息:")
                print("="*50)
                print(f"IP地址: {ip_info['addr']}")
                print(f"国家/地区: {ip_info['country']}")
                if 'province' in ip_info and ip_info['province']:
                    print(f"省/州: {ip_info['province']}")
                if 'city' in ip_info and ip_info['city']:
                    print(f"城市: {ip_info['city']}")
                print(f"运营商: {ip_info['isp']}")
                if 'longitude' in ip_info and ip_info['longitude']:
                    print(f"经度: {ip_info['longitude']}")
                if 'latitude' in ip_info and ip_info['latitude']:
                    print(f"纬度: {ip_info['latitude']}")
                print("="*50)
            else:
                print(f"获���IP信息失败：{data.get('message', '') or data.get('msg', '')}")
            
            input("\n按回车继续...")
            
    except Exception as e:
        print(f"获取IP信息时出错: {str(e)}")

def get_live_room_info(room_id: str) -> None:
    """获取直播间信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/room/v1/Room/get_info'
        params = {'room_id': room_id}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            room_info = data['data']
            print("\n直播间信息:")
            print("="*50)
            print(f"主播UID: {room_info['uid']}")
            print(f"直播间号: {room_info['room_id']}")
            if room_info['short_id'] != 0:
                print(f"直播间短号: {room_info['short_id']}")
            print(f"关注数: {room_info['attention']}")
            print(f"观看人数: {room_info['online']}")
            print(f"标题: {room_info['title']}")
            print(f"分区: {room_info['parent_area_name']} - {room_info['area_name']}")
            
            # 显示直播状态
            status_map = {
                0: "未开播",
                1: "直播中",
                2: "轮播中"
            }
            status = status_map.get(room_info['live_status'], "未知状态")
            print(f"直播状态: {status}")
            
            if room_info['live_status'] == 1:
                print(f"开播时间: {room_info['live_time']}")
            
            if room_info['description']:
                print(f"\n房间简介: {room_info['description']}")
            
            # 显示认证信息
            if room_info['new_pendants']['badge']:
                badge = room_info['new_pendants']['badge']
                badge_type = {
                    'v_person': '个人认证',
                    'v_company': '企业认证'
                }
                print(f"\n认证类型: {badge_type.get(badge['name'], '未知认证')}")
                if badge['desc']:
                    print(f"认证说明: {badge['desc']}")
            
            # 显示热词
            if room_info['hot_words']:
                print("\n房间热词:")
                for word in room_info['hot_words']:
                    print(f"- {word}")
            
            print("="*50)
            
        else:
            print(f"获取直播间信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取直播间信息时出错: {str(e)}")

def get_user_live_status(mid: str) -> None:
    """获取用户直播间状态"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld'
        params = {'mid': mid}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            live_info = data['data']
            print("\n用户直播间状态:")
            print("="*50)
            
            # 显示房间状态
            room_status = "有直播间" if live_info['roomStatus'] == 1 else "无直播间"
            print(f"房间状态: {room_status}")
            
            if live_info['roomStatus'] == 1:
                # 显示直播状态
                live_status_map = {
                    0: "未开播",
                    1: "直播中"
                }
                live_status = live_status_map.get(live_info['live_status'], "未知状态")
                print(f"直播状态: {live_status}")
                
                # 显示轮播状态
                round_status = "轮播中" if live_info['roundStatus'] == 1 else "未轮播"
                print(f"轮播状态: {round_status}")
                
                print(f"直播间ID: {live_info['roomid']}")
                print(f"直播间标题: {live_info['title']}")
                print(f"观看人数: {live_info['online']}")
                print(f"直播间地址: {live_info['url']}")
                if live_info['cover']:
                    print(f"封面地址: {live_info['cover']}")
            
            print("="*50)
            
        else:
            print(f"获取直播间状态失败：{data['message']}")
            
    except Exception as e:
        print(f"获取直播间状态时出错: {str(e)}")

def get_room_init_info(room_id: str) -> None:
    """获取直播间初始化信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/room/v1/Room/room_init'
        params = {'id': room_id}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            room_info = data['data']
            print("\n直播间初始化信息:")
            print("="*50)
            print(f"真实房间号: {room_info['room_id']}")
            print(f"短号: {room_info['short_id']}")
            print(f"主播UID: {room_info['uid']}")
            
            # 显示直播状态
            status_map = {
                0: "未开播",
                1: "直播中",
                2: "轮播中"
            }
            status = status_map.get(room_info['live_status'], "未知状态")
            print(f"直播状态: {status}")
            
            # 示开播时间
            if room_info['live_time'] > 0:
                live_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(room_info['live_time']))
                print(f"开播时间: {live_time}")
            
            # 显示房间类型
            special_type_map = {
                0: "普通直播间",
                1: "付费直播间",
                2: "拜年祭直播间"
            }
            special_type = special_type_map.get(room_info['special_type'], "未知类型")
            print(f"房间���型: {special_type}")
            
            # 显示其他状态
            print(f"是否隐藏: {'是' if room_info['is_hidden'] else '否'}")
            print(f"是否锁定: {'是' if room_info['is_locked'] else '否'}")
            print(f"是否竖屏: {'是' if room_info['is_portrait'] else '否'}")
            print(f"是否加密: {'是' if room_info['encrypted'] else '否'}")
            if room_info['encrypted']:
                print(f"密码验证: {'已通过' if room_info['pwd_verified'] else '未通过'}")
            
            print("="*50)
            
        else:
            print(f"获取直播间信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取直播间信息时出错: {str(e)}")

def get_anchor_info(uid: str) -> None:
    """获取主播信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/live_user/v1/Master/info'
        params = {'uid': uid}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            anchor_data = data['data']
            info = anchor_data['info']
            exp = anchor_data['exp']
            
            print("\n主播信息:")
            print("="*50)
            print(f"UID: {info['uid']}")
            print(f"用户名: {info['uname']}")
            print(f"头像: {info['face']}")
            
            # 显示性别
            gender_map = {
                -1: "保密",
                0: "女",
                1: "男"
            }
            gender = gender_map.get(info['gender'], "未知")
            print(f"性别: {gender}")
            
            # 显示认证信息
            if info['official_verify']['type'] != -1:
                verify_type = "个人认证" if info['official_verify']['type'] == 0 else "机构认证"
                print(f"认证类型: {verify_type}")
                print(f"认证说明: {info['official_verify']['desc']}")
            
            # 显示等级信息
            level_info = exp['master_level']
            print(f"\n主播等级: {level_info['level']}")
            print(f"当前经验: {level_info['current'][1]}/{level_info['next'][1]}")
            print(f"升级还需: {level_info['next'][0] - level_info['current'][0]}")
            
            # 显示其他信息
            print(f"\n粉丝数: {anchor_data['follower_num']}")
            print(f"直播间ID: {anchor_data['room_id']}")
            if anchor_data['medal_name']:
                print(f"粉丝勋章: {anchor_data['medal_name']}")
            if anchor_data['glory_count'] > 0:
                print(f"主播荣誉数: {anchor_data['glory_count']}")
            if anchor_data['pendant']:
                print(f"头像框: {anchor_data['pendant']}")
            
            # 显示公告
            if anchor_data['room_news']['content']:
                print("\n主播公告:")
                print(f"内容: {anchor_data['room_news']['content']}")
                print(f"时间: {anchor_data['room_news']['ctime_text']}")
            
            print("="*50)
            
        else:
            print(f"获取主播信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取主播信息时出错: {str(e)}")

def get_room_base_info(room_ids: list) -> None:
    """获取直播间基本信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo'
        params = {
            'req_biz': 'web_room_componet',
        }
        # 添加多个房间号
        for room_id in room_ids:
            params[f'room_ids'] = room_id
            
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            rooms_info = data['data']['by_room_ids']
            
            for room_id, room_info in rooms_info.items():
                print(f"\n直播间 {room_id} 基本信息:")
                print("="*50)
                print(f"主播: {room_info['uname']} (UID: {room_info['uid']})")
                print(f"真实房间号: {room_info['room_id']}")
                if room_info['short_id'] != 0:
                    print(f"短号: {room_info['short_id']}")
                print(f"标题: {room_info['title']}")
                print(f"分区: {room_info['parent_area_name']} - {room_info['area_name']}")
                
                # 显示直播状态
                status_map = {
                    0: "未开播",
                    1: "直播中",
                    2: "轮播中"
                }
                status = status_map.get(room_info['live_status'], "未知状态")
                print(f"直播状态: {status}")
                
                print(f"关注数: {room_info['attention']}")
                print(f"在线人数: {room_info['online']}")
                
                if room_info['live_time'] != "0000-00-00 00:00:00":
                    print(f"开播时间: {room_info['live_time']}")
                
                if room_info['description']:
                    print(f"\n房间简介: {room_info['description']}")
                
                if room_info['tags']:
                    print(f"标签: {room_info['tags']}")
                
                if room_info['cover']:
                    print(f"封面: {room_info['cover']}")
                
                if room_info['background']:
                    print(f"背景: {room_info['background']}")
                
                print(f"直播间地址: {room_info['live_url']}")
                print("="*50)
            
        else:
            print(f"获取直播间信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取直播间信息时出错: {str(e)}")

def get_batch_live_status(uids: list) -> None:
    """批量查询直播间状态"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
        # 构造请求参数
        params = {}
        for i, uid in enumerate(uids):
            params[f'uids[]'] = uid
            
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            rooms_info = data['data']
            
            for uid, room_info in rooms_info.items():
                print(f"\n主播 {room_info['uname']} (UID: {uid}) 的直播状态:")
                print("="*50)
                print(f"直播间标题: {room_info['title']}")
                print(f"房间号: {room_info['room_id']}")
                if room_info['short_id'] != 0:
                    print(f"短号: {room_info['short_id']}")
                
                # 显示直播状态
                status_map = {
                    0: "未开播",
                    1: "正在直播",
                    2: "轮播中"
                }
                status = status_map.get(room_info['live_status'], "未知状态")
                print(f"直播状态: {status}")
                
                print(f"在线人数: {room_info['online']}")
                
                if room_info['live_time'] > 0:
                    live_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(room_info['live_time']))
                    print(f"开播时间: {live_time}")
                
                print(f"分区: {room_info['area_v2_parent_name']} - {room_info['area_v2_name']}")
                
                if room_info['tag_name']:
                    print(f"标签: {room_info['tag_name']}")
                
                if room_info['tags']:
                    print(f"���义标签: {room_info['tags']}")
                
                if room_info['cover_from_user']:
                    print(f"封面: {room_info['cover_from_user']}")
                
                # 显示直播类型
                broadcast_type = "手机直播" if room_info['broadcast_type'] == 1 else "普通直播"
                print(f"直播类型: {broadcast_type}")
                
                print("="*50)
            
        else:
            print(f"获取直播间状态失败：{data['message']}")
            
    except Exception as e:
        print(f"获取直播间状态时出错: {str(e)}")

def get_live_history_danmaku(room_id: str) -> None:
    """获取直播间最近历史弹幕"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory'
        params = {'roomid': room_id}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            admin_msgs = data['data']['admin']  # 管理员的弹���
            room_msgs = data['data']['room']    # 普通用户的弹幕
            
            print("\n直播间历史弹幕:")
            print("="*50)
            
            if admin_msgs:
                print("\n管理员弹幕:")
                print("-"*30)
                for msg in admin_msgs:
                    print(f"时����: {msg['timeline']}")
                    print(f"用户: {msg['nickname']} (UID: {msg['uid']})")
                    if msg['medal']:  # 如果有粉丝勋章
                        print(f"勋章: {msg['medal'][1]} {msg['medal'][0]}级")
                    print(f"内容: {msg['text']}")
                    print("-"*30)
            
            if room_msgs:
                print("\n普通用户弹幕:")
                print("-"*30)
                for msg in room_msgs:
                    print(f"时间: {msg['timeline']}")
                    print(f"用户: {msg['nickname']} (UID: {msg['uid']})")
                    if msg['medal']:  # 如果有粉丝勋章
                        print(f"勋章: {msg['medal'][1]} {msg['medal'][0]}级")
                    print(f"内容: {msg['text']}")
                    print("-"*30)
            
            # 询问是否保存到文件
            choice = input("\n是否保存历史弹幕到文本文件？(y/n) [y]: ").lower()
            if not choice or choice == 'y':
                # 创建直播弹幕文件夹（如果不存在）
                danmaku_dir = os.path.join("弹幕", "直播弹幕")
                if not os.path.exists(danmaku_dir):
                    os.makedirs(danmaku_dir)
                
                # 生成文件名（房间号 + 当前时间 + 历史弹幕后缀）
                filename = f"{room_id} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 历史弹幕.txt"
                filepath = os.path.join(danmaku_dir, filename)
                
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        if admin_msgs:
                            f.write("管理员弹幕:\n")
                            f.write("-"*30 + "\n")
                            for msg in admin_msgs:
                                f.write(f"时间: {msg['timeline']}\n")
                                f.write(f"用户: {msg['nickname']} (UID: {msg['uid']})\n")
                                if msg['medal']:
                                    f.write(f"勋章: {msg['medal'][1]} {msg['medal'][0]}级\n")
                                f.write(f"内容: {msg['text']}\n")
                                f.write("-"*30 + "\n")
                                f.flush()  # 立即写入文件
                            
                            time.sleep(10)
                        
                    print(f"\n监听完成，共收集到 {len(seen_msgs)} 条弹幕")
                    print(f"弹幕已保存到文件: {filepath}")
                    
                except KeyboardInterrupt:
                    print("\n用户停止监听")
                    print(f"已收集到 {len(seen_msgs)} 条弹幕")
                    print(f"弹幕已保存到文件: {filepath}")
        
        else:
            print(f"获取历史弹幕失败：{data['message']}")
            
    except Exception as e:
        print(f"获取历史弹幕时出错: {str(e)}")

def get_room_play_info(room_id: str) -> None:
    """获取直播间播放信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    # 清晰度代码映射
    quality_map = {
        30000: "杜比",
        20000: "4K",
        10000: "原画",
        400: "蓝光",
        250: "超清",
        150: "高清",
        80: "流畅"
    }
    
    try:
        url = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo'
        params = {
            'room_id': room_id,
            'protocol': '0,1',    # http_stream,http_hls
            'format': '0,1,2',    # flv,ts,fmp4
            'codec': '0,1',       # AVC,HEVC
            'qn': '10000',        # 原画质量
            'platform': 'web',
            'ptype': '8',
            'dolby': '5',
            'panorama': '1'
        }
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            room_info = data['data']
            print("\n直播间播放信息:")
            print("="*50)
            print(f"房间号: {room_info['room_id']}")
            if room_info['short_id'] != 0:
                print(f"短号: {room_info['short_id']}")
            print(f"主UID: {room_info['uid']}")
            
            # 显示直播状态
            status_map = {
                0: "未开播",
                1: "直播中",
                2: "轮播中"
            }
            status = status_map.get(room_info['live_status'], "未知状态")
            print(f"直播状态: {status}")
            
            if room_info['live_status'] == 1:
                live_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(room_info['live_time']))
                print(f"开播时间: {live_time}")
            
            # 显示房间状态
            print(f"是否隐藏: {'是' if room_info['is_hidden'] else '否'}")
            print(f"是否锁定: {'是' if room_info['is_locked'] else '否'}")
            print(f"是否竖屏: {'是' if room_info['is_portrait'] else '否'}")
            print(f"是否加密: {'是' if room_info['encrypted'] else '否'}")
            if room_info['encrypted']:
                print(f"密码验证: {'已通过' if room_info['pwd_verified'] else '未通过'}")
            
            # 显示清晰度信息
            if 'playurl_info' in room_info and 'playurl' in room_info['playurl_info']:
                playurl = room_info['playurl_info']['playurl']
                if 'g_qn_desc' in playurl:
                    print("\n可用清晰度:")
                    for qn in playurl['g_qn_desc']:
                        quality_name = quality_map.get(qn['qn'], qn['desc'])
                        desc = f"{quality_name}"
                        if qn['hdr_desc']:
                            desc += f" ({qn['hdr_desc']})"
                        print(f"- {desc} (qn: {qn['qn']})")
                
                # 显示直播流信息
                if 'stream' in playurl:
                    print("\n直播流信息:")
                    for stream in playurl['stream']:
                        print(f"\n协议: {stream['protocol_name']}")
                        for format_info in stream['format']:
                            print(f"格式: {format_info['format_name']}")
                            for codec in format_info['codec']:
                                print(f"编码: {codec['codec_name']}")
                                current_quality = quality_map.get(codec['current_qn'], f"未知({codec['current_qn']})")
                                print(f"当前清晰度: {current_quality}")
                                accept_qualities = [quality_map.get(qn, f"未知({qn})") for qn in codec['accept_qn']]
                                print(f"可用清晰度: {', '.join(accept_qualities)}")
                                if codec['url_info']:
                                    print(f"播放地址: {codec['url_info'][0]['host']}{codec['base_url']}")
            
            print("="*50)
            
        else:
            print(f"获取直播间播放信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取直播间播放信息时出错: {str(e)}")

def get_room_anchor_info(room_id: str) -> None:
    """获取直播间主播详细信息"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://live.bilibili.com',
    }
    
    try:
        url = 'https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room'
        params = {'roomid': room_id}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            if 'data' in data and data['data']:
                anchor_data = data['data']
                info = anchor_data['info']
                level = anchor_data['level']
                
                print("\n主播详细信息:")
                print("="*50)
                # ... 其他打印信息 ...
                print("="*50)
            else:
                print("未找到主播信息")
        else:
            print(f"获取主播信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取主播信息时出错: {str(e)}")

class LiveRoom:
    """B站直播间相关功能类"""
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://live.bilibili.com',
        }
        
    def get_room_info(self, room_id: str) -> None:
        """获取直播间信息"""
        try:
            url = 'https://api.live.bilibili.com/room/v1/Room/get_info'
            params = {'room_id': room_id}
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            if data['code'] == 0:
                room_info = data['data']
                print("\n直播间信息:")
                print("="*50)
                print(f"主播UID: {room_info['uid']}")
                print(f"直播间号: {room_info['room_id']}")
                if room_info['short_id'] != 0:
                    print(f"直播间短号: {room_info['short_id']}")
                print(f"关注数: {room_info['attention']}")
                print(f"观看人数: {room_info['online']}")
                print(f"标题: {room_info['title']}")
                print(f"分区: {room_info['parent_area_name']} - {room_info['area_name']}")
                print(f"直播状态: {'直播中' if room_info['live_status'] == 1 else '未开播'}")
                print("="*50)
            else:
                print(f"获取直播间信息失败：{data['message']}")
        except Exception as e:
            print(f"获取直播间信息时出错: {str(e)}")

def extract_room_id(url: str) -> str:
    """从直播间URL中提取房间号"""
    # 匹配live.bilibili.com/后面的数字
    pattern = r'live\.bilibili\.com/(\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ''

def extract_uid(url: str) -> str:
    """从B站个人空间URL中提取UID"""
    # 匹配space.bilibili.com/后面的数字
    pattern = r'space\.bilibili\.com/(\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ''

def send_danmaku(bvid: str, msg: str, progress: int = 0, color: int = 16777215, 
                 fontsize: int = 25, mode: int = 1, cookies: Dict = None) -> None:
    """发送视频弹幕
    Args:
        bvid: 视频BV号
        msg: 弹幕内容
        progress: 弹幕出现时间(毫秒)
        color: 弹幕颜色(十进制RGB888)
        fontsize: 弹幕字号(12-64)
        mode: 弹幕类型(1普通/4底部/5顶部/7高级/9BAS)
        cookies: cookies信息
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
        'Origin': 'https://www.bilibili.com'
    }

    try:
        # 1. 获取视频cid
        video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        response = requests.get(video_url, headers=headers)
        data = response.json()
        
        if data['code'] != 0:
            print(f"获取视频信息失败: {data['message']}")
            return
            
        cid = data['data']['cid']
        
        # 2. 准备发送弹幕的参数
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误: 无法获取CSRF Token")
            return
            
        send_url = 'https://api.bilibili.com/x/v2/dm/post'
        params = {
            'type': 1,
            'oid': cid,
            'msg': msg,
            'bvid': bvid,
            'progress': progress,
            'color': color,
            'fontsize': fontsize,
            'pool': 0,
            'mode': mode,
            'rnd': int(time.time() * 1000000),
            'csrf': csrf
        }
        
        # 3. 发送弹幕
        response = requests.post(send_url, data=params, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print(f"弹幕发送成功! dmid: {result['data']['dmid']}")
        else:
            error_messages = {
                -101: "账号未登录",
                -102: "账号被封停",
                -111: "csrf校验失败",
                -400: "请求错误",
                -404: "无此���",
                36700: "系统升级中",
                36701: "弹幕包含被禁止的内容",
                36702: "弹幕长度大于100",
                36703: "发送频率过快",
                36704: "禁止向未审核的视频发送弹幕",
                36705: "等级不足，不能发送弹幕",
                36706: "等级不足，不能发送顶端弹幕",
                36707: "等级不足，不能发送底端弹幕",
                36708: "等级不足，不能发送彩色弹幕",
                36709: "等级不足，不能发送高级弹幕",
                36710: "权限不足，不能发送这种样式的弹幕",
                36711: "该视频禁止发送弹幕",
                36712: "level 1用户发送弹幕的最大长度为20",
                36713: "稿件未付费",
                36714: "弹幕发送时间不合法",
                36715: "当日操作数量超过上限",
                36718: "目前您不是大会员，无法使用会员权益"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"弹幕发送失败: {error_msg}")
            
    except Exception as e:
        print(f"发送弹幕时出错: {str(e)}")

if __name__ == "__main__":
    try:
        # 创建必要的文件夹
        try:
            if not os.path.exists('logs'):
                os.makedirs('logs')
        except Exception as e:
            print(f"创建日志文件夹失败: {str(e)}")
            logging.error(f"创建日志文件夹失败: {str(e)}")

        # 检查cookies.txt
        if not os.path.exists('cookies.txt'):
            print("错误：找不到cookies.txt文件！")
            print("请确保cookies.txt文件存在且包含有效的cookies信息")
            logging.error("找不到cookies.txt文件")
            input("\n按回车键退出...")
            exit(1)
            
        # 检查必要模块
        try:
            import google.protobuf.text_format as text_format
            from bilibili.community.service.dm.v1 import dm_pb2 as Danmaku
        except ImportError as e:
            print("错误：缺少必要的模块！")
            print(f"导入错误: {str(e)}")
            print("\n请确保已安装以下模块：")
            print("1. protobuf")
            print("2. 已编译生成dm_pb2.py文件")
            logging.error(f"模块导入失败: {str(e)}")
            input("\n按回车键退出...")
            exit(1)
            
        # 运行主程序
        try:
            main()
        except Exception as e:
            print("\n程序运行出错:")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            logging.error(f"主程序运行错误: {str(e)}", exc_info=True)
            input("\n按回车继续...")
            
    except Exception as e:
        print("\n程序出现未处理的错误:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        logging.error(f"未处理的错误: {str(e)}", exc_info=True)
        print("\n错误详细信息:")
        traceback.print_exc()
        input("\n按回车键退出...")
        
    finally:
        print("\n" + "="*50)
        input("按回车键退出...")