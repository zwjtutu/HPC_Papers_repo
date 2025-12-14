"""
筛选器工厂类
根据配置创建对应的筛选器实例
"""
import os
import logging
from typing import Optional
from base_filter import BaseFilter
from deepseek_filter import DeepSeekFilter
# from gemini_filter import GeminiFilter
from qwen_filter import QwenFilter

logger = logging.getLogger(__name__)


class FilterFactory:
    """筛选器工厂类"""
    
    @staticmethod
    def create_filter(filter_config: dict) -> Optional[BaseFilter]:
        """
        根据配置创建筛选器实例
        
        Args:
            filter_config: 筛选器配置字典，包含：
                - provider: 模型提供商 ("deepseek", "gemini", "qwen")
                - api_key: API密钥
                - model: 模型名称（可选）
                - base_url: API基础URL（可选，仅OpenAI兼容接口）
                - relevance_threshold: 相关性阈值（可选）
                - keywords: 关键词列表（可选）
        
        Returns:
            筛选器实例，如果配置无效则返回None
        """
        ###Add for secret env
        llmapikey_env = os.environ.get("LLM_API_KEY")

        provider = filter_config.get("provider", "").lower()
        api_key = filter_config.get("api_key", "")
        api_key = llmapikey_env if llmapikey_env else api_key
        model = filter_config.get("model", "")
        base_url = filter_config.get("base_url", "")
        relevance_threshold = filter_config.get("relevance_threshold", 0.7)
        keywords = filter_config.get("keywords", [])
        coarse_filter_threshold = filter_config.get("coarse_filter_threshold", 0.3)
        enable_coarse_filter = filter_config.get("enable_coarse_filter", True)
        title_filter_threshold = filter_config.get("title_filter_threshold", 0.5)
        
        if not provider:
            logger.warning("未指定筛选器提供商，将使用关键词匹配")
            return None
        
        try:
            if provider == "deepseek":
                return DeepSeekFilter(
                    api_key=api_key,
                    model=model or "deepseek-chat",
                    base_url=base_url or "https://api.deepseek.com",
                    relevance_threshold=relevance_threshold,
                    keywords=keywords,
                    coarse_filter_threshold=coarse_filter_threshold,
                    enable_coarse_filter=enable_coarse_filter,
                    title_filter_threshold=title_filter_threshold
                )
            # elif provider == "gemini":
            #     return GeminiFilter(
            #         api_key=api_key,
            #         model=model or "gemini-pro",
            #         relevance_threshold=relevance_threshold,
            #         keywords=keywords
            #     )
            elif provider == "qwen":
                return QwenFilter(
                    api_key=api_key,
                    model=model or "qwen-turbo",
                    base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    relevance_threshold=relevance_threshold,
                    keywords=keywords,
                    coarse_filter_threshold=coarse_filter_threshold,
                    enable_coarse_filter=enable_coarse_filter,
                    title_filter_threshold=title_filter_threshold
                )
            else:
                logger.warning(f"不支持的筛选器提供商: {provider}")
                return None
        except Exception as e:
            logger.error(f"创建筛选器失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def create_from_config(config: dict) -> Optional[BaseFilter]:
        """
        从配置对象创建筛选器
        
        Args:
            config: 配置对象，应包含 "filter" 或 "ai_filter" 键
        
        Returns:
            筛选器实例
        """
        # 优先使用新的统一配置格式
        filter_config = config.get("filter") or config.get("ai_filter")
        
        if filter_config:
            return FilterFactory.create_filter(filter_config)
        
        # 兼容旧配置格式
        # 检查是否有deepseek配置
        deepseek_config = config.get("deepseek")
        if deepseek_config and deepseek_config.get("api_key"):
            logger.info("使用旧配置格式（deepseek），建议迁移到新格式")
            filter_config = {
                "provider": "deepseek",
                "api_key": deepseek_config.get("api_key", ""),
                "model": deepseek_config.get("model", "deepseek-chat"),
                "base_url": deepseek_config.get("base_url", "https://api.deepseek.com"),
                "relevance_threshold": deepseek_config.get("relevance_threshold", 0.7),
                "keywords": deepseek_config.get("keywords", []),
                "coarse_filter_threshold": deepseek_config.get("coarse_filter_threshold", 0.3),
                "enable_coarse_filter": deepseek_config.get("enable_coarse_filter", True),
                "title_filter_threshold": deepseek_config.get("title_filter_threshold", 0.5)
            }
            return FilterFactory.create_filter(filter_config)
        
        # 检查是否有gemini配置
        gemini_config = config.get("gemini")
        if gemini_config and gemini_config.get("api_key"):
            logger.info("使用旧配置格式（gemini），建议迁移到新格式")
            filter_config = {
                "provider": "gemini",
                "api_key": gemini_config.get("api_key", ""),
                "model": gemini_config.get("model", "gemini-pro"),
                "relevance_threshold": gemini_config.get("relevance_threshold", 0.7),
                "keywords": gemini_config.get("keywords", []),
                "coarse_filter_threshold": gemini_config.get("coarse_filter_threshold", 0.3),
                "enable_coarse_filter": gemini_config.get("enable_coarse_filter", True),
                "title_filter_threshold": gemini_config.get("title_filter_threshold", 0.5)
            }
            return FilterFactory.create_filter(filter_config)
        
        logger.warning("未找到筛选器配置，将使用关键词匹配")
        return None

