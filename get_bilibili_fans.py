import requests
import json

def get_follower_count(uid):
    """
    获取B站用户的粉丝数
    :param uid: B站用户UID
    :return: 粉丝数
    """
    url = f"https://api.bilibili.com/x/relation/stat?vmid={uid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data["code"] == 0:
            return data["data"]["follower"]
        else:
            return f"获取失败: {data['message']}"
    except Exception as e:
        return f"发生错误: {str(e)}"

if __name__ == "__main__":
    uid = input("请输入B站用户UID: ")
    follower_count = get_follower_count(uid)
    print(f"粉丝数: {follower_count}") 