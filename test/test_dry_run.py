"""
HPC论文自动获取工具 - 试运行脚本
不实际发送邮件/微信，只测试完整流程
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def dry_run():
    """试运行：模拟完整流程但不发送通知"""
    print("\n" + "="*80)
    print("HPC论文自动获取工具 - 试运行模式")
    print("="*80)
    print("\n此模式将:")
    print("  ✓ 从arXiv获取论文")
    print("  ✓ 使用AI筛选（如果配置了API密钥）")
    print("  ✓ 保存到数据库")
    print("  ✗ 不发送邮件/微信通知")
    print("\n" + "-"*80 + "\n")
    
    try:
        from config import Config
        from arxiv_fetcher import ArxivFetcher
        from filter_factory import FilterFactory
        from storage import PaperStorage
        
        # 加载配置
        config = Config()
        
        # 初始化组件
        print("初始化组件...")
        arxiv_config = config.get("arxiv", {})
        fetcher = ArxivFetcher(
            categories=arxiv_config.get("categories", ["cs.DC"]),
            max_results=min(arxiv_config.get("max_results", 50), 10)  # 试运行只获取10篇
        )
        
        # 使用工厂类创建筛选器
        filter_obj = FilterFactory.create_from_config(config.config)
        if filter_obj:
            provider = config.get("filter.provider", "unknown")
            print(f"✓ {provider}筛选器已初始化")
        else:
            filter_obj = None
            print("⚠ 未配置AI筛选器，将跳过筛选步骤")
        
        storage_config = config.get("storage", {})
        max_storage_size = storage_config.get("max_storage_size", 0)
        storage = PaperStorage(
            storage_config.get("database_path", "test_papers.db"),
            max_storage_size=max_storage_size
        )
        if max_storage_size > 0:
            print(f"✓ 存储管理器已初始化（存储上限: {max_storage_size} 篇）")
        else:
            print("✓ 存储管理器已初始化（无存储上限）")
        
        # 步骤1: 获取论文
        print("\n" + "-"*80)
        print("步骤1: 从arXiv获取论文...")
        papers = fetcher.fetch_recent_papers(days=7)
        print(f"获取到 {len(papers)} 篇论文")
        
        if not papers:
            print("⚠ 未获取到论文，可能原因:")
            print("  - 网络连接问题")
            print("  - 该时间段没有新论文")
            print("  - arXiv服务暂时不可用")
            return
        
        # 显示前3篇论文
        print("\n前3篇论文预览:")
        for i, paper in enumerate(papers[:3], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   作者: {', '.join(paper['authors'][:3])}")
            print(f"   链接: {paper['link']}")
        
        # 步骤2: 过滤已存在的论文
        print("\n" + "-"*80)
        print("步骤2: 过滤已存在的论文...")
        new_papers = storage.filter_new_papers(papers)
        print(f"过滤后剩余 {len(new_papers)} 篇新论文")
        
        if not new_papers:
            print("所有论文都已存在，无需处理")
            return
        
        # 步骤3: AI筛选
        if filter_obj:
            provider = config.get("filter.provider", "unknown")
            print("\n" + "-"*80)
            print(f"步骤3: 使用{provider}筛选相关论文...")
            print("（这可能需要一些时间，请耐心等待）")
            
            relevant_papers = filter_obj.filter_papers(new_papers)
            print(f"筛选出 {len(relevant_papers)} 篇相关论文")
            
            if relevant_papers:
                print("\n相关论文预览:")
                for i, paper in enumerate(relevant_papers[:3], 1):
                    print(f"\n{i}. {paper['title']}")
                    print(f"   相关性分数: {paper.get('relevance_score', 0):.2f}")
                    print(f"   原因: {paper.get('relevance_reason', 'N/A')[:50]}...")
        else:
            relevant_papers = new_papers
            print("\n步骤3: 跳过AI筛选（未配置API密钥）")
        
        # 步骤4: 保存到数据库（但不标记为已发送）
        print("\n" + "-"*80)
        print("步骤4: 保存论文到数据库...")
        if relevant_papers:
            storage.add_papers(relevant_papers, sent=False)
            print(f"✓ 已保存 {len(relevant_papers)} 篇论文到数据库")
        else:
            storage.add_papers(new_papers, sent=False)
            print(f"✓ 已保存 {len(new_papers)} 篇论文到数据库（未筛选）")
        
        # 步骤5: 显示通知预览
        print("\n" + "-"*80)
        print("步骤5: 通知预览（试运行模式，不实际发送）")
        
        email_config = config.get("email", {})
        wechat_config = config.get("wechat", {})
        
        papers_to_notify = relevant_papers if relevant_papers else new_papers
        
        if email_config.get("enabled", False):
            print(f"\n邮件通知: 将发送 {len(papers_to_notify)} 篇论文到 {email_config.get('receiver_email', 'N/A')}")
        else:
            print("\n邮件通知: 未启用")
        
        if wechat_config.get("enabled", False):
            print(f"\n微信通知: 将发送 {min(len(papers_to_notify), 5)} 篇论文（微信限制）")
        else:
            print("\n微信通知: 未启用")
        
        if not email_config.get("enabled") and not wechat_config.get("enabled"):
            print("\n⚠ 警告: 未配置任何通知方式")
            print("  请编辑 config.json 启用邮件或微信通知")
        
        print("\n" + "="*80)
        print("试运行完成！")
        print("="*80)
        print("\n如果一切正常，可以:")
        print("  1. 运行 'python main.py' 执行完整流程（会实际发送通知）")
        print("  2. 运行 'python scheduler.py' 启动定时任务")
        print("  3. 编辑 config.json 调整配置")
        
    except Exception as e:
        print(f"\n✗ 试运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(dry_run())
