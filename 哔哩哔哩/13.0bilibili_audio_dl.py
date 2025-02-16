import json
import os
import subprocess
from typing import Dict
from tqdm import tqdm
import re
import requests
import time
import random
import base64
import shutil
import hashlib

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
                        # 检查必要的cookie是否存在
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
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-acodec', 'libmp3lame',
            '-q:a', '0',  # ���高质量
            '-threads', '4',  # 使���4个线程
            '-progress', 'pipe:1',  # 输出进度信息到stdout
            '-nostats',  # 不输出额外统计信息
            output_file
        ]
        
        print(f"正在转换为MP3: {os.path.basename(input_file)}")
        
        # 创�����进度条
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
        # 获取视频BV号并显���信息
        bvid = extract_bvid(url_or_bvid)
        if bvid:
            pages = get_video_info(bvid, headers, show_info=False)  # 添加参数控制是否显示信息
            if len(pages) > 1:
                choice = input("\n是��显示分P列表？(y/n) [n]: ").lower()
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
                print("支持范围选择（例如：1-5 7 9-11）")
                choice = input("请选择 [1]: ").strip()
                
                # 如果直接回车，默认下载第一P
                if not choice:
                    choice = "1"
                
                # 解析选��的分P
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
        print(f"下载过程出错: {str(e)}")

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
        # 获取用户导航信息
        nav_url = 'https://api.bilibili.com/x/web-interface/nav'
        nav_resp = requests.get(nav_url, cookies=cookies, headers=headers)
        nav_data = nav_resp.json()
        
        if nav_data['code'] == 0:
            data = nav_data['data']
            print(f"用户名: {data['uname']}")
            print(f"用户ID: {data['mid']}")
            print(f"邮箱验证: {'已验证' if data['email_verified'] else '未验证'}")
            print(f"手机验证: {'已验证' if data['mobile_verified'] else '未验证'}")
            print(f"硬币数: {data['money']}")
            print(f"B币余额: {data['wallet']['bcoin_balance']}")
            print(f"道德值: {data['moral']}")
            
            # 等级信息
            level_info = data['level_info']
            print(f"\n等级信息:")
            print(f"当前等级: {level_info['current_level']}")
            print(f"当前经验: {level_info['current_exp']}")
            print(f"下一级所需经验: {level_info['next_exp']}")
            
            # 会员信息
            vip = data['vip']
            print(f"\n会员信息:")
            vip_type_map = {0: "无", 1: "月度大会员", 2: "年度大会员"}
            print(f"会员类型: {vip_type_map.get(vip['type'], '未知')}")
            if vip['status'] == 1:
                due_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(vip['due_date']/1000))
                print(f"到期时间: {due_date}")
            
            # 认证信息
            if data['official']['type'] != -1:
                print(f"\n认证信息:")
                print(f"认证类型: {'个人认证' if data['official']['type'] == 0 else '机构认证'}")
                if data['official']['title']:
                    print(f"认证信息: {data['official']['title']}")
                if data['official']['desc']:
                    print(f"认证描述: {data['official']['desc']}")
            
            # 获取关注和粉丝数
            stat_url = f'https://api.bilibili.com/x/relation/stat?vmid={data["mid"]}'
            stat_resp = requests.get(stat_url, headers=headers)
            stat_data = stat_resp.json()
            
            if stat_data['code'] == 0:
                stat_info = stat_data['data']
                print(f"\n社交信息:")
                print(f"关注数: {stat_info['following']}")
                print(f"粉丝数: {stat_info['follower']}")
            
            # 获取今日投币经验
            coin_exp_url = 'https://api.bilibili.com/x/web-interface/coin/today/exp'
            coin_exp_resp = requests.get(coin_exp_url, cookies=cookies, headers=headers)
            coin_exp_data = coin_exp_resp.json()
            
            if coin_exp_data['code'] == 0:
                today_exp = coin_exp_data['data']
                max_coin_exp = 50
                print(f"\n投币信息:")
                print(f"今日投币经验: {today_exp}/{max_coin_exp}")
                remaining_coins = (max_coin_exp - today_exp) // 10
                if remaining_coins > 0:
                    print(f"今日还可投币: {remaining_coins}个")
        
        else:
            print(f"获取用户信息失败：{nav_data['message']}")
            
    except Exception as e:
        print(f"获取用户信���时出错: {str(e)}")
    
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
            
            # 从文件中读取��取BV号
            bvids = extract_bvid_from_file('bvid.txt')
            
            if not bvids:
                print("错误：无法从文件中提取有效的BV号！")
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
    print("1. 批量点赞视频 (默认)")
    print("2. 批量投币")
    print("3. 下载视频音频")
    print("4. 获取视频BV号")
    print("5. 查看用户信息")
    print("6. bv转av")
    print("7. 获取视频弹幕")
    print("8. 获取视频热评")
    print("9. 查看IP地理位置")
    print("10. 直播")
    print("11. 弹幕点赞")
    print("12. 老粉计划")
    print("13. 举报视频")
    print("14. 搜索视频")  # 新增选项
    print("15. 退出程序")  # 退出选项改为15
    print("="*50)
    
    choice = input("请选择功能 (1-15) [1]: ").strip()
    if not choice:
        return '1'
    if choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']:
        return choice
    print("无效的选择，使用默认选项1")
    return '1'

def show_live_menu() -> str:
    """显示直播功能子菜单"""
    print("\n" + "="*50)
    print("直播功能")
    print("="*50)
    print("1. 获取直播间信息")
    print("2. 获取用户�������播状态")
    print("3. 获取主播信息")
    print("4. 获取多个直播间信息")
    print("5. 批量查询直播状态")
    print("6. 获取直播间历史弹幕")
    print("7. 获取直播间播放信息")
    print("8. 获取直播间主播详情")
    print("9. ���回主菜单")
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
    
    print("请输入B站视频URL�����BV号，每行一���，输入q��束：")
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
            
            # ���回分P信息，供下载功能使用
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
                            print("��止点赞操作")
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
    """��载单个音频"""
    try:
        cmd = [
            'yt-dlp',
            '--cookies', 'cookies.txt',  # 直接使用当前目����的cookies.txt
            '-f', 'ba',
            '--no-playlist',
            '--no-check-certificates',
            '--progress',
            '--newline',
            '-o', os.path.join("音频", "%(title)s.%(ext)s"),  # 指定下载路径
            url
        ]
        
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
        
        # 用于解析下载进度的正则表���式
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
                        print("未找到ffmpeg，无法转换为MP3格式")
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
            print(f"下载失败！错误���息：\n{error}")
            
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
        "举报",                    # 存放举报相关文件
        os.path.join("举报", "图片"),  # 存放举报附件图片
        os.path.join("举报", "记录"),  # 存放举报记录
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"创建文件夹: {directory}")
            except Exception as e:
                print(f"创建文件夹 {directory} 时出错: {str(e)}")

def main():
    # 创建必要的文件夹
    create_required_directories()
    
    # 检查cookies.txt是否存在
    if not os.path.exists('cookies.txt'):  # 直接���查当前目录
        print("错误：找不到cookies.txt文件！")
        print("请确保cookies.txt文件存在且包含有效的cookies信息")
        return
    
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
                print("\n请输入B站视频URL或BV号 (输入q返回主菜单):")
                input_text = input().strip()
                
                if input_text.lower() == 'q':
                    break
                    
                # 如果输入的是BV号
                if input_text.startswith('BV'):
                    download_audio(input_text, cookies)
                    continue
                    
                # 如果输入的是URL
                if not input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                    print("请输入有效的B站视频链接或BV号！")
                    continue
                    
                download_audio(input_text, cookies)
        
        elif choice == '4':
            # ���取视频BV号
            get_video_bvids()
        
        elif choice == '5':
            # 查看用户信息
            get_user_info(cookies)
        
        elif choice == '6':
            # 新增的功能：bv转av
            bvid = input("请输入BV号: ").strip()
            if bvid.startswith('BV'):
                av_number = bv_to_av(bvid)
                print(f"对应AV号是: {av_number}")
            else:
                print("请输入有效的BV号！")
        
        elif choice == '7':
            # 获取视频弹幕
            input_text = input("请输入视频URL或BV号: ").strip()
            
            # 如果输入的��BV号
            if input_text.startswith('BV'):
                bvid = input_text
            # 如果输入的是URL
            elif input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                bvid = extract_bvid(input_text)
            else:
                print("请输入有效的B站视频链接或BV号！")
                continue
                
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
                            get_danmaku(cid, bvid, int(segment), cookies)  # 传入cookies参数
                        else:
                            print("请输入有效的数字！")
                    else:
                        print(f"获取视频信息失败：{data['message']}")
                except Exception as e:
                    print(f"获取弹幕时出错: {str(e)}")
            else:
                print("无法��别BV号")
        
        elif choice == '8':
            # 获取视频热评
            input_text = input("请输入视频URL或BV号: ").strip()
            
            # 如果输入的BV号
            if input_text.startswith('BV'):
                bvid = input_text
            # 如果输入的是URL
            elif input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                bvid = extract_bvid(input_text)
            else:
                print("请输入有效的B站视频链接或BV号！")
                continue
                
            if bvid:
                # 获取每页评论数
                ps = input("请输入每页显示的评论数 (1-49) [20]: ").strip()
                if not ps:
                    ps = "20"
                if ps.isdigit() and 1 <= int(ps) <= 49:
                    get_hot_comments(bvid, int(ps))
                else:
                    print("请输入有效的数字！")
            else:
                print("无法识别BV号！")
        
        elif choice == '9':
            # 查看IP地理位置
            get_ip_location()
        
        elif choice == '10':
            # 进入直播子菜单
            while True:
                live_choice = show_live_menu()
                
                if live_choice == '1':
                    room_input = input("请输入直播间号或直播间链接: ").strip()
                    room_id = extract_room_id(room_input) if 'live.bilibili.com' in room_input else room_input
                    if room_id.isdigit():
                        live_room.get_room_info(room_id)
                    else:
                        print("请输入有效的直播间号或链接！")
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继续显示直播菜单
                
                elif live_choice == '2':
                    uid_input = input("请输入用户UID或个人空间链接: ").strip()
                    if 'space.bilibili.com' in uid_input:
                        uid = extract_uid(uid_input)
                    else:
                        uid = uid_input
                    if uid.isdigit():
                        live_room.get_user_live_status(uid)
                    else:
                        print("请输入有效的用户UID或个人空间链接！")
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继续显示直播菜单
                
                elif live_choice == '3':
                    uid_input = input("请输入主播UID或直播间链接: ").strip()
                    if 'live.bilibili.com' in uid_input:
                        uid = extract_uid(uid_input)
                    else:
                        uid = uid_input
                    if uid.isdigit():
                        live_room.get_anchor_info(uid)
                    else:
                        print("请输入有效的主播UID或直播间链接！")
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继���显示直播菜单
                
                elif live_choice == '4':
                    room_input = input("请输入直播间号或直播间链接: ").strip()
                    live_room.get_room_base_info([room_input])
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继续显示直播菜单
                
                elif live_choice == '5':
                    live_room.get_batch_live_status([room_input])
                    input("\n按回车继续...")  # 添加���一行
                    continue  # 继续��示直播菜单
                
                elif live_choice == '6':
                    room_input = input("请输入直播间号或直播间链接: ").strip()
                    live_room.get_history_danmaku(room_input)
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继续显示直播菜单
                
                elif live_choice == '7':
                    room_input = input("请输入直播间号或直播间链接: ").strip()
                    live_room.get_play_info(room_input)
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继续显示直播菜单
                
                elif live_choice == '8':
                    room_input = input("请输入直播间号或直播间链接: ").strip()
                    live_room.get_room_anchor_info(room_input)
                    input("\n按回车继续...")  # 添加这一行
                    continue  # 继续显示直播菜单
                
                elif live_choice == '9':
                    break  # 返回主菜单
        
        elif choice == '11':
            # 弹幕点赞功能
            input_text = input("请输入视频URL或BV号: ").strip()
            
            # 如果输入的是BV号
            if input_text.startswith('BV'):
                bvid = input_text
            # 如果输入的是URL
            elif input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                bvid = extract_bvid(input_text)
            else:
                print("请输入有效的B站视频链接或BV号！")
                continue
                
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
                            get_danmaku(cid, bvid, int(segment), cookies)  # 传入cookies参数
                        else:
                            print("请输入有效的数字！")
                    else:
                        print(f"获取视频信息失败：{data['message']}")
                except Exception as e:
                    print(f"获取弹幕时出错: {str(e)}")
            else:
                print("无法识别BV号")
        
        elif choice == '12':  # 原来的退出选项改为12
            print("\n=== 老粉计划 ===")
            print("1. 加入老粉计划")
            print("2. 发送老粉留言")
            print("3. 返回主菜单")
            
            fan_choice = input("\n请选择功能 (1-3) [1]: ").strip()
            if not fan_choice:
                fan_choice = "1"
                
            if fan_choice == "1":
                up_input = input("\n请输入UP主UID或空间链接: ").strip()
                if 'space.bilibili.com' in up_input:
                    up_mid = extract_uid(up_input)
                else:
                    up_mid = up_input
                    
                if up_mid.isdigit():
                    join_old_fan_plan(up_mid, cookies)
                else:
                    print("请输入有效的UP主UID或空间链接！")
                    
            elif fan_choice == "2":
                up_input = input("\n请输入UP主UID或空间链接: ").strip()
                if 'space.bilibili.com' in up_input:
                    up_mid = extract_uid(up_input)
                else:
                    up_mid = up_input
                    
                if up_mid.isdigit():
                    message = input("请输入要发送的留言: ").strip()
                    if message:
                        send_old_fan_message(up_mid, message, cookies)
                    else:
                        print("留言内容不能为空！")
                else:
                    print("请输入有效的UP主UID或空间链接！")
            
            input("\n按回车继续...")  # 添加这行防止直接退出
            continue  # 继续显示主菜单
            
        elif choice == '13':
            # 举报视频
            input_text = input("请输入要举报的视频URL或BV号: ").strip()
            
            # 如果输入的是BV号
            if input_text.startswith('BV'):
                bvid = input_text
            # 如果输入的是URL
            elif input_text.startswith(('https://www.bilibili.com', 'https://b23.tv')):
                bvid = extract_bvid(input_text)
            else:
                print("请输入有效的B站视频链接或BV号！")
                continue
                
            if bvid:
                show_report_menu(bvid, cookies)
            else:
                print("无法识别BV号！")
        
        elif choice == '14':
            show_search_menu(cookies)  # 传入cookies
        
        elif choice == '15':
            print("\n感谢使用！再见！")
            break

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
        '#ff8080': '��红',
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

def like_danmaku(dmid: str, oid: str, cookies: Dict) -> bool:
    """点赞弹幕
    
    Args:
        dmid (str): 弹幕ID
        oid (str): 视频cid
        cookies (Dict): cookies信息
        
    Returns:
        bool: 是否点赞成功
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        # 获取csrf令牌
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return False
            
        # 构造请求数据
        data = {
            'dmid': dmid,
            'oid': oid,
            'op': 1,  # 1表示点赞，2表示取消点赞
            'platform': 'web_player',
            'csrf': csrf
        }
        
        # 发送点赞请求
        url = 'https://api.bilibili.com/x/v2/dm/thumbup/add'
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print(f"成功给弹幕 {dmid} 点赞")
            return True
        else:
            error_messages = {
                -101: "账号未登录",
                -111: "csrf校验失败",
                -400: "请求错误",
                36106: "���弹幕已被删除",
                36805: "该视频禁止点赞弹幕",
                65004: "取消赞失败，未点赞过",
                65006: "已赞过该弹幕"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"点赞弹幕失败：{error_msg}")
            return False
            
    except Exception as e:
        print(f"点赞弹幕时出错: {str(e)}")
        return False

def get_danmaku(cid: str, bvid: str, segment_index: int = 1, cookies: Dict = None) -> None:
    """获取视频弹幕"""
    try:
        import google.protobuf.text_format as text_format
        from bilibili.community.service.dm.v1 import dm_pb2 as Danmaku
    except ImportError:
        print("错误：缺少必要的库，请先安装：")
        print("pip install protobuf")
        print("同时需要编译proto文件生成dm_pb2.py")
        return

    url = 'https://api.bilibili.com/x/v2/dm/web/seg.so'
    params = {
        'type': 1,              
        'oid': cid,            
        'segment_index': segment_index  
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
            
            danmaku_list = []
            
            print(f"\n获取到 {len(danmaku_seg.elems)} 条弹幕:")
            print("-" * 50)
            
            for elem in danmaku_seg.elems:
                seconds = elem.progress / 1000
                minutes = int(seconds / 60)
                seconds = int(seconds % 60)
                
                mode_types = {
                    1: "普通弹幕",
                    2: "普通弹幕",
                    3: "普通弹幕",
                    4: "底部弹幕",
                    5: "顶部弹幕",
                    6: "逆向弹幕",
                    7: "高级弹幕",
                    8: "代码弹幕",
                    9: "BAS弹幕"
                }
                mode_type = mode_types.get(elem.mode, "未知类型")
                
                hex_color = f"#{elem.color:06x}"
                color_name = get_color_name(hex_color)
                
                danmaku_info = (
                    f"时间: {minutes:02d}:{seconds:02d}\n"
                    f"内容: {elem.content}\n"
                    f"类型: {mode_type}\n"
                    f"颜色: {color_name} ({hex_color})\n"
                    f"字号: {elem.fontsize}\n"
                    f"发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(elem.ctime))}\n"
                    f"弹幕ID: {elem.id}\n"  # 添加弹幕ID显示
                    f"{'-' * 50}"
                )
                
                # 只打印一次弹幕信息
                print(danmaku_info)
                
                # 询问是否点赞
                choice = input("是否点赞该弹幕？(y/n) [n]: ").lower()
                if choice == 'y':
                    like_danmaku(str(elem.id), cid, cookies)
                
                danmaku_list.append(danmaku_info)
            
            # 询问是否保存到文件
            if danmaku_list:
                choice = input("\n是否保存弹幕到文本文件？(y/n) [y]: ").lower()
                if not choice or choice == 'y':
                    danmaku_dir = "弹幕"
                    if not os.path.exists(danmaku_dir):
                        os.makedirs(danmaku_dir)
                    
                    filename = f"{bvid} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 弹幕.txt"
                    filepath = os.path.join(danmaku_dir, filename)
                    
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
        print("���误详细信息:")
        import traceback
        traceback.print_exc()

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
                # ��查data字段是否存在
                if 'data' not in hot_data or hot_data['data'] is None:
                    print("该视频暂无热评")
                    return
                    
                # 检查replies字段是否存在
                if 'replies' not in hot_data['data'] or not hot_data['data']['replies']:
                    print("该视频暂无热���")
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
                    
                    # 生成文件名（BV号 + 当前���间 + 评论后���）
                    filename = f"{bvid} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 评论.txt"
                    # 完整文件路径
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
                        print(f"保存文件���出��: {str(e)}")
            else:
                print(f"获取热评失败：{hot_data['message']}")
        else:
            print(f"获取视频信息失败：{data['message']}")
            
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
                print(f"获取IP信息失败：{data.get('message', '') or data.get('msg', '')}")
            
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
            print(f"主��UID: {room_info['uid']}")
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
            
            # 显示开播时间
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
            print(f"房间类型: {special_type}")
            
            # 显示其��状态
            print(f"是否隐藏: {'是' if room_info['is_hidden'] else '否'}")
            print(f"是否锁���: {'是' if room_info['is_locked'] else '否'}")
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
                print(f"时��: {anchor_data['room_news']['ctime_text']}")
            
            print("="*50)
            
        else:
            print(f"获取主播信息失败：{data['message']}")
            
    except Exception as e:
        print(f"获取主播信息时出错: {str(e)}")

def get_room_base_info(room_ids: list) -> None:
    """获取多个直播间基本信息"""
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
                status = status_map.get(room_info['live_status'], "未知��态")
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
        print(f"获取直播间信息时�����错: {str(e)}")

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
                    print(f"开���时间: {live_time}")
                
                print(f"分区: {room_info['area_v2_parent_name']} - {room_info['area_v2_name']}")
                
                if room_info['tag_name']:
                    print(f"标签: {room_info['tag_name']}")
                
                if room_info['tags']:
                    print(f"定义标签: {room_info['tags']}")
                
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
            admin_msgs = data['data']['admin']  # 管理员的弹幕
            room_msgs = data['data']['room']    # 普通用户的弹幕
            
            print("\n直播间历史弹幕:")
            print("="*50)
            
            if admin_msgs:
                print("\n管理员弹幕:")
                print("-"*30)
                for msg in admin_msgs:
                    print(f"时间: {msg['timeline']}")
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
                    print(f"���户: {msg['nickname']} (UID: {msg['uid']})")
                    if msg['medal']:  # 如果有粉丝勋章
                        print(f"勋章: {msg['medal'][1]} {msg['medal'][0]}级")
                    print(f"内容: {msg['text']}")
                    print("-"*30)
            
            # 询问是否保存到文件
            choice = input("\n是否保存历史弹幕到文本文件？(y/n) [y]: ").lower()
            if not choice or choice == 'y':
                # 创建直��弹幕文件夹（如果不存在）
                danmaku_dir = os.path.join("弹幕", "直播弹幕")
                if not os.path.exists(danmaku_dir):
                    os.makedirs(danmaku_dir)
                
                # 生成文件名（房间号 + 当前时间 + 历史弹幕后缀）
                filename = f"{room_id} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} �����史弹幕.txt"
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
                        
                    print(f"\n监��完成，共收集到 {len(seen_msgs)} 条弹幕")
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
                
                # 基本信息
                print("基本信息:")
                print(f"UID: {info['uid']}")
                print(f"用户名: {info['uname']}")
                print(f"头像: {info['face']}")
                print(f"排名: {info['rank']}")
                print(f"平台用户等级: {info['platform_user_level']}")
                
                # 认证状态
                print(f"\n认证状态:")
                print(f"手机认证: {'已认证' if info['mobile_verify'] == 1 else '未认证'}")
                print(f"身份认证: {'已认证' if info['identification'] == 1 else '未认证'}")
                
                # 官方认证信息
                if info['official_verify']['type'] != -1:
                    verify_type = "认证" if info['official_verify']['type'] == 0 else "机构认证"
                    print(f"认证类型: {verify_type}")
                    print(f"认证说���: {info['official_verify']['desc']}")
                
                # 性别
                gender_map = {
                    -1: "保密",
                    0: "女",
                    1: "男"
                }
                print(f"性别: {gender_map.get(info['gender'], '未知')}")
                
                # 等级信息
                print("\n等级信息:")
                master_level = level['master_level']
                print(f"主播等级: {master_level['level']}")
                print(f"用户等级: {level['user_level']}")
                print(f"���播积分: {master_level['anchor_score']}")
                if master_level['upgrade_score'] > 0:
                    print(f"升级还需: {master_level['upgrade_score']}")
                
                # 消费信息
                print("\n消费信息:")
                print(f"消费金额: {level['cost']}")
                print(f"充值金额: {level['rcost']}")
                
                # VIP信息
                print("\nVIP状态:")
                if level['vip'] == 1:
                    print(f"VIP到期时间: {level['vip_time']}")
                else:
                    print("不是VIP")
                if level['svip'] == 1:
                    print(f"SVIP到期时间: {level['svip_time']}")
                else:
                    print("不是SVIP")
                
                # SAN值
                print(f"\nSAN值: {anchor_data['san']}/12")
                
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
        # 清晰度代码映射
        self.quality_map = {
            30000: "杜比",
            20000: "4K",
            10000: "原画",
            400: "蓝光",
            250: "超清",
            150: "高清",
            80: "流畅"
        }
    
    def _process_room_id(self, room_input: str) -> str:
        """处理直播间号输入，支持直接输入房�����号或链接"""
        if 'live.bilibili.com' in room_input:
            return extract_room_id(room_input)
        return room_input
    
    def get_room_info(self, room_input: str) -> None:
        """获取直播间信息"""
        room_id = self._process_room_id(room_input)
        if not room_id.isdigit():
            print("请输入有效的直播间号或链接！")
            return
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
    
    def get_user_live_status(self, mid: str) -> None:
        """获取用户直播间状态"""
        # 原get_user_live_status函数的内容
        
    def get_anchor_info(self, uid: str) -> None:
        """获取主播信息"""
        try:
            url = 'https://api.live.bilibili.com/live_user/v1/Master/info'
            params = {'uid': uid}
            response = requests.get(url, params=params, headers=self.headers)
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
                
                # ������其他信息
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
            print(f"获取��播��息时出错: {str(e)}")
    
    def get_room_base_info(self, room_ids: list) -> None:
        """获取多个直播间基本信息"""
        # 原get_room_base_info函数的内容
        
    def get_batch_live_status(self, uids: list) -> None:
        """批量查询直播间状态"""
        # 原get_batch_live_status函数的���容
        
    def get_history_danmaku(self, room_input: str) -> None:
        """获取直播间历史弹幕"""
        room_id = self._process_room_id(room_input)
        if not room_id.isdigit():
            print("请输入有效的直播间号或链接！")
            return
        
        try:
            print("\n请选择获取方式：")
            print("1. 获取最近弹幕")
            print("2. 持续监听弹幕")
            choice = input("请选择 [1]: ").strip()
            
            if not choice:
                choice = "1"
                
            if choice == "1":
                self._get_recent_danmaku(room_id)
            elif choice == "2":
                self._monitor_danmaku(room_id)
        
        except Exception as e:
            print(f"获取历史弹幕时出错: {str(e)}")

    def _get_recent_danmaku(self, room_id: str) -> None:
        """获取最近的弹幕"""
        try:
            url = 'https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory'
            params = {'roomid': room_id}
            response = requests.get(url, params=params, headers=self.headers)
            data = response.json()
            
            if data['code'] == 0:
                self._save_danmaku_to_file(room_id, data['data'])
            else:
                print(f"获取历史弹幕失败：{data['message']}")
        
        except Exception as e:
            print(f"获取最近弹幕时出错: {str(e)}")

    def _monitor_danmaku(self, room_id: str) -> None:
        """持续监听直播间弹幕"""
        try:
            duration = input("请输入监听时长（分钟）[30]: ").strip()
            duration = int(duration) if duration.isdigit() else 30
            interval = input("请输入获取间隔（秒）[10]: ").strip()
            interval = int(interval) if interval.isdigit() else 10
            
            print(f"\n开始监听直播间 {room_id} 的弹幕")
            print(f"将持续监听 {duration} 分钟，每 {interval} 秒获取一次")
            print("按Ctrl+C可以随时停止")
            
            # 创建文件
            danmaku_dir = os.path.join("弹幕", "直播弹幕")
            if not os.path.exists(danmaku_dir):
                os.makedirs(danmaku_dir)
            
            filename = f"{room_id} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 监听弹幕.txt"
            filepath = os.path.join(danmaku_dir, filename)
            
            seen_msgs = set()  # 用于去重
            start_time = time.time()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                try:
                    while time.time() - start_time < duration * 60:
                        new_msgs = self._fetch_danmaku(room_id)
                        for msg in new_msgs:
                            msg_id = f"{msg['timeline']}_{msg['nickname']}_{msg['text']}"
                            if msg_id not in seen_msgs:
                                seen_msgs.add(msg_id)
                                # 写入文件
                                f.write(f"时间: {msg['timeline']}\n")
                                f.write(f"用户: {msg['nickname']} (UID: {msg['uid']})\n")
                                if msg['medal']:
                                    f.write(f"勋章: {msg['medal'][1]} {msg['medal'][0]}级\n")
                                f.write(f"内容: {msg['text']}\n")
                                f.write("-"*30 + "\n")
                                f.flush()  # 立即写入文件
                        
                        time.sleep(interval)
                    
                    print(f"\n监完成，共收集到 {len(seen_msgs)} 条弹幕")
                    print(f"弹幕已保存到文件: {filepath}")
                    
                except KeyboardInterrupt:
                    print("\n用户停止监听")
                    print(f"已收集到 {len(seen_msgs)} 条弹幕")
                    print(f"弹幕已保存到文件: {filepath}")
                
        except Exception as e:
            print(f"监听弹幕时出错: {str(e)}")

    def _save_danmaku_to_file(self, room_id: str, data: dict) -> None:
        """保存弹幕到文件"""
        admin_msgs = data['admin']
        room_msgs = data['room']
        
        danmaku_dir = os.path.join("弹幕", "直播弹幕")
        if not os.path.exists(danmaku_dir):
            os.makedirs(danmaku_dir)
        
        filename = f"{room_id} {time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())} 历史弹幕.txt"
        filepath = os.path.join(danmaku_dir, filename)
        
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
            
            if room_msgs:
                f.write("\n普通用户弹幕:\n")
                f.write("-"*30 + "\n")
                for msg in room_msgs:
                    f.write(f"时间: {msg['timeline']}\n")
                    f.write(f"用户: {msg['nickname']} (UID: {msg['uid']})\n")
                    if msg['medal']:
                        f.write(f"勋章: {msg['medal'][1]} {msg['medal'][0]}级\n")
                    f.write(f"内容: {msg['text']}\n")
                    f.write("-"*30 + "\n")
        
        total_msgs = len(admin_msgs) + len(room_msgs)
        print(f"\n共获取到 {total_msgs} 条弹幕")
        print(f"弹幕已保存到文件: {filepath}")
    
    def _fetch_danmaku(self, room_id: str) -> list:
        """获取一次弹幕数据"""
        url = 'https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory'
        params = {'roomid': room_id}
        response = requests.get(url, params=params, headers=self.headers)
        data = response.json()
        
        if data['code'] == 0:
            msgs = []
            if 'admin' in data['data']:
                msgs.extend(data['data']['admin'])
            if 'room' in data['data']:
                msgs.extend(data['data']['room'])
            return msgs
        return []
    
    def get_play_info(self, room_input: str) -> None:
        """获取直播间播放信息"""
        room_id = self._process_room_id(room_input)
        if not room_id.isdigit():
            print("请输入有效的直播间号或链接！")
            return
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://live.bilibili.com',
        }
        
        # 清晰度代码映射
        quality_map = {
            30000: "杜比",
            20000: "4K",
            10000: "���画",
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
    
    def get_room_anchor_info(self, room_input: str) -> None:
        """获取直播间主播详细信息"""
        room_id = self._process_room_id(room_input)
        if not room_id.isdigit():
            print("请输入有效的直播间号或链接！")
            return
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
                    
                    # 基本信息
                    print("基本信息:")
                    print(f"UID: {info['uid']}")
                    print(f"���户名: {info['uname']}")
                    print(f"头像: {info['face']}")
                    print(f"排名: {info['rank']}")
                    print(f"平台用户等级: {info['platform_user_level']}")
                    
                    # 认证状态
                    print(f"\n认证状态:")
                    print(f"手机认证: {'已认证' if info['mobile_verify'] == 1 else '未认证'}")
                    print(f"身份认证: {'已认证' if info['identification'] == 1 else '未认证'}")
                    
                    # 官方认证信息
                    if info['official_verify']['type'] != -1:
                        verify_type = "认证" if info['official_verify']['type'] == 0 else "机构认证"
                        print(f"认证类型: {verify_type}")
                        print(f"认证说明: {info['official_verify']['desc']}")
                    
                    # 性别
                    gender_map = {
                        -1: "保密",
                        0: "女",
                        1: "男"
                    }
                    print(f"性别: {gender_map.get(info['gender'], '未知')}")
                    
                    # 等级信息
                    print("\n等级信息:")
                    master_level = level['master_level']
                    print(f"主播等级: {master_level['level']}")
                    print(f"用户等级: {level['user_level']}")
                    print(f"主播积分: {master_level['anchor_score']}")
                    if master_level['upgrade_score'] > 0:
                        print(f"升级还需: {master_level['upgrade_score']}")
                    
                    # 消费信息
                    print("\n消费信息:")
                    print(f"消费金额: {level['cost']}")
                    print(f"充值金额: {level['rcost']}")
                    
                    # VIP信息
                    print("\nVIP状态:")
                    if level['vip'] == 1:
                        print(f"VIP到期时间: {level['vip_time']}")
                    else:
                        print("不是VIP")
                    if level['svip'] == 1:
                        print(f"SVIP到期时间: {level['svip_time']}")
                    else:
                        print("不是SVIP")
                    
                    # SAN值
                    print(f"\nSAN值: {anchor_data['san']}/12")
                    
                    print("="*50)
                else:
                    print("未找到主播信息")
            else:
                print(f"获取主播信息失败：{data['message']}")
                
        except Exception as e:
            print(f"获取主播信息时出错: {str(e)}")

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

def send_old_fan_message(up_mid: str, content: str, cookies: Dict) -> bool:
    """发��老粉计划留言
    
    Args:
        up_mid (str): UP主的UID
        content (str): 留言内容
        cookies (Dict): cookies信息
        
    Returns:
        bool: 是否发送成功
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://space.bilibili.com',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        # 获取csrf令牌
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return False
            
        # 构造请求��据
        data = {
            'aid': '',
            'up_mid': up_mid,
            'source': '4',
            'scene': '105',
            'content': content,
            'csrf': csrf
        }
        
        # 发送请求
        url = 'https://api.bilibili.com/x/v1/contract/add_message'
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print(f"\n{result['data']['success_toast']}")
            return True
        else:
            error_messages = {
                -101: "账号未登录",
                -111: "csrf校验失��",
                -400: "请求错误",
                158005: "您跟up主还不是契约关系，请先加入老粉计划"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"\n发送留言失败：{error_msg}")
            return False
            
    except Exception as e:
        print(f"\n发送留言时出错: {str(e)}")
        return False

def join_old_fan_plan(up_mid: str, cookies: Dict) -> bool:
    """加入UP主的老粉计划"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://space.bilibili.com',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return False
            
        data = {
            'aid': '',
            'up_mid': up_mid,
            'source': '4',
            'scene': '105',
            'platform': 'web',
            'mobi_app': 'pc',
            'csrf': csrf
        }
        
        url = 'https://api.bilibili.com/x/v1/contract/add_contract'
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print("\n成功加入老粉计划！")
            if result['data']['allow_message']:
                print(f"\n{result['data']['input_title']}")
                choice = input("\n是否发送留言？(y/n) [n]: ").lower()
                if choice == 'y':
                    message = input(f"请输入要���送的留言 [默认: {result['data']['input_text']}]: ").strip()
                    if not message:
                        message = result['data']['input_text']
                    send_old_fan_message(up_mid, message, cookies)
            return True
        else:
            error_messages = {
                -101: "账号未登录",
                -111: "csrf校验失败",
                -400: "请���错误",
                158001: "不满足��入条件",
                158002: "已经是老粉了",
                158003: "UP主未开通老粉计划",
                158004: "UP主暂未达到开通条件"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"\n加入老粉计划失败：{error_msg}")
            return False
            
    except Exception as e:
        print(f"\n加入老粉计划时出错: {str(e)}")
        return False

def check_follow_status(up_mid: str, cookies: Dict) -> bool:
    """检查是否关注了UP主
    
    Args:
        up_mid (str): UP主的UID
        cookies (Dict): cookies信息
        
    Returns:
        bool: 是否已关注
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://space.bilibili.com',
    }
    
    try:
        # 获取关注状态
        url = f'https://api.bilibili.com/x/relation/stat?vmid={up_mid}'
        response = requests.get(url, cookies=cookies, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            # 获取UP主信息
            info_url = f'https://api.bilibili.com/x/space/acc/info?mid={up_mid}'
            info_response = requests.get(info_url, headers=headers)
            info_data = info_response.json()
            
            if info_data['code'] == 0:
                up_info = info_data['data']
                print(f"\nUP主信息:")
                print(f"名称: {up_info['name']}")
                print(f"等级: LV{up_info['level']}")
                if up_info['official']['title']:
                    print(f"认证信息: {up_info['official']['title']}")
                
                # 检查关注状态
                relation_url = f'https://api.bilibili.com/x/relation?fid={up_mid}'
                relation_response = requests.get(relation_url, cookies=cookies, headers=headers)
                relation_data = relation_response.json()
                
                if relation_data['code'] == 0:
                    is_followed = relation_data['data']['attribute'] == 1
                    print(f"关���状态: {'已关注' if is_followed else '未关注'}")
                    
                    if not is_followed:
                        print("\n提示: 需要先关注UP主才能加入老粉计划")
                        choice = input("是否现在关注？(y/n) [y]: ").lower()
                        if not choice or choice == 'y':
                            return follow_up(up_mid, cookies)
                    return is_followed
        
        print(f"获取关注状态失败：{data['message']}")
        return False
            
    except Exception as e:
        print(f"检查关注状态时出错: {str(e)}")
        return False

def follow_up(up_mid: str, cookies: Dict) -> bool:
    """关注UP主
    
    Args:
        up_mid (str): UP主的UID
        cookies (Dict): cookies信息
        
    Returns:
        bool: 是否关注成功
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://space.bilibili.com',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return False
            
        data = {
            'fid': up_mid,
            'act': 1,  # 1：关注 2：取消关注
            're_src': 11,
            'csrf': csrf
        }
        
        url = 'https://api.bilibili.com/x/relation/modify'
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print("\n成功关注UP主！")
            return True
        else:
            print(f"\n关注UP主失败：{result['message']}")
            return False
            
    except Exception as e:
        print(f"关注UP主时出错: {str(e)}")
        return False

def report_video(aid: str, tid: str, desc: str, attach: str, cookies: Dict, video_info: dict = None) -> bool:
    """无图片举报视频"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
        'buid': str(random.randint(100000, 999999))  # 随机生成风控代码
    }
    
    try:
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return False
            
        data = {
            'csrf': csrf,
            'aid': aid,
            'tid': tid,
            'desc': desc,
        }
        
        if attach:
            data['attach'] = attach
            
        cookies['Buid'] = headers['buid']
        
        url = 'https://api.bilibili.com/x/web-interface/appeal/v2/submit'
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print("\n举报成功！")
            # 保存举报记录
            if video_info:
                report_info = {
                    'reason': report_types.get(tid, {}).get('name', '未知理由'),
                    'desc': desc,
                    'attach': attach,
                    'is_image': False
                }
                save_report_record(video_info, report_info)
            return True
        else:
            error_messages = {
                -101: "账未登录",
                -111: "csrf校验失败",
                -400: "请求错误",
                -404: "视频不存在",
                78001: "举报理由不合法",
                78002: "举报描述过短",
                78003: "举报描述过长",
                78004: "附件格式不支持",
                78005: "附件数量超限"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"\n举报失败：{error_msg}")
            return False
            
    except Exception as e:
        print(f"\n举报时出错: {str(e)}")
        return False

def report_video_with_image(aid: str, tid: str, desc: str, image_url: str, cookies: Dict, video_info: dict = None) -> bool:
    """带图片举报视频"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
        'buid': str(random.randint(100000, 999999))  # 随机生成风控代码
    }
    
    try:
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return False
            
        data = {
            'csrf': csrf,
            'aid': aid,
            'tid': tid,
            'desc': desc,
            'attach': image_url
        }
            
        cookies['Buid'] = headers['buid']
        
        url = 'https://api.bilibili.com/x/web-interface/appeal/v2/submit'
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            print("\n举报成功！")
            # 保存举报记录
            if video_info:
                report_info = {
                    'reason': report_types.get(tid, {}).get('name', '未知理���'),
                    'desc': desc,
                    'attach': image_url,
                    'is_image': True
                }
                save_report_record(video_info, report_info)
            return True
        else:
            error_messages = {
                -101: "账号未登录",
                -111: "csrf校验失败",
                -400: "请求错误",
                -404: "视频不存在",
                78001: "举报理由不合��",
                78002: "举报描述过短",
                78003: "举报描述过长",
                78004: "附件格式不支持",
                78005: "附件数量超限"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"\n举报失败：{error_msg}")
            return False
            
    except Exception as e:
        print(f"\n举报时出错: {str(e)}")
        return False

def get_report_types() -> dict:
    """获取视频举报类型列表
    
    Returns:
        dict: 举报类型映射表 {tid: {name: str, remark: str, controls: list}}
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    
    try:
        url = 'https://api.bilibili.com/x/web-interface/archive/appeal/tags'
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            report_types = {}
            for item in data['data']:
                report_types[str(item['tid'])] = {
                    'name': item['name'],
                    'remark': item['remark'],
                    'controls': item['controls']
                }
            return report_types
        else:
            print(f"获取举报类型失败：{data['message']}")
            return {}
            
    except Exception as e:
        print(f"获取举报类型时出��: {str(e)}")
        return {}

def show_report_menu(bvid: str, cookies: Dict) -> None:
    """显示举报菜单"""
    try:
        # 获取视频aid
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
        }
        
        video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        response = requests.get(video_url, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            aid = str(data['data']['aid'])
            
            # 获取举报类型
            report_types = get_report_types()
            if not report_types:
                print("\n获取举报类型失败，使用默认类型")
                # 使用默认的举报类型
                report_types = {
                    "2": {"name": "违法违禁", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
                    "3": {"name": "色情低俗", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
                    "5": {"name": "赌博诈骗", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
                    "6": {"name": "血腥暴力", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
                    "7": {"name": "人身攻击", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
                }
            
            print("\n请选择举报理由：")
            for tid, info in report_types.items():
                print(f"{tid}. {info['name']}")
                
            tid = input("\n请选择举报理由编号: ").strip()
                
            if tid in report_types:
                print(f"\n提示: {report_types[tid]['remark']}")
                
                desc = input("\n请输入详细描述（至少10个字）：").strip()
                if len(desc) < 10:
                    print("\n描述太短，至少需要10个字！")
                    return
                
                attach = ""
                # 如果需要额外信息(如撞车举报)
                if report_types[tid]['controls']:
                    for control in report_types[tid]['controls']:
                        if control['required']:
                            value = input(f"\n请输入{control['title']} ({control['placeholder']}): ").strip()
                            if not value:
                                print(f"\n{control['title']}为必填项！")
                                return
                            attach = value
                else:
                    # 普通举报,询问是否需要上传图片
                    print("\n是否上传举报附件图片？")
                    print("1. 上传本地图片")
                    print("2. 直接输入图片URL")
                    print("3. 跳过")
                    
                    upload_choice = input("\n请选择 [3]: ").strip()
                    if not upload_choice:
                        upload_choice = "3"
                    
                    if upload_choice == "1":
                        image_path = input("\n请输入图片文件路径: ").strip()
                        if os.path.exists(image_path):
                            image_url = upload_report_image(image_path, cookies)
                            if image_url:
                                attach = image_url
                            else:
                                print("\n图片上传失败！")
                        else:
                            print("\n找不到图片文件！")
                    elif upload_choice == "2":
                        attach = input("\n请输入图片URL（多个用逗号分隔）：").strip()
                
                # 确认举报
                print("\n举报信息确认：")
                print(f"视频：{bvid}")
                print(f"理由：{report_types[tid]['name']}")
                print(f"描述：{desc}")
                if attach:
                    if report_types[tid]['controls']:
                        print(f"{report_types[tid]['controls'][0]['title']}: {attach}")
                    else:
                        print(f"附件：{attach}")
                    
                confirm = input("\n确认提交举报？(y/n) [n]: ").lower()
                if confirm == 'y':
                    if report_types[tid]['controls']:
                        # 特殊举报(如撞车)不需要上传图片
                        report_video(aid, tid, desc, attach, cookies)
                    else:
                        # 普通举报
                        report_video_with_image(aid, tid, desc, attach, cookies)
            else:
                print("\n无效的举报理由编号！")
        else:
            print(f"\n获取视频信息失败：{data['message']}")
            
    except Exception as e:
        print(f"\n显示举报菜单时出错: {str(e)}")

def upload_report_image(image_path: str, cookies: Dict) -> str:
    """上传举报附件图片"""
    try:
        # 复制图片到举报图片文件夹
        image_dir = os.path.join("举报", "图片")
        image_name = f"{time.strftime('%Y-%m-%d %H-%M-%S')}_{os.path.basename(image_path)}"
        new_image_path = os.path.join(image_dir, image_name)
        
        import shutil
        shutil.copy2(image_path, new_image_path)
        print(f"\n图片已保存到: {new_image_path}")
        
        # 上传图片到B站
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
        }
        
        csrf = cookies.get('bili_jct')
        if not csrf:
            print("错误：无法获取csrf令牌！")
            return ""
            
        with open(new_image_path, 'rb') as f:
            image_data = f.read()
            base64_data = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"
        
        data = {
            'csrf': csrf,
            'cover': base64_data
        }
        
        url = 'https://member.bilibili.com/x/vu/web/cover/up'
        params = {'ts': int(time.time() * 1000)}
        response = requests.post(url, params=params, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        if result['code'] == 0:
            return result['data']['url']
        else:
            error_messages = {
                -101: "账号未登录",
                -111: "csrf校验失败",
                -400: "请求错误"
            }
            error_msg = error_messages.get(result['code'], result['message'])
            print(f"上传图片失败：{error_msg}")
            return ""
            
    except Exception as e:
        print(f"上传图片时出错: {str(e)}")
        return ""

def search_videos(keyword: str, cookies: Dict, page: int = 1, order: str = 'totalrank') -> list:
    """搜索视频"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://search.bilibili.com',
    }
    
    try:
        # 构造基础参数
        params = {
            'keyword': keyword,
            'page': page,
            'order': order,
            'search_type': 'video',
            'tids': 0,
            'duration': 0,
        }
        
        # 尝试添加WBI签名，传入cookies
        try:
            signed_params = encode_wbi(params, cookies)  # 确保传入cookies
            use_wbi = True
        except:
            # WBI签名失败，使用普通搜索
            signed_params = params
            use_wbi = False
            print("WBI签名获取失败，使用普通搜索模式")
        
        url = 'https://api.bilibili.com/x/web-interface/search/type'
        response = requests.get(url, params=signed_params, cookies=cookies, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            if 'result' in data['data']:
                results = []
                for item in data['data']['result']:
                    if item['type'] == 'video':
                        video_info = {
                            'title': re.sub(r'<.*?>', '', item['title']),
                            'bvid': item['bvid'],
                            'aid': item['aid'],
                            'author': item['author'],
                            'mid': item['mid'],
                            'play': item['play'],
                            'favorites': item['favorites'],
                            'duration': item['duration'],
                            'description': item['description'],
                            'pubdate': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['pubdate'])),
                            'tag': item['tag']
                        }
                        results.append(video_info)
                return results
            else:
                print("未找到相关视频")
                return []
        else:
            print(f"搜索失败：{data['message']}")
            return []
            
    except Exception as e:
        print(f"搜索时出错: {str(e)}")
        print("错误详细信息:")
        import traceback
        traceback.print_exc()
        return []

def show_search_menu(cookies: Dict) -> None:  # 添加cookies参数
    """显示搜索菜单"""
    print("\n=== 视频搜索 ===")
    print("排序方式:")
    print("1. 综合排序")
    print("2. 最多点击")
    print("3. 最新发布")
    print("4. 最多弹幕")
    print("5. 最多收藏")
    
    order_map = {
        '1': 'totalrank',
        '2': 'click',
        '3': 'pubdate',
        '4': 'dm',
        '5': 'stow'
    }
    
    keyword = input("\n请输入搜索关键词: ").strip()
    if not keyword:
        print("搜索关键词不能为空！")
        return
        
    order = input("请选择排序方式 [1]: ").strip()
    if not order:
        order = '1'
    
    if order not in order_map:
        print("无效的排序方式，使用默认排序")
        order = '1'
        
    page = input("请输入页码 [1]: ").strip()
    if not page or not page.isdigit():
        page = 1
    else:
        page = int(page)
        
    results = search_videos(keyword, cookies, page, order_map[order])  # 传入cookies
    
    if results:
        print(f"\n找到 {len(results)} 个视频:")
        print("="*50)
        
        for i, video in enumerate(results, 1):
            print(f"{i}. {video['title']}")
            print(f"   UP主: {video['author']}")
            print(f"   播放: {video['play']} | 收藏: {video['favorites']} | 时长: {video['duration']}")
            print(f"   发布时间: {video['pubdate']}")
            print(f"   BV号: {video['bvid']}")
            print(f"   标签: {video['tag']}")
            print(f"   简介: {video['description'][:100]}..." if len(video['description']) > 100 else f"   简介: {video['description']}")
            print("-"*50)
            
        while True:
            choice = input("\n请选择要操作的视频序号 (输入q返回): ").strip().lower()
            if choice == 'q':
                break
                
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                video = results[int(choice)-1]
                print("\n请选择操作:")
                print("1. 下载音频")
                print("2. 获取弹幕")
                print("3. 获取评论")
                print("4. 举报视频")
                print("5. ���回")
                
                op = input("\n请选择 [1]: ").strip()
                if not op:
                    op = "1"
                    
                if op == "1":
                    download_audio(video['bvid'], cookies)
                elif op == "2":
                    # 获取视频cid
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Referer': 'https://www.bilibili.com',
                    }
                    video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={video["bvid"]}'
                    response = requests.get(video_url, headers=headers)
                    data = response.json()
                    if data['code'] == 0:
                        cid = data['data']['cid']
                        get_danmaku(cid, video['bvid'], 1, cookies)
                elif op == "3":
                    get_hot_comments(video['bvid'])
                elif op == "4":
                    show_report_menu(video['bvid'], cookies)
            else:
                print("无效的选择！")
    
    input("\n按回车继续...")

def batch_report_videos(cookies: Dict) -> None:
    """批量举报视频"""
    print("\n=== 批量举报视频 ===")
    
    # 1. 先搜索视频
    print("排序方式:")
    print("1. 综合排序")
    print("2. 最多点击")
    print("3. 最新发布")
    print("4. 最多弹幕")
    print("5. 最多收藏")
    
    order_map = {
        '1': 'totalrank',
        '2': 'click',
        '3': 'pubdate',
        '4': 'dm',
        '5': 'stow'
    }
    
    keyword = input("\n请输入搜索关键词: ").strip()
    if not keyword:
        print("搜索键词不能为！")
        return
        
    order = input("请选择排序方式 [1]: ").strip()
    if not order:
        order = '1'
    
    if order not in order_map:
        print("无效的排序方式，使用默认排序")
        order = '1'
        
    page = input("请输入页码 [1]: ").strip()
    if not page or not page.isdigit():
        page = 1
    else:
        page = int(page)
        
    results = search_videos(keyword, page, order_map[order])
    
    if not results:
        return
        
    # 2. 显示搜索结果并让用户选择要举报的视频
    print(f"\n找到 {len(results)} 个视频:")
    print("="*50)
    
    for i, video in enumerate(results, 1):
        print(f"{i}. {video['title']}")
        print(f"   UP主: {video['author']}")
        print(f"   播放: {video['play']} | 收藏: {video['favorites']} | 时长: {video['duration']}")
        print(f"   发布时间: {video['pubdate']}")
        print(f"   BV号: {video['bvid']}")
        print(f"   标签: {video['tag']}")
        print(f"   简介: {video['description'][:100]}..." if len(video['description']) > 100 else f"   简介: {video['description']}")
        print("-"*50)
    
    print("\n请选择要举报的视频序号（用空格分隔，例如：1 3 5）")
    print("支持范围选择（例如：1-5 7 9-11）")
    choice = input("请选择: ").strip()
    
    selected_videos = set()
    for part in choice.split():
        if '-' in part:
            start, end = map(int, part.split('-'))
            selected_videos.update(range(start, end +1))
        else:
            if part.isdigit():
                selected_videos.add(int(part))
    
    # 过滤无效的序号
    valid_videos = sorted([i for i in selected_videos if 1 <= i <= len(results)])
    
    if not valid_videos:
        print("未选择��效的视频！")
        return
    
    # 3. 获取举报类型
    report_types = get_report_types()
    if not report_types:
        print("\n获取举报类型失败，使用默认类型")
        report_types = {
            "2": {"name": "违法违禁", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
            "3": {"name": "色情低俗", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
            "5": {"name": "赌博诈骗", "remark": "为帮助审���人员更快处理��补充违规内容出现位置", "controls": None},
            "6": {"name": "血腥暴力", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
            "7": {"name": "人身攻击", "remark": "为帮助审核人员更快处理，补充违规内容出现位置", "controls": None},
        }
    
    print("\n请选择举报理由：")
    for tid, info in report_types.items():
        print(f"{tid}. {info['name']}")
        
    tid = input("\n请选择举报理由编号: ").strip()
    
    if tid not in report_types:
        print("\n无效的举报理由编号！")
        return
    
    print(f"\n提示: {report_types[tid]['remark']}")
    
    desc = input("\n请输入详细描述（至少10个字）：").strip()
    if len(desc) < 10:
        print("\n描述太短，至少需要10个字！")
        return
    
    attach = ""
    # 如果需要额外信息(如撞车举报)
    if report_types[tid]['controls']:
        for control in report_types[tid]['controls']:
            if control['required']:
                value = input(f"\n请输入{control['title']} ({control['placeholder']}): ").strip()
                if not value:
                    print(f"\n{control['title']}为必填项！")
                    return
                attach = value
    else:
        # 普通举报,询问是否需要上传图片
        print("\n是否上传举报附件图片？")
        print("1. 上传本地图片")
        print("2. 直接输入图片URL")
        print("3. 跳过")
        
        upload_choice = input("\n请选择 [3]: ").strip()
        if not upload_choice:
            upload_choice = "3"
        
        if upload_choice == "1":
            image_path = input("\n请输入图片文件路径: ").strip()
            if os.path.exists(image_path):
                image_url = upload_report_image(image_path, cookies)
                if image_url:
                    attach = image_url
                else:
                    print("\n图片上传失败！")
            else:
                print("\n找不到图片文件！")
        elif upload_choice == "2":
            attach = input("\n请输入图片URL（多个用逗号分隔）：").strip()
    
    # 4. 确认并执行批量举报
    print("\n以下视频将被举报:")
    for i in valid_videos:
        video = results[i-1]
        print(f"- {video['title']} (BV号: {video['bvid']}")
    print(f"\n举报理由: {report_types[tid]['name']}")
    print(f"描述: {desc}")
    if attach:
        if report_types[tid]['controls']:
            print(f"{report_types[tid]['controls'][0]['title']}: {attach}")
        else:
            print(f"附件: {attach}")
    
    confirm = input("\n确认提交举报？(y/n) [n]: ").lower()
    if confirm == 'y':
        success_count = 0
        fail_count = 0
        
        # 创建进度条
        with tqdm(total=len(valid_videos), desc="举报进度") as pbar:
            for i in valid_videos:
                video = results[i-1]
                try:
                    if report_types[tid]['controls']:
                        # 特殊举报(如撞车)不需要上传图片
                        if report_video(str(video['aid']), tid, desc, attach, cookies):
                            success_count += 1
                        else:
                            fail_count += 1
                    else:
                        # 普通举报
                        if report_video_with_image(str(video['aid']), tid, desc, attach, cookies):
                            success_count += 1
                        else:
                            fail_count += 1
                except Exception as e:
                    print(f"\n举报视频 {video['bvid']} 时出错: {str(e)}")
                    fail_count += 1
                
                pbar.update(1)
                # 添加延时，避免请求过快
                time.sleep(2)
        
        print(f"\n批量举报完成！成功: {success_count}, 失败: {fail_count}")

def save_report_record(video_info: dict, report_info: dict) -> None:
    """保存举报记录
    
    Args:
        video_info (dict): 视频信息
        report_info (dict): 举报信息
    """
    try:
        record_dir = os.path.join("举报", "记录")
        filename = f"{time.strftime('%Y-%m-%d %H-%M-%S')} {video_info['bvid']}.txt"
        filepath = os.path.join(record_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("视频信息:\n")
            f.write(f"标题: {video_info['title']}\n")
            f.write(f"BV号: {video_info['bvid']}\n")
            f.write(f"AV号: {video_info['aid']}\n")
            f.write(f"UP主: {video_info['author']}\n")
            f.write(f"发布时间: {video_info['pubdate']}\n")
            f.write("\n举报信息:\n")
            f.write(f"举报理由: {report_info['reason']}\n")
            f.write(f"详细描述: {report_info['desc']}\n")
            if report_info.get('attach'):
                if report_info.get('is_image'):
                    f.write(f"附件图片: {report_info['attach']}\n")
                else:
                    f.write(f"附加信息: {report_info['attach']}\n")
            f.write(f"举报时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        print(f"\n举报记录已保存: {filepath}")
        
    except Exception as e:
        print(f"保存举报记录时出错: {str(e)}")

def get_wbi_keys(cookies: Dict = None) -> tuple:
    """获取最新的 img_key 和 sub_key，带缓存机制
    
    Args:
        cookies (Dict): cookies信息
        
    Returns:
        tuple: (img_key, sub_key)
    """
    cache_file = os.path.join("举报", "wbi_cache.json")
    
    try:
        # 检查缓存是否存在且未过期
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                # 检查缓存是否在24小时内
                if time.time() - cache['timestamp'] < 24 * 3600:
                    return cache['img_key'], cache['sub_key']
        
        # 缓存不存在或已过期，重新获取
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
        }
        
        url = 'https://api.bilibili.com/x/web-interface/nav'
        # 添加cookies参数
        response = requests.get(url, cookies=cookies, headers=headers)
        data = response.json()
        
        if data['code'] == 0:
            img_url = data['data']['wbi_img']['img_url']
            sub_url = data['data']['wbi_img']['sub_url']
            
            img_key = os.path.splitext(os.path.basename(img_url))[0]
            sub_key = os.path.splitext(os.path.basename(sub_url))[0]
            
            # 保存到缓存
            cache_data = {
                'img_key': img_key,
                'sub_key': sub_key,
                'timestamp': time.time()
            }
            
            # 确保缓存目录存在
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            return img_key, sub_key
        else:
            print(f"获取WBI keys失败: {data['message']}")
            return None, None
            
    except Exception as e:
        print(f"获取WBI keys时出错: {str(e)}")
        return None, None

def get_mixin_key(raw_key: str) -> str:
    """生成 mixin_key
    
    Args:
        raw_key (str): img_key + sub_key 拼接的字符串
        
    Returns:
        str: mixin_key
    """
    MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
    ]
    
    # 对raw_key按照MIXIN_KEY_ENC_TAB的索引进行重排
    mixin_key = ''
    for i in MIXIN_KEY_ENC_TAB:
        if i < len(raw_key):
            mixin_key += raw_key[i]
            
    # 截取前32位
    return mixin_key[:32]

def encode_wbi(params: dict, cookies: Dict = None) -> dict:
    """为请求参数进行WBI签名
    
    Args:
        params (dict): 原始请求参数
        cookies (Dict): cookies信息
        
    Returns:
        dict: 加入w_rid和wts的新参数
    """
    # 获取img_key和sub_key，传入cookies
    img_key, sub_key = get_wbi_keys(cookies)  # 确保传入cookies
    if not img_key or not sub_key:
        return params
    
    # 生成mixin_key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # 添加wts参数
    wts = str(int(time.time()))
    params['wts'] = wts
    
    # 按键名升序排序并拼接参数
    sorted_params = dict(sorted(params.items()))
    query = []
    for k, v in sorted_params.items():
        # URL编码,需要大写
        query.append(f"{k}={requests.utils.quote(str(v), safe='').upper()}")
    query = '&'.join(query)
    
    # 计算w_rid
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    # 将w_rid和wts添加到原始参数中
    params['w_rid'] = w_rid
    
    return params

if __name__ == "__main__":
    try:
        # 检查必要的文件和文件夹
        if not os.path.exists('cookies.txt'):
            print("错误：找不到cookies.txt文件！")
            print("请确保cookies.txt文件存在且包含有效的cookies信息")
            input("\n按回车键退出...")
            exit(1)
            
        # 检查是否能导入必要模块
        try:
            import google.protobuf.text_format as text_format
            from bilibili.community.service.dm.v1 import dm_pb2 as Danmaku
        except ImportError as e:
            print("错误：缺少必要的模块！")
            print(f"导入错误: {str(e)}")
            print("\n请确保已安装以下模块：")
            print("1. protobuf")
            print("2. 已编译生成dm_pb2.py文件")
            input("\n按回车键退出...")
            exit(1)
            
        # 运行主程序
        main()
        
    except Exception as e:
        print("\n程序出现错误:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print("\n错误详细信息:")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n" + "="*50)
        input("按回车键退出...")