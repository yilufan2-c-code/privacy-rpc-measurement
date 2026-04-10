"""
实验2：测量是否可以通过请求模式关联同一用户的不同钱包地址

方法论：
1. 创建多个测试钱包地址
2. 通过同一RPC端点发送请求
3. 分析请求的时间模式、参数偏好、响应时间特征
4. 使用机器学习方法检测可区分性
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import random
import numpy as np
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, asdict
from utils.rpc_client import RPCClient

# RPC端点配置（简化版，使用公共端点）
RPC_ENDPOINTS = {
    "PublicNode": "https://ethereum.publicnode.com",
    "Cloudflare": "https://cloudflare-eth.com",
}

# 测试钱包地址（建议使用自己创建的钱包，这里用公开地址演示）
# 注意：实际研究中应该使用自己控制的钱包
TEST_WALLETS = {
    "wallet_A": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # vitalik.eth
    "wallet_B": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",  # Binance
    "wallet_C": "0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a",  # 知名地址
}

# 不同的RPC方法，用于构建指纹
RPC_METHODS = [
    ('eth_getBalance', 'latest'),
    ('eth_getTransactionCount', 'latest'),
    ('eth_getBalance', '0x1000000'),  # 指定区块
    ('eth_getBalance', '0x2000000'),
]

@dataclass
class RequestFingerprint:
    """请求指纹特征"""
    wallet_id: str
    timestamp: float
    method: str
    param_hash: int
    response_time_ms: float
    consecutive_request_interval: float
    hour_of_day: int
    weekday: int

class FingerprintAnalyzer:
    """地址指纹分析器"""
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.client = RPCClient(rpc_url)
        self.fingerprints: List[RequestFingerprint] = []
    
    def generate_requests(self, wallet_id: str, address: str, 
                          num_requests: int = 50) -> List[RequestFingerprint]:
        """
        为特定钱包生成请求序列
        
        模拟真实用户行为：随机间隔、混合方法
        """
        fingerprints = []
        last_time = time.time()
        
        for i in range(num_requests):
            # 随机选择RPC方法
            method, block = random.choice(RPC_METHODS)
            
            # 随机间隔（模拟人类行为）
            if i > 0:
                interval = random.expovariate(0.5)  # 平均2秒间隔
                time.sleep(min(interval, 5))
            
            current_time = time.time()
            interval_since_last = current_time - last_time if i > 0 else 0
            
            try:
                if method == 'eth_getBalance':
                    result = self.client.get_balance(address, block)
                elif method == 'eth_getTransactionCount':
                    result = self.client.get_transaction_count(address, block)
                else:
                    result = None
                
                # 获取响应时间
                if self.client.request_logs:
                    response_time = self.client.request_logs[-1].response_time_ms
                else:
                    response_time = 0
                
                # 计算参数哈希（简化特征）
                param_str = f"{method}_{block}_{address[:10]}"
                param_hash = hash(param_str) % 10000
                
                fingerprint = RequestFingerprint(
                    wallet_id=wallet_id,
                    timestamp=current_time,
                    method=method,
                    param_hash=param_hash,
                    response_time_ms=response_time,
                    consecutive_request_interval=interval_since_last,
                    hour_of_day=time.localtime(current_time).tm_hour,
                    weekday=time.localtime(current_time).tm_wday
                )
                fingerprints.append(fingerprint)
                
            except Exception as e:
                print(f"  Request failed: {e}")
            
            last_time = current_time
        
        return fingerprints
    
    def extract_features(self, fingerprints: List[RequestFingerprint]) -> np.ndarray:
        """
        从指纹列表中提取特征向量
        
        特征包括：
        - 平均响应时间
        - 响应时间方差
        - 平均请求间隔
        - 间隔方差
        - 方法分布熵
        - 时间段偏好
        """
        if not fingerprints:
            return np.zeros(10)
        
        response_times = [f.response_time_ms for f in fingerprints]
        intervals = [f.consecutive_request_interval for f in fingerprints if f.consecutive_request_interval > 0]
        methods = [f.method for f in fingerprints]
        
        # 统计特征
        features = []
        
        # 响应时间特征
        features.append(np.mean(response_times) if response_times else 0)
        features.append(np.std(response_times) if len(response_times) > 1 else 0)
        features.append(np.percentile(response_times, 95) if response_times else 0)
        
        # 间隔特征
        features.append(np.mean(intervals) if intervals else 0)
        features.append(np.std(intervals) if len(intervals) > 1 else 0)
        
        # 方法分布（计算熵）
        method_counts = defaultdict(int)
        for m in methods:
            method_counts[m] += 1
        total = len(methods)
        entropy = -sum((c/total) * np.log(c/total) for c in method_counts.values() if c > 0)
        features.append(entropy)
        
        # 方法多样性
        features.append(len(set(methods)) / len(RPC_METHODS))
        
        # 时间段偏好（小时集中度）
        hours = [f.hour_of_day for f in fingerprints]
        if hours:
            hour_mode = max(set(hours), key=hours.count)
            hour_concentration = hours.count(hour_mode) / len(hours)
        else:
            hour_concentration = 0
        features.append(hour_concentration)
        
        # 工作日 vs 周末比例
        weekdays = [1 if f.weekday < 5 else 0 for f in fingerprints]
        weekday_ratio = sum(weekdays) / len(weekdays) if weekdays else 0
        features.append(weekday_ratio)
        
        # 稳定性特征
        features.append(np.std(response_times) / (np.mean(response_times) + 0.001))  # CV
        
        return np.array(features)
    
    def run_linkage_experiment(self, requests_per_wallet: int = 30) -> Dict:
        """
        运行地址关联实验
        
        收集多个钱包的请求指纹，分析是否可以区分/关联
        """
        print("=" * 60)
        print("Fingerprint Analysis - Running linkage experiment...")
        print("=" * 60)
        
        all_fingerprints = []
        
        for wallet_id, address in TEST_WALLETS.items():
            print(f"\nCollecting fingerprints for {wallet_id} ({address[:10]}...)")
            fingerprints = self.generate_requests(wallet_id, address, requests_per_wallet)
            all_fingerprints.extend(fingerprints)
            print(f"  Collected {len(fingerprints)} fingerprints")
        
        # 提取特征矩阵
        features_by_wallet = defaultdict(list)
        for fp in all_fingerprints:
            # 这里简化处理，实际应该使用滑动窗口
            # 为演示，直接使用单点特征
            features_by_wallet[fp.wallet_id].append([
                fp.response_time_ms,
                fp.consecutive_request_interval,
                fp.hour_of_day,
                hash(fp.method) % 100
            ])
        
        # 计算钱包间特征相似度
        from scipy.spatial.distance import cosine
        
        wallet_features = {}
        for wallet_id, features in features_by_wallet.items():
            # 特征聚合
            features_array = np.array(features)
            wallet_features[wallet_id] = np.mean(features_array, axis=0)
        
        # 计算相似度矩阵
        wallet_ids = list(wallet_features.keys())
        similarity_matrix = np.zeros((len(wallet_ids), len(wallet_ids)))
        
        for i, w1 in enumerate(wallet_ids):
            for j, w2 in enumerate(wallet_ids):
                f1 = wallet_features[w1]
                f2 = wallet_features[w2]
                # 余弦相似度
                sim = 1 - cosine(f1, f2) if np.linalg.norm(f1) > 0 and np.linalg.norm(f2) > 0 else 0
                similarity_matrix[i, j] = sim
        
        # 分析结果
        same_wallet_similarity = np.mean([similarity_matrix[i, i] for i in range(len(wallet_ids))])
        cross_wallet_similarity = []
        for i in range(len(wallet_ids)):
            for j in range(len(wallet_ids)):
                if i != j:
                    cross_wallet_similarity.append(similarity_matrix[i, j])
        cross_wallet_similarity = np.mean(cross_wallet_similarity) if cross_wallet_similarity else 0
        
        linkage_possible = same_wallet_similarity > cross_wallet_similarity + 0.1
        
        results = {
            'similarity_matrix': similarity_matrix.tolist(),
            'wallet_ids': wallet_ids,
            'same_wallet_similarity': float(same_wallet_similarity),
            'cross_wallet_similarity': float(cross_wallet_similarity),
            'linkage_possible': linkage_possible,
            'confidence': float(abs(same_wallet_similarity - cross_wallet_similarity))
        }
        
        return results

def main():
    """主函数"""
    print("Fingerprint Analysis Tool")
    print("=" * 40)
    
    # 选择第一个可用的RPC
    rpc_url = list(RPC_ENDPOINTS.values())[0]
    
    analyzer = FingerprintAnalyzer(rpc_url)
    results = analyzer.run_linkage_experiment(requests_per_wallet=20)
    
    # 保存结果
    output_file = 'data/raw/fingerprint_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Same-wallet similarity: {results['same_wallet_similarity']:.3f}")
    print(f"Cross-wallet similarity: {results['cross_wallet_similarity']:.3f}")
    print(f"Linkage possible: {'YES ⚠️' if results['linkage_possible'] else 'NO ✅'}")
    print(f"Confidence score: {results['confidence']:.3f}")
    
    if results['linkage_possible']:
        print("\n⚠️  Potential privacy leakage detected!")
        print("   Different wallets using same RPC may be linkable.")
    else:
        print("\n✅ No strong evidence of address linkage.")
    
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
