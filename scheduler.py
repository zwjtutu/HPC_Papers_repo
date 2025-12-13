"""
定时任务调度模块
使用APScheduler实现定时执行
"""
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import Config
from main import HPCPaperAgent

logger = logging.getLogger(__name__)


class PaperScheduler:
    """论文获取定时调度器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化调度器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = Config(config_path)
        self.agent = HPCPaperAgent(config_path)
        self.scheduler = BlockingScheduler(timezone=pytz.timezone('Asia/Shanghai'))
    
    def start(self):
        """启动定时任务"""
        schedule_config = self.config.get("schedule", {})
        
        if not schedule_config.get("enabled", True):
            logger.info("定时任务未启用")
            return
        
        # 解析执行时间
        time_str = schedule_config.get("time", "09:00")
        hour, minute = map(int, time_str.split(":"))
        
        # 添加定时任务
        self.scheduler.add_job(
            func=self._run_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='hpc_paper_fetch',
            name='HPC论文自动获取',
            replace_existing=True
        )
        
        logger.info(f"定时任务已启动，每天 {time_str} 执行")
        logger.info("按 Ctrl+C 退出")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("定时任务已停止")
            self.scheduler.shutdown()
    
    def _run_job(self):
        """执行任务"""
        logger.info(f"定时任务触发: {datetime.now()}")
        try:
            self.agent.run(days=1)
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}", exc_info=True)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HPC论文自动获取定时任务")
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（可选）"
    )
    
    args = parser.parse_args()
    
    scheduler = PaperScheduler(config_path=args.config)
    scheduler.start()


if __name__ == "__main__":
    main()
