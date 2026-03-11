import json
import requests
from flask import Flask, render_template, request
from my_classes import *
import threading

#-------------------- for simultaneous background tasks------------------#
background_tasks = {}


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

def run_fulfill(contract, ship, task_id):
    try:
        contract.fulfill(ship)
        background_tasks[task_id] = "done"
    except Exception as e:
        background_tasks[task_id] = f"error: {e}"
        return render_template("error.html", error_code=e.args[0], error_message=e.args[1])


app = Flask(__name__)
agent = None


@app.route("/", methods = ["GET", "POST"])
def index():

    if request.method == "POST":
        token = request.form.get("username")# This could be token or username.
        try:
            global agent
            agent = Agent(token)
        except Exception as e:
            return render_template("error.html", error_code=e.args[0], error_message=e.args[1])
        return render_template("summary.html", agent=agent)
        
    
    return render_template("index.html")

@app.route("/contracts/<contract_id>/fulfill")# METHOD SHOULD BE POST
def fulfill_contract(contract_id):
    contract = next(c for c in agent.contracts if c.id == contract_id)
    ship = agent.ships[0]  # For simplicity, using the first ship, would make it specific to contract but we have time restraint

    task_id = f"{contract_id}_fulfill"
    background_tasks[task_id] = "running"

    thread = threading.Thread(target=run_fulfill, args=(contract, ship, task_id))
    thread.start()

    return render_template("summary.html", agent=agent, message="Fulfillment started in background.")

@app.route("/task_status/<task_id>")
def task_status(task_id):
    #TODO: Make it render template iab
    return background_tasks.get(task_id, "unknown")


@app.route("/error")
def error():
    return render_template("error.html", error_message=error_message, error_code=error_code)

@app.route("/summary")
def summary():
    return render_template("summary.html", agent=agent)

@app.route("/contracts/<contract_id>", methods=["POST"])
def accept_contract(contract_id):
    for contract in agent.contracts:
        print(contract)
        if contract.id == contract_id:
            try:
                contract.accept()
            except Exception as e:
                return render_template("error.html", error_code=e.args[0], error_message=e.args[1])
    return render_template("summary.html", agent=agent)

if __name__ == "__main__":
    app.run(debug=True)
