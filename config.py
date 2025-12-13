"""
配置文件管理模块
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径,默认为项目根目录下的config.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "hpc_paper_agent" / "config.json"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            # 使用环境变量或默认值
            self.config = self._get_default_config()
            self.save_config()
    
    def save_config(self):
        """保存配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "arxiv": {
                "categories": ["cs.DC", "cs.Distributed", "cs.PF", "cs.AR", "cs.CE"],
                "max_results": 50,
                "sort_by": "submittedDate",
                "sort_order": "descending"
            },
            "filter": {
                "provider": "deepseek",  # 可选: "deepseek", "gemini", "qwen"
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "relevance_threshold": 0.7,  # 阶段3阈值（标题+摘要LLM筛选）
                "title_filter_threshold": 0.5,  # 阶段2阈值（仅标题LLM筛选）
                "coarse_filter_threshold": 0.3,  # 阶段1阈值（关键词匹配）
                "enable_coarse_filter": True,  # 是否启用粗筛
                "keywords": [
                    "high performance computing",
                    "HPC",
                    "distributed computing",
                    "parallel computing",
                    "GPU computing",
                    "supercomputing",
                    "cluster computing",
                    "MPI",
                    "OpenMP",
                    "CUDA",
                    "高性能计算",
                    "分布式计算",
                    "并行计算"
                ]
            },
            "email": {
                "enabled": False,
                "smtp_server": "smtp.163.com",
                "smtp_port": 25,
                "sender_email": os.getenv("SENDER_EMAIL", ""),
                "sender_password": os.getenv("SENDER_PASSWORD", ""),
                "receiver_email": os.getenv("RECEIVER_EMAIL", "")
            },
            "wechat": {
                "enabled": False,
                "type": "serverchan",  # serverchan 或 wecom
                "serverchan_key": os.getenv("SERVERCHAN_KEY", ""),
                "wecom_webhook": os.getenv("WECOM_WEBHOOK", "")
            },
            "schedule": {
                "enabled": True,
                "time": "09:00",  # 每天执行时间
                "timezone": "Asia/Shanghai"
            },
            "storage": {
                "database_path": str(Path(__file__).parent / "papers.db"),
                "log_path": str(Path(__file__).parent / "logs"),
                "max_storage_size": 0  # 最大存储论文数量，0表示无限制
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save_config()
