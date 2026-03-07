import json
import requests
from flask import Flask, render_template, request
from my_classes import *

#------------------------CONSTANTS------------------------#
API_STATUS = "https://api.spacetraders.io/v2/"
LIST_FACTIONS = "https://api.spacetraders.io/v2/factions"
CLAIM_USER = "https://api.spacetraders.io/v2/register"
MY_ACCOUNT = "https://api.spacetraders.io/v2/my/agent"
MY_CONTRACTS = "https://api.spacetraders.io/v2/my/contracts"
MY_SHIPS = "https://api.spacetraders.io/v2/my/ships"


#------------------------Test data for now init-------------------------#
error_message = "This is an error message"
error_code = 67

app = Flask(__name__)

@app.route("/", methods = ["GET", "POST"])
def index():

    if request.method == "POST":
        token = request.form.get("username")# This could be token or username.
        print(token)
        global agent
        try:
            agent = Agent(token)
        except Exception as e:
            return render_template("error.html", error_code=e.args[0], error_message=e.args[1])
        return render_template("summary.html", agent=agent)
        
    
    return render_template("index.html")
    

@app.route("/error")
def error():
    return render_template("error.html", error_message=error_message, error_code=error_code)

@app.route("/summary")
def summary():

    return render_template("summary.html", agent=agent)

if __name__ == "__main__":
    app.run(debug=True)
