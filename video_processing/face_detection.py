import cv2
import os
import base64
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# --- INITIALIZATION ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load Models
detector = cv2.FaceDetectorYN.create("face_detection_yunet_2023mar.onnx", "", (0, 0))
detector.setScoreThreshold(0.5)  # Set lower threshold for better detection
recognizer = cv2.FaceRecognizerSF.create("face_recognition_sface_2021dec.onnx", "")

def get_face_feature(img):
    """Detects face and extracts its unique 128-d feature vector."""
    detector.setInputSize((img.shape[1], img.shape[0]))
    _, faces = detector.detect(img)
    if faces is not None:
        # Align and extract feature for the first face found
        aligned_face = recognizer.alignCrop(img, faces[0])
        feature = recognizer.feature(aligned_face)
        return feature  # Return the feature as-is (2D array)
    return None

# --- PRE-LOAD KNOWN FACES (Non-Trigger List) ---
# Replace 'hitesh_ref.jpg' with a clear photo of your face
ref_img = cv2.imread("hitesh_image.jpg")
KNOWN_FEATURE = get_face_feature(ref_img)

def is_owner(current_frame, face_box):
    """Compares detected face against known owner feature."""
    aligned_face = recognizer.alignCrop(current_frame, face_box)
    current_feature = recognizer.feature(aligned_face)
    
    # Cosine Similarity: > 0.36 is usually a match
    score = recognizer.match(KNOWN_FEATURE, current_feature, cv2.FaceRecognizerSF_FR_COSINE)
    return score > 0.36

def run_maid_bot(video_path):
    cap = cv2.VideoCapture(video_path)
    trigger_frames = []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    
    print("🕵️ Analyzing video for triggers...")

    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        # Sample every 2 seconds to be efficient
        if frame_idx % int(fps * 2) == 0:
            detector.setInputSize((frame.shape[1], frame.shape[0]))
            _, faces = detector.detect(frame)
            if faces is not None:
                for face in faces:
                    if is_owner(frame, face):
                        print(f"⏭️ Frame {frame_idx}: Owner detected (Non-Trigger).")
                    else:
                        print(f"🔔 Frame {frame_idx}: Unknown/Staff detected (TRIGGER!)")
                        _, buffer = cv2.imencode(".jpg", cv2.resize(frame, (640, 480)))
                        trigger_frames.append(base64.b64encode(buffer).decode("utf-8"))
        
        frame_idx += 1
    cap.release()

    # --- GPT-4O INSIGHT GENERATION ---
    if trigger_frames:
        print(f"🤖 Processing {len(trigger_frames)} trigger frames with GPT-4o...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Analyze these frames of the maid/cook. Provide a summary of work done (mopping, kitchen work) and arrival/departure times."},
                {"role": "user", "content": [
                    {"type": "text", "text": "What activity is happening here?"},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{f}", "detail": "low"}} for f in trigger_frames[:10]]
                ]}
            ]
        )
        return response.choices[0].message.content
    
    return "No trigger events found today."

# Execute
print(run_maid_bot("hall_camera_clip.mp4"))
#print(run_maid_bot("motion_2026-03-29_17-03-06.mp4"))