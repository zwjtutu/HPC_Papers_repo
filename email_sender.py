"""
邮件发送模块
"""
import os
import resend
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_alphaxiv_link(paper: Dict) -> str:
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


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, send_mode: str, smtp_server: str, smtp_port: int, 
                 sender_email: str, sender_password: str, receiver_email: str):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发送者邮箱
            sender_password: 发送者邮箱密码或应用专用密码
            receiver_email: 接收者邮箱
        """
        self.send_mode = send_mode
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email
    
    def send_papers(self, papers: List[Dict], subject: str = None) -> bool:
        """
        发送论文列表到邮箱
        
        Args:
            papers: 论文列表
            subject: 邮件主题
            
        Returns:
            是否发送成功
        """
        if not papers:
            logger.info("没有论文需要发送")
            return True
        
        if subject is None:
            subject = f"HPC论文推荐 - {datetime.now().strftime('%Y-%m-%d')}"
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = subject
            
            # 生成邮件内容
            html_content = self._generate_html_content(papers)
            text_content = self._generate_text_content(papers)
            
            # 添加文本和HTML版本
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # # 发送邮件
            if self.send_mode == "smtp":
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            else:
                resend.api_key = os.environ['RESEND_API_KEY']
                res = resend.Emails.send( self.mime_to_api_payload(msg) )

            logger.info(f"成功发送 {len(papers)} 篇论文到邮箱")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件时出错: {e}", exc_info=True)
            return False

    def mime_to_api_payload(self, msg: MIMEMultipart):
        """
        将 MIMEMultipart 对象转换为 Resend API 可用的 Payload 字典
        """
        payload = {
            "subject": msg.get("Subject", "No Subject"),
            # 注意：API通常要求 to 是列表或清洗过的字符串
            # 这里假设 msg['To'] 是标准的邮箱字符串
            "to": msg.get("To"), 
            "from": "onboarding@resend.dev", # 暂时写死或从 msg['From'] 提取并清洗
            "html": "",
            "text": ""
        }

        # 遍历 MIME 的各个部分
        # 如果 msg 本身不是 multipart (例如只是纯文本)，walk() 依然有效
        for part in msg.walk():
            # 跳过 multipart 容器本身，只看具体内容
            if part.get_content_maintype() == 'multipart':
                continue

            # 获取内容类型
            content_type = part.get_content_type()
            # 获取字符集，默认为 utf-8
            charset = part.get_content_charset() or 'utf-8'

            # 提取 payload 并解码
            try:
                content = part.get_payload(decode=True).decode(charset)
            except Exception:
                # 如果解码失败，跳过或记录错误
                continue

            if content_type == 'text/html':
                payload['html'] = content
            elif content_type == 'text/plain':
                payload['text'] = content

        # 如果只有 HTML 没有纯文本，通常 API 会自动处理，反之亦然
        # 但为了稳健，如果 html 为空但 text 有值，可以用 text 填充 html
        if not payload['html'] and payload['text']:
            payload['html'] = f"<pre>{payload['text']}</pre>"

        return payload

    def _format_reason(self, reason: str) -> str:
        """
        格式化原因文本，将PICO/T格式的各个部分换行显示
        
        Args:
            reason: 原始原因文本
            
        Returns:
            格式化后的原因文本
        """
        if not reason or reason == 'N/A':
            return reason
        
        # 使用正则表达式匹配P、I、C、O、T各部分
        # 匹配模式：P(Problem/Population): 或 P(Problem): 等格式，支持跨行内容
        patterns = [
            (r'P\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'P(Problem)'),
            (r'I\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'I(Intervention)'),
            (r'C\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'C(Comparison)'),
            (r'O\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'O(Outcome)'),
            (r'0\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'O(Outcome)'),  # 处理数字0的情况
            (r'T\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'T(Theory)'),
        ]
        
        # 按顺序提取各个部分
        parts = []
        text = reason
        last_pos = 0
        
        # 找到所有匹配项及其位置
        matches = []
        for pattern, label in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                matches.append((match.start(), match.end(), label, match.group(1).strip()))
        
        # 按位置排序
        matches.sort(key=lambda x: x[0])
        
        # 提取简要说明（在第一个PICO/T部分之前的内容）
        if matches:
            brief = text[:matches[0][0]].strip()
            if brief:
                parts.append(('简要说明', brief))
            
            # 添加各个PICO/T部分
            for start, end, label, content in matches:
                parts.append((label, content))
            
            # 提取最后一部分之后的内容（如果有）
            if matches:
                remaining = text[matches[-1][1]:].strip()
                if remaining:
                    parts.append(('补充说明', remaining))
        else:
            # 如果没有匹配到PICO/T格式，返回原始文本
            return reason
        
        # 格式化输出
        result = []
        for label, content in parts:
            if label == '简要说明' or label == '补充说明':
                result.append(content)
            else:
                result.append(f"{label}: {content}")
        
        return '\n'.join(result)
    
    def _format_reason_html(self, reason: str) -> str:
        """
        格式化原因文本为HTML格式，将PICO/T格式的各个部分换行显示
        
        Args:
            reason: 原始原因文本
            
        Returns:
            格式化后的HTML原因文本
        """
        if not reason or reason == 'N/A':
            return reason
        
        # 使用正则表达式匹配P、I、C、O、T各部分
        patterns = [
            (r'P\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'P(Problem)'),
            (r'I\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'I(Intervention)'),
            (r'C\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'C(Comparison)'),
            (r'O\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'O(Outcome)'),
            (r'0\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'O(Outcome)'),  # 处理数字0的情况
            (r'T\([^)]+\):\s*([^\n]+(?:\n(?![PICOT0]\([^)]+\):)[^\n]+)*)', 'T(Theory)'),
        ]
        
        # 按顺序提取各个部分
        parts = []
        text = reason
        last_pos = 0
        
        # 找到所有匹配项及其位置
        matches = []
        for pattern, label in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                matches.append((match.start(), match.end(), label, match.group(1).strip()))
        
        # 按位置排序
        matches.sort(key=lambda x: x[0])
        
        # 提取简要说明（在第一个PICO/T部分之前的内容）
        if matches:
            brief = text[:matches[0][0]].strip()
            if brief:
                parts.append(('简要说明', brief))
            
            # 添加各个PICO/T部分
            for start, end, label, content in matches:
                parts.append((label, content))
            
            # 提取最后一部分之后的内容（如果有）
            if matches:
                remaining = text[matches[-1][1]:].strip()
                if remaining:
                    parts.append(('补充说明', remaining))
        else:
            # 如果没有匹配到PICO/T格式，返回原始文本（转义HTML）
            return reason.replace('\n', '<br>').replace('<', '&lt;').replace('>', '&gt;')
        
        # 格式化输出为HTML
        result = []
        for label, content in parts:
            # 将换行符转换为HTML换行，并转义HTML特殊字符
            content_html = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            if label == '简要说明' or label == '补充说明':
                result.append(f'<div style="margin-bottom: 8px;">{content_html}</div>')
            else:
                result.append(f'<div style="margin-bottom: 8px;"><strong>{label}:</strong> {content_html}</div>')
        
        return ''.join(result)
    
    def _generate_text_content(self, papers: List[Dict]) -> str:
        """生成纯文本邮件内容"""
        content = f"今日HPC相关论文推荐 ({len(papers)} 篇)\n\n"
        content += "=" * 80 + "\n\n"
        
        for i, paper in enumerate(papers, 1):
            content += f"{i}. {paper['title']}\n"
            content += f"   作者: {', '.join(paper['authors'][:5])}\n"
            content += f"   发布日期: {paper['published']}\n"
            content += f"   相关性分数: {paper.get('relevance_score', 0):.2f}\n"
            # 格式化原因，按PICO/T格式换行显示
            formatted_reason = self._format_reason(paper.get('relevance_reason', 'N/A'))
            content += f"   核心内容:\n"
            # 为每行添加缩进
            for line in formatted_reason.split('\n'):
                content += f"      {line}\n"
            content += f"   arXiv链接: {paper['link']}\n"
            alphaxiv_link = _get_alphaxiv_link(paper)
            if alphaxiv_link:
                content += f"   AlphaXiv链接: {alphaxiv_link}\n"
                zhalphaxiv_link = alphaxiv_link.replace("alphaxiv.org/abs", "alphaxiv.org/zh/overview")
                content += f"   ZHAlphaXiv链接: {zhalphaxiv_link}\n"
            if paper.get('pdf_link'):
                content += f"   PDF: {paper['pdf_link']}\n"
            content += f"   摘要: {paper['summary'][:500]}...\n"
            content += "\n" + "-" * 80 + "\n\n"
        
        return content
    
    def _generate_html_content(self, papers: List[Dict]) -> str:
        """生成HTML邮件内容"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .paper {{ margin: 20px 0; padding: 15px; border-left: 4px solid #4CAF50; background-color: #f9f9f9; }}
                .title {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
                .meta {{ color: #666; font-size: 14px; margin: 5px 0; }}
                .summary {{ margin-top: 10px; color: #555; }}
                .link {{ color: #4CAF50; text-decoration: none; }}
                .score {{ display: inline-block; background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>HPC论文推荐</h1>
                <p>今日推荐 {len(papers)} 篇相关论文</p>
            </div>
        """
        
        for i, paper in enumerate(papers, 1):
            score = paper.get('relevance_score', 0)
            alphaxiv_link = _get_alphaxiv_link(paper)
            if alphaxiv_link:
                zhalphaxiv_link = alphaxiv_link.replace("alphaxiv.org/abs", "alphaxiv.org/zh/overview")
            pdf_link = paper.get('pdf_link', '')
            formatted_reason = self._format_reason_html(paper.get('relevance_reason', 'N/A'))
            
            html += f"""
            <div class="paper">
                <div class="title">
                    {i}. {paper['title']}
                    <span class="score">相关性: {score:.2f}</span>
                </div>
                <div class="meta">
                    <strong>作者:</strong> {', '.join(paper['authors'][:5])}
                    {('等' if len(paper['authors']) > 5 else '')}
                </div>
                <div class="meta">
                    <strong>发布日期:</strong> {paper['published']}
                </div>
                <div class="meta" style="margin-top: 10px;">
                    <strong>核心内容:</strong>
                    <div style="margin-top: 5px; padding-left: 10px; white-space: pre-wrap;">
                        {formatted_reason}
                    </div>
                </div>
                <div class="meta">
                    <a href="{paper['link']}" class="link">arXiv</a>
                    {f'<a href="{alphaxiv_link}" class="link" style="margin-left: 10px;">AlphaXiv</a>' if alphaxiv_link else ''}
                    {f'<a href="{zhalphaxiv_link}" class="link" style="margin-left: 10px;">ZHAlphaXiv</a>' if zhalphaxiv_link else ''}
                    {f'<a href="{pdf_link}" class="link" style="margin-left: 10px;">下载PDF</a>' if pdf_link else ''}
                </div>
                <div class="summary">
                    <strong>摘要:</strong> {paper['summary'][:300]}...
                </div>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
