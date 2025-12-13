# 测试指南

本文档详细说明如何测试HPC论文自动获取工具的各个功能模块。

## 测试前准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
# Windows
set DEEPSEEK_API_KEY=your_api_key_here
set SENDER_EMAIL=your_email@gmail.com
set SENDER_PASSWORD=your_app_password

# Linux/Mac
export DEEPSEEK_API_KEY=your_api_key_here
export SENDER_EMAIL=your_email@gmail.com
export SENDER_PASSWORD=your_app_password
```

### 3. 创建配置文件

首次运行会自动创建 `config.json`，或手动复制 `config.json.example`：

```bash
cp config.json.example config.json
# 然后编辑 config.json 填入你的配置
```

## 测试方法

### 方法1: 运行完整测试套件

```bash
python test_agent.py
```

这将运行所有模块的测试，包括：
- 配置模块
- arXiv获取模块
- 存储模块
- 邮件发送模块（仅内容生成，不实际发送）
- 微信发送模块（仅内容生成，不实际发送）
- DeepSeek筛选模块（需要API密钥）
- 集成测试

### 方法2: 试运行模式（推荐）

```bash
python test_dry_run.py
```

试运行模式会：
- ✅ 实际从arXiv获取论文
- ✅ 使用DeepSeek筛选（如果配置了）
- ✅ 保存到数据库
- ❌ 不发送邮件/微信通知

这是最接近真实使用的测试方式。

### 方法3: 手动测试

#### 测试arXiv获取

```python
from arxiv_fetcher import ArxivFetcher

# 创建获取器
fetcher = ArxivFetcher(
    categories=["cs.DC", "cs.Distributed"],
    max_results=10
)

# 获取最近7天的论文
papers = fetcher.fetch_recent_papers(days=7)

# 查看结果
print(f"获取到 {len(papers)} 篇论文")
for paper in papers[:3]:
    print(f"- {paper['title']}")
    print(f"  链接: {paper['link']}")
```

#### 测试DeepSeek筛选

```python
from deepseek_filter import DeepSeekFilter

# 创建筛选器
filter_obj = DeepSeekFilter(
    api_key="YOUR_DEEPSEEK_API_KEY",
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    relevance_threshold=0.7,
    keywords=["HPC", "high performance computing", "distributed computing"]
)

# 测试论文
test_paper = {
    "title": "High Performance Computing with GPU Acceleration",
    "summary": "This paper discusses distributed computing and parallel processing...",
    # ... 其他字段
}

is_relevant, score, reason = filter_obj.is_relevant(test_paper)
print(f"相关性: {is_relevant}")
print(f"分数: {score:.2f}")
print(f"原因: {reason}")
```

#### 测试存储

```python
from storage import PaperStorage
from datetime import datetime

# 创建存储管理器
storage = PaperStorage("test_papers.db")

# 添加测试论文
test_paper = {
    "id": "test123",
    "arxiv_id": "test123",
    "title": "Test Paper",
    "authors": ["Author 1"],
    "summary": "Test summary",
    "published": datetime.now().isoformat(),
    "link": "https://arxiv.org/abs/test123",
    "categories": ["cs.DC"]
}

storage.add_paper(test_paper, sent=False)

# 检查是否存在
exists = storage.paper_exists("test123")
print(f"论文存在: {exists}")

# 过滤新论文
new_papers = storage.filter_new_papers([test_paper])
print(f"新论文数量: {len(new_papers)}")
```

#### 测试邮件内容生成

```python
from email_sender import EmailSender

# 创建发送器（使用假配置，不会实际发送）
sender = EmailSender(
    smtp_server="smtp.test.com",
    smtp_port=587,
    sender_email="test@test.com",
    sender_password="test",
    receiver_email="receiver@test.com"
)

# 生成邮件内容
test_papers = [{
    "title": "Test Paper",
    "authors": ["Author 1"],
    "summary": "Test summary",
    "link": "https://arxiv.org/abs/test123",
    "relevance_score": 0.85
}]

text_content = sender._generate_text_content(test_papers)
html_content = sender._generate_html_content(test_papers)

print("文本内容:")
print(text_content[:200])
print("\nHTML内容长度:", len(html_content))
```

#### 测试微信内容生成

```python
from wechat_sender import WeChatSender

# 创建发送器
sender = WeChatSender(
    sender_type="serverchan",
    serverchan_key="test_key"
)

# 注意：这里只是测试结构，实际发送需要真实的key
# 可以查看代码中的 _send_via_serverchan 和 _send_via_wecom 方法
```

## 测试完整流程

### 1. 最小配置测试

只配置必要的部分，测试基本功能：

```json
{
  "arxiv": {
    "categories": ["cs.DC"],
    "max_results": 5
  },
  "deepseek": {
    "api_key": "",
    "relevance_threshold": 0.5
  },
  "email": {
    "enabled": false
  },
  "wechat": {
    "enabled": false
  }
}
```

运行：
```bash
python test_dry_run.py
```

### 2. 完整配置测试

配置所有功能后测试：

```json
{
  "arxiv": {
    "categories": ["cs.DC", "cs.Distributed"],
    "max_results": 20
  },
  "deepseek": {
    "api_key": "YOUR_KEY",
    "relevance_threshold": 0.7
  },
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "sender_password": "your_app_password",
    "receiver_email": "receiver@example.com"
  },
  "wechat": {
    "enabled": true,
    "type": "serverchan",
    "serverchan_key": "YOUR_KEY"
  }
}
```

运行：
```bash
# 先试运行
python test_dry_run.py

# 如果一切正常，运行完整流程
python main.py --days 1
```

## 测试检查清单

- [ ] arXiv获取模块能正常获取论文
- [ ] 存储模块能正确保存和查询论文
- [ ] DeepSeek筛选模块能正确判断相关性（如果配置了）
- [ ] 邮件内容生成正常（HTML和文本格式）
- [ ] 微信消息格式正确
- [ ] 配置文件能正确加载和保存
- [ ] 日志文件正常生成
- [ ] 数据库文件正常创建

## 常见测试问题

### 1. 测试时获取不到论文

**原因**: 可能是网络问题或该时间段确实没有新论文

**解决**: 
- 增加 `days` 参数，获取更长时间范围的论文
- 检查网络连接
- 尝试不同的arXiv分类

### 2. DeepSeek API测试失败

**原因**: API密钥未配置或无效

**解决**:
- 检查 `config.json` 中的 `deepseek.api_key`
- 或设置环境变量 `DEEPSEEK_API_KEY`
- 确认API密钥有效且有足够配额

### 3. 存储测试失败

**原因**: 数据库文件权限问题

**解决**:
- 检查目录写入权限
- 确保有足够的磁盘空间
- 尝试使用绝对路径

### 4. 邮件/微信测试

**注意**: 测试脚本不会实际发送邮件/微信，只测试内容生成。

要测试实际发送，需要：
1. 配置真实的SMTP/微信密钥
2. 运行 `python main.py`（会实际发送）

## 性能测试

测试大量论文的处理性能：

```python
from arxiv_fetcher import ArxivFetcher
import time

fetcher = ArxivFetcher(categories=["cs.DC"], max_results=100)

start = time.time()
papers = fetcher.fetch_recent_papers(days=30)
fetch_time = time.time() - start

print(f"获取 {len(papers)} 篇论文耗时: {fetch_time:.2f} 秒")
print(f"平均每篇: {fetch_time/len(papers)*1000:.2f} 毫秒")
```

## 持续集成测试

如果要在CI/CD中运行测试，可以：

```bash
# 只运行不需要API的测试
python test_agent.py 2>&1 | grep -v "DeepSeek"
```

或创建专门的CI测试脚本，跳过需要外部服务的测试。
