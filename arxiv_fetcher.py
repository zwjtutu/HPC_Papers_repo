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
            categories: arXiv分类列表，如 ['cs.DC', 'cs.PF']
            max_results: 最大获取数量
        """
        self.categories = categories or ["cs.DC", "cs.PF"]
        self.max_results = max_results
        self.max_retries = max_retries
        
        # ArXiv API 限制，建议每次批量查询不超过 50-100 个 ID
        self.arxiv_batch_size = 50

    def get_ids_from_rss(self, days_lookback=3):
        """
        第一阶段：从 RSS 获取候选论文 ID，并按时间初筛
        """
        unique_ids = set()
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_lookback)
        logger.info(f"[*] 正在从 RSS 拉取数据，筛选时间窗口: {start_date.strftime('%Y-%m-%d')} 至今...")

        for category in self.categories:
            rss_url = f"https://rss.arxiv.org/atom/{category}"
            logger.info(f"    - Scanning {category} ...")
            
            try:
                #拉取arxiv RSS数据
                try:
                    response = requests.get(rss_url, timeout=100)
                    response.raise_for_status()

                    feed = feedparser.parse(response.content)
                    if not feed.entries:
                        logger.warning(f"      ⚠️ Warning: {category} RSS is empty failed.")
                        continue
                except Exception as e:
                    logger.error(f"      ⚠️ Error: {category} RSS is failed.")
                    continue

                count = 0
                for entry in feed.entries:
                    # entry.published 是字符串，需要解析为 datetime 对象
                    # ArXiv RSS 时间格式通常为: "Mon, 15 Dec 2025 00:00:00 GMT"
                    # 使用 dateutil.parser 可以自动处理各种格式
                    try:
                        # 解析发布日期
                        # 尝试获取发布时间，如果没有则用更新时间   entry.get("published", entry.get("updated"))
                        published = datetime(*entry.published_parsed[:6])
                        # print(f'published:{published}, start_date:{start_date}')
                        
                        # 核心过滤逻辑：只保留最近 n 天的
                        if published >= start_date:
                            # 提取 ID: oai:arXiv.org:2511.11907v2 -> 2511.11907
                            paper_id = entry.id.split(':')[-1].split('v')[0] # 去掉可能存在的版本号v1
                            unique_ids.add(paper_id)
                            count += 1
                    except Exception as e:
                        logger.error(f"      Error parsing date for entry: {e}")
                        continue
                
                logger.info(f"      -> Found {count} recent papers in {category}")
                
                # 礼貌性延时，防止请求过快被 Ban
                time.sleep(3)

            except Exception as e:
                logger.error(f"    ❌ Error fetching RSS {category}: {e}")

        logger.info(f"[*] RSS 阶段结束。共收集到 {len(unique_ids)} 个不重复的论文 ID。")
        return list(unique_ids)

    def fetch_metadata_via_api(self, paper_ids):
        """
        第二阶段：利用 ID 列表批量查询 API 获取详细信息
        """
        if not paper_ids:
            return []

        logger.info(f"[*] 开始通过 API 批量查询详情，共 {len(paper_ids)} 篇...")
        all_papers = []

        # 分批处理 (Chunking)
        for i in range(0, len(paper_ids), self.arxiv_batch_size):
            chunk = paper_ids[i : i + self.arxiv_batch_size]
            id_list_str = ",".join(chunk)
            
            # 构造 API URL
            url = f"http://export.arxiv.org/api/query?id_list={id_list_str}&max_results={self.arxiv_batch_size}"
            
            try:
                # 调用 API (ArXiv API 返回的是 Atom XML，正好也可以用 feedparser 解析)
                # with urllib.request.urlopen(url) as response:
                response = requests.get(url, timeout=100)
                response.raise_for_status()
                # xml_response = response.read()
                # feed = feedparser.parse(xml_response)
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries:
                    # 提取我们需要的数据字段
                    paper_data = {
                        "id": entry.id.split('/')[-1],
                        "arxiv_id": entry.id.split('/')[-1],
                        "title": entry.title.replace('\n', ' ').strip(), # 清洗标题换行符
                        "summary": entry.summary.replace('\n', ' ').strip(), # 清洗摘要
                        "authors": [author.name for author in entry.authors],
                        "published": datetime(*entry.published_parsed[:6]).isoformat(),
                        "link": entry.link,
                        # "category": entry.arxiv_primary_category['term'],
                        "categories": [tag.term for tag in entry.get("tags", [])],
                        "pdf_link": None
                    }
                    all_papers.append(paper_data)
                
                logger.info(f"    - Batch {i // self.arxiv_batch_size + 1} done. Fetched {len(feed.entries)} items.")
                
                # 必须延时！ArXiv API 对并发限制很严，建议 3 秒
                time.sleep(3)

            except Exception as e:
                logger.error(f"    ❌ Batch request failed: {e}")

        return all_papers

    def fetch_recent_papers_rss(self, days: int = 1) -> List[Dict]:
        """
        使用RSS接口获取最近几天的论文
        
        Args:
            days: 获取最近几天的论文，默认1天
            
        Returns:
            论文列表，每个论文包含id, title, authors, summary, published, link等字段
        """ 
        paper_ids = self.get_ids_from_rss(days)
        papers = self.fetch_metadata_via_api(paper_ids)
        return papers

    def fetch_recent_papers(self, days: int = 1) -> List[Dict]:
        """
        使用API接口获取最近几天的论文
        
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
                    time.sleep(3)  # 等待2秒后重试
            
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
            # batch_papers = self.fetch_recent_papers(days=min(days, 7))
            batch_papers = self.fetch_recent_papers_rss(days=min(days, 7))
            
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
