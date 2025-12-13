"""
论文筛选器基类
定义统一的筛选接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class BaseFilter(ABC):
    """论文筛选器基类"""
    
    def __init__(self, relevance_threshold: float = 0.7, keywords: List[str] = None,
                 coarse_filter_threshold: float = 0.3, enable_coarse_filter: bool = True,
                 title_filter_threshold: float = 0.5):
        """
        初始化筛选器
        
        Args:
            relevance_threshold: 精筛相关性阈值（0-1），用于第3阶段LLM筛选（标题+摘要）
            keywords: 关键词列表
            coarse_filter_threshold: 粗筛阈值（0-1），用于第1阶段关键词匹配预筛选
            enable_coarse_filter: 是否启用粗筛
            title_filter_threshold: 标题筛选阈值（0-1），用于第2阶段LLM筛选（仅标题）
        """
        self.relevance_threshold = relevance_threshold
        self.keywords = keywords or []
        self.coarse_filter_threshold = coarse_filter_threshold
        self.enable_coarse_filter = enable_coarse_filter
        self.title_filter_threshold = title_filter_threshold
    
    @abstractmethod
    def is_relevant(self, paper: Dict, title_only: bool = False) -> Tuple[bool, float, str]:
        """
        判断论文是否与HPC相关（抽象方法）
        
        Args:
            paper: 论文字典，包含title, summary等字段
            title_only: 是否仅使用标题进行筛选（True=仅标题，False=标题+摘要）
            
        Returns:
            (是否相关, 相关性分数, 原因说明)
        """
        pass
    
    def _coarse_filter(self, paper: Dict) -> Tuple[bool, float, str]:
        """
        粗筛：使用关键词匹配进行初步筛选（大小写不敏感）
        
        Args:
            paper: 论文字典
            
        Returns:
            (是否通过粗筛, 相关性分数, 原因说明)
        """
        # 将文本转为小写，实现大小写不敏感匹配
        text = f"{paper['title']} {paper.get('summary', '')}".lower()
        matched_keywords = []
        for keyword in self.keywords:
            # 将关键词转为小写进行匹配，忽略大小写
            keyword_lower = keyword.lower().strip()
            if keyword_lower and keyword_lower in text:
                matched_keywords.append(keyword)
        
        # print('matched_keywords: ', matched_keywords)
        if matched_keywords:
            # 计算匹配分数：匹配的关键词数量 / 总关键词数量
            score = min(len(matched_keywords) / max(len(self.keywords), 1), 1.0)
            # 粗筛使用较低的阈值，只过滤明显不相关的论文
            is_passed = score >= self.coarse_filter_threshold
            reason = f"粗筛匹配到关键词: {', '.join(matched_keywords)} (分数: {score:.2f})"
            return (is_passed, score, reason)
        else:
            return (False, 0.0, "粗筛未匹配到相关关键词")
    
    def _simple_keyword_match(self, paper: Dict) -> Tuple[bool, float, str]:
        """
        简单的关键词匹配（备用方案，当LLM不可用时使用，大小写不敏感）
        
        Args:
            paper: 论文字典
            
        Returns:
            (是否相关, 相关性分数, 原因说明)
        """
        # 将文本转为小写，实现大小写不敏感匹配
        text = f"{paper['title']} {paper.get('summary', '')}".lower()
        matched_keywords = []
        for keyword in self.keywords:
            # 将关键词转为小写进行匹配，忽略大小写
            keyword_lower = keyword.lower().strip()
            if keyword_lower and keyword_lower in text:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            score = min(len(matched_keywords) / max(len(self.keywords), 1), 1.0)
            is_relevant = score >= self.relevance_threshold
            reason = f"匹配到关键词: {', '.join(matched_keywords)}"
            return (is_relevant, score, reason)
        else:
            return (False, 0.0, "未匹配到相关关键词")
    
    def _build_prompt(self, paper: Dict, title_only: bool = False) -> str:
        """
        构建提示词（通用方法）
        
        Args:
            paper: 论文字典
            title_only: 是否仅使用标题（True=仅标题，False=标题+摘要）
            
        Returns:
            提示词字符串
        """
        keywords_str = ", ".join(self.keywords)
        
        if title_only:
            prompt = f"""你是一位AI高性能计算(HPC)领域的专家。请仅根据论文标题评估以下论文是否与高性能计算、分布式计算、并行计算、GPU计算、超级计算、端到端训练优化、训练优化等相关。

论文标题: {paper['title']}

相关关键词包括: {keywords_str}

请以JSON格式回复，包含以下字段:
- "relevant": true/false (是否相关)
- "score": 0.0-1.0 (相关性分数，1.0表示完全相关)
- "reason": "无"
只返回JSON，不要其他文字。"""
        else:
            prompt = f"""你是一位AI高性能计算(HPC)领域的专家。请评估以下论文是否与高性能计算、分布式计算、并行计算、GPU计算、超级计算、端到端训练优化、训练优化等相关。

论文标题: {paper['title']}
论文摘要: {paper.get('summary', '')[:2000]}

相关关键词包括: {keywords_str}

请以JSON格式回复，包含以下字段:
- "relevant": true/false (是否相关)
- "score": 0.0-1.0 (相关性分数，1.0表示完全相关)
- "reason": "用中文简要说明原因后，另起一行按照以下内容结构化说明论文的核心研究问题:
            P(Problem/Population):它研究的核心问题或群体是什么?
            I(Intervention/Interest):采用了什么新方法、干预或技术?
            C(Comparison):(如果有)它的比较对象是什么?
            0(Outcome):它测量的主要结果是什么?
            T(Theory/Thesis):它的核心理论假设或最终论点是什么?"
只返回JSON，不要其他文字。"""
        
        return prompt
    
    def filter_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        批量筛选论文：3阶段筛选（关键词粗筛 -> 标题LLM筛选 -> 标题+摘要LLM筛选）
        
        Args:
            papers: 论文列表
            
        Returns:
            筛选后的论文列表，每篇论文添加了relevance_score和relevance_reason字段
        """
        if not papers:
            return []
        
        total_papers = len(papers)
        
        # 阶段1: 粗筛（关键词匹配）
        stage1_papers = []
        if self.enable_coarse_filter:
            logger.info(f"阶段1: 粗筛（关键词匹配，阈值: {self.coarse_filter_threshold:.2f}）...")
            for paper in papers:
                is_passed, score, reason = self._coarse_filter(paper)
                if is_passed:
                    paper["coarse_score"] = score
                    paper["coarse_reason"] = reason  
                    stage1_papers.append(paper)
                else:
                    # 粗筛未通过的论文，记录信息但不进入后续阶段
                    paper["relevance_score"] = score
                    paper["relevance_reason"] = f"阶段1未通过: {reason}"
                    logger.debug(f"论文 '{paper['title'][:50]}...' 阶段1未通过 (分数: {score:.2f})")
            
            logger.info(f"阶段1完成: {len(stage1_papers)}/{total_papers} 篇论文通过粗筛")
            if len(stage1_papers) == 0:
                logger.info("阶段1后无论文，跳过后续阶段")
                return []
        else:
            stage1_papers = papers
            logger.info("阶段1已禁用，所有论文进入阶段2")
        
        # 阶段2: 标题LLM筛选
        logger.info(f"阶段2: 标题LLM筛选（阈值: {self.title_filter_threshold:.2f}）...")
        stage2_papers = []
        stage2_token_saved = 0
        
        for paper in stage1_papers:
            is_relevant, score, reason = self.is_relevant(paper, title_only=True)
            
            # is_relevant已经根据title_filter_threshold判断过了，这里直接使用
            if is_relevant:
                paper["title_score"] = score
                paper["title_reason"] = reason 
                stage2_papers.append(paper)
                logger.debug(f"论文 '{paper['title'][:50]}...' 阶段2通过 (分数: {score:.2f})")
            else:
                # 阶段2未通过的论文，记录信息但不进入阶段3
                paper["relevance_score"] = score
                paper["relevance_reason"] = f"{paper.get('coarse_reason', '')} -> 阶段2未通过: {reason}"
                logger.debug(f"论文 '{paper['title'][:50]}...' 阶段2未通过 (分数: {score:.2f})")
                stage2_token_saved += 1
        
        logger.info(f"阶段2完成: {len(stage2_papers)}/{len(stage1_papers)} 篇论文通过标题筛选")
        if len(stage2_papers) == 0:
            logger.info("阶段2后无论文，跳过阶段3")
            return []
        
        # 阶段3: 标题+摘要LLM筛选
        logger.info(f"阶段3: 标题+摘要LLM筛选（阈值: {self.relevance_threshold:.2f}）...")
        final_papers = []
        
        for paper in stage2_papers:
            is_relevant, score, reason = self.is_relevant(paper, title_only=False)
            
            # is_relevant已经根据relevance_threshold判断过了，这里直接使用
            # 保留所有阶段的信息
            if "coarse_reason" in paper:
                ###Modify by zwj, only step3 reason
                #paper["relevance_reason"] = f"{paper.get('coarse_reason', '')} -> 阶段2: {paper.get('title_reason', '')} -> 阶段3: {reason}"
                paper["relevance_reason"] = f"{reason}"
            else:
                paper["relevance_reason"] = f"阶段2: {paper.get('title_reason', '')} -> 阶段3: {reason}"
            paper["relevance_score"] = score
            
            if is_relevant:
                final_papers.append(paper)
                logger.info(f"论文 '{paper['title'][:50]}...' 最终相关 (分数: {score:.2f})")
            else:
                logger.debug(f"论文 '{paper['title'][:50]}...' 阶段3未通过 (分数: {score:.2f})")
        
        logger.info(f"筛选完成: {len(final_papers)}/{total_papers} 篇论文最终相关")
        
        # 计算token节省
        stage1_saved = total_papers - len(stage1_papers)
        stage2_saved = len(stage1_papers) - len(stage2_papers)
        total_saved = stage1_saved + stage2_saved
        total_llm_calls = len(stage1_papers) + len(stage2_papers)  # 阶段2和阶段3的LLM调用
        
        logger.info(f"Token节省统计:")
        logger.info(f"  - 阶段1过滤: {stage1_saved} 篇论文（关键词匹配，无需LLM）")
        logger.info(f"  - 阶段2过滤: {stage2_saved} 篇论文（仅标题LLM，节省摘要token）")
        logger.info(f"  - 总LLM调用: {total_llm_calls} 次（阶段2: {len(stage1_papers)}次，阶段3: {len(stage2_papers)}次）")
        logger.info(f"  - 相比单阶段筛选，节省约 {((total_papers - total_llm_calls) / total_papers * 100):.1f}% 的完整LLM调用")
        
        return final_papers

