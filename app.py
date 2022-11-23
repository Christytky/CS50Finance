import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stock_data = db.execute("SELECT symbol, SUM(shares) FROM transactions WHERE user_id=:user_id GROUP BY symbol", user_id=session["user_id"]) # symbol | shares
    cash = db.execute("SELECT cash FROM users where id=:id", id=session["user_id"])
    # Display the user's current cash balance
    cash = cash[0]['cash']
    
    # Delete if the stock has sold out
    for i in range(len(stock_data)):
        if stock_data[i]['SUM(shares)'] == 0:
            del(stocks_owned[i])
    
    # Check all stocks owned, no. of shares of each stock, current price of each stock, total value of each holding
    # Store into list
    symbol = []
    name = []
    price = []
    total_share = []
    value = []
    total_value = 0
    
    for stock in stock_data:
        symbol.append(stock["symbol"])
        name.append(lookup(stock["symbol"])['name'])
        stock_price = lookup(stock["symbol"])['price']
        price.append(usd(stock_price))
        stock_share = stock["SUM(shares)"]
        total_share.append(stock_share)
        stock_value = float(stock_price) * float(stock_share)
        stock_value = stock_value
        value.append(usd(stock_value))
        total_value += stock_value
        
    total_value = usd(total_value)
    
    data = [symbol, name, price, value, cash, total_value]
           
    return render_template("index.html", data=data)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    
    # The form is submitted via POST
    if request.method == "POST":
        
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        
        getQuote = lookup(symbol)
        
        # Lookup the stock symbol and check no. of shares
        if not symbol:
            return apology("Please provide a symbol", 400)
            
        elif not getQuote:
            return apology("Please input correct symbol", 400)
        
        if not shares:
            return apology("Please provide no. of shares", 400)
        
        elif not shares.isdigit():
            return apology("Please input a positive integer for shares", 400)

        else:
            price = float(getQuote["price"])
            transact_amount = int(shares) * float(price)
            
            # Check if cash is enough for transaction
            cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
            cash = cash[0]["cash"]
            
            cash_remain =  float(cash) - transact_amount
            if cash_remain < 0:
                return apology("Not enough cash", 403)
            
            # Display the results
            else:
                # Add new table to database using appropriate SQL types
                db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash_remain, id=session["user_id"])
                db.execute("INSERT INTO transactions (user_id, symbol, shares, price, action, transact_amount) VALUES (:user_id, :symbol, :shares, :price, 'BUY', :transact_amount)",
                                     user_id=session["user_id"], 
                                     symbol=symbol,
                                     shares=shares, 
                                     price=price, 
                                     transact_amount=transact_amount)
                
                return redirect("/")
    
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    stock_data = db.execute("SELECT * FROM transactions WHERE user_id=:user_id", user_id=session["user_id"])
    
    # Store into list
    symbol = []
    name = []
    action = []
    shares = []
    price = []
    amount = []
    
    for stock in stock_data:
        symbol.append(stock["symbol"])
        stock_name = lookup(stock["symbol"])["name"]
        name.append(stock_name)
        action.append(stock["action"])
        shares.append(stock["shares"])
        price.append(stock["price"])
        amount.append(stock["transact_amount"])
    
    data = [symbol, name, action, shares, price, amount]
    
    return render_template("history.html", data=data)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
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
    
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        
        # Look up the stock symbol by calling the loookyp function
        getQuote = lookup(symbol)      
        
        # If lookup is unsuccessful, function returns None
        if not symbol:
            return apology("Please enter a stock symbol", 400)
        
        elif not getQuote:
            return apology("No stock found", 400)
        
        # If lookup is successful, function returns a dictionary with name, price, symbol
        else:
            # Display the results (see helpers.py)
            name = getQuote["name"]
            price = getQuote["price"]
        
            return render_template("quoted.html", name=name, price=price, symbol=symbol.upper())
    
    # When requested via GET, display form to request a stock quote
    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()
    
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_pw = request.form.get("confirmation")
    
    # When requested via GET, should display registration form
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not username:
            return apology("Please provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("Please provide password", 400)
            
        # Ensure password (again) was submitted
        elif not confirm_pw:
            return apology("Please confirm the password", 400)
            
        # Ensure the typed password is same as password (again)
        elif password != confirm_pw:
            return apology("Mismatch password", 400)
            
        else:
            # Check if user name is already exist
            check_user = db.execute("SELECT username FROM users WHERE username=:username", 
                                    username=request.form.get("username"))
            if len(check_user) == 1:
                return apology("Username already exists", 400)
                
            else:
                # Create database for username
                # Hash the user's password
                add_user = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", 
                                      username=request.form.get("username"), 
                                      password=generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8))
                # Flash for success registered
                flash("Registered")
                return redirect("/")
            
    return render_template("register.html")
        

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
       
    # The form is submitted via POST
    if request.method == "POST":
        
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        
        getQuote = lookup(symbol)
        
        # Lookup the stock symbol and check no. of shares
        if not symbol:
            return apology("Please provide a symbol", 400)
            
        if not getQuote:
            return apology("Please input correct symbol", 400)
        
        if not shares:
            return apology("Please provide no. of shares", 400)
        
        if shares.isdigit() == False:
            return apology("Please input a positive integer for shares", 400)
        
        
        # Check stock exist in transaction record and have enough stock to sell
        stock_record = db.execute("SELECT symbol, SUM(shares), action FROM transactions WHERE user_id=:user_id GROUP BY symbol, action", user_id=session["user_id"])
        
        # Find shares owned
        shares_buy  = 0
        shares_sell = 0
        
        for stock in stock_record:
            if stock['symbol'] == symbol:
                if stock['action'] == 'BUY':
                    shares_buy = stock['SUM(shares)']
                else:
                    shares_sell = stock['SUM(shares)']
                    
        shares_owned = shares_buy - shares_sell
        print(shares_owned)
        
        if int(shares) > int(shares_owned):
                return apology("Not enough shares to sell", 400)
        
        else:
            price = float(getQuote["price"])
            transact_amount = int(shares) * float(price)
            
            # Check if cash is enough for transaction
            cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
            cash = cash[0]["cash"]
            
            cash =  float(cash) + transact_amount

            # Add new table to database using appropriate SQL types
            db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash, id=session["user_id"])
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price, action, transact_amount) VALUES (:user_id, :symbol, :shares, :price, 'SELL', :transact_amount)",
                                    user_id=session["user_id"], 
                                    symbol=symbol,
                                    shares=shares, 
                                    price=price, 
                                    transact_amount=transact_amount)
            
            return redirect("/")

    else:
        # Get stocks symbol
        stocks = db.execute("SELECT symbol FROM transactions WHERE user_id=:user_id GROUP BY symbol", user_id=session["user_id"])
        
        stocks_opt = []
        for i in stocks:
            stocks_opt.append(i["symbol"])
        
        return render_template("sell.html", stocks_opt=stocks_opt)


if __name__ == "__main__":
    app.run(debug=False)