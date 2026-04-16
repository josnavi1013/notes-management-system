from flask import Flask, request, render_template, url_for, redirect, session, flash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import sqlite3

app = Flask(__name__)
app.secret_key = "mysecretkey"

# Helper function to get SQLite connection
def get_db_connect():
    # This connects to a local file named notedb.db
    conn = sqlite3.connect('notedb.db')
    # This allows accessing columns by name (like a dictionary)
    conn.row_factory = sqlite3.Row
    return conn

# Mail Configuration
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
        
        # Open connection
        db = get_db_connect()
        cur = db.cursor()
        
        # SQLite uses '?' as placeholders instead of '%s'
        cur.execute("SELECT * FROM user WHERE uname=? AND password=?", (uname, pwd))
        user = cur.fetchone()
        
        db.close()

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
    db = get_db_connect()
    # Fetch user details safely
    res = db.execute("SELECT * FROM user WHERE email=?", (email,)).fetchone()
    db.close()

    if not res:
        flash("Email not registered!")
        return redirect('/forgot_password')
    
    # Generate token
    token = s.dumps(email, salt='password-reset-salt')
    link = url_for('reset_password', token=token, _external=True)
    
    msg = Message("Password Reset Request", 
                  sender="josnavidunga@gmail.com",
                  recipients=[email])
    msg.body = f"Click the link to reset your password: {link}"
    mail.send(msg) 
    
    flash("Reset link sent to your email!")
    return redirect(url_for('Home')) # Best practice: redirect after POST

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Token expires in 5 minutes (300 seconds)
        email = s.loads(token, salt='password-reset-salt', max_age=300)  
    except SignatureExpired:
        return "<h1>Link expired!</h1><p>The reset link is only valid for 5 minutes.</p>"
    except BadSignature:
        return "<h1>Invalid Token</h1><p>The reset link has been modified.</p>"
    
    if request.method == 'POST':
        new_password = request.form['password']
        
        db = get_db_connect()
        # FIX 1: Pass the 'email' variable into the query using '?'
        # FIX 2: Commit the changes! SQLite requires commit() for UPDATE/INSERT/DELETE
        db.execute("UPDATE user SET password=? WHERE email=?", (new_password, email))
        db.commit() 
        db.close()
        
        flash("Password reset successful! Please login.")
        return redirect(url_for('Home'))
    
    return render_template("reset_password.html")

@app.route("/reg")
def Reg():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def Register_User():
    uname = request.form['uname']
    pwrd = request.form['pwrd']
    email = request.form['email']
    
    # FIX: Added () to call the function and used db variable
    db = get_db_connect()
    db.execute("INSERT INTO user(uname, email, password) VALUES(?, ?, ?)", 
                (uname, email, pwrd))
    db.commit()
    db.close()
    
    flash("Registration successful!")
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    # FIX: Check if "admin" is in session BEFORE trying to access it
    if "admin" in session:
        user_id = session["admin"]
        db = get_db_connect()
        
        # SQLite uses '?' as placeholder
        notes = db.execute("SELECT * FROM notes WHERE user_id=?", (user_id,)).fetchall()
        db.close()
        
        return render_template("dashboard.html", notes=notes)
    
    flash("Please login first.")
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
            sender=app.config['MAIL_USERNAME'], # Best practice: use your auth email as sender
            recipients=["josnavidunga@gmail.com"],
            reply_to=sender_email # So you can reply directly to the user
        )
        
        msg.body = f"Name: {name}\nEmail: {sender_email}\n\n{message_body}"

        try:
            mail.send(msg)
            flash("Message sent successfully!", "success")
        except Exception as e:
            flash("Failed to send message.", "danger")

        return redirect(url_for('contact'))

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
    if "admin" not in session:
        flash("Please login to add notes.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user_id = session["admin"]

        db = get_db_connect()
        try:
            # SQLite uses '?' instead of '%s'
            db.execute(
                "INSERT INTO notes (title, content, user_id) VALUES (?, ?, ?)", 
                (title, content, user_id)
            )
            db.commit()
            flash("Note added successfully!", "success")
            return redirect(url_for('notes')) 
            
        except Exception as e:
            db.rollback() 
            flash(f"Error saving note: {str(e)}", "danger")
            return redirect(url_for('add_note'))
        finally:
            db.close() # Always close the connection

    return render_template('add_note.html')

@app.route('/notes')
def notes():
    if "admin" not in session:
        flash("Unauthorized access. Please login.", "danger")
        return redirect(url_for('login'))

    user_id = session["admin"]
    db = get_db_connect()

    try:
        # SQLite uses '?' placeholder
        # Note: 'id' in SQLite is usually the PRIMARY KEY
        user_notes = db.execute(
            "SELECT id, title, content, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC", 
            (user_id,)
        ).fetchall()
        
        return render_template('dashboard.html', notes=user_notes)

    except Exception as e:
        flash(f"Could not load notes: {str(e)}", "danger")
        # Fixed typo from 'dasboard' to 'dashboard'
        return redirect(url_for('dashboard'))
    finally:
        db.close()
    
@app.route('/view_note/<int:note_id>')
def view_note(note_id):
    if "admin" not in session: 
        return redirect(url_for('login'))
    
    db = get_db_connect()
    # Changed %s to ? and used the db connection
    note = db.execute(
        "SELECT id, title, content, created_at FROM notes WHERE id = ? AND user_id = ?", 
        (note_id, session["admin"])
    ).fetchone()
    db.close()
    
    if note:
        return render_template('view_note.html', note=note)
    
    flash("Note not found!", "danger")
    return redirect(url_for('notes'))


@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    if "admin" not in session: 
        return redirect(url_for('login'))
    
    db = get_db_connect()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        db.execute(
            "UPDATE notes SET title = ?, content = ? WHERE id = ? AND user_id = ?", 
            (title, content, note_id, session["admin"])
        )
        db.commit()
        db.close()
        flash("Note updated!", "success")
        return redirect(url_for('notes'))

    # GET request: Fetch existing data
    note = db.execute(
        "SELECT id, title, content FROM notes WHERE id = ? AND user_id = ?", 
        (note_id, session["admin"])
    ).fetchone()
    db.close()
    
    return render_template('edit_note.html', note=note)


@app.route('/delete_note/<int:note_id>')
def delete_note(note_id):
    if "admin" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for('login'))

    user_id = session["admin"]
    db = get_db_connect()

    try:
        cur = db.cursor()
        cur.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        db.commit()
        
        if cur.rowcount > 0:
            flash("Note deleted successfully!", "success")
        else:
            flash("Note not found or unauthorized.", "danger")

    except Exception as e:
        db.rollback()
        flash(f"Error deleting note: {str(e)}", "danger")
    finally:
        db.close()

    return redirect(url_for('notes'))


if __name__ == '__main__':
    app.run(debug=True)