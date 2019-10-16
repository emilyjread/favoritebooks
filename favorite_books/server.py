from flask import Flask, render_template, request, redirect, flash, session
from mysqlconnection import connectToMySQL

app = Flask(__name__)
app.secret_key= "so secret"
import humanize
import datetime

import re
EMAIL_REGEX= re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
PW_REGEX= re.compile(r'^[a-zA-Z.+_-]+[0-9._-]+$')

from flask_bcrypt import Bcrypt        
bcrypt = Bcrypt(app)

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/create", methods=["POST"])
def create():
	valid=True
	mysql=connectToMySQL("favorite_books")
	query=(f"SELECT email FROM users where email= %(email)s")
	data={
	'email': request.form["email"]
	}
	result=mysql.query_db(query, data)
	if result!=False:
		flash("this email is already registered")
		valid= False

	if request.form['pw']!=request.form['pwconf']:
		flash("Passwords do not match!")
		valid=False
	if len(request.form["username"])<5:
		flash("username must be at least 5 characters")
		valid=False
	if len(request.form["fname"])<2:
		flash("Please enter a first name")
		valid=False
	if len(request.form["lname"])<2:
		flash("Please enter a last name")
		valid=False
	if not EMAIL_REGEX.match(request.form["email"]):
		flash("Please enter valid email")
		valid=False
	if not PW_REGEX.match(request.form['pw']):
		flash("Passwords must be at least 8 characters and contain at least one letter and one number")
		valid=False

	if valid==False:
		return redirect("/")
	if valid==True:
		pw_hash = bcrypt.generate_password_hash(request.form['pw'])

		mysql=connectToMySQL("favorite_books")
		query= "INSERT INTO users (username, fname, lname, email, pw, created_at, updated_at) VALUES(%(un)s, %(fn)s, %(ln)s, %(em)s, %(pw)s, now(), now())"
		data= {
			'un':request.form["username"], 
			'fn':request.form["fname"], 
			'ln':request.form["lname"], 
			'em':request.form["email"], 
			'pw':pw_hash
		}
		result=mysql.query_db(query, data)

		session['userid'] = result

		return redirect("/wall")

@app.route("/login", methods=["POST"])
def login():
	mysql=connectToMySQL("favorite_books")
	query=(f"SELECT * FROM users where email= %(email)s")
	data={
	'email': request.form["email"]
	}
	result=mysql.query_db(query, data)
	session['user']=result
	if len(result)>0:
		if bcrypt.check_password_hash(result[0]['pw'], request.form['pw']):
			session['userid'] = result[0]['id']
			return redirect("/wall")
	flash("not valid login credentials")
	return redirect("/")

@app.route("/wall")
def mainpage():
	if 'userid' in session:

		mysql=connectToMySQL("favorite_books")
		query=(f"SELECT username from users where users.id= {session['userid']}")
		user=mysql.query_db(query)

		mysql=connectToMySQL("favorite_books")
		query=(f"select books.id, books.description, uploader_id, username, title from books JOIN users on books.uploader_id= users.id")
		books=mysql.query_db(query)
		

		mysql=connectToMySQL("favorite_books")
		query=(f"select title, books.description, books.id, uploader_id, username, favorites.users_id, favorites.books_id from favorites JOIN users on favorites.users_id= users.id JOIN books ON books.id= favorites.books_id WHERE favorites.users_id={session['userid']}")
		favorites=mysql.query_db(query)
		
		return render_template("user_page.html", user=user, books= books, favorites=favorites)

@app.route("/addbook", methods=["POST"])
def addbook():
	if len(request.form["desc"])<5:
		flash("description must be at least 5 characters")
		return redirect("/wall")
	else:
		mysql=connectToMySQL("favorite_books")
		query="INSERT INTO books (title, description, uploader_id, created_at, updated_at) VALUES (%(title)s, %(desc)s, %(upid)s, now(), now())"
		data={
		'title': request.form["title"],
		'desc': request.form["desc"], 
		'upid': session["userid"]
		}
		bookid= mysql.query_db(query, data)
		mysql=connectToMySQL("favorite_books")
		query="INSERT INTO favorites (users_id, books_id) VALUES (%(user)s, %(book)s)"
		data={
		'user': session["userid"],
		'book': bookid
		}
		mysql.query_db(query, data)
		return redirect("/wall")

@app.route("/addfavorite/<id>", methods=["POST"])
def addfavorite(id):
	mysql=connectToMySQL("favorite_books")
	query="INSERT INTO favorites (users_id, books_id) VALUES (%(user)s, %(book)s)"
	data={
	'user': session["userid"],
	'book': id
	}
	mysql.query_db(query, data)
	return redirect("/wall")

@app.route("/delete/<id>")
def delete(id):
		mysql=connectToMySQL("favorite_books")
		query=(f"SELECT uploader_id from books where books.id={id}")
		uploader=mysql.query_db(query)
		if uploader[0]["uploader_id"]==session['userid']:
			mysql=connectToMySQL("favorite_books")
			query= mysql.query_db(f"DELETE FROM favorites where books_id={id}")

			mysql=connectToMySQL("favorite_books")
			query= mysql.query_db(f"DELETE FROM books where books.id={id}")
		else:
			flash("you cannot delete a book that you did not upload")


		return redirect("/wall")

@app.route("/removefav/<id>")
def removefav(id):
	mysql=connectToMySQL("favorite_books")
	query= mysql.query_db(f"DELETE FROM favorites where books_id={id} and users_id= {session['userid']}")
	return redirect("/wall")
	
@app.route("/books/<id>")
def book(id):

		mysql=connectToMySQL("favorite_books")
		query=(f"SELECT username from users where users.id= {session['userid']}")
		user=mysql.query_db(query)

		mysql=connectToMySQL("favorite_books")
		query=(f"select books.id, uploader_id, username, title, books.created_at, description from books JOIN users on books.uploader_id= users.id where books.id={id}")
		books=mysql.query_db(query)
		

		mysql=connectToMySQL("favorite_books")
		query=(f"select users.fname, users.lname, title, books_id from favorites JOIN users on favorites.users_id= users.id JOIN books ON books.id= favorites.books_id where books_id={id}")
		fans=mysql.query_db(query)
		if books[0]['uploader_id']== session["userid"]:
			return render_template("editbook.html", user=user, books= books, fans=fans)
		else:
			return render_template("book.html", user=user, books= books, fans=fans)

@app.route("/user/<id>")
def user(id):

		mysql=connectToMySQL("favorite_books")
		query=(f"select books.title as title, users.fname as name, books.id as bookid from favorites join users on favorites.users_id= users.id join books on favorites.books_id= books.id where users.id={id}")
		user=mysql.query_db(query)


		return render_template("user.html", users=user)
		


@app.route("/books/books/<id>/update", methods=["POST"])
def update(id):
	if len(request.form["desc"])<5:
		flash("description must be at least 5 characters")
		return redirect("/books/<id>")
	else:
		mysql=connectToMySQL("favorite_books")
		query=(f"UPDATE books SET title= %(title)s, description =%(desc)s, updated_at= now() where books.id={id}")
		data={
		'title': request.form["title"],
		'desc': request.form["desc"],
		}
		mysql.query_db(query, data)
		return redirect(f"/books/{id}")

@app.route("/deletebook/<id>", methods=["POST"])
def deletebook(id):
	mysql=connectToMySQL("favorite_books")
	query= mysql.query_db(f"DELETE FROM favorites where books_id={id}")

	mysql=connectToMySQL("favorite_books")
	query= mysql.query_db(f"DELETE FROM books where books.id={id}")
	return redirect("/wall")
		

		

@app.route("/logout")
def logout():
	session.clear()
	flash("you have been logged out")
	return redirect("/")

if __name__ == "__main__":
	app.run(debug=True)