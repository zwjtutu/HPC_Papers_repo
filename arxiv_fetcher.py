"""
arXiv论文获取模块
"""
import feedparser
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ArxivFetcher:
    """arXiv论文获取器"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self, categories: List[str] = None, max_results: int = 50, max_retries: int = 3):
        """
        初始化arXiv获取器
        
        Args:
            categories: arXiv分类列表，如 ['cs.DC', 'cs.Distributed']
            max_results: 最大获取数量
        """
        self.categories = categories or ["cs.DC", "cs.Distributed", "cs.PF"]
        self.max_results = max_results
        self.max_retries = max_retries
    
    def fetch_recent_papers(self, days: int = 1) -> List[Dict]:
        """
        获取最近几天的论文
        
        Args:
            days: 获取最近几天的论文，默认1天
            
        Returns:
            论文列表，每个论文包含id, title, authors, summary, published, link等字段
        """
        papers = []
        
        # 构建查询字符串
        # 查询最近提交的论文
        query_parts = []
        for category in self.categories:
            query_parts.append(f"cat:{category}")
        
        query = " OR ".join(query_parts)
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # arXiv API参数
        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        
        try:
            url = f"{self.BASE_URL}?{urlencode(params)}"
            logger.info(f"正在从arXiv获取论文: {url}")
            
            # arxiv拉取逻辑，若首次失败，将重新尝试3次
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = requests.get(url, timeout=100)
                    response.raise_for_status()
                    break  # 请求成功，跳出重试循环
                except Exception as e:
                    logger.warning(f"第 {attempt} 次获取 arXiv 论文失败: {e}")
                    if attempt == self.max_retries:
                        logger.error(f"多次尝试后仍无法获取 arXiv 数据: {e}", exc_info=True)
                        return []
                    time.sleep(2)  # 等待2秒后重试
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                # 解析发布日期
                published = datetime(*entry.published_parsed[:6])
                
                # 只获取指定日期范围内的论文
                if published < start_date:
                    continue
                
                # 提取作者列表
                authors = [author.name for author in entry.get("authors", [])]
                
                paper = {
                    "id": entry.id.split("/")[-1],
                    "arxiv_id": entry.id.split("/")[-1],
                    "title": entry.title.replace("\n", " ").strip(),
                    "authors": authors,
                    "summary": entry.summary.replace("\n", " ").strip(),
                    "published": published.isoformat(),
                    "link": entry.link,
                    "categories": [tag.term for tag in entry.get("tags", [])],
                    "pdf_link": None
                }
                
                # 提取PDF链接
                for link in entry.get("links", []):
                    if link.get("type") == "application/pdf":
                        paper["pdf_link"] = link.get("href")
                        break
                
                papers.append(paper)
            
            logger.info(f"成功获取 {len(papers)} 篇论文")
            
        except Exception as e:
            logger.error(f"获取arXiv论文时出错: {e}", exc_info=True)
        
        return papers
    
    def fetch_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        获取指定日期范围内的论文
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            论文列表
        """
        papers = []
        current_date = start_date
        
        while current_date <= end_date:
            days = (end_date - current_date).days + 1
            batch_papers = self.fetch_recent_papers(days=min(days, 7))
            
            for paper in batch_papers:
                paper_date = datetime.fromisoformat(paper["published"])
                if start_date <= paper_date <= end_date:
                    papers.append(paper)
            
            current_date += timedelta(days=7)
        
        # 去重
        seen_ids = set()
        unique_papers = []
        for paper in papers:
            if paper["id"] not in seen_ids:
                seen_ids.add(paper["id"])
                unique_papers.append(paper)
        
        return unique_papers
