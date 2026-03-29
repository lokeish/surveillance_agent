# Phase 2: Motion-Triggered Recording Pipeline — Summary

## 🎯 Objective

Build an automated pipeline that:
- Connects to the Tapo C210 camera via RTSP
- Continuously monitors the video feed using **frame differencing**
- Records video clips **only when motion is detected**
- Saves recordings as local MP4 files with timestamp overlays

---

## 🏗️ Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ RTSP Stream  │───▶│ Motion Detector  │───▶│ Recording Manager│
│ (Camera)     │    │ (Frame Diff)     │    │ (Video Writer)   │
│              │    │                  │    │                  │
│ StreamCapture│    │ MotionDetector   │    │ RecordingManager │
│ (threaded)   │    │ (OpenCV)         │    │ (buffered)       │
└──────────────┘    └──────────────────┘    └──────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  SurveillancePipeline  │
                    │  (Orchestrator)        │
                    └───────────────────────┘
```

### Processing Flow:
1. **StreamCapture** grabs frames in a background thread (always has latest frame)
2. **Pipeline** reads frames at configured FPS (e.g., 5 FPS to save CPU)
3. **MotionDetector** compares each frame with the previous using frame differencing
4. If motion detected → **RecordingManager** starts writing frames to MP4
5. Pre-buffer captures 3 seconds BEFORE motion for context
6. Post-buffer continues recording 10 seconds AFTER motion stops
7. Recordings saved with timestamps: `motion_2024-03-29_16-45-23.mp4`

---

## 📁 Files Created

| File | Purpose |
|------|---------|
| `phase_2/__init__.py` | Package init |
| `phase_2/config.py` | Configuration loader (YAML + .env) |
| `phase_2/stream_capture.py` | RTSP stream reader with auto-reconnect |
| `phase_2/motion_detector.py` | Frame differencing motion detection |
| `phase_2/recording_manager.py` | Video recording with pre/post buffering |
| `phase_2/pipeline.py` | Main orchestrator connecting all components |
| `phase_2/run.py` | CLI entry point |
| `config.yaml` | Pipeline configuration file |
| `requirements.txt` | Python dependencies |
| `phase_2/summary.md` | This summary |

---

## 🔧 Motion Detection Algorithm

```
Frame N-1 (grayscale + blur)  ──┐
                                 ├──▶ Absolute Difference ──▶ Threshold ──▶ Contours ──▶ Motion Score
Frame N   (grayscale + blur)  ──┘
```

1. Convert frame to **grayscale**
2. Apply **Gaussian blur** (kernel=21) to reduce noise
3. Compute **absolute difference** between current and previous frame
4. Apply **binary threshold** (sensitivity=25) to create motion mask
5. **Dilate** the mask to fill small gaps
6. Find **contours** in the mask
7. Filter by **minimum contour area** (500px)
8. Calculate **motion score** (% of frame with motion)
9. If score ≥ 0.5% AND significant contours exist → **MOTION DETECTED**

---

## 🔄 Recording State Machine

```
         motion detected
    ┌──────────────────────────────┐
    │                              ▼
┌───┴───┐    no motion    ┌────────────┐    motion resumes    
│ IDLE  │◀───────────────│ COOLDOWN   │◀──────────────────┐
│       │   (after post   │ (10s timer)│                   │
│buffer │    buffer)      └─────┬──────┘    ┌──────────────┴──┐
│frames │                       │           │   RECORDING     │
└───────┘                timeout│           │ (writing frames)│
                         expires│           └─────────────────┘
                                │    motion     │
                                │    stops      │
                                └───────────────┘
```

---

## 🚀 How to Run

```bash
# From project root directory:

# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the pipeline (default config)
python -m phase_2.run

# 3. Run with debug logging
python -m phase_2.run --debug

# 4. Run with custom config
python -m phase_2.run --config /path/to/config.yaml
```

### Prerequisites
- Camera must be on and connected to your network
- `phase_1/.env` must be configured with camera credentials
- Python 3.8+ with OpenCV installed

---

## ⚙️ Configuration (`config.yaml`)

| Setting | Default | Description |
|---------|---------|-------------|
| `stream.process_fps` | 5 | Frames analyzed per second |
| `motion.sensitivity` | 25 | Pixel diff threshold (0-255) |
| `motion.blur_kernel` | 21 | Gaussian blur size (noise reduction) |
| `motion.min_motion_area_pct` | 0.5 | Min % of frame that must change |
| `motion.min_contour_area` | 500 | Min contour size in pixels |
| `recording.pre_buffer_seconds` | 3 | Seconds kept before motion |
| `recording.post_buffer_seconds` | 10 | Seconds recorded after motion stops |
| `recording.max_recording_seconds` | 300 | Safety max recording duration |
| `recording.timestamp_overlay` | true | Add timestamp on video |
| `recording.codec` | mp4v | Video codec |

---

## 📊 Key Design Decisions

1. **Threaded Stream Capture**: Background thread continuously grabs frames, so the main loop always gets the latest frame without RTSP buffer lag.

2. **FPS Throttling**: Process at 5 FPS instead of 15-30 FPS from the camera — reduces CPU usage by ~80% while still catching motion.

3. **Pre-Buffer**: Circular buffer keeps last 3 seconds of frames. When motion starts, these frames are written first so you see what happened just before the motion event.

4. **Post-Buffer (Cooldown)**: Continues recording for 10 seconds after motion stops. This prevents fragmented recordings when someone is intermittently moving.

5. **Max Duration Safety**: Force-stops recording at 300 seconds (5 minutes) to prevent runaway recordings.

6. **Auto-Reconnect**: If the RTSP stream drops, the pipeline automatically tries to reconnect with configurable retry intervals.

---

## 🚀 Next Steps (Phase 3+)

- [ ] Add a **web dashboard** for live stream + recorded clips
- [ ] **AI object detection** (YOLO/MobileNet) to filter by person/vehicle
- [ ] **Alerting** — email/push notifications on motion
- [ ] **Multi-camera** support
- [ ] **Disk management** — auto-delete old recordings
- [ ] **Motion zones** — define regions of interest to monitor
