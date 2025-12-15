"""
微信通知模块
支持Server酱和企业微信
"""
import requests
import re
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def _get_alphaxiv_link_wechat(paper: Dict) -> str:
    """
    从论文信息生成alphaxiv.org链接
    
    Args:
        paper: 论文字典，包含link或arxiv_id字段
        
    Returns:
        alphaxiv.org链接，如果无法提取则返回空字符串
    """
    # 优先使用arxiv_id
    arxiv_id = paper.get('arxiv_id', '')
    
    # 如果没有arxiv_id，尝试从link中提取
    if not arxiv_id:
        link = paper.get('link', '')
        if link:
            # 匹配格式：https://arxiv.org/abs/2301.12345 或 https://arxiv.org/pdf/2301.12345.pdf
            match = re.search(r'arxiv\.org/(?:abs|pdf)/([\d.]+)', link)
            if match:
                arxiv_id = match.group(1)
    
    if arxiv_id:
        # 移除可能的版本号（如 2301.12345v1 -> 2301.12345）
        arxiv_id = arxiv_id.split('v')[0]
        return f"https://www.alphaxiv.org/abs/{arxiv_id}"
    
    return ""

class WeChatSender:
    """微信通知发送器"""
    
    def __init__(self, sender_type: str = "wecom", 
                 serverchan_key: str = None,
                 wecom_webhook: str = None):
        """
        初始化微信发送器
        
        Args:
            sender_type: 发送类型，"serverchan" 或 "wecom"
            serverchan_key: Server酱的SendKey
            wecom_webhook: 企业微信机器人Webhook URL
        """
        self.sender_type = sender_type
        self.serverchan_key = serverchan_key
        self.wecom_webhook = wecom_webhook
    
    def send_papers(self, papers: List[Dict], title: str = None) -> bool:
        """
        发送论文列表到微信
        
        Args:
            papers: 论文列表
            title: 消息标题
            
        Returns:
            是否发送成功
        """
        if not papers:
            logger.info("没有论文需要发送")
            return True
        
        if title is None:
            title = f"HPC论文推荐 - {datetime.now().strftime('%Y-%m-%d')}"
        
        try:
            if self.sender_type == "serverchan":
                return self._send_via_serverchan(papers, title)
            elif self.sender_type == "wecom":
                return self._send_via_wecom(papers, title)
            else:
                logger.error(f"不支持的微信发送类型: {self.sender_type}")
                return False
        except Exception as e:
            logger.error(f"发送微信消息时出错: {e}", exc_info=True)
            return False
    
    def _send_via_serverchan(self, papers: List[Dict], title: str) -> bool:
        """通过Server酱发送"""
        if not self.serverchan_key:
            logger.error("未配置ServerChan Key")
            return False
        
        # Server酱支持Markdown格式
        content = f"## {title}\n\n"
        content += f"今日推荐 **{len(papers)}** 篇HPC相关论文\n\n"
        content += "---\n\n"
        
        for i, paper in enumerate(papers, 1):
            score = paper.get('relevance_score', 0)
            content += f"### {i}. {paper['title']}\n\n"
            content += f"**作者:** {', '.join(paper['authors'][:3])}\n\n"
            content += f"**相关性:** {score:.2f}\n\n"
            content += f"**链接:** [{paper['link']}]({paper['link']})\n\n"
            alphaxiv_link = _get_alphaxiv_link_wechat(paper)
            if alphaxiv_link:
                # content += f"**AlphaXiv链接:** [{alphaxiv_link}]({alphaxiv_link})\n\n"
                #https://www.alphaxiv.org/abs/2512.10947 => https://www.alphaxiv.org/zh/overview/2512.10947
                zhalphaxiv_link = alphaxiv_link.replace("alphaxiv.org/abs", "alphaxiv.org/zh/overview")
                content += f"**AlphaXiv中文链接:** [{zhalphaxiv_link}]({zhalphaxiv_link})\n\n"
            content += f"**核心内容:** {paper.get('relevance_reason', 'N/A')}\n\n"
            # content += f"**摘要:** {paper['summary'][:500]}...\n\n"
            content += "---\n\n"
        
        url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
        data = {
            "title": title,
            "desp": content
        }
        
        response = requests.post(url, json=data, timeout=100)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 0:
            logger.info(f"成功通过ServerChan发送 {len(papers)} 篇论文")
            return True
        else:
            logger.error(f"ServerChan发送失败: {result}")
            return False
    
    def _send_via_wecom(self, papers: List[Dict], title: str) -> bool:
        """通过企业微信发送"""
        if not self.wecom_webhook:
            logger.error("未配置企业微信Webhook")
            return False
        
        # 企业微信支持Markdown格式
        content = f"## {title}\n\n"
        content += f"今日推荐 **{len(papers)}** 篇HPC相关论文\n\n"
        
        # 企业微信Markdown消息长度限制，只发送前5篇
        papers_to_send = papers[:5]
        
        for i, paper in enumerate(papers_to_send, 1):
            score = paper.get('relevance_score', 0)
            content += f"### {i}. {paper['title']}\n"
            content += f"**作者:** {', '.join(paper['authors'][:3])}\n"
            content += f"**相关性:** {score:.2f}\n"
            content += f"**链接:** {paper['link']}\n\n"
            alphaxiv_link = _get_alphaxiv_link_wechat(paper)
            if alphaxiv_link:
                # content += f"**AlphaXiv链接:** [{alphaxiv_link}]({alphaxiv_link})\n\n"
                #https://www.alphaxiv.org/abs/2512.10947 => https://www.alphaxiv.org/zh/overview/2512.10947
                zhalphaxiv_link = alphaxiv_link.replace("alphaxiv.org/abs", "alphaxiv.org/zh/overview")
                content += f"**AlphaXiv中文链接:** [{zhalphaxiv_link}]({zhalphaxiv_link})\n\n"
            content += f"**原因:** {paper.get('relevance_reason', 'N/A')}\n\n"
            # content += f"**摘要:** {paper['summary'][:500]}...\n\n"
            content += "---\n\n"
        
        if len(papers) > 5:
            content += f"\n> 还有 {len(papers) - 5} 篇论文，请查看完整邮件或日志\n"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        response = requests.post(self.wecom_webhook, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("errcode") == 0:
            logger.info(f"成功通过企业微信发送 {len(papers_to_send)} 篇论文")
            return True
        else:
            logger.error(f"企业微信发送失败: {result}")
            return False
