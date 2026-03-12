#TODO: fuel. its running out. add fuel checks and refuel.
#TODO: Make sure everything works with the new control page


import json
import os
import requests
from datetime import datetime
from time import sleep

#------------------------CONSTANTS------------------------#
API_STATUS = "https://api.spacetraders.io/v2/"
LIST_FACTIONS = "https://api.spacetraders.io/v2/factions"
CLAIM_USER = "https://api.spacetraders.io/v2/register"
MY_ACCOUNT = "https://api.spacetraders.io/v2/my/agent"
MY_CONTRACTS = "https://api.spacetraders.io/v2/my/contracts"
MY_SHIPS = "https://api.spacetraders.io/v2/my/ships"
SYSTEMS = "https://api.spacetraders.io/v2/systems"
TOKEN_FILE = "agents.json" 


#---------THE FOLLOWING TWO FUNCTIONS ARTE COPIED FROM SIR'S TEMPLATE---------#
UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
DISPLAY_FORMAT = " %B, %Y at %H:%M:%S"

def parse_datetime(dt):
    return datetime.strptime(dt, UTC_FORMAT)

def format_datetime(dt_text):
    dt = parse_datetime(dt_text)
    d = dt.day
    return (
        str(d)
        + ("th" if 11 <= d <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th"))
        + datetime.strftime(dt, DISPLAY_FORMAT)
    )



#------------------------CLASSES------------------------#
class Contract():
    def __init__(self, contract_id, token):

        self.token = token
        load = self._load_contract(contract_id)
        data = load["data"]

        self.id = data["id"]
        self.faction = data["factionSymbol"]
        self.type = data["type"]
        self.deadline = format_datetime(data["terms"]["deadline"])
        self.paymet_onAccepted = data["terms"]["payment"]["onAccepted"]
        self.paymet_onFulfilled = data["terms"]["payment"]["onFulfilled"]

        self.accepted = data["accepted"]
        self.fulfilled = data["fulfilled"]
        self.deadlineToAccept = data["deadlineToAccept"]

        self.deliver = data["terms"]["deliver"]




    def _load_contract(self, contract_id):

        response = requests.get(
            MY_CONTRACTS + f"/{contract_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code not in [200, 201]:
            print("Something went wrong, Agent class load_contract")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        return response.json()



    def accept(self):
        response = requests.post(
            MY_CONTRACTS + f"/{self.id}/accept",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong, Agent class load_contract")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        self.accepted = True
        self.deadlineToAccept = None



    def _delivered_so_far(self, symbol):
        """Return how many units have already been delivered (server-side)."""
        for d in self.deliver:
            if d["tradeSymbol"] == symbol:
                return d["unitsFulfilled"]
        return 0


    #This is where the magic happens :D

    def fulfill(self, ship):

        print("\n BEGINNING CONTRACT FULFILLMENT \n")

        self._ensure_in_orbit(ship)

        asteroid_fields = self._find_all_asteroid_fields(ship)
        if not asteroid_fields:
            raise Exception("No asteroid fields found in this system.")

        print(f"Found {len(asteroid_fields)} asteroid fields.")

        current_field_index = 0
        self._navigate_to_waypoint(ship, asteroid_fields[current_field_index]["symbol"])

        for item in self.deliver:
            required_symbol = item["tradeSymbol"]
            required_units = item["unitsRequired"]

            print(f"\n STARTING DELIVERY FOR {required_symbol} ({required_units} units) \n")

            self._mine_for_delivery(
                ship,
                required_symbol,
                required_units,
                asteroid_fields,
                current_field_index
            )

        print("\n CONTRACT MINING COMPLETE — READY FOR FINAL DELIVERY \n")



    # helper functions for navigation and mining

    def _ensure_in_orbit(self, ship):
        ship.deserialize()

        if ship.status == "IN_TRANSIT":
            print("Ship is in transit — waiting for arrival instead of orbiting.")
            self._wait_until_arrived(ship)
            return

        if ship.status != "IN_ORBIT":
            print("Going to orbit...")
            ship.orbit()


    def _navigate_to_waypoint(self, ship, waypoint_symbol):

        if ship.waypoint == waypoint_symbol:
            print(f"[NAV] Already at {waypoint_symbol}, skipping navigation.")
            return
        print(f"[NAV DEBUG] From {ship.waypoint} to {waypoint_symbol}, fuel={ship.fuel_current}/{ship.fuel_capacity}")

        
        if waypoint_symbol == self._find_nearest_fuel_station(ship)["symbol"]:
            print("[NAV] Skipping fuel check because we are already heading to a fuel station.")
        else:
            if ship.is_low_fuel():
                print("[NAV] Fuel low before navigation — refueling first.")
                self._auto_refuel(ship)

        print(f"Navigating to waypoint: {waypoint_symbol}")

        try:
            # First attempt: normal navigation
            response = requests.post(
                MY_SHIPS + f"/{ship.symbol}/navigate",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"waypointSymbol": waypoint_symbol}
            )

            if response.status_code not in [200, 201]:
                raise Exception(response.status_code, response.text)

        except Exception as e:

            msg = str(e)
            if "fuelRequired" in msg or "4203" in msg:
                print("[NAV-EMERGENCY] Not enough fuel — switching to DRIFT mode.")
                ship.set_flight_mode("DRIFT")

                # Retry navigation in DRIFT mode (always succeeds)
                response = requests.post(
                    MY_SHIPS + f"/{ship.symbol}/navigate",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"waypointSymbol": waypoint_symbol}
                )

                if response.status_code not in [200, 201]:
                    print("[NAV-EMERGENCY] DRIFT navigation failed unexpectedly.")
                    print(response.text)
                    raise Exception(response.status_code, response.reason)

                print("[NAV-EMERGENCY] DRIFT navigation succeeded.")


            else:
                # Not a fuel error
                raise
        
        arrival = ship.route["arrival"]
        print(f"[NAV-EMERGENCY] DRIFT navigation succeeded.")
        print(f"[NAV-EMERGENCY] Arrival ETA: {format_datetime(arrival)}")
        # Continue as normal
        self._wait_until_arrived(ship)
        ship.set_flight_mode("CRUISE")
        self._ensure_in_orbit(ship)



    def _wait_until_arrived(self, ship):
        print("Waiting for arrival...")

        while True:
            ship.deserialize()

            # If server says we're not in transi t, we're done
            if ship.status != "IN_TRANSIT":
                break

            # If arrival time is in the past, force one more refresh and break
            arrival_dt = parse_datetime(ship.route["arrival"])
            if arrival_dt.timestamp() <= datetime.now().timestamp():
                print("Arrival time passed — forcing final sync...")
                sleep(2)
                ship.deserialize()
                break

            print(f"Still in transit... {format_datetime(ship.route['arrival'])}")
            sleep(2)

        if ship.status != "IN_ORBIT":
            print("Arrived — entering orbit...")
            ship.orbit()

        print("Arrival confirmed.")






    def _find_all_asteroid_fields(self, ship):
        waypoints = self.find_waypoints(ship)
        return [
            wp for wp in waypoints
            if wp["type"] in ["ASTEROID", "ASTEROID_FIELD", "ENGINEERED_ASTEROID"]
        ]



    def _mine_for_delivery(self, ship, required_symbol, required_units, asteroid_fields, current_field_index):

        active_survey = None
        survey_expiry = None
        no_progress = 0

        delivered = self._delivered_so_far(required_symbol)

        while delivered < required_units:
            #Check fuel, if low refuel:
            if ship.is_low_fuel():
                print("Fuel low — initiating auto-refuel sequence.")
                self._auto_refuel(ship)
            
            if ship.cargo_units >= ship.cargo_capacity:
                print("Cargo full — delivering what we have.")
                self._handle_full_cargo(
                    ship,
                    required_symbol,
                    asteroid_fields,
                    current_field_index
                )
                delivered = self._delivered_so_far(required_symbol)
                continue

            self._wait_for_cooldown(ship)

            if active_survey is None or datetime.now().timestamp() > survey_expiry:
                active_survey, survey_expiry = self._get_best_survey(ship, required_symbol)

            before = ship.count_cargo(required_symbol)
            self._wait_for_cooldown(ship)
            self._extract(ship, active_survey)
            after = ship.count_cargo(required_symbol)

            print(f"Current count of {required_symbol}: {after}/{required_units} (delivered: {delivered})")

            if after == before:
                no_progress += 1
                print(f"No progress detected ({no_progress}/5)")
            else:
                no_progress = 0

            if no_progress >= 5:
                print("\nMining not giving anything — moving to next asteroid field.")
                current_field_index = self._move_to_next_asteroid(
                    ship, asteroid_fields, current_field_index
                )
                active_survey = None
                survey_expiry = None
                no_progress = 0

            delivered = self._delivered_so_far(required_symbol)



    def _wait_for_cooldown(self, ship):
        sleep(5)
        while True:
            ship.deserialize()
            cooldown = ship.cooldown["remainingSeconds"]

            if cooldown <= 0:
                print("Cooldown reached zero — waiting for server sync...")
                sleep(5)
                ship.deserialize()
                return

            print(f"Waiting for cooldown: {cooldown}s")
            sleep(cooldown + 1)



    def _get_best_survey(self, ship, required_symbol):
        print("\nCreating new survey...")
        surveys = self.create_survey(ship.symbol)["surveys"]

        best = None
        best_count = 0

        for s in surveys:
            count = sum(1 for d in s["deposits"] if d["symbol"] == required_symbol)
            if count > best_count:
                best = s
                best_count = count

        if best is None:
            print("No useful survey found — mining without survey.")
            return None, None

        print("Best survey deposits:", best["deposits"])
        expiry = datetime.now().timestamp() + 15 * 60
        return best, expiry



    def _extract(self, ship, active_survey):
        if active_survey:
            print("Extracting with survey...")
            ship.extract_with_survey(active_survey)
        else:
            print("Extracting without survey...")
            ship.extract()



    def _move_to_next_asteroid(self, ship, fields, index):
        index = (index + 1) % len(fields)
        next_wp = fields[index]

        print(f"Switching to asteroid field: {next_wp['symbol']}")
        self._navigate_to_waypoint(ship, next_wp["symbol"])

        return index



    def _handle_full_cargo(self, ship, required_symbol, asteroid_fields, current_field_index):

        for d in self.deliver:
            if d["tradeSymbol"] == required_symbol:
                destination = d["destinationSymbol"]
                break

        print(f"Delivering cargo to {destination}...")

        self._navigate_to_waypoint(ship, destination)
        self._wait_until_arrived(ship)

        print("Docking for delivery...")
        ship.dock()

        self._deliver_resource(ship, required_symbol)

        for item in ship.cargo_inventory:
            if item["symbol"] != required_symbol:
                print(f"Jettisoning {item['units']} of {item['symbol']}")
                ship.jettison(item["symbol"], item["units"])

        print("Undocking...")
        ship.undock()

        print("Returning to asteroid field...")
        self._navigate_to_waypoint(ship, asteroid_fields[current_field_index]["symbol"])
        self._ensure_in_orbit(ship)



    def _deliver_resource(self, ship, symbol):
        units = ship.count_cargo(symbol)

        print(f"Delivering {units} units of {symbol}...")

        response = requests.post(
            MY_CONTRACTS + f"/{self.id}/deliver",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "shipSymbol": ship.symbol,
                "tradeSymbol": symbol,
                "units": units
            }
        )

        if response.status_code not in [200, 201]:
            print("Something went wrong delivering cargo")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        ship.deserialize()
        print("Delivery complete.")



    # API helpers

    def create_survey(self, ship_symbol):
        response = requests.post(
            MY_SHIPS + f"/{ship_symbol}/survey",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code != 201:
            print("Something went wrong, create survey class contract")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        return response.json()["data"]

    def find_waypoints(self, ship):
        response = requests.get(
            SYSTEMS + f"/{ship.system}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong, find waypoint class contract")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        return response.json()["data"]["waypoints"]

    def _find_nearest_fuel_station(self, ship):
        waypoints = self.find_waypoints(ship)

        fuel_stations = [
            wp for wp in waypoints
            if wp["type"] == "FUEL_STATION"
        ]

        if fuel_stations:
            return fuel_stations[0]
        raise Exception("", "No fuel stations found in this system.")

    def _auto_refuel(self, ship):
        print(f"[AUTO-REFUEL] Triggered at waypoint {ship.waypoint}, fuel={ship.fuel_current}")

        station = self._find_nearest_fuel_station(ship)
        print(f"Nearest fuel station: {station['symbol']}")

        return_point = ship.waypoint

        self._navigate_to_waypoint(ship, station["symbol"])

        print("Docking for refuel...")
        ship.dock()

        try:
            ship.refuel()
        except:
            print("Refuel failed ")
            ship.undock()
            raise Exception("", "Refuel failed at station " + station["symbol"])
        
        print(f"[AUTO-REFUEL] After refuel: fuel={ship.fuel_current}")

        print("Undocking...")
        ship.undock()

        # Return to asteroid 
        print(f"Returning to {return_point}...")
        self._navigate_to_waypoint(ship, return_point)
        print(f"[AUTO-REFUEL] Arrived back at {ship.waypoint}, fuel={ship.fuel_current}")
        print("Rufuel Completed\n")

        

class Ship:
    def __init__(self, ship_id, token):
        self.token = token
        self.ship_id = ship_id
        self.deserialize()

    def deserialize(self):
        
        load = self._load_ship(self.ship_id)
        data = load["data"]

        self.symbol = data["symbol"]
        self.registration = data["registration"]

        # everything in nav has been unpacked.
        self.nav = data["nav"]
        self.system = data["nav"]["systemSymbol"]
        self.waypoint = data["nav"]["waypointSymbol"]
        self.route = data["nav"]["route"]
        self.status = data["nav"]["status"]
        self.flight_mode = data["nav"]["flightMode"]

        # crew
        self.crew = data["crew"]

        # components
        self.frame = data["frame"]
        self.reactor = data["reactor"]
        self.engine = data["engine"]
        self.modules = data["modules"]
        self.mounts = data["mounts"]

        # cargo
        cargo = data["cargo"]
        self.cargo_capacity = cargo["capacity"]
        self.cargo_units = cargo["units"]
        self.cargo_inventory = cargo["inventory"]

        # fuel
        fuel = data["fuel"]
        self.fuel_current = fuel["current"]
        self.fuel_capacity = fuel["capacity"]
        self.fuel_consumed = fuel["consumed"]

        self.cooldown = data["cooldown"]

    def _load_ship(self, ship_id):
        response = requests.get(
            MY_SHIPS + f"/{ship_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code not in [200, 201]:
            print("Something went wrong, Agent class load_ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        return response.json()

    def orbit(self):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/orbit",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong, orbit class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        self.deserialize()
    
    def navigate(self, waypoint):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/navigate",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"waypointSymbol": waypoint}  )
    

        if response.status_code not in [200, 201]:
            print("Something went wrong, navigate class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
    
        print("Navigating...", end="")
        # Loop until we arrive
        while self.status == "IN_TRANSIT":
            print(".", end="")
            sleep(1)
            self.deserialize()  # refresh status from GET
        print("\nArrived!")
        
    def extract_with_survey(self, survey):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/extract/survey",
            headers={"Authorization": f"Bearer {self.token}"},
            json=survey
        )
        if response.status_code != 201: 
            print("Something went wrong, extract with survey, class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        sleep(5)  # Sleep a bit to allow the server to update the ship's cargo and cooldown

        self.deserialize()

    def count_cargo(self, trade_symbol):
        for item in self.cargo_inventory:
            if item["symbol"] == trade_symbol:
                return item["units"]
        return 0


    def extract(self):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/extract",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong, extract, class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        sleep(5)  # Sleep a bit to allow the server to update the ship's cargo and cooldown
        
        self.deserialize()

    def dock(self):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/dock",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong docking")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        self.deserialize()

    def undock(self):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/orbit",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong undocking")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        self.deserialize()
    def jettison(self, trade_symbol, units):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/jettison",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "symbol": trade_symbol,
                "units": units
            }
        )

        if response.status_code not in [200, 201]:
            print("Something went wrong jettisoning cargo")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        print(f"Jettisoned {units} units of {trade_symbol}.")
        self.deserialize()
    

    #Experience tells me 250 is enough, its only a mini NEA so not that deep
    def is_low_fuel(self, threshold=250):
        print(f"[FUEL CHECK] Current: {self.fuel_current}, Capacity: {self.fuel_capacity}, Threshold: {threshold}")
        return self.fuel_current < threshold


    def refuel(self):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/refuel",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code not in [200, 201]:
            print("Refuel failed")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        print("Refueled successfully.")
        self.deserialize()

    def set_flight_mode(self, mode):
        response = requests.patch(
            MY_SHIPS + f"/{self.symbol}/nav",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"flightMode": mode}
        )
        if response.status_code not in [200, 201]:
            print("Something went wrong setting flight mode")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        self.deserialize()
        print(f"[NAV] Flight mode set to {self.flight_mode}")


        


class Agent:
    def __init__(self,  token= ""):
        if token:
            self.token = token
            self._save_token(token)
        else:
            saved = self._load_token()
            if saved:
                self.token = saved
            else:
                raise Exception(400, "Invalid token")
            
        
        data = self._get_agent_data()

        self.accountId = data["accountId"]
        self.symbol = data["symbol"]
        self.headquarters = data["headquarters"]
        self.credits = data["credits"]
        self.faction = data["startingFaction"]
        self.shipCount = data["shipCount"]

        self.contracts = [Contract(contract["id"], self.token) for contract in data["contracts"]]
        self.ships = [Ship(ship["symbol"], self.token) for ship in data["ships"]]
        

    # Using internal functions 
    def _load_token(self):
        if not os.path.exists(TOKEN_FILE):
            return None
        
        try:
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("token")
            
        except Exception as e:
            print("Error in class agent, loading token: ", e)
            return None

    def _save_token(self, token):
        with open(TOKEN_FILE, "w") as f:
            json.dump({"token": token}, f)


    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    #NOT internal function, I'll call this once in main.
    #nvm it is an internal function, it gets called in the constructor to load all the data about the agent, ships and contracts.
    def _get_agent_data(self):
        response = requests.get(MY_ACCOUNT, headers=self._headers())

        if response.status_code not in [200, 201]:
            print("Something went wrong, Agent class get_agent_data")
            print(response.text)# Only for debugging 
            raise Exception(response.status_code, response.reason + " maybe token has expired?")
        
        data = response.json()["data"]

        response = requests.get(MY_CONTRACTS, headers=self._headers())

        if response.status_code not in [200, 201]:
            print("Something went wrong, Agent class get_agent_data, contracts")
            raise Exception(response.status_code, response.reason)
        
        data2 = response.json()["data"]

        response = requests.get(MY_SHIPS, headers=self._headers())
        if response.status_code not in [200, 201]:
            print("Something went wrong, Agent class get_agent_data, ships")
            raise Exception(response.status_code, response.reason) 
        
        data3 = response.json()["data"]

        data = {**data, "contracts": data2, "ships": data3}
        return data
