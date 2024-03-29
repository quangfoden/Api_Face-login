import json
import mysql.connector
from flask import Flask, jsonify
from flask import Flask, request, render_template, send_from_directory, redirect
import face_recognition as fr
import cv2
import numpy as np
import os
from flask_cors import CORS
import base64
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Kết nối đến cơ sở dữ liệu MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="flask"
)
cursor = db.cursor(buffered=True)

known_names = []
known_name_encodings = []
path = "./img_train/"

images = os.listdir(path)
for _ in images:
    if _ == ".DS_Store":
        continue
    image = fr.load_image_file(path + _)
    image_path = path + _
    encoding = fr.face_encodings(image)[0]
    known_name_encodings.append(encoding)
    known_names.append(os.path.splitext(os.path.basename(image_path))[0].capitalize())

print(known_names)
def b64toimg(uri):
    encoded_data = uri.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

@app.route("/create", methods=["POST"])
def create():
    data = request.form.to_dict()
    print(data)
    file = request.files['file'].read()
    npimg = np.frombuffer(file, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    face = fr.face_encodings(img)
    
    query = "INSERT INTO users (fname, lname, email, registerNo, pass, confPass) VALUES (%s, %s, %s, %s, %s, %s)"
    values = (data.get("fName"), data.get("lName"), data.get("email"), data.get("registerNo"), data.get("password"), data.get("confirmPassword"))
    cursor.execute(query, values)
    db.commit()
    
    # Lấy ID của user vừa tạo
    user_id = cursor.lastrowid

    cv2.imwrite("./img_train/"+str(user_id)+".jpg", img)

    known_name_encodings.append(face[0])
    known_names.append(str(user_id))
    
    # return redirect("/index.html", code=302)
    user_data = {
        "id": user_id,
        "fname": data.get("fName"),
        "lname": data.get("lName"),
        "email": data.get("email"),
        "registerNo": data.get("registerNo")
    }
    return jsonify({"status": "success", "user": user_data})

@app.route("/login", methods=["POST"])
def login():
    data = request.form.to_dict()
    b64 = data["imgdata"]
    del data["imgdata"]
    query = f'SELECT * FROM users WHERE email = "{data.get("email")}" AND pass = "{data.get("password")}"'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
         return jsonify({"status": "false", "message":"mật khẩu sai"})
    fuser = {}
    user_id = str(res[0])
    image = b64toimg(b64)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_locations = fr.face_locations(image)
    face_encodings = fr.face_encodings(image, face_locations)
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = fr.compare_faces(known_name_encodings, face_encoding)
        name = ""
        face_distances = fr.face_distance(known_name_encodings, face_encoding)
        best_match = np.argmin(face_distances)
        if matches[best_match]:
            name = known_names[best_match]
            print("name = " + name)
        if name == user_id:
            fuser["Full Name"] = res[1] + " " + res[2]
            fuser["email"] = res[3]
            fuser["registerNo"] = res[4]
            return jsonify({"status": "success", "message":"đăng nhập thành công"})
        else:
            return jsonify({"status": "false", "message":"Khuôn mặt không khơp"})
    return jsonify({"status": "false", "message":"Thử lại sau"})

if __name__ == "__main__":
    app.run(debug=True)
