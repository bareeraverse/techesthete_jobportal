Job Portal Application Overview
This is a Job portal web application made with the flask framework. It enables users to see and apply for jobs, while the admin can manage jobs and viewapplications.

##scope of the project
Google OAuth is used to handle user authentication
**Users**: can log in, view available job opening, apply to them and submit resumes and cover letters
**Admin**: can create a job, edit or delete it and view the submitted applications
**Resumes** can be uploaded of extensions : pdf, doc, docx, txt
**Email notification** will be sent to the amdin when an application is submitted
**SQLite databse** for storing users, jobs, and applications

*Used Tech*
**Backend:** Flask (Python)
**Database:** SQLite with SQLAlchemy ORM
**Authentication:** Flask-Dance (Google OAuth)
**Email:** Flask-Mail (Gmail SMTP)
**File Uploads:** Handled securely with Werkzeug
**User Sessions:** Flask-Login
**Frontend:** Jinja2 templates with Bootstrap CSS

*Application Flow:*
-> **User visits `/`** and logs in with Google.
-> After logging in, user is redirected to `/welcome`
-> Users can:
   - Browse all jobs at `/jobs`.
   - Search jobs with `/jobs/search?q=keyword`.
   - View job details at `/jobs/<job_id>`.
   - Submit an application with resume upload and cover letter.
-> Admin user (`ADMIN_EMAIL`) can access admin dashboard at `/admin` to manage jobs and view applications.
-> Admin can create, edit, delete jobs and view applications for each job.

**API ENDPOINTS**
*Routes of User:*
**GET /** — Home / Login page
**GET /force-login** — Redirect to Google OAuth login
**GET /welcome** — User welcome page after login
**GET /jobs** — List all jobs
**GET /jobs/search?q=keyword** — Search jobs by title
**GET /jobs/<job_id>** — View job details
**POST /jobs/<job_id>** — Submit job application with resume and cover letter
**GET /logout** — Log out the user
**GET /uploads/<filename>** — Download uploaded resume file


*Admin Only routes:*
**GET /admin** — Admin dashboard
**GET /admin/jobs** — List all jobs with management options
**GET, POST /admin/jobs/create** — Create a new job
**GET, POST /admin/jobs/edit/<job_id>** — Edit a job
**GET /admin/jobs/delete/<job_id>** — Delete a job
**GET /admin/applications** — List jobs with applications
**GET /admin/applications/<job_id>** — View applications for a specific job



