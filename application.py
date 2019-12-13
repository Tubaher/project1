""" Universidad Yachay Tech
Diego Hernán Suntaxi Domínguez
Curso de Web Programming
Prof. Rigoberto Fonseca  
 """
import os
import requests
from helpers import login_required

from flask import Flask, session, redirect, render_template, request, flash, jsonify, make_response
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    #Search box
    r = make_response(render_template("index.html"))
    #r.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r


@app.route("/login", methods=["GET", "POST"])
def login():
    # Login Page

    session.clear()

    username = request.form.get("username")

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": username})
        
        result = rows.fetchone()

        if result == None or not (result[1] == request.form.get("password")):
            return render_template("error.html", message="invalid username and/or password")

        session["user_id"] = result[0]

        r = make_response(redirect("/"))
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return r
    
    else:
        r = make_response(render_template("login.html"))
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return r

@app.route("/logout")
def logout():

    session.clear()

    r = make_response(redirect("/"))
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        # Query database for username
        userCheck = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Check if username already exist
        if userCheck:
            return render_template("error.html", message="username already exist")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        # Ensure confirmation wass submitted 
        elif not request.form.get("confirmation"):
            return render_template("error.html", message="must confirm password")

        # Check passwords are equal
        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message="passwords didn't match")
        
        # Insert register into DB
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                            {"username":request.form.get("username"), 
                             "password":request.form.get("password")})

        # Commit changes to database
        db.commit()

        flash('Account created', 'info')

        # Redirect user to login page
        r = make_response(redirect("/login"))
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return r

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        r = make_response(render_template("register.html")) 
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return r

@app.route("/search", methods=["GET"])
@login_required
def search():
    """ Get books results """

    # Check book id was provided
    if not request.args.get("book"):
        return render_template("error.html", message="you must provide a book.")

    # Take input and add a wildcard
    query = "%" + request.args.get("book") + "%"

    # Capitalize all words of input for search
    # https://docs.python.org/3.7/library/stdtypes.html?highlight=title#str.title
    query = query.title()
    
    rows = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR \
                        author LIKE :query LIMIT 15",
                        {"query": query})
    
    # Books not founded
    if rows.rowcount == 0:
        return render_template("error.html", message="we can't find books with that description.")
    
    # Fetch all the results
    books = rows.fetchall()
    r = make_response(render_template("results.html", books=books))
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return r
@app.route("/book/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    """ Save user review and load same page with reviews updated."""

    if request.method == "POST":

        # Save current user info
        currentUser = session["user_id"]
        
        # Fetch form data
        rating = request.form.get("rating")
        opinion = request.form.get("comment")
        

        # Check for user submission (ONLY 1 review/user allowed per book)
        row = db.execute("SELECT * FROM reviews WHERE username = :username AND isbn = :isbn",
                    {"username": currentUser,
                     "isbn": isbn})

        # A review already exists
        if row.rowcount == 1:
            
            flash('You already submitted a review for this book', 'warning')
            return redirect("/book/" + isbn)

        # Convert to save into DB
        rating = int(rating)

        db.execute("INSERT INTO reviews (username, isbn, rating, opinion) VALUES \
                    (:username, :isbn, :rating, :opinion)",
                    {"username": currentUser, 
                    "isbn": isbn, 
                    "rating": rating, 
                    "opinion": opinion})

        # Commit transactions to DB and close the connection
        db.commit()

        flash('Review submitted!', 'info')
        r = make_response(redirect("/book/" + isbn))
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        return r
    
    # Take the book ISBN and redirect to his page (GET)
    else:

        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})

        bookInfo = row.fetchall()

        """ GOODREADS reviews """

        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")
        
        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

        # Convert the response to JSON
        response = query.json()

        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

        # Append it as the second element on the list. [1]
        bookInfo.append(response)

        """ Users reviews """

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)
        results = db.execute("SELECT users.username, rating, opinion \
                            FROM users \
                            INNER JOIN reviews \
                            ON users.username = reviews.username \
                            WHERE reviews.isbn = :isbn",
                            {"isbn": isbn})

        reviews = results.fetchall()

        r = make_response(render_template("book.html", bookInfo=bookInfo, reviews=reviews))
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        return r

@app.route("/api/<isbn>", methods=['GET'])
def api_call(isbn):

    # COUNT returns rowcount
    # SUM returns sum selected cells' values
    # INNER JOIN associates books with reviews tables

    row = db.execute("SELECT * \
                    FROM books\
                    WHERE isbn = :isbn",
                    {"isbn": isbn})
    
    if row.rowcount != 1:
        return jsonify({"Error": "Invalid book ISBN"}), 404

    row = db.execute("SELECT title, author, year, books.isbn, \
                    COUNT(reviews.username) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.isbn = reviews.isbn \
                    WHERE books.isbn = :isbn \
                    GROUP BY title, author, year, books.isbn",
                    {"isbn": isbn})

    # Error checking
    if row.rowcount != 1:
        return jsonify({"Error": "ISBN with not reviews yet"}), 404

    # Fetch result from RowProxy    
    tmp = row.fetchone()

    # Convert to dict
    result = dict(tmp.items())

    # Round Avg Score to 2 decimal. This returns a string which does not meet the requirement.
    # https://floating-point-gui.de/languages/python/
    result['average_score'] = float('%.2f'%(result['average_score']))

    r = make_response(jsonify(result))
    return r
