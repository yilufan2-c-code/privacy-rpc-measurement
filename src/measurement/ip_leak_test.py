# -*- coding: utf-8 -*-
import sys
import io

# 强制使用UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
"""
实验1：测量RPC提供商是否泄露客户端IP地址
方法论：
1. 通过不同代理IP发送请求
2. 分析响应中是否包含IP相关信息
3. 通过时序分析检测间接泄露
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from typing import Dict, List, Tuple
from collections import defaultdict
from utils.rpc_client import RPCClient
from utils.proxy_manager import ProxyManager, get_default_proxy_manager

# 配置：主流的RPC端点（需要替换为实际API Key）
RPC_ENDPOINTS = {
    "Infura": "https://mainnet.infura.io/v3/010a6b4946bb486b98f75a50d7b5a1ef",
    "Alchemy": "https://eth-mainnet.g.alchemy.com/v2/4rsua1CyrIDRKW8UEE2-b",
    "Ankr": "https://rpc.ankr.com/eth",
    "Cloudflare": "https://cloudflare-eth.com",
    "PublicNode": "https://ethereum.publicnode.com",
}

# 测试钱包地址（公开的知名地址，如Vitalik的捐赠地址）
TEST_ADDRESSES = [
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # vitalik.eth
    "0x00000000219ab540356cBB839Cbe05303d7705Fa",  # 知名合约
    "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",  # Binance热钱包
]

class IPLeakMeasurer:
    """IP泄露测量器"""
    
    def __init__(self, proxy_manager: ProxyManager):
        self.proxy_manager = proxy_manager
        self.results = []
    
    def measure_single_rpc(self, rpc_name: str, rpc_url: str, 
                           address: str, iterations: int = 10) -> Dict:
        """
        测量单个RPC端点的IP泄露情况
        
        Args:
            rpc_name: RPC名称
            rpc_url: RPC URL
            address: 测试地址
            iterations: 每个代理的请求次数
        
        Returns:
            测量结果字典
        """
        results = {
            'rpc_name': rpc_name,
            'rpc_url': rpc_url,
            'tests': []
        }
        
        # 测试1：无代理（基准）
        print(f"  Testing {rpc_name} without proxy...")
        client = RPCClient(rpc_url)
        proxy_results = {'proxy': 'none', 'responses': []}
        
        for i in range(iterations):
            try:
                balance = client.get_balance(address)
                proxy_results['responses'].append({
                    'success': True,
                    'balance': balance,
                    'response_time': client.request_logs[-1].response_time_ms if client.request_logs else 0
                })
            except Exception as e:
                proxy_results['responses'].append({'success': False, 'error': str(e)})
            time.sleep(0.5)  # 避免速率限制
        
        results['tests'].append(proxy_results)
        
        # 测试2：通过不同代理
        proxies = self.proxy_manager.proxies
        if not proxies:
            print(f"  Warning: No proxies configured, skipping proxy tests")
            return results
        
        for proxy in proxies[:3]:  # 限制测试数量
            print(f"  Testing {rpc_name} with proxy {proxy}...")
            client = RPCClient(rpc_url)
            proxy_results = {'proxy': proxy, 'responses': []}
            
            # 先测试代理连通性
            if not self.proxy_manager.test_proxy(proxy):
                print(f"    Proxy {proxy} not working, skipping")
                continue
            
            for i in range(iterations):
                try:
                    balance = client.get_balance(address, proxy=proxy)
                    proxy_results['responses'].append({
                        'success': True,
                        'balance': balance,
                        'response_time': client.request_logs[-1].response_time_ms if client.request_logs else 0
                    })
                except Exception as e:
                    proxy_results['responses'].append({'success': False, 'error': str(e)})
                time.sleep(0.5)
            
            results['tests'].append(proxy_results)
        
        return results
    
    def analyze_ip_leak(self, results: Dict) -> Dict:
        """
        分析IP泄露证据
        
        检测指标：
        1. 直接泄露：响应中包含IP字符串
        2. 间接泄露：不同代理的响应时间模式差异
        3. 速率限制：不同IP是否触发不同的限流行为
        """
        analysis = {
            'has_direct_leak': False,
            'direct_leak_evidence': [],
            'indirect_leak_score': 0.0,
            'rate_limit_differences': False,
            'confidence': 0.0
        }
        
        tests = results.get('tests', [])
        if len(tests) < 2:
            return analysis
        
        # 检查直接泄露
        for test in tests:
            responses = test.get('responses', [])
            for resp in responses:
                # 检查错误消息中是否包含IP
                error = resp.get('error', '')
                if 'ip' in error.lower() or 'address' in error.lower():
                    analysis['has_direct_leak'] = True
                    analysis['direct_leak_evidence'].append(error[:100])
        
        # 分析间接泄露（响应时间差异）
        response_times_by_proxy = []
        for test in tests:
            times = [r.get('response_time', 0) for r in test.get('responses', []) if r.get('success')]
            if times:
                avg_time = sum(times) / len(times)
                response_times_by_proxy.append(avg_time)
        
        if len(response_times_by_proxy) >= 2:
            # 计算变异系数（CV），高CV可能表示IP被识别
            import numpy as np
            cv = np.std(response_times_by_proxy) / (np.mean(response_times_by_proxy) + 0.001)
            # CV > 0.3 表示显著差异
            analysis['indirect_leak_score'] = min(cv, 1.0)
        
        # 综合置信度
        if analysis['has_direct_leak']:
            analysis['confidence'] = 0.95
        elif analysis['indirect_leak_score'] > 0.3:
            analysis['confidence'] = 0.6
        else:
            analysis['confidence'] = 0.1
        
        return analysis
    
    def run_full_measurement(self, iterations_per_proxy: int = 5) -> List[Dict]:
        """运行完整的IP泄露测量"""
        print("=" * 60)
        print("IP Leak Measurement - Starting...")
        print("=" * 60)
        
        all_results = []
        
        for rpc_name, rpc_url in RPC_ENDPOINTS.items():
            print(f"\nMeasuring {rpc_name}...")
            
            for address in TEST_ADDRESSES[:1]:  # 只测第一个地址以节省时间
                result = self.measure_single_rpc(rpc_name, rpc_url, address, iterations_per_proxy)
                analysis = self.analyze_ip_leak(result)
                result['analysis'] = analysis
                all_results.append(result)
                
                # 输出分析结果
                print(f"  Analysis for {rpc_name}:")
                print(f"    Direct leak: {analysis['has_direct_leak']}")
                print(f"    Indirect leak score: {analysis['indirect_leak_score']:.3f}")
                print(f"    Confidence: {analysis['confidence']:.2f}")
        
        return all_results

def main():
    """主函数"""
    print("IP Leak Measurement Tool")
    print("=" * 40)
    print("\n⚠️  IMPORTANT:")
    print("1. Replace YOUR_INFURA_KEY and YOUR_ALCHEMY_KEY in RPC_ENDPOINTS")
    print("2. Configure proxies in proxy_manager.py")
    print("3. For accurate results, use real proxies (not free ones)")
    print("\nStarting measurement in 3 seconds...")
    time.sleep(3)
    
    # 初始化代理管理器
    pm = get_default_proxy_manager()
    
    # 运行测量
    measurer = IPLeakMeasurer(pm)
    results = measurer.run_full_measurement(iterations_per_proxy=3)
    
    # 保存结果
    output_file = 'data/raw/ip_leak_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        analysis = r.get('analysis', {})
        status = "🔴 LEAK DETECTED" if analysis.get('has_direct_leak') or analysis.get('indirect_leak_score', 0) > 0.3 else "🟢 No leak detected"
        print(f"{r['rpc_name']}: {status}")

if __name__ == "__main__":
    main()
