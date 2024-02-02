'''import os
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
from http.client import HTTPException
import aiohttp
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from PIL import Image
import io
from starlette.responses import FileResponse 

# import reScaleImage as reScale


app = FastAPI()

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
PRE_PROCESSED_FOLDER = "pre_processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


@app.get("/")
def root():
    return {"message": "Welcome to the image processing API!"}


@app.post("/uploadAndProcess")
async def upload_image(file: UploadFile = File(...)):
    try:
        output_path = os.path.join(".", "processed", file.filename)
        image = Image.open(io.BytesIO(await file.read()))
        # Save the uploaded file
        upload_path = os.path.join(UPLOAD_FOLDER, file.filename)
        # Save the processed image
        image.save(upload_path)
        command = f"docscan {upload_path} {output_path}"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Check if the command was successful (return code 0)
        if result.returncode == 0:
            print("Command executed successfully.")
            # reScale.cropRescaleImage(f"{output_path}", file.filename)
            print("Output:\n", result.stdout)
        else:
            print("Command failed with an error.")
            print("Error:\n", result.stderr)
        return {"message": "Upload successful", "filename": file.filename,
                "file_link": "http://13.200.238.163:5001/images/" + file.filename}
    except Exception as e:
        return {"error": str(e)}


@app.get("/images/{filename}")
async def serve_image(filename: str):
    image_path = Path("processed") / filename  # Replace with actual path
    if image_path.exists():
        return FileResponse(image_path)
    else:
        return {"message": "File Not found"}


async def fetch_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()


@app.post("/send-email/")
async def send_email(
    to_email: str = Form(...),
    subject: str = Form("Your Doc is Ready - Renote.ai"),
    message: str = Form("Please check attached Doc."),
    image: UploadFile = File(...)  # Receive the uploaded image
):
    # Access the image data and filename
    image_data = await image.read()
    image_name = image.filename  # Extract the original filename

    # Set up the email message
    msg = MIMEMultipart()
    msg['From'] = 'snehaldev007@gmail.com'  # Replace with your email address
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach HTML content
    msg.attach(MIMEText(message, 'html'))

    # Attach image using the extracted filename
    image_attachment = MIMEImage(image_data, name=image_name)
    msg.attach(image_attachment)

    # Connect to the SMTP server
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Replace with your SMTP server details
            server.starttls()
            server.login('snehaldev007@gmail.com', 'mpznluokyfjzpqfo')  # Replace with your email and password
            server.sendmail('snehaldev007@gmail.com', to_email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"message": "Email sent successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5001)'''

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
from http.client import HTTPException
import aiohttp
from PIL import Image
import io

# Initialize Flask App
app = Flask(__name__)

# Folders for storing images
UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route("/")
def root():
    return jsonify({"message": "Welcome to the image processing API!"})

@app.route("/uploadAndProcess", methods=["POST"])
def upload_image():
    try:
        file = request.files['image']
        filename = secure_filename(file.filename)
        upload_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(upload_path)

        # Process the image (example with PIL, replace with your processing)
        image = Image.open(upload_path)
        output_path = os.path.join(PROCESSED_FOLDER, filename)
        image.save(output_path)

        # Example command (replace with actual processing command)
        command = f"echo 'Processing {upload_path}'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return jsonify({"message": "Upload successful", "filename": filename, 
                            "file_link": f"/images/{filename}"})
        else:
            return jsonify({"error": "Failed to process image"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/images/<filename>")
def serve_image(filename):
    image_path = os.path.join(PROCESSED_FOLDER, filename)
    if os.path.exists(image_path):
        return send_file(image_path)
    else:
        return jsonify({"message": "File Not found"}), 404

@app.route("/send-email/", methods=["POST"])
def send_email():
    try:
        to_email = request.form['to_email']
        subject = request.form.get('subject', 'Your Doc is Ready - Renote.ai')
        message = request.form.get('message', 'Please check attached Doc.')
        file = request.files['image']
        filename = secure_filename(file.filename)
        image_data = file.read()

        msg = MIMEMultipart()
        msg['From'] = 'noreply.renote.ai@gmail.com'
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'html'))
        image_attachment = MIMEImage(image_data, name=filename)
        msg.attach(image_attachment)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('noreply.renote.ai@gmail.com', 'ihde zzml kkip opng')
            server.sendmail('noreply.renote.ai@gmail.com', to_email, msg.as_string())

        return jsonify({"message": "Email sent successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
