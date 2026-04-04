# Surveillance Agent

AI-powered surveillance system with motion-triggered recording and automated video analysis.

## Overview

A complete surveillance solution that combines:
- 📹 **Motion-triggered recording** from RTSP camera feeds
- 🔍 **Automated video processing** with face detection and recognition
- 🤖 **AI-powered analysis** using GPT-4 for activity summaries
- 📱 **WhatsApp notifications** for unknown individuals

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RTSP Camera Feed                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Video Pipeline (video_pipeline/)               │
│  • Stream capture from RTSP camera                          │
│  • Motion detection (frame differencing)                    │
│  • Motion-triggered recording with pre/post buffers         │
│  • Saves to recordings/ directory                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ .mp4 files
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Video Processing Watcher (video_processing/)        │
│  • Monitors recordings/ for new videos                      │
│  • Face detection (YuNet model)                             │
│  • Face recognition (SFace model)                           │
│  • AI-powered activity analysis (GPT-4)                     │
│  • WhatsApp notifications for unknown faces                 │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Video Pipeline
- ✅ RTSP stream capture from IP cameras (Tapo C200)
- ✅ Real-time motion detection using frame differencing
- ✅ Pre-motion buffering (captures 3s before motion)
- ✅ Post-motion recording (continues 10s after motion stops)
- ✅ Timestamp overlay on recordings
- ✅ Automatic reconnection on stream failure

### Video Processing
- ✅ Automated monitoring of recordings directory
- ✅ Face detection using YuNet ONNX model
- ✅ Face recognition using SFace ONNX model
- ✅ Known faces database for identification
- ✅ AI-powered activity summaries using GPT-4
- ✅ WhatsApp notifications via OpenClaw
- ✅ State tracking to prevent duplicate processing

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone git@github.com:lokeish/surveillance_agent.git
cd surveillance_agent

# Install dependencies (using uv)
uv pip install -e .

# Or with pip
pip install -e .
```

### 2. Configuration

Create a `.env` file with your credentials:

```bash
# Camera credentials
TAPO_CAMERA_USER=your_camera_username
TAPO_CAMERA_PASSWORD=your_camera_password
TAPO_IP=192.168.1.100

# OpenAI API key (for AI analysis)
OPENAI_API_KEY=sk-...

# WhatsApp notification (optional)
WHATSAPP_TARGET_NUMBER=+1234567890
```

Configure settings in `config.yaml` (see file for all options).

### 3. Add Known Faces

Add images of known individuals to `video_processing/known_faces/`:

```bash
# Add a known face
cp /path/to/person_photo.jpg video_processing/known_faces/person_name.jpg
```

The system will automatically load these faces for recognition.

### 4. Run the System

**Terminal 1: Start the recording pipeline**
```bash
python3 -m video_pipeline.run
```

**Terminal 2: Start the video processing watcher**
```bash
python3 -m video_processing.run_watcher --process-existing
```

## Usage

### Video Pipeline (Recording)

```bash
# Basic usage
python3 -m video_pipeline.run

# With debug logging
python3 -m video_pipeline.run --debug

# Custom config
python3 -m video_pipeline.run --config /path/to/config.yaml
```

### Video Processing Watcher

```bash
# Basic usage (monitors for new videos)
python3 -m video_processing.run_watcher

# Process existing videos on startup
python3 -m video_processing.run_watcher --process-existing

# Debug mode
python3 -m video_processing.run_watcher --debug

# Custom recordings directory
python3 -m video_processing.run_watcher --recordings-dir /path/to/recordings
```

### Manual Video Analysis

```bash
# Analyze a single video
python3 -m video_processing.run recordings/motion_2026-04-04_13-47-13.mp4
```

## Project Structure

```
surveillance_agent/
├── video_pipeline/              # Motion-triggered recording
│   ├── run.py                   # Entry point
│   ├── pipeline.py              # Main pipeline orchestrator
│   ├── stream_capture.py        # RTSP stream handling
│   ├── motion_detector.py       # Motion detection logic
│   ├── recording_manager.py     # Video recording with buffers
│   └── config.py                # Configuration management
│
├── video_processing/            # Automated video analysis
│   ├── run.py                   # Manual analysis entry point
│   ├── run_watcher.py           # Watcher service entry point
│   ├── watcher.py               # Filesystem monitoring & processing
│   ├── processing_state.py      # State tracking
│   ├── video_analyzer.py        # Main analysis orchestrator
│   ├── face_detector.py         # Face detection (YuNet)
│   ├── face_recognizer.py       # Face recognition (SFace)
│   ├── whatsapp_notifier.py     # WhatsApp notifications
│   ├── config.py                # Configuration management
│   ├── README_WATCHER.md        # Detailed watcher documentation
│   └── known_faces/             # Known faces database
│
├── recordings/                  # Recorded videos (auto-created)
├── logs/                        # Log files (auto-created)
├── config.yaml                  # Main configuration file
├── .env                         # Environment variables (create this)
└── README.md                    # This file
```

## Configuration

### Camera Settings (`config.yaml`)

```yaml
stream:
  stream_path: "/stream1"        # HD stream
  rtsp_port: 554
  process_fps: 5                 # Process 5 frames/second
```

### Motion Detection

```yaml
motion:
  sensitivity: 25                # Lower = more sensitive
  min_motion_area_pct: 0.5       # 0.5% of frame must change
  min_contour_area: 500          # Minimum pixels for motion
```

### Recording

```yaml
recording:
  output_dir: "./recordings"
  pre_buffer_seconds: 3          # Capture 3s before motion
  post_buffer_seconds: 10        # Continue 10s after motion
  timestamp_overlay: true
```

### Video Processing

```yaml
video_processing:
  face_detection:
    score_threshold: 0.5         # Face detection confidence
  
  face_recognition:
    match_threshold: 0.36        # Face matching threshold
  
  video_analysis:
    sample_interval_seconds: 2   # Sample every 2 seconds
    ai_model: "gpt-4o"           # OpenAI model
  
  watcher:
    enabled: true
    recordings_dir: "./recordings"
    process_existing_on_startup: false
    file_stable_delay: 2.0
```

## Documentation

- **Video Pipeline**: See `docs/motion_detection_manager.md`
- **Video Processing Watcher**: See `video_processing/README_WATCHER.md`
- **WhatsApp Integration**: See `video_processing/WHATSAPP_INTEGRATION.md`

## Dependencies

- Python 3.12+
- OpenCV (cv2)
- NumPy
- PyTapo (for Tapo cameras)
- Watchdog (filesystem monitoring)
- OpenAI (for AI analysis)
- python-dotenv
- PyYAML

See `pyproject.toml` for complete list.

## How It Works

### 1. Motion Detection & Recording
1. Connects to RTSP camera stream
2. Continuously analyzes frames for motion using frame differencing
3. When motion detected:
   - Writes pre-buffered frames (3s before motion)
   - Continues recording during motion
   - Continues for 10s after motion stops
4. Saves video to `recordings/` with timestamp

### 2. Automated Video Processing
1. Watcher monitors `recordings/` directory
2. When new video detected:
   - Waits for file write completion
   - Samples frames every 2 seconds
   - Detects faces in each frame
   - Recognizes faces against known database
   - Identifies unknown individuals (triggers)
3. If unknown faces found:
   - Generates AI summary using GPT-4
   - Sends WhatsApp notification
4. Saves processing state to prevent duplicates

## Troubleshooting

### Camera Connection Issues
- Verify camera IP and credentials in `.env`
- Check network connectivity
- Ensure RTSP is enabled on camera

### Face Detection Not Working
- Ensure ONNX models are present in `video_processing/`
- Check face detection threshold in config
- Verify images in `known_faces/` contain clear faces

### Watcher Not Processing Videos
- Check `recordings_dir` path is correct
- Verify `watchdog` is installed: `uv pip install watchdog`
- Check logs for errors
- Ensure videos are `.mp4` format

### WhatsApp Notifications Not Sending
- Verify `WHATSAPP_TARGET_NUMBER` in `.env`
- Check OpenClaw service is running
- Enable debug logging to see notification attempts

## Performance Tips

- Lower `process_fps` to reduce CPU usage
- Increase `sample_interval_seconds` for faster processing
- Disable AI summaries if not needed
- Use lower resolution stream (`/stream2`)

## License

MIT License - see LICENSE file

## Authors

Lokeish And Hitesh

## Contributing

Contributions welcome! Please open an issue or PR.
