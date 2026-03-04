import json
import requests
from flask import Flask, render_template, request
from my_classes import *
import os.path


#------------------------CONSTANTS------------------------#
API_STATUS = "https://api.spacetraders.io/v2/"
LIST_FACTIONS = "https://api.spacetraders.io/v2/factions"
CLAIM_USER = "https://api.spacetraders.io/v2/register"
MY_ACCOUNT = "https://api.spacetraders.io/v2/my/agent"
MY_CONTRACTS = "https://api.spacetraders.io/v2/my/contracts"
MY_SHIPS = "https://api.spacetraders.io/v2/my/ships"
AGENT_FILE = "agents.json"

#------------------------Test data for now -------------------------#
error_message = "This is an error message"
agent_name, faction, credits = "saurabh", "test faction", 6767

def main():
    app = Flask(__name__)

    @app.route("/", methods =["GET", "POST"])
    def index():
        if request.method == "POST":
            username = request.form.get("username")
            if username:
                response = requests.post(CLAIM_USER, json={"symbol": username})
                if response.status_code == 201:
                    json_result = response.json()
                    store_agent_login(json_result["data"])
                    print(json_result)
                else:
                    print(f"Error claiming user: {response.text}")
        return render_template("index.html")


    @app.route("/error")
    def error():
        return render_template("error.html")

    @app.route("/summary")
    def summary():
        return render_template("summary.html", agent_name=agent_name, contracts= [my_contracts, my_contracts])

    if __name__ == "__main__":
        app.run(debug=True)


#test contract to test with summary page
my_contracts = Contracts({
    "faction":"best faction",
    "type" : "transport",
    "deadline" : "2024-06-30T23:59:00.000Z",
    "goods" : "food",
    "destination" : "earth",
    "owing" : 1000
})


def load_player_logins():
    known_agents = {}

    if os.path.exists(AGENT_FILE):
        with open(AGENT_FILE) as json_agents:
            known_agents = json.load(json_agents)

    return known_agents

def store_agent_login(json_result):
    known_agents = load_player_logins()
    known_agents[json_result["symbol"]] = json_result["token"]

    with open(AGENT_FILE, "w") as json_agents:
        json.dump(known_agents, json_agents)

main()