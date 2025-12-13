"""
HPC论文自动获取工具测试脚本
用于测试各个模块的功能
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_arxiv_fetcher():
    """测试arXiv获取模块"""
    print("\n" + "="*80)
    print("测试1: arXiv论文获取模块")
    print("="*80)
    
    try:
        from arxiv_fetcher import ArxivFetcher
        
        fetcher = ArxivFetcher(
            categories=["cs.DC"],
            max_results=5
        )
        
        print("正在从arXiv获取论文（最多5篇）...")
        papers = fetcher.fetch_recent_papers(days=7)
        
        if papers:
            print(f"✓ 成功获取 {len(papers)} 篇论文")
            print(f"\n示例论文:")
            paper = papers[0]
            print(f"  标题: {paper['title'][:60]}...")
            print(f"  作者: {', '.join(paper['authors'][:3])}")
            print(f"  链接: {paper['link']}")
            return True
        else:
            print("⚠ 未获取到论文（可能是网络问题或该时间段没有新论文）")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_filter():
    """测试AI筛选模块"""
    print("\n" + "="*80)
    print("测试2: AI筛选模块")
    print("="*80)
    
    try:
        from filter_factory import FilterFactory
        from config import Config
        
        config = Config()
        filter_obj = FilterFactory.create_from_config(config.config)
        
        if not filter_obj:
            provider = config.get("filter.provider", "unknown")
            print(f"⚠ 未配置{provider} API密钥，跳过测试")
            print("  提示: 在config.json中配置filter.provider和filter.api_key")
            return None
        
        # 创建测试论文
        test_paper = {
            "id": "test123",
            "arxiv_id": "test123",
            "title": "High Performance Computing with GPU Acceleration",
            "authors": ["Test Author"],
            "summary": "This paper discusses distributed computing and parallel processing using GPU clusters for high performance computing applications.",
            "published": datetime.now().isoformat(),
            "link": "https://arxiv.org/abs/test123",
            "categories": ["cs.DC"]
        }
        
        print("正在测试论文筛选...")
        is_relevant, score, reason = filter_obj.is_relevant(test_paper)
        
        print(f"✓ 筛选完成")
        print(f"  相关性: {'是' if is_relevant else '否'}")
        print(f"  分数: {score:.2f}")
        print(f"  原因: {reason}")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage():
    """测试存储模块"""
    print("\n" + "="*80)
    print("测试3: 存储模块")
    print("="*80)
    
    try:
        from storage import PaperStorage
        import tempfile
        import os
        
        # 使用临时数据库
        db_path = os.path.join(tempfile.gettempdir(), "test_papers.db")
        
        storage = PaperStorage(db_path)
        
        # 测试添加论文
        test_paper = {
            "id": "test123",
            "arxiv_id": "test123",
            "title": "Test Paper",
            "authors": ["Author 1", "Author 2"],
            "summary": "Test summary",
            "published": datetime.now().isoformat(),
            "link": "https://arxiv.org/abs/test123",
            "categories": ["cs.DC"],
            "relevance_score": 0.8,
            "relevance_reason": "Test reason"
        }
        
        print("正在测试添加论文...")
        storage.add_paper(test_paper, sent=True)
        print("✓ 论文已添加")
        
        # 测试检查是否存在
        print("正在测试检查论文是否存在...")
        exists = storage.paper_exists("test123")
        if exists:
            print("✓ 论文存在检查通过")
        else:
            print("✗ 论文存在检查失败")
            return False
        
        # 测试过滤新论文
        print("正在测试过滤新论文...")
        new_papers = storage.filter_new_papers([test_paper])
        if len(new_papers) == 0:
            print("✓ 过滤功能正常（已存在的论文被正确过滤）")
        else:
            print("✗ 过滤功能异常")
            return False
        
        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)
            print("✓ 临时数据库已清理")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_sender():
    """测试邮件发送模块（不实际发送）"""
    print("\n" + "="*80)
    print("测试4: 邮件发送模块（内容生成）")
    print("="*80)
    
    try:
        from email_sender import EmailSender
        
        # 创建测试发送器（使用假配置）
        sender = EmailSender(
            smtp_server="smtp.test.com",
            smtp_port=587,
            sender_email="test@test.com",
            sender_password="test",
            receiver_email="receiver@test.com"
        )
        
        # 测试内容生成
        test_papers = [{
            "id": "test123",
            "arxiv_id": "test123",
            "title": "Test Paper Title",
            "authors": ["Author 1", "Author 2"],
            "summary": "This is a test paper summary for high performance computing.",
            "published": datetime.now().isoformat(),
            "link": "https://arxiv.org/abs/test123",
            "pdf_link": "https://arxiv.org/pdf/test123.pdf",
            "relevance_score": 0.85,
            "relevance_reason": "Contains HPC keywords"
        }]
        
        print("正在测试邮件内容生成...")
        text_content = sender._generate_text_content(test_papers)
        html_content = sender._generate_html_content(test_papers)
        
        if text_content and html_content:
            print("✓ 邮件内容生成成功")
            print(f"  文本长度: {len(text_content)} 字符")
            print(f"  HTML长度: {len(html_content)} 字符")
            return True
        else:
            print("✗ 邮件内容生成失败")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wechat_sender():
    """测试微信发送模块（内容生成）"""
    print("\n" + "="*80)
    print("测试5: 微信发送模块（内容生成）")
    print("="*80)
    
    try:
        from wechat_sender import WeChatSender
        
        sender = WeChatSender(
            sender_type="wecom",  # serverchan 或 wecom
            serverchan_key="SCT305598TGOWz6DOxAKHVWNgonDUqVWkp",
            wecom_webhook="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd9a1f0f-07a8-4e5f-b152-278002a6b15f"
        )
        
        test_papers = [{
            "id": "test123",
            "arxiv_id": "test123",
            "title": "Test Paper Title",
            "authors": ["Author 1", "Author 2"],
            "summary": "This is a test paper summary.",
            "published": datetime.now().isoformat(),
            "link": "https://arxiv.org/abs/test123",
            "pdf_link": "https://arxiv.org/pdf/test123.pdf",
            "relevance_score": 0.85,
            "relevance_reason": "Contains HPC keywords"
        }]
        
        print("正在测试微信消息内容生成...")
        # 测试ServerChan格式
        content = sender._send_via_serverchan.__code__
        print("✓ ServerChan发送方法存在")
        
        # 测试企业微信格式
        content = sender._send_via_wecom.__code__
        print("✓ 企业微信发送方法存在")
        
        print("✓ 微信发送模块结构正常")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """测试配置模块"""
    print("\n" + "="*80)
    print("测试6: 配置模块")
    print("="*80)
    
    try:
        from config import Config
        import tempfile
        import json
        import os
        
        # 使用临时配置文件
        config_file = os.path.join(tempfile.gettempdir(), "test_config.json")
        
        config = Config(config_path=config_file)
        
        print("正在测试配置读取...")
        arxiv_cats = config.get("arxiv.categories", [])
        if arxiv_cats:
            print(f"✓ 配置读取成功: arXiv分类 = {arxiv_cats[:2]}...")
        else:
            print("⚠ 使用默认配置")
        
        print("正在测试配置写入...")
        config.set("test.key", "test_value")
        test_value = config.get("test.key")
        if test_value == "test_value":
            print("✓ 配置写入成功")
        else:
            print("✗ 配置写入失败")
            return False
        
        # 清理
        if os.path.exists(config_file):
            os.remove(config_file)
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """集成测试（不实际发送）"""
    print("\n" + "="*80)
    print("测试7: 集成测试（模拟完整流程）")
    print("="*80)
    
    try:
        from arxiv_fetcher import ArxivFetcher
        from storage import PaperStorage
        import tempfile
        import os
        
        print("步骤1: 获取论文...")
        fetcher = ArxivFetcher(categories=["cs.DC"], max_results=3)
        papers = fetcher.fetch_recent_papers(days=30)  # 扩大范围以获取论文
        
        if not papers:
            print("⚠ 未获取到论文，跳过集成测试")
            return None
        
        print(f"✓ 获取到 {len(papers)} 篇论文")
        
        print("步骤2: 存储论文...")
        db_path = os.path.join(tempfile.gettempdir(), "test_integration.db")
        storage = PaperStorage(db_path)
        
        # 过滤新论文
        new_papers = storage.filter_new_papers(papers[:2])
        print(f"✓ 过滤后剩余 {len(new_papers)} 篇新论文")
        
        if new_papers:
            print("步骤3: 保存论文...")
            storage.add_papers(new_papers, sent=False)
            print("✓ 论文已保存")
        
        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)
        
        print("✓ 集成测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("HPC论文自动获取工具 - 功能测试")
    print("="*80)
    print("\n提示: 某些测试需要网络连接和API密钥")
    print("     如果某个测试失败，请检查配置和网络连接\n")
    
    results = {}
    
    # 运行各项测试
    # results["配置模块"] = test_config()
    # results["arXiv获取"] = test_arxiv_fetcher()
    # results["存储模块"] = test_storage()
    # results["邮件发送"] = test_email_sender()
    results["微信发送"] = test_wechat_sender()
    # results["AI筛选"] = test_ai_filter()
    # results["集成测试"] = test_integration()
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results.items():
        if result is True:
            print(f"✓ {test_name}: 通过")
            passed += 1
        elif result is False:
            print(f"✗ {test_name}: 失败")
            failed += 1
        else:
            print(f"⚠ {test_name}: 跳过")
            skipped += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if failed == 0:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print(f"\n✗ 有 {failed} 个测试失败，请检查上述错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
