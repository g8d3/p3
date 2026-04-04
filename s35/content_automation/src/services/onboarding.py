"""
Onboarding module - Guides new users through initial setup
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.config import settings
from src.models.content import ContentTopic

logger = logging.getLogger(__name__)

class OnboardingManager:
    """Manages user onboarding and initial configuration"""
    
    def __init__(self):
        self.config_file = "data/onboarding.json"
        self.is_configured = self._check_configuration()
    
    def _check_configuration(self) -> bool:
        """Check if user has completed onboarding"""
        if not os.path.exists(self.config_file):
            return False
        
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
            return config.get("completed", False)
        except Exception:
            return False
    
    def complete_onboarding(self, preferences: Dict[str, Any]) -> bool:
        """Complete onboarding with user preferences"""
        try:
            os.makedirs("data", exist_ok=True)
            
            config = {
                "completed": True,
                "completed_at": datetime.utcnow().isoformat(),
                "preferences": preferences,
                "topics_enabled": preferences.get("topics", [topic.value for topic in ContentTopic]),
                "posting_frequency": preferences.get("posting_frequency", "moderate"),
                "platforms_enabled": preferences.get("platforms", []),
            }
            
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            
            self.is_configured = True
            logger.info(f"Onboarding completed with preferences: {preferences}")
            return True
        except Exception as e:
            logger.error(f"Error completing onboarding: {str(e)}")
            return False
    
    def get_preferences(self) -> Optional[Dict[str, Any]]:
        """Get user preferences"""
        if not self.is_configured:
            return None
        
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
            return config.get("preferences", {})
        except Exception:
            return None
    
    def update_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            current = self.get_preferences() or {}
            current.update(preferences)
            
            return self.complete_onboarding(current)
        except Exception as e:
            logger.error(f"Error updating preferences: {str(e)}")
            return False
    
    def get_onboarding_status(self) -> Dict[str, Any]:
        """Get onboarding status"""
        return {
            "completed": self.is_configured,
            "preferences": self.get_preferences(),
        }