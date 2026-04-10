"""
代理池管理器，用于IP轮换和匿名测试
"""
import random
from typing import List, Optional, Dict
import requests
import time

class ProxyManager:
    """管理代理IP池"""
    
    def __init__(self):
        self.proxies: List[str] = []
        self.current_index = 0
        self.proxy_quality: Dict[str, float] = {}
    
    def add_proxy(self, proxy_url: str):
        """添加代理"""
        if proxy_url not in self.proxies:
            self.proxies.append(proxy_url)
            self.proxy_quality[proxy_url] = 1.0
    
    def add_proxies(self, proxy_urls: List[str]):
        """批量添加代理"""
        for proxy in proxy_urls:
            self.add_proxy(proxy)
    
    def get_random_proxy(self) -> Optional[str]:
        """随机获取一个代理"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_round_robin_proxy(self) -> Optional[str]:
        """轮询获取代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def test_proxy(self, proxy_url: str, test_url: str = "https://api.ipify.org?format=json") -> bool:
        """测试代理是否可用"""
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            start = time.time()
            response = requests.get(test_url, proxies=proxies, timeout=10)
            response_time = time.time() - start
            
            if response.status_code == 200:
                self.proxy_quality[proxy_url] = 1.0 / (response_time + 0.1)
                return True
        except Exception:
            self.proxy_quality[proxy_url] = 0
        return False
    
    def get_working_proxies(self, test_url: str = "https://api.ipify.org") -> List[str]:
        """过滤出可用的代理"""
        working = []
        for proxy in self.proxies:
            if self.test_proxy(proxy, test_url):
                working.append(proxy)
        return working
    
    def get_proxy_info(self, proxy_url: str) -> Optional[Dict]:
        """获取代理的地理位置信息"""
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            response = requests.get('https://ipapi.co/json/', proxies=proxies, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

# 免费代理源（仅供测试，生产环境建议使用付费代理）
FREE_PROXY_SOURCES = [
    "http://127.0.0.1:8080",  # 本地代理，需要自行配置
    # 注意：免费代理不稳定，建议使用：
    # - 自己搭建的代理服务器
    # - 付费代理服务（如BrightData、Oxylabs）
]

def get_default_proxy_manager() -> ProxyManager:
    """获取默认配置的代理管理器"""
    pm = ProxyManager()
    for proxy in FREE_PROXY_SOURCES:
        pm.add_proxy(proxy)
    return pm
