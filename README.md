# HPC论文自动获取工具

一个自动化工具，每天从arXiv获取最新的高性能计算(HPC)相关论文，使用DeepSeek AI筛选相关性，并自动发送到指定邮箱或微信。

## 功能特性

- 🔍 **自动获取**: 从arXiv自动获取最新论文
- 🤖 **智能筛选**: 使用DeepSeek AI筛选HPC相关论文
- 📧 **邮件通知**: 支持发送精美的HTML邮件
- 💬 **微信通知**: 支持Server酱和企业微信机器人
- 💾 **去重存储**: 使用SQLite数据库避免重复发送
- ⏰ **定时任务**: 支持每天自动执行

## 安装

### 1. 克隆或下载项目

```bash
cd hpc_paper_agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

首次运行会自动创建配置文件 `config.json`，你需要编辑它来设置：

#### 必需配置

- **DeepSeek API密钥**: 从 [DeepSeek官网](https://platform.deepseek.com/) 获取
- **通知方式**: 至少配置一种（邮箱或微信）

#### 配置文件示例

```json
{
  "arxiv": {
    "categories": ["cs.DC", "cs.Distributed", "cs.PF", "cs.AR", "cs.CE"],
    "max_results": 50,
    "sort_by": "submittedDate",
    "sort_order": "descending"
  },
  "deepseek": {
    "api_key": "你的DeepSeek_API密钥",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "relevance_threshold": 0.7,
    "keywords": [
      "high performance computing",
      "HPC",
      "distributed computing",
      "parallel computing",
      "GPU computing"
    ]
  },
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "sender_password": "你的邮箱密码或应用专用密码",
    "receiver_email": "receiver@example.com"
  },
  "wechat": {
    "enabled": true,
    "type": "serverchan",
    "serverchan_key": "你的ServerChan_Key",
    "wecom_webhook": "你的企业微信Webhook_URL"
  },
  "schedule": {
    "enabled": true,
    "time": "09:00",
    "timezone": "Asia/Shanghai"
  }
}
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

首次运行会自动创建 `config.json`，编辑它填入你的配置：

- DeepSeek API密钥（必需，用于筛选）
- 邮件或微信配置（至少配置一种，用于接收通知）

### 3. 测试

```bash
# 快速测试（推荐首次使用）
python quick_test.py

# 完整测试套件
python test_agent.py

# 试运行（不实际发送通知，推荐）
python test_dry_run.py
```

详细测试说明请查看 [TESTING.md](TESTING.md)

### 4. 使用

```bash
# 手动运行一次
python main.py

# 或启动定时任务
python scheduler.py
```

## 使用方法

### 方式1: 手动运行

```bash
python main.py --days 1
```

参数说明：
- `--config`: 指定配置文件路径（可选）
- `--days`: 获取最近几天的论文（默认：1）

### 方式2: 定时任务（推荐）

```bash
python scheduler.py --config config.json
```

这将启动一个后台任务，每天在配置的时间自动执行。

### 方式3: 使用系统定时任务（Linux/Mac）

使用cron：

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天上午9点执行）
0 9 * * * cd /path/to/hpc_paper_agent && python main.py >> logs/cron.log 2>&1
```

Windows可以使用任务计划程序。

## 配置说明

### arXiv配置

- `categories`: arXiv分类，常用HPC相关分类：
  - `cs.DC`: 分布式、并行和集群计算
  - `cs.Distributed`: 分布式系统
  - `cs.PF`: 性能
  - `cs.AR`: 硬件架构
  - `cs.CE`: 计算工程、金融和科学

### DeepSeek配置

- `api_key`: 从DeepSeek官网获取
- `model`: 使用的模型（推荐 `deepseek-chat`）
- `base_url`: API基础URL（默认：`https://api.deepseek.com`）
- `relevance_threshold`: 相关性阈值（0-1），越高越严格
- `keywords`: 关键词列表，用于筛选

### 邮件配置

- Gmail用户需要使用[应用专用密码](https://support.google.com/accounts/answer/185833)
- 其他邮箱服务商请参考其SMTP设置

### 微信配置

#### Server酱

1. 访问 [Server酱官网](https://sct.ftqq.com/)
2. 注册并获取SendKey
3. 配置到 `serverchan_key`

#### 企业微信

1. 在企业微信群中添加机器人
2. 获取Webhook URL
3. 配置到 `wecom_webhook`
4. 设置 `type` 为 `"wecom"`

## 项目结构

```
hpc_paper_agent/
├── __init__.py          # 包初始化
├── config.py            # 配置管理
├── arxiv_fetcher.py     # arXiv论文获取
├── deepseek_filter.py   # DeepSeek筛选
├── email_sender.py      # 邮件发送
├── wechat_sender.py     # 微信通知
├── storage.py           # 数据库存储
├── main.py              # 主程序
├── scheduler.py         # 定时任务
├── requirements.txt     # 依赖列表
├── README.md           # 说明文档
├── config.json         # 配置文件（自动生成）
├── papers.db           # SQLite数据库（自动生成）
└── logs/               # 日志目录（自动生成）
```

## 日志

日志文件保存在 `logs/` 目录下，按日期命名。可以查看日志来了解运行状态和排查问题。

## 测试

### 快速测试

运行测试脚本验证各个模块是否正常工作：

```bash
# 运行完整测试套件
python test_agent.py
```

测试包括：
- ✓ 配置模块测试
- ✓ arXiv获取模块测试
- ✓ 存储模块测试
- ✓ 邮件发送模块测试（内容生成）
- ✓ 微信发送模块测试（内容生成）
- ✓ DeepSeek筛选模块测试（需要API密钥）
- ✓ 集成测试

### 试运行模式

在正式使用前，建议先运行试运行模式，模拟完整流程但不实际发送通知：

```bash
# 试运行（不发送邮件/微信）
python test_dry_run.py
```

试运行将：
- ✓ 从arXiv获取论文
- ✓ 使用DeepSeek筛选（如果配置了）
- ✓ 保存到数据库
- ✗ 不发送邮件/微信通知

### 手动测试单个模块

```python
# 测试arXiv获取
from arxiv_fetcher import ArxivFetcher
fetcher = ArxivFetcher(categories=["cs.DC"], max_results=5)
papers = fetcher.fetch_recent_papers(days=7)
print(f"获取到 {len(papers)} 篇论文")

# 测试DeepSeek筛选
from deepseek_filter import DeepSeekFilter
filter_obj = DeepSeekFilter(api_key="YOUR_KEY", relevance_threshold=0.7)
is_relevant, score, reason = filter_obj.is_relevant(papers[0])
print(f"相关性: {is_relevant}, 分数: {score}")

# 测试存储
from storage import PaperStorage
storage = PaperStorage("test.db")
storage.add_paper(papers[0], sent=False)
```

## 常见问题

### 1. DeepSeek API调用失败

- 检查API密钥是否正确
- 确认网络可以访问DeepSeek API服务
- 查看日志了解具体错误信息

### 2. 邮件发送失败

- Gmail用户需要使用应用专用密码，不是普通密码
- 检查SMTP服务器和端口配置
- 确认发送者邮箱已开启SMTP服务

### 3. 微信通知失败

- Server酱：检查SendKey是否正确
- 企业微信：检查Webhook URL是否有效

### 4. 没有获取到论文

- 检查arXiv分类是否正确
- 确认网络连接正常
- 查看日志了解详细信息

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 作者

高性能计算工程师
