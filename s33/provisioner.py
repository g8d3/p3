"""
AutoContent - Auto Provisioner
Automatically provisions required accounts and services
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional
from logger import logger
from error_handler import self_healer, ErrorContext


@dataclass
class ServiceAccount:
    """Service account details"""
    service: str
    email: str
    account_id: str
    api_key: Optional[str] = None
    status: str = "pending"


class Provisioner:
    """Auto-provisioning of accounts and services"""
    
    def __init__(self, wallet_config: dict = None):
        self.wallet_config = wallet_config or {}
        self.accounts: list[ServiceAccount] = []
        self.provisioned = False
    
    def provision_all(self, required_services: list[str]) -> bool:
        """Provision all required services"""
        logger.info(f"Provisioning services: {required_services}")
        
        success = True
        
        for service in required_services:
            if service == "github":
                success = self._provision_github() and success
            elif service == "x":
                success = self._provision_x() and success
            elif service == "llm":
                success = self._provision_llm() and success
            elif service == "video":
                success = self._provision_video_tools() and success
            elif service == "hosting":
                success = self._provision_hosting() and success
        
        self.provisioned = success
        return success
    
    def _provision_github(self) -> bool:
        """Provision GitHub account"""
        logger.info("Checking GitHub account")
        
        token = os.getenv("GITHUB_TOKEN")
        if token:
            account = ServiceAccount(
                service="github",
                email="configured@via.token",
                account_id="token",
                api_key=token,
                status="ready"
            )
            self.accounts.append(account)
            logger.info("GitHub account ready")
            return True
        
        logger.warning("GITHUB_TOKEN not set")
        return False
    
    def _provision_x(self) -> bool:
        """Provision X.com account"""
        logger.info("Checking X.com account")
        
        username = os.getenv("X_USERNAME")
        password = os.getenv("X_PASSWORD")
        
        if username and password:
            account = ServiceAccount(
                service="x",
                email=f"{username}@x.com",
                account_id=username,
                status="ready"
            )
            self.accounts.append(account)
            logger.info("X.com account ready")
            return True
        
        logger.warning("X credentials not configured")
        return False
    
    def _provision_llm(self) -> bool:
        """Provision LLM API access"""
        logger.info("Checking LLM API")
        
        api_keys = [
            os.getenv("OPENAI_API_KEY"),
            os.getenv("ANTHROPIC_API_KEY"),
            os.getenv("OLLAMA_API_KEY")
        ]
        
        for key in api_keys:
            if key:
                account = ServiceAccount(
                    service="llm",
                    email="api@provider.com",
                    account_id="api",
                    api_key=key,
                    status="ready"
                )
                self.accounts.append(account)
                logger.info("LLM API ready")
                return True
        
        logger.warning("No LLM API key configured")
        return False
    
    def _provision_video_tools(self) -> bool:
        """Provision video generation tools"""
        logger.info("Checking video tools")
        
        # Check ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True)
            logger.info("ffmpeg available")
        except FileNotFoundError:
            logger.warning("ffmpeg not installed")
        
        # Check TTS tools
        try:
            subprocess.run(["espeak", "--version"], capture_output=True)
            logger.info("espeak available")
        except FileNotFoundError:
            pass
        
        return True
    
    def _provision_hosting(self) -> bool:
        """Provision hosting for videos/code"""
        logger.info("Checking hosting options")
        
        # Could integrate with:
        # - Vercel (for hosting)
        # - Netlify
        # - AWS S3
        # - Cloudflare R2
        
        hosting_configured = bool(
            os.getenv("VERCEL_TOKEN") or
            os.getenv("NETLIFY_TOKEN") or
            os.getenv("AWS_ACCESS_KEY_ID")
        )
        
        if hosting_configured:
            account = ServiceAccount(
                service="hosting",
                email="configured@via.env",
                account_id="env",
                status="ready"
            )
            self.accounts.append(account)
            logger.info("Hosting ready")
            return True
        
        logger.warning("No hosting configured")
        return True  # Not critical
    
    def verify_provisioning(self) -> bool:
        """Verify all services are provisioned"""
        logger.info("Verifying provisioning")
        
        for account in self.accounts:
            if account.status != "ready":
                logger.warning(f"Account {account.service} not ready")
                return False
        
        logger.info("All services provisioned")
        return True
    
    def get_status(self) -> dict:
        """Get provisioning status"""
        return {
            "provisioned": self.provisioned,
            "accounts": [
                {
                    "service": a.service,
                    "status": a.status,
                    "email": a.email
                }
                for a in self.accounts
            ]
        }


def create_provisioner(wallet_config: dict = None) -> Provisioner:
    """Factory function"""
    return Provisioner(wallet_config)
