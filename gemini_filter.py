"""
使用Gemini API筛选相关论文
"""
import google.generativeai as genai
from typing import Dict, Tuple
import logging
import json
from base_filter import BaseFilter

logger = logging.getLogger(__name__)


class GeminiFilter(BaseFilter):
    """使用Gemini筛选论文相关性"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro",
                 relevance_threshold: float = 0.7,
                 keywords: list = None,
                 coarse_filter_threshold: float = 0.3,
                 enable_coarse_filter: bool = True,
                 title_filter_threshold: float = 0.5):
        """
        初始化Gemini筛选器
        
        Args:
            api_key: Gemini API密钥
            model: 使用的模型名称（默认：gemini-pro）
            relevance_threshold: 精筛相关性阈值（0-1），用于阶段3（标题+摘要）
            keywords: 关键词列表
            coarse_filter_threshold: 粗筛阈值（0-1），用于阶段1
            enable_coarse_filter: 是否启用粗筛
            title_filter_threshold: 标题筛选阈值（0-1），用于阶段2（仅标题）
        """
        super().__init__(relevance_threshold, keywords, coarse_filter_threshold, enable_coarse_filter, title_filter_threshold)
        self.api_key = api_key
        self.model_name = model
        
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model)
        else:
            self.model = None
            logger.warning("未提供Gemini API密钥，将使用关键词匹配")
    
    def is_relevant(self, paper: Dict, title_only: bool = False) -> Tuple[bool, float, str]:
        """
        判断论文是否与HPC相关
        
        Args:
            paper: 论文字典，包含title, summary等字段
            title_only: 是否仅使用标题进行筛选（True=仅标题，False=标题+摘要）
            
        Returns:
            (是否相关, 相关性分数, 原因说明)
        """
        if not self.model:
            # 如果没有配置API，使用简单的关键词匹配
            return self._simple_keyword_match(paper)
        
        try:
            # 构建提示词（根据title_only决定是否包含摘要）
            prompt = super()._build_prompt(paper, title_only=title_only)
            
            # 调用Gemini API
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # 解析结果
            return self._parse_response(result_text, paper, title_only)
            
        except Exception as e:
            logger.error(f"Gemini筛选论文时出错: {e}", exc_info=True)
            # 出错时回退到关键词匹配
            return self._simple_keyword_match(paper)
    
    def _parse_response(self, response_text: str, paper: Dict, title_only: bool = False) -> Tuple[bool, float, str]:
        """解析Gemini响应"""
        try:
            # 尝试提取JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            result = json.loads(response_text)
            
            relevant = result.get("relevant", False)
            score = float(result.get("score", 0.0))
            reason = result.get("reason", "未提供原因")
            
            # 根据阶段使用不同的阈值
            threshold = self.title_filter_threshold if title_only else self.relevance_threshold
            is_relevant = relevant and score >= threshold
            
            return (is_relevant, score, reason)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"解析Gemini响应失败: {e}, 回退到关键词匹配")
            return self._simple_keyword_match(paper)

