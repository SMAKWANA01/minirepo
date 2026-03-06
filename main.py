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
#test contract to test with summary page
#TODO: replace with actual API thing
my_contracts = Contracts({
    "faction":"best faction",
    "type" : "transport",
    "deadline" : "2024-06-30T23:59:00.000Z",
    "goods" : "food",
    "destination" : "earth",
    "owing" : 1000
})

app = Flask(__name__)

@app.route("/", methods = ["GET", "POST"])
def index():

    if request.method == "POST":
        token = request.form.get("username")# This could be token or username.
        
        global agent
        agent = Agent(token)
        if agent.error:
            return render_template("error.html", error_message=agent.error, error_code=400)
        if not agent.get_agent_data():
            return render_template("error.html", error_message=agent.error["message"], error_code=agent.error["status"])

        return render_template("summary.html", agent_name=agent.symbol, contracts= [my_contracts, my_contracts])
    
    return render_template("index.html")


@app.route("/error")
def error():
    return render_template("error.html", error_message=error_message, error_code=error_code)

@app.route("/summary")
def summary():
    return render_template("summary.html", agent=agent, contracts= [my_contracts, my_contracts])

if __name__ == "__main__":
    app.run(debug=True)
