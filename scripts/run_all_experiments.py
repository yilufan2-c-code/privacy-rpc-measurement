# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

#!/usr/bin/env python3
"""
一键运行所有实验
"""
import subprocess
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_command(cmd, description):
    """运行命令并打印状态"""
    print("\n" + "=" * 60)
    print(f"▶ {description}")
    print("=" * 60)
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout[-500:])  # 打印最后500字符
    else:
        print(f"❌ {description} failed")
        print(f"Error: {result.stderr}")
    
    return result.returncode == 0

def main():
    print("=" * 60)
    print("RPC PRIVACY LEAKAGE MEASUREMENT - FULL EXPERIMENT SUITE")
    print("=" * 60)
    print("\nThis script will run all three experiments in sequence.")
    print("Make sure you have:")
    print("  1. Configured API keys in the measurement files")
    print("  2. Installed dependencies: pip install -r requirements.txt")
    print("\nPress Enter to continue, or Ctrl+C to cancel...")
    input()
    
    # 创建必要目录
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    os.makedirs('results/figures', exist_ok=True)
    
    # 运行实验
    experiments = [
        ("python src/measurement/ip_leak_test.py", "IP Leakage Measurement"),
        ("python src/measurement/fingerprint_test.py", "Address Fingerprint Analysis"),
        ("python src/measurement/consistency_test.py", "Cross-Provider Consistency Test"),
        ("python src/analysis/stats.py", "Statistical Analysis & Visualization"),
    ]
    
    success_count = 0
    for cmd, desc in experiments:
        if run_command(cmd, desc):
            success_count += 1
    
    print("\n" + "=" * 60)
    print("EXPERIMENT SUITE COMPLETE")
    print("=" * 60)
    print(f"Completed: {success_count}/{len(experiments)} experiments")
    
    if success_count == len(experiments):
        print("\n✅ All experiments completed successfully!")
        print("\nResults are available in:")
        print("  - data/raw/          (raw measurement data)")
        print("  - results/figures/   (visualizations)")
        print("  - results/summary_report.txt (summary)")
    else:
        print("\n⚠️ Some experiments failed. Check the errors above.")
    
    print("\nNext steps:")
    print("  1. Review results in results/summary_report.txt")
    print("  2. Use findings in your final report")
    print("  3. Push all code to GitHub")

if __name__ == "__main__":
    main()
