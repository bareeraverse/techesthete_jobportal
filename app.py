from flask import Flask, redirect, url_for, session
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import request
from flask import request, render_template_string 
from datetime import datetime
from flask import render_template

from flask_login import UserMixin
import os
from flask import request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask import Flask
from flask_login import current_user
from flask_login import LoginManager
from flask import send_from_directory
from flask_mail import Mail, Message
db=SQLAlchemy()

load_dotenv()
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['UPLOAD_FOLDER']='static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobportal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "your-admin@gmail.com")
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']= 587
app.config['MAIL_USE_TLS']= True
app.config['MAIL_USERNAME']=os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD']=os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER']=os.getenv('MAIL_USERNAME')

mail= Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)


google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_to="welcome"
)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), default='user')  # 'user' or 'admin'
    registered_on = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Application', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Application', backref='job', lazy=True)

    def __repr__(self):
        return f'<Job {self.title}>'
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    resume_link = db.Column(db.String(300))
    cover_letter = db.Column(db.Text)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.id} by User {self.user_id}>'

app.register_blueprint(google_bp, url_prefix="/login")

@login_manager.user_loader  
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    return '<a href="/force-login">Login with Google (Choose Account)</a>'


@app.route("/force-login")
def force_login():
    return redirect(url_for("google.login") + "?prompt=select_account")

from flask_login import login_user

@app.route("/welcome")
def welcome():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return f"Failed to fetch user info: {resp.text}"

    user_info = resp.json()
    session["user"] = {
        "name": user_info["name"],
        "email": user_info["email"],
        "role": "admin" if user_info["email"] == ADMIN_EMAIL else "user"
    }

    user = User.query.filter_by(email=user_info["email"]).first()
    if not user:
        user = User(name=user_info["name"], email=user_info["email"])
        db.session.add(user)
        db.session.commit()
    login_user(user)

    return f"""
        <h1>Welcome, {user_info['name']}</h1>
        <p>Email: {user_info['email']}</p>
        <p>Role: {'Admin' if user_info['email'] == ADMIN_EMAIL else 'User'}</p>
        <a href='/admin'>Go to Admin Panel</a>
        <a href='/jobs'>View Job Listings</a>
    """

@app.route("/jobs/<int:job_id>", methods=["GET", "POST"])
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)

    if request.method == "POST":
        print("Form Submitted")
        if not current_user.is_authenticated:
            print("User not authenticated, redirecting to login")
            return redirect(url_for("google.login"))

        try:
            resume = request.files["resume"]
            cover_letter = request.form.get("cover_letter")

            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            if resume.filename == '':
                return "No file selected", 400

            if not allowed_file(resume.filename):
                return "Unsupported file type", 400

            filename = secure_filename(resume.filename)
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(resume_path)

            application = Application(
                user_id=current_user.id,
                job_id=job.id,
                resume_link=filename,
                cover_letter=cover_letter,
            )
            db.session.add(application)
            db.session.commit()
            #email of application to amdin
            msg= Message(
                subject=f'New Application for:{job.title}',
                recipients=[ADMIN_EMAIL],
                body=f'''
A new job application just got submitted.
Job Title: {job.title}
Applicant Name: {current_user.name}
Application Email :{current_user.email}
Cover Letter: {cover_letter}
Resume Link: {request.url_root}uploads/{filename}


                '''
            )
            try:
                mail.send(msg)
                print("Email sent to admin")
            except Exception as e:
                print("failed to send 404",e)

            print("✅ Application saved successfully")
            return "<p>Application submitted successfully!</p><a href='/jobs'>Back to Jobs</a>"

        except Exception as e:
            print("❌ Error during form submission:", e)
            return f"<p>Something went wrong: {e}</p>"

    return f"""
        <h1>{job.title}</h1>
        <p><strong>Description:</strong> {job.description}</p>
        <p><strong>Requirements:</strong> {job.requirements}</p>

        <h3>Apply Now</h3>
        <form method="POST" enctype="multipart/form-data">
            <label>Upload Resume:</label><br>
            <input type="file" name="resume" required><br><br>
            <label>Cover Letter:</label><br>
            <textarea name="cover_letter" rows="5" cols="50" required></textarea><br><br>
            <button type="submit">Submit Application</button>
        </form>
    """


@app.route("/admin")
def admin():
    user = session.get("user")
    if not user:
        return redirect(url_for("google.login"))

    if user["email"] != ADMIN_EMAIL:
        return "Access denied. You are not an admin."

    return f"""
    <h1>Admin Panel</h1>
    <p>Welcome, {user['name']}!</p>
    <a href='/admin/jobs'>Go to Job Management</a>
"""


@app.route("/admin/jobs")
def admin_jobs():
    user = session.get("user")
    if not user or user.get("email") != ADMIN_EMAIL:
        return "Access denied."

    jobs = Job.query.order_by(Job.created_at.desc()).all()
    job_list = ""
    print(f"Jobs found: {len(jobs)}")

    for job in jobs:
        job_list += f"""
            <div style='border:1px solid #ccc; padding:10px; margin:10px;'>
                <h3>{job.title}</h3>
                <p><strong>Description:</strong> {job.description}</p>
                <p><strong>Requirements:</strong> {job.requirements}</p>
                <a href="/admin/jobs/edit/{job.id}">Edit</a> |
                <a href="/admin/jobs/delete/{job.id}">Delete</a> |
                <a href="/admin/applications/{job.id}">View Applications</a>


            </div>
        """

    return f"""
        <h1>Admin Job Management</h1>
        <a href="/admin/jobs/create">Create New Job</a>
        <br><br>
        {job_list}
    """

@app.route("/jobs")
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    job_list = ""

    for job in jobs:
        job_list += f"""
            <div style='border:1px solid #ccc; padding:10px; margin:10px;'>
                <h2>{job.title}</h2>
                <p>{job.description[:150]}...</p>
                <a href="/jobs/{job.id}">View Details</a>
            </div>
        """

    return f"""
        <h1>Available Jobs</h1>
        <form method="GET" action="/jobs/search">
            <input type="text" name="q" placeholder="Search by title...">
            <button type="submit">Search</button>
        </form>
        <br>
        {job_list if job_list else '<p>No jobs available.</p>'}
    """
@app.route("/jobs/search")
def search_jobs():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("list_jobs"))

    results = Job.query.filter(Job.title.ilike(f"%{query}%")).order_by(Job.created_at.desc()).all()
    job_list = ""

    for job in results:
        job_list += f"""
            <div style='border:1px solid #ccc; padding:10px; margin:10px;'>
                <h2>{job.title}</h2>
                <p>{job.description[:150]}...</p>
                <a href="/jobs/{job.id}">View Details</a>
            </div>
        """

    return f"""
        <h1>Search Results for: '{query}'</h1>
        <a href="/jobs">← Back to All Jobs</a>
        <br><br>
        {job_list if job_list else '<p>No matching jobs found.</p>'}
    """

@app.route("/admin/jobs/create", methods=["GET", "POST"])
def create_job():
    user = session.get("user")
    if not user or user.get("email") != ADMIN_EMAIL:
        return "Access denied."

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        requirements = request.form.get("requirements")

        if title and description:
            new_job = Job(title=title, description=description, requirements=requirements)
            db.session.add(new_job)
            db.session.commit()
            return redirect(url_for('admin_jobs'))
        else:
            return "Title and Description are required.", 400

    # If GET request, show the form
    return render_template_string("""
        <h1>Create New Job</h1>
        <form method="POST">
            <label>Title:</label><br>
            <input type="text" name="title" required><br><br>

            <label>Description:</label><br>
            <textarea name="description" required></textarea><br><br>

            <label>Requirements:</label><br>
            <textarea name="requirements"></textarea><br><br>

            <button type="submit">Create Job</button>
        </form>
        <br>
        <a href="/admin/jobs">Back to Job List</a>
    """)

@app.route("/admin/jobs/edit/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):
    user = session.get("user")
    if not user or user.get("email") != ADMIN_EMAIL:
        return "Access denied."

    job = Job.query.get_or_404(job_id)

    if request.method == "POST":
        job.title = request.form["title"]
        job.description = request.form["description"]
        job.requirements = request.form["requirements"]
        db.session.commit()
        return redirect(url_for("admin_jobs"))

    return f"""
        <h1>Edit Job</h1>
        <form method="post">
            <label>Title:</label><br>
            <input type="text" name="title" value="{job.title}"><br><br>
            
            <label>Description:</label><br>
            <textarea name="description">{job.description}</textarea><br><br>
            
            <label>Requirements:</label><br>
            <textarea name="requirements">{job.requirements}</textarea><br><br>
            
            <input type="submit" value="Update Job">
        </form>
        <br>
        <a href="/admin/jobs">← Back to Job List</a>
    """
   

@app.route("/admin/jobs/delete/<int:job_id>")
def delete_job(job_id):
    user = session.get("user")
    if not user or user.get("email") != ADMIN_EMAIL:
        return "Access denied."
    job = Job.query.get_or_404(job_id)

    # Delete applications linked to this job
    Application.query.filter_by(job_id=job.id).delete()

    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return redirect(url_for("admin_jobs"))

@app.route('/admin/applications/<int:job_id>')
def view_applications(job_id):
    user = session.get("user")
    if not user or user.get("email") != ADMIN_EMAIL:
        return redirect(url_for('welcome'))    
    job=Job.query.get_or_404(job_id)
    applications=Application.query.filter_by(job_id=job.id).all()
    return render_template('admin_applications.html', job=job, applications=applications)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment =True)


if __name__ == "__main__":
    with app.app_context():
        print("Creating database.")
        db.create_all()
        print("Database created.")
    app.run(debug=True)




