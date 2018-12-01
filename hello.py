from functools import wraps
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt

hello = Flask(__name__)

# Config MySQL
hello.config['MYSQL_HOST'] = '192.168.0.102'
hello.config['MYSQL_USER'] = 'fin'
hello.config['MYSQL_PASSWORD'] = 'password'
hello.config['MYSQL_DB'] = 'myflaskapp'
hello.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MySQL
mysql = MySQL(hello)


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please log in!', 'danger')
            return redirect(url_for('login'))
    return wrap


def try_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get('role') == 2:
            return f(*args, **kwargs)
        else:
            flash('You are not an administrator!', 'danger')
            return redirect(url_for('calendar'))
    return wrap


# Home page
@hello.route('/')
def home():
    return render_template('home.html')


# Calendar page
@hello.route('/calendar')
def calendar():
    return render_template('calendar.html')


# Employee page
@hello.route('/employee')
def employee():
    return render_template('employee.html')


# Admin page
@hello.route('/admin')
@is_logged_in
@try_admin
def admin():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Requests
    result = cur.execute("SELECT * FROM requests")

    allrequests = cur.fetchall()

    if result > 0:
        return render_template('admin.html', allrequests=allrequests)
    else:
        msg = 'No Request Found'
        return render_template('admin.html', msg=msg)
    # Close connection
    cur.close()


# Single Request
@hello.route('/request/<string:id>/')
@is_logged_in
def leaverequest(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Request
    result = cur.execute("SELECT * FROM requests WHERE id =%s", [id])

    onerequest = cur.fetchone()

    return render_template('requests.html', onerequest=onerequest)


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm', message='Passwords do not match!')])
    confirm = PasswordField('Confirm Password')


# User Register
@hello.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute Query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in!', 'success')

        return redirect(url_for('calendar'))
    return render_template('register.html', form=form)


# User login
@hello.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']
            role = data['role']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                session['role'] = role

                flash('You are now logged in!', 'success')
                return redirect(url_for('calendar'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found!'
            return render_template('login.html', error=error)

    return render_template('login.html')


# Logout
@hello.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out!', 'success')
    return redirect(url_for('login'))


# Dashboard
@hello.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Requests
    result = cur.execute("SELECT * FROM requests")

    allrequests = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', allrequests=allrequests)
    else:
        msg = 'No Request Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()


# Request Form Class
class RequestForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


# Add Request
@hello.route('/add_request', methods=['GET', 'POST'])
@is_logged_in
def add_request():
    form = RequestForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO requests(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Request created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_request.html', form=form)


# Edit Request
@hello.route('/edit_request/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_request(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get the request by id
    result = cur.execute("SELECT * FROM requests WHERE id = %s", [id])

    onerequest = cur.fetchone()

    # Get form
    form = RequestForm(request.form)

    # Populate request form fields
    form.title.data = onerequest['title']
    form.body.data = onerequest['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE requests SET title=%s, body=%s WHERE id=%s ", (title, body, id))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Request updated!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_request.html', form=form)


# Delete request
@hello.route('/delete_request/<string:id>', methods=['POST'])
@is_logged_in
def delete_request(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM requests WHERE id=%s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Request deleted!', 'success')

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    hello.secret_key = b'jz\x8dB\xf3\xeb\n\xe3\x9f\x9c\xf7\x8e\xc3"\x8d\x13\xf2\xb9\xd8QxQ6\xcf'
    hello.run(debug=True)
