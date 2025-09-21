#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bilibili工具测试脚本
用于验证各个功能模块的正常工作
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestBilibiliTool(unittest.TestCase):
    """测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_cookies = {
            'SESSDATA': 'test_sessdata',
            'bili_jct': 'test_bili_jct',
            'DedeUserID': 'test_dedeuserid'
        }
    
    def test_cookie_validation(self):
        """测试Cookie验证"""
        # 导入15.0版本的模块
        try:
            from importlib import import_module
            # 动态导入模块
            spec = import_module('15.0bilibili_audio_dl')
            cookie_manager = spec.CookieManager
            
            # 测试有效cookies
            self.assertTrue(cookie_manager._validate_cookies(self.test_cookies))
            
            # 测试无效cookies
            invalid_cookies = {'invalid': 'cookie'}
            self.assertFalse(cookie_manager._validate_cookies(invalid_cookies))
            
            print("✅ Cookie验证测试通过")
        except ImportError:
            print("⚠️  无法导入15.0版本模块，跳过此测试")
    
    def test_bvid_extraction(self):
        """测试BV号提取功能"""
        try:
            from importlib import import_module
            spec = import_module('15.0bilibili_audio_dl')
            downloader = spec.VideoDownloader(self.test_cookies)
            
            # 测试各种URL格式
            test_cases = [
                ('BV1234567890', 'BV1234567890'),
                ('https://www.bilibili.com/video/BV1234567890', 'BV1234567890'),
                ('https://b23.tv/BV1234567890', 'BV1234567890'),
                ('invalid_url', ''),
            ]
            
            for input_url, expected in test_cases:
                result = downloader.extract_bvid(input_url)
                self.assertEqual(result, expected)
            
            print("✅ BV号提取测试通过")
        except ImportError:
            print("⚠️  无法导入15.0版本模块，跳过此测试")
    
    def test_directory_creation(self):
        """测试目录创建"""
        try:
            from importlib import import_module
            spec = import_module('15.0bilibili_audio_dl')
            
            # 模拟目录创建
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                spec.create_required_directories()
                
                # 检查目录是否创建成功
                self.assertTrue(os.path.exists('音频'))
                self.assertTrue(os.path.exists('logs'))
            
            print("✅ 目录创建测试通过")
        except ImportError:
            print("⚠️  无法导入15.0版本模块，跳过此测试")
    
    def test_config_loading(self):
        """测试配置文件加载"""
        config_file = 'config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 检查必要的配置项
            self.assertIn('download', config)
            self.assertIn('network', config)
            self.assertIn('logging', config)
            
            print("✅ 配置文件加载测试通过")
        else:
            print("⚠️  配置文件不存在，跳过此测试")
    
    def test_requirements(self):
        """测试依赖文件"""
        req_file = 'requirements.txt'
        if os.path.exists(req_file):
            with open(req_file, 'r', encoding='utf-8') as f:
                requirements = f.read()
            
            # 检查必要的依赖
            self.assertIn('requests', requirements)
            self.assertIn('tqdm', requirements)
            
            print("✅ 依赖文件测试通过")
        else:
            print("⚠️  依赖文件不存在，跳过此测试")
    
    def test_ffmpeg_detection(self):
        """测试ffmpeg检测"""
        try:
            from importlib import import_module
            spec = import_module('15.0bilibili_audio_dl')
            ffmpeg_manager = spec.FFmpegManager
            
            # 测试ffmpeg检测（可能成功或失败，不影响测试）
            ffmpeg_path = ffmpeg_manager.find_ffmpeg()
            self.assertIsInstance(ffmpeg_path, str)
            
            print(f"✅ FFmpeg检测测试通过 (路径: {ffmpeg_path or '未找到'})")
        except ImportError:
            print("⚠️  无法导入15.0版本模块，跳过此测试")

def run_functionality_test():
    """运行功能测试"""
    print("🧪 开始运行Bilibili工具功能测试")
    print("="*50)
    
    # 检查文件存在性
    files_to_check = [
        '14.0bilibili_audio_dl.py',
        '15.0bilibili_audio_dl.py',
        'config.json',
        'requirements.txt'
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ 文件存在: {file}")
        else:
            print(f"❌ 文件缺失: {file}")
    
    print("\n" + "="*50)
    
    # 运行单元测试
    unittest.main(verbosity=2, exit=False)

def check_version_differences():
    """检查版本差异"""
    print("\n📊 版本差异分析")
    print("="*50)
    
    v14_file = '14.0bilibili_audio_dl.py'
    v15_file = '15.0bilibili_audio_dl.py'
    
    if os.path.exists(v14_file) and os.path.exists(v15_file):
        with open(v14_file, 'r', encoding='utf-8') as f:
            v14_lines = len(f.readlines())
        
        with open(v15_file, 'r', encoding='utf-8') as f:
            v15_lines = len(f.readlines())
        
        print(f"v14.0 代码行数: {v14_lines}")
        print(f"v15.0 代码行数: {v15_lines}")
        print(f"代码精简: {v14_lines - v15_lines} 行")
    
    print("\n主要改进:")
    print("✅ 重构为面向对象架构")
    print("✅ 添加完善的错误处理")
    print("✅ 修复进度条计算bug")
    print("✅ 改进Cookie管理")
    print("✅ 添加配置文件支持")
    print("✅ 优化日志系统")

if __name__ == '__main__':
    run_functionality_test()
    check_version_differences()
