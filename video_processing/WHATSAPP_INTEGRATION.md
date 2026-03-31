# WhatsApp Integration via OpenClaw

This document explains how to use the WhatsApp notification feature integrated with the video processing module.

## Overview

The video processing module can now automatically send AI-powered surveillance summaries to your WhatsApp via OpenClaw when unknown individuals are detected in surveillance footage.

## Prerequisites

1. **OpenClaw CLI** must be installed and configured on your system
   - Install from: https://docs.openclaw.ai/cli
   - Verify installation: `openclaw --version`

2. **WhatsApp Channel** must be connected to OpenClaw
   - Run: `openclaw channels login`
   - Follow the QR code authentication process

3. **OpenAI API Key** for AI-powered analysis
   - Set in `.env` file: `OPENAI_API_KEY=your-key-here`

## Configuration

### 1. Set Your WhatsApp Number

Add your WhatsApp number in E.164 format to `.env`:

```bash
# .env
WHATSAPP_TARGET_NUMBER=+919834570619  # Your number with country code
```

### 2. Enable WhatsApp Notifications

In `config.yaml`, enable the WhatsApp notification feature:

```yaml
video_processing:
  whatsapp_notification:
    enabled: true               # Enable WhatsApp notifications
    target_number: ""           # Leave empty to use WHATSAPP_TARGET_NUMBER from .env
    channel: "whatsapp"         # OpenClaw channel
    send_on_trigger: true       # Send notification when unknown individuals detected
```

## Usage

### Basic Usage

Simply run the video analyzer as usual. If triggers are detected, you'll automatically receive a WhatsApp notification:

```bash
python -m video_processing.run path/to/video.mp4
```

### Programmatic Usage

```python
from video_processing import VideoAnalyzer, load_config

# Load configuration (includes WhatsApp settings)
config = load_config()

# Initialize analyzer (WhatsApp notifier auto-initialized if enabled)
analyzer = VideoAnalyzer(config)

# Analyze video - WhatsApp notification sent automatically if triggers detected
result = analyzer.analyze_video("recordings/motion_2026-03-29_17-03-06.mp4")
```

### Manual Notification

You can also send custom WhatsApp notifications:

```python
from video_processing import WhatsAppNotifier

# Initialize notifier
notifier = WhatsAppNotifier(target_number="+919834570619")

# Send custom message
notifier.send_message("🚨 Security Alert: Motion detected!")

# Send video analysis summary
notifier.send_video_analysis_summary(
    video_name="motion_2026-03-29_17-03-06.mp4",
    trigger_count=5,
    ai_summary="Unknown individual detected entering premises at 17:03...",
    analysis_duration=12.5
)

# Send trigger alert
notifier.send_trigger_alert(
    video_name="motion_2026-03-29_17-03-06.mp4",
    frame_count=5,
    unknown_faces=2
)
```

## Notification Format

When triggers are detected, you'll receive a WhatsApp message like:

```
🎥 *Surveillance Video Analysis*

📹 Video: motion_2026-03-29_17-03-06.mp4
⚠️ Trigger Events: 5
⏱️ Analysis Time: 12.5s

🤖 *AI Summary:*
The footage shows an unknown individual entering the premises at approximately 17:03. 
The person appears to be wearing dark clothing and approaches the main entrance. 
They remain in view for approximately 30 seconds before moving out of frame.
```

## Configuration Options

### WhatsApp Notification Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `enabled` | Enable/disable WhatsApp notifications | `false` |
| `target_number` | WhatsApp number in E.164 format | `""` (uses env var) |
| `channel` | OpenClaw channel name | `"whatsapp"` |
| `send_on_trigger` | Auto-send when triggers detected | `true` |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `WHATSAPP_TARGET_NUMBER` | Your WhatsApp number (E.164 format) | Yes |
| `OPENAI_API_KEY` | OpenAI API key for AI summaries | Yes |

## Troubleshooting

### OpenClaw Not Found

```bash
# Check if OpenClaw is installed
which openclaw

# If not found, install it
# See: https://docs.openclaw.ai/cli
```

### WhatsApp Channel Not Connected

```bash
# Login to WhatsApp via OpenClaw
openclaw channels login

# Check channel status
openclaw status
```

### Notification Not Sent

Check the logs for error messages:

```bash
# Run with debug logging
python -m video_processing.run video.mp4 --debug
```

Common issues:
- WhatsApp number not in E.164 format (must start with `+` and country code)
- OpenClaw WhatsApp channel not authenticated
- Network connectivity issues

### Invalid Phone Number Format

Ensure your phone number is in E.164 format:
- ✅ Correct: `+919834570619` (India)
- ✅ Correct: `+15555550123` (USA)
- ❌ Wrong: `9834570619` (missing country code)
- ❌ Wrong: `+91 9834570619` (contains spaces)

## Advanced Usage

### Using Different Channels

OpenClaw supports multiple channels. To use Telegram instead of WhatsApp:

```yaml
whatsapp_notification:
  enabled: true
  target_number: "@your_telegram_username"
  channel: "telegram"
  send_on_trigger: true
```

### Conditional Notifications

Disable auto-notifications and send manually based on custom logic:

```python
from video_processing import VideoAnalyzer, WhatsAppNotifier, load_config

config = load_config()
# Disable auto-notifications
config.whatsapp_notification.send_on_trigger = False

analyzer = VideoAnalyzer(config)
result = analyzer.analyze_video("video.mp4")

# Send notification only if more than 3 triggers
if len(result.trigger_frames) > 3:
    notifier = WhatsAppNotifier("+919834570619")
    notifier.send_video_analysis_summary(
        video_name="video.mp4",
        trigger_count=len(result.trigger_frames),
        ai_summary=result.ai_summary,
        analysis_duration=result.analysis_duration
    )
```

### Sending Media

You can also send images or videos along with notifications:

```python
notifier = WhatsAppNotifier("+919834570619")

# Send message with image
notifier.send_message(
    message="🚨 Unknown person detected!",
    media_path="trigger_frame.jpg"
)
```

## Integration with Surveillance Pipeline

To automatically analyze recordings and send WhatsApp notifications:

```python
from video_pipeline import SurveillancePipeline
from video_processing import VideoAnalyzer, load_config
import time
from pathlib import Path

# Load config
config = load_config()

# Initialize video analyzer with WhatsApp enabled
analyzer = VideoAnalyzer(config)

# Monitor recordings directory
recordings_dir = Path("./recordings")

while True:
    # Get latest recording
    recordings = sorted(recordings_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    
    if recordings:
        latest = recordings[-1]
        
        # Analyze it
        result = analyzer.analyze_video(str(latest))
        
        # WhatsApp notification sent automatically if triggers detected
        
    time.sleep(60)  # Check every minute
```

## Security Considerations

1. **Protect Your .env File**: Never commit `.env` to version control
2. **Phone Number Privacy**: Keep your WhatsApp number confidential
3. **API Keys**: Secure your OpenAI API key
4. **OpenClaw Authentication**: Keep your OpenClaw session secure

## Support

For issues related to:
- **Video Processing**: Check `video_processing/README.md`
- **OpenClaw**: Visit https://docs.openclaw.ai
- **WhatsApp Integration**: Check OpenClaw channel documentation

## Example: Complete Workflow

```bash
# 1. Ensure OpenClaw is running and authenticated
openclaw status

# 2. Configure your WhatsApp number in .env
echo "WHATSAPP_TARGET_NUMBER=+919834570619" >> .env

# 3. Enable notifications in config.yaml
# (Set whatsapp_notification.enabled: true)

# 4. Run video analysis
python -m video_processing.run recordings/motion_2026-03-29_17-03-06.mp4

# 5. Check your WhatsApp for the notification!
```

## License

MIT License - See main project LICENSE file
