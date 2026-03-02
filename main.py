import json
import requests
from flask import Flask, render_template
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
agent_name, faction, credits = "saurabh", "test faction", 6767

#test contract to test with summary page
my_contracts = Contracts({
    "faction":"best faction",
    "type" : "transport",
    "deadline" : "2024-06-30T23:59:00.000Z",
    "goods" : "food",
    "destination" : "earth",
    "owing" : 1000
})

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/error")
def error():
    return render_template("error.html")

@app.route("/summary")
def summary():
    return render_template("summary.html", agent_name=agent_name, contracts= [my_contracts, my_contracts])

if __name__ == "__main__":
    app.run(debug=True)
