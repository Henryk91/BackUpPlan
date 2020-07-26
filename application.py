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

import requests

import threading

import array

# reminder_timer_itm = ''
# reminder_timer_itm['next_expiration'] = '2030-07-18 17:18:20'
# reminder_timer_itm['reminder_is'] = -1
reminder_timer_array = []

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

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# app.debug = True
Session(app)

# Configure CS50 Library to use SQLite database
db_link = "sqlite:///findme.db"
db = SQL(db_link)
# db = SQL("postgres://<password>:<url>/<db>")

@app.route("/")
@login_required
def index():
    """Show active plans"""
    checkin_id = request.args.get('checkin')
    if checkin_id:
        checkin_reminder(checkin_id)

    stop_id = request.args.get('stop')
    if stop_id:
        # threading.Timer(1.0, test_email).start()
        stop_reminder(stop_id)

    reminders = get_user_active_reminders()

    msg = session["msg"]
    session["msg"] = ''
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # time_now = datetime.datetime.strptime(time_now, '%Y-%m-%d %H:%M:%S')

    return render_template("index.html", reminders=reminders, message=msg, time_now=time_now)




@app.route("/plan", methods=["GET", "POST"])
@login_required
def create():
    """Create shares of stock"""
    if request.method == "POST":
        print('Post on create route')
        interval = int(request.form.get("interval"))
        reminder_name = request.form.get("name")
        details = request.form.get("details")
        user_id = session["user_id"]
        contacts = request.form.get("contacts")
        if interval < 1:
            return apology('Time interval should be higher than 0')
        else:
            reminder_id = request.form.get("reminder_id")
            if reminder_id:
                current_date_and_time = datetime.datetime.now()
                minutes_added = datetime.timedelta(minutes = interval)
                next_expiration = current_date_and_time + minutes_added
                next_expiration = next_expiration.strftime("%Y-%m-%d %H:%M:%S")
                update_reminder_by_id(interval, details, next_expiration, contacts, reminder_name, reminder_id)
            else:
                print('Creating new reminder')
                # Make call to create

                msg = create_user_reminder(reminder_name, details, user_id, interval, contacts)
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
        reuse = request.args.get('reuse')
        if reminder_id or reuse:
            reminder_id = reminder_id if reminder_id else reuse
            reminder = get_user_reminder_by_id(reminder_id)
            if reminder:
                reminder_id = None if reuse else reminder_id
                return render_template("plan.html", interval=int(reminder['interval']), name=reminder['name'], details=reminder['details'], contacts=reminder['contacts'], reminder_id=reminder_id)
            else:
                return render_template("plan.html")
        else:
            return render_template("plan.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "POST":
        return apology("TODO")
    else:
        reminders = get_user_reminders()

        return render_template("history.html", reminders=reminders)

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

# test email function
def test_email():
    # https://henryk91-note.herokuapp.com/api/email
    url = 'https://henryk91-note.herokuapp.com/api/emails'
    # myobj = {'email': 'bob@mailinator.com', 'text' : 'FFs Message missing.'}
    myobj = {'from': 'live@henryk.co.za', 'to': ['henry@mailinator.com', 'bob@mailinator.com'], 'subject': 'Live Switch', 'text': 'FFs Message missing.'}
    x = requests.post(url, data = myobj)
    #print the response text (the content of the requested file):
    print(x.text)

# test email function
def email_contacts(to, subject, text):
    print('About to send email to:', to)
    # https://henryk91-note.herokuapp.com/api/email
    url = 'https://henryk91-note.herokuapp.com/api/emails'
    # myobj = {'email': 'bob@mailinator.com', 'text' : 'FFs Message missing.'}
    myobj = {'from': 'mail@henryk.co.za', 'to': to, 'subject': subject, 'text': text}
    print('Email obj:', myobj)
    x = requests.post(url, data = myobj)
    #print the response text (the content of the requested file):
    # print(x.text)
    print('Email sent')

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

# get reminders for timer
def get_timer_reminders():
    print('Loading timers from db')
    global reminder_timer_array
    global db_link
    db = SQL(db_link)

    rows = db.execute("SELECT next_expiration, id as reminder_id FROM reminders WHERE end_time IS NULL AND notify_time IS NULL")
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        rows.sort(key = lambda x: datetime.datetime.strptime(x['next_expiration'], '%Y-%m-%d %H:%M:%S'))
        reminder_timer_array = rows

# get user active reminders
def get_user_active_reminders():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM reminders WHERE user_id = :user_id AND end_time IS NULL",user_id=user_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        # Sort by latest first
        rows.sort(key = lambda x: datetime.datetime.strptime(x['next_expiration'], '%Y-%m-%d %H:%M:%S'))
        return create_remaining_time(rows)

# get user reminders
def get_user_reminders():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM reminders WHERE user_id = :user_id AND interval > 0;",user_id=user_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        # Sort by latest first
        rows.sort(key = lambda x: datetime.datetime.strptime(x['start_time'], '%Y-%m-%d %H:%M:%S'))
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

# get reminder by id with user check so user cant call any reminder
def get_user_reminder_by_id(reminder_id):
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM reminders WHERE user_id = :user_id AND id = :reminder_id;",user_id=user_id, reminder_id=reminder_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        return rows[0]

# get reminder by id withouth user check for use on notify. (recreating db as function is called in seperate thread)
def get_reminder_by_id_with_sql_create(reminder_id):
    global db_link
    db = SQL(db_link)

    rows = db.execute("SELECT * FROM reminders WHERE id = :reminder_id;", reminder_id=reminder_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        return rows[0]

# get reminder by id withouth user check for use on notify. (recreating db as function is called in seperate thread)
def get_user_by_id_with_sql_create(user_id):
    global db_link
    db = SQL(db_link)

    rows = db.execute("SELECT username FROM users WHERE id = :user_id",user_id=user_id)
    if len(rows) <= 0:
            return [{'details': '', 'interval': 0}]
    else:
        return rows[0]

# create reminder
def create_user_reminder(reminder_name, details, user_id, interval, contacts):
    print('Creating user reminder with user id:', user_id)

    current_date_and_time = datetime.datetime.now()
    minutes_added = datetime.timedelta(minutes = interval)
    next_expiration = current_date_and_time + minutes_added

    # insert into reminders
    db.execute("INSERT INTO reminders (name, details, user_id, interval, start_time, next_expiration, contacts) VALUES (:name, :details, :user_id, :interval, :start_time, :next_expiration, :contacts)", name=reminder_name  ,details=details,user_id=user_id, interval=interval, start_time=current_date_and_time, next_expiration=next_expiration, contacts=contacts)

    return 'Reminder created'
# update reminders
def update_reminder_by_id(interval, details, next_expiration, contacts, name, reminder_id):

    reminder_stopped = reminder_stop_check(reminder_id);
    if reminder_stopped:
        print('Cant update stopped reminder.')
    else:
        reminder_timer_update(next_expiration, reminder_id, True)
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
    print('Checking in on reminder:', reminder_id)
    global db_link
    db = SQL(db_link)
    rows = db.execute("SELECT interval, notify_time, end_time FROM reminders WHERE id = :reminder_id",reminder_id=reminder_id)
    if rows:
        interval = rows[0]['interval']
        notify_time = rows[0]['notify_time']
        end_time = rows[0]['end_time']
        if notify_time != None or end_time != None:
            print('Cant update expired reminder.')
        else:
            current_date_and_time = datetime.datetime.now()
            minutes_added = datetime.timedelta(minutes = interval)
            next_expiration = current_date_and_time + minutes_added
            next_expiration = next_expiration.strftime("%Y-%m-%d %H:%M:%S")
            print('Updated expiration:',next_expiration)
            reminder_timer_update(next_expiration, reminder_id, True)

            db.execute(
                "UPDATE reminders SET next_expiration=:next_expiration WHERE id=:reminder_id",
                reminder_id=reminder_id,
                next_expiration=next_expiration
                )

# dict array filter
def filter_remove(timer_reminder_array, attribute, filter_value):
    new_array = []
    for timer_reminder in timer_reminder_array:
        if str(timer_reminder[attribute]) != str(filter_value):
            # print(attribute)
            # print(filter_value)
            # print(timer_reminder[attribute])
            # print(timer_reminder[attribute] != filter_value)
            new_array = new_array + [timer_reminder]
    return new_array

# updating reminder to timer array
def reminder_timer_update(next_expiration, reminder_id, add_remove):
    global reminder_timer_array
    if add_remove:
        # first remove previous
        if len(reminder_timer_array) > 0:
            reminder_timer_array = filter_remove(reminder_timer_array, 'reminder_id', reminder_id)


        timer = {
          "reminder_id": reminder_id,
          "next_expiration": next_expiration
        }
        if len(reminder_timer_array) < 1:
            print('Adding to timer array reminder with id: ', reminder_id)
            reminder_timer_array = [timer]
        else:
            print('Adding to timer array reminder with id: ', reminder_id)
            reminder_timer_array = reminder_timer_array + [timer]
    elif len(reminder_timer_array) > 0:
        print('Removing from timer array reminder with id: ', reminder_id)
        reminder_timer_array = filter_remove(reminder_timer_array, 'reminder_id', reminder_id)
    print('')
    if len(reminder_timer_array) > 0:
        reminder_timer_array.sort(key = lambda x: datetime.datetime.strptime(x['next_expiration'], '%Y-%m-%d %H:%M:%S'))
        reminders_late_check()

# Check if reminder has been stopped
def reminder_stop_check(reminder_id):
    print('Checking if reminder has been stopped reminder:', reminder_id)
    global db_link
    db = SQL(db_link)
    rows = db.execute("SELECT end_time FROM reminders WHERE id = :reminder_id",reminder_id=reminder_id)
    if rows:
        end_time = rows[0]['end_time']
        if end_time != None:
            return True
        else:
            return False

# update reminders
def stop_reminder(reminder_id):

    reminder_stopped = reminder_stop_check(reminder_id);
    if reminder_stopped:
        print('Cant update stoped reminder:', reminder_id)
    else:
        global db_link
        db = SQL(db_link)
        end_time = datetime.datetime.now()
        # Stop query
        reminder_timer_update(False, reminder_id, False)
        print('Stopping reminder with id:', reminder_id)
        db.execute("UPDATE reminders SET end_time=:end_time WHERE id=:reminder_id", end_time=end_time, reminder_id=reminder_id)

# update reminders
def set_reminder_notify_time(reminder_id):
    notify_time = datetime.datetime.now()
    # Notify time query
    print('Setting notify time for reminder with id:', reminder_id)
    db.execute("UPDATE reminders SET notify_time=:notify_time WHERE id=:reminder_id", notify_time=notify_time, reminder_id=reminder_id)

# Notifiy contacts
def notify_reminder_contacts(timer_reminder):
    # get full reminder data
    # print(timer_reminder['reminder_id'])
    reminder_id = timer_reminder['reminder_id']
    full_reminder = get_reminder_by_id_with_sql_create(reminder_id)

    contacts = full_reminder['contacts']
    details = full_reminder['details']
    user_id = full_reminder['user_id']
    reminder_name = full_reminder['name']
    user = get_user_by_id_with_sql_create(user_id)
    username = user['username']
    text = 'Reminder name: ' + reminder_name  + '\nPerson: ' + username + '\nMessage:' + details


    print('Username: ',username)

    if "," in contacts:
        contacts = contacts.split(",")
    else:
        contacts = [contacts]

    # send notification
    email_contacts(contacts, 'Live Switch', text)
    set_reminder_notify_time(reminder_id)

# process expired reminder
def handle_expired_reminder(reminder):
    print('')
    print('Time expired for reminder with id: ', reminder['reminder_id'])
    notify_reminder_contacts(reminder)
    reminder_timer_update(False, reminder['reminder_id'], False)
    print('')

# Check if there is a late reminder
def reminders_late_check():
    global reminder_timer_array
    if len(reminder_timer_array) > 0:
        closes_reminder = reminder_timer_array[0]
        next_expiration = closes_reminder['next_expiration'];
        time_exp = datetime.datetime.strptime(str(next_expiration), '%Y-%m-%d %H:%M:%S')
        time_now = datetime.datetime.now()
        remaining_time = time_exp - time_now

        if remaining_time > datetime.timedelta(0):
            print(str('Time is fine ' + time_now.strftime("%Y-%m-%d %H:%M:%S")))
            print('Next timer to expire: ', closes_reminder)
        else:
            handle_expired_reminder(closes_reminder)

    else:
        print('Reminder array is empty')

# Runs function and calls reminder timer again
def timer_engine():
    reminders_late_check()
    threading.Timer(5.0, timer_engine).start()

@app.before_first_request
def initialize():
    get_timer_reminders()
    timer_engine()

# if __name__ == '__main__':
    # app.run(debug = True)
    # get_timer_reminders()
    # timer_engine()