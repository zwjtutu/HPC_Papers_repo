"""
快速测试脚本 - 验证基本功能是否正常
"""
import sys

def quick_test():
    """快速测试基本功能"""
    print("="*60)
    print("HPC论文自动获取工具 - 快速测试")
    print("="*60)
    print()
    
    # 测试1: 导入模块
    print("1. 测试模块导入...")
    try:
        from config import Config
        from arxiv_fetcher import ArxivFetcher
        from storage import PaperStorage
        print("   ✓ 所有模块导入成功")
    except ImportError as e:
        print(f"   ✗ 模块导入失败: {e}")
        print("   提示: 请确保所有文件都在当前目录")
        return 1
    
    # 测试2: 配置加载
    print("\n2. 测试配置加载...")
    try:
        config = Config()
        print("   ✓ 配置加载成功")
        arxiv_cats = config.get("arxiv.categories", [])
        if arxiv_cats:
            print(f"   ✓ arXiv分类: {len(arxiv_cats)} 个")
    except Exception as e:
        print(f"   ✗ 配置加载失败: {e}")
        return 1
    
    # 测试3: 网络连接（arXiv）
    print("\n3. 测试arXiv连接...")
    try:
        fetcher = ArxivFetcher(categories=["cs.DC"], max_results=1)
        papers = fetcher.fetch_recent_papers(days=30)  # 扩大范围
        if papers:
            print(f"   ✓ 成功连接到arXiv，获取到 {len(papers)} 篇论文")
        else:
            print("   ⚠ 连接到arXiv但未获取到论文（可能是网络问题或该时间段无新论文）")
    except Exception as e:
        print(f"   ✗ arXiv连接失败: {e}")
        print("   提示: 请检查网络连接")
        return 1
    
    # 测试4: 数据库
    print("\n4. 测试数据库...")
    try:
        import tempfile
        import os
        db_path = os.path.join(tempfile.gettempdir(), "quick_test.db")
        storage = PaperStorage(db_path)
        print("   ✓ 数据库创建成功")
        
        # 测试添加
        if papers:
            test_paper = papers[0].copy()
            test_paper["id"] = "quick_test_123"
            test_paper["arxiv_id"] = "quick_test_123"
            storage.add_paper(test_paper, sent=False)
            exists = storage.paper_exists("quick_test_123")
            if exists:
                print("   ✓ 数据库读写正常")
            else:
                print("   ✗ 数据库写入失败")
                return 1
        
        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f"   ✗ 数据库测试失败: {e}")
        return 1
    
    # 测试5: AI筛选器配置检查
    print("\n5. 检查AI筛选器配置...")
    try:
        from filter_factory import FilterFactory
        filter_obj = FilterFactory.create_from_config(config.config)
        if filter_obj:
            provider = config.get("filter.provider", "unknown")
            print(f"   ✓ {provider}筛选器已配置并初始化成功")
        else:
            print("   ⚠ AI筛选器未配置或初始化失败")
            print("   提示: 在config.json中配置filter.provider和filter.api_key")
    except Exception as e:
        print(f"   ⚠ AI筛选器初始化失败: {e}")
    
    # 测试6: 通知配置检查
    print("\n6. 检查通知配置...")
    email_enabled = config.get("email.enabled", False)
    wechat_enabled = config.get("wechat.enabled", False)
    
    if email_enabled:
        receiver = config.get("email.receiver_email", "")
        if receiver:
            print(f"   ✓ 邮件通知已配置: {receiver}")
        else:
            print("   ⚠ 邮件通知已启用但未配置接收邮箱")
    else:
        print("   - 邮件通知未启用")
    
    if wechat_enabled:
        wechat_type = config.get("wechat.type", "")
        print(f"   ✓ 微信通知已配置: {wechat_type}")
    else:
        print("   - 微信通知未启用")
    
    if not email_enabled and not wechat_enabled:
        print("   ⚠ 警告: 未配置任何通知方式")
        print("   提示: 至少需要配置一种通知方式（邮件或微信）")
    
    print("\n" + "="*60)
    print("快速测试完成！")
    print("="*60)
    print("\n下一步:")
    print("  - 如果所有测试通过，可以运行 'python test_dry_run.py' 进行完整试运行")
    print("  - 或直接运行 'python main.py' 执行完整流程")
    print("  - 查看 TESTING.md 了解详细测试方法")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(quick_test())
