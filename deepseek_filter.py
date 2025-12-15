"""
使用DeepSeek API筛选相关论文
"""
import openai
import math
from typing import List, Dict, Tuple
import logging
import json
from base_filter import BaseFilter

logger = logging.getLogger(__name__)


class DeepSeekFilter(BaseFilter):
    """使用DeepSeek筛选论文相关性"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", 
                 base_url: str = "https://api.deepseek.com",
                 relevance_threshold: float = 0.7,
                 keywords: List[str] = None,
                 coarse_filter_threshold: float = 0.3,
                 enable_coarse_filter: bool = True,
                 title_filter_threshold: float = 0.5):
        """
        初始化DeepSeek筛选器
        
        Args:
            api_key: DeepSeek API密钥
            model: 使用的模型名称（默认：deepseek-chat）
            base_url: API基础URL（默认：https://api.deepseek.com）
            relevance_threshold: 精筛相关性阈值（0-1），用于阶段3（标题+摘要）
            keywords: 关键词列表
            coarse_filter_threshold: 粗筛阈值（0-1），用于阶段1
            enable_coarse_filter: 是否启用粗筛
            title_filter_threshold: 标题筛选阈值（0-1），用于阶段2（仅标题）
        """
        super().__init__(relevance_threshold, keywords, coarse_filter_threshold, enable_coarse_filter, title_filter_threshold)
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url
        
        if api_key:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        else:
            self.client = None
            logger.warning("未提供DeepSeek API密钥，将使用关键词匹配")
    
    def _format_batch_prompt(self, batch_papers, title_only=True, return_reason=False):
        """
        batch_papers: List[Dict] , single paper包含 id, title, categories, summary
        title_only: Bool , default: True
                    True: 大模型初筛，筛选内容包括 categories + title + first sentence;
                    False: 大模型精筛，筛选内容包括 categories + title + summary;
        return_reason: Bool, default: False，注意包含reason时max_token可能超过，因此需要加返回string格式保护
                    True: 返回内容中包含筛选reason，一般用于精筛;
                    False: 返回内容中不包含筛选reason，一般用于初筛;

        """
        #构建论文内容text
        prompt_lines = []
        for p in batch_papers:
            # 1. 提取分类 (只取简写，如 cs.DC)
            cat = p['categories'].split('.')[1] if '.' in p['categories'] else p['categories']
            
            # title_only=True，筛选内容包括 categories + title + first sentence;
            # tile_only=False, 筛选内容包括 categories + title + summary;
            if title_only:
                # 2. 提取摘要的第一句话 (截断，防止太长)，简单的按句号分割，取前 200 字符足够判断
                first_sentence = p['summary'].split('.')[0][:200]
                
                # 3. 组合：[ID] [Tag] Title :: First_Sentence
                line = f"[ID: {p['id']}] [{cat}] {p['title']} :: {first_sentence}..."
                prompt_lines.append(line)
            else:
                # 3. 组合：[ID] [Tag] Title :: summary
                line = f"[ID: {p['id']}] [{cat}] {p['title']} :: {p['summary']}..."
                prompt_lines.append(line)
        
        context_text = "\n".join(prompt_lines)
        
        #构建 system Prompt
        if return_reason:
            format_str = (
                "2. **Output JSON ONLY** in this format:\n"
                "   {\"reviews\": [{\"id\": \"...\", \"score\": 0.8, \"reason\": \"reason...\"}, ...]}\n"
                "**reason MUST in this format:"
                """
                "用中文简要说明论文的核心内容后，另起一行按照以下内容结构化说明论文的核心研究问题:
                P(Problem):该论文解决的具体痛点或任务是什么?
                I(Intervention):提出了什么核心算法、架构或优化策略?
                C(Comparison):(若有)对比了哪些SOTA模型或Baseline?
                O(Outcome):在什么指标(如Latency, Accuracy, Mem)上取得了提升?
                T(Theory):它的核心理论假设或最终论点是什么? 核心贡献或对未来的启示" 
                """
                "**MUST return all papers with score and reason.\n"
                )
        else:
            format_str = ( 
                "2. **Output JSON ONLY** in this format:\n"
                "   {\"reviews\": [{\"id\": \"...\", \"score\": 0.8}, ...]}\n"
                "**MUST return all papers with score.\n"
                )
        
        labs_str = ", ".join(self.top_labs).lower()
        auth_str = ", ".join(self.star_authors).lower()
        keywords_str = ", ".join(self.keywords).lower()
        system_prompt = (
            "You are an expert HPC and AI System researcher. Score papers based on relevance to: "
            + keywords_str +
            # "**High Performance Computing, LLM Training/Inference Optimization, Distributed Systems, GPU Architecture, KV Cache, Kernel Fusion.**\n\n"
            "Note: Pay attention to the Category tags (e.g., DC, AR are high priority). "
            "**AUTHORITY BOOSTER:**\n"
            f"If a paper involves authors from these labs: [{labs_str}], OR authors listed here: [{auth_str}], boost the Score by +0.1 points(up to max 1.0).\n"
            "Identify famous authors/labs even if not explicitly listed but generally recognized as top-tier.\n\n"
            "**SCORING CRITERIA (0.0-1.0):**\n"
            "- 0.8-1.0: Critical System/Hardware optimization (e.g., FlashAttention, ZeRO, vLLM, Megatron, distributed training).\n"
            "- 0.6-0.8: Solid improvements in efficiency, quantization.\n"
            "- 0.3-0.6: Standard model architecture tweaks with minor system implications.\n"
            "- 0-0.3: Pure applications, Social Science, Surveys, or irrelevant topics.\n\n"
            "**INSTRUCTIONS:**\n"
            "1. Read [Category], Title, and Gist.\n"
            + format_str +
            "3. Be careful with 'meme titles'. Trust Category and Gist."
        )

        user_prompt = f"Here is the list of papers:\n\n{context_text}"
        
        return system_prompt, user_prompt

    def _parse_batch_response(self, response_text: str, papers: Dict, title_only: bool = True):
        try:
            result_json = json.loads(response_text)

            # 兼容性处理：有时候模型可能把 key 写成 results 或 papers，这里统一读取
            reviews = result_json.get("reviews", result_json.get("results", []))
            
            # 数据合并与清洗 :创建一个 id -> paper 的映射，方便快速查找
            paper_map = {paper['id']: paper for paper in papers}
            scored_papers = []

            # 根据阶段使用不同的阈值
            for item in reviews:
                p_id = item.get('id')
                score = item.get('score', 0)
                reason = item.get('reason', "")
                ###适配不同阶段的筛选阈值
                threshold = self.title_filter_threshold if title_only else self.relevance_threshold
                is_relevant = score >= threshold

                # 确保 ID 存在于原始列表中（防止幻觉）
                if p_id in paper_map:
                    original_paper = paper_map[p_id]
                    original_paper["relevance_score"] = score
                    original_paper["relevance_reason"] = reason
                    if is_relevant:
                        scored_papers.append(original_paper)
                        logger.debug(f"论文 '{original_paper['title'][:50]}...' 当前阶段通过 (分数: {score:.2f})")
                    else:
                        logger.debug(f"论文 '{original_paper['title'][:50]}...' 当前阶段未通过 (分数: {score:.2f})")

            # logger.info(f"[*] Filtered: {len(papers)} -> {len(scored_papers)}")
            return scored_papers
        except Exception as e:
            logger.error(f"❌ Error: DeepSeek筛选论文时出错: {e}", exc_info=True)
            # 出错时返回原list
            return papers

    def _filter_papers(self, papers: List[Dict], title_only: bool = False):
        """
        粗筛：使用关键词和摘要第一句进行第二步title筛选（大小写不敏感）
        
        Args:
            paper: 论文字典
            
        Returns:
            (是否通过粗筛, 相关性分数, 原因说明)
        """
        # 初筛时只对title分析，此时不返回reason
        system_prompt, user_prompt = self._format_batch_prompt(papers, title_only, not title_only)

        try:
            # 2. 调用 DeepSeek API
            logger.info(f"[*] Sending {len(papers)} papers to DeepSeek for filtering...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # 关键：强制 JSON 模式，DeepSeek 支持此功能
                response_format={"type": "json_object"}, 
                temperature=0.1, # 低温度，保证确定性
            )

            # 3. 获取并解析响应
            # result_text = response.choices[0].message.content.strip()
            result_text = response.choices[0].message.content
            # print(f"[*] Raw Response Snippet: {result_text}") # 调试打印前100字符

            return self._parse_batch_response(result_text, papers, title_only)
        except Exception as e:
            logger.error(f"❌ Error: DeepSeek筛选论文title时出错: {e}", exc_info=True)
            # 出错时返回原list
            return papers

    def filter_all_papers(self, all_papers: List[Dict], title_only: bool = True, batch_size: int = 150) -> List[Dict]:
        results = []
        # 分批循环
        for i in range(0, len(all_papers), batch_size):
            batch = all_papers[i : i + batch_size]
            logger.info(f"[*] Processing batch {i//batch_size + 1}/{math.ceil(len(all_papers)/batch_size)} ({len(batch)} papers)...")
            
            batch_results = self._filter_papers(batch, title_only)
            results.extend(batch_results)
        return results

    def is_relevant(self, paper: Dict, title_only: bool = False) -> Tuple[bool, float, str]:
        """
        判断论文是否与HPC相关
        
        Args:
            paper: 论文字典，包含title, summary等字段
            title_only: 是否仅使用标题进行筛选（True=仅标题，False=标题+摘要）
            
        Returns:
            (是否相关, 相关性分数, 原因说明)
        """
        if not self.client:
            # 如果没有配置API，使用简单的关键词匹配
            return self._simple_keyword_match(paper)
        
        try:
            # 构建提示词（根据title_only决定是否包含摘要）
            prompt = super()._build_prompt(paper, title_only=title_only)
            
            # 调用DeepSeek API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            result_text = response.choices[0].message.content.strip()
            
            # 解析结果
            return self._parse_response(result_text, paper, title_only)
            
        except Exception as e:
            logger.error(f"DeepSeek筛选论文时出错: {e}", exc_info=True)
            # 出错时回退到关键词匹配
            return self._simple_keyword_match(paper)
    
    def _parse_response(self, response_text: str, paper: Dict, title_only: bool = False) -> Tuple[bool, float, str]:
        """解析DeepSeek响应"""
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
            logger.warning(f"解析DeepSeek响应失败: {e}, 回退到关键词匹配")
            return self._simple_keyword_match(paper)

