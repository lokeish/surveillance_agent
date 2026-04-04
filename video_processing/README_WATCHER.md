# Video Processing Watcher

Automated video processing service that monitors the recordings directory and processes videos through face detection, recognition, and AI analysis.

## Overview

The Video Processing Watcher automatically:
- 📹 Monitors the `recordings/` folder for new video files
- 🔍 Processes videos through face detection and recognition
- 🤖 Generates AI-powered summaries using GPT-4
- 📱 Sends WhatsApp notifications when unknown faces are detected
- 💾 Tracks processing state to avoid duplicate processing

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Video Pipeline                           │
│  (Records motion-triggered videos to recordings/)           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ New .mp4 files
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Video Processing Watcher                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FileSystem Observer (watchdog)                      │  │
│  │  - Detects new .mp4 files                            │  │
│  │  - Waits for file write completion                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Processing Queue                                    │  │
│  │  - Queues videos for processing                      │  │
│  │  - Prevents duplicate processing                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Video Analyzer                                      │  │
│  │  - Face detection (YuNet)                            │  │
│  │  - Face recognition (SFace)                          │  │
│  │  - AI summary generation (GPT-4)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  State Manager                                       │  │
│  │  - Tracks processed videos                           │  │
│  │  - Persists to JSON file                             │  │
│  │  - Provides statistics                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  WhatsApp Notifier (Optional)                        │  │
│  │  - Sends alerts for unknown faces                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. **watcher.py**
Main watcher service that orchestrates the entire processing pipeline.

**Key Classes:**
- `VideoFileHandler`: Handles filesystem events and tracks file modifications
- `VideoProcessingWatcher`: Main service that coordinates processing

**Features:**
- Real-time file monitoring using `watchdog` library
- File stability detection (waits for write completion)
- Multi-threaded processing (observer, stability checker, worker)
- Graceful shutdown with statistics

### 2. **processing_state.py**
State management for tracking processed videos.

**Key Classes:**
- `ProcessingRecord`: Dataclass representing a processed video record
- `ProcessingStateManager`: Manages state persistence and queries

**Features:**
- JSON-based state persistence
- Duplicate prevention
- Processing statistics
- Crash recovery

### 3. **run_watcher.py**
Command-line entry point for the watcher service.

## Usage

### Basic Usage

```bash
# Start the watcher with default settings
python3 -m video_processing.run_watcher

# Process existing videos on startup
python3 -m video_processing.run_watcher --process-existing

# Enable debug logging
python3 -m video_processing.run_watcher --debug
```

### Advanced Options

```bash
# Custom recordings directory
python3 -m video_processing.run_watcher --recordings-dir /path/to/recordings

# Custom file stability delay (seconds to wait after file modification)
python3 -m video_processing.run_watcher --file-stable-delay 5.0

# Custom state file location
python3 -m video_processing.run_watcher --state-file /path/to/state.json

# Custom config and env files
python3 -m video_processing.run_watcher --config /path/to/config.yaml --env /path/to/.env
```

### Full Example

```bash
python3 -m video_processing.run_watcher \
  --recordings-dir ./recordings \
  --process-existing \
  --file-stable-delay 2.0 \
  --debug
```

## Configuration

Add the following to your `config.yaml`:

```yaml
video_processing:
  # ... existing config ...
  
  # Automated Watcher Settings
  watcher:
    enabled: true                           # Enable automated video processing watcher
    recordings_dir: "./recordings"          # Directory to monitor for new videos
    process_existing_on_startup: false      # Process existing videos when watcher starts
    file_stable_delay: 2.0                  # Wait N seconds after file modification stops
    state_file: "video_processing/processed_videos.json"  # State persistence file
```

## State File

The watcher maintains a JSON state file (`processed_videos.json`) that tracks all processed videos:

```json
{
  "/absolute/path/to/video.mp4": {
    "video_path": "/absolute/path/to/video.mp4",
    "processed_at": "2026-04-04T14:00:59.123456",
    "trigger_count": 5,
    "analyzed_frames": 10,
    "total_frames": 100,
    "analysis_duration": 2.5,
    "has_unknown_faces": true,
    "notification_sent": true,
    "error": null
  }
}
```

## Workflow

1. **Video Pipeline** records motion-triggered video → saves to `recordings/`
2. **FileSystem Observer** detects new `.mp4` file
3. **Stability Checker** waits for file write completion (default: 2 seconds)
4. **Processing Queue** receives stable file
5. **State Manager** checks if already processed (skip if yes)
6. **Video Analyzer** processes video:
   - Samples frames at configured interval (default: every 2 seconds)
   - Detects faces using YuNet model
   - Recognizes faces using SFace model
   - Identifies unknown faces (triggers)
   - Generates AI summary using GPT-4 (if triggers found)
7. **WhatsApp Notifier** sends alert (if unknown faces detected)
8. **State Manager** saves processing record

## Error Handling

The watcher handles various error scenarios:

- **File not ready**: Waits for file stability before processing
- **Corrupted video**: Marks as processed with error, continues with next
- **Processing failure**: Logs error, marks as processed to avoid retry loops
- **Crash recovery**: Loads state from JSON on restart, resumes processing

## Statistics

On shutdown, the watcher displays processing statistics:

```
📊 PROCESSING STATISTICS
Total processed: 10
With triggers: 3
With unknown faces: 2
Notifications sent: 2
Total analysis time: 25.5s
Avg analysis time: 2.6s
```

## Integration with Video Pipeline

The watcher is designed to run alongside the video pipeline:

### Terminal 1: Video Pipeline (Recording)
```bash
python3 -m video_pipeline.run
```

### Terminal 2: Video Watcher (Processing)
```bash
python3 -m video_processing.run_watcher --process-existing
```

This setup provides:
- ✅ Real-time motion detection and recording
- ✅ Automatic video processing as recordings are created
- ✅ Face detection and recognition
- ✅ AI-powered activity analysis
- ✅ WhatsApp notifications for unknown individuals

## Dependencies

The watcher requires the `watchdog` library:

```bash
# Install with pip
pip install watchdog

# Or with uv
uv pip install watchdog
```

Already added to `pyproject.toml`:
```toml
dependencies = [
    # ... other dependencies ...
    "watchdog>=6.0.0",
]
```

## Troubleshooting

### Watcher not detecting new files
- Check that `recordings_dir` path is correct
- Verify filesystem observer is running (check logs)
- Ensure `.mp4` extension is used

### Videos processed multiple times
- Check state file exists and is writable
- Verify absolute paths are being used consistently
- Clear state file if needed: delete `processed_videos.json`

### Processing too slow
- Reduce `sample_interval_seconds` in config
- Disable AI summary generation
- Process fewer frames per analysis

### File stability issues
- Increase `file_stable_delay` if videos are large
- Check that video pipeline is properly closing files

## Performance Considerations

- **CPU Usage**: Face detection/recognition is CPU-intensive
- **Memory**: Each video is loaded into memory for processing
- **Disk I/O**: State file is written after each video
- **Network**: AI summary requires OpenAI API calls

**Recommendations:**
- Run on a machine with adequate CPU/RAM
- Use SSD for faster video I/O
- Monitor API usage/costs for AI summaries
- Consider processing videos in batches during off-peak hours

## Future Enhancements

Potential improvements:
- [ ] Batch processing mode for large backlogs
- [ ] Priority queue for recent videos
- [ ] Parallel processing of multiple videos
- [ ] Database backend instead of JSON
- [ ] Web dashboard for monitoring
- [ ] Email notifications in addition to WhatsApp
- [ ] Video clip extraction for trigger events
- [ ] Integration with cloud storage
