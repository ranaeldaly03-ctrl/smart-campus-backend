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


import os, time, traceback


dbconfig = {
    "user": "DB_USER",
    "password": "DB_PASS",
    "host": "DB_HOST",
    "database": "DB_NAME",
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

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXT = {'pdf','docx','pptx','mp4','zip','jpg','jpeg','png','gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME")
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
    cursor.execute("SELECT * FROM users WHERE role='Student' AND id = %s", (student_id))
    student=cursor.fetchone()
    if student:
        return jsonify(student)
    else:
        return jsonify({"message" : "Student not found"}), 404



@app.route('/student/<int:student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    try:
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
    image_file = request.form.get('image')

    image_name = 'admin.png'
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
    cursor.execute("SELECT * FROM users WHERE role='instructor' AND id = %s", (instructor_id))
    instructor = cursor.fetchone()
    if instructor:
        return jsonify(instructor)
    else:
        return jsonify({"message": "Instructor not found"}), 404



@app.route('/add_admin', methods=['POST'])
def add_admin():
    try:
        # تحديد نوع الطلب
        if request.content_type.startswith('multipart/form-data'):
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('pass')
            phone = request.form.get('phone')
            image_file = request.files.get('image')  # ✅ لازم request.files
        else:
            data = request.get_json()
            name = data.get('name')
            email = data.get('email')
            password = data.get('pass')
            phone = data.get('phone')
            image_file = None

        # التحقق من الحقول المطلوبة
        if not all([name, email, password, phone]):
            return jsonify({"message": "Missing required fields"}), 400

        # التأكد من عدم تكرار البريد الإلكتروني
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 400

        # المسار الافتراضي للصورة
        image_path = 'uploads/admin.png'

        # حفظ الصورة في المجلد
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"admin_{name}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            image_path = f"uploads/{unique_filename}"

        # إدخال البيانات في قاعدة البيانات
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
        # التحقق من نوع الطلب (form-data لو فيها صورة، أو JSON لو بدون صورة)
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

        # تحقق من الحقول المطلوبة
        if not all([name, email, password, phone, department]):
            return jsonify({"message": "Missing required fields"}), 400

        # تأكد إن الإيميل مش مكرر
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 400

        # لو فيه صورة، احفظها
        image_path = 'uploads/default.png'
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"instructor_{name}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            image_path = f"uploads/{unique_filename}"

        # أضف الدكتور إلى قاعدة البيانات
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




# @app.route('/courses/<int:course_id>/students', methods=['GET'])
# def get_course_students(course_id):
#     try:
#         cursor = db.cursor(dictionary=True)
#         cursor.execute("""
#             SELECT s.id, s.name, s.email, s.level
#             FROM student_courses sc
#             JOIN users s ON sc.student_id = s.id
#             WHERE sc.course_id = %s
#         """, (course_id,))  # ✅ الفاصلة هنا مهمة جداً
#         students = cursor.fetchall()
#         return jsonify({"status": "ok", "students": students})
#     except Exception as e:
#         print("Error fetching course students:", e)
#         return jsonify({"status": "error", "message": str(e)}), 500




# في ملف campus.py (أو الملف اللي بتشغلي منه Flask) — استبدلي دالة get_courses الحالية بالآتي:

@app.route('/courses', methods=['GET'])
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
        data = request.get_json()
        user_id = data.get('id')
        password = data.get('password')

        # تأكد إن فيه بيانات جاية أصلًا
        if not user_id or not password:
            return jsonify({"status": "error", "message": "Missing ID or password"}), 400

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        # لو مفيش يوزر بالـ ID ده
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # التحقق من كلمة المرور
        if user["pass"] == password:  # ⚠️ (هنتكلم بعدين عن التشفير)
            return jsonify({
                "status": "ok",
                "role": user["role"],
                "name": user["name"],
                "id": user["id"],
                "image": user["image"]
            })
        else:
            return jsonify({"status": "error", "message": "Invalid password"}), 401

    except Exception as e:
        print("Error in login:", e)
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500



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



# @app.route('/user_stats', methods=['GET'])
# def user_stats():
#     try:
#         cur = db.cursor()
#         cur.execute("SELECT role, COUNT(*) as cnt FROM users GROUP BY role")
#         rows = cur.fetchall()  # [(role, cnt), ...]
#         cur.close()

#         # نهيئ الناتج بقيم افتراضية
#         stats = {"student": 0, "instructor": 0, "admin": 0}

#         for row in rows:
#             role = (row[0] or "").strip()
#             cnt = int(row[1] or 0)

#             key = role.lower()
#             if key == 'student':
#                 stats['student'] += cnt
#             elif key in ('instructor', 'instractor', 'professor', 'doctor'):
#                 stats['instructor'] += cnt
#             elif key == 'admin':
#                 stats['admin'] += cnt
#             else:
#                 # أدوار غير متوقعة — نخزنها أيضاً بصيغة lower-case
#                 stats.setdefault(key, 0)
#                 stats[key] += cnt

#         return jsonify(stats), 200

#     except Exception as e:
#         print("Error in user_stats:", e)
#         return jsonify({"message": str(e)}), 500





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
    


# @app.route('/schedule', methods=['GET'])
# def get_schedule():
#     try:
#         cursor = db.cursor(dictionary=True)
#         cursor.execute("""
#             SELECT 
#                 s.id,
#                 c.course_name,
#                 u.name AS instructor,
#                 s.day,
#                 s.start_time,
#                 s.end_time,
#                 s.room
#             FROM schedule s
#             JOIN course c ON s.course_id = c.id
#             JOIN users u ON s.instructor_id = u.id
#         """)
#         data = cursor.fetchall()
#         return jsonify(data)
#     except Exception as e:
#         print("❌ Error loading schedule:", e)
#         return jsonify({"message": str(e)}), 500


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
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---- route لجلب بيانات المستخدم مع رابط الصورة (مفيد بعد login) ----
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, role, image FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        if not user:
            return jsonify({"message": "User not found"}), 404

        # حوّلي قيمة الحقل image (لو موجودة) إلى رابط كامل للعرض
        if user.get('image'):
            user['image_url'] = request.host_url.rstrip('/') + '/' + user['image']
        else:
            user['image_url'] = request.host_url.rstrip('/') + '/static/default.png'

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




# @app.route('/courses/<int:course_id>/students', methods=['GET'])
# def get_students_in_course(course_id):
#     try:
#         cursor = db.cursor(dictionary=True)
#         cursor.execute("""
#             SELECT 
#                 u.id, 
#                 u.name, 
#                 u.email, 
#                 u.level,
#                 COALESCE(SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END), 0) AS attendance_count,
#                 COALESCE(SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END), 0) AS absence_count
#             FROM student_course sc
#             JOIN users u ON sc.student_id = u.id
#             LEFT JOIN attendance a ON a.student_id = u.id AND a.course_id = sc.course_id
#             WHERE sc.course_id = %s
#             GROUP BY u.id, u.name, u.email, u.level
#         """, (course_id,))
#         students = cursor.fetchall()
#         return jsonify({"students": students})
#     except Exception as e:
#         print("❌ Error loading students with attendance:", e)
#         return jsonify({"message": str(e)}), 500




# @app.route('/instructor/<int:inst_id>/courses', methods=['GET'])
# def get_instructor_courses(inst_id):
#     cursor = db.cursor(dictionary=True)
#     cursor.execute("""
#         SELECT id, course_name
#         FROM course
#         WHERE instructor_id = %s
#     """, (inst_id,))
#     courses = cursor.fetchall()
#     return jsonify(courses)



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



# @app.route('/instructor/<int:inst_id>/courses', methods=['GET'])
# def get_instructor_courses(inst_id):
#     cursor = db.cursor(dictionary=True)
#     cursor.execute("""
#         SELECT id, course_name 
#         FROM course 
#         WHERE instructor_id = %s
#     """, (inst_id,))
#     courses = cursor.fetchall()
#     return jsonify(courses)



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



# @app.route('/student/<int:student_id>/grades/<int:course_id>', methods=['GET'])
# def student_grades(student_id, course_id):
#     cursor = db.cursor(dictionary=True)
#     cursor.execute("""
#         SELECT a.title, a.type, g.grade, g.total_grade
#         FROM grades g
#         JOIN assignment a ON g.assignment_id = a.id
#         WHERE g.student_id = %s AND g.course_id = %s
#     """, (student_id, course_id))
#     return jsonify(cursor.fetchall())


# upload_book: يحفظ الملف في static/uploads ويدخل سجل في جدول Books
# @app.route('/upload_book', methods=['POST'])
# def upload_book():
#     try:
#         course_id = request.form.get('course_id')
#         title = request.form.get('title') or "Book"
#         if 'file' not in request.files:
#             return jsonify({"message":"No file"}), 400
#         f = request.files['file']
#         if f.filename == '':
#             return jsonify({"message":"Empty filename"}), 400
#         filename = secure_filename(f.filename)
#         save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         f.save(save_path)
#         # خزني المسار النسبي في جدول book — العمود الصحيح file_path
#         rel_path = f"uploads/{filename}"
#         cur = db.cursor()
#         # استخدمي file_path هنا بدلاً من file_bath
#         cur.execute("INSERT INTO book (title, file_path, course_id) VALUES (%s, %s, %s)", (title, rel_path, course_id))
#         db.commit()
#         book_id = cur.lastrowid
#         # لو حابة تربطي الكتاب بالمادة
#         cur.execute("UPDATE course SET book_id = %s WHERE id = %s", (book_id, course_id))
#         db.commit()
#         return jsonify({"message":"Book uploaded", "book_id": book_id}), 200
#     except Exception as e:
#         db.rollback()
#         return jsonify({"message": str(e)}), 500



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




# @app.route('/student/<int:student_id>/assignments', methods=['GET'])
# def get_student_assignments(student_id):
#     cursor = db.cursor(dictionary=True)

#     cursor.execute("""
#         SELECT 
#             a.id,
#             a.title,
#             a.description,
#             a.type,
#             a.due_date,
#             a.total_mark,
#             c.course_name
#         FROM assignment a
#         JOIN student_courses sc ON sc.course_id = a.course_id
#         JOIN course c ON c.id = a.course_id
#         WHERE sc.student_id = %s
#         ORDER BY a.due_date ASC
#     """, (student_id,))
    
#     assignments = cursor.fetchall()
#     return jsonify(assignments)


# @app.route('/student/<int:student_id>/assignments', methods=['GET'])
# def get_student_assignments(student_id):
#     try:
#         cur = db.cursor(dictionary=True)
#         cur.execute("""
#             SELECT a.id, a.course_id, c.course_name, 
#                    a.title, a.description, a.type, 
#                    a.due_date, a.total_mark,
#                    a.start_time, a.end_time
#             FROM assignment a
#             JOIN course c ON a.course_id = c.id
#             JOIN student_courses sc ON sc.course_id = a.course_id
#             WHERE sc.student_id = %s AND a.type = 'Assignment'
#             ORDER BY a.due_date ASC
#         """, (student_id,))
#         assignments = cur.fetchall()
#         cur.close()
#         return jsonify(assignments), 200
#     except Exception as e:
#         print("Error in get_student_assignments:", e)
#         return jsonify({"message": str(e)}), 500


@app.route('/student/<int:student_id>/assignments', methods=['GET'])
def get_student_assignments(student_id):
    try:
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
                        r['file_url'] = url_for('serve_uploads', filename=fname, _external=True)
                    except Exception:
                        r['file_url'] = request.url_root.rstrip('/') + '/' + fp_str
                elif fp_str.startswith('static/'):
                    r['file_url'] = request.url_root.rstrip('/') + '/' + fp_str
                else:
                    # افتراض: مجرد اسم ملف مخزن
                    try:
                        r['file_url'] = url_for('serve_uploads', filename=os.path.basename(fp_str), _external=True)
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
    cur = db.cursor(dictionary=True)
    # درجات مفصلة
    cur.execute("""
        SELECT g.id AS grade_id, g.student_id, g.course_id, c.course_name,
               g.assignment_id, a.title AS assignment_title, g.grade, g.total_grade
        FROM grades g
        JOIN course c ON g.course_id = c.id
        LEFT JOIN assignment a ON g.assignment_id = a.id
        WHERE g.student_id = %s
        ORDER BY c.course_name, a.due_date
    """, (student_id,))
    rows = cur.fetchall()

    # مجموعات حسب course
    cur.execute("""
        SELECT g.student_id, g.course_id, SUM(g.grade) AS total_marks
        FROM grades g
        WHERE g.student_id = %s
        GROUP BY g.student_id, g.course_id
    """, (student_id,))
    totals = cur.fetchall()
    cur.close()

    return jsonify({"grades": rows, "totals": totals})


# GET grades for a course (for instructor): all students + their grades per assignment
# @app.route('/course/<int:course_id>/grades', methods=['GET'])
# def get_course_grades(course_id):
#     cur = db.cursor(dictionary=True)
#     # كل الـ assignments في المادة
#     cur.execute("SELECT id, title, total_mark FROM assignment WHERE course_id = %s ORDER BY id", (course_id,))
#     assignments = cur.fetchall()

#     # كل الطلاب المسجلين في المادة
#     cur.execute("""
#         SELECT u.id AS student_id, u.name
#         FROM student_courses sc
#         JOIN users u ON sc.student_id = u.id
#         WHERE sc.course_id = %s
#     """, (course_id,))
#     students = cur.fetchall()

#     # درجات كل طالب لكل اسايمنت
#     cur.execute("""
#         SELECT g.id AS grade_id, g.student_id, g.assignment_id, g.grade
#         FROM grades g
#         WHERE g.course_id = %s
#     """, (course_id,))
#     grades = cur.fetchall()
#     cur.close()

#     return jsonify({"assignments": assignments, "students": students, "grades": grades})


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




@app.route('/student/<int:student_id>/dashboard', methods=['GET'])
def get_student_dashboard(student_id):
    try:
        cur = db.cursor(dictionary=True)

        # student basic
        cur.execute("SELECT id, name, email, role, level, image FROM users WHERE id = %s", (student_id,))
        student = cur.fetchone() or {}

        # courses list + assignments count per course
        cur.execute("""
            SELECT c.id AS course_id, c.course_name, c.department,
                   COUNT(a.id) AS assignments_count
            FROM student_courses sc
            JOIN course c ON sc.course_id = c.id
            LEFT JOIN assignment a ON a.course_id = c.id
            WHERE sc.student_id = %s
            GROUP BY c.id, c.course_name, c.department
        """, (student_id,))
        courses = cur.fetchall() or []
        courses_count = len(courses)

        # total assignments count across courses
        cur.execute("""
            SELECT COUNT(*) AS total_assignments
            FROM assignment a
            JOIN student_courses sc ON sc.course_id = a.course_id
            WHERE sc.student_id = %s AND a.type = 'Assignment'
        """, (student_id,))
        assignments_count = cur.fetchone().get('total_assignments', 0)

        # upcoming assignments (limit some)
        cur.execute("""
            SELECT a.id, a.course_id, c.course_name, a.title, a.due_date, a.total_mark
            FROM assignment a
            JOIN course c ON a.course_id = c.id
            JOIN student_courses sc ON sc.course_id = a.course_id
            WHERE sc.student_id = %s
            ORDER BY a.due_date ASC
            LIMIT 10
        """, (student_id,))
        upcoming = cur.fetchall() or []

        cur.close()

        return jsonify({
            "student": student,
            "courses_count": courses_count,
            "courses": courses,
            "assignments_count": assignments_count,
            "assignments": upcoming
        }), 200

    except Exception as e:
        print("Error in get_student_dashboard:", e)
        return jsonify({"message": str(e)}), 500



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
    cur = db.cursor()
    cur.execute("""
        UPDATE attendance_sessions
        SET active=0, end_time = NOW()
        WHERE course_id=%s AND active=1
    """, (course_id,))
    db.commit()
    return jsonify({"message":"Attendance stopped"}), 200




@app.route('/mark_by_code', methods=['POST'])
def mark_by_code():
    data = request.get_json() or {}
    student_id = data.get('student_id')
    session_code = data.get('session_code')

    if not student_id or not session_code:
        return jsonify({"message":"student_id and session_code required"}), 400

    cur = db.cursor(dictionary=True)
    # جلب الجلسة الفعّالة بالكود
    cur.execute("SELECT * FROM attendance_sessions WHERE session_code=%s AND active=1", (session_code,))
    sess = cur.fetchone()
    if not sess:
        return jsonify({"message":"Session not active or code invalid"}), 400

    session_id = sess['id']
    course_id = sess['course_id']

    # تحقق إن الطالب مسجّل في المادة (اختياري لكن يفضل)
    cur.execute("SELECT * FROM student_courses WHERE student_id=%s AND course_id=%s", (student_id, course_id))
    if not cur.fetchone():
        return jsonify({"message":"Student not enrolled in this course"}), 403

    # تحقق من عدم التكرار لنفس الجلسة
    cur.execute("SELECT id FROM attendance WHERE student_id=%s AND session_id=%s", (student_id, session_id))
    if cur.fetchone():
        return jsonify({"message":"Already marked"}), 200

    # أضف حضور
    cur2 = db.cursor()
    cur2.execute("INSERT INTO attendance (student_id, course_id, date, status, session_id) VALUES (%s,%s,CURDATE(),'present',%s)",
                 (student_id, course_id, session_id))
    db.commit()
    return jsonify({"message":"Attendance marked"}), 200





@app.route('/attendance_session/<int:session_id>/students', methods=['GET'])
def attendance_session_students(session_id):
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
            host='localhost', user='root', password='', database='smart_campus_new'
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
            SELECT u.id, u.name,
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





@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    conn = None; cur = None
    try:
        # قبول JSON أو multipart/form-data
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            course_id = request.form.get('course_id')
            title = request.form.get('title')
            description = request.form.get('description') or ''
            type_ = request.form.get('type') or 'Assignment'
            due_date = request.form.get('due_date') or None
            total_mark = request.form.get('total_mark') or 0
            file_obj = request.files.get('file')
        else:
            data = request.get_json(force=True, silent=True) or {}
            course_id = data.get('course_id')
            title = data.get('title')
            description = data.get('description') or ''
            type_ = data.get('type') or 'Assignment'
            due_date = data.get('due_date') or None
            total_mark = data.get('total_mark') or 0
            file_obj = None

        if not course_id or not title:
            return jsonify({"ok": False, "message": "course_id and title required"}), 400

        # get connection (pool preferred)
        if pool:
            conn = pool.get_connection()
            cur = conn.cursor()
        else:
            if db is None or not getattr(db, 'is_connected', lambda: True)():
                db.reconnect(attempts=3, delay=1)
            conn = db
            cur = conn.cursor()

        # insert assignment (table name 'assignments' expected)
        try:
            cur.execute(
                "INSERT INTO assignments (course_id, title, description, type, due_date, total_mark) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (course_id, title, description, type_, due_date, total_mark)
            )
        except Exception as e:
            # fallback if table named 'assignment'
            try:
                cur.execute(
                    "INSERT INTO assignment (course_id, title, description, type, due_date, total_mark) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (course_id, title, description, type_, due_date, total_mark)
                )
            except Exception as ee:
                conn.rollback()
                raise

        assignment_id = cur.lastrowid

        # handle file if provided
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

            # try update assignments.file_path, if fails try insert into assignment_files table
            try:
                cur.execute("UPDATE assignments SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
            except Exception:
                try:
                    cur.execute("UPDATE assignment SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
                except Exception:
                    # fallback to assignment_files table if exists
                    try:
                        cur.execute("INSERT INTO assignment_files (assignment_id, original_filename, file_path) VALUES (%s,%s,%s)",
                                    (assignment_id, filename, rel_path))
                    except Exception:
                        # ignore, but keep assignment created
                        pass

        conn.commit()
        return jsonify({"ok": True, "assignment_id": assignment_id}), 201

    except Exception as e:
        try:
            if conn: conn.rollback()
        except: pass
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
            if pool and conn: conn.close()
        except: pass





from flask import url_for

@app.route('/course/<int:course_id>/books_and_files', methods=['GET'])
def course_books_and_files(course_id):
    try:
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
                    r['file_url'] = url_for('serve_uploads', filename=filename, _external=True)
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
    print('DEBUG serve_uploads request for:', filename)
    print('DEBUG uploads_dir =', uploads_dir)
    print('DEBUG full path =', full)
    print('DEBUG exists =', os.path.exists(full))
    if not os.path.exists(full):
        return jsonify({"message":"file not found on server","path": full}), 404
    return send_from_directory(uploads_dir, filename, as_attachment=False)


# ===========================
#  Serve Uploaded Files
# ===========================

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    uploads_dir = app.config.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    
    full = os.path.join(uploads_dir, filename)

    print('DEBUG serve_uploads request for:', filename)
    print('DEBUG uploads_dir =', uploads_dir)
    print('DEBUG full path =', full)
    print('DEBUG exists =', os.path.exists(full))

    if not os.path.exists(full):
        return jsonify({"message":"file not found", "path": full}), 404

    return send_from_directory(uploads_dir, filename, as_attachment=False)




import stat

@app.route('/assignments/<int:assignment_id>/submit', methods=['POST'])
def submit_assignment(assignment_id):
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "No file provided"}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({"ok": False, "error": "Empty filename"}), 400

        student_id = request.form.get('student_id') or request.values.get('student_id')
        if not student_id:
            return jsonify({"ok": False, "error": "student_id required"}), 400

        uploads_dir = app.config.get('UPLOAD_FOLDER')
        os.makedirs(uploads_dir, exist_ok=True)

        filename = secure_filename(f.filename)
        unique = f"submission_{student_id}_{assignment_id}_{int(time.time())}_{filename}"
        save_path = os.path.join(uploads_dir, unique)
        f.save(save_path)

        # make file read-only on filesystem (best-effort)
        try:
            # Unix-like
            os.chmod(save_path, 0o444)
        except Exception as e:
            # On Windows this may not have expected effect, ignore errors
            app.logger.debug("Could not chmod file to readonly: %s", e)

        # insert record with locked=1
        cur = db.cursor()
        cur.execute(
            "INSERT INTO assignment_submissions (assignment_id, student_id, original_filename, file_path, locked, uploaded_at) "
            "VALUES (%s,%s,%s,%s,%s,NOW())",
            (assignment_id, student_id, filename, f"uploads/{unique}", 1)
        )
        db.commit()
        sub_id = cur.lastrowid
        cur.close()

        file_url = url_for('serve_uploads', filename=unique, _external=True)
        return jsonify({"ok": True, "file_url": file_url, "submission_id": sub_id}), 200

    except Exception as e:
        db.rollback()
        app.logger.exception("submit_assignment failed")
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
        uploads_dir = app.config.get('UPLOAD_FOLDER')
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, unique)
        f.save(save_path)
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
            cur.execute("UPDATE assignments SET file_path = %s WHERE id = %s", (rel_path, assignment_id))
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

        file_url = url_for('serve_uploads', filename=unique, _external=True)
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
                s = str(fp).lstrip('/')
                if s.startswith('static/') or s.startswith('uploads/'):
                    file_url = request.url_root.rstrip('/') + '/' + s
                else:
                    file_url = request.url_root.rstrip('/') + '/static/uploads/' + s

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

if __name__ == '__main__':
    app.run(debug=True)    


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

        file_url = url_for('serve_uploads', filename=unique, _external=True)
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







if __name__ == '__main__':
    app.run(debug=True)


