"""
统一的RPC客户端封装，支持代理和请求记录
"""
import requests
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

@dataclass
class RequestLog:
    """请求日志数据结构"""
    timestamp: float
    method: str
    params: str
    response_preview: str
    response_time_ms: float
    proxy_used: Optional[str]
    rpc_url: str
    request_id: str

class RPCClient:
    """支持代理和日志记录的RPC客户端"""
    
    def __init__(self, rpc_url: str, enable_logging: bool = True):
        self.rpc_url = rpc_url
        self.enable_logging = enable_logging
        self.request_logs: List[RequestLog] = []
        self.request_counter = 0
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _generate_request_id(self) -> str:
        """生成唯一请求ID"""
        self.request_counter += 1
        timestamp = int(time.time() * 1000)
        return f"req_{timestamp}_{self.request_counter}"
    
    def _log_request(self, method: str, params: Any, response: Any, 
                     response_time_ms: float, proxy: Optional[str]):
        """记录请求日志"""
        if not self.enable_logging:
            return
        
        log = RequestLog(
            timestamp=time.time(),
            method=method,
            params=json.dumps(params)[:200],  # 限制长度
            response_preview=str(response)[:200],
            response_time_ms=response_time_ms,
            proxy_used=proxy,
            rpc_url=self.rpc_url,
            request_id=self._generate_request_id()
        )
        self.request_logs.append(log)
    
    def send_request(self, method: str, params: List[Any], 
                     proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        发送JSON-RPC请求
        
        Args:
            method: RPC方法名，如 'eth_getBalance'
            params: 参数列表
            proxy: 代理URL，如 'http://127.0.0.1:8080'
        
        Returns:
            RPC响应字典
        """
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': self.request_counter
        }
        
        proxies = None
        if proxy:
            proxies = {'http': proxy, 'https': proxy}
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                self.rpc_url,
                json=payload,
                proxies=proxies,
                timeout=30
            )
            response_time_ms = (time.time() - start_time) * 1000
            result = response.json()
            
            self._log_request(method, params, result, response_time_ms, proxy)
            return result
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_result = {'error': str(e)}
            self._log_request(method, params, error_result, response_time_ms, proxy)
            raise
    
    def get_balance(self, address: str, block: str = 'latest', 
                    proxy: Optional[str] = None) -> int:
        """获取账户余额"""
        result = self.send_request('eth_getBalance', [address, block], proxy)
        if 'result' in result:
            return int(result['result'], 16)
        return 0
    
    def get_transaction_count(self, address: str, block: str = 'latest',
                               proxy: Optional[str] = None) -> int:
        """获取nonce（交易计数）"""
        result = self.send_request('eth_getTransactionCount', [address, block], proxy)
        if 'result' in result:
            return int(result['result'], 16)
        return 0
    
    def call_contract(self, to: str, data: str, block: str = 'latest',
                      proxy: Optional[str] = None) -> str:
        """调用合约（只读）"""
        params = [{'to': to, 'data': data}, block]
        result = self.send_request('eth_call', params, proxy)
        if 'result' in result:
            return result['result']
        return ''
    
    def get_logs(self) -> List[Dict]:
        """获取所有请求日志"""
        return [asdict(log) for log in self.request_logs]
    
    def clear_logs(self):
        """清空日志"""
        self.request_logs.clear()
