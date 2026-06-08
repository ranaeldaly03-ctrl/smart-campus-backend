# # import typer
# import cv2
# import supervision as sv
# from ultralytics import YOLO
# # import pyresearch

# # Define the path to the weights file
# # Load the model
# model = YOLO(r"c:\Projects\Graduation\Ai_Camera2\best.pt")
# # app = typer.Typer()

# def process_webcam(output_file="output.mp4"):
#     cap = cv2.VideoCapture(r"C:\Projects\Graduation\Ai_Camera2\test5.mp4")  # Replace with 0 for the default webcam

#     if not cap.isOpened():
#         print("Error: Could not open video file.")
#         return
    
#     box_annotator = sv.BoxAnnotator()
#     label_annotator = sv.LabelAnnotator()

#     # Get the width, height, and fps of the input video
#     # width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     # height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     # fps = cap.get(cv2.CAP_PROP_FPS)

#     # Define the codec and create VideoWriter object
#     # fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'XVID' for .avi
#     # out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

    
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         results = model(frame)[0]
#         detections = sv.Detections.from_ultralytics(results)

#         annotated_frame = box_annotator.annotate(scene=frame, detections=detections)
#         annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections)

#         # Write the annotated frame to the output file
#         # out.write(annotated_frame)

#         cv2.imshow("Webcam", annotated_frame)
#         if cv2.waitKey(25) & 0xFF == ord("q"):
#             break

#     cap.release()
#     # out.release()
#     cv2.destroyAllWindows()

# # @app.command()
# # def webcam(output_file: str = "output.mp4"):
# #     typer.echo("Starting webcam processing...")
# #     process_webcam(output_file)

# if __name__ == "__main__":
#     print("Starting ...")
#     process_webcam()





from flask import Flask, Response
from flask_cors import CORS
import cv2
from ultralytics import YOLO
import supervision as sv
import requests
import time
import os

# =============================
# Flask App
# =============================
app = Flask(__name__)
CORS(app)

# =============================
# Load YOLO Model
# =============================
model = YOLO(r"C:\Projects\Graduation\Ai_Camera2\best.pt")

# =============================
# Snapshot Folder
# =============================
snapshot_folder = r"C:\Projects\Graduation\Ai_Camera2\snapshots"
os.makedirs(snapshot_folder, exist_ok=True)

# =============================
# Video Source
# =============================
video_path = r"C:\Projects\Graduation\Ai_Camera2\test5.mp4"

# =============================
# Annotators
# =============================
box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

# =============================
# Generate Frames
# =============================
def generate_frames():

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("❌ Could not open video")
        return

    last_sent_time = 0

    while True:

        success, frame = cap.read()

        # لو الفيديو خلص يبدأ من الأول
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # =============================
        # YOLO Detection
        # =============================
        results = model(frame)[0]

        detections = sv.Detections.from_ultralytics(results)

        annotated_frame = box_annotator.annotate(
            scene=frame.copy(),
            detections=detections
        )

        annotated_frame = label_annotator.annotate(
            scene=annotated_frame,
            detections=detections
        )

        # =============================
        # Detect Cheating
        # =============================
        for box in results.boxes:

            cls_id = int(box.cls[0])

            label = model.names[cls_id]

            conf = float(box.conf[0])

            print("Detected:", label)

            if label.lower() == "cheating":

                current_time = time.time()

                # يرسل مرة كل 5 ثواني
                if current_time - last_sent_time > 5:

                    try:

                        # =============================
                        # Save Snapshot
                        # =============================
                        filename = f"cheating_{int(time.time())}.jpg"

                        filepath = os.path.join(
                            snapshot_folder,
                            filename
                        )

                        cv2.imwrite(filepath, annotated_frame)

                        print("📸 Snapshot saved:", filename)

                        # =============================
                        # Send to Campus API
                        # =============================
                        res = requests.post(
                            "http://127.0.0.1:5000/log_cheating",
                            json={
                                "student_id": 1,
                                "course_id": 1,
                                "behavior": "cheating",
                                "confidence": conf,
                                "image": filename
                            }
                        )

                        print("Status:", res.status_code)
                        print("Response:", res.text)

                        last_sent_time = current_time

                    except Exception as e:

                        print("❌ Error sending:", e)

        # =============================
        # Convert Frame to Stream
        # =============================
        _, buffer = cv2.imencode('.jpg', annotated_frame)

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame_bytes +
            b'\r\n'
        )

    cap.release()

# =============================
# Video Feed Route
# =============================
@app.route('/video_feed')
def video_feed():

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# =============================
# Home Route
# =============================
@app.route('/')
def home():

    return "YOLO Camera Running"

# =============================
# Run App
# =============================
if __name__ == "__main__":

    print("🚀 Starting Camera Server...")

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )