#!/usr/bin/env python3
"""
CLI tool for managing the Content Automation System
"""
import asyncio
import click
from datetime import datetime
from typing import Optional

@click.group()
def cli():
    """Content Automation System CLI"""
    pass

@cli.command()
def setup():
    """Run the setup wizard"""
    click.echo("Running setup wizard...")
    from setup import main
    main()

@cli.command()
@click.option("--topic", type=click.Choice([
    "ai news", "github news", "tech tutorials", 
    "ai applied to politics", "ai applied to business", "real value ai"
]), help="Content topic to generate")
@click.option("--count", default=1, help="Number of content pieces to generate")
def generate(topic: Optional[str], count: int):
    """Manually generate content"""
    from src.core.config import settings
    from src.services.content_engine import ContentEngine
    from src.models.content import ContentTopic
    
    async def _generate():
        engine = ContentEngine()
        await engine.start()
        
        if topic:
            topic_enum = ContentTopic(topic)
            click.echo(f"Generating {count} content piece(s) for: {topic}")
            content_items = await engine.gather_and_create_content(topic_enum)
            click.echo(f"✅ Generated {len(content_items)} content piece(s)")
            for item in content_items:
                click.echo(f"   - {item.title}")
        else:
            # Generate for all topics
            for topic_enum in ContentTopic:
                click.echo(f"Generating content for: {topic_enum.value}")
                content_items = await engine.gather_and_create_content(topic_enum)
                click.echo(f"✅ Generated {len(content_items)} content piece(s)")
        
        await engine.stop()
    
    asyncio.run(_generate())

@cli.command()
@click.option("--platforms", default="twitter,linkedin,facebook", help="Comma-separated list of platforms")
@click.option("--schedule-time", type=click.DateTime(), help="Schedule time (ISO format)")
def post(platforms: str, schedule_time: Optional[datetime]):
    """Post scheduled content"""
    from src.services.content_engine import ContentEngine
    
    async def _post():
        engine = ContentEngine()
        await engine.start()
        
        platform_list = [p.strip() for p in platforms.split(",")]
        click.echo(f"Posting to: {', '.join(platform_list)}")
        
        results = await engine.post_scheduled_content()
        click.echo(f"✅ Posted: {results.get('successful', 0)}")
        click.echo(f"❌ Failed: {results.get('failed', 0)}")
        
        if results.get('errors'):
            click.echo("Errors:")
            for error in results['errors']:
                click.echo(f"   - {error}")
        
        await engine.stop()
    
    asyncio.run(_post())

@cli.command()
def status():
    """Show system status"""
    from src.core.database import get_db
    from src.models.content import Content, ContentStatus, SocialPost
    
    db = next(get_db())
    
    total_content = db.query(Content).count()
    draft_content = db.query(Content).filter(Content.status == ContentStatus.DRAFT).count()
    scheduled_content = db.query(Content).filter(Content.status == ContentStatus.SCHEDULED).count()
    posted_content = db.query(Content).filter(Content.status == ContentStatus.POSTED).count()
    
    total_posts = db.query(SocialPost).count()
    posted_posts = db.query(SocialPost).filter(SocialPost.status == "posted").count()
    failed_posts = db.query(SocialPost).filter(SocialPost.status == "failed").count()
    
    click.echo("\n📊 Content Automation System Status\n")
    click.echo(f"Total Content:     {total_content}")
    click.echo(f"  Draft:           {draft_content}")
    click.echo(f"  Scheduled:       {scheduled_content}")
    click.echo(f"  Posted:          {posted_content}")
    click.echo(f"\nTotal Posts:       {total_posts}")
    click.echo(f"  Posted:          {posted_posts}")
    click.echo(f"  Failed:          {failed_posts}")
    click.echo()
    
    db.close()

@cli.command()
def topics():
    """List supported content topics"""
    from src.models.content import ContentTopic
    
    click.echo("\n📝 Supported Content Topics:\n")
    for topic in ContentTopic:
        click.echo(f"  • {topic.value}")
    click.echo()

@cli.command()
@click.option("--limit", default=10, help="Number of recent items to show")
def recent(limit: int):
    """Show recent content"""
    from src.core.database import get_db
    from src.models.content import Content
    
    db = next(get_db())
    content_list = db.query(Content).order_by(Content.created_at.desc()).limit(limit).all()
    
    click.echo(f"\n📄 Recent Content (last {limit}):\n")
    for content in content_list:
        status_emoji = {
            "draft": "📝",
            "scheduled": "⏰",
            "posted": "✅",
            "failed": "❌"
        }.get(content.status.value, "❓")
        
        click.echo(f"{status_emoji} {content.title}")
        click.echo(f"   Topic: {content.topic.value} | Type: {content.content_type.value}")
        click.echo(f"   Status: {content.status.value} | Created: {content.created_at.strftime('%Y-%m-%d %H:%M') if content.created_at else 'N/A'}")
        click.echo()
    
    db.close()

if __name__ == "__main__":
    cli()