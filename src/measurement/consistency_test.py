"""
实验3：测量不同RPC提供商返回数据的一致性

方法论：
1. 向多个RPC提供商发送相同请求
2. 比较响应是否一致
3. 检测潜在的审查或数据伪造
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from utils.rpc_client import RPCClient

# 主要RPC端点（需要替换API Key）
RPC_ENDPOINTS = {
    "Infura": "https://mainnet.infura.io/v3/010a6b4946bb486b98f75a50d7b5a1ef",
    "Alchemy": "https://eth-mainnet.g.alchemy.com/v2/4rsua1CyrIDRKW8UEE2-b",
    "Ankr": "https://rpc.ankr.com/eth",
    "Cloudflare": "https://cloudflare-eth.com",
    "PublicNode": "https://ethereum.publicnode.com",
}

# 测试用交易哈希（知名交易）
TEST_TRANSACTIONS = [
    "0x15f12e2f3b8a4a3b2c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7",
    "0x1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
]

# 测试区块号
TEST_BLOCKS = ["latest", "0x1000000", "0x1500000"]

class ConsistencyTester:
    """跨RPC提供商一致性测试器"""
    
    def __init__(self):
        self.clients: Dict[str, RPCClient] = {}
        self.results: Dict[str, Any] = {}
    
    def initialize_clients(self):
        """初始化所有RPC客户端"""
        for name, url in RPC_ENDPOINTS.items():
            if "YOUR_" not in url:  # 跳过未配置的
                self.clients[name] = RPCClient(url)
                print(f"Initialized: {name}")
    
    def test_balance_consistency(self, address: str) -> Dict:
        """测试余额查询的一致性"""
        print(f"\nTesting balance consistency for {address[:10]}...")
        
        results = {}
        for name, client in self.clients.items():
            try:
                balance = client.get_balance(address)
                results[name] = {
                    'balance_wei': balance,
                    'balance_eth': balance / 1e18,
                    'success': True
                }
            except Exception as e:
                results[name] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def test_block_consistency(self, block_number: str) -> Dict:
        """测试区块数据的一致性"""
        print(f"\nTesting block consistency for block {block_number}...")
        
        results = {}
        for name, client in self.clients.items():
            try:
                # 获取区块哈希
                block = client.send_request('eth_getBlockByNumber', [block_number, False])
                if 'result' in block and block['result']:
                    results[name] = {
                        'block_hash': block['result'].get('hash'),
                        'block_number': int(block['result'].get('number', '0x0'), 16),
                        'timestamp': int(block['result'].get('timestamp', '0x0'), 16),
                        'success': True
                    }
                else:
                    results[name] = {'success': False, 'error': 'Block not found'}
            except Exception as e:
                results[name] = {'success': False, 'error': str(e)}
        
        return results
    
    def analyze_consistency(self, results: Dict) -> Dict:
        """
        分析一致性
        
        检测：
        - 多数共识：哪个结果与大多数一致
        - 离群者：哪个提供商返回异常数据
        """
        if not results:
            return {'consensus_reached': False, 'outliers': []}
        
        # 收集成功的响应
        successful = {k: v for k, v in results.items() if v.get('success')}
        
        if len(successful) < 2:
            return {'consensus_reached': False, 'outliers': list(results.keys())}
        
        # 对于余额测试，比较数值
        if 'balance_wei' in list(successful.values())[0]:
            balances = {k: v['balance_wei'] for k, v in successful.items()}
            unique_balances = {}
            for k, b in balances.items():
                if b not in unique_balances:
                    unique_balances[b] = []
                unique_balances[b].append(k)
            
            # 多数派
            majority_value = max(unique_balances.items(), key=lambda x: len(x[1]))
            majority = majority_value[1]
            outliers = [k for k in successful.keys() if k not in majority]
            
            return {
                'consensus_reached': len(majority) > len(successful) / 2,
                'outliers': outliers,
                'majority_providers': majority,
                'majority_value': majority_value[0],
                'consensus_type': 'balance'
            }
        
        # 对于区块测试，比较区块哈希
        if 'block_hash' in list(successful.values())[0]:
            hashes = {k: v['block_hash'] for k, v in successful.items()}
            unique_hashes = {}
            for k, h in hashes.items():
                if h not in unique_hashes:
                    unique_hashes[h] = []
                unique_hashes[h].append(k)
            
            majority_value = max(unique_hashes.items(), key=lambda x: len(x[1]))
            majority = majority_value[1]
            outliers = [k for k in successful.keys() if k not in majority]
            
            return {
                'consensus_reached': len(majority) > len(successful) / 2,
                'outliers': outliers,
                'majority_providers': majority,
                'majority_hash': majority_value[0],
                'consensus_type': 'block'
            }
        
        return {'consensus_reached': False, 'outliers': []}
    
    def run_full_test(self) -> List[Dict]:
        """运行完整的测试套件"""
        print("=" * 60)
        print("Cross-Provider Consistency Test")
        print("=" * 60)
        
        self.initialize_clients()
        
        if not self.clients:
            print("\n❌ No RPC clients initialized. Please configure API keys.")
            return []
        
        all_analyses = []
        
        # 测试1：余额一致性
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        balance_results = self.test_balance_consistency(test_address)
        balance_analysis = self.analyze_consistency(balance_results)
        balance_analysis['test_type'] = 'balance'
        balance_analysis['raw_results'] = balance_results
        all_analyses.append(balance_analysis)
        
        # 测试2：区块一致性
        for block in TEST_BLOCKS[:2]:
            block_results = self.test_block_consistency(block)
            block_analysis = self.analyze_consistency(block_results)
            block_analysis['test_type'] = f'block_{block}'
            block_analysis['raw_results'] = block_results
            all_analyses.append(block_analysis)
        
        return all_analyses

def main():
    """主函数"""
    print("Cross-Provider Consistency Test Tool")
    print("=" * 40)
    print("\n⚠️  IMPORTANT:")
    print("1. Replace YOUR_INFURA_KEY and YOUR_ALCHEMY_KEY")
    print("2. Some public endpoints may have rate limits")
    
    tester = ConsistencyTester()
    results = tester.run_full_test()
    
    # 保存结果
    output_file = 'data/raw/consistency_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    for result in results:
        if result.get('consensus_reached', False):
            status = "✅ CONSENSUS"
            outliers = result.get('outliers', [])
            if outliers:
                status = f"⚠️  PARTIAL - Outliers: {outliers}"
        else:
            status = "🔴 NO CONSENSUS"
        
        print(f"{result.get('test_type', 'unknown')}: {status}")
    
    print(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    main()
