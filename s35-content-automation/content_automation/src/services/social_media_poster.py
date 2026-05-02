"""
Social Media Poster - Post content to various social media platforms
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.config import settings
from src.models.content import Content

logger = logging.getLogger(__name__)

class SocialMediaPoster:
    def __init__(self):
        self.twitter_api_key = settings.TWITTER_API_KEY
        self.twitter_api_secret = settings.TWITTER_API_SECRET
        self.twitter_access_token = settings.TWITTER_ACCESS_TOKEN
        self.twitter_access_token_secret = settings.TWITTER_ACCESS_TOKEN_SECRET
        
        self.facebook_access_token = settings.FACEBOOK_ACCESS_TOKEN
        self.linkedin_access_token = settings.LINKEDIN_ACCESS_TOKEN
        self.instagram_access_token = settings.INSTAGRAM_ACCESS_TOKEN
    
    async def post_to_platform(self, platform: str, content: Content) -> bool:
        """Post content to a specific social media platform"""
        platform_posters = {
            "twitter": self._post_to_twitter,
            "facebook": self._post_to_facebook,
            "linkedin": self._post_to_linkedin,
            "instagram": self._post_to_instagram,
        }
        
        poster = platform_posters.get(platform)
        if not poster:
            logger.warning(f"Unsupported platform: {platform}")
            return False
        
        try:
            return await poster(content)
        except Exception as e:
            logger.error(f"Error posting to {platform}: {str(e)}")
            return False
    
    async def _post_to_twitter(self, content: Content) -> bool:
        """Post content to Twitter/X"""
        if not all([self.twitter_api_key, self.twitter_api_secret, 
                   self.twitter_access_token, self.twitter_access_token_secret]):
            logger.warning("Twitter credentials not configured")
            return False
        
        try:
            import tweepy
            
            # Authenticate
            auth = tweepy.OAuth1UserHandler(
                self.twitter_api_key,
                self.twitter_api_secret,
                self.twitter_access_token,
                self.twitter_access_token_secret
            )
            api = tweepy.API(auth)
            
            # Post content
            if content.content_type.value == "thread":
                # Handle thread posting
                tweets = content.body.split("\n\n---\n\n")
                thread = []
                for tweet in tweets:
                    response = api.update_status(tweet)
                    thread.append(response)
                logger.info(f"Posted thread to Twitter: {content.title}")
            else:
                # Single post
                api.update_status(content.body[:280])  # Twitter character limit
                logger.info(f"Posted to Twitter: {content.title}")
            
            return True
        except Exception as e:
            logger.error(f"Twitter posting error: {str(e)}")
            return False
    
    async def _post_to_facebook(self, content: Content) -> bool:
        """Post content to Facebook"""
        if not self.facebook_access_token:
            logger.warning("Facebook access token not configured")
            return False
        
        try:
            import facebook
            
            graph = facebook.GraphAPI(access_token=self.facebook_access_token, version="18.0")
            
            # Post to page
            graph.put_object(
                parent_object="me",
                connection_name="feed",
                message=content.body,
                link=content.source_url
            )
            
            logger.info(f"Posted to Facebook: {content.title}")
            return True
        except Exception as e:
            logger.error(f"Facebook posting error: {str(e)}")
            return False
    
    async def _post_to_linkedin(self, content: Content) -> bool:
        """Post content to LinkedIn"""
        if not self.linkedin_access_token:
            logger.warning("LinkedIn access token not configured")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.linkedin_access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Get user profile ID
            import requests
            profile_response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers=headers
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            author_id = f"urn:li:person:{profile_data['id']}"
            
            # Create post
            post_data = {
                "author": author_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content.body
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=post_data
            )
            response.raise_for_status()
            
            logger.info(f"Posted to LinkedIn: {content.title}")
            return True
        except Exception as e:
            logger.error(f"LinkedIn posting error: {str(e)}")
            return False
    
    async def _post_to_instagram(self, content: Content) -> bool:
        """Post content to Instagram"""
        if not self.instagram_access_token:
            logger.warning("Instagram access token not configured")
            return False
        
        try:
            # Instagram Business API requires media creation first
            import requests
            
            # Create media container
            media_data = {
                "image_url": "https://example.com/default-image.jpg",  # Would need actual image
                "caption": content.body[:2200]  # Instagram caption limit
            }
            
            response = requests.post(
                f"https://graph.facebook.com/v18.0/me/media",
                params={"access_token": self.instagram_access_token},
                json=media_data
            )
            response.raise_for_status()
            
            container_id = response.json().get("id")
            
            # Publish the media
            publish_response = requests.post(
                f"https://graph.facebook.com/v18.0/me/media_publish",
                params={
                    "access_token": self.instagram_access_token,
                    "creation_id": container_id
                }
            )
            publish_response.raise_for_status()
            
            logger.info(f"Posted to Instagram: {content.title}")
            return True
        except Exception as e:
            logger.error(f"Instagram posting error: {str(e)}")
            return False