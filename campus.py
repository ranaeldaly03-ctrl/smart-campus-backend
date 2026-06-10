from flask import Flask, jsonify, request, send_from_directory, send_file, url_for
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from datetime import date, datetime
from werkzeug.utils import secure_filename
import random
import string
import json
import time
from flask import current_app

import PyPDF2

import os, time, traceback


from ai.pdf_utils import extract_pdf_text
from ai.qa_ai import answer_question
from ai.summarizer_ai import summarize
from ai.quiz_ai import generate_mcq


from flask_socketio import SocketIO, emit, join_room 


DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

dbconfig = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "port": DB_PORT,
    "raise_on_warnings": True,
    "autocommit": False
}
try:
    pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)
except Exception as e:
    print("Warning: could not create pool:", e)
    pool = None



app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


UPLOAD_FOLDER = "static/uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    port=DB_PORT
)

cursor = db.cursor(dictionary=True)


ALLOWED_EXT = {'pdf','docx','pptx','mp4','zip','jpg','jpeg','png','gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT




@app.route('/students' , methods=['GET'])
def get_students():
    cursor.execute("SELECT * FROM users WHERE role = 'Student'")
    students = cursor.fetchall()
    return jsonify(students)



@app.route('/student/<int:student_id>', methods=['GET'])
def get_student(student_id):
    cursor.execute("SELECT * FROM users WHERE role='Student' AND id = %s", (student_id,))
    student=cursor.fetchone()
    if student:
        return jsonify(student)
    else:
        return jsonify({"message" : "Student not found"}), 404



@app.route('/student/<int:student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT c.id AS course_id, c.course_name, c.department,
                   COUNT(sc.student_id) AS student_count
            FROM student_courses sc
            JOIN course c ON sc.course_id = c.id
            WHERE sc.student_id = %s
            GROUP BY c.id, c.course_name, c.department
        """, (student_id,))
        courses = cur.fetchall()
        cur.close()
        return jsonify(courses), 200
    except Exception as e:
        print("Error in get_student_courses:", e)
        return jsonify({"message": str(e)}), 500




@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('pass')
    phone = request.form.get('phone')
    department = request.form.get('department')
    level = request.form.get('level')
    image_file = request.files.get('image')

    image_name = 'admin.jpg'
    if image_file:
        image_name = secure_filename(image_file.filename)
        image_path = os.path.join('static/image', image_name)
        image_file.save(image_path)

    cursor.execute("""
        INSERT INTO users (name, email, pass, phone, department, role, level, image)
        VALUES (%s, %s, %s, %s, %s, 'Student', %s, %s)
    """, (name, email, password, phone, department, level, image_name))    

    db.commit()
    return jsonify({"message": "✅ Student added successfully"})




@app.route('/instructors' , methods=['GET'])
def get_instructors():
    cursor.execute("SELECT * FROM users WHERE role = 'Instructor'")
    instructors = cursor.fetchall()
    return jsonify(instructors)



@app.route('/instructor/<int:instructor_id>', methods=['GET'])
def get_instractor(instructor_id):
    cursor.execute("SELECT * FROM users WHERE role='Instructor' AND id = %s", (instructor_id))
    instructor = cursor.fetchone()
    if instructor:
        return jsonify(instructor)
    else:
        return jsonify({"message": "Instructor not found"}), 404



@app.route('/add_admin', methods=['POST'])
def add_admin():
    try:
        
        if request.content_type.startswith('multipart/form-data'):
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('pass')
            phone = request.form.get('phone')
            image_file = request.files.get('image')  
        else:
            data = request.get_json()
            name = data.get('name')
            email = data.get('email')
            password = data.get('pass')
            phone = data.get('phone')
            image_file = None
    
        if not all([name, email, password, phone]):
            return jsonify({"message": "Missing required fields"}), 400

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 400
       
        image_path = 'uploads/admin.jpg'
 
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"admin_{name}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            image_path = f"uploads/{unique_filename}"

            
        cursor.execute("""
            INSERT INTO users (name, email, pass, phone, role, image)
            VALUES (%s, %s, %s, %s, 'Admin', %s)
        """, (name, email, password, phone, image_path))
        db.commit()

        return jsonify({"message": "✅ Admin added successfully!"}), 200

    except Exception as e:
        db.rollback()
        print("Error adding admin:", e)
        return jsonify({"message": f"Error: {str(e)}"}), 500




@app.route('/add_instructor', methods=['POST'])
def add_instructor():
    try:
        if request.content_type.startswith('multipart/form-data'):
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('pass')
            phone = request.form.get('phone')
            department = request.form.get('department')
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            name = data.get('name')
            email = data.get('email')
            password = data.get('pass')
            phone = data.get('phone')
            department = data.get('department')
            image_file = None

        if not all([name, email, password, phone, department]):
            return jsonify({"message": "Missing required fields"}), 400

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 400

        image_path = 'uploads/default.jpg'
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"instructor_{name}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            image_path = f"uploads/{unique_filename}"

        cursor.execute("""
            INSERT INTO users (name, email, pass, phone, department, role, image)
            VALUES (%s, %s, %s, %s, %s, 'Instructor', %s)
        """, (name, email, password, phone, department, image_path))
        db.commit()

        return jsonify({"message": "✅ Instructor added successfully!"}), 200

    except Exception as e:
        db.rollback()
        print("❌ Error adding instructor:", e)
        return jsonify({"message": f"Error: {str(e)}"}), 500






@app.route('/admin/student_requests', methods=['GET'])
def get_requests():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM student_requests WHERE status='pending'")
    return jsonify(cur.fetchall())


@app.route('/admin/student_requests/<int:id>/approve', methods=['POST'])
def approve_request(id):
    cur = db.cursor()
    cur.execute("UPDATE student_requests SET status='approved' WHERE id=%s", (id,))
    db.commit()
    return jsonify({"ok": True})


@app.route('/admin/student_requests/<int:id>/reject', methods=['POST'])
def reject_request(id):
    cur = db.cursor()
    cur.execute("UPDATE student_requests SET status='rejected' WHERE id=%s", (id,))
    db.commit()
    return jsonify({"ok": True})



@app.route('/cleanup_pending_students')
def cleanup_pending_students():
    cur = db.cursor()
    cur.execute("""
        DELETE FROM users
        WHERE role='Student'
        AND status='pending'
        AND created_at < NOW() - INTERVAL 10 DAY
    """)
    db.commit()
    return "cleaned"




@app.route('/admin/pending_students', methods=['GET'])
def pending_students():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT id, name, email, department, level, status
        FROM users
        WHERE role = 'Student' AND status = 'pending'
    """)
    students = cur.fetchall()
    return jsonify(students), 200



@app.route('/admin/approve_student/<int:id>', methods=['POST'])
def approve_student(id):
    cur = db.cursor()
    cur.execute("""
        UPDATE users
        SET status='active'
        WHERE id=%s AND role='Student'
    """, (id,))
    db.commit()
    return jsonify({"message": "✅ Student approved"})


@app.route('/admin/reject_student/<int:id>', methods=['POST'])
def reject_student(id):
    cur = db.cursor()
    cur.execute("""
        DELETE FROM users
        WHERE id=%s AND role='Student' AND status='pending'
    """, (id,))
    db.commit()
    return jsonify({"message": "❌ Student rejected"})






@app.route('/student_signup', methods=['POST'])
def student_signup():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        department = request.form.get('department')
        level = request.form.get('level')

        image_file = request.files.get('image')

        # صورة افتراضية
        image_path = 'uploads/default_student.png'

        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            unique_name = f"student_{email}_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            image_file.save(save_path)
            image_path = f"uploads/{unique_name}"

        cur = db.cursor()

        cur.execute("""
            INSERT INTO users
            (name, email, pass, phone, department, level, role, status, image)
            VALUES (%s, %s, %s, %s, %s, %s, 'Student', 'pending', %s)
        """, (
            name,
            email,
            password,   # ⚠️ لاحقًا نعمل hashing
            phone,
            department,
            level,
            image_path
        ))

        db.commit()
        return jsonify({"message": "✅ Request sent, waiting for admin approval"}), 200

    except Exception as e:
        db.rollback()
        print("Signup error:", e)
        return jsonify({"message": "❌ Signup failed"}), 500









# في ملف campus.py (أو الملف اللي بتشغلي منه Flask) — استبدلي دالة get_courses الحالية بالآتي:

@app.route('/courses_data', methods=['GET'])
def get_courses():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                c.id,
                c.course_name,
                c.department,
                u.name AS instructor_name,
                COUNT(sc.student_id) AS student_count
            FROM course c
            LEFT JOIN users u ON c.instructor_id = u.id
            LEFT JOIN student_courses sc ON c.id = sc.course_id
            GROUP BY c.id, c.course_name, c.department, u.name
            ORDER BY c.course_name
        """)
        courses = cursor.fetchall()
        return jsonify({"courses": courses}), 200
    except Exception as e:
        print("❌ Error fetching courses:", e)
        return jsonify({"message": f"Error: {str(e)}"}), 500




@app.route('/enroll_student', methods=['POST'])
def enroll_student():
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        course_id = data.get('course_id')

        if not student_id or not course_id:
            return jsonify({"message": "Missing student_id or course_id"}), 400

        cursor = db.cursor()

        cursor.execute("""
             INSERT INTO student_courses (student_id, course_id)
            VALUES (%s, %s)
        """, (student_id, course_id))
        db.commit()
        cursor.close()

        return jsonify({"message": "✅ Student added successfully!"}), 200

    except mysql.connector.IntegrityError as e:
        
        if "Duplicate" in str(e):
            return jsonify({"message": "⚠️ Student already enrolled in this course."}), 400
        else:
            db.rollback()
            return jsonify({"message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print("Error enrolling student:", e)
        return jsonify({"message": f"Error: {str(e)}"}), 500





@app.route('/admins', methods=['GET'])
def get_admins():
    cursor.execute("SELECT * FROM users WHERE role = 'Admin'")
    admins = cursor.fetchall()
    return jsonify(admins)




@app.route('/admin/<int:admin_id>', methods=['GET'])
def get_admin(admin_id):
    cursor.execute("SELECT * FROM users WHERE role='admin' AND id = %s", (admin_id,))
    admin = cursor.fetchone()
    if admin:
        return jsonify(admin)
    else:
        return jsonify({"message": "Admin not found"}), 404




@app.route('/add_grade', methods=['POST'])
def add_grade():
    try:
        data = request.get_json()
        cursor.execute("""
            INSERT INTO grades (student_id, course_id, assignment_id, grade, total_grade)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['student_id'],
            data['course_id'],
            data['assignment_id'],
            data['grade'],
            data['total_grade']
        ))
        db.commit()
        return jsonify({"message": "Grade added successfully!"}), 200
    except Exception as e:
        db.rollback()
        print("Error while adding grade:", e)
        return jsonify({"message": f"Error: {str(e)}"}), 500






@app.route('/get_grades/<int:student_id>', methods=['GET'])
def get_grades(student_id):
    try:
        cursor.execute("""
            SELECT 
                g.id,
                c.name AS course_name,
                a.title AS assignment_title,
                a.type AS assignment_type,
                g.grade,
                g.total_grade
            FROM grades g
            JOIN course c ON g.course_id = c.id
            JOIN assignment a ON g.assignment_id = a.id
            WHERE g.student_id = %s
        """, (student_id,))
        
        grades = cursor.fetchall()
        return jsonify(grades), 200

    except Exception as e:
        print("Error while fetching grades:", e)
        return jsonify({"message": f"Error: {str(e)}"}), 500





@app.route('/login', methods=['POST'])
def login():
    try:
        db = get_db()   # ← أضيفي السطر ده

        data = request.get_json()
        user_id = data.get('id')
        password = data.get('password')

        if not user_id or not password:
            return jsonify({"status": "error", "message": "Missing ID or password"}), 400

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        if user["pass"] == password:

            if user["role"] == "Student" and user.get("status") != "active":
                return jsonify({
                    "status": "error",
                    "message": "⏳ Waiting for admin approval"
                }), 403

            return jsonify({
                "status": "ok",
                "role": user["role"],
                "name": user["name"],
                "id": user["id"],
                "image": user["image"]
            }), 200

        return jsonify({
            "status": "error",
            "message": "Invalid password"
        }), 401

    except Exception as e:
        print("Error in login:", e)
        return jsonify({
            "status": "error",
            "message": "Server error"
        }), 500



@app.route('/user_stats')
def user_stats():
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Student'")
    student_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Instructor'")
    doctor_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Admin'")
    admin_count = cursor.fetchone()[0]

    return jsonify({
        "student": student_count,
        "professors": doctor_count,
        "admin": admin_count
    })




@app.route('/courses_stats')
def courses_count():
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM course")
    courses_count = cursor.fetchone()[0]

    return jsonify({
        "courses": courses_count
    })







@app.route('/users/<role>', methods=['GET'])
def get_users_by_role(role):

    try:
        cursor = db.cursor(dictionary=True)
        level = request.args.get('level')

        if role == "student" and level:
            cursor.execute("SELECT id, name, email, role, level FROM users WHERE role = %s AND level = %s", (role, level))
        else:
            cursor.execute("SELECT id, name, email, role, level FROM users WHERE role = %s", (role,))
        
        users = cursor.fetchall()
        return jsonify({"status": "ok", "users": users})
    except Exception as e:
        print("Error fetchin users:", e)
        return jsonify({"status": "error", "message": "Database error"}), 500



@app.route('/schedule', methods=['GET'])
def get_schedule():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                s.id,
                s.course_id,
                c.course_name,
                u.name AS instructor,
                s.day,
                s.start_time,
                s.end_time,
                s.room
            FROM schedule s
            JOIN course c ON s.course_id = c.id
            LEFT JOIN users u ON s.instructor_id = u.id
        """)
        schedules = cursor.fetchall()

        # تحويل أوقات إلى نصوص (اختياري لكن يساعد الواجهة)
        for item in schedules:
            if 'start_time' in item and item['start_time'] is not None:
                item['start_time'] = str(item['start_time'])
            if 'end_time' in item and item['end_time'] is not None:
                item['end_time'] = str(item['end_time'])

        return jsonify(schedules), 200
    except Exception as e:
        print("❌ Error loading schedule:", e)
        return jsonify({"message": str(e)}), 500





@app.route('/student/<int:student_id>/schedule', methods=['GET'])
def get_student_schedule(student_id):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                s.id,
                s.course_id,
                c.course_name,
                u.name AS instructor,
                s.day,
                s.start_time,
                s.end_time,
                s.room
            FROM schedule s
            JOIN course c ON s.course_id = c.id
            JOIN student_courses sc ON sc.course_id = c.id
            LEFT JOIN users u ON s.instructor_id = u.id
            WHERE sc.student_id = %s
        """, (student_id,))

        schedules = cursor.fetchall()

        for item in schedules:
            if item['start_time']:
                item['start_time'] = str(item['start_time'])
            if item['end_time']:
                item['end_time'] = str(item['end_time'])

        return jsonify(schedules), 200

    except Exception as e:
        print("❌ Error loading student schedule:", e)
        return jsonify({"message": str(e)}), 500

    

@app.route('/schedule', methods=['POST'])
def add_schedule():
    data = request.get_json()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO schedule (course_id, instructor_id, day, start_time, end_time, room)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data['course_id'], data['instructor_id'], data['day'], data['start_time'], data['end_time'], data['room']))
    db.commit()
    return jsonify({"message": "Schedule added successfully!"}), 200


@app.route('/schedule/<int:id>', methods=['PUT'])
def update_schedule(id):
    try:
        data = request.get_json()
        day = data.get("day")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        room = data.get("room")

        cursor = db.cursor()
        cursor.execute("""
            UPDATE schedule 
            SET day=%s, start_time=%s, end_time=%s, room=%s
            WHERE id=%s
        """, (day, start_time, end_time, room, id))
        db.commit()

        return jsonify({"message": "✅ Schedule updated successfully!"}), 200
    except Exception as e:
        print("❌ Error updating schedule:", e)
        db.rollback()
        return jsonify({"message": str(e)}), 500




@app.route('/upload_image/<int:user_id>', methods=['POST'])
def upload_image(user_id):
    try:
        if 'image' not in request.files:
            return jsonify({"message": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"message": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"message": "Invalid file type. Allowed: png,jpg,jpeg,gif"}), 400

        filename = secure_filename(file.filename)
        unique_filename = f"user_{user_id}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        # خزني المسار النسبي داخل قاعدة البيانات (مثال: 'uploads/user_1_img.jpg')
        image_db_path = f"uploads/{unique_filename}"

        cur = db.cursor()
        cur.execute("UPDATE users SET image = %s WHERE id = %s", (image_db_path, user_id))
        db.commit()
        cur.close()

        # ارجّع رابط كامل للواجهة
        full_url = request.host_url.rstrip('/') + '/' + image_db_path
        return jsonify({"message": "Image uploaded successfully!", "image_url": full_url}), 200

    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

# ---- route لتقديم (serve) ملفات الصور من static/uploads ----
@app.route('/uploads/<path:filename>')
def serve_upload(filename):

    uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads')

    return send_from_directory(uploads_dir, filename)
# ---- route لجلب بيانات المستخدم مع رابط الصورة (مفيد بعد login) ----
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, role, image FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        if not user:
            return jsonify({"message": "User not found"}), 404

       
        if user.get('image'):

            filename = os.path.basename(user['image'])

            user['image_url'] = (
                request.host_url.rstrip('/')
                + '/static/uploads/'
                + filename
            )

        else:

            user['image_url'] = (
                request.host_url.rstrip('/')
                + '/static/default.jpg'
            )

        return jsonify(user), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500





import qrcode
from flask import send_file

@app.route('/generate_qr/<int:course_id>', methods=['GET'])
def generate_qr(course_id):
    try:
        qr_data = f"http://127.0.0.1:5000/mark_attendance/{course_id}"
        img = qrcode.make(qr_data)
        img_path = f"static/qr/course_{course_id}.png"
        img.save(img_path)
        return send_file(img_path, mimetype='image/png')
    except Exception as e:
        return jsonify({"message": str(e)}), 500



from datetime import date

@app.route('/mark_attendance/<int:course_id>', methods=['POST'])
def mark_attendance(course_id):
    try:
        data = request.get_json()
        student_id = data.get("student_id")

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO attendance (student_id, course_id, date, status)
            VALUES (%s, %s, %s, 'present')
        """, (student_id, course_id, date.today()))
        db.commit()

        return jsonify({"message": "✅ Attendance marked successfully!"}), 200
    except Exception as e:
        print("❌ Error marking attendance:", e)
        db.rollback()
        return jsonify({"message": str(e)}), 500




@app.route('/attendance_report', methods=['GET'])
def attendance_report():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id, u.name, c.course_name,
                SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absences
            FROM users u
            JOIN attendance a ON u.id = a.student_id
            JOIN course c ON a.course_id = c.id
            WHERE u.role = 'Student'
            GROUP BY u.id, c.course_name
        """)
        data = cursor.fetchall()
        return jsonify(data), 200
    except Exception as e:
        print("❌ Error fetching report:", e)
        return jsonify({"message": str(e)}), 500


@app.route('/attendance_count/<int:course_id>', methods=['GET'])
def attendance_count(course_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            u.id, u.name
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.course_id = %s
    """, (course_id,))

    students = cursor.fetchall()

    return jsonify({
        "count": len(students),
        "students": students
    })



@app.route('/course/<int:course_id>/students', methods=['GET'])
def get_course_students(course_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.name, u.email, u.level
        FROM student_courses sc
        JOIN users u ON sc.student_id = u.id
        WHERE sc.course_id = %s
    """, (course_id,))
    return jsonify(cursor.fetchall())



@app.route('/student/<int:student_id>/attendance/<int:course_id>', methods=['GET'])
def student_attendance(student_id, course_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status='Absent'  THEN 1 ELSE 0 END) AS absent_count
        FROM attendance
        WHERE student_id = %s AND course_id = %s
    """, (student_id, course_id))
    return jsonify(cursor.fetchone())



@app.route('/upload_book', methods=['POST'])
def upload_book():
    try:
        course_id = request.form.get('course_id')
        title = request.form.get('title') or "Resource"
        resource_type = request.form.get('type') or 'book'  # 'book' or 'lecture'
        if 'file' not in request.files:
            return jsonify({"message":"No file"}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({"message":"Empty filename"}), 400
        filename = secure_filename(f.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(save_path)
        rel_path = f"uploads/{filename}"
        cur = db.cursor()
        # حاول حفظ نوع المورد إذا كان العمود موجودًا في جدول book
        try:
            cur.execute("INSERT INTO book (title, file_path, course_id, type) VALUES (%s, %s, %s, %s)",
                        (title, rel_path, course_id, resource_type))
        except mysql.connector.Error:
            # لو العمود 'type' مش موجود — fallback للـ INSERT القديم
            cur.execute("INSERT INTO book (title, file_path, course_id) VALUES (%s, %s, %s)",
                        (title, rel_path, course_id))
        db.commit()
        book_id = cur.lastrowid
        # ربط الكتاب بالمادة (كما عندك)
        try:
            cur.execute("UPDATE course SET book_id = %s WHERE id = %s", (book_id, course_id))
            db.commit()
        except Exception:
            db.rollback()
        return jsonify({"message":"Book uploaded", "book_id": book_id, "type": resource_type}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"message": str(e)}), 500





@app.route('/add_ads', methods=['POST'])
def add_ads():
    try:
        data = request.get_json()
        instructor_id = data.get('instructor_id')
        course_id = data.get('course_id')  # may be None
        text = data.get('text')

        if not instructor_id or not text or text.strip() == "":
            return jsonify({"message": "Missing required fields"}), 400

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            INSERT INTO ads (instructor_id, course_id, text)
            VALUES (%s, %s, %s)
        """, (instructor_id, course_id, text))
        db.commit()
        ad_id = cur.lastrowid

        cur.execute("""
            SELECT a.id, a.instructor_id, a.course_id, a.text, a.created_at,
                   u.name AS instructor_name, c.course_name
            FROM ads a
            LEFT JOIN users u ON a.instructor_id = u.id
            LEFT JOIN course c ON a.course_id = c.id
            WHERE a.id = %s
        """, (ad_id,))
        ad = cur.fetchone()
        cur.close()
        return jsonify({"status": "ok", "ad": ad}), 201
    except Exception as e:
        db.rollback()
        print("Error in add_ads:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/instructor/<int:inst_id>/ads', methods=['GET'])
def get_instructor_ads(inst_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT a.id, a.content, a.course_id, c.course_name, a.created_at
            FROM ads a
            LEFT JOIN course c ON a.course_id = c.id
            WHERE a.instructor_id = %s
            ORDER BY a.created_at DESC
        """, (inst_id,))
        rows = cur.fetchall()
        cur.close()
        return jsonify(rows), 200
    except Exception as e:
        print("Error in get_instructor_ads:", e)
        return jsonify({"message": str(e)}), 500



@app.route('/course/<int:course_id>/ads', methods=['GET'])
def get_course_ads(course_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
           SELECT a.id, a.content, a.created_at, u.name AS instructor_name, a.course_id
           FROM ads a
           JOIN users u ON a.instructor_id = u.id
           WHERE a.course_id = %s OR a.course_id IS NULL
           ORDER BY a.created_at DESC
        """, (course_id,))
        rows = cur.fetchall()
        cur.close()
        return jsonify(rows), 200
    except Exception as e:
        print("Error in get_course_ads:", e)
        return jsonify({"message": str(e)}), 500



@app.route('/ads', methods=['GET'])
def get_all_ads():
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT a.id, a.content, a.course_id, c.course_name, u.name AS instructor_name, a.created_at
            FROM ads a
            LEFT JOIN course c ON a.course_id = c.id
            LEFT JOIN users u ON a.instructor_id = u.id
            ORDER BY a.created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return jsonify(rows), 200
    except Exception as e:
        print("Error in get_all_ads:", e)
        return jsonify({"message": str(e)}), 500




@app.route('/ads/<int:ad_id>', methods=['PUT'])
def update_ad(ad_id):
    try:
        data = request.get_json()
        content = data.get('content')
        course_id = data.get('course_id')  # can be None

        if content is None or content.strip() == "":
            return jsonify({"message":"Content required"}), 400

        cur = db.cursor()
        cur.execute("UPDATE ads SET content = %s, course_id = %s WHERE id = %s", (content, course_id, ad_id))
        db.commit()
        cur.close()
        return jsonify({"status":"ok","message":"Ad updated"}), 200
    except Exception as e:
        db.rollback()
        print("Error update_ad:", e)
        return jsonify({"message": str(e)}), 500




@app.route('/ads/<int:ad_id>', methods=['DELETE'])
def delete_ad(ad_id):
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM ads WHERE id = %s", (ad_id,))
        db.commit()
        cur.close()
        return jsonify({"status":"ok","message":"Ad deleted"}), 200
    except Exception as e:
        db.rollback()
        print("Error delete_ad:", e)
        return jsonify({"message": str(e)}), 500


@app.route('/course/<int:course_id>/schedule', methods=['GET'])
def get_course_schedule(course_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT s.id, s.day, s.start_time, s.end_time, s.room,
                   u.id AS instructor_id, u.name AS instructor_name,
                   c.course_name
            FROM schedule s
            LEFT JOIN users u ON s.instructor_id = u.id
            LEFT JOIN course c ON s.course_id = c.id
            WHERE s.course_id = %s
            ORDER BY 
              FIELD(s.day, 'Saturday','Sunday','Monday','Tuesday','Wednesday','Thursday','Friday'),
              s.start_time
        """, (course_id,))
        rows = cur.fetchall()
        cur.close()
        # convert time objects to strings if necessary
        for r in rows:
            if isinstance(r.get('start_time'), (bytes, bytearray)):
                r['start_time'] = r['start_time'].decode()
            if isinstance(r.get('end_time'), (bytes, bytearray)):
                r['end_time'] = r['end_time'].decode()
            if r.get('start_time') is not None:
                r['start_time'] = str(r['start_time'])
            if r.get('end_time') is not None:
                r['end_time'] = str(r['end_time'])
        return jsonify({"status":"ok", "schedule": rows}), 200
    except Exception as e:
        print("Error in get_course_schedule:", e)
        return jsonify({"status":"error", "message": str(e)}), 500



@app.route('/student/<int:student_id>/dashboard', methods=['GET'])
def student_dashboard(student_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        # 1) جلب معلومات الطالب (level)
        cur.execute("SELECT id, name, level FROM users WHERE id = %s AND role = 'Student'", (student_id,))
        student = cur.fetchone()
        if not student:
            cur.close()
            return jsonify({"message":"Student not found"}), 404

        # 2) عدد الكورسات اللي الطالب مسجل فيها + قائمة الكورسات مع عدد الassignments لكل مادة
        cur.execute("""
            SELECT c.id, c.course_name, c.department,
              (SELECT COUNT(*) FROM assignment a WHERE a.course_id = c.id) AS assignments_count
            FROM student_courses sc
            JOIN course c ON sc.course_id = c.id
            WHERE sc.student_id = %s
        """, (student_id,))
        courses = cur.fetchall()
        courses_count = len(courses)

        # 3) عدد الـ assignments للطالب عبر كورساته (نحسب كل الـ assignments المرتبطة بكورسات الطالب)
        cur.execute("""
            SELECT COUNT(*) AS total_assignments
            FROM assignment a
            WHERE a.course_id IN (
                SELECT course_id FROM student_courses WHERE student_id = %s
            )
        """, (student_id,))
        total_assignments = cur.fetchone()['total_assignments'] or 0

        # 4) جلب تفاصيل الـ assignments (اختياري: للعرض في الواجهة) - يمكن تقييدها ب due_date >= اليوم لو حابة
        cur.execute("""
            SELECT a.id, a.title, a.course_id, a.due_date, a.total_mark, c.course_name
            FROM assignment a
            JOIN course c ON a.course_id = c.id
            WHERE a.course_id IN (
                SELECT course_id FROM student_courses WHERE student_id = %s
            )
            ORDER BY a.due_date ASC
            LIMIT 200
        """, (student_id,))
        assignments = cur.fetchall()

        cur.close()

        return jsonify({
            "student": {"id": student['id'], "name": student['name'], "level": student.get('level')},
            "courses_count": courses_count,
            "courses": courses,
            "assignments_count": int(total_assignments),
            "assignments": assignments
        }), 200

    except Exception as e:
        db.rollback()
        print("Error in student_dashboard:", e)
        return jsonify({"message": str(e)}), 500
    

@app.route('/student/<int:student_id>/ads', methods=['GET'])
def get_student_ads(student_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        # 1) جلب كورسات الطالب المسجلة
        cur.execute("SELECT course_id FROM student_courses WHERE student_id = %s", (student_id,))
        rows = cur.fetchall()
        course_ids = [r['course_id'] for r in rows]
        if not course_ids:
            return jsonify([]), 200

        # 2) اعرف أسماء الأعمدة الموجودة في جدول ads
        cur.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ads'
        """, (db.database,))
        cols = [r['COLUMN_NAME'] for r in cur.fetchall()]

        # 3) مرشحات للأسماء الشائعة
        content_candidates = ['text', 'message', 'body', 'content', 'announcement', 'title', 'description']
        author_candidates = ['posted_by', 'author', 'user_id', 'creator', 'posted_by_id']
        date_candidates = ['created_at', 'date', 'timestamp', 'created', 'posted_at']

        content_col = next((c for c in content_candidates if c in cols), None)
        author_col = next((c for c in author_candidates if c in cols), None)
        date_col = next((c for c in date_candidates if c in cols), None)

        # 4) بناء الاستعلام المرن
        select_parts = [
            "a.id",
            "a.course_id",
            "c.course_name"
        ]
        if content_col:
            select_parts.append(f"a.`{content_col}` AS text")
        else:
            select_parts.append("'' AS text")

        if author_col:
            # join على users إذا author_col يخزن id المستخدم
            # لو author_col عبارة عن اسم مباشرة (مثلاً اسم الناشر) حاولنا نعرضه
            if author_col in cols and author_col.endswith('_id'):
                select_parts.append("u.name AS posted_by")
                join_user = True
            elif author_col in ['posted_by', 'author'] and author_col in cols:
                # قد يكون عمود نصي يحتوي اسم الناشر
                select_parts.append(f"a.`{author_col}` AS posted_by")
                join_user = False
            else:
                # حاول نفترض أنه id
                select_parts.append("u.name AS posted_by")
                join_user = True
        else:
            select_parts.append("'' AS posted_by")
            join_user = False

        if date_col:
            select_parts.append(f"a.`{date_col}` AS created_at")
            order_by = f"a.`{date_col}` DESC"
        else:
            select_parts.append("NULL AS created_at")
            order_by = "a.id DESC"

        select_sql = ", ".join(select_parts)

        placeholders = ",".join(["%s"] * len(course_ids))
        query = f"""
            SELECT {select_sql}
            FROM ads a
            LEFT JOIN course c ON a.course_id = c.id
        """

        if join_user:
            # حاول نوجد اسم العمود المستخدم للربط (posted_by_id أو posted_by)
            # إذا author_col كان من الأنواع اللي تم الافتراض انها id
            # نربط على users.id
            query += " LEFT JOIN users u ON a.posted_by = u.id "

        query += f" WHERE a.course_id IN ({placeholders}) ORDER BY {order_by} LIMIT 200"

        cur.execute(query, tuple(course_ids))
        ads = cur.fetchall()
        return jsonify(ads), 200

    except Exception as e:
        print("Error in get_student_ads:", e)
        import traceback; traceback.print_exc()
        return jsonify({"message": str(e)}), 500
    

@app.route('/student/<int:student_id>/assignments', methods=['GET'])
def get_student_assignments(student_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT
                a.id,
                a.course_id,
                c.course_name,
                a.title,
                a.description,
                a.type,
                a.due_date,
                a.total_mark,
                a.start_time,
                a.end_time,
                a.file_path    -- <- جلب مسار الملف لو موجود
            FROM assignment a
            JOIN course c ON a.course_id = c.id
            JOIN student_courses sc ON sc.course_id = a.course_id
            WHERE sc.student_id = %s AND a.type = 'Assignment'
            ORDER BY a.due_date ASC
        """, (student_id,))
        rows = cur.fetchall()
        cur.close()

        # بِنِي رابط عرض الملف لكل صف إن وُجد file_path
        for r in rows:
            fp = r.get('file_path') or ''
            r['file_path'] = fp
            if fp:
                fp_str = str(fp).lstrip('/')
                # لو مخزن 'uploads/xxx' أو اسم الملف فقط
                if fp_str.startswith('uploads/'):
                    fname = os.path.basename(fp_str)
                    try:
                        r['file_url'] = url_for('serve_upload', filename=fname, _external=True)
                    except Exception:
                        r['file_url'] = request.url_root.rstrip('/') + '/' + fp_str
                elif fp_str.startswith('static/'):
                    r['file_url'] = request.url_root.rstrip('/') + '/' + fp_str
                else:
                    # افتراض: مجرد اسم ملف مخزن
                    try:
                        r['file_url'] = url_for('serve_upload', filename=os.path.basename(fp_str), _external=True)
                    except Exception:
                        r['file_url'] = request.url_root.rstrip('/') + '/static/uploads/' + fp_str
            else:
                r['file_url'] = None

        return jsonify(rows), 200
    except Exception as e:
        print("Error in get_student_assignments:", e)
        return jsonify({"message": str(e)}), 500


@app.route('/student/<int:student_id>/quizzes', methods=['GET'])
def get_student_quizzes(student_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        # نفترض أن الكويزات محفوظة في جدول assignment مع type='Quiz'
        cur.execute("""
            SELECT 
                a.id,
                a.course_id,
                c.course_name,
                a.title,
                a.question_count,     -- لو عندك حقل بعدد الأسئلة
                a.duration,           -- مدة بالدقائق
                a.start_time,
                a.end_time,
                a.created_at
            FROM assignment a
            JOIN course c ON a.course_id = c.id
            JOIN student_courses sc ON sc.course_id = a.course_id
            WHERE sc.student_id = %s AND a.type = 'Quiz'
            ORDER BY a.start_time ASC
        """, (student_id,))
        quizzes = cur.fetchall()
        cur.close()
        return jsonify(quizzes), 200
    except Exception as e:
        print("Error in get_student_quizzes:", e)
        return jsonify({"message": str(e)}), 500







# ====== Grades APIs ======

# GET grades for a student (detailed list + totals per course)
@app.route('/student/<int:student_id>/grades', methods=['GET'])
def get_student_grades(student_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    # درجات مفصلة
    cur.execute("""
        SELECT 
            g.id AS grade_id,
            g.student_id,
            a.course_id,
            c.course_name,
            g.assignment_id,
            a.title AS assignment_title,
            g.grade,
            a.total_mark AS total_grade
        FROM assignment_submissions g
        JOIN assignment a ON g.assignment_id = a.id
        JOIN course c ON a.course_id = c.id
        WHERE g.student_id = %s
        ORDER BY c.course_name, a.due_date
    """, (student_id,))
    rows = cur.fetchall()

    # مجموعات حسب course
    cur.execute("""
        SELECT 
            a.course_id,
            SUM(g.grade) AS total_marks
        FROM assignment_submissions g
        JOIN assignment a ON g.assignment_id = a.id
        WHERE g.student_id = %s
        GROUP BY a.course_id
    """, (student_id,))
    totals = cur.fetchall()
    cur.close()

    return jsonify({"grades": rows, "totals": totals})





@app.route('/course/<int:course_id>/grades', methods=['GET'])
def get_course_grades(course_id):
    conn = None
    cur = None
    try:
        # connection
        if pool:
            conn = pool.get_connection()
        else:
            conn = mysql.connector.connect(**dbconfig)
        cur = conn.cursor(dictionary=True)

        # students enrolled in course (student_courses table uses student_id)
        cur.execute("""
            SELECT u.id AS student_id, u.name
            FROM student_courses sc
            JOIN users u ON sc.student_id = u.id
            WHERE sc.course_id = %s
            ORDER BY u.name
        """, (course_id,))
        students = cur.fetchall() or []

        # fetch grades
        cur.execute("""
            SELECT student_id, mid_grade, final_grade
            FROM course_grades
            WHERE course_id = %s
        """, (course_id,))
        grade_rows = cur.fetchall() or []
        grades_map = { r['student_id']: {'mid_grade': r['mid_grade'], 'final_grade': r['final_grade']} for r in grade_rows }

        students_out = []
        for s in students:
            sid = s['student_id']
            students_out.append({
                "student_id": sid,
                "name": s.get('name'),
                "mid_grade": grades_map.get(sid, {}).get('mid_grade'),
                "final_grade": grades_map.get(sid, {}).get('final_grade')
            })

        return jsonify({"ok": True, "students": students_out}), 200

    except Exception as e:
        app.logger.exception("get_course_grades failed")
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
        except: pass
        try:
            if conn: conn.close()
        except: pass




@app.route('/course/<int:course_id>/grades', methods=['POST'])
def save_course_grade(course_id):
    """
    POST body JSON:
    { "student_id": 5, "mid_grade": 25.5, "final_grade": 40.0 }
    """
    data = request.get_json(silent=True) or {}
    student_id = data.get('student_id')
    mid_grade = data.get('mid_grade')
    final_grade = data.get('final_grade')

    if not student_id:
        return jsonify({"ok": False, "message": "student_id required"}), 400

    conn = None
    cur = None
    try:
        if pool:
            conn = pool.get_connection()
        else:
            conn = mysql.connector.connect(**dbconfig)
        cur = conn.cursor()

        sql = """
            INSERT INTO course_grades (course_id, student_id, mid_grade, final_grade)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              mid_grade = VALUES(mid_grade),
              final_grade = VALUES(final_grade),
              updated_at = CURRENT_TIMESTAMP
        """
        cur.execute(sql, (course_id, student_id, mid_grade, final_grade))
        conn.commit()
        return jsonify({"ok": True, "message": "Grade saved"}), 200

    except Exception as e:
        app.logger.exception("save_course_grade failed")
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
        except: pass
        try:
            if conn: conn.close()
        except: pass

        


# POST add or update a grade (instructor uses this)
@app.route('/grades', methods=['POST'])
def add_or_update_grade():
    try:
        data = request.get_json()
        student_id = data.get("student_id")
        course_id = data.get("course_id")
        assignment_id = data.get("assignment_id")
        grade_val = data.get("grade")

        if not all([student_id, course_id, assignment_id]):
            return jsonify({"message": "Missing required fields"}), 400

        cur = db.cursor()
        # تحقق إذا فيه صف موجود
        cur.execute("""
            SELECT id FROM grades
            WHERE student_id = %s AND course_id = %s AND assignment_id = %s
        """, (student_id, course_id, assignment_id))
        existing = cur.fetchone()

        if existing:
            # تحديث
            cur.execute("""
                UPDATE grades SET grade = %s
                WHERE id = %s
            """, (grade_val, existing[0]))
        else:
            # إضافة
            cur.execute("""
                INSERT INTO grades (student_id, course_id, assignment_id, grade, total_grade)
                VALUES (%s, %s, %s, %s, 0)
            """, (student_id, course_id, assignment_id, grade_val))

        db.commit()
        cur.close()

        # اختياري: نعيد حساب total_grade لهذا الطالب+المادة الآن
        recalc_student_course_total(student_id, course_id)

        return jsonify({"message": "Grade saved"}), 200
    except Exception as e:
        db.rollback()
        print("Error saving grade:", e)
        return jsonify({"message": str(e)}), 500


# وظيفة مساعدة لإعادة حساب المجموع لطالب و مادة (تخزن في total_grade كل صفوف الطالب/المادة)
def recalc_student_course_total(student_id, course_id):
    cur = db.cursor()
    cur.execute("""
        SELECT SUM(grade) FROM grades
        WHERE student_id = %s AND course_id = %s
    """, (student_id, course_id))
    s = cur.fetchone()
    total = s[0] if s and s[0] is not None else 0

    # نحدث كل صفوف الطالب للمادة بالقيمة دي (أو ممكن نخزن صف واحد مجمل)
    cur.execute("""
        UPDATE grades SET total_grade = %s
        WHERE student_id = %s AND course_id = %s
    """, (total, student_id, course_id))
    db.commit()
    cur.close()


# اختياري: Recalculate totals for the whole DB (admin use)
@app.route('/recalc_totals', methods=['POST'])
def recalc_all_totals():
    try:
        cur = db.cursor()
        cur.execute("SELECT DISTINCT student_id, course_id FROM grades")
        pairs = cur.fetchall()
        for student_id, course_id in pairs:
            cur2 = db.cursor()
            cur2.execute("SELECT SUM(grade) FROM grades WHERE student_id=%s AND course_id=%s", (student_id, course_id))
            s = cur2.fetchone()
            total = s[0] if s and s[0] is not None else 0
            cur2.execute("UPDATE grades SET total_grade=%s WHERE student_id=%s AND course_id=%s", (total, student_id, course_id))
            cur2.close()
        db.commit()
        cur.close()
        return jsonify({"message":"Totals recalculated"}), 200
    except Exception as e:
        db.rollback()
        print("Error in recalc:", e)
        return jsonify({"message": str(e)}), 500




# @app.route('/student/<int:student_id>/dashboard', methods=['GET'])
# def get_student_dashboard(student_id):
#     try:
#         cur = db.cursor(dictionary=True)

#         # student basic
#         cur.execute("SELECT id, name, email, role, level, image FROM users WHERE id = %s", (student_id,))
#         student = cur.fetchone() or {}

#         # courses list + assignments count per course
#         cur.execute("""
#             SELECT c.id AS course_id, c.course_name, c.department,
#                    COUNT(a.id) AS assignments_count
#             FROM student_courses sc
#             JOIN course c ON sc.course_id = c.id
#             LEFT JOIN assignment a ON a.course_id = c.id
#             WHERE sc.student_id = %s
#             GROUP BY c.id, c.course_name, c.department
#         """, (student_id,))
#         courses = cur.fetchall() or []
#         courses_count = len(courses)

#         # total assignments count across courses
#         cur.execute("""
#             SELECT COUNT(*) AS total_assignments
#             FROM assignment a
#             JOIN student_courses sc ON sc.course_id = a.course_id
#             WHERE sc.student_id = %s AND a.type = 'Assignment'
#         """, (student_id,))
#         assignments_count = cur.fetchone().get('total_assignments', 0)

#         # upcoming assignments (limit some)
#         cur.execute("""
#             SELECT a.id, a.course_id, c.course_name, a.title, a.due_date, a.total_mark
#             FROM assignment a
#             JOIN course c ON a.course_id = c.id
#             JOIN student_courses sc ON sc.course_id = a.course_id
#             WHERE sc.student_id = %s
#             ORDER BY a.due_date ASC
#             LIMIT 10
#         """, (student_id,))
#         upcoming = cur.fetchall() or []

#         cur.close()

#         return jsonify({
#             "student": student,
#             "courses_count": courses_count,
#             "courses": courses,
#             "assignments_count": assignments_count,
#             "assignments": upcoming
#         }), 200

#     except Exception as e:
#         print("Error in get_student_dashboard:", e)
#         return jsonify({"message": str(e)}), 500



@app.route('/instructor/<int:inst_id>/courses', methods=['GET'])
def get_instructor_courses(inst_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id, c.course_name, c.department,
               COUNT(sc.student_id) AS student_count
        FROM course c
        LEFT JOIN student_courses sc ON c.id = sc.course_id
        WHERE c.instructor_id = %s
        GROUP BY c.id, c.course_name, c.department
    """, (inst_id,))
    courses = cursor.fetchall()
    return jsonify(courses)




def generate_code(length=6):
    # تعديل لو عايزة أرقام بس: return ''.join(random.choices(string.digits, k=length))
    return ''.join(random.choices(string.digits, k=length))



@app.route('/start_attendance/<int:course_id>', methods=['POST'])
def start_attendance(course_id):
    data = request.get_json() or {}
    instructor_id = data.get('instructor_id')
    if not instructor_id:
        return jsonify({"message":"instructor_id required"}), 400

    cur = db.cursor()
    # اغلاق جلسة سابقة لنفس الكورس (اختياري)
    cur.execute("UPDATE attendance_sessions SET active=0, end_time = NOW() WHERE course_id=%s AND active=1", (course_id,))
    db.commit()

    code = generate_code(6)
    cur.execute("INSERT INTO attendance_sessions (course_id, started_by, session_code) VALUES (%s,%s,%s)",
                (course_id, instructor_id, code))
    db.commit()
    session_id = cur.lastrowid

    # ارجاع session_id و code (الاستايل اللي تبعتيه للدكتور)
    return jsonify({"session_id": session_id, "session_code": code}), 200





@app.route('/stop_attendance/<int:course_id>', methods=['POST'])
def stop_attendance(course_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    # 1️⃣ هات السيشن الفعالة
    cur.execute("""
        SELECT id
        FROM attendance_sessions
        WHERE course_id = %s AND active = 1
        ORDER BY start_time DESC
        LIMIT 1
    """, (course_id,))
    session = cur.fetchone()

    if not session:
        return jsonify({"message": "No active session"}), 400

    session_id = session['id']

    # 2️⃣ اقفل السيشن
    cur.execute("""
        UPDATE attendance_sessions
        SET active = 0, end_time = NOW()
        WHERE id = %s
    """, (session_id,))
    db.commit()

    # 3️⃣ ضيف غياب للطلاب اللي محضروش
    cur.execute("""
        INSERT INTO attendance (student_id, course_id, session_id, date, status)
        SELECT sc.student_id, sc.course_id, %s, CURDATE(), 'absent'
        FROM student_courses sc
        WHERE sc.course_id = %s
        AND sc.student_id NOT IN (
            SELECT student_id FROM attendance WHERE session_id = %s
        )
    """, (session_id, course_id, session_id))
    db.commit()

    cur.close()

    return jsonify({
        "message": "Attendance closed & absences recorded",
        "session_id": session_id
    }), 200




@app.route('/mark_by_code', methods=['POST'])
def mark_by_code():
    data = request.get_json() or {}
    student_id = data.get('student_id')
    session_code = data.get('session_code')

    if not student_id or not session_code:
        return jsonify({"message":"student_id and session_code required"}), 400

    db = get_db()
    cur = db.cursor(dictionary=True)
    # 1️⃣ هات السيشن الفعالة بس
    cur.execute("""
        SELECT * FROM attendance_sessions
        WHERE session_code = %s AND active = 1
    """, (session_code,))
    sess = cur.fetchone()

    if not sess:
        return jsonify({"message":"❌ Attendance is closed"}), 403

    session_id = sess['id']
    course_id = sess['course_id']

    # 2️⃣ تأكد إن الطالب مسجل في المادة
    cur.execute("""
        SELECT 1 FROM student_courses
        WHERE student_id = %s AND course_id = %s
    """, (student_id, course_id))
    if not cur.fetchone():
        return jsonify({"message":"Student not enrolled"}), 403

    # 3️⃣ منع التكرار
    cur.execute("""
        SELECT id FROM attendance
        WHERE student_id = %s AND session_id = %s
    """, (student_id, session_id))
    if cur.fetchone():
        return jsonify({"message":"Already marked"}), 200

    # 4️⃣ تسجيل حضور
    cur.execute("""
        INSERT INTO attendance (student_id, course_id, session_id, date, status)
        VALUES (%s, %s, %s, CURDATE(), 'present')
    """, (student_id, course_id, session_id))
    db.commit()

    return jsonify({"message":"✅ Attendance recorded"}), 200





@app.route('/attendance_session/<int:session_id>/students', methods=['GET'])
def attendance_session_students(session_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT u.id, u.name, a.date, a.status
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.session_id = %s
    """, (session_id,))
    students = cur.fetchall()
    return jsonify({"students": students, "count": len(students)}), 200




@app.route('/course/<int:course_id>/last_session', methods=['GET'])
def last_session(course_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM attendance_sessions WHERE course_id=%s ORDER BY start_time DESC LIMIT 1", (course_id,))
    s = cur.fetchone()
    if not s:
        return jsonify({"message":"No sessions"}), 404
    return jsonify(s), 200




def get_cursor(dictionary=True):
    global db
    try:
        # إذا الاتصال متقطع نحاول إعادة الاتصال
        if not db.is_connected():
            db.reconnect(attempts=3, delay=2)
    except Exception:
        # recreate connection if needed (تعدلي بيانات الاتصال هنا لو مختلفة)
        db = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
        )
    return db.cursor(dictionary=dictionary)


@app.route('/student/<int:student_id>/attendance/<int:course_id>', methods=['GET'] , endpoint='student_attendance_course')
def student_attendance(student_id, course_id):
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("""
            SELECT
                SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN status = 'absent'  THEN 1 ELSE 0 END) AS absent_count
            FROM attendance
            WHERE student_id = %s AND course_id = %s
        """, (student_id, course_id))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return jsonify({"present_count": 0, "absent_count": 0}), 200
        return jsonify({
            "present_count": int(row.get('present_count') or 0),
            "absent_count": int(row.get('absent_count') or 0)
        }), 200
    except mysql.connector.Error as e:
        print("DB error student_attendance:", e)
        try:
            cur.close()
        except:
            pass
        return jsonify({"message": str(e)}), 500
    except Exception as e:
        print("Error student_attendance:", e)
        return jsonify({"message": str(e)}), 500


@app.route('/courses/<int:course_id>/students_overview', methods=['GET'])
def students_overview(course_id):
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("""
            SELECT u.id, u.name, u.email, u.level,
                COALESCE(SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END),0) AS present_count,
                COALESCE(SUM(CASE WHEN a.status='absent' THEN 1 ELSE 0 END),0) AS absent_count
            FROM student_courses sc
            JOIN users u ON sc.student_id = u.id
            LEFT JOIN attendance a ON a.student_id = u.id AND a.course_id = sc.course_id
            WHERE sc.course_id = %s
            GROUP BY u.id, u.name
            ORDER BY u.name
        """, (course_id,))
        rows = cur.fetchall()
        cur.close()
        # rows already dictionary because cursor(dictionary=True)
        return jsonify({"students": rows}), 200
    except Exception as e:
        print("Error students_overview:", e)
        try:
            cur.close()
        except:
            pass
        return jsonify({"message": str(e)}), 500





@app.route('/student/<int:student_id>/grades/<int:course_id>', methods=['GET'])
def student_grades(student_id, course_id):
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("""
            SELECT a.title, a.type, g.grade, g.total_grade
            FROM grades g
            JOIN assignment a ON g.assignment_id = a.id
            WHERE g.student_id = %s AND g.course_id = %s
        """, (student_id, course_id))
        rows = cur.fetchall()
        cur.close()
        return jsonify(rows), 200
    except Exception as e:
        print("Error student_grades:", e)
        try:
            cur.close()
        except:
            pass
        return jsonify({"message": str(e)}), 500
    


# 1) إنشاء Quiz (في جدول assignment) — يرجّع assignment.id
@app.route('/create_quiz', methods=['POST'])
def create_quiz():
    try:
        data = request.get_json()
        # متوقع: title, course_id, due_date (اختياري), total_mark (اختياري)
        title = data.get('title') or 'Untitled Quiz'
        course_id = data.get('course_id')
        due_date = data.get('due_date')  # format 'YYYY-MM-DD' or None
        total_mark = data.get('total_mark') or 0

        cur = db.cursor()
        cur.execute("""
            INSERT INTO assignment (course_id, title, description, type, due_date, total_mark)
            VALUES (%s, %s, %s, 'Quiz', %s, %s)
        """, (course_id, title, data.get('description',''), due_date, total_mark))
        db.commit()
        quiz_id = cur.lastrowid
        cur.close()
        return jsonify({"status":"ok","quiz_id": quiz_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"status":"error","message": str(e)}), 500


# 2) إضافة سؤال لكويز
@app.route('/quiz/<int:quiz_id>/questions', methods=['POST'])
def add_question(quiz_id):
    try:
        data = request.get_json()
        q_type = data.get('q_type') or data.get('type') or 'MCQ'
        text = data.get('question_text') or data.get('text') or ''
        options = data.get('options')  # can be list or string
        correct = data.get('correct') or data.get('correct_answer')

        # normalize options -> store JSON
        import json
        opts_json = None
        if isinstance(options, list):
            opts_json = json.dumps(options, ensure_ascii=False)
        elif isinstance(options, str) and options.strip():
            # split lines into array then json
            arr = [s.trim() for s in options.splitlines() if s.strip()] if hasattr(options, 'splitlines') else []
            opts_json = json.dumps(arr, ensure_ascii=False) if arr else None

        conn = pool.get_connection() if pool else db
        cur = conn.cursor()
        cur.execute("INSERT INTO quiz_question (assignment_id, q_type, question_text, options, correct_answer) VALUES (%s,%s,%s,%s,%s)",
                    (quiz_id, q_type, text, opts_json, correct))
        qid = cur.lastrowid
        conn.commit()
        cur.close()
        if pool and conn: conn.close()
        return jsonify({"ok": True, "question_id": qid}), 201
    except Exception as e:
        app.logger.error("DB error add_question: %s", e)
        try:
            conn.rollback()
        except: pass
        return jsonify({"ok": False, "message": str(e)}), 500



@app.route('/quiz/<int:quiz_id>/questions/<int:qid>', methods=['DELETE'])
def delete_question(quiz_id, qid):
    try:
        conn = pool.get_connection() if pool else db
        cur = conn.cursor()
        cur.execute("DELETE FROM quiz_question WHERE id=%s AND assignment_id=%s", (qid, quiz_id))
        conn.commit()
        cur.close()
        if pool and conn: conn.close()
        return jsonify({"ok": True, "deleted": True}), 200
    except Exception as e:
        app.logger.error("DB error delete_question: %s", e)
        try: conn.rollback()
        except: pass
        return jsonify({"ok": False, "message": str(e)}), 500




@app.route('/publish_quiz/<int:quiz_id>', methods=['POST'])
def publish_quiz(quiz_id):
    try:
        conn = pool.get_connection() if pool else db
        cur = conn.cursor()
        # your previous code tried to update 'assignments' table; update 'assignment' here
        cur.execute("UPDATE assignment SET published=1 WHERE id=%s AND type='Quiz'", (quiz_id,))
        conn.commit()
        cur.close()
        if pool and conn: conn.close()
        return jsonify({"ok": True, "message": "Quiz published."}), 200
    except Exception as e:
        try: conn.rollback()
        except: pass
        app.logger.error("DB error publish_quiz: %s", e)
        return jsonify({"ok": False, "message": str(e)}), 500

# 3) جلب كويز مع الأسئلة (للطالب)
@app.route('/quiz/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        # جدولك اسمه `assignment` — نتحقق أن النوع Quiz (اختياري)
        cur.execute("SELECT id, course_id, title, due_date, total_mark, start_time, end_time FROM assignment WHERE id = %s AND type = 'Quiz'", (quiz_id,))
        quiz = cur.fetchone()
        if not quiz:
            cur.close()
            return jsonify({"message":"Quiz not found"}), 404

        # جلب الاسئلة من جدول quiz_question
        cur.execute("SELECT id, assignment_id, q_type, question_text, options, correct_answer, marks FROM quiz_question WHERE assignment_id = %s ORDER BY id", (quiz_id,))
        qrows = cur.fetchall()
        # parse options if stored as JSON string
        for r in qrows:
            if r.get('options') and isinstance(r.get('options'), str):
                try:
                    import json
                    r['options'] = json.loads(r['options'])
                except:
                    r['options'] = r['options'].splitlines()
            else:
                # ensure array
                r['options'] = r.get('options') or []
        quiz['questions'] = qrows
        cur.close()
        return jsonify(quiz), 200
    except Exception as e:
        app.logger.error("DB error get_quiz: %s", e)
        return jsonify({"message":"DB error"}), 500



# 4) إرسال إجابات الطالب (حفظ النتائج — بسيط)
@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        answers = data.get('answers')  # [{question_id, answer_string}...]

        # بسيطة: نحسب درجات مطابقة الإجابة الصحيحة (للـ MCQ/TF/Short) — ممكن تطوري
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, correct_answer, points FROM quiz_question WHERE assignment_id = %s", (quiz_id,))
        qrows = cur.fetchall()
        correct_map = {q['id']:{'correct': q['correct_answer'], 'points': q['points']} for q in qrows}

        total_score = 0
        for a in answers:
            qid = a.get('question_id')
            ans = str(a.get('answer','')).strip()
            item = correct_map.get(qid)
            if not item:
                continue
            # مقارنة بسيطة (case-insensitive). لو عايزة تقييم أكثر تعقيد لازم تطوري.
            if item['correct'] is not None and ans.lower() == str(item['correct']).lower():
                total_score += float(item['points'] or 0)

        # خزني النتيجة في جدول grades (أو جدول خاص بالquiz_results)
        cur.execute("""
            INSERT INTO grades (student_id, course_id, assignment_id, grade, total_grade)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, data.get('course_id'), quiz_id, total_score, data.get('total_mark',0)))
        db.commit()
        cur.close()
        return jsonify({"status":"ok","score": total_score}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"status":"error","message": str(e)}), 500







@app.route('/quiz/<int:assignment_id>/questions', methods=['POST'])
def add_quiz_question(assignment_id):
    try:
        data = request.get_json()
        qtype = data.get('q_type', 'MCQ')
        qtext = data['question_text']
        options = data.get('options')   # array or None
        correct = data.get('correct_answer')
        marks = int(data.get('marks', 1))

        cur = db.cursor()
        cur.execute("""
            INSERT INTO quiz_question (assignment_id, q_type, question_text, options, correct_answer, marks)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (assignment_id, qtype, qtext, json.dumps(options) if options else None, correct, marks))
        db.commit()
        qid = cur.lastrowid
        cur.close()
        return jsonify({"message":"question added","question_id": qid}), 200
    except Exception as e:
        db.rollback()
        print("Error add question:", e)
        return jsonify({"message": str(e)}), 500

@app.route('/quiz/<int:assignment_id>/questions', methods=['GET'])
def get_quiz_questions(assignment_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM quiz_question WHERE assignment_id = %s ORDER BY id", (assignment_id,))
        rows = cur.fetchall()
        cur.close()
        # parse options JSON
        for r in rows:
            if r.get('options'):
                try:
                    r['options'] = json.loads(r['options'])
                except:
                    r['options'] = None
        return jsonify({"questions": rows}), 200
    except Exception as e:
        print("Error get questions:", e)
        return jsonify({"message": str(e)}), 500

# helper: get assignment (quiz) with questions
@app.route('/assignment/<int:assignment_id>/with_questions', methods=['GET'])
def get_assignment_with_questions(assignment_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM assignment WHERE id = %s", (assignment_id,))
        assignment = cur.fetchone()
        if not assignment:
            cur.close()
            return jsonify({"message":"Assignment not found"}), 404

        cur.execute("SELECT * FROM quiz_question WHERE assignment_id = %s ORDER BY id", (assignment_id,))
        questions = cur.fetchall()
        cur.close()
        for q in questions:
            if q.get('options'):
                try: q['options'] = json.loads(q['options'])
                except: q['options'] = None
        assignment['questions'] = questions
        return jsonify(assignment), 200
    except Exception as e:
        print("Error get assignment with questions:", e)
        return jsonify({"message": str(e)}), 500



from datetime import datetime

@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    conn = None
    cur = None

    try:
        # ===============================
        # استقبال البيانات (JSON أو form)
        # ===============================
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            course_id = request.form.get('course_id')
            title = request.form.get('title')
            description = request.form.get('description') or ''
            type_ = request.form.get('type') or 'Assignment'
            due_date = request.form.get('due_date')
            total_mark = request.form.get('total_mark') or 0
            file_obj = request.files.get('file')
        else:
            data = request.get_json(force=True, silent=True) or {}
            course_id = data.get('course_id')
            title = data.get('title')
            description = data.get('description') or ''
            type_ = data.get('type') or 'Assignment'
            due_date = data.get('due_date')
            total_mark = data.get('total_mark') or 0
            file_obj = None

        # ===============================
        # تحويل التاريخ (المهم 👈)
        # ===============================
        if due_date:
            try:
                due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            except:
                due_date = None

        # ===============================
        # validation
        # ===============================
        if not course_id or not title:
            return jsonify({"ok": False, "message": "course_id and title required"}), 400

        # ===============================
        # الاتصال بالداتا بيز
        # ===============================
        if pool:
            conn = pool.get_connection()
            cur = conn.cursor()
        else:
            if db is None or not getattr(db, 'is_connected', lambda: True)():
                db.reconnect(attempts=3, delay=1)
            conn = db
            cur = conn.cursor()

        # ===============================
        # إدخال assignment
        # ===============================
        try:
            cur.execute("""
                INSERT INTO assignment 
                (course_id, title, description, type, due_date, total_mark)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (course_id, title, description, type_, due_date, total_mark))
        except:
            # fallback لو اسم الجدول مختلف
            cur.execute("""
                INSERT INTO assignment 
                (course_id, title, description, type, due_date, total_mark)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (course_id, title, description, type_, due_date, total_mark))

        assignment_id = cur.lastrowid

        # ===============================
        # رفع الملف (لو موجود)
        # ===============================
        if file_obj and file_obj.filename:
            if not allowed_file(file_obj.filename):
                conn.rollback()
                return jsonify({"ok": False, "message": "Invalid file type"}), 400

            filename = secure_filename(file_obj.filename)
            unique = f"assignment_{assignment_id}_{int(time.time())}_{filename}"

            uploads_dir = app.config.get('UPLOAD_FOLDER')
            os.makedirs(uploads_dir, exist_ok=True)

            save_path = os.path.join(uploads_dir, unique)
            file_obj.save(save_path)

            rel_path = f"uploads/{unique}"

            try:
                cur.execute("UPDATE assignment SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
            except:
                try:
                    cur.execute("UPDATE assignment SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
                except:
                    try:
                        cur.execute("""
                            INSERT INTO assignment_files 
                            (assignment_id, original_filename, file_path)
                            VALUES (%s, %s, %s)
                        """, (assignment_id, filename, rel_path))
                    except:
                        pass

        # ===============================
        # حفظ
        # ===============================
        conn.commit()

        return jsonify({
            "ok": True,
            "assignment_id": assignment_id,
            "due_date": str(due_date) if due_date else None
        }), 201

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except:
            pass

        import traceback
        traceback.print_exc()

        return jsonify({"ok": False, "message": str(e)}), 500

    finally:
        try:
            if cur:
                cur.close()
            if pool and conn:
                conn.close()
        except:
            pass





from flask import url_for

@app.route('/course/<int:course_id>/books_and_files', methods=['GET'])
def course_books_and_files(course_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT id, course_id, title, file_path, type, uploaded_at
            FROM book
            WHERE course_id = %s
            ORDER BY uploaded_at DESC
        """, (course_id,))
        rows = cur.fetchall()
        cur.close()

        for r in rows:
            raw = (r.get('file_path') or '').lstrip('/')
            filename = ''
            if raw.startswith('uploads/'):
                filename = raw[len('uploads/'):]
            else:
                filename = raw

            if filename:
                try:
                    r['file_url'] = url_for('serve_upload', filename=filename, _external=True)
                except Exception:
                    r['file_url'] = f"http://127.0.0.1:5000/uploads/{filename}"
            else:
                r['file_url'] = None

        return jsonify({'success': True, 'resources': rows}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/debug_uploads/<path:filename>')
def debug_uploads(filename):
    uploads_dir = app.config.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(__file__), 'uploads')
    full = os.path.join(uploads_dir, filename)
    print('DEBUG serve_upload request for:', filename)
    print('DEBUG uploads_dir =', uploads_dir)
    print('DEBUG full path =', full)
    print('DEBUG exists =', os.path.exists(full))
    if not os.path.exists(full):
        return jsonify({"message":"file not found on server","path": full}), 404
    return send_from_directory(uploads_dir, filename, as_attachment=False)


# ===========================
#  Serve Uploaded Files
# ===========================

# @app.route('/uploads/<path:filename>')
# def serve_uploads(filename):
#     uploads_dir = app.config.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    
#     full = os.path.join(uploads_dir, filename)

#     print('DEBUG serve_uploads request for:', filename)
#     print('DEBUG uploads_dir =', uploads_dir)
#     print('DEBUG full path =', full)
#     print('DEBUG exists =', os.path.exists(full))

#     if not os.path.exists(full):
#         return jsonify({"message":"file not found", "path": full}), 404

#     return send_from_directory(uploads_dir, filename, as_attachment=False)




import stat

@app.route('/assignments/<int:assignment_id>/submit', methods=['POST'])
def submit_assignment(assignment_id):
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "No file provided"}), 400

        f = request.files['file']
        if f.filename == '':
            return jsonify({"ok": False, "error": "Empty filename"}), 400

        student_id = request.form.get('student_id')
        if not student_id:
            return jsonify({"ok": False, "error": "student_id required"}), 400

        uploads_dir = app.config.get('UPLOAD_FOLDER')
        os.makedirs(uploads_dir, exist_ok=True)

        filename = secure_filename(f.filename)

        name, ext = os.path.splitext(filename)

        unique = f"{int(time.time())}{ext}"
        save_path = os.path.join(uploads_dir, unique)
        f.save(save_path)

        # ✅ نحفظ في الجدول الصح
        cur = db.cursor()
        cur.execute("""
            INSERT INTO assignment_submissions 
            (assignment_id, student_id, original_filename, file_path, locked, uploaded_at)
            VALUES (%s,%s,%s,%s,%s,NOW())
        """, (assignment_id, student_id, filename, f"uploads/{unique}", 1))

        db.commit()
        sub_id = cur.lastrowid
        cur.close()

        file_url = request.url_root.rstrip('/') + "/static/uploads/" + unique

        return jsonify({
            "ok": True,
            "file_url": file_url,
            "submission_id": sub_id
        }), 200

    except Exception as e:
        db.rollback()
        print("❌ ERROR:", e)
        return jsonify({"ok": False, "error": str(e)}), 500



@app.route('/assignment/<int:assignment_id>/upload_file', methods=['POST'])
def upload_file_for_assignment(assignment_id):
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "message": "No file provided"}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({"ok": False, "message": "Empty filename"}), 400
        if not allowed_file(f.filename):
            return jsonify({"ok": False, "message": "Invalid file type"}), 400

        filename = secure_filename(f.filename)
        unique = f"assignment_{assignment_id}_{int(time.time())}_{filename}"
        uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, unique)
        f.save(save_path)
        print("SAVED:", unique)
        print("PATH:", save_path)
        rel_path = f"uploads/{unique}"

        # try update assignments.file_path, fallback to assignment_files
        cur = None; conn = None
        if pool:
            conn = pool.get_connection()
            cur = conn.cursor()
        else:
            conn = db
            cur = conn.cursor()
        try:
            cur.execute("UPDATE assignment SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
        except Exception:
            try:
                cur.execute("UPDATE assignment SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
            except Exception:
                try:
                    cur.execute("INSERT INTO assignment_files (assignment_id, original_filename, file_path) VALUES (%s,%s,%s)",
                                (assignment_id, filename, rel_path))
                except Exception as e:
                    conn.rollback()
                    return jsonify({"ok": False, "message": f"DB error: {e}"}), 500

        conn.commit()
        try:
            if pool and conn: conn.close()
        except: pass

        file_url = url_for('serve_upload', filename=unique, _external=True)
        return jsonify({"ok": True, "file_path": rel_path, "file_url": file_url}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "message": str(e)}), 500




@app.route('/submission/<int:submission_id>/unlock', methods=['POST'])
def unlock_submission(submission_id):
    try:
        data = request.get_json() or {}
        action_by = data.get('action_by')  # user id or role in real app
        # TODO: تحقق إن action_by لديه صلاحية (مثلاً user.role == 'Admin' أو نفس الطالب)
        # الآن: نسمح لو مررنا force=True أو إذا action_by هو نفس student (اختياري)
        force = data.get('force', False)

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, student_id, file_path, locked FROM assignment_submissions WHERE id = %s", (submission_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"ok": False, "error": "Submission not found"}), 404

        # مثال بسيط للسياسة: يسمح للطالب نفسه أو لأي admin (يجب تنفيذ تحقق حقيقي)
        # هنا أتحقق: إذا action_by == student_id نسمح، أو force==True نسمح
        allowed = False
        if force:
            allowed = True
        elif action_by and str(action_by) == str(row['student_id']):
            allowed = True
        # else: نحتاج تحقق أكثر — رفض
        if not allowed:
            cur.close()
            return jsonify({"ok": False, "error": "Not authorized to unlock"}), 403

        # unlock DB
        cur2 = db.cursor()
        cur2.execute("UPDATE assignment_submissions SET locked = 0 WHERE id = %s", (submission_id,))
        db.commit()
        cur2.close()

        # also make file writable again (best-effort)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(row['file_path']))
        try:
            os.chmod(file_path, 0o666)
        except Exception as e:
            app.logger.debug("Could not chmod file to writable: %s", e)

        cur.close()
        return jsonify({"ok": True, "message": "Unlocked"}), 200

    except Exception as e:
        db.rollback()
        app.logger.exception("unlock_submission failed")
        return jsonify({"ok": False, "error": str(e)}), 500






@app.route('/submission/<int:submission_id>', methods=['DELETE'])
def delete_submission(submission_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, file_path, locked FROM assignment_submissions WHERE id = %s", (submission_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"ok": False, "error": "Not found"}), 404

        if row['locked']:
            cur.close()
            return jsonify({"ok": False, "error": "Submission is locked. Unlock before delete."}), 403

        # delete file from disk
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(row['file_path']))
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            app.logger.debug("Could not remove file: %s", e)

        # delete DB record
        cur2 = db.cursor()
        cur2.execute("DELETE FROM assignment_submissions WHERE id = %s", (submission_id,))
        db.commit()
        cur2.close()

        cur.close()
        return jsonify({"ok": True, "message": "Deleted"}), 200

    except Exception as e:
        db.rollback()
        app.logger.exception("delete_submission failed")
        return jsonify({"ok": False, "error": str(e)}), 500


import os
from flask import request, jsonify, url_for
import mysql.connector
from mysql.connector import pooling

# --- تأكّد إن dbconfig و pool معرفة في أعلى الملف كما عندك ---
# dbconfig = {...}
# pool creation code كما عندك

def get_conn():
    """
    Return a live connection. If pool available, get from pool.
    If connection is stale, attempt ping/reconnect.
    """
    if pool:
        try:
            conn = pool.get_connection()
            # ensure connection is alive
            try:
                conn.ping(reconnect=True, attempts=3, delay=0.5)
            except Exception:
                # if ping fails, close and re-get
                try:
                    conn.close()
                except:
                    pass
                conn = pool.get_connection()
            return conn
        except Exception as e:
            # fallback to direct connect
            app.logger.warning("pool.get_connection failed, fallback to direct: %s", e)
    # fallback direct
    return mysql.connector.connect(**dbconfig)


@app.route('/assignments/<int:aid>/submission', methods=['GET'])
def get_assignment_submission_route(aid):
    """
    GET /assignments/<aid>/submission?student_id=5
    Returns JSON with submission info or found:false
    """
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"ok": False, "message": "student_id required"}), 400

    conn = None
    cur = None
    try:
        conn = get_conn()
        # use buffered cursor to avoid "commands out of sync"
        cur = conn.cursor(dictionary=True, buffered=True)

        sql = """
            SELECT id AS submission_id,
                   original_filename,
                   file_path,
                   locked,
                   uploaded_at,
                   grade
            FROM assignment_submissions
            WHERE assignment_id = %s AND student_id = %s
            ORDER BY uploaded_at DESC, id DESC
            LIMIT 1
        """
        cur.execute(sql, (aid, student_id))
        row = cur.fetchone()
        # IMPORTANT: if you executed a stored procedure or multiple result sets earlier,
        # ensure they were consumed/closed before using this cursor.

        if not row:
            return jsonify({"ok": True, "found": False}), 200

        file_url = None
        fp = row.get('file_path')
        if fp:
            # normalize path
            fp = str(fp).lstrip('/')
            # if stored full path like 'static/uploads/xxx'
            if fp.startswith('static/'):
                # get filename from path and use url_for static
                filename = os.path.basename(fp)
                file_url = url_for('static', filename=f'uploads/{filename}', _external=True)
            elif fp.startswith('uploads/'):
                filename = os.path.basename(fp)
                file_url = url_for('static', filename=f'uploads/{filename}', _external=True)
            else:
                # assume filename only
                filename = os.path.basename(fp)
                file_url = url_for('static', filename=f'uploads/{filename}', _external=True)

        return jsonify({
            "ok": True,
            "found": True,
            "submission_id": row.get('submission_id'),
            "original_filename": row.get('original_filename'),
            "file_url": file_url,
            "locked": bool(row.get('locked')),
            "uploaded_at": row.get('uploaded_at'),
            "grade": row.get('grade')
        }), 200

    except mysql.connector.errors.OperationalError as oe:
        app.logger.exception("DB operational error in get_assignment_submission")
        return jsonify({"ok": False, "message": "DB operational error: " + str(oe)}), 500
    except Exception as e:
        app.logger.exception("get_assignment_submission failed")
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()   # if conn from pool, this returns it to pool
        except Exception:
            pass





@app.route('/course/<int:course_id>/assignments', methods=['GET'])
def get_course_assignments(course_id):
    conn = None
    cur = None
    try:
        if pool:
            conn = pool.get_connection()
        else:
            conn = mysql.connector.connect(**dbconfig)

        cur = conn.cursor(dictionary=True, buffered=True)

        sql = """
            SELECT 
                id, course_id, title, description, start_time, end_time,
                type, due_date, total_mark, duration, question_count,
                created_at, file_path
            FROM assignment
            WHERE course_id = %s
            ORDER BY created_at DESC
        """

        cur.execute(sql, (course_id,))
        rows = cur.fetchall()

        # generate full file_url if file_path exists
        for r in rows:
            fp = r.get('file_path')
            if fp:
                fp = str(fp).lstrip("/")
                if fp.startswith("uploads/") or fp.startswith("static/"):
                    r['file_url'] = request.url_root.rstrip("/") + "/" + fp
                else:
                    r['file_url'] = request.url_root.rstrip("/") + "/uploads/" + fp
            else:
                r['file_url'] = None

        return jsonify({"ok": True, "assignments": rows}), 200

    except Exception as e:
        app.logger.exception("get_course_assignments failed")
        return jsonify({"ok": False, "message": str(e)}), 500

    finally:
        if cur: 
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass






from flask import request, jsonify

@app.route('/assignment/<int:aid>/submissions', methods=['GET'])
def get_assignment_submissions(aid):
    """
    GET /assignment/<aid>/submissions
    Returns JSON: { ok: True, submissions: [ ... ] }
    Each submission: { submission_id, assignment_id, student_id, student_name, original_filename, file_url, locked, uploaded_at, grade? }
    """
    conn = None
    cur = None
    try:
        if pool:
            conn = pool.get_connection()
        else:
            conn = mysql.connector.connect(**dbconfig)

        cur = conn.cursor(dictionary=True, buffered=True)

        # تأكد إن الجدول موجود
        cur.execute("SHOW TABLES LIKE 'assignment_submissions'")
        if cur.fetchone() is None:
            return jsonify({"ok": False, "message": "table assignment_submissions not found"}), 500

        # هل يوجد عمود grade في الجدول؟ (لو مش موجود نتجنّب SELECT عليه)
        cur.execute("SHOW COLUMNS FROM assignment_submissions LIKE 'grade'")
        has_grade = cur.fetchone() is not None

        # بناء SELECT ديناميكي
        select_fields = [
            "s.id AS submission_id",
            "s.assignment_id",
            "s.student_id",
            "u.name AS student_name",
            "s.original_filename",
            "s.file_path",
            "s.locked",
            "s.uploaded_at"
        ]
        if has_grade:
            select_fields.append("s.grade")
        sql = "SELECT " + ", ".join(select_fields) + """
            FROM assignment_submissions s
            LEFT JOIN users u ON u.id = s.student_id
            WHERE s.assignment_id = %s
            ORDER BY s.uploaded_at DESC, s.id DESC
        """

        cur.execute(sql, (aid,))
        rows = cur.fetchall()

        submissions = []
        for r in rows:
            fp = r.get('file_path')
            file_url = None
            if fp:

                clean_name = str(fp).replace("uploads/", "")

                file_url = request.url_root.rstrip('/') + "/static/uploads/" + clean_name

            submissions.append({
                "submission_id": r.get('submission_id'),
                "assignment_id": r.get('assignment_id'),
                "student_id": r.get('student_id'),
                "student_name": r.get('student_name') or "",
                "original_filename": r.get('original_filename') or "",
                "file_url": file_url,
                "locked": bool(r.get('locked')),
                "uploaded_at": r.get('uploaded_at'),
                # attach grade only if present in result
                "grade": r.get('grade') if ('grade' in r) else None
            })

        return jsonify({"ok": True, "submissions": submissions}), 200

    except Exception as e:
        app.logger.exception("get_assignment_submissions failed")
        return jsonify({"ok": False, "message": str(e)}), 500

    finally:
        try:
            if cur: cur.close()
        except:
            pass
        try:
            if conn: conn.close()
        except:
            pass





@app.route('/submission/<int:sub_id>/grade', methods=['POST'])
def grade_submission(sub_id):
    data = request.get_json() or {}
    grade = data.get('grade')

    if grade is None:
        return jsonify({"ok": False, "message": "grade required"}), 400

    conn = None
    cur = None
    try:
        if pool:
            conn = pool.get_connection()
        else:
            conn = mysql.connector.connect(**dbconfig)

        cur = conn.cursor()

        sql = "UPDATE assignment_submissions SET grade = %s WHERE id = %s"
        cur.execute(sql, (grade, sub_id))
        conn.commit()

        return jsonify({"ok": True, "updated": cur.rowcount}), 200

    except Exception as e:
        app.logger.exception("grade_submission failed")
        return jsonify({"ok": False, "message": str(e)}), 500

    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass






@app.route('/admin/assignments/<int:aid>/submissions', methods=['GET'])
def list_submissions_for_assignment(aid):
    """
    Instructor view: list all submissions for assignment id = aid
    Returns array of submissions with student info (if you have student table you can join)
    """
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        sql = """
            SELECT s.id AS submission_id, s.assignment_id, s.student_id, s.original_filename, s.file_path, s.locked, s.uploaded_at, s.grade
            FROM assignment_submissions s
            WHERE s.assignment_id = %s
            ORDER BY s.uploaded_at DESC
        """
        cur.execute(sql, (aid,))
        rows = cur.fetchall()
        # optionally join student names by additional queries if needed
        return jsonify({"ok": True, "submissions": rows}), 200
    except Exception as e:
        app.logger.exception("list_submissions_for_assignment failed")
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
        except: pass
        try:
            if conn: conn.close()
        except: pass

@app.route('/assignment/<int:assignment_id>/attach_file', methods=['POST'])
def attach_file_to_assignment(assignment_id):
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "message": "No file provided"}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({"ok": False, "message": "Empty filename"}), 400
        if not allowed_file(f.filename):
            return jsonify({"ok": False, "message": "Invalid file type"}), 400

        filename = secure_filename(f.filename)
        unique = f"assignment_{assignment_id}_{int(time.time())}_{filename}"
        uploads_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, unique)
        f.save(save_path)

        rel_path = f"uploads/{unique}"

        # update assignments table file_path column
        cur = db.cursor()
        cur.execute("UPDATE assignments SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
        db.commit()
        cur.close()

        file_url = url_for('serve_upload', filename=unique, _external=True)
        return jsonify({"ok": True, "file_path": rel_path, "file_url": file_url}), 200

    except Exception as e:
        db.rollback()
        app.logger.exception("attach_file failed")
        return jsonify({"ok": False, "message": str(e)}), 500





@app.route('/course/<int:course_id>/grades', methods=['POST'])
def set_course_grade(course_id):
    """
    POST /course/<course_id>/grades
    Body JSON: { "student_id": 5, "mid_grade": 12.5, "final_grade": 18.0 }
    Accepts either grade or both. Performs upsert into course_grades.
    """
    payload = request.get_json()
    if not payload or "student_id" not in payload:
        return jsonify({"ok": False, "message": "student_id required"}), 400

    student_id = int(payload["student_id"])
    mid = payload.get("mid_grade")
    final = payload.get("final_grade")

    conn = None
    cur = None
    try:
        if pool:
            conn = pool.get_connection()
        else:
            conn = mysql.connector.connect(**dbconfig)
        cur = conn.cursor()

        # use INSERT ... ON DUPLICATE KEY UPDATE for upsert
        sql = """
            INSERT INTO course_grades (course_id, student_id, mid_grade, final_grade)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              mid_grade = VALUES(mid_grade),
              final_grade = VALUES(final_grade),
              updated_at = CURRENT_TIMESTAMP
        """
        cur.execute(sql, (course_id, student_id, mid, final))
        conn.commit()
        return jsonify({"ok": True, "message": "Grades saved"}), 200
    except Exception as e:
        app.logger.exception("set_course_grade failed")
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        try: 
            if cur: cur.close()
        except: pass
        try:
            if conn: conn.close()
        except: pass

# ---------------------------------------------------------------------
# Debug routes list
@app.route('/_routes_debug', methods=['GET'])
def routes_debug():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({"endpoint": rule.endpoint, "rule": str(rule), "methods": sorted(list(rule.methods))})
    return jsonify(routes), 200


# ===== Route: gate_policy =====
# --- gate_policy routes (place after app and db setup) ---

# helper to get a fresh cursor (safer)
def get_cursor_dict():
    try:
        # If using pooling:
        # conn = pool.get_connection() 
        # return conn, conn.cursor(dictionary=True)
        # If using global db:
        db = get_db()
        cur = db.cursor(dictionary=True)
        return db, cur
    except Exception as e:
        print("Error getting cursor:", e)
        raise

@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200





@app.route('/gate_check', methods=['POST'])
def gate_check():
    data = request.get_json()
    student_id = data.get('student_id')
    term = data.get('term', 'term1')

    if not student_id:
        return jsonify({"allowed": False, "reason": "student_id required"}), 400

    db = get_db()
    cur = db.cursor(dictionary=True)

    # اقرأ السياسة الحالية
    cur.execute("SELECT mode FROM gate_policy LIMIT 1")
    policy_row = cur.fetchone()
    mode = policy_row['mode'] if policy_row else 'id_only'

    # 1️⃣ دخول بالـ ID فقط
    if mode == 'id_only':
        cur.execute("SELECT id FROM users WHERE id=%s AND role='Student'", (student_id,))
        return jsonify({"allowed": bool(cur.fetchone()), "policy": mode})

    # 2️⃣ ترم واحد مدفوع
    if mode == 'term1_paid':
        cur.execute("""
            SELECT 1 FROM payments
            WHERE student_id=%s AND term='term1' AND status='paid'
        """, (student_id,))
        return jsonify({"allowed": bool(cur.fetchone()), "policy": mode})

    # 3️⃣ الترمين مدفوعين
    if mode == 'term1_and_term2_paid':
        cur.execute("""
            SELECT COUNT(*) AS c FROM payments
            WHERE student_id=%s AND term IN ('term1','term2') AND status='paid'
        """, (student_id,))
        ok = cur.fetchone()['c'] == 2
        return jsonify({"allowed": ok, "policy": mode})

    return jsonify({"allowed": False, "reason": "unknown policy"}), 400










# جلب بيانات الطالب وبحالة الدفع
@app.route('/student_status/<int:student_id>', methods=['GET'])
def student_status(student_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    # جلب المستخدم
    cur.execute("SELECT id, name, role FROM users WHERE id = %s", (student_id,))
    user = cur.fetchone()
    if not user:
        return jsonify({"message":"Student not found"}), 404

    # تحقق الدفعات
    cur.execute("SELECT term, SUM(amount) as total FROM payments WHERE student_id = %s GROUP BY term", (student_id,))
    pays = {row['term']: row['total'] for row in cur.fetchall()}

    return jsonify({
        "user": user,
        "payments": pays
    }), 200









@app.route('/gate_policy', methods=['GET'])
def get_gate_policy():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT mode FROM gate_policy LIMIT 1")
    row = cur.fetchone()
    cur.close()
    return jsonify({"mode": row['mode'] if row else None}), 200




@app.route('/gate_policy', methods=['POST'])
def set_gate_policy():
    data = request.get_json()
    mode = data.get('mode')
    if not mode:
        return jsonify({"error": "mode required"}), 400

    cur = db.cursor()
    try:
        cur.execute("DELETE FROM gate_policy")
        cur.execute(
            "INSERT INTO gate_policy (id, mode) VALUES (1, %s)",
            (mode,)
        )
        db.commit()
        return jsonify({"ok": True, "mode": mode}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()



@app.route('/test_gate')
def test_gate():
    return "GATE OK"


@app.route('/hello')
def hello():
    return "HELLO FROM CAMPUS"



# تحقق الدخول حسب سياسة البوابة
@app.route("/check_access", methods=["POST"])
def check_access():
    data = request.get_json()
    student_id = data.get("student_id")

    db = get_db()
    cur = db.cursor(dictionary=True)

    # 1️⃣ نجيب السياسة
    cur.execute("SELECT mode FROM gate_policy ORDER BY id DESC LIMIT 1")
    policy = cur.fetchone()
    mode = policy["mode"] if policy else "id_only"

    # 2️⃣ نجيب المستخدم
    cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    user = cur.fetchone()

    if not user:
        return jsonify({
            "access": False,
            "reason": "User not found"
        })

    # 🔥 3️⃣ لو Admin أو Doctor يدخل دايمًا
    if user["role"] in ["admin", "doctor"]:
        return jsonify({
            "access": True,
            "reason": "Role override (Admin/Doctor)"
        })

    # 🔥 4️⃣ لو في Override فردي
    if user["override_access"] is not None:
        return jsonify({
            "access": bool(user["override_access"]),
            "reason": "Manual override applied"
        })

    # 🔥 5️⃣ غير كده نطبق Policy
    if mode == "id_only":
        access = True

    elif mode == "term1_paid":
        access = user["term1_paid"]

    elif mode == "term1_and_term2_paid":
        access = user["term2_paid"]

    elif mode == "any_paid":
        access = user["term1_paid"] or user["term2_paid"]

    else:
        access = False

    return jsonify({
        "access": access,
        "policy_used": mode
    })



@app.route('/student/<int:student_id>/midterm', methods=['GET'])
def get_student_midterm(student_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT
                c.id AS course_id,
                c.course_name,
                cg.mid_grade
            FROM student_courses sc
            JOIN course c ON sc.course_id = c.id
            LEFT JOIN course_grades cg
                ON cg.course_id = c.id
               AND cg.student_id = sc.student_id
            WHERE sc.student_id = %s
            ORDER BY c.course_name
        """, (student_id,))

        data = cur.fetchall()
        cur.close()

        return jsonify({
            "ok": True,
            "midterms": data
        }), 200

    except Exception as e:
        print("❌ Midterm API Error:", e)
        return jsonify({
            "ok": False,
            "message": str(e)
        }), 500




# @app.route('/chatbot/ai', methods=['POST'])
# def chatbot_ai():
#     data = request.get_json()

#     course_id = data.get("course_id")
#     action = data.get("action")
#     source = data.get("source")
#     question = data.get("question")

#     cur = db.cursor(dictionary=True)
#     cur.execute("""
#         SELECT file_path
#         FROM book
#         WHERE course_id=%s AND type=%s
#         ORDER BY uploaded_at DESC
#         LIMIT 1
#     """, (course_id, source))
#     row = cur.fetchone()
#     cur.close()

#     if not row:
#         return jsonify({"reply": "مفيش محتوى متاح"})

#     text = extract_pdf_text(row['file_path'])

#     if action == "ask":
#         return jsonify({"reply": answer_question(question, text)})

#     if action == "summarize":
#         return jsonify({"reply": summarize(text)})

#     return jsonify({"reply": "طلب غير مفهوم"})



@app.route('/chatbot/ai', methods=['POST'])
def chatbot_ai():
    data = request.get_json()

    course_id = data.get("course_id")
    action = data.get("action")        # "ask" or "summarize"
    source = data.get("source")        # "lecture" or "book"
    question = data.get("question")    # required if action = ask

    if not course_id or not action or not source:
        return jsonify({
            "reply": "Missing required parameters."
        }), 400

    # 1️⃣ Get lecture or book PDF from database
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT file_path
        FROM book
        WHERE course_id = %s AND type = %s
        ORDER BY uploaded_at DESC
        LIMIT 1
    """, (course_id, source))

    row = cur.fetchone()
    cur.close()

    if not row:
        return jsonify({
            "reply": "No lecture or book available for this course."
        })

    # 👇👇 حطي السطرين دول هنا
    print("FILE PATH FROM DB:", row['file_path'])

    try:
        text = extract_pdf_text(row['file_path'])
    except Exception:
        return jsonify({
            "reply": "Failed to read the PDF file."
        })


    if not text.strip():
        return jsonify({
            "reply": "The selected file does not contain readable text."
        })

    # 3️⃣ AI Processing
    if action == "ask":
        if not question:
            return jsonify({
                "reply": "Please provide a question."
            })

        answer = answer_question(question, text)
        return jsonify({
            "reply": answer
        })

    if action == "summarize":
        summary = summarize(text)
        return jsonify({
            "reply": summary
        })

    if action == "quiz":

        questions = generate_mcq(text, 5)

        cur = db.cursor()

        # create quiz
        cur.execute("""
            INSERT INTO assignment (course_id,title,type)
            VALUES (%s,%s,'Quiz')
        """,(course_id,"AI Quiz"))

        db.commit()

        quiz_id = cur.lastrowid

        for q in questions:

            cur.execute("""
                INSERT INTO quiz_question
                (assignment_id,q_type,question_text,options,correct_answer)
                VALUES (%s,%s,%s,%s,%s)
            """,(
                quiz_id,
                "MCQ",
                q["question"],
                json.dumps(q["options"]),
                q["correct"]
            ))

        db.commit()

        return jsonify({
            "reply":"عملتلك امتحان 🎓",
            "quiz_id":quiz_id,
            "questions":questions
        })    

    return jsonify({
        "reply": "Invalid action type."
    })



# from flask import render_template

# @app.route('/chatbot')
# def chatbot_page():
#     return send_from_directory('web', 'chatbot.html')

#----------------------------AI2------------------------

def detect_intent(message):
    msg = message.lower()

    if any(w in msg for w in ["جدول", "schedule"]):
        return "schedule"
    if any(w in msg for w in ["غياب", "attendance"]):
        return "attendance"
    if any(w in msg for w in ["درجات", "grade"]):
        return "grades"
    if any(w in msg for w in ["بوابة", "gate", "ادخل"]):
        return "gate"
    if any(w in msg for w in ["كورسات", "مواد"]):
        return "courses"
    return "unknown"





@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    message = data.get("message", "")
    student_id = data.get("student_id")

    intent = detect_intent(message)

    # 1️⃣ الجدول
    if intent == "schedule":
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT c.course_name, s.day, s.start_time, s.end_time, s.room
            FROM schedule s
            JOIN course c ON s.course_id = c.id
            JOIN student_courses sc ON sc.course_id = c.id
            WHERE sc.student_id = %s
        """, (student_id,))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return jsonify({"reply": "📅 معندكش جدول مسجل دلوقتي"})

        reply = "📅 جدولك:\n"
        for r in rows:
            reply += f"- {r['course_name']} | {r['day']} {r['start_time']}-{r['end_time']} | {r['room']}\n"

        return jsonify({"reply": reply})

    # 2️⃣ الغياب
    elif intent == "attendance":
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT 
                SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN status='absent' THEN 1 ELSE 0 END) AS absent
            FROM attendance
            WHERE student_id = %s
        """, (student_id,))
        row = cur.fetchone()
        cur.close()

        return jsonify({
            "reply": f"📊 حضورك: {row['present']} | غيابك: {row['absent']}"
        })

    # 3️⃣ الدرجات
    elif intent == "grades":
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT c.course_name, g.total_grade
            FROM grades g
            JOIN course c ON g.course_id = c.id
            WHERE g.student_id = %s
            GROUP BY c.course_name
        """, (student_id,))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return jsonify({"reply": "📉 مفيش درجات متسجلة لسه"})

        reply = "📚 درجاتك:\n"
        for r in rows:
            reply += f"- {r['course_name']}: {r['total_grade']}\n"

        return jsonify({"reply": reply})

    # 4️⃣ البوابة
    elif intent == "gate":
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT mode FROM gate_policy LIMIT 1")
        policy = cur.fetchone()
        cur.close()

        return jsonify({
            "reply": f"🚪 سياسة الدخول الحالية: {policy['mode']}"
        })

    # 5️⃣ الكورسات
    elif intent == "courses":
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT c.course_name
            FROM student_courses sc
            JOIN course c ON sc.course_id = c.id
            WHERE sc.student_id = %s
        """, (student_id,))
        rows = cur.fetchall()
        cur.close()

        reply = "📘 كورساتك:\n"
        for r in rows:
            reply += f"- {r['course_name']}\n"

        return jsonify({"reply": reply})

    # ❌ غير مفهوم
    return jsonify({"reply": "🤖 مش فاهم سؤالك، جرب تسأل عن (الجدول – الغياب – الدرجات – البوابة)"})




# ================= AI ROUTER =================
# def detect_intent(message):
#     msg = message.lower()

#     intents = {
#         "attendance": ["حضور", "غياب", "غبت", "attendance"],
#         "grades": ["درجات", "gpa", "نجحت", "سقطت"],
#         "advisor": ["مواد", "اسجل", "اتخرج", "ترم", "level"],
#         "schedule": ["جدول", "محاضرة", "ميعاد"],
#         "summary": ["لخص", "ملخص", "summarize"],
#           "quiz": ["اختبرني", "quiz", "امتحان", "test"]
#     }

#     for intent, keywords in intents.items():
#         for k in keywords:
#             if k in msg:
#                 return intent

#     return "general"



def attendance_ai(student_id):
    cur = db.cursor(dictionary=True, buffered=True)

    cur.execute("""
        SELECT 
            SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN status='absent' THEN 1 ELSE 0 END) AS absent
        FROM attendance
        WHERE student_id = %s
    """, (student_id,))

    row = cur.fetchone()
    cur.close()

    present = row['present'] or 0
    absent = row['absent'] or 0

    return {
        "reply": f"""
📊 **الحضور والغياب**
✅ حضور: {present}
❌ غياب: {absent}

⚠️ حاول تحافظ على الحضور
"""
    }



def academic_advisor_ai(student_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT level FROM users WHERE id=%s AND role='Student'", 
        (student_id,)
    )
    student = cur.fetchone()

    if not student:
        cur.close()
        return {"reply": "❌ الطالب غير موجود"}

    level = student['level']

    cur.execute("""
        SELECT c.course_name
        FROM student_courses sc
        JOIN course c ON sc.course_id = c.id
        WHERE sc.student_id = %s
    """, (student_id,))
    courses = cur.fetchall()
    cur.close()

    reply = f"""
🎓 **المرشد الأكاديمي**
📚 Level: {level}
📖 عدد المواد: {len(courses)}

📌 موادك:
"""

    for c in courses:
        reply += f"- {c['course_name']}\n"

    if len(courses) >= 5:
        reply += "\n⚠️ حاول تقلل مواد الترم الجاي"
    else:
        reply += "\n✅ عدد المواد مناسب"

    return {"reply": reply}




def grades_ai(student_id):
    try:
        cur = db.cursor(dictionary=True, buffered=True)

        cur.execute("""
            SELECT 
                a.title AS title,
                s.grade,
                a.total_mark,
                c.course_name
            FROM assignment_submissions s
            JOIN assignment a ON s.assignment_id = a.id
            JOIN course c ON a.course_id = c.id
            WHERE s.student_id = %s
        """, (student_id,))

        rows = cur.fetchall()
        cur.close()

        print("DEBUG ROWS:", rows)  

        if not rows:
            return "❌ مفيش درجات لحد دلوقتي"

        msg = "📊 درجاتك:\n\n"

        for r in rows:
            course = r.get("course_name", "Course")
            title = r.get("title", "Assignment")
            grade = r.get("grade")
            total = r.get("total_mark", 0)

            if grade is None:
                grade = "لم يتم التصحيح"

            msg += f"{course} | {title} → {grade}/{total}\n"

        return msg

    except Exception as e:
        print("ERROR:", e)
        return "❌ حصل خطأ في عرض الدرجات"
    

def schedule_ai(student_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            c.course_name,
            s.day,
            s.start_time,
            s.end_time,
            s.room
        FROM schedule s
        JOIN course c ON s.course_id = c.id
        JOIN student_courses sc ON sc.course_id = c.id
        WHERE sc.student_id = %s
        ORDER BY 
            FIELD(s.day, 'Saturday','Sunday','Monday','Tuesday','Wednesday','Thursday','Friday'),
            s.start_time
    """, (student_id,))

    rows = cur.fetchall()
    cur.close()

    if not rows:
        return {
            "reply": "📅 معندكش جدول مسجل دلوقتي"
        }

    reply = "📅 **جدولك الدراسي:**\n\n"

    for r in rows:
        reply += (
            f"📘 {r['course_name']}\n"
            f"🗓 {r['day']} | ⏰ {r['start_time']} - {r['end_time']}\n"
            f"🏫 {r['room']}\n\n"
        )

    return {
        "reply": reply
    }




import re
from deep_translator import GoogleTranslator


def summarize_lecture_ai(message):
    # نشيل كلمات الطلب
    text = re.sub(r"(لخص|ملخص|summarize|تلخيص)", "", message, flags=re.IGNORECASE).strip()

    if len(text) < 40:
        return {
            "reply": "❗ Please provide enough text so I can summarize it."
        }

    
    sentences = re.split(r'(?<=[.!؟])\s+', text)

    
    if len(sentences) <= 2:
        selected = sentences
    else:
        selected = [
            sentences[0],
            sentences[len(sentences)//2],
            sentences[-1]
        ]

    arabic_summary = []
    english_summary = []

    for s in selected:
        
        ar = GoogleTranslator(source='auto', target='ar').translate(s)
        arabic_summary.append(ar)

        
        en = GoogleTranslator(source='auto', target='en').translate(s)
        english_summary.append(en)

    ar_text = "\n- ".join(arabic_summary)
    en_text = "\n- ".join(english_summary)

    reply = f"""📚 **ملخص النص | Text Summary**

🇦🇪 **الملخص بالعربي:**
- {ar_text}

🇬🇧 **Summary in English:**
- {en_text}

✅ **Conclusion:**
This summary was generated using extractive summarization and automatic translation.
"""

    return {
        "reply": reply
    }


last_uploaded_text = {}

def generate_quiz_ai(student_id):

    text = last_uploaded_text.get(student_id)

    if not text:
        return {"reply":"❌ ارفع المحاضرة أولاً"}

    questions = generate_mcq(text,5)
    print("QUIZ DATA:", questions)
    return {
        "reply":"🎓 عملتلك امتحان",
        "questions":questions
    }
    



# ================= AI INTENT DETECTION =================
def detect_intent(message):

    msg = message.lower().strip()

    if "غياب" in msg or "attendance" in msg:
        return "attendance"

    if "درجات" in msg or "grades" in msg:
        return "grades"

    if "جدول" in msg or "schedule" in msg:
        return "schedule"

    if "لخص" in msg or "summary" in msg:
        return "summary"
    
    if "مواد" in msg or "كورسات" in msg:
        return "advisor"

    # 👇 الجديد للامتحان
    if "اختبرني" in msg or "quiz" in msg or "امتحان" in msg:
        return "quiz"

    return "unknown"



@app.route('/upload_lecture_ai', methods=['POST'])
def upload_lecture_ai():

    global last_uploaded_text

    if 'file' not in request.files:
        return jsonify({"reply":"❌ لم يتم رفع ملف"})

    file = request.files['file']
    filename = secure_filename(file.filename)

    if filename.lower().endswith(".pdf.pdf"):
        filename = filename[:-4]

    path = os.path.join("static/uploads", filename)

    os.makedirs("static/uploads", exist_ok=True)

    file.save(path)

    text = extract_pdf_text(path)

    student_id = request.form.get("student_id")

    last_uploaded_text[student_id] = text   

    return jsonify({
        "reply":"📚 تم رفع المحاضرة بنجاح، يمكنك الآن كتابة (اختبرني) أو (لخص)"
    })




@app.route('/ai/chat', methods=['POST'])
def ai_chat():

    data = request.get_json()
    student_id = data.get('student_id')
    message = data.get('message')

    if not student_id or not message:
        return jsonify({"reply": "❌ بيانات ناقصة"}), 400

    intent = detect_intent(message)

    if intent == "attendance":
        result = attendance_ai(student_id)

    elif intent == "advisor":
        result = academic_advisor_ai(student_id)

    elif intent == "grades":
        result = grades_ai(student_id)

    elif intent == "schedule":
        result = schedule_ai(student_id)

    elif intent == "summary":
        lecture = last_uploaded_text.get(student_id)
        result = summarize_lecture_ai(lecture)

    elif intent == "quiz":
        quiz = generate_quiz_ai(student_id)
        return jsonify(quiz)   

    else:
        result = "🤖 اسألني عن الحضور، الدرجات، المواد، الجدول أو اختبرني"

    return jsonify({
        "reply": result
    })





@app.route('/ai_generate_quiz', methods=['POST'])
def ai_generate_quiz():

    data = request.get_json()

    text = data.get("text")
    course_id = data.get("course_id")
    title = data.get("title", "AI Generated Quiz")

    cur = db.cursor()

    # create quiz
    cur.execute("""
        INSERT INTO assignment (course_id, title, type)
        VALUES (%s,%s,'Quiz')
    """, (course_id, title))

    db.commit()

    quiz_id = cur.lastrowid

    # generate questions
    questions = generate_mcq(text, 5)

    for q in questions:

        cur.execute("""
            INSERT INTO quiz_question
            (assignment_id,q_type,question_text,options,correct_answer)
            VALUES (%s,%s,%s,%s,%s)
        """,(
            quiz_id,
            "MCQ",
            q["question"],
            json.dumps(q["options"]),
            q["correct"]
        ))

    db.commit()

    return jsonify({
        "message":"Quiz created",
        "quiz_id":quiz_id,
        "questions":questions
    })









##################################camera##############################

# @app.route('/ai/behavior_log', methods=['POST'])
# def ai_behavior_log():
#     try:
#         data = request.get_json()

#         student_id = data.get('student_id')
#         course_id = data.get('course_id')
#         behavior = data.get('behavior')
#         confidence = data.get('confidence', 1.0)

#         if not all([student_id, course_id, behavior]):
#             return jsonify({"message": "Missing required fields"}), 400

#         cur = db.cursor()
#         cur.execute("""
#             INSERT INTO behavior_logs
#             (student_id, course_id, behavior, confidence, created_at)
#             VALUES (%s, %s, %s, %s, NOW())
#         """, (student_id, course_id, behavior, confidence))

#         db.commit()
#         cur.close()

#         return jsonify({"status": "ok"}), 200

#     except Exception as e:
#         db.rollback()
#         print("❌ AI behavior log error:", e)
#         return jsonify({"status": "error", "message": str(e)}), 500




@app.route("/ai/behavior_log", methods=["POST"])
def ai_behavior_log():
    try:
        data = request.get_json()
        print("📥 Received from AI:", data)

        student_id = data.get("student_id")
        course_id  = data.get("course_id")
        behavior   = data.get("behavior")
        confidence = data.get("confidence", 1.0)
        image_path = data.get("image_path")

        cur = db.cursor()
        cur.execute("""
            INSERT INTO behavior_logs
            (student_id, course_id, behavior, confidence, image_path, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (student_id, course_id, behavior, confidence, image_path))

        db.commit()
        cur.close()

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        db.rollback()
        print("❌ AI behavior log error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500




# @app.route("/cheating_alerts")
# def cheating_alerts():
#     try:
#         cur = db.cursor(dictionary=True)

#         cur.execute("""
#             SELECT student_id, behavior, confidence, image_path, created_at
#             FROM behavior_logs
#             ORDER BY created_at DESC
#         """)

#         rows = cur.fetchall()
#         cur.close()

#         data = []
#         for r in rows:
#             data.append({
#                 "student_id": r["student_id"],
#                 "behavior": r["behavior"],
#                 "confidence": r["confidence"],
#                 "image": r["image_path"],
#                 "time": r["created_at"]
#             })

#         return jsonify(data)

#     except Exception as e:
#         print("❌ cheating_alerts error:", e)
#         return jsonify([])

@app.route('/cheating_alerts')
def cheating_alerts():

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT student_id,behavior,confidence,created_at
        FROM cheating_logs
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    return jsonify(rows)

#################Gate####################3
# ######################################3

@app.route('/api/check_access', methods=['POST'])
def api_check_access():

    print("CHECK ACCESS API CALLED")

    data = request.get_json()
    uid = data.get("uid")

    if not uid:
        return jsonify({
            "access": 0,
            "name": "Unknown",
            "role": ""
        }), 400

    cur = db.cursor(dictionary=True, buffered=True)

    cur.execute("""
        SELECT *
        FROM users
        WHERE rfid_uid=%s
    """, (uid,))

    user = cur.fetchone()

    print("USER FOUND =", user)

    access = 0
    name = "Access Denied"
    role = ""

    if user and user["gate_access"] == 1:
        access = 1
        name = user["name"]
        role = user["role"]

    # تسجيل اللوج
    cur2 = db.cursor()

    cur2.execute("""
        INSERT INTO gate_logs
        (name, uid, status, user_name)
        VALUES (%s,%s,%s,%s)
    """, (
        name,
        uid,
        "Allowed" if access else "Denied",
        name
    ))

    db.commit()

    cur2.close()
    cur.close()

    return jsonify({
        "access": access,
        "name": name,
        "role": role
    })



@app.route("/registration_status")
def registration_status():

    global current_registration
    global registration_mode

    return jsonify({
        "waiting":
        current_registration is not None,

        "registration_mode":
        registration_mode
    })



@app.route("/delete_card", methods=["POST"])
def delete_card():

    data = request.get_json()
    uid = data.get("uid")

    print("DELETE UID =", uid)

    cur = db.cursor()

    cur.execute("""
        UPDATE users
        SET rfid_uid=NULL
        WHERE rfid_uid=%s
    """, (uid,))

    db.commit()

    cur.close()

    return jsonify({
        "success": True
    })


# @app.route("/check_rfid", methods=["POST"])
# def check_rfid():
#     data = request.get_json()
#     uid = data.get("uid").upper()

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     # 1️⃣ نجيب سياسة البوابة
#     cur.execute("SELECT mode FROM gate_policy ORDER BY id DESC LIMIT 1")
#     policy = cur.fetchone()
#     mode = policy["mode"] if policy else "id_only"

#     # 2️⃣ نجيب المستخدم
#     cur.execute("SELECT * FROM students WHERE rfid_uid = %s", (uid,))
#     user = cur.fetchone()

#     access = False
#     student_id = None

#     if user:
#         student_id = user["student_id"]


#         if user["override_access"] is not None:
#             access = bool(user["override_access"])

#         # 🔥 لو دكتور أو أدمن يدخل دايمًا
#         elif user["role"] in ["doctor", "admin"]:
#             access = True

#         # 👨‍🎓 لو طالب يخضع للسياسة
#         else:
#             if mode == "id_only":
#                 access = True

#             elif mode == "term1_paid":
#                 if user["term1_paid"]:
#                     access = True

#             elif mode == "term1_and_term2_paid":
#                 if user["term2_paid"]:
#                     access = True

#             elif mode == "any_paid":
#                 if user["term1_paid"] or user["term2_paid"]:
#                     access = True

#     # تسجيل في اللوجز
#     cur.execute(
#         "INSERT INTO gate_logs (student_id, rfid_uid, access) VALUES (%s, %s, %s)",
#         (student_id, uid, access)
#     )

#     db.commit()

#     return jsonify({"access": access})



@app.route("/update_gate_access", methods=["POST"])
def update_gate_access():

    data = request.get_json()

    uid = data.get("uid")
    access = data.get("access")

    print("UID =", uid)
    print("ACCESS =", access)

    cur = db.cursor()
    cur.execute(
    """
    UPDATE users
    SET gate_access=%s
    WHERE rfid_uid=%s
    """,
    (access, uid)
    )

    db.commit()

    cur.execute(
    "SELECT gate_access FROM users WHERE rfid_uid=%s",
    (uid,)
    )

    print("AFTER UPDATE =", cur.fetchone())

    cur.close()

    return jsonify({
        "success": True
    })




@app.route("/get_cards")
def get_cards():

    cur = db.cursor(dictionary=True)

    cur.execute("""
            SELECT
            id,
            name,
            role,
            rfid_uid,
            gate_access
            FROM users
            WHERE rfid_uid IS NOT NULL
            """)

    cards = cur.fetchall()

    cur.close()

    return jsonify(cards)    




@app.route("/register_rfid", methods=["POST"])
def register_rfid():
    data = request.get_json()

    student_id = data.get("student_id")
    uid = data.get("uid").upper()

    cur = db.cursor()

    cur.execute(
        "UPDATE students SET rfid_uid = %s WHERE student_id = %s",
        (uid, student_id)
    )

    db.commit()

    return jsonify({"success": True})



current_registration_id = None


@app.route("/start_registration", methods=["POST"])
def start_registration():

    global current_registration
    global registration_mode

    data = request.get_json()

    user_id = data.get("user_id")

    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cur.fetchone()

    if not user:
        return jsonify({
            "status": "error",
            "message": "User ID not found"
        })

    current_registration = {
        "user_id": user_id

    }
    registration_mode = True
    print("WAITING FOR USER:", user_id)
    return jsonify({
        "status": "waiting",
        "name": user["name"]
    })



    

@app.route("/scan_rfid", methods=["POST"])
def scan_rfid():
    global current_registration

    data = request.get_json()
    uid = data.get("uid").upper()

    db = get_db()
    cur = db.cursor(dictionary=True)

    if current_registration:

        student_id = current_registration["student_id"]
        name = current_registration["name"]

        # هل الطالب موجود؟
        cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cur.fetchone()

        if student:
            cur.execute(
                "UPDATE students SET rfid_uid = %s WHERE student_id = %s",
                (uid, student_id)
            )
        else:
            cur.execute(
                "INSERT INTO students (student_id, name, rfid_uid) VALUES (%s, %s, %s)",
                (student_id, name, uid)
            )

        db.commit()
        current_registration = {}

        return jsonify({"access": True})

    return jsonify({"access": False})

 


@app.route("/get_logs")
def get_logs():

    cur = db.cursor(dictionary=True, buffered=True)

    cur.execute("""
            SELECT
                users.name,
                users.role,
                gate_logs.uid,
                gate_logs.status,
                gate_logs.time
            FROM gate_logs
            LEFT JOIN users
            ON TRIM(gate_logs.uid) = TRIM(users.rfid_uid)
            ORDER BY gate_logs.time DESC
            LIMIT 100
            """)

    logs = cur.fetchall()

    print(logs[:20])
    print("TOTAL LOGS =", len(logs))

 
    return jsonify(logs)


# gate_logs.uid = users.rfid_uid  




@app.route("/test")
def test():
    return "Working"




@app.route('/log_cheating', methods=['POST'])
def log_cheating():

    data = request.get_json()

    student_id = data.get("student_id")
    confidence = data.get("confidence")
    image = data.get("image")

    cur = db.cursor()

    cur.execute("""
        INSERT INTO cheating_logs
        (student_id, course_id, behavior, confidence, image, created_at)
        VALUES (%s,%s,'cheating',%s,%s,NOW())
    """,(student_id,1,confidence,image))

    db.commit()

    return {"status":"ok"}




@app.route('/snapshot/<filename>')
def snapshot(filename):
    return send_from_directory("camera/snapshots", filename)


###################Chat########################


@app.route('/start_conversation', methods=['POST'])
def start_conversation():
    data = request.get_json()
    student_id = data.get('student_id')
    instructor_id = data.get('instructor_id')

    cur = db.cursor(dictionary=True)

    # تأكد إنها مش موجودة
    cur.execute("""
        SELECT id FROM conversations
        WHERE student_id=%s AND instructor_id=%s
    """, (student_id, instructor_id))
    existing = cur.fetchone()

    if existing:
        return jsonify({"conversation_id": existing['id']}), 200

    cur.execute("""
        INSERT INTO conversations (student_id, instructor_id)
        VALUES (%s, %s)
    """, (student_id, instructor_id))
    db.commit()

    return jsonify({"conversation_id": cur.lastrowid}), 200


@app.route('/conversation/<int:id>')
def get_messages(id):

    db = get_db()  # 🔥 افتحي connection جديد
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT * FROM messages
        WHERE conversation_id = %s
    """, (id,))

    messages = cur.fetchall()  # 🔥 مهم

    cur.close()   # 🔥 اقفلي cursor
    db.close()    # 🔥 اقفلي connection

    return jsonify(messages)           


def get_db():
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_POR
    )

@app.route('/student/<int:student_id>/instructors')
def get_student_instructors(student_id):

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT DISTINCT 
            u.id,
            u.name,
            u.image
        FROM student_courses sc
        JOIN course c ON sc.course_id = c.id
        JOIN users u ON c.instructor_id = u.id
        WHERE sc.student_id = %s
    """, (student_id,))

    result = cur.fetchall()

    cur.close()
    db.close()

    return jsonify(result)




@app.route('/instructor/<int:instructor_id>/students')
def get_instructor_students(instructor_id):

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT DISTINCT 
            u.id,
            u.name,
            u.image
        FROM course c
        JOIN student_courses sc ON c.id = sc.course_id
        JOIN users u ON sc.student_id = u.id
        WHERE c.instructor_id = %s
    """, (instructor_id,))

    result = cur.fetchall()

    cur.close()
    db.close()

    return jsonify(result)




@app.route('/conversation/<int:conversation_id>/mark_read', methods=['PUT'])
def mark_as_read(conversation_id):
    cur = db.cursor()
    cur.execute("""
        UPDATE messages
        SET is_read = TRUE
        WHERE conversation_id = %s
    """, (conversation_id,))
    db.commit()
    return jsonify({"status": "updated"})



@app.route('/student/<int:student_id>/unread_count')
def student_unread_count(student_id):

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT COUNT(*) AS unread
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.student_id = %s
        AND m.is_read = FALSE
        AND m.sender_id != %s
    """, (student_id, student_id))

    result = cur.fetchone()   # 👈 مهم جدًا

    cur.close()               # 👈 مهم جدًا
    db.close()                # 👈 مهم جدًا

    return jsonify({"unread": result['unread']})




# @app.route('/student/<int:student_id>/unread_count')
# def student_unread_count(student_id):
#     cur = db.cursor()

#     cur.execute("""
#         SELECT COUNT(*)
#         FROM messages m
#         JOIN conversations c ON m.conversation_id = c.id
#         WHERE c.student_id = %s
#         AND m.is_read = FALSE
#         AND m.sender_id != %s
#     """, (student_id, student_id))

#     count = cur.fetchone()[0]
#     return jsonify({"unread": count})



@app.route('/instructor/<int:instructor_id>/unread_by_conversation')
def unread_by_conversation(instructor_id):
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT c.id AS conversation_id,
               COUNT(m.id) AS unread
        FROM conversations c
        LEFT JOIN messages m 
            ON c.id = m.conversation_id
            AND m.is_read = FALSE
            AND m.sender_id != %s
        WHERE c.instructor_id = %s
        GROUP BY c.id
    """, (instructor_id, instructor_id))

    return jsonify(cur.fetchall())



@app.route('/instructor/<int:instructor_id>/conversations')
def get_instructor_conversations(instructor_id):

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT c.id AS conversation_id,
               u.id,
               u.name,
               u.image
        FROM conversations c
        JOIN users u ON c.student_id = u.id
        WHERE c.instructor_id = %s
    """, (instructor_id,))

    result = cur.fetchall()

    cur.close()
    db.close()

    return jsonify(result)




@app.route('/student/<int:student_id>/unread_by_conversation')
def student_unread_by_conversation(student_id):
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT c.id AS conversation_id,
               COUNT(m.id) AS unread
        FROM conversations c
        LEFT JOIN messages m 
            ON c.id = m.conversation_id
            AND m.is_read = FALSE
            AND m.sender_id != %s
        WHERE c.student_id = %s
        GROUP BY c.id
    """, (student_id, student_id))

    return jsonify(cur.fetchall())


@app.route('/upload_chat_file', methods=['POST'])
def upload_chat_file():

    file = request.files.get('file')

    if not file:
        return jsonify({"error": "No file"}), 400

    filename = secure_filename(file.filename)

    save_path = os.path.join("static/uploads", filename)
    file.save(save_path)

    return jsonify({
        "file_url": filename
    })


@socketio.on("send_message")
def handle_send_message(data):

    import mysql.connector

    db = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_POR
    )

    cur = db.cursor()

    conversation_id = data.get("conversation_id")
    sender_id = data.get("sender_id")
    message = data.get("message")
    file_url = data.get("file_url")

    cur.execute("""
        INSERT INTO messages
        (conversation_id, sender_id, message, file_path, is_read)
        VALUES (%s, %s, %s, %s, FALSE)
    """, (conversation_id, sender_id, message, file_url))

    db.commit()

    cur.close()
    db.close()

    socketio.emit("receive_message", {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "message": message,
        "file_url": file_url
    }, room=str(conversation_id))



@socketio.on("join")
def on_join(data):
    conversation_id = str(data.get("conversation_id"))
    join_room(conversation_id)      



@app.route('/instructor/<int:instructor_id>/unread_count')
def unread_count(instructor_id):

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT COUNT(*) AS unread
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.instructor_id = %s
        AND m.is_read = FALSE
        AND m.sender_id != %s
    """, (instructor_id, instructor_id))

    result = cur.fetchone()

    cur.close()
    db.close()

    return jsonify({"unread": result['unread']})


# @app.route('/start_conversation', methods=['POST'])
# def start_conversation():
#     data = request.get_json()
#     student_id = data.get('student_id')
#     instructor_id = data.get('instructor_id')

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     # تأكد إنها مش موجودة
#     cur.execute("""
#         SELECT id FROM conversations
#         WHERE student_id=%s AND instructor_id=%s
#     """, (student_id, instructor_id))
#     existing = cur.fetchone()

#     if existing:
#         return jsonify({"conversation_id": existing['id']}), 200

#     cur.execute("""
#         INSERT INTO conversations (student_id, instructor_id)
#         VALUES (%s, %s)
#     """, (student_id, instructor_id))
#     db.commit()

#     return jsonify({"conversation_id": cur.lastrowid}), 200


# @app.route("/conversation/<int:conversation_id>/mark_read", methods=["PUT"])
# def mark_as_read_chat(conversation_id):
#     db = get_db()
#     cur = db.cursor()

#     cur.execute("""
#         SELECT * FROM messages
#         WHERE conversation_id = %s
#     """, (conversation_id,))

#     messages = cur.fetchall()

#     cur.close()
#     db.close()

#     return jsonify(messages)        


# def get_db():
#     import mysql.connector
#     return mysql.connector.connect(
        # host=DB_HOST,
        # user=DB_USER,
        # password=DB_PASSWORD,
        # database=DB_NAME,
        # port=DB_PORT
#     )

# @app.route('/student/<int:student_id>/instructors')
# def get_student_instructors(student_id):

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT DISTINCT 
#             u.id,
#             u.name,
#             u.image
#         FROM student_courses sc
#         JOIN course c ON sc.course_id = c.id
#         JOIN users u ON c.instructor_id = u.id
#         WHERE sc.student_id = %s
#     """, (student_id,))

#     result = cur.fetchall()

#     cur.close()
#     db.close()

#     return jsonify(result)




# @app.route('/instructor/<int:instructor_id>/students')
# def get_instructor_students(instructor_id):

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT DISTINCT 
#             u.id,
#             u.name,
#             u.image
#         FROM course c
#         JOIN student_courses sc ON c.id = sc.course_id
#         JOIN users u ON sc.student_id = u.id
#         WHERE c.instructor_id = %s
#     """, (instructor_id,))

#     result = cur.fetchall()

#     cur.close()
#     db.close()

#     return jsonify(result)




# @app.route('/conversation/<int:conversation_id>/mark_read', methods=['PUT'])
# def mark_as_read(conversation_id):
#     cur = db.cursor()
#     cur.execute("""
#         UPDATE messages
#         SET is_read = TRUE
#         WHERE conversation_id = %s
#     """, (conversation_id,))
#     db.commit()
#     return jsonify({"status": "updated"})



# @app.route('/student/<int:student_id>/unread_count')
# def student_unread_count(student_id):

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT COUNT(*) AS unread
#         FROM messages m
#         JOIN conversations c ON m.conversation_id = c.id
#         WHERE c.student_id = %s
#         AND m.is_read = FALSE
#         AND m.sender_id != %s
#     """, (student_id, student_id))

#     result = cur.fetchone()   # 👈 مهم جدًا

#     cur.close()               # 👈 مهم جدًا
#     db.close()                # 👈 مهم جدًا

#     return jsonify({"unread": result['unread']})




# @app.route('/instructor/<int:instructor_id>/unread_by_conversation')
# def unread_by_conversation(instructor_id):
#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT c.id AS conversation_id,
#                COUNT(m.id) AS unread
#         FROM conversations c
#         LEFT JOIN messages m 
#             ON c.id = m.conversation_id
#             AND m.is_read = FALSE
#             AND m.sender_id != %s
#         WHERE c.instructor_id = %s
#         GROUP BY c.id
#     """, (instructor_id, instructor_id))

#     return jsonify(cur.fetchall())



# @app.route('/instructor/<int:instructor_id>/conversations')
# def get_instructor_conversations(instructor_id):

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT c.id AS conversation_id,
#                u.id,
#                u.name,
#                u.image
#         FROM conversations c
#         JOIN users u ON c.student_id = u.id
#         WHERE c.instructor_id = %s
#     """, (instructor_id,))

#     result = cur.fetchall()

#     cur.close()
#     db.close()

#     return jsonify(result)




# @app.route("/conversation/<int:conversation_id>", methods=["GET"])
# def get_messages(conversation_id):

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT *
#         FROM messages
#         WHERE conversation_id=%s
#         ORDER BY sent_at
#     """, (conversation_id,))

#     messages = cur.fetchall()

#     cur.close()
#     db.close()

#     return jsonify(messages)


    

# @app.route('/student/<int:student_id>/unread_by_conversation')
# def student_unread_by_conversation(student_id):
#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT c.id AS conversation_id,
#                COUNT(m.id) AS unread
#         FROM conversations c
#         LEFT JOIN messages m 
#             ON c.id = m.conversation_id
#             AND m.is_read = FALSE
#             AND m.sender_id != %s
#         WHERE c.student_id = %s
#         GROUP BY c.id
#     """, (student_id, student_id))

#     return jsonify(cur.fetchall())


# @app.route('/upload_chat_file', methods=['POST'])
# def upload_chat_file():

#     file = request.files.get('file')

#     if not file:
#         return jsonify({"error": "No file"}), 400

#     filename = secure_filename(file.filename)

#     save_path = os.path.join("static/uploads", filename)
#     file.save(save_path)

#     return jsonify({
#         "file_url": filename
#     })


# @socketio.on("send_message")
# def handle_send_message(data):

#     import mysql.connector

#     db = mysql.connector.connect(
#         host=DB_HOST,
#         user=DB_USER,
#         password=DB_PASSWORD,
#         database=DB_NAME,
#         port=DB_PORT
#     )

#     cur = db.cursor()

#     conversation_id = data.get("conversation_id")
#     sender_id = data.get("sender_id")
#     message = data.get("message")
#     file_url = data.get("file_url")

#     cur.execute("""
#         INSERT INTO messages
#         (conversation_id, sender_id, message, file_path, is_read)
#         VALUES (%s, %s, %s, %s, FALSE)
#     """, (conversation_id, sender_id, message, file_url))

#     db.commit()

#     cur.close()
#     db.close()

#     socketio.emit("receive_message", {
#         "conversation_id": conversation_id,
#         "sender_id": sender_id,
#         "message": message,
#         "file_url": file_url
#     }, room=str(conversation_id))



# @socketio.on("join")
# def on_join(data):
#     conversation_id = str(data.get("conversation_id"))
#     print("JOIN ROOM:", conversation_id)
#     join_room(conversation_id)  



# @app.route('/instructor/<int:instructor_id>/unread_count')
# def unread_count(instructor_id):

#     db = get_db()
#     cur = db.cursor(dictionary=True)

#     cur.execute("""
#         SELECT COUNT(*) AS unread
#         FROM messages m
#         JOIN conversations c ON m.conversation_id = c.id
#         WHERE c.instructor_id = %s
#         AND m.is_read = FALSE
#         AND m.sender_id != %s
#     """, (instructor_id, instructor_id))

#     result = cur.fetchone()

#     cur.close()
#     db.close()

#     return jsonify({"unread": result['unread']})


#######Robot#################
@app.route('/robot/order', methods=['POST'])
def robot_order():
    data = request.get_json()

    lat = data.get("lat")
    lon = data.get("lon")
    item = data.get("item")

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO robot_orders (lat, lon, item, status)
        VALUES (%s,%s,%s,'waiting')
    """,(lat,lon,item))

    db.commit()

    return jsonify({"message":"order received"})
    



@app.route('/robot/get_order')
def get_order():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT * FROM robot_orders
    WHERE status='waiting'
    ORDER BY id DESC
    """)

    orders = cursor.fetchall()

    return jsonify(orders)



@app.route('/robot/done/<int:id>', methods=['POST'])
def robot_done(id):

    cursor = db.cursor()

    cursor.execute("""
        UPDATE robot_orders
        SET status='done'
        WHERE id=%s
    """,(id,))

    db.commit()

    return jsonify({"message":"done"})



@app.route('/robot/get_my_order')
def get_my_order():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT * FROM robot_orders
    ORDER BY id DESC
    LIMIT 1
    """)

    order = cursor.fetchone()

    return jsonify(order)





@app.route('/robot/close_box/<int:id>', methods=['POST'])
def close_box(id):

    cursor=db.cursor()

    cursor.execute("""
    UPDATE robot_orders
    SET box_status='closed',status='delivering'
    WHERE id=%s
    """,(id,))

    db.commit()

    return jsonify({"message":"box closed"})






@app.route('/robot/open_box/<int:id>', methods=['POST'])
def open_box(id):

    cursor=db.cursor()

    cursor.execute("""
    UPDATE robot_orders
    SET box_status='open',status='arrived'
    WHERE id=%s
    """,(id,))

    db.commit()

    return jsonify({"message":"box opened"})


####################################
from flask import render_template

@app.route("/")
def home():
    return render_template("login.html")



@app.route("/signup")
def signup_page():
    return render_template("signup.html")


@app.route("/addUser")
def add_user_page():
    return render_template("addUser.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/admin_schedule")
def admin_schedule_page():
    return render_template("admin_schedule.html")


@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")



# @app.route('/video_feed')
# def video_feed():
#     return Response(
#         generate_frames(),
#         mimetype='multipart/x-mixed-replace; boundary=frame'
#     )

 
@app.route("/courses")
def courses_page():
    return render_template("courses.html")


@app.route("/generate_qr")
def generate_qr_page():
    return render_template("generate_qr.html")


@app.route("/Prof_ads")
def Prof_ads_page():
    return render_template("Prof_ads.html")


@app.route("/prof_assigment")
def prof_assigment_page():
    return render_template("prof_assigment.html")


@app.route("/Prof_courses")
def Prof_courses_page():
    return render_template("Prof_courses.html")


@app.route("/Prof_DaskBoard")
def Prof_DaskBoard_page():
    return render_template("Prof_DaskBoard.html")


@app.route("/prof_mid&final")
def prof_mid_final_page():
    return render_template("prof_mid&final.html")


@app.route("/Prof_quiz_editor")
def Prof_quiz_editor_page():
    return render_template("Prof_quiz_editor.html")


@app.route("/Prof_Proctoring")
def Prof_Proctoring_page():
    return render_template("Prof_Proctoring.html")


@app.route("/Prof_schedule")
def Prof_schedule_page():
    return render_template("Prof_schedule.html")


@app.route("/prof_chat")
def prof_chat_page():
    return render_template("prof_chat.html")


@app.route("/Prof_students")
def prof_students_page():
    return render_template("Prof_students.html")


@app.route("/robot")
def robot_page():
    return render_template("robot.html")



@app.route("/stu_assigment")
def stu_assigment_page():
    return render_template("stu_assigment.html")


@app.route("/stu_att")
def stu_att_page():
    return render_template("stu_att.html")


@app.route("/stu_chat")
def stu_chat_page():
    return render_template("stu_chat.html")


@app.route("/stu_courses")
def stu_courses_page():
    return render_template("stu_courses.html")



@app.route("/stu_ads")
def stu_ads_page():
    return render_template("stu_ads.html")


@app.route("/stu_schedule")
def stu_schedule_page():
    return render_template("stu_schedule.html")


@app.route("/stu_dashboard")
def stu_dashboard():
    return render_template("stu_dashboard.html")


@app.route("/stu_deg")
def stu_deg_page():
    return render_template("stu_deg.html")


@app.route("/stu_midterm")
def stu_midterm_page():
    return render_template("stu_midterm.html")


@app.route("/stu_quiz")
def stu_quiz_page():
    return render_template("stu_quiz.html")


@app.route("/stu_resources")
def stu_resources_page():
    return render_template("stu_resources.html")



@app.route("/student_course")
def student_course_page():
    return render_template("student_course.html")


@app.route("/student_requests")
def student_requests_page():
    return render_template("student_requests.html")    


@app.route("/track")
def track_page():
    return render_template("track.html")


@app.route("/users")
def users_page():
    return render_template("users.html")


@app.route("/worker")
def worker_page():
    return render_template("worker.html")



@app.route("/admin_gate")
def admin_gate_page():
    return render_template("admin_gate.html")



@app.route("/register_card")
def register_card_page():
    return render_template("register_card.html")


@app.route("/gate_logs")
def gate_logs_page():
    return render_template("gate_logs.html")

          



if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        allow_unsafe_werkzeug=True
    )
    # app.run(host="0.0.0.0", port=5000)

