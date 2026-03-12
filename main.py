from flask import Flask, render_template, request, session
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
        print("exception", e)
        background_tasks[task_id] = f"error: {e}"
        return render_template("error.html", error_code=e.args[0], error_message=e.args[1])


app = Flask(__name__)

#Secret key for sessions, make random later but this is fun for now
app.secret_key = "superdupersecretkey that nobody will ever guess 676767 lmnopqrstuvwxyz" 


# Tribute to the line that crashed my entire code: agent = None


@app.route("/", methods = ["GET", "POST"])
def index():
    global agent
    if request.method == "POST":
        token = request.form.get("username")# This could be token or username.
        try:
            session["token"] = token

            agent = Agent(token)
        except Exception as e:
            return render_template("error.html", error_code=e.args[0], error_message=e.args[1])
        return render_template("summary.html", agent=agent)
    
    #This is for whenever the user refreshes the page.
    if "token" in session:

        agent = Agent(session["token"])
        return render_template("summary.html", agent=agent)
    

    return render_template("index.html")

        
    
    return render_template("index.html")

@app.route("/contracts/<contract_id>/fulfill")# METHOD SHOULD BE POST
def fulfill_contract(contract_id):
    contract = next(c for c in agent.contracts if c.id == contract_id)
    print("fullfilling contract:", contract.id)
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
        print("contract=",contract)
        if contract.id == contract_id:
            try:
                contract.accept()
            except Exception as e:
                return render_template("error.html", error_code=e.args[0], error_message=e.args[1])
    return render_template("summary.html", agent=agent)

@app.route("/ships/<ship_symbol>")
def ship_details(ship_symbol):
    global agent
    ship = next((s for s in agent.ships if s.symbol == ship_symbol), None)
    if not ship:
        return render_template("error.html", error_code=404, error_message=f"Ship {ship_symbol} not found")

    # Refresh ship 
    ship.deserialize()

    return render_template("ship.html", ship=ship, agent=agent)

@app.route("/contracts")
def contracts_page():
    return render_template("contracts.html", agent=agent)

@app.route("/ships/<ship_symbol>/control", methods=["GET", "POST"])
def ship_control(ship_symbol):
    global agent

    ship = next((s for s in agent.ships if s.symbol == ship_symbol), None)
    if not ship:
        return render_template("error.html", error_code=404, error_message="Ship not found")

    ship.deserialize()

    # Load waypoints for dropdown
    contract = agent.contracts[0]  # any contract works, just need wp hehehe
    waypoints = contract.find_waypoints(ship)

    if request.method == "POST":
        action = request.form.get("action")

        try:
            if action == "orbit":
                ship.orbit()

            elif action == "dock":
                ship.dock()

            elif action == "undock":
                ship.undock()

            elif action == "refuel":
                ship.refuel()

            elif action == "navigate":
                wp = request.form.get("waypoint")
                ship.navigate(wp)

            elif action == "jettison":
                symbol = request.form.get("cargo_symbol")
                units = int(request.form.get("cargo_units"))
                ship.jettison(symbol, units)

            elif action == "flight_mode":
                mode = request.form.get("mode")
                ship.set_flight_mode(mode)

        except Exception as e:
            return render_template("ship_control.html", ship=ship, agent=agent, waypoints=waypoints, error=str(e))

        ship.deserialize()

    return render_template("ship_control.html", ship=ship, agent=agent, waypoints=waypoints)



if __name__ == "__main__":
    app.run(debug=True)
