from flask import Flask, render_template, request, jsonify
import requests
import json
import re
import os
from flask_cors import CORS
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import pickle

app = Flask(__name__)
CORS(app)

# API 配置文件路径
CONFIG_FILE = 'api_config.json'

def load_api_config():
    """加载 API 配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'youtube': '', 'twitter': ''}

def save_api_config(config):
    """保存 API 配置"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_bilibili_info(uid):
    """
    获取B站用户信息
    :param uid: B站用户UID
    :return: 用户信息
    """
    url = f"https://api.bilibili.com/x/web-interface/card?mid={uid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        print("API Response:", json.dumps(data, ensure_ascii=False, indent=2))  # 调试输出
        
        if data["code"] == 0 and "data" in data and "card" in data["data"]:
            card = data["data"]["card"]
            # 直接使用API返回的头像URL
            return {
                "success": True,
                "username": card["name"],
                "avatar": card["face"],  # 直接使用原始URL
                "follower": card["fans"]
            }
        else:
            error_msg = data.get("message", "获取用户信息失败")
            print("Error:", error_msg)  # 调试输出
            return {"success": False, "message": error_msg}
    except Exception as e:
        print("Exception:", str(e))  # 调试输出
        return {"success": False, "message": str(e)}

def get_youtube_info(channel_id):
    """获取 YouTube 频道信息"""
    config = load_api_config()
    api_key = config.get('youtube')
    
    if not api_key:
        return {
            'success': False,
            'message': '请先在配置页面设置 YouTube API 密钥'
        }
    
    try:
        url = f'https://www.googleapis.com/youtube/v3/channels'
        params = {
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': api_key
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data:
            error_message = data['error'].get('message', '未知错误')
            return {
                'success': False,
                'message': f'YouTube API 错误: {error_message}'
            }
        
        if not data.get('items'):
            return {
                'success': False,
                'message': '未找到该 YouTube 频道，请确保输入了正确的频道ID'
            }
        
        channel = data['items'][0]
        return {
            'success': True,
            'username': channel['snippet']['title'],
            'avatar': channel['snippet']['thumbnails']['default']['url'],
            'follower': int(channel['statistics']['subscriberCount'])
        }
    except Exception as e:
        print(f"YouTube API Error: {str(e)}")  # 添加调试输出
        return {
            'success': False,
            'message': f'获取 YouTube 信息失败: {str(e)}'
        }

def get_twitter_info(username):
    """获取 Twitter 用户信息"""
    config = load_api_config()
    api_key = config.get('twitter')
    
    if not api_key:
        return {
            'success': False,
            'message': '请先在配置页面设置 Twitter API 密钥'
        }
    
    try:
        url = f'https://api.twitter.com/2/users/by/username/{username}'
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        params = {
            'user.fields': 'profile_image_url,public_metrics'
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if 'errors' in data:
            return {
                'success': False,
                'message': f'Twitter API 错误: {data["errors"][0]["message"]}'
            }
        
        if not data.get('data'):
            return {
                'success': False,
                'message': '未找到该 Twitter 用户'
            }
        
        user = data['data']
        return {
            'success': True,
            'data': {
                'name': user['name'],
                'avatar': user['profile_image_url'],
                'fans': int(user['public_metrics']['followers_count'])
            }
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'获取 Twitter 信息失败: {str(e)}'
        }

def get_telegram_channel_info(channel_name):
    """爬取Telegram频道订阅数，兼容@和不同单位"""
    # 自动去除@
    channel_name = channel_name.lstrip('@')
    url = f'https://t.me/s/{channel_name}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {'success': False, 'message': '无法访问频道页面'}
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 频道名
        title_tag = soup.find('meta', property='og:title')
        channel_title = title_tag['content'] if title_tag else channel_name
        # 订阅数
        sub_text = soup.find('div', class_='tgme_page_extra')
        if sub_text:
            # 兼容 subscribers 和 members
            match = re.search(r'(\d[\d,\.]*)\s+(subscribers|members)', sub_text.text)
            if match:
                count = match.group(1).replace(',', '').replace('.', '')
                return {
                    'success': True,
                    'username': channel_title,
                    'avatar': '/static/telegram.png',
                    'follower': int(count)
                }
        return {'success': False, 'message': '未能解析订阅数，页面结构可能已变'}
    except Exception as e:
        return {'success': False, 'message': f'爬取失败: {str(e)}'}

def get_telegram_group_info(group_name):
    """爬取Telegram群组成员数"""
    url = f'https://t.me/s/{group_name}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {'success': False, 'message': '无法访问群组页面'}
        soup = BeautifulSoup(resp.text, 'html.parser')
        title_tag = soup.find('meta', property='og:title')
        group_title = title_tag['content'] if title_tag else group_name
        extra = soup.find('div', class_='tgme_page_extra')
        if extra:
            match = re.search(r'(\d[\d,\.]*)\s+members', extra.text)
            if match:
                count = match.group(1).replace(',', '').replace('.', '')
                return {
                    'success': True,
                    'username': group_title,
                    'avatar': '/static/telegram.png',
                    'follower': int(count)
                }
        return {'success': False, 'message': '未能解析成员数'}
    except Exception as e:
        return {'success': False, 'message': f'爬取失败: {str(e)}'}

def get_xiaohongshu_info(user_id):
    """爬取小红书用户粉丝数"""
    url = f'https://www.xiaohongshu.com/user/{user_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {'success': False, 'message': '无法访问小红书主页'}
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 用户名
        title_tag = soup.find('title')
        nickname = title_tag.text.split('的个人主页')[0] if title_tag else user_id
        # 粉丝数（页面结构可能变化，需适配）
        fans = None
        for span in soup.find_all('span'):
            if '粉丝' in span.text:
                match = re.search(r'(\d[\d,\.]*)', span.text)
                if match:
                    fans = int(match.group(1).replace(',', '').replace('.', ''))
                    break
        if fans:
            return {
                'success': True,
                'username': nickname,
                'avatar': '/static/xiaohongshu.png',
                'follower': fans
            }
        return {'success': False, 'message': '未能解析粉丝数'}
    except Exception as e:
        return {'success': False, 'message': f'爬取失败: {str(e)}'}

def get_twitter_followers(username):
    """获取推特用户粉丝数"""
    try:
        # 构建推特用户页面URL
        url = f'https://twitter.com/{username}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 发送请求获取页面内容
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析页面
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找包含粉丝数的元素
        # 注意：由于推特页面结构可能会变化，这里需要根据实际情况调整选择器
        followers_element = soup.find('a', href=re.compile(r'followers'))
        if followers_element:
            followers_text = followers_element.text.strip()
            # 处理粉丝数格式（例如：1.2M, 100K等）
            followers = parse_twitter_number(followers_text)
            print(response.text[:1000])  # 打印前1000字符，检查返回内容
            return followers
        
        return None
    except Exception as e:
        print(f"Error fetching Twitter followers: {str(e)}")
        return None

def parse_twitter_number(number_str):
    """解析推特数字格式（如1.2M, 100K等）"""
    try:
        number_str = number_str.lower().replace(',', '')
        if 'k' in number_str:
            return int(float(number_str.replace('k', '')) * 1000)
        elif 'm' in number_str:
            return int(float(number_str.replace('m', '')) * 1000000)
        else:
            return int(number_str)
    except:
        return 0

def save_cookies(driver, path):
    with open(path, 'wb') as filehandler:
        pickle.dump(driver.get_cookies(), filehandler)

def load_cookies(driver, path):
    if os.path.exists(path):
        with open(path, 'rb') as cookiesfile:
            cookies = pickle.load(cookiesfile)
            for cookie in cookies:
                driver.add_cookie(cookie)

def get_douyin_fans(username):
    url = f'https://www.douyin.com/user/{username}'
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1200,800')
    chrome_options.add_argument('--lang=zh-CN')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://www.douyin.com/')  # 先访问主页以便加载cookie

    # 尝试加载cookie
    cookie_path = 'douyin_cookies.pkl'
    try:
        load_cookies(driver, cookie_path)
        driver.refresh()
        time.sleep(3)
    except Exception as e:
        print("未能加载cookie，需手动扫码登录", e)

    # 如果未登录，手动扫码一次
    if "登录" in driver.page_source or "扫码" in driver.page_source:
        print("请扫码登录抖音...")
        time.sleep(20)  # 给足扫码时间
        save_cookies(driver, cookie_path)
        print("已保存cookie，下次可自动登录")

    driver.get(url)
    time.sleep(5)
    fans = None
    try:
        fans_elem = driver.find_element(By.XPATH, '//span[contains(text(),"粉丝")]/preceding-sibling::span')
        fans = fans_elem.text
    except Exception as e:
        print("未能获取粉丝数，页面结构可能已变或需要登录。", e)
    driver.quit()
    return fans

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config')
def config():
    return render_template('config.html')

@app.route('/get_api_config')
def get_api_config():
    """获取 API 配置"""
    return jsonify(load_api_config())

@app.route('/save_api_config', methods=['POST'])
def save_config():
    """保存 API 配置"""
    try:
        config = request.json
        save_api_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/check_api_status')
def check_api_status():
    """检查 API 状态"""
    config = load_api_config()
    return jsonify({
        'youtube': bool(config.get('youtube')),
        'twitter': bool(config.get('twitter'))
    })

@app.route('/get_followers', methods=['POST'])
def get_followers():
    platform = request.form.get('platform')
    identifier = request.form.get('identifier')
    
    if not platform or not identifier:
        return jsonify({'success': False, 'error': 'Missing platform or identifier'})
    
    try:
        if platform == 'bilibili':
            # 现有的B站查询逻辑
            result = get_bilibili_info(identifier)
            if result['success']:
                return jsonify({
                    'success': True,
                    'username': result['username'],
                    'avatar': result['avatar'],
                    'follower': result['follower']
                })
        elif platform == 'youtube':
            result = get_youtube_info(identifier)
            if result['success']:
                return jsonify({
                    'success': True,
                    'username': result['username'],
                    'avatar': result['avatar'],
                    'follower': result['follower']
                })
        elif platform == 'wechat_mp':
            result = {"success": False, "message": "公众号粉丝数查询暂未实现"}
        elif platform == 'xiaohongshu':
            result = get_xiaohongshu_info(identifier)
        elif platform == 'douyin':
            fans = get_douyin_fans(identifier)
            if fans:
                return jsonify({
                    'success': True,
                    'username': identifier,
                    'avatar': f'https://p3.douyinpic.com/img/{identifier}~c5_300x300.jpg',
                    'follower': fans
                })
            else:
                return jsonify({'success': False, 'message': '抖音粉丝数获取失败'})
        elif platform == 'kuaishou':
            result = {"success": False, "message": "快手粉丝数查询暂未实现"}
        elif platform == 'wechat_video':
            result = {"success": False, "message": "视频号粉丝数查询暂未实现"}
        elif platform == 'twitter':
            # 新增的推特查询逻辑
            followers = get_twitter_followers(identifier)
            if followers is not None:
                return jsonify({
                    'success': True,
                    'username': identifier,
                    'follower': followers,
                    'avatar': f'https://twitter.com/{identifier}/profile_image?size=original'
                })
        else:
            return jsonify({"success": False, "message": "不支持的平台"})
        
        print(f"Platform: {platform}")
        print(f"Identifier: {identifier}")
        print(f"Result: {result}")
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5001) 