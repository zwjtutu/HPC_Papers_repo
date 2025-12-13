# 论文筛选器配置说明

本系统支持通过配置选择不同的AI模型进行论文筛选，目前支持以下模型：

- **DeepSeek**: 使用DeepSeek API
- **Gemini**: 使用Google Gemini API
- **Qwen**: 使用阿里云通义千问API

## 配置方式

### 方式1: 使用deepseek

在 `config.json` 中添加 `filter` 配置项：

```json
{
  "filter": {
    "provider": "deepseek",
    "api_key": "YOUR_API_KEY",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "relevance_threshold": 0.7,
    "keywords": [
      "high performance computing",
      "HPC",
      "distributed computing"
    ]
  }
}
```

### 方式2: 使用Gemini

```json
{
  "filter": {
    "provider": "gemini",
    "api_key": "YOUR_GEMINI_API_KEY",
    "model": "gemini-pro",
    "relevance_threshold": 0.7,
    "keywords": [...]
  }
}
```

### 方式3: 使用Qwen

```json
{
  "filter": {
    "provider": "qwen",
    "api_key": "YOUR_QWEN_API_KEY",
    "model": "qwen-turbo",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "relevance_threshold": 0.7,
    "keywords": [...]
  }
}
```

## 配置参数说明

- `provider`: 模型提供商，可选值：`"deepseek"`, `"gemini"`, `"qwen"`
- `api_key`: API密钥（必需）
- `model`: 模型名称（可选，有默认值）
- `base_url`: API基础URL（仅OpenAI兼容接口需要，如DeepSeek和Qwen）
- `relevance_threshold`: 相关性阈值，0-1之间，越高越严格（默认：0.7）
- `keywords`: 关键词列表，用于备用关键词匹配

## 向后兼容

系统仍然支持旧的配置格式（如 `deepseek`、`gemini` 配置项），但建议迁移到新的统一格式。

## 获取API密钥

- **DeepSeek**: https://platform.deepseek.com/
- **Gemini**: https://makersuite.google.com/app/apikey
- **Qwen**: https://dashscope.console.aliyun.com/

## 注意事项

1. 如果未配置API密钥，系统将自动回退到关键词匹配模式
2. 不同模型的API调用方式可能不同，请确保网络连接正常
3. 建议先使用试运行模式测试配置是否正确

