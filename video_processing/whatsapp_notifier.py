"""
WhatsApp Notifier Module.

Sends notifications via OpenClaw WhatsApp integration.
"""

import logging
import subprocess
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    """
    Sends WhatsApp notifications using OpenClaw CLI.
    """

    def __init__(self, target_number: str, channel: str = "whatsapp"):
        """
        Initialize WhatsApp notifier.
        
        Args:
            target_number: WhatsApp number in E.164 format (e.g., +1234567890)
            channel: OpenClaw channel name (default: "whatsapp")
        """
        self.target_number = target_number
        self.channel = channel
        
        # Validate target number format
        if not target_number.startswith("+"):
            logger.warning(f"Target number should be in E.164 format (e.g., +1234567890): {target_number}")
        
        logger.info(f"WhatsApp notifier initialized for {target_number}")

    def send_message(self, message: str, media_path: Optional[str] = None) -> bool:
        """
        Send a WhatsApp message via OpenClaw.
        
        Args:
            message: Message text to send
            media_path: Optional path to media file (image/video/document)
        
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Build openclaw command - correct syntax: openclaw agent --to <number> --message <text> --deliver --channel <channel>
            cmd = [
                "openclaw",
                "agent",
                "--to", self.target_number,
                "--message", message,
                "--deliver",
                "--channel", self.channel,
            ]
            
            # Note: media attachments are not supported via openclaw agent CLI
            if media_path:
                logger.warning("Media attachments are not supported via openclaw agent CLI. Sending text only.")
            
            # Execute command
            logger.info(f"Sending WhatsApp message to {self.target_number}...")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                logger.info("✅ WhatsApp message sent successfully")
                logger.debug(f"Output: {result.stdout}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("WhatsApp message send timed out after 30 seconds")
            return False
        except FileNotFoundError:
            logger.error("OpenClaw CLI not found. Make sure it's installed and in PATH.")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
            return False

    def send_video_analysis_summary(
        self,
        video_name: str,
        trigger_count: int,
        ai_summary: Optional[str],
        analysis_duration: float,
    ) -> bool:
        """
        Send a formatted video analysis summary via WhatsApp.
        
        Args:
            video_name: Name of the analyzed video
            trigger_count: Number of trigger frames detected
            ai_summary: AI-generated summary (optional)
            analysis_duration: Time taken for analysis in seconds
        
        Returns:
            True if message sent successfully, False otherwise
        """
        # Format message
        message_parts = [
            "🎥 *Surveillance Video Analysis*",
            "",
            f"📹 Video: {video_name}",
            f"⚠️ Trigger Events: {trigger_count}",
            f"⏱️ Analysis Time: {analysis_duration:.1f}s",
        ]
        
        if ai_summary:
            message_parts.extend([
                "",
                "🤖 *AI Summary:*",
                ai_summary,
            ])
        else:
            message_parts.extend([
                "",
                "ℹ️ No AI summary available.",
            ])
        
        message = "\n".join(message_parts)
        
        return self.send_message(message)

    def send_trigger_alert(
        self,
        video_name: str,
        frame_count: int,
        unknown_faces: int,
    ) -> bool:
        """
        Send a quick trigger alert for unknown individuals detected.
        
        Args:
            video_name: Name of the video
            frame_count: Number of frames with triggers
            unknown_faces: Number of unknown faces detected
        
        Returns:
            True if message sent successfully, False otherwise
        """
        message = (
            f"🚨 *ALERT: Unknown Individual Detected*\n"
            f"\n"
            f"📹 Video: {video_name}\n"
            f"⚠️ Trigger Frames: {frame_count}\n"
            f"👤 Unknown Faces: {unknown_faces}\n"
            f"\n"
            f"Check the full analysis for details."
        )
        
        return self.send_message(message)
