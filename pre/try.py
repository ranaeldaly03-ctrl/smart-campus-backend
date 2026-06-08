# campus_fixed.py — نسخة مُصلَحة من API
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
import os
import traceback

# ---- config DB pool ----
dbconfig = {
    "user": "root",
    "password": "",
    "host": "127.0.0.1",
    "database": "smart_campus_new",
    "raise_on_warnings": True,
    "autocommit": False
}

# connection pool (used by some endpoints)
try:
    pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)
except Exception as e:
    print("Warning: could not create pool:", e)
    pool = None

app = Flask(__name__)
CORS(app)

# ---- uploads config ----
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---- allowed extensions (single definition) ----
ALLOWED_EXT = {'pdf','docx','pptx','mp4','zip','jpg','jpeg','png','gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ---- global db connection (fallback) ----
def create_db_connection():
    try:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='smart_campus_new'
        )
    except Exception as e:
        print("DB connect error:", e)
        return None

db = create_db_connection()

# helper to get a cursor with dictionary rows and auto-reconnect
def get_cursor(dictionary=True):
    global db
    try:
        if db is None or not db.is_connected():
            db = create_db_connection()
    except Exception:
        db = create_db_connection()
    return db.cursor(dictionary=dictionary)

# ---------------------------------------------------------------------
# Utility endpoints / serve uploads (name must match url_for('serve_uploads',...))
@app.route('/uploads/<path:filename>', endpoint='serve_uploads')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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

# ---------------------------------------------------------------------
# Routes (cleaned / fixed common bugs)
@app.route('/students', methods=['GET'])
def get_students():
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE role = %s", ('Student',))
    students = cur.fetchall()
    cur.close()
    return jsonify(students)

@app.route('/student/<int:student_id>', methods=['GET'])
def get_student(student_id):
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE role=%s AND id = %s", ('Student', student_id))
    student = cur.fetchone()
    cur.close()
    if student:
        return jsonify(student)
    else:
        return jsonify({"message" : "Student not found"}), 404

@app.route('/student/<int:student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    try:
        cur = get_cursor()
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
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('pass')
        phone = request.form.get('phone')
        department = request.form.get('department')
        level = request.form.get('level')
        image_file = request.files.get('image')

        image_name = 'admin.png'
        if image_file and allowed_file(image_file.filename):
            image_name = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
            image_file.save(image_path)

        cur = get_cursor()
        cur.execute("""
            INSERT INTO users (name, email, pass, phone, department, role, level, image)
            VALUES (%s, %s, %s, %s, %s, 'Student', %s, %s)
        """, (name, email, password, phone, department, level, image_name))
        db.commit()
        cur.close()
        return jsonify({"message": "✅ Student added successfully"})
    except Exception as e:
        db.rollback()
        print("Error in add_student:", e)
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

@app.route('/instructors', methods=['GET'])
def get_instructors():
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE role = %s", ('Instructor',))
    instructors = cur.fetchall()
    cur.close()
    return jsonify(instructors)

@app.route('/instructor/<int:instructor_id>', methods=['GET'])
def get_instructor(instructor_id):
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE role=%s AND id = %s", ('Instructor', instructor_id))
    instructor = cur.fetchone()
    cur.close()
    if instructor:
        return jsonify(instructor)
    else:
        return jsonify({"message": "Instructor not found"}), 404

@app.route('/add_admin', methods=['POST'])
def add_admin():
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('pass')
            phone = request.form.get('phone')
            image_file = request.files.get('image')
        else:
            data = request.get_json() or {}
            name = data.get('name')
            email = data.get('email')
            password = data.get('pass')
            phone = data.get('phone')
            image_file = None

        if not all([name, email, password, phone]):
            return jsonify({"message": "Missing required fields"}), 400

        cur = get_cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            return jsonify({"message": "Email already exists"}), 400

        image_path = 'uploads/admin.png'
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"admin_{name}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            image_path = f"uploads/{unique_filename}"

        cur.execute("""
            INSERT INTO users (name, email, pass, phone, role, image)
            VALUES (%s, %s, %s, %s, 'Admin', %s)
        """, (name, email, password, phone, image_path))
        db.commit()
        cur.close()
        return jsonify({"message": "✅ Admin added successfully!"}), 200
    except Exception as e:
        db.rollback()
        print("Error adding admin:", e)
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/add_instructor', methods=['POST'])
def add_instructor():
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('pass')
            phone = request.form.get('phone')
            department = request.form.get('department')
            image_file = request.files.get('image')
        else:
            data = request.get_json() or {}
            name = data.get('name')
            email = data.get('email')
            password = data.get('pass')
            phone = data.get('phone')
            department = data.get('department')
            image_file = None

        if not all([name, email, password, phone, department]):
            return jsonify({"message": "Missing required fields"}), 400

        cur = get_cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            return jsonify({"message": "Email already exists"}), 400

        image_path = 'uploads/default.png'
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"instructor_{name}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(filepath)
            image_path = f"uploads/{unique_filename}"

        cur.execute("""
            INSERT INTO users (name, email, pass, phone, department, role, image)
            VALUES (%s, %s, %s, %s, %s, 'Instructor', %s)
        """, (name, email, password, phone, department, image_path))
        db.commit()
        cur.close()
        return jsonify({"message": "✅ Instructor added successfully!"}), 200
    except Exception as e:
        db.rollback()
        print("❌ Error adding instructor:", e)
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

# ---- courses ----
@app.route('/courses', methods=['GET'])
def get_courses():
    try:
        cur = get_cursor()
        cur.execute("""
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
        courses = cur.fetchall()
        cur.close()
        return jsonify({"courses": courses}), 200
    except Exception as e:
        print("❌ Error fetching courses:", e)
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/enroll_student', methods=['POST'])
def enroll_student():
    try:
        data = request.get_json() or {}
        student_id = data.get('student_id')
        course_id = data.get('course_id')

        if not student_id or not course_id:
            return jsonify({"message": "Missing student_id or course_id"}), 400

        cur = get_cursor()
        cur.execute("INSERT INTO student_courses (student_id, course_id) VALUES (%s, %s)", (student_id, course_id))
        db.commit()
        cur.close()
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
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/admins', methods=['GET'])
def get_admins():
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE role = %s", ('Admin',))
    admins = cur.fetchall()
    cur.close()
    return jsonify(admins)

@app.route('/admin/<int:admin_id>', methods=['GET'])
def get_admin(admin_id):
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE role=%s AND id = %s", ('Admin', admin_id))
    admin = cur.fetchone()
    cur.close()
    if admin:
        return jsonify(admin)
    else:
        return jsonify({"message": "Admin not found"}), 404

@app.route('/add_grade', methods=['POST'])
def add_grade():
    try:
        data = request.get_json() or {}
        cur = get_cursor()
        cur.execute("""
            INSERT INTO grades (student_id, course_id, assignment_id, grade, total_grade)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data.get('student_id'),
            data.get('course_id'),
            data.get('assignment_id'),
            data.get('grade'),
            data.get('total_grade')
        ))
        db.commit()
        cur.close()
        return jsonify({"message": "Grade added successfully!"}), 200
    except Exception as e:
        db.rollback()
        print("Error while adding grade:", e)
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/get_grades/<int:student_id>', methods=['GET'])
def get_grades(student_id):
    try:
        cur = get_cursor()
        cur.execute("""
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
        grades = cur.fetchall()
        cur.close()
        return jsonify(grades), 200
    except Exception as e:
        print("Error while fetching grades:", e)
        traceback.print_exc()
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        user_id = data.get('id')
        password = data.get('password')

        if not user_id or not password:
            return jsonify({"status": "error", "message": "Missing ID or password"}), 400

        cur = get_cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()

        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        if user.get("pass") == password:
            return jsonify({
                "status": "ok",
                "role": user.get("role"),
                "name": user.get("name"),
                "id": user.get("id"),
                "image": user.get("image")
            })
        else:
            return jsonify({"status": "error", "message": "Invalid password"}), 401
    except Exception as e:
        print("Error in login:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@app.route('/user_stats')
def user_stats():
    try:
        cur = get_cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role=%s", ('Student',))
        student_count = cur.fetchone().get('cnt', 0)

        cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role=%s", ('Instructor',))
        doctor_count = cur.fetchone().get('cnt', 0)

        cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role=%s", ('Admin',))
        admin_count = cur.fetchone().get('cnt', 0)
        cur.close()

        return jsonify({
            "student": student_count,
            "professors": doctor_count,
            "admin": admin_count
        })
    except Exception as e:
        print("Error in user_stats:", e)
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

@app.route('/courses_stats')
def courses_count():
    try:
        cur = get_cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM course")
        courses_count = cur.fetchone().get('cnt', 0)
        cur.close()
        return jsonify({"courses": courses_count})
    except Exception as e:
        print("Error in courses_count:", e)
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

@app.route('/users/<role>', methods=['GET'])
def get_users_by_role(role):
    try:
        cur = get_cursor()
        level = request.args.get('level')
        if role == "student" and level:
            cur.execute("SELECT id, name, email, role, level FROM users WHERE role = %s AND level = %s", (role, level))
        else:
            cur.execute("SELECT id, name, email, role, level FROM users WHERE role = %s", (role,))
        users = cur.fetchall()
        cur.close()
        return jsonify({"status": "ok", "users": users})
    except Exception as e:
        print("Error fetchin users:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Database error"}), 500

# ---- student assignments listing endpoint (kept) ----
@app.route('/student/<int:student_id>/assignments', methods=['GET'])
def get_student_assignments(student_id):
    try:
        cur = get_cursor()
        cur.execute("""
            SELECT a.id, a.course_id, c.course_name, 
                   a.title, a.description, a.type, 
                   a.due_date, a.total_mark,
                   a.start_time, a.end_time
            FROM assignment a
            JOIN course c ON a.course_id = c.id
            JOIN student_courses sc ON sc.course_id = a.course_id
            WHERE sc.student_id = %s AND a.type = 'Assignment'
            ORDER BY a.due_date ASC
        """, (student_id,))
        assignments = cur.fetchall()
        cur.close()
        return jsonify(assignments), 200
    except Exception as e:
        print("Error in get_student_assignments:", e)
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

# ---------------------------------------------------------------------
# Upload book (save file to uploads and record DB)
@app.route('/upload_book', methods=['POST'])
def upload_book():
    try:
        course_id = request.form.get('course_id')
        title = request.form.get('title') or "Book"
        if 'file' not in request.files:
            return jsonify({"message":"No file"}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({"message":"Empty filename"}), 400
        filename = secure_filename(f.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(save_path)
        rel_path = f"uploads/{filename}"
        cur = get_cursor()
        cur.execute("INSERT INTO book (title, file_path, course_id) VALUES (%s, %s, %s)", (title, rel_path, course_id))
        db.commit()
        book_id = cur.lastrowid
        cur.execute("UPDATE course SET book_id = %s WHERE id = %s", (book_id, course_id))
        db.commit()
        cur.close()
        return jsonify({"message":"Book uploaded", "book_id": book_id}), 200
    except Exception as e:
        db.rollback()
        print("Error upload_book:", e)
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

# ---------------------------------------------------------------------
# Submit assignment (fixed and diagnostic logs)
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



@app.route('/assignments/<int:assignment_id>/submission', methods=['GET'])
def get_assignment_submission(assignment_id):
    """Return latest submission for given assignment + student_id (query param)."""
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"ok": False, "error": "student_id required"}), 400
    try:
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT id, original_filename, file_path, locked, uploaded_at
            FROM assignment_submissions
            WHERE assignment_id = %s AND student_id = %s
            ORDER BY uploaded_at DESC, id DESC
            LIMIT 1
        """, (assignment_id, student_id))
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify({"ok": False, "found": False}), 200

        # build external URL for the file if file_path exists
        file_url = None
        if row.get('file_path'):
            # file_path stored like 'uploads/xxx'
            fname = os.path.basename(row['file_path'])
            try:
                file_url = url_for('serve_uploads', filename=fname, _external=True)
            except Exception:
                file_url = request.host_url.rstrip('/') + '/uploads/' + fname

        return jsonify({
            "ok": True,
            "found": True,
            "submission_id": row['id'],
            "original_filename": row['original_filename'],
            "file_url": file_url,
            "locked": bool(row.get('locked')),
            "uploaded_at": row.get('uploaded_at')
        }), 200

    except Exception as e:
        app.logger.exception("get_assignment_submission failed")
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------------------------------------------------------------
# Debug routes list
@app.route('/_routes_debug', methods=['GET'])
def routes_debug():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({"endpoint": rule.endpoint, "rule": str(rule), "methods": sorted(list(rule.methods))})
    return jsonify(routes), 200

# ---------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
