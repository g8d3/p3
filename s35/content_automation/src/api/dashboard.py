"""
Web Dashboard - Simple frontend for the Content Automation System
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.models.content import Content, ContentTopic, ContentStatus, SocialPost

dashboard_router = APIRouter()

# Simple HTML dashboard template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Automation Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: #1a1a2e; color: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; }
        header h1 { font-size: 24px; margin-bottom: 5px; }
        header p { opacity: 0.8; font-size: 14px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { font-size: 14px; color: #666; margin-bottom: 10px; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #1a1a2e; }
        .stat-card.draft .value { color: #f59e0b; }
        .stat-card.scheduled .value { color: #3b82f6; }
        .stat-card.posted .value { color: #10b981; }
        .stat-card.failed .value { color: #ef4444; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .section h2 { font-size: 18px; margin-bottom: 15px; color: #1a1a2e; }
        .content-list { list-style: none; }
        .content-item { padding: 15px; border-bottom: 1px solid #eee; }
        .content-item:last-child { border-bottom: none; }
        .content-item h4 { font-size: 16px; margin-bottom: 5px; }
        .content-item .meta { font-size: 12px; color: #666; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge-draft { background: #fef3c7; color: #92400e; }
        .badge-scheduled { background: #dbeafe; color: #1e40af; }
        .badge-posted { background: #d1fae5; color: #065f46; }
        .badge-failed { background: #fee2e2; color: #991b1b; }
        .actions { margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-success { background: #10b981; color: white; }
        .btn-success:hover { background: #059669; }
        .btn-warning { background: #f59e0b; color: white; }
        .btn-warning:hover { background: #d97706; }
        .empty-state { text-align: center; padding: 40px; color: #666; }
        .refresh-info { font-size: 12px; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Content Automation Dashboard</h1>
            <p>Automated content creation and posting across social media platforms</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Content</h3>
                <div class="value">{total_content}</div>
            </div>
            <div class="stat-card draft">
                <h3>Draft</h3>
                <div class="value">{draft_content}</div>
            </div>
            <div class="stat-card scheduled">
                <h3>Scheduled</h3>
                <div class="value">{scheduled_content}</div>
            </div>
            <div class="stat-card posted">
                <h3>Posted</h3>
                <div class="value">{posted_content}</div>
            </div>
            <div class="stat-card failed">
                <h3>Failed Posts</h3>
                <div class="value">{failed_posts}</div>
            </div>
        </div>

        <div class="section">
            <h2>Quick Actions</h2>
            <div class="actions">
                <button class="btn btn-primary" onclick="generateContent()">Generate New Content</button>
                <button class="btn btn-success" onclick="postNow()">Post Scheduled Content Now</button>
                <button class="btn btn-warning" onclick="refreshDashboard()">Refresh Dashboard</button>
            </div>
            <p class="refresh-info">Auto-refreshes every 60 seconds</p>
        </div>

        <div class="section">
            <h2>Recent Content</h2>
            {content_list}
        </div>

        <div class="section">
            <h2>Recent Posts</h2>
            {posts_list}
        </div>
    </div>

    <script>
        async function generateContent() {{
            const topic = prompt('Enter topic (ai_news, github_news, tech_tutorials, ai_politics, ai_business, real_value_ai):', 'ai_news');
            if (!topic) return;
            
            try {{
                const response = await fetch('/api/v1/content/generate?topic=' + topic, {{
                    method: 'POST'
                }});
                const data = await response.json();
                alert(data.message);
                refreshDashboard();
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}

        async function postNow() {{
            if (!confirm('Post all scheduled content now?')) return;
            
            try {{
                const response = await fetch('/api/v1/content/post-now', {{
                    method: 'POST'
                }});
                const data = await response.json();
                alert('Posted: ' + data.successful + ', Failed: ' + data.failed);
                refreshDashboard();
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}

        function refreshDashboard() {{
            location.reload();
        }}

        // Auto-refresh every 60 seconds
        setTimeout(refreshDashboard, 60000);
    </script>
</body>
</html>
"""

@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page"""
    # Get statistics
    total_content = db.query(Content).count()
    draft_content = db.query(Content).filter(Content.status == ContentStatus.DRAFT).count()
    scheduled_content = db.query(Content).filter(Content.status == ContentStatus.SCHEDULED).count()
    posted_content = db.query(Content).filter(Content.status == ContentStatus.POSTED).count()
    failed_posts = db.query(SocialPost).filter(SocialPost.status == "failed").count()
    
    # Get recent content
    recent_content = db.query(Content).order_by(Content.created_at.desc()).limit(10).all()
    content_html = ""
    if recent_content:
        content_items = []
        for c in recent_content:
            badge_class = f"badge-{c.status.value}"
            content_items.append(f"""
                <li class="content-item">
                    <h4>{c.title}</h4>
                    <div class="meta">
                        <span class="badge {badge_class}">{c.status.value}</span>
                        <span>Topic: {c.topic.value}</span>
                        <span>Type: {c.content_type.value}</span>
                        <span>Created: {c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else 'N/A'}</span>
                    </div>
                </li>
            """)
        content_html = f"<ul class='content-list'>{''.join(content_items)}</ul>"
    else:
        content_html = "<div class='empty-state'>No content yet. Click 'Generate New Content' to get started!</div>"
    
    # Get recent posts
    recent_posts = db.query(SocialPost).order_by(SocialPost.created_at.desc()).limit(10).all()
    posts_html = ""
    if recent_posts:
        post_items = []
        for p in recent_posts:
            badge_class = f"badge-{p.status}"
            post_items.append(f"""
                <li class="content-item">
                    <h4>{p.platform.capitalize()} - Content #{p.content_id}</h4>
                    <div class="meta">
                        <span class="badge {badge_class}">{p.status}</span>
                        <span>Created: {p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else 'N/A'}</span>
                        {f'<span>Error: {p.error_message}</span>' if p.error_message else ''}
                    </div>
                </li>
            """)
        posts_html = f"<ul class='content-list'>{''.join(post_items)}</ul>"
    else:
        posts_html = "<div class='empty-state'>No posts yet. Content will be posted automatically when scheduled.</div>"
    
    # Render template
    html = DASHBOARD_TEMPLATE.format(
        total_content=total_content,
        draft_content=draft_content,
        scheduled_content=scheduled_content,
        posted_content=posted_content,
        failed_posts=failed_posts,
        content_list=content_html,
        posts_list=posts_html
    )
    
    return HTMLResponse(content=html)