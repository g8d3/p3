"""
Content Generator - Uses LLM to create engaging content from raw data
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from src.core.config import settings
from src.models.content import ContentTopic, ContentType

logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.temperature = settings.CONTENT_TEMPERATURE
        self.max_length = settings.MAX_CONTENT_LENGTH
    
    async def generate_content(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate engaging content from raw data
        Returns list of content items ready for posting
        """
        if not raw_data:
            logger.warning(f"No raw data provided for topic: {topic}")
            return []
        
        # Generate different types of content
        content_items = []
        
        # 1. Generate a summary article
        article = await self._generate_article(topic, raw_data)
        if article:
            content_items.append(article)
        
        # 2. Generate social media posts
        social_posts = await self._generate_social_posts(topic, raw_data)
        content_items.extend(social_posts)
        
        # 3. Generate a thread (for Twitter/X)
        thread = await self._generate_thread(topic, raw_data)
        if thread:
            content_items.append(thread)
        
        logger.info(f"Generated {len(content_items)} content items for {topic}")
        return content_items
    
    async def _generate_article(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a comprehensive article from raw data"""
        try:
            prompt = self._create_article_prompt(topic, raw_data)
            
            if self.openai_api_key:
                content = await self._call_openai(prompt)
            elif self.anthropic_api_key:
                content = await self._call_anthropic(prompt)
            else:
                logger.warning("No API keys configured, using fallback content generation")
                content = self._fallback_article_generation(topic, raw_data)
            
            if content:
                return {
                    "title": content.get("title", f"Latest {topic.value} Updates"),
                    "content_type": ContentType.ARTICLE,
                    "topic": topic,
                    "body": content.get("body", ""),
                    "summary": content.get("summary", ""),
                    "source_url": raw_data[0].get("link") if raw_data else None,
                    "source_name": raw_data[0].get("source") if raw_data else None,
                    "tags": self._extract_tags(topic, raw_data),
                }
        except Exception as e:
            logger.error(f"Error generating article: {str(e)}")
        
        return None
    
    async def _generate_social_posts(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate social media posts from raw data"""
        posts = []
        
        # Generate posts for different platforms
        platforms = ["twitter", "linkedin", "facebook"]
        
        for platform in platforms:
            try:
                prompt = self._create_social_post_prompt(topic, raw_data, platform)
                
                if self.openai_api_key:
                    content = await self._call_openai(prompt)
                elif self.anthropic_api_key:
                    content = await self._call_anthropic(prompt)
                else:
                    content = self._fallback_social_post_generation(topic, raw_data, platform)
                
                if content:
                    posts.append({
                        "title": content.get("title", f"{topic.value} update"),
                        "content_type": ContentType.SOCIAL_POST,
                        "topic": topic,
                        "body": content.get("body", ""),
                        "summary": content.get("summary", ""),
                        "source_url": raw_data[0].get("link") if raw_data else None,
                        "source_name": raw_data[0].get("source") if raw_data else None,
                        "tags": self._extract_tags(topic, raw_data),
                    })
            except Exception as e:
                logger.error(f"Error generating {platform} post: {str(e)}")
        
        return posts
    
    async def _generate_thread(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a Twitter/X thread from raw data"""
        try:
            prompt = self._create_thread_prompt(topic, raw_data)
            
            if self.openai_api_key:
                content = await self._call_openai(prompt)
            elif self.anthropic_api_key:
                content = await self._call_anthropic(prompt)
            else:
                content = self._fallback_thread_generation(topic, raw_data)
            
            if content:
                return {
                    "title": content.get("title", f"Thread: {topic.value}"),
                    "content_type": ContentType.THREAD,
                    "topic": topic,
                    "body": content.get("body", ""),
                    "summary": content.get("summary", ""),
                    "source_url": raw_data[0].get("link") if raw_data else None,
                    "source_name": raw_data[0].get("source") if raw_data else None,
                    "tags": self._extract_tags(topic, raw_data),
                }
        except Exception as e:
            logger.error(f"Error generating thread: {str(e)}")
        
        return None
    
    async def _call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI API to generate content"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_api_key)
            
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert content creator who creates engaging, informative, and shareable content about technology and AI."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return None
    
    async def _call_anthropic(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Anthropic API to generate content"""
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self.anthropic_api_key)
            
            response = await client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=self.temperature,
                system="You are an expert content creator who creates engaging, informative, and shareable content about technology and AI.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            # Try to parse as JSON, fallback to structured text
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "title": "Generated Content",
                    "body": content,
                    "summary": content[:200] + "..." if len(content) > 200 else content
                }
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            return None
    
    def _create_article_prompt(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> str:
        """Create prompt for article generation"""
        data_summary = "\n".join([
            f"- {item.get('title', '')}: {item.get('summary', '')[:200]}"
            for item in raw_data[:10]
        ])
        
        return f"""
Create an engaging article about {topic.value} based on the following recent developments:

{data_summary}

Requirements:
1. Write a compelling title (max 70 characters)
2. Create a comprehensive article (500-800 words)
3. Include a brief summary (max 150 characters)
4. Make it engaging and informative
5. Use a conversational but professional tone
6. Include relevant hashtags at the end

Return your response as JSON with these keys:
- title: string
- body: string (the full article)
- summary: string (brief summary for social sharing)
"""
    
    def _create_social_post_prompt(self, topic: ContentTopic, raw_data: List[Dict[str, Any]], platform: str) -> str:
        """Create prompt for social media post generation"""
        data_summary = "\n".join([
            f"- {item.get('title', '')}: {item.get('summary', '')[:150]}"
            for item in raw_data[:5]
        ])
        
        platform_limits = {
            "twitter": 280,
            "linkedin": 3000,
            "facebook": 63206,
        }
        
        char_limit = platform_limits.get(platform, 500)
        
        return f"""
Create an engaging {platform} post about {topic.value} based on these recent developments:

{data_summary}

Requirements:
1. Write a catchy title (max 50 characters)
2. Create a post optimized for {platform} (max {char_limit} characters)
3. Include a brief summary (max 100 characters)
4. Make it engaging and encourage interaction
5. Use appropriate hashtags for {platform}
6. Include a call-to-action

Return your response as JSON with these keys:
- title: string
- body: string (the full post)
- summary: string (brief summary)
"""
    
    def _create_thread_prompt(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> str:
        """Create prompt for Twitter/X thread generation"""
        data_summary = "\n".join([
            f"- {item.get('title', '')}: {item.get('summary', '')[:150]}"
            for item in raw_data[:8]
        ])
        
        return f"""
Create an engaging Twitter/X thread about {topic.value} based on these recent developments:

{data_summary}

Requirements:
1. Write a compelling thread title (max 60 characters)
2. Create a thread of 5-8 tweets, each under 280 characters
3. Number each tweet (1/7, 2/7, etc.)
4. Make it engaging and informative
5. Include relevant hashtags in the final tweet
6. End with a question or call-to-action

Return your response as JSON with these keys:
- title: string
- body: string (the full thread with numbered tweets separated by newlines)
- summary: string (brief summary of the thread)
"""
    
    def _extract_tags(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> str:
        """Extract relevant tags from the data"""
        base_tags = {
            ContentTopic.AI_NEWS: "AI,artificial intelligence,machine learning,tech news",
            ContentTopic.GITHUB_NEWS: "GitHub,open source,developer tools,programming",
            ContentTopic.TECH_TUTORIALS: "tutorial,programming,web development,coding",
            ContentTopic.AI_POLITICS: "AI policy,AI regulation,tech policy,government",
            ContentTopic.AI_BUSINESS: "AI business,enterprise AI,AI ROI,business technology",
            ContentTopic.REAL_VALUE_AI: "AI applications,AI use cases,practical AI,AI tools",
        }
        
        return base_tags.get(topic, "AI,technology")
    
    # Fallback methods when no API keys are configured
    def _fallback_article_generation(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate article without LLM (fallback)"""
        titles = [item.get("title", "") for item in raw_data[:3]]
        summaries = [item.get("summary", "") for item in raw_data[:5]]
        
        body = f"# Latest Updates in {topic.value}\n\n"
        body += f"Here are the most recent developments in {topic.value}:\n\n"
        
        for i, (title, summary) in enumerate(zip(titles, summaries), 1):
            body += f"## {i}. {title}\n\n"
            body += f"{summary}\n\n"
        
        body += f"\n*Stay tuned for more updates on {topic.value}!*\n\n"
        body += f"#{topic.value.replace(' ', '')} #AI #Technology"
        
        return {
            "title": f"Latest {topic.value} Updates - {datetime.now().strftime('%B %d, %Y')}",
            "body": body,
            "summary": f"Recent developments in {topic.value} including {titles[0] if titles else 'various updates'}"
        }
    
    def _fallback_social_post_generation(self, topic: ContentTopic, raw_data: List[Dict[str, Any]], platform: str) -> Dict[str, Any]:
        """Generate social post without LLM (fallback)"""
        title = raw_data[0].get("title", "") if raw_data else f"{topic.value} update"
        summary = raw_data[0].get("summary", "")[:150] if raw_data else ""
        
        body = f"🚀 {title}\n\n{summary}\n\n"
        body += f"Read more: {raw_data[0].get('link', '') if raw_data else ''}\n\n"
        body += f"#{topic.value.replace(' ', '')} #AI #Technology"
        
        return {
            "title": title,
            "body": body[:280] if platform == "twitter" else body,
            "summary": summary
        }
    
    def _fallback_thread_generation(self, topic: ContentTopic, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate thread without LLM (fallback)"""
        tweets = []
        for i, item in enumerate(raw_data[:5], 1):
            tweet = f"{i}/{min(5, len(raw_data[:5]))} {item.get('title', '')}\n\n"
            tweet += f"{item.get('summary', '')[:200]}"
            tweets.append(tweet)
        
        body = "\n\n---\n\n".join(tweets)
        
        return {
            "title": f"Thread: {topic.value} Updates",
            "body": body,
            "summary": f"A thread covering recent {topic.value} developments"
        }