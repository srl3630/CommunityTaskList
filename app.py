from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Tasks
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from os import urandom
from functools import wraps
import uuid

app = Flask(__name__)

# MYSQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'hunter732'
app.config['MYSQL_DB'] = 'TaskApp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# Start MYSQL
mysql = MySQL(app)

def is_logged_in(f):
			@wraps(f)
			def wrap(*args, **kwargs):
				if 'logged_in' in session:
					return f(*args, **kwargs)
				else:
					flash("Unauthorized, please login", 'danger')
					return redirect(url_for('login'))
			return wrap

def is_logged_out(f):
			@wraps(f)
			def wrap(*args, **kwargs):
				if 'logged_in' in session:
					flash("You are already logged in", 'danger')
					return redirect(url_for('dashboard'))
				else:
					return f(*args, **kwargs)
			return wrap

def is_admin(f):
			@wraps(f)
			def wrap(*args, **kwargs):
				if 'logged_in' in session:
					cur = mysql.connection.cursor()
					cur.execute("SELECT admin FROM users WHERE username = %s", (session['username'], ))
					result = cur.fetchone()
					if(result['admin']):
						return f(*args, **kwargs)
					else:
						flash("Unauthorized", 'danger')
						return redirect(url_for('dashboard'))

				else:
					flash("Unauthorized, please login", 'danger')
					return redirect(url_for('login'))
			return wrap


Tasks = Tasks()
@app.route('/')
def index():
	return render_template('home.html')
@app.route('/about')
def about():
	return render_template('about.html')
@app.route('/tasks')
@is_logged_in
def tasks():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM ActiveTasks where done=0"
	cur.execute(sql)
	result = cur.fetchall()
	if len(result) > 0:
			return render_template('tasks.html', tasks=result)
	else:
		msg = "No tasks"
		return render_template('tasks.html', msg=msg)
@app.route('/view_feedback')
@is_admin
def view_feedback():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM feedback"
	cur.execute(sql)
	result = cur.fetchall()
	if len(result) > 0:
			return render_template('view_feedback.html', tasks=result)
	else:
		msg = "No tasks"
		return render_template('view_feedback.html', msg=msg)

@app.route('/view_feedback/<string:id>/')
@is_admin
def  view_some_feedback(id):
		cur = mysql.connection.cursor()
		sql = "SELECT * FROM feedback WHERE id = %s"
		adr = ([id], )
		cur.execute(sql, adr)
		result = cur.fetchone()
		app.logger.info(result)
		return render_template('task.html', task=result)



@app.route('/approve_tasks')
@is_logged_in
def approve_tasks():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM ActiveTasks where done=1 and approved='nohbody'"
	cur.execute(sql)
	result = cur.fetchall()
	if len(result) > 0:
			return render_template('approve_tasks.html', tasks=result, username=session['username'])
	else:
		msg = "No tasks"
		return render_template('approve_tasks.html', msg=msg)

@app.route('/approve_task/<string:id>')
@is_logged_in
def approve_task(id):
			cur = mysql.connection.cursor()
			cur.execute("SELECT * FROM ActiveTasks WHERE id = %s and done = 1 and approved = 'nohbody'", ([id], ))

			# commit to db
			result = cur.fetchone()
			cur.close()
			if len(result) > 0:
				if not result['claimer']==session['username']:
					cur = mysql.connection.cursor()
					cur.execute("UPDATE ActiveTasks SET approved = %s WHERE id = %s", (session['username'],[id] ))

					# commit to db
					mysql.connection.commit()
					cur.close()
					cur = mysql.connection.cursor()
					cur.execute("UPDATE users SET score = score + 1 WHERE username=%s",(result['claimer'], ))

					# commit to db
					mysql.connection.commit()
					cur.close()
					flash("You have approved the task, \""+ result['taskname']+"\" thanks!")
					return redirect(url_for('approve_tasks'))
				else:
					flash("You can't approve your own task >:(")
					return redirect(url_for('approve_tasks'))
			else:
				flash("That does task is not up for approval or does not exist")
				return redirect(url_for('approve_tasks'))
			return redirect(url_for('approve_tasks'))

@app.route('/leaderboard')
@is_logged_in
def leaderboard():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM users ORDER BY score DESC"
	cur.execute(sql)
	result = cur.fetchall()
	if len(result) > 0:
			return render_template('LeaderBoard.html', users=result, username=session['username'])
	else:
		msg = "No users"
		return render_template('LeaderBoard.html', msg=msg)



@app.route('/done_task/<string:id>')
@is_logged_in
def done_task(id):
			cur = mysql.connection.cursor()
			cur.execute("SELECT * FROM ActiveTasks WHERE id = %s and done = 0 and claimer IS NOT NULL ", ([id], ))

			# commit to db
			result = cur.fetchone()
			cur.close()
			if len(result) > 0:
				if result['claimer'] == session['username']:
						cur = mysql.connection.cursor()
						cur.execute("UPDATE ActiveTasks SET done = 1 WHERE id = %s", ([id] ))

						# commit to db
						mysql.connection.commit()
						cur.close()
						flash("You have finshed the task, "+ result['taskname']+" it has been put up for approval")
						return redirect(url_for('approve_tasks'))
				else:
						flash("You did not claim this task and cannot mark it as done")

			else:
				return redirect(url_for('approve_tasks'))
			return redirect(url_for('approve_tasks'))

@app.route('/task/<string:id>/')
@is_logged_in
def  task(id):
		cur = mysql.connection.cursor()
		sql = "SELECT * FROM ActiveTasks WHERE id = %s"
		adr = ([id], )
		cur.execute(sql, adr)
		result = cur.fetchone()
		app.logger.info(result)
		return render_template('task.html', task=result)

class RegisterForm(Form):
	"""docstring for RegisterForm"""
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50 )])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwors do not match')
		])
	confirm = PasswordField('Confirm Password')

def tasks():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM ActiveTasks"
	cur.execute(sql)
	result = cur.fetchall()
	if len(result) > 0:
			return render_template('tasks.html', tasks=result)
	else:
		msg = "No tasks"
		return render_template('tasks.html', msg=msg)


@app.route('/register', methods=['GET','POST'])
@is_logged_out
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))
		# make cursor
		cur = mysql.connection.cursor()
		cur.execute("SELECT username from users where username=%s OR email=%s",(username,email))
		# commit to db
		if cur.rowcount!=0:
			flash('That user is already registered', 'danger')
			cur.close()
			return redirect(url_for('register'))
		cur.close()
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

		# commit to db
		mysql.connection.commit()
		cur.close()

		flash('you are now registered and can login', 'success')

		return redirect(url_for('index'))



		
	return render_template('register.html', form=form)
@app.route('/login', methods=['GET','POST'])
@is_logged_out
def login():
		if request.method == 'POST':
			username = request.form['username']
			password_candidate = request.form['password']
			cur = mysql.connection.cursor()
			result = cur.execute("SELECT * from users where username=%s ",([username]))
			# commit to db
			if result > 0:
				data = cur.fetchone()
				app.logger.info(data)
				password =  data['password']
				if sha256_crypt.verify(password_candidate, password):
					#Passed
					session['logged_in'] = True
					session['username'] = username
					flash('You are now logged in', 'success')
					cur.close()
					return redirect(url_for('dashboard'))
				else:
					error = 'Username does not exist or password is wrong'
					cur.close()
					return render_template("login.html", error=error)
			else:
				error = 'Username does not exist or password is wrong'
				cur.close()
				return render_template("login.html", error=error)
		return render_template("login.html")

@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM ActiveTasks WHERE claimer = %s"
	adr = (session['username'], )
	cur.execute(sql, adr)
	result = cur.fetchall()
	sql = "SELECT * FROM ActiveTasks WHERE author = %s"
	adr = (session['username'], )
	cur.execute(sql, adr)
	tasks = cur.fetchall()
	cur.close()
	if len(result) > 0:
			return render_template('dashboard.html', mytasks=result, tasks=tasks)
	else:
		msg = "No tasks taken"
		return render_template('dashboard.html', msg=msg)

@app.route('/done_tasks')
@is_logged_in
def done_tasks():
	cur = mysql.connection.cursor()
	sql = "SELECT * FROM ActiveTasks where approved != 'nohbody' ORDER BY create_date DESC"
	cur.execute(sql)
	result = cur.fetchall()
	cur.close()
	if len(result) > 0:
			return render_template('done_tasks.html', mytasks=result, tasks=tasks)
	else:
		msg = "No tasks succesfully completed"
		return render_template('done_tasks.html', msg=msg)

class TaskForm(Form):
	"""docstring for TaskForm"""
	title = StringField('Title', [validators.Length(min=1, max=200)])
	body = TextAreaField('Body', [validators.Length(max=500)])
			
@app.route('/add_task', methods=['GET', 'POST'])
@is_logged_in
def add_task():
	form = TaskForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO ActiveTasks(taskname, body, author) VALUES(%s,%s,%s)",(title,body,session['username']))
		mysql.connection.commit()
		cur.close()
		flash('Article Created', 'success')
		return redirect(url_for('tasks'))
	return render_template('add_task.html', form=form)

@app.route('/give_feedback', methods=['GET', 'POST'])
@is_logged_in
def give_feedback():
	form = TaskForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO feedback(title, body, author) VALUES(%s,%s,%s)",(title,body,session['username']))
		mysql.connection.commit()
		cur.close()
		flash('Feedback Received', 'success')
		return redirect(url_for('give_feedback'))
	return render_template('give_feedback.html', form=form)

@app.route('/edit_task/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_task(id):
	form = TaskForm(request.form)
	cur = mysql.connection.cursor()
	cur.execute("select * from ActiveTasks where id = %s",([id],))
	task = cur.fetchone()
	cur.close()
	form.title.data = task['taskname'] 
	form.body.data = task['body']
	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']
		cur = mysql.connection.cursor()
		cur.execute("UPDATE ActiveTasks set taskname = %s, body = %s where id = %s",(title,body,[id]))
		mysql.connection.commit()
		cur.close()
		flash('Article Edited', 'success')
		return redirect(url_for('tasks'))
	return render_template('add_task.html', form=form)
@app.route('/claim_task/<string:id>')
@is_logged_in
def claim_task(id):
		cur = mysql.connection.cursor()
		cur.execute("UPDATE ActiveTasks SET claimer = %s WHERE id = %s", (session['username'],[id] ))

		# commit to db
		mysql.connection.commit()
		cur.close()
		flash("You have claimed this task, thanks!")
		return redirect(url_for('tasks'))

@app.route('/unclaim_task/<string:id>')
@is_logged_in
def unclaim_task(id):
		cur = mysql.connection.cursor()
		cur.execute("UPDATE ActiveTasks SET claimer = NULL WHERE id = %s", ([id], ))

		# commit to db
		mysql.connection.commit()
		cur.close()
		flash("You have unclaimed this task, :(")
		return redirect(url_for('dashboard'))

@app.route('/delete_task/<string:id>/')
@is_logged_in
def  delete_task(id):
		cur = mysql.connection.cursor()
		cur.execute("SELECT taskname from ActiveTasks where id = %s AND author = %s", ([id], session['username']))

		# commit to db
		result = cur.fetchone()
		cur.close()
		if len(result) == 1:
			cur = mysql.connection.cursor()
			cur.execute("DELETE from ActiveTasks where id = %s AND author = %s", ([id], session['username']))

			# commit to db
			mysql.connection.commit()
			cur.close()
			app.logger.info(result)
			flash("You have deleted task, "+result['taskname']+"!")
		else:
			flash("You either did not create the task or the task does not exist")
		return redirect(url_for('dashboard'))



if __name__ == '__main__':
	app.secret_key="ServeMeOutsideHowBoutFlask"
	app.run(host='0.0.0.0',port=5000)
