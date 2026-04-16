from flask import Flask, request, render_template, url_for, redirect, session, flash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import pymysql

app = Flask(__name__)
app.secret_key = "mysecretkey"


con = pymysql.connect(
    host='localhost',
    user='root',
    password='josnavi',
    database='notedb',
    cursorclass=pymysql.cursors.DictCursor
)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 587               
app.config['MAIL_USE_TLS'] = True            
app.config['MAIL_USERNAME'] = "josnavidunga@gmail.com"  
app.config['MAIL_PASSWORD'] = "ckgl tbak ipon cadq" 

mail = Mail(app)  
s = URLSafeTimedSerializer(app.secret_key)

@app.route("/")
def Home():
    return render_template('login.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form["username"]
        pwd = request.form["password"]
        cur = con.cursor()
        cur.execute("SELECT * FROM user WHERE uname=%s AND password=%s", (uname, pwd))
        user = cur.fetchone()
        if user:
            session["admin"] = user['user_id']
       
            return redirect("/dashboard")
        else:
            flash("Invalid credentials!")
            return render_template("login.html")
    return render_template("login.html")

@app.route('/forgot_password')
def forgot_password():
    return render_template("forgot_password.html")

@app.route('/send_reset_link', methods=['POST'])
def send_reset_link():
    email = request.form['email']  
    cur=con.cursor()
    cur.execute("select * from user where email=%s",(email,))
    res=cur.fetchone()

    if not res:
        flash("Email not registered!")
        return redirect('/forgot_password')
    
    token = s.dumps(email, salt='password-reset-salt')
    
    link = f"http://localhost:5000/reset_password/{token}"
    
    msg = Message("Password Reset Request", 
                  sender="josnavidunga@gmail.com",
                  recipients=[email])
    msg.body = f"Click the link to reset your password: {link}"
    mail.send(msg)  # Send email
    
    flash("Reset link sent to your email!")
    return render_template('login.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=300)  
    except SignatureExpired:
        return "Link expired! Try again."
    except BadSignature:
        return "Token modifed"
    
    if request.method == 'POST':
        new_password = request.form['password']
        cur=con.cursor()
        res=cur.execute("update user set password=%s where email=email",(new_password,))
        
        flash("Password reset successful! Please login.")
        return render_template('login.html')
    
    return render_template("reset_password.html")

@app.route("/reg")
def Reg():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def Register_User():
    uname = request.form['uname']
    pwrd = request.form['pwrd']
    email = request.form['email']
    cur = con.cursor()
    # Fixed: Removed extra %s
    cur.execute("INSERT INTO user(uname, email, password) VALUES(%s, %s, %s)", 
                (uname, email, pwrd))
    con.commit()
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    a=session["admin"]
    if "admin" in session:
        cur = con.cursor()
        
        cur.execute("SELECT * FROM notes where user_id=%s",(a,))
        notes=cur.fetchall()
        
        # Pass the data to your template
        return render_template("dashboard.html",notes=notes)
    return redirect("/")


@app.route("/contact1")
def Contact1():
    return render_template('contact.html')

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
       
        name = request.form.get('name')
        sender_email = request.form.get('email')
        subject = request.form.get('subject')
        message_body = request.form.get('message')

        
        msg = Message(
            subject=f"EMS Contact: {subject}",
            sender=sender_email,
            recipients=["josnavidunga@gmail.com"]
        )
        
        msg.body = f"""
        New message from your EMS Contact Form:
        
        Name: {name}
        Email: {sender_email}
        Subject: {subject}
        
        Message:
        {message_body}
        """

        try:
          
            mail.send(msg)
            flash("Message sent successfully to Admin!", "success")
        except Exception as e:
            flash("Failed to send message. Please check your connection.", "danger")

        return redirect(url_for('contact'))

    # If GET request, just show the page
    return render_template('login.html')

@app.route('/about')
def About():
    return render_template('about.html')


@app.route('/logout')
def logout():
    session.pop('admin', None) 
    return redirect('/')

@app.route('/add_note')
def Addnote():
    return render_template('add_note.html')



@app.route('/add_note', methods=['GET', 'POST'])
def add_note():
   
    if request.method == 'POST':
        
        title = request.form.get('title')
        content = request.form.get('content')
        user_id = session["admin"]

        try:
           
            cur = con.cursor()
            cur.execute(
                "INSERT INTO notes (title, content, user_id) VALUES (%s, %s, %s)", 
                (title, content, user_id)
            )
            con.commit()
            flash("Note added successfully!", "success")

            return redirect(url_for('notes')) 
            
        except Exception as e:
            con.rollback() 
            flash(f"Error saving note: {str(e)}", "danger")
            return redirect(url_for('add_note'))

    return render_template('add_note.html')

@app.route('/notes')
def notes():
    if "admin" not in session:
        flash("Unauthorized access. Please login.", "danger")
        return redirect(url_for('login'))

    user_id = session["admin"]

    try:
       
        cur = con.cursor()
        cur.execute("SELECT id, title, content, created_at FROM notes WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        user_notes = cur.fetchall()
        return render_template('dashboard.html', notes=user_notes)

    except Exception as e:
        flash(f"Could not load notes: {str(e)}", "danger")
        return redirect(url_for('dasboard'))
    
@app.route('/view_note/<int:note_id>')
def view_note(note_id):
    if "admin" not in session: 
        return redirect(url_for('login'))
    
    cur = con.cursor()
    cur.execute("SELECT id,title, content, created_at FROM notes WHERE id = %s AND user_id = %s", (note_id, session["admin"]))
    note = cur.fetchone()
    
    if note:
        return render_template('view_note.html', note=note)
    flash("Note not found!", "danger")
    return redirect(url_for('notes'))


@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    if "admin" not in session: 
        return redirect(url_for('login'))
    cur = con.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        cur.execute("UPDATE notes SET title = %s, content = %s WHERE id = %s AND user_id = %s", 
                    (title, content, note_id, session["admin"]))
        con.commit()
        flash("Note updated!", "success")
        return redirect(url_for('notes'))

    cur.execute("SELECT id, title, content FROM notes WHERE id = %s AND user_id = %s", (note_id, session["admin"]))
    note = cur.fetchone()
    return render_template('edit_note.html', note=note)

@app.route('/delete_note/<int:note_id>')
def delete_note(note_id):
    if "admin" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for('login'))

    user_id = session["admin"]

    try:
        cur = con.cursor()
        
        cur.execute("DELETE FROM notes WHERE id = %s AND user_id = %s", (note_id, user_id))
        
        con.commit()
        
        if cur.rowcount > 0:
            flash("Note deleted successfully!", "success")
        else:
            flash("Note not found or unauthorized.", "danger")

    except Exception as e:
        con.rollback()
        flash(f"Error deleting note: {str(e)}", "danger")

    return redirect(url_for('notes'))
       

if __name__ == '__main__':
    app.run(debug=True)