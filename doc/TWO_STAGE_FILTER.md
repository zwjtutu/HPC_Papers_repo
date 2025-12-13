# 两阶段筛选说明

## 功能概述

论文筛选现在采用**两阶段筛选机制**，通过粗筛和精筛两步，大幅节省大模型token使用：

1. **粗筛（Coarse Filter）**：使用关键词匹配快速过滤明显不相关的论文
2. **精筛（Fine Filter）**：对粗筛通过的论文使用LLM进行精确筛选

## 工作原理

### 阶段1: 粗筛（关键词匹配）

- **目的**：快速过滤明显不相关的论文，减少需要调用LLM的论文数量
- **方法**：关键词匹配
- **阈值**：`coarse_filter_threshold`（默认：0.3）
- **计算方式**：匹配的关键词数量 / 总关键词数量

### 阶段2: 精筛（LLM筛选）

- **目的**：对粗筛通过的论文进行精确判断
- **方法**：调用大模型API（DeepSeek/Gemini/Qwen）
- **阈值**：`relevance_threshold`（默认：0.7）
- **节省效果**：只对粗筛通过的论文调用LLM，可节省50-80%的token

## 配置说明

在 `config.json` 的 `filter` 配置项中：

```json
{
  "filter": {
    "provider": "deepseek",
    "api_key": "YOUR_API_KEY",
    "model": "deepseek-chat",
    "relevance_threshold": 0.7,        // 精筛阈值（LLM筛选）
    "coarse_filter_threshold": 0.3,    // 粗筛阈值（关键词匹配）
    "enable_coarse_filter": true,       // 是否启用粗筛
    "keywords": [
      "high performance computing",
      "HPC",
      "distributed computing"
    ]
  }
}
```

### 参数说明

- **`relevance_threshold`** (0-1): 精筛相关性阈值
  - 用于LLM筛选阶段
  - 越高越严格，默认0.7
  - 建议范围：0.6-0.8

- **`coarse_filter_threshold`** (0-1): 粗筛阈值
  - 用于关键词匹配预筛选
  - 越低越宽松，默认0.3
  - 建议范围：0.2-0.5
  - 设置过低可能漏掉相关论文，设置过高可能无法有效过滤

- **`enable_coarse_filter`** (bool): 是否启用粗筛
  - `true`: 启用两阶段筛选（推荐，节省token）
  - `false`: 禁用粗筛，所有论文直接进入LLM筛选

- **`keywords`**: 关键词列表
  - 用于粗筛的关键词匹配
  - 建议包含领域相关的核心术语

## 使用示例

### 示例1: 启用粗筛（推荐）

```json
{
  "filter": {
    "provider": "deepseek",
    "api_key": "YOUR_KEY",
    "relevance_threshold": 0.7,
    "coarse_filter_threshold": 0.3,
    "enable_coarse_filter": true,
    "keywords": ["HPC", "distributed computing", "parallel computing"]
  }
}
```

**效果**：
- 100篇论文 → 粗筛通过30篇 → LLM筛选10篇
- 节省70%的LLM调用

### 示例2: 禁用粗筛（所有论文都用LLM）

```json
{
  "filter": {
    "provider": "deepseek",
    "api_key": "YOUR_KEY",
    "relevance_threshold": 0.7,
    "enable_coarse_filter": false,
    "keywords": ["HPC", "distributed computing"]
  }
}
```

**效果**：
- 100篇论文 → 直接LLM筛选 → 10篇相关
- 所有论文都调用LLM，token消耗较大

### 示例3: 调整粗筛阈值

```json
{
  "filter": {
    "coarse_filter_threshold": 0.2,  // 更宽松，更多论文进入精筛
    "relevance_threshold": 0.8        // 精筛更严格
  }
}
```

## 筛选流程

```
原始论文列表 (100篇)
    ↓
[粗筛] 关键词匹配 (threshold=0.3)
    ↓
通过粗筛 (30篇)    未通过 (70篇，直接标记为不相关)
    ↓
[精筛] LLM筛选 (threshold=0.7)
    ↓
最终相关论文 (10篇)
```

## Token节省效果

假设每篇论文的LLM调用消耗约500 tokens：

| 场景 | 论文数 | LLM调用 | Token消耗 | 节省 |
|------|--------|---------|-----------|------|
| 无粗筛 | 100 | 100 | 50,000 | 0% |
| 粗筛(30%通过) | 100 | 30 | 15,000 | 70% |
| 粗筛(20%通过) | 100 | 20 | 10,000 | 80% |

## 日志输出

筛选过程会输出详细日志：

```
步骤1: 粗筛（关键词匹配，阈值: 0.30）...
粗筛完成: 30/100 篇论文通过粗筛
步骤2: 精筛（LLM筛选，阈值: 0.70）...
筛选完成: 10/100 篇论文最终相关
Token节省: 粗筛过滤了 70 篇论文，节省约 70.0% 的LLM调用
```

## 注意事项

1. **粗筛阈值设置**：
   - 过低（<0.2）：可能漏掉相关论文
   - 过高（>0.5）：过滤效果不明显
   - 建议：0.2-0.4

2. **关键词质量**：
   - 关键词越准确，粗筛效果越好
   - 建议包含领域核心术语和常见缩写

3. **性能平衡**：
   - 粗筛阈值低 → 更多论文进入精筛 → 更准确但token消耗大
   - 粗筛阈值高 → 更少论文进入精筛 → 节省token但可能漏掉相关论文

4. **向后兼容**：
   - 如果未配置粗筛参数，默认启用粗筛（threshold=0.3）
   - 旧配置会自动使用默认值

## 最佳实践

1. **首次使用**：启用粗筛，使用默认阈值0.3
2. **观察效果**：查看日志中的"Token节省"比例
3. **调整优化**：
   - 如果节省比例<50%，考虑降低粗筛阈值
   - 如果漏掉相关论文，考虑降低粗筛阈值或增加关键词
   - 如果token消耗仍较大，考虑提高粗筛阈值

