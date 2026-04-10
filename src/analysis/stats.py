"""
统计分析模块：生成图表和统计报告
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any
from collections import defaultdict

# 设置中文字体（可选）
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ResultAnalyzer:
    """结果分析器，生成可视化图表"""
    
    def __init__(self, data_dir: str = 'data/raw'):
        self.data_dir = data_dir
        self.results = {}
    
    def load_results(self):
        """加载所有测量结果"""
        files = {
            'ip_leak': 'ip_leak_results.json',
            'fingerprint': 'fingerprint_results.json',
            'consistency': 'consistency_results.json'
        }
        
        for name, filename in files.items():
            path = os.path.join(self.data_dir, filename)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.results[name] = json.load(f)
                print(f"Loaded {name}: {path}")
    
    def plot_ip_leak_results(self, save_dir: str = 'results/figures'):
        """绘制IP泄露结果"""
        if 'ip_leak' not in self.results:
            print("No IP leak results found")
            return
        
        results = self.results['ip_leak']
        os.makedirs(save_dir, exist_ok=True)
        
        # 提取每个RPC的泄露分数
        rpc_names = []
        leak_scores = []
        confidences = []
        
        for r in results:
            rpc_names.append(r.get('rpc_name', 'Unknown'))
            analysis = r.get('analysis', {})
            leak_scores.append(analysis.get('indirect_leak_score', 0))
            confidences.append(analysis.get('confidence', 0))
        
        # 条形图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        colors = ['red' if s > 0.3 else 'green' for s in leak_scores]
        bars = ax1.bar(rpc_names, leak_scores, color=colors)
        ax1.set_ylabel('Indirect Leak Score')
        ax1.set_title('RPC Provider IP Leak Score')
        ax1.set_ylim(0, 1)
        ax1.tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for bar, score in zip(bars, leak_scores):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'{score:.2f}', ha='center', va='bottom')
        
        # 置信度条形图
        bars2 = ax2.bar(rpc_names, confidences, color='skyblue')
        ax2.set_ylabel('Confidence')
        ax2.set_title('Detection Confidence')
        ax2.set_ylim(0, 1)
        ax2.tick_params(axis='x', rotation=45)
        
        for bar, conf in zip(bars2, confidences):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'{conf:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, 'ip_leak_analysis.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_dir}/ip_leak_analysis.png")
    
    def plot_fingerprint_results(self, save_dir: str = 'results/figures'):
        """绘制指纹分析结果"""
        if 'fingerprint' not in self.results:
            print("No fingerprint results found")
            return
        
        results = self.results['fingerprint']
        os.makedirs(save_dir, exist_ok=True)
        
        # 提取相似度矩阵
        if 'similarity_matrix' in results:
            matrix = np.array(results['similarity_matrix'])
            wallet_ids = results.get('wallet_ids', ['A', 'B', 'C'])
            
            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(matrix, cmap='RdYlGn', vmin=0, vmax=1)
            
            # 添加颜色条
            plt.colorbar(im, ax=ax, label='Similarity')
            
            # 设置标签
            ax.set_xticks(range(len(wallet_ids)))
            ax.set_yticks(range(len(wallet_ids)))
            ax.set_xticklabels(wallet_ids)
            ax.set_yticklabels(wallet_ids)
            ax.set_xlabel('Wallet')
            ax.set_ylabel('Wallet')
            ax.set_title('Wallet Fingerprint Similarity Matrix')
            
            # 添加数值
            for i in range(len(wallet_ids)):
                for j in range(len(wallet_ids)):
                    text = ax.text(j, i, f'{matrix[i, j]:.2f}',
                                   ha="center", va="center",
                                   color="white" if matrix[i, j] < 0.5 else "black")
            
            plt.tight_layout()
            plt.savefig(os.path.join(save_dir, 'fingerprint_similarity.png'), dpi=150, bbox_inches='tight')
            plt.close()
            print(f"Saved: {save_dir}/fingerprint_similarity.png")
        
        # 绘制摘要条形图
        if 'same_wallet_similarity' in results:
            fig, ax = plt.subplots(figsize=(6, 4))
            
            categories = ['Same Wallet', 'Different Wallets']
            values = [
                results['same_wallet_similarity'],
                results['cross_wallet_similarity']
            ]
            colors = ['blue', 'orange']
            
            bars = ax.bar(categories, values, color=colors)
            ax.set_ylabel('Average Similarity')
            ax.set_title('Wallet Linkability Analysis')
            ax.set_ylim(0, 1)
            
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                       f'{val:.3f}', ha='center', va='bottom')
            
            # 添加标注
            if results.get('linkage_possible', False):
                ax.text(0.5, 0.95, '⚠️  Linkage Possible', transform=ax.transAxes,
                       ha='center', color='red', fontsize=12, fontweight='bold')
            else:
                ax.text(0.5, 0.95, '✅  No Linkage Detected', transform=ax.transAxes,
                       ha='center', color='green', fontsize=12, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(os.path.join(save_dir, 'fingerprint_summary.png'), dpi=150, bbox_inches='tight')
            plt.close()
            print(f"Saved: {save_dir}/fingerprint_summary.png")
    
    def plot_consistency_results(self, save_dir: str = 'results/figures'):
        """绘制一致性测试结果"""
        if 'consistency' not in self.results:
            print("No consistency results found")
            return
        
        results = self.results['consistency']
        os.makedirs(save_dir, exist_ok=True)
        
        # 统计每个测试的离群者
        test_names = []
        outlier_counts = []
        consensus_status = []
        
        for r in results:
            test_name = r.get('test_type', 'unknown')
            test_names.append(test_name)
            outliers = r.get('outliers', [])
            outlier_counts.append(len(outliers))
            consensus_status.append(r.get('consensus_reached', False))
        
        if not test_names:
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 离群者数量
        colors = ['red' if c else 'green' for c in consensus_status]
        bars = ax1.bar(test_names, outlier_counts, color=colors)
        ax1.set_ylabel('Number of Outliers')
        ax1.set_title('Cross-Provider Consistency')
        ax1.tick_params(axis='x', rotation=45)
        
        for bar, count in zip(bars, outlier_counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                    f'{count}', ha='center', va='bottom')
        
        # 共识饼图
        consensus_count = sum(consensus_status)
        no_consensus_count = len(consensus_status) - consensus_count
        ax2.pie([consensus_count, no_consensus_count], 
                labels=['Consensus Reached', 'No Consensus'],
                colors=['green', 'red'], autopct='%1.1f%%')
        ax2.set_title('Consensus Summary')
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, 'consistency_analysis.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_dir}/consistency_analysis.png")
    
    def generate_summary_report(self) -> str:
        """生成文本摘要报告"""
        report = []
        report.append("=" * 60)
        report.append("RPC PRIVACY LEAKAGE MEASUREMENT - SUMMARY REPORT")
        report.append("=" * 60)
        report.append("")
        
        # IP泄露摘要
        if 'ip_leak' in self.results:
            report.append("1. IP LEAKAGE ANALYSIS")
            report.append("-" * 30)
            for r in self.results['ip_leak']:
                name = r.get('rpc_name', 'Unknown')
                analysis = r.get('analysis', {})
                leak_score = analysis.get('indirect_leak_score', 0)
                confidence = analysis.get('confidence', 0)
                
                status = "🔴 LEAK" if leak_score > 0.3 else "🟢 SAFE"
                report.append(f"   {name}: {status} (score={leak_score:.2f}, conf={confidence:.2f})")
            report.append("")
        
        # 指纹分析摘要
        if 'fingerprint' in self.results:
            report.append("2. ADDRESS FINGERPRINT ANALYSIS")
            report.append("-" * 30)
            r = self.results['fingerprint']
            report.append(f"   Same-wallet similarity: {r.get('same_wallet_similarity', 0):.3f}")
            report.append(f"   Cross-wallet similarity: {r.get('cross_wallet_similarity', 0):.3f}")
            report.append(f"   Linkage possible: {'YES ⚠️' if r.get('linkage_possible', False) else 'NO ✅'}")
            report.append("")
        
        # 一致性摘要
        if 'consistency' in self.results:
            report.append("3. CROSS-PROVIDER CONSISTENCY")
            report.append("-" * 30)
            for r in self.results['consistency']:
                test_name = r.get('test_type', 'unknown')
                consensus = r.get('consensus_reached', False)
                outliers = r.get('outliers', [])
                status = "✅" if consensus else "❌"
                report.append(f"   {status} {test_name}: outliers={outliers}")
            report.append("")
        
        report.append("=" * 60)
        report.append("RECOMMENDATIONS")
        report.append("=" * 60)
        report.append("   1. Use multiple RPC providers for sensitive queries")
        report.append("   2. Rotate RPC endpoints regularly")
        report.append("   3. Consider self-hosted nodes for maximum privacy")
        report.append("   4. Use VPN/proxy layers when using public RPCs")
        
        return "\n".join(report)

def main():
    """主函数"""
    print("Statistical Analysis Module")
    print("=" * 40)
    
    analyzer = ResultAnalyzer()
    analyzer.load_results()
    
    if not analyzer.results:
        print("No results found. Please run measurements first.")
        print("Run: python src/measurement/ip_leak_test.py")
        print("     python src/measurement/fingerprint_test.py")
        print("     python src/measurement/consistency_test.py")
        return
    
    # 生成图表
    analyzer.plot_ip_leak_results()
    analyzer.plot_fingerprint_results()
    analyzer.plot_consistency_results()
    
    # 生成摘要报告
    summary = analyzer.generate_summary_report()
    print("\n" + summary)
    
    # 保存报告
    os.makedirs('results', exist_ok=True)
    with open('results/summary_report.txt', 'w') as f:
        f.write(summary)
    print("\n✅ Summary report saved to results/summary_report.txt")

if __name__ == "__main__":
    main()
