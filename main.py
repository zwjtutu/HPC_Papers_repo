"""
HPC论文自动获取工具主程序
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import Config
from arxiv_fetcher import ArxivFetcher
from filter_factory import FilterFactory
from email_sender import EmailSender
from wechat_sender import WeChatSender
from storage import PaperStorage


# 配置日志
def setup_logging(log_path: str):
    """设置日志配置"""
    log_dir = Path(log_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"hpc_paper_agent_{datetime.now().strftime('%Y%m%d')}.log"
    max_log_size = 5 * 1024 * 1024  # 单个日志文件最大 5MB（5*1024*1024 字节）
    backup_count = 3  # 最多保留 3 个备份文件

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # logging.FileHandler(log_file, encoding='utf-8'),
            RotatingFileHandler(
                log_file,
                maxBytes=max_log_size,
                backupCount=backup_count,
                encoding='utf-8'  # 避免中文乱码
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )


class HPCPaperAgent:
    """HPC论文自动获取代理"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化代理
        
        Args:
            config_path: 配置文件路径
        """
        self.config = Config(config_path)
        
        # 设置日志
        log_path = self.config.get("storage.log_path", "logs")
        setup_logging(log_path)
        self.logger = logging.getLogger(__name__)
        
        # 初始化各个组件
        self._init_components()
    
    def _init_components(self):
        ###Add for secret env
        email_sender_env = os.environ.get("EMAIL_PATH")
        email_password_env = os.environ.get("EMAIL_PASS")
        serverchan_key_env = os.environ.get("PUSH_SERVERCHAN_KEY")
        wecom_webhook_env = os.environ.get("PUSH_WECOM_WEBHOOK")

        """初始化各个组件"""
        # arXiv获取器
        arxiv_config = self.config.get("arxiv", {})
        self.arxiv_fetcher = ArxivFetcher(
            categories=arxiv_config.get("categories", []),
            max_results=arxiv_config.get("max_results", 50)
        )

        # AI筛选器（通过工厂类创建）
        self.paper_filter = FilterFactory.create_from_config(self.config.config)
        if self.paper_filter:
            provider = self.config.get("filter.provider", "unknown")
            self.logger.info(f"已初始化 {provider} 筛选器")
        else:
            self.logger.warning("未配置AI筛选器，将使用关键词匹配")
        
        # 存储管理器
        storage_config = self.config.get("storage", {})
        max_storage_size = storage_config.get("max_storage_size", 0)
        self.storage = PaperStorage(
            storage_config.get("database_path", "papers.db"),
            max_storage_size=max_storage_size
        )
        if max_storage_size > 0:
            self.logger.info(f"存储上限已设置: {max_storage_size} 篇论文")
        
        # 邮件发送器
        email_config = self.config.get("email", {})
        self.email_sender = None
        if email_config.get("enabled", False):
            self.email_sender = EmailSender(
                send_mode=email_config.get("send_mode", "smtp"),
                smtp_server=email_config.get("smtp_server", ""),
                smtp_port=email_config.get("smtp_port", 587),
                sender_email=email_sender_env if email_sender_env else email_config.get("sender_email", ""),
                sender_password=email_password_env if email_password_env else email_config.get("sender_password", ""),
                receiver_email=email_config.get("receiver_email", "")
            )
        
        # 微信发送器
        wechat_config = self.config.get("wechat", {})
        self.wechat_sender = None
        if wechat_config.get("enabled", False):
            self.wechat_sender = WeChatSender(
                sender_type=wechat_config.get("type", "serverchan"),
                serverchan_key=serverchan_key_env if serverchan_key_env else wechat_config.get("serverchan_key", ""),
                wecom_webhook=wecom_webhook_env if wecom_webhook_env else wechat_config.get("wecom_webhook", "")
            )
    
    def run(self, days: int = 1):
        """
        运行一次完整的获取和发送流程
        
        Args:
            days: 获取最近几天的论文
        """
        self.logger.info("=" * 80)
        self.logger.info("开始运行HPC论文自动获取工具")
        self.logger.info("=" * 80)
        
        try:
            # 1. 从arXiv获取论文
            self.logger.info(f"步骤1: 从arXiv获取最近 {days} 天的论文...")
            papers = self.arxiv_fetcher.fetch_recent_papers(days=days)
            self.logger.info(f"获取到 {len(papers)} 篇论文")
            
            if not papers:
                self.logger.info("没有获取到新论文，退出")
                return
            
            # 2. 过滤已存在的论文
            if False:
                self.logger.info("步骤2: 过滤已存在的论文...")
                new_papers = self.storage.filter_new_papers(papers)
                self.logger.info(f"过滤后剩余 {len(new_papers)} 篇新论文")
                
                if not new_papers:
                    self.logger.info("没有新论文，退出")
                    return
            else:
                new_papers = papers
            
            # 3. 使用AI筛选相关论文
            if self.paper_filter:
                provider = self.config.get("filter.provider", "unknown")
                self.logger.info(f"步骤3: 使用{provider}筛选相关论文...")
                relevant_papers = self.paper_filter.filter_papers(new_papers)
                self.logger.info(f"筛选出 {len(relevant_papers)} 篇相关论文")
                
                if not relevant_papers:
                    self.logger.info("没有相关论文，退出")
                    # 仍然保存这些论文，标记为不相关
                    self.storage.add_papers(new_papers, sent=False)
                    return
            else:
                # 如果没有配置AI筛选器，使用所有新论文
                relevant_papers = new_papers
                self.logger.info("步骤3: 跳过AI筛选（未配置），使用所有新论文")
            
            # 4. 保存论文到数据库
            self.logger.info("步骤4: 保存论文到数据库...")
            self.storage.add_papers(relevant_papers, sent=True)
            
            # 5. 发送通知
            self.logger.info("步骤5: 发送通知...")
            success_count = 0
            
            # 发送邮件
            if self.email_sender:
                self.logger.info("发送邮件通知...")
                if self.email_sender.send_papers(relevant_papers):
                    success_count += 1
                    self.logger.info("邮件发送成功")
                else:
                    self.logger.error("邮件发送失败")
            
            # 发送微信
            if self.wechat_sender:
                self.logger.info("发送微信通知...")
                if self.wechat_sender.send_papers(relevant_papers):
                    success_count += 1
                    self.logger.info("微信发送成功")
                else:
                    self.logger.error("微信发送失败")
            
            if success_count == 0:
                self.logger.warning("未配置任何通知方式，论文已保存但未发送")
            
            self.logger.info("=" * 80)
            self.logger.info(f"完成！共处理 {len(relevant_papers)} 篇相关论文")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"运行过程中出错: {e}", exc_info=True)
            raise

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HPC论文自动获取工具")
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（可选）"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="获取最近几天的论文(默认:1)"
    )
    
    args = parser.parse_args()
    
    # 创建并运行代理
    agent = HPCPaperAgent(config_path=args.config)
    agent.run(days=args.days)

if __name__ == "__main__":
    main()
