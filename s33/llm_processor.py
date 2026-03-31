"""
AutoContent - LLM Content Processor
Generates content from scraped x.com posts using LLM
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional
from logger import logger
from error_handler import self_healer, ErrorContext


@dataclass
class GeneratedContent:
    """Generated content from LLM"""
    title: str
    body: str
    summary: str
    tags: list[str] = field(default_factory=list)
    code_snippets: list[str] = field(default_factory=list)
    video_script: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class VideoScript:
    """Video script for content"""
    hook: str
    intro: str
    main_points: list[str]
    conclusion: str
    call_to_action: str
    duration_seconds: int = 180


class LLMProcessor:
    """LLM-based content generation"""
    
    def __init__(self, api_key: str, provider: str = "openai", 
                 model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize LLM client"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("OpenAI not installed, using fallback")
                self.client = None
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("Anthropic not installed, using fallback")
                self.client = None
        elif self.provider == "ollama":
            self.base_url = self.base_url or "http://localhost:11434"
            self.client = "ollama"  # Placeholder
    
    def generate_content(self, posts: list, system_prompt: str = "") -> GeneratedContent:
        """Generate content from posts"""
        logger.info(f"Generating content from {len(posts)} posts")
        
        # Prepare posts data
        posts_summary = self._prepare_posts_summary(posts)
        
        # Build prompt
        prompt = self._build_content_prompt(posts_summary)
        
        # Call LLM
        response = self._call_llm(prompt, system_prompt)
        
        if response:
            return self._parse_content_response(response)
        
        return self._fallback_content(posts)
    
    def _prepare_posts_summary(self, posts: list) -> str:
        """Prepare posts for LLM context"""
        summaries = []
        for i, post in enumerate(posts[:20]):  # Limit to 20 posts
            summaries.append(f"""
Post {i+1}:
- Author: {post.get('author', 'Unknown')}
- Handle: {post.get('author_handle', '')}
- Content: {post.get('content', '')[:500]}
- Likes: {post.get('likes', 0)}
- Retweets: {post.get('retweets', 0)}
""")
        return "\n".join(summaries)
    
    def _build_content_prompt(self, posts_summary: str) -> str:
        """Build content generation prompt"""
        return f"""Based on the following X.com posts (likes and bookmarks), generate:

1. A compelling title for a content piece
2. A summary of the trending topics/ideas
3. Key insights (3-5 bullet points)
4. Code snippets if any technical content is found
5. Tags for categorization

Posts:
{posts_summary}

Respond in JSON format:
{{
  "title": "...",
  "summary": "...",
  "insights": ["...", "..."],
  "code_snippets": ["..."],
  "tags": ["...", "..."]
}}
"""
    
    def _call_llm(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Call LLM API"""
        if not self.client:
            return None
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt or "You are a content generator."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )
                return response.choices[0].message.content
            
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return None
    
    def _parse_content_response(self, response: str) -> GeneratedContent:
        """Parse LLM response"""
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                return GeneratedContent(
                    title=data.get("title", "Generated Content"),
                    body=data.get("summary", ""),
                    summary=data.get("summary", ""),
                    tags=data.get("tags", []),
                    code_snippets=data.get("code_snippets", []),
                    metadata=data
                )
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
        
        return GeneratedContent(
            title="Generated Content",
            body=response[:1000],
            summary=response[:500]
        )
    
    def _fallback_content(self, posts: list) -> GeneratedContent:
        """Fallback content generation"""
        logger.warning("Using fallback content generation")
        
        return GeneratedContent(
            title="Content from X.com",
            body=f"Generated from {len(posts)} posts",
            summary="Summary placeholder",
            tags=["automated", "x.com"]
        )
    
    def generate_video_script(self, content: GeneratedContent) -> VideoScript:
        """Generate video script from content"""
        logger.info("Generating video script")
        
        prompt = f"""Create a video script for a YouTube/shorts video based on:

Title: {content.title}
Summary: {content.summary}
Key Points: {content.body}

Create a script with:
- Hook (attention-grabbing opening)
- Intro (brief introduction)
- Main Points (3-5 key points to cover)
- Conclusion (summary)
- Call to Action

Respond in JSON format:
{{
  "hook": "...",
  "intro": "...",
  "main_points": ["...", "..."],
  "conclusion": "...",
  "call_to_action": "...",
  "duration_seconds": 180
}}
"""
        
        response = self._call_llm(prompt)
        
        if response:
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(response[json_start:json_end])
                    return VideoScript(
                        hook=data.get("hook", ""),
                        intro=data.get("intro", ""),
                        main_points=data.get("main_points", []),
                        conclusion=data.get("conclusion", ""),
                        call_to_action=data.get("call_to_action", ""),
                        duration_seconds=data.get("duration_seconds", 180)
                    )
            except Exception as e:
                logger.error(f"Failed to parse video script: {e}")
        
        return VideoScript(
            hook="Welcome to today's content!",
            intro="Let's explore this topic",
            main_points=["Point 1", "Point 2", "Point 3"],
            conclusion="Thanks for watching",
            call_to_action="Like and subscribe!"
        )
    
    def generate_code(self, content: GeneratedContent) -> str:
        """Generate code based on content"""
        logger.info("Generating code from content")
        
        if not content.code_snippets:
            return ""
        
        prompt = f"""Based on these code snippets and context:
{chr(10).join(content.code_snippets)}

Create a complete, working code example. Include:
- Proper imports
- Main functionality
- Comments explaining the code

Return only the code, no explanation.
"""
        
        return self._call_llm(prompt) or ""


def create_processor(api_key: str, **kwargs) -> LLMProcessor:
    """Factory function"""
    return LLMProcessor(api_key, **kwargs)
