# Video Processing Module

AI-powered video analysis module for the surveillance agent. Provides face detection, recognition, and intelligent activity analysis using OpenCV and OpenAI GPT-4.

## Features

- **Face Detection**: Fast and accurate face detection using OpenCV's YuNet model
- **Face Recognition**: Identify known individuals using SFace embeddings and cosine similarity
- **AI-Powered Analysis**: Generate intelligent summaries of surveillance footage using GPT-4
- **Trigger Detection**: Automatically identify frames with unknown/unauthorized individuals
- **WhatsApp Notifications**: Send AI summaries via WhatsApp using OpenClaw integration
- **Configurable**: Fully configurable via YAML config file

## Architecture

The module follows a clean, modular architecture similar to `video_pipeline`:

```
video_processing/
├── __init__.py           # Module exports
├── config.py             # Configuration management
├── face_detector.py      # Face detection using YuNet
├── face_recognizer.py    # Face recognition using SFace
├── video_analyzer.py     # Main orchestrator
├── run.py                # CLI runner
├── known_faces/          # Directory for known face images
└── *.onnx                # Pre-trained models
```

## Setup

### 1. Install Dependencies

The required dependencies are already included in the main `pyproject.toml`:

```bash
cd /Users/hiteshmusale/work/Projects/personal/surveillance_agent
uv sync
```

### 2. Configure Environment Variables

Add your OpenAI API key to `.env`:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Add Known Faces (Optional)

Place images of known individuals in `video_processing/known_faces/`:

```
video_processing/known_faces/
├── john_doe.jpg
├── jane_smith.png
└── owner.jpg
```

The filename (without extension) becomes the person's identifier.

## Usage

### Command Line

Analyze a video file:

```bash
python -m video_processing.run path/to/video.mp4
```

### Programmatic Usage

```python
from video_processing import VideoAnalyzer, load_config

# Load configuration
config = load_config()

# Initialize analyzer
analyzer = VideoAnalyzer(config)

# Analyze video
result = analyzer.analyze_video("recordings/motion_2026-03-29_17-03-06.mp4")

# Access results
print(f"Trigger frames: {len(result.trigger_frames)}")
print(f"AI Summary: {result.ai_summary}")
```

### Add Known Faces Programmatically

```python
from video_processing import VideoAnalyzer, load_config

config = load_config()
analyzer = VideoAnalyzer(config)

# Add a known face from an image
analyzer.add_known_face_from_image("john_doe", "path/to/john.jpg")

# Get list of known faces
known_faces = analyzer.get_known_faces()
print(f"Known faces: {known_faces}")
```

## Configuration

Video processing settings are configured in `config.yaml` under the `video_processing` section:

```yaml
video_processing:
  face_detection:
    model_path: "video_processing/face_detection_yunet_2023mar.onnx"
    score_threshold: 0.5
    nms_threshold: 0.3
    top_k: 5000

  face_recognition:
    model_path: "video_processing/face_recognition_sface_2021dec.onnx"
    match_threshold: 0.36
    known_faces_dir: "video_processing/known_faces"

  video_analysis:
    sample_interval_seconds: 2
    max_frames_per_analysis: 10
    resize_width: 640
    resize_height: 480
    ai_model: "gpt-4o"
    ai_detail_level: "low"
```

## How It Works

### 1. Face Detection

Uses OpenCV's YuNet model for fast, accurate face detection:
- Detects faces in video frames
- Provides bounding boxes and 5-point facial landmarks
- Configurable confidence threshold

### 2. Face Recognition

Uses OpenCV's SFace model for face recognition:
- Extracts 128-dimensional face embeddings
- Compares against known faces using cosine similarity
- Identifies known vs. unknown individuals

### 3. Video Analysis Pipeline

1. **Frame Sampling**: Samples frames at configured intervals (default: every 2 seconds)
2. **Face Detection**: Detects all faces in sampled frames
3. **Face Recognition**: Matches detected faces against known faces database
4. **Trigger Detection**: Flags frames containing unknown/unauthorized individuals
5. **AI Analysis**: Sends trigger frames to GPT-4 for intelligent summary

### 4. AI-Powered Insights

For trigger events, the system:
- Selects up to 10 representative frames
- Resizes and encodes frames for efficient API usage
- Sends to GPT-4 with context-aware prompts
- Generates concise activity summaries

## Output

The analyzer returns a `VideoAnalysisResult` containing:

- **video_path**: Path to analyzed video
- **total_frames**: Total frames in video
- **analyzed_frames**: Number of frames analyzed
- **trigger_frames**: List of frames with unknown individuals
- **ai_summary**: AI-generated activity summary
- **analysis_duration**: Time taken for analysis

## Performance

- **Face Detection**: ~30-50ms per frame (CPU)
- **Face Recognition**: ~10-20ms per face (CPU)
- **Video Analysis**: Depends on video length and sampling rate
- **AI Summary**: ~2-5 seconds (API call)

## Models

### YuNet (Face Detection)
- **File**: `face_detection_yunet_2023mar.onnx`
- **Size**: ~350KB
- **Speed**: Fast (real-time capable)
- **Accuracy**: High

### SFace (Face Recognition)
- **File**: `face_recognition_sface_2021dec.onnx`
- **Size**: ~40MB
- **Embedding**: 128-dimensional
- **Accuracy**: High (>95% on standard benchmarks)

## Integration with Surveillance Pipeline

The video processing module can be integrated with the main surveillance pipeline to:

1. **Post-Process Recordings**: Analyze motion-triggered recordings for faces
2. **Real-Time Alerts**: Identify unknown individuals in live streams
3. **Activity Logging**: Generate daily summaries of detected activities
4. **Access Control**: Verify authorized vs. unauthorized individuals

## Example Workflow

```python
from video_processing import VideoAnalyzer, load_config

# Initialize
config = load_config()
analyzer = VideoAnalyzer(config)

# Add known faces (one-time setup)
analyzer.add_known_face_from_image("owner", "video_processing/known_faces/owner.jpg")
analyzer.add_known_face_from_image("maid", "video_processing/known_faces/maid.jpg")

# Analyze a recording
result = analyzer.analyze_video("recordings/motion_2026-03-29_17-03-06.mp4")

# Check for unknown individuals
if result.trigger_frames:
    print(f"⚠️ {len(result.trigger_frames)} frames with unknown individuals!")
    print(f"AI Summary: {result.ai_summary}")
else:
    print("✅ Only known individuals detected")
```

## Troubleshooting

### No faces detected
- Check `score_threshold` in config (try lowering to 0.3-0.4)
- Ensure video has sufficient resolution
- Verify faces are clearly visible (not too small or blurry)

### Poor recognition accuracy
- Ensure known face images are high quality
- Use frontal face images for training
- Adjust `match_threshold` (lower = more lenient, higher = stricter)

### AI summary not generated
- Verify `OPENAI_API_KEY` is set in `.env`
- Check OpenAI API quota/limits
- Ensure `openai` package is installed

## WhatsApp Notifications

The module now supports automatic WhatsApp notifications via OpenClaw! When unknown individuals are detected, you'll receive an AI-powered summary directly on WhatsApp.

**See [WHATSAPP_INTEGRATION.md](WHATSAPP_INTEGRATION.md) for complete setup and usage instructions.**

Quick setup:
1. Install and configure OpenClaw CLI
2. Add `WHATSAPP_TARGET_NUMBER=+919834570619` to `.env`
3. Set `whatsapp_notification.enabled: true` in `config.yaml`
4. Run video analysis - notifications sent automatically!

## Future Enhancements

- [ ] Real-time video stream analysis
- [ ] Multi-face tracking across frames
- [ ] Age/gender/emotion detection
- [x] Integration with notification system (WhatsApp via OpenClaw)
- [ ] Web dashboard for results visualization
- [ ] Database storage for analysis history

## License

MIT License - See main project LICENSE file
