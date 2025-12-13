# LRU存储管理说明

## 功能概述

数据库模块现在支持LRU（Least Recently Used，最近最少使用）存储管理机制。当存储的论文数量超过配置的上限时，系统会自动删除最久未访问的论文。

## 配置方法

在 `config.json` 的 `storage` 配置项中添加 `max_storage_size` 参数：

```json
{
  "storage": {
    "database_path": "papers.db",
    "log_path": "logs",
    "max_storage_size": 1000
  }
}
```

### 参数说明

- `max_storage_size`: 最大存储论文数量
  - `0` 或未设置：无限制（默认行为）
  - 大于 `0`：启用LRU机制，当达到上限时自动删除最久未访问的论文

## LRU工作原理

1. **访问时间记录**：每次访问论文时（如检查是否存在、获取论文列表），系统会更新该论文的 `last_accessed` 时间戳。

2. **自动清理**：当添加新论文时，如果当前存储数量已达到或超过 `max_storage_size`，系统会：
   - 查找最久未访问的论文（按 `last_accessed` 排序，NULL值优先）
   - 删除足够数量的旧论文，使存储数量保持在 `max_storage_size` 以下
   - 记录删除操作到日志

3. **访问时间更新时机**：
   - `paper_exists()`: 检查论文是否存在时
   - `get_recent_papers()`: 获取论文列表时
   - `add_paper()`: 添加或更新论文时

## 使用示例

### 示例1: 设置存储上限为1000篇

```json
{
  "storage": {
    "max_storage_size": 1000
  }
}
```

当存储超过1000篇论文时，系统会自动删除最久未访问的论文。

### 示例2: 无限制存储（默认）

```json
{
  "storage": {
    "max_storage_size": 0
  }
}
```

或者不设置 `max_storage_size`，系统将无限制存储论文。

## 查看存储统计

可以使用 `get_storage_stats()` 方法查看存储统计信息：

```python
from storage import PaperStorage

storage = PaperStorage("papers.db", max_storage_size=1000)
stats = storage.get_storage_stats()

print(f"总论文数: {stats['total']}")
print(f"已发送: {stats['sent']}")
print(f"未发送: {stats['unsent']}")
print(f"从未访问: {stats['never_accessed']}")
print(f"存储上限: {stats['max_storage_size']}")
print(f"最久未访问的5篇论文:")
for paper in stats['oldest_papers']:
    print(f"  - {paper['title']} (最后访问: {paper['last_accessed']})")
```

## 注意事项

1. **数据迁移**：如果数据库已存在但没有 `last_accessed` 字段，系统会在首次运行时自动添加该字段。

2. **NULL值处理**：从未访问过的论文（`last_accessed` 为 NULL）会被优先删除。

3. **删除策略**：当需要删除时，系统会按以下顺序选择：
   - 首先删除 `last_accessed` 为 NULL 的论文
   - 然后删除 `last_accessed` 最早的论文
   - 如果 `last_accessed` 相同，则按 `created_at` 排序

4. **日志记录**：所有删除操作都会记录到日志中，包括删除的论文数量和标题。

5. **性能考虑**：LRU清理操作在添加论文时执行，不会影响查询性能。

## 数据库结构

新增的 `last_accessed` 字段用于记录论文的最后访问时间：

```sql
CREATE TABLE papers (
    ...
    last_accessed TEXT,  -- ISO格式的时间戳
    ...
)
```

索引已自动创建，确保LRU查询性能：

```sql
CREATE INDEX idx_last_accessed ON papers(last_accessed);
```

