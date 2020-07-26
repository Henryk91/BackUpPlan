import os

import datetime;
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
import datetime

import threading

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
# app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///findme.db")
# db = SQL("postgres://<password>:<url>/<db>")

# Make sure API key is set
# if not os.environ.get("API_KEY"):
#     raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    """Show reminders of stocks"""
    # cash_balance = get_user_balance()

    # reminders = get_user_reminders() #get_reminders_with_price(True)
    # total = total_value(cash_balance)

    checkin_id = request.args.get('checkin')
    if checkin_id:
        checkin_reminder(checkin_id)
        print(checkin_id)

    stop_id = request.args.get('stop')
    if stop_id:
        stop_reminder(stop_id)
        print(stop_id)

    reminders = get_user_reminders()

    msg = session["msg"]
    session["msg"] = ''
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # time_now = datetime.datetime.strptime(time_now, '%Y-%m-%d %H:%M:%S')
    return render_template("index.html", reminders=reminders, message=msg, time_now=time_now)


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create shares of stock"""
    if request.method == "POST":
        interval = int(request.form.get("interval"))
        if interval < 1:
            return apology('Time interval should be higher than 0')
        else:
            print(request.form.get("name"))
            print("Reminder CHeck here")
            print(request.form.get("reminder_id"))
            reminder_id = request.form.get("reminder_id")
            if reminder_id:
                current_date_and_time = datetime.datetime.now()
                minutes_added = datetime.timedelta(minutes = interval)
                next_expiration = current_date_and_time + minutes_added
                update_reminder_by_id(interval, request.form.get("details"), next_expiration, request.form.get("contacts"), request.form.get("name"), reminder_id)

            else:

                # Make call to create
                msg = create_reminder(request.form.get("details"), interval, request.form.get("name"), request.form.get("contact"))
                if msg == 'Insufficient funds' :
                    return apology('Insufficient funds')
                elif msg:
                    session["msg"] = msg
                    return redirect("/")
                    # return render_template("index.html", message=msg)
                else:
                    return apology("Unknown Symbol")

            # Then Redirect user to home page
            return redirect("/")
    else:
        # Get details if the query has one
        reminder_id = request.args.get('id')
        if reminder_id:
            reminder = get_user_reminder_by_id(reminder_id)
            if reminder:
                print(reminder)
                # return render_template("create.html",  details=reminder['details'], contacts=contacts)
                return render_template("create.html", interval=int(reminder['interval']), name=reminder['name'], details=reminder['details'], contacts=reminder['contacts'], reminder_id=reminder_id)
            else:
                return render_template("create.html")
        else:
            return render_template("create.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "POST":
        return apology("TODO")
    else:
        transactions = get_user_history()
        result=list(reversed(transactions))
        return render_template("history.html", transactions=result)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["msg"] = ''


        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        stock_value = lookup(request.form.get("details"))
        if stock_value:
            msg = 'A share of ' + stock_value['name'] + ' (' + stock_value['details'] + ') costs $' + str(stock_value['price'])
            return render_template("quoted.html", price=msg)
        else:
            return apology("Quote error:")
        # return render_template("quote.html")
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        # Endure pass and confirm is the same
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords don't match", 403)

        # Check if user exists
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) > 0:
            return apology("Username already exists", 403)

        # Insert new user in database
        db.execute("INSERT INTO users (username, hash) VALUES (:username,:hash)", username=request.form.get("username"), hash= generate_password_hash(request.form.get("password")))

        # Redirect user to Login
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Gets user current stock
    stocks = get_user_reminders()

    if request.method == "POST":
        interval = int(request.form.get("shares"))
        details = request.form.get('details')

        if interval < 1:
            return apology('Amount should be higher than 0')
        elif details != '-1':
            # Make call to sell
            sell_count = int(request.form.get('shares'))
            index = int(request.form.get('details')) - 1
            owned_count = stocks[index]['interval']
            details = stocks[index]['details']

            # check if user can sell stock interval
            if owned_count >= sell_count:
                # Sell shares
                stock_value = lookup(details)
                make_trade(stock_value, interval, request.form.get('name'), 'sell', 'contact')
                session["msg"] = 'Sold!' # msg
            else:
                msg = "You have " + str(owned_count) + " shares of " + details
                return apology(msg)
            # Then Redirect user to home page
            return redirect("/")
        else:
            # User didnt select anything
            return apology("Missing Symbol")
    else:
        # Get method
        details = request.args.get('details')
        if details:
            # Sympol form quick sell on main page
            return render_template("sell.html", stocks=stocks, details=details)
        else:
            return render_template("sell.html", stocks=stocks)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Get user profile"""
    user = get_user()
    contacts = ['test@mailinator.com', 'test@mailinator.com']
    if request.method == "POST":
        msg =  update_user(request)
        if msg == 'Profile Updated!':
            return redirect("/")
        else:
            # Error Msg
            return apology(msg)

    else:
        return render_template("profile.html", username=user['username'], contacts=contacts)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


# Create stock
def create_reminder(details, interval, reminder_name, contact):
    stock_value = 1 #lookup(request.form.get("details"))
    if stock_value:
        print("Creating here")
        # Did get a response from lookup
        trade_msg =  make_trade(details, interval, reminder_name, 'create', contact)
        if trade_msg:
            return trade_msg
        return "Added Reminder!"
    else:
        return

# Get user data
def get_user():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM users WHERE id = :user_id",user_id=user_id)
    if len(rows) <= 0:
            return
    else:
        return rows[0]

# Update user data
def update_user(request):
    user_id = session["user_id"]
    user_hash = generate_password_hash(request.form.get("password"))
    new_username = request.form.get("new_username")

    new_detail = request.form.get("details")

    new_pass = request.form.get("new-password")
    new_confirm = request.form.get("new-confirm")

    user_rows = db.execute("SELECT * FROM users WHERE id = :user_id",user_id=user_id)

    # Ensure username exists and password is correct
    if len(user_rows) != 1 or not check_password_hash(user_rows[0]["hash"], request.form.get("password")):
        return apology("invalid password", 403)

    if new_pass:
        # Updating password
        if new_pass == new_confirm:
            # Update passwords
            row = db.execute("UPDATE users SET username=:new_username, hash=:new_pass WHERE id = :user_id", new_username=new_username  ,user_id=user_id, new_pass=generate_password_hash(new_pass))

            session["msg"] = 'Profile Updated!'
            return 'Profile Updated!'
        else:
            # Password Mismatch
            return "Passwords don't match"
    else:
        # Updating only username
        row = db.execute("UPDATE users SET username=:username, detail=:new_detail WHERE id=:user_id", username=new_username, detail=new_detail ,user_id=user_id)
        session["msg"] = 'Profile Updated!'

        return 'Profile Updated!'

# Get user balance
def get_user_balance():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM users WHERE id = :user_id",user_id=user_id)
    if len(rows) <= 0:
            return
    else:
        return rows[0]['cash']

# Save user balance
def set_user_balance(user_id, user_balance):
    db.execute("UPDATE users SET cash=:balance WHERE id = :user_id", balance=user_balance  ,user_id=user_id)

# Create stock
def make_trade(reminder_details, interval, reminder_name, trade_type,contact):

    balance = 10000 #get_user_balance()
    price = 5 #stock_value['price']
    if balance:
        details = reminder_details #tock_value['details']
        user_id = session["user_id"]
        if trade_type == 'create':

            if True: # can_create_check(balance, price, interval):
                # User can create shares
                add_to_history(details, user_id, price,reminder_name, interval,  trade_type, contact)
                # post_trade_balance = balance - (price * interval)
                # set_user_balance(user_id,post_trade_balance)
                return
            else:

                # Insufficient funds
                return "Insufficient funds"
        else:
            # Selling shares
            add_to_history(details, user_id, price, reminder_name, interval, trade_type, contact)
            # post_trade_balance = balance + (price * interval)
            # set_user_balance(user_id, post_trade_balance)
    else:
        return "DB error"

# Check if user has enough funds
def can_create_check(user_balance, price, interval):
    if (price * interval ) < user_balance:
        return True
    else:
        return False

# Save trade to log
def add_to_history(details, user_id, stock_price, reminder_name, interval, trade_type, contact):

    # Insert trade in history table
    db.execute("INSERT INTO history (name, details, user_id, stock_price, interval, trade_type) VALUES (:name, :details, :user_id, :stock_price, :interval, :trade_type)", name=reminder_name,details=details,user_id=user_id, stock_price=stock_price,  interval=interval, trade_type=trade_type)

    update_user_reminders(reminder_name, details, user_id, stock_price, interval, trade_type, contact)

# Get user history
def get_user_history():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM history WHERE user_id = :user_id",user_id=user_id)
    if len(rows) <= 0:
            return [{'stock_price': '','details': '', 'interval':'', 'timestamp':'', 'trade_type': ''}]
    else:
        # User has history
        return rows

# get reminders
def get_user_reminders():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM reminders WHERE user_id = :user_id AND interval > 0;",user_id=user_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:

        create_remaining_time(rows)
        return create_remaining_time(rows)

# Adding remaining time to reminder
def create_remaining_time(rows):
    if rows:
        for reminder in rows:
            next_expiration = reminder['next_expiration']
            time_exp = datetime.datetime.strptime(next_expiration, '%Y-%m-%d %H:%M:%S')
            time_now = datetime.datetime.now()
            remaining_time = time_exp - time_now

            if remaining_time > datetime.timedelta(0):
                remaining_time = str(remaining_time)
                reminder['remaining_time'] = remaining_time[0:remaining_time.index('.')]
                reminder['runout'] = False
            else:
                remaining_time = str(time_now - time_exp)
                reminder['remaining_time'] = remaining_time[0:remaining_time.index('.')]
                reminder['runout'] = True

    return rows

# get reminders
def get_user_reminder_by_id(reminder_id):
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM reminders WHERE user_id = :user_id AND id = :reminder_id;",user_id=user_id, reminder_id=reminder_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        return rows[0]

# get port with current prices
def get_reminders_with_price(with_usd_format):
    reminders = get_user_reminders()
    for reminder in reminders:
        if reminder['details'] != '':
            # Stock isnt empty
            #reminder_value = #lookup(reminder["details"])
            # reminder['name'] = reminder_value['name']

            if with_usd_format:
                # Returns with values formatted for ui
                reminder['price'] = 1 #usd(reminder_value['price'])
                reminder['total'] = 1 #usd((reminder['interval']) * reminder_value['price'])
            else:
                # Returns with numerical values
                reminder['price'] = 1 #reminder_value['price']
                reminder['total'] = 1 #(reminder['interval']) * reminder_value['price']

    return reminders

# update reminders
def update_user_reminders(reminder_name, details, user_id, stock_price, interval, trade_type, contact):

    # check if stock is in reminders
    rows = db.execute("SELECT * FROM reminders WHERE user_id = :user_id AND details = :details",user_id=user_id, details=details)

    if rows:
        # Update reminders
        reminder_data = rows[0]
        new_count = interval
        print(reminder_data)

        db.execute("UPDATE reminders SET interval=:interval WHERE user_id = :user_id AND id=:reminder_id", interval=new_count  ,user_id=user_id, reminder_id=reminder_data['id'])
    else:
        current_date_and_time = datetime.datetime.now()
        minutes_added = datetime.timedelta(minutes = interval)
        next_expiration = current_date_and_time + minutes_added

        # insert into reminders
        db.execute("INSERT INTO reminders (name, details, user_id, interval, start_time, next_expiration, contacts) VALUES (:name, :details, :user_id, :interval, :start_time, :next_expiration, :contact)", name=reminder_name  ,details=details,user_id=user_id, interval=interval, start_time=current_date_and_time, next_expiration=next_expiration, contact=contact)


# update reminders
def update_reminder_by_id(interval, details, next_expiration, contacts, name, reminder_id):
# 	details
# 	interval
# 	next_expiration
# 	end_time
# 	contacts
# 	name
    # check if stock is in reminders
    db.execute(
        "UPDATE reminders SET interval=:interval, details=:details, next_expiration=:next_expiration, contacts=:contacts, name=:name WHERE id=:reminder_id",
        interval=interval,
        details=details,
        next_expiration=next_expiration,
        contacts=contacts,
        name=name,
        reminder_id=reminder_id
        )

# checking in reminders
def checkin_reminder(reminder_id):
    # get reminders interval
    rows = db.execute("SELECT interval FROM reminders WHERE id = :reminder_id",reminder_id=reminder_id)
    if rows:
        interval = rows[0]['interval']
        print('Interval')
        print(interval)
        current_date_and_time = datetime.datetime.now()
        minutes_added = datetime.timedelta(minutes = interval)
        next_expiration = current_date_and_time + minutes_added
        print(next_expiration)
        db.execute(
            "UPDATE reminders SET next_expiration=:next_expiration WHERE id=:reminder_id",
            reminder_id=reminder_id,
            next_expiration=next_expiration
            )

# update reminders
def stop_reminder(reminder_id):
    end_time = datetime.datetime.now()
    # Stop query
    db.execute("UPDATE reminders SET end_time=:end_time WHERE id=:reminder_id", end_time=end_time, reminder_id=reminder_id)

# Get user total asset value
def total_value(cash_balance):
    stocks = get_reminders_with_price(False)
    ret_val = cash_balance

    for stock in stocks:
        if stock['details'] != '':
            # Add value of stock
            ret_val = ret_val + stock['total']

    return ret_val

# Check if there is a late reminder 
def reminder
    print("hello, world")
def timer_engine():
    print("hello, world")
    reminder_timer()

# timeout for interval checking
def reminder_timer():
  threading.Timer(5.0, timer_engine).start()

reminder_timer()