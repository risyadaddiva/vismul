from flask import Flask, render_template, request, send_file, redirect, url_for, session
from PIL import Image
from pydub import AudioSegment
import subprocess
import io
import os
import numpy as np
import cv2      
import base64

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/image', methods=['GET', 'POST'])
def compress_image():
    if request.method == 'POST':
        file = request.files['image']
        format_out = request.form.get('format', 'JPEG')
        if file:
            input_bytes = file.read()
            original_size = len(input_bytes)
            file.seek(0)
            img = Image.open(io.BytesIO(input_bytes))
            img = img.resize((img.width // 2, img.height // 2))
            buffer = io.BytesIO()
            img.save(buffer, format=format_out, quality=50)
            compressed_size = buffer.tell()
            filename = f'compressed_image.{format_out.lower()}'
            path = os.path.join(UPLOAD_FOLDER, filename)
            with open(path, 'wb') as f:
                f.write(buffer.getvalue())
            session['image_info'] = {'original': original_size, 'compressed': compressed_size, 'file': filename}
            return redirect(url_for('compress_image'))
    info = session.pop('image_info', None)
    return render_template('compress_image.html', info=info)

@app.route('/audio', methods=['GET', 'POST'])
def compress_audio():
    if request.method == 'POST':
        file = request.files['audio']
        format_out = request.form.get('format', 'mp3')
        if file:
            input_bytes = file.read()
            original_size = len(input_bytes)
            file.seek(0)
            original = AudioSegment.from_file(io.BytesIO(input_bytes))
            filename = f'compressed_audio.{format_out}'
            path = os.path.join(UPLOAD_FOLDER, filename)
            original.export(path, format=format_out, bitrate="64k")
            compressed_size = os.path.getsize(path)
            session['audio_info'] = {'original': original_size, 'compressed': compressed_size, 'file': filename}
            return redirect(url_for('compress_audio'))
    info = session.pop('audio_info', None)
    return render_template('compress_audio.html', info=info)

@app.route('/video', methods=['GET', 'POST'])
def compress_video():
    if request.method == 'POST':
        file = request.files['video']
        format_out = request.form.get('format', 'mp4')
        if file:
            input_path = os.path.join(UPLOAD_FOLDER, f'temp_input.{format_out}')
            output_path = os.path.join(UPLOAD_FOLDER, f'compressed_video.{format_out}')
            file.save(input_path)
            original_size = os.path.getsize(input_path)
            subprocess.call([
                'ffmpeg', '-i', input_path,
                '-vcodec', 'libx264', '-crf', '28', '-preset', 'fast',
                '-acodec', 'aac', '-b:a', '64k',
                output_path
            ])
            compressed_size = os.path.getsize(output_path)
            session['video_info'] = {'original': original_size, 'compressed': compressed_size, 'file': f'compressed_video.{format_out}'}
            return redirect(url_for('compress_video'))
    info = session.pop('video_info', None)
    return render_template('compress_video.html', info=info)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/stego', methods=['GET', 'POST'])
def stego():
    result = None
    if request.method == 'POST':
        file = request.files['image']
        message = request.form['message']
        if file and message:
            # Load image
            image_np = np.frombuffer(file.read(), np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply DCT
            gray_float = np.float32(gray)
            dct = cv2.dct(gray_float)

            # Encode message into dct coefficients
            message_bin = ''.join([format(ord(c), '08b') for c in message])
            flat = dct.flatten()
            for i in range(len(message_bin)):
                flat[i] = flat[i] - (int(flat[i]) % 2) + int(message_bin[i])
            encoded_dct = flat.reshape(dct.shape)

            # Apply inverse DCT
            encoded_img = cv2.idct(encoded_dct)
            encoded_img = np.uint8(encoded_img)
            color_encoded = cv2.merge((encoded_img, encoded_img, encoded_img))
            _, buffer = cv2.imencode('.png', color_encoded)
            output_path = os.path.join('uploads', 'stego_image.png')
            with open(output_path, 'wb') as f:
                f.write(buffer.tobytes())
            session['stego'] = True
            result = True
    return render_template('stego.html', result=result)

@app.route('/download_stego')
def download_stego():
    return send_file(os.path.join('uploads', 'stego_image.png'), as_attachment=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
