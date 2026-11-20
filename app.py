import base64
import io
import os
from flask import Flask, render_template_string, request, jsonify
from PIL import Image, ImageOps

app = Flask(__name__)

CAMERA_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>هلا.cc</title>
    <style>
        body { font-family: sans-serif; text-align: center; padding: 20px; }
        video { width: 100%; max-width: 500px; border: 2px solid #333; border-radius: 8px; }
        button { margin-top: 14px; padding: 12px 24px; font-size: 16px; border: none; border-radius: 8px; background-color: #1a73e8; color: #fff; }
        #status { margin-top: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <h2>تشغيل الكاميرا</h2>
    <video id="video" autoplay playsinline></video>
    <br>
    <button id="captureBtn" disabled>التقاط وإرسال الصورة</button>
    <p id="status">جاري طلب إذن الكاميرا...</p>
    <canvas id="canvas" style="display:none;"></canvas>

    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const captureBtn = document.getElementById('captureBtn');
        const status = document.getElementById('status');

        async function startCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                video.srcObject = stream;
                video.onloadedmetadata = () => { captureBtn.disabled = false; };
                status.textContent = "الكاميرا جاهزة.";
                status.style.color = "green";
            } catch (err) {
                status.textContent = "تعذر تشغيل الكاميرا: " + err.message;
                status.style.color = "#b00020";
            }
        }

        async function captureAndSend() {
            captureBtn.disabled = true;
            status.textContent = "جاري الإرسال والمعالجة...";
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            const imageData = canvas.toDataURL('image/jpeg', 0.85);

            try {
                const res = await fetch('/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: imageData })
                });
                const result = await res.json();
                if (res.ok && result.ok) {
                    status.textContent = "تمت المعالجة في الذاكرة: " + result.processed_size + " (" + result.processed_kb + " KB)";
                    status.style.color = "green";
                } else {
                    status.textContent = "خطأ: " + (result.error || "فشل");
                    status.style.color = "#b00020";
                }
            } catch (err) {
                status.textContent = "خطأ في الاتصال: " + err.message;
                status.style.color = "#b00020";
            } finally {
                captureBtn.disabled = false;
            }
        }

        captureBtn.addEventListener('click', captureAndSend);
        window.addEventListener('DOMContentLoaded', startCamera);
    </script>
</body>
</html>
"""

@app.route("/")
@app.route("/هلا.cc")
def hala_camera():
    return render_template_string(CAMERA_PAGE)

@app.route("/upload", methods=["POST"])
def upload_image():
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image", "")
    if not image_b64:
        return jsonify({"ok": False, "error": "لا توجد صورة"}), 400
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(image_b64, validate=True)
        with Image.open(io.BytesIO(img_bytes)) as img:
            width, height = img.size
            gray_img = ImageOps.grayscale(img)
            ratio = 320 / float(width)
            resized_img = gray_img.resize((320, int(height * ratio)))
            out_buf = io.BytesIO()
            resized_img.save(out_buf, format="JPEG", quality=80)
            processed_kb = round(len(out_buf.getvalue()) / 1024, 1)

        return jsonify({
            "ok": True,
            "processed_size": f"{resized_img.width}x{resized_img.height}",
            "processed_kb": processed_kb
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
