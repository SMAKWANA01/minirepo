import json
import os
import requests
from datetime import datetime

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
DISPLAY_FORMAT = " %B, %Y"
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

        #There may be many things to deliver, hence a list of dictionaries, 
        #with "tradeSymbol", "destinationSymbol", "unitsRequired", "unitsFulfilled"
        #The units part is integers

        self.deliver = data["terms"]["deliver"]

        

    def _load_contract(self, contract_id):

        response = requests.get(MY_CONTRACTS +f"/{contract_id}", headers={"Authorization": f"Bearer {self.token}"})


        if response.status_code != 200:
            print("Something went wrong, Agent class load_contract")
            print(response.text)# Only for debugging
            raise Exception(response.status_code, response.reason)
        return response.json()


    def accept(self):
        response = requests.post(MY_CONTRACTS +f"/{self.id}/accept", headers={"Authorization": f"Bearer {self.token}"})
        if response.status_code != 200:
            print("Something went wrong, Agent class load_contract")
            print(response.text)# Only for debugging
            raise Exception(response.status_code, response.reason)
        self.accepted = True
        self.deadlineToAccept = None
    
    def fulfill(self, ship):
#TODO:  1) orbit from current possition
#       2)  Find waypoint of the nearest asteroid, navigate there
#       3) Looks like we have to survey otherwise itll take ages, if the survey gives deposit, use survey, otherwise mine whilst on cooldown
#       Also, make sure to check all the available surveys and use the best one
#       4)  Mine until we have enough resources
#       5)  Fly to the destination
#       6/7)  Deliver the resources, fulfill the contract
        if ship.status != "IN_ORBIT":
            print("Going to orbit")
            ship.orbit()
        
        waypoints = self.find_waypoints(ship.symbol)
        
        for _waypoint in waypoints:
            if _waypoint["type"] in ["ENGINEERED_ASTEROID", "ASTEROID"]:
                waypoint = _waypoint
                break
        else:
            raise Exception("", "No valid waypoints were found, cannot continue")

        ship.navigate(waypoint)




        # SURVEY
        surveys = self.create_survey(ship.symbol)["surveys"]
        for survey in surveys:
            pass
        #TODO: FIND WHICH SURVEY HAS THE HIGHEST YIELD. 
            
    
    def create_survey(self, ship_symbol):
        response = requests.get(
            MY_SHIPS + f"/{ship_symbol}/survey",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code != 200:
            print("Something went wrong, orbit class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        return response

    def find_waypoints(self, ship_symbol):
        response = requests.get(
            SYSTEMS + f"/{ship_symbol}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code != 200:
            print("Something went wrong, orbit class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        return response["waypoints"]
    

class Ship:
    def __init__(self, ship_id, token):
        self.token = token
        self.ship_id = ship_id
        self._registration()

    def _registration(self):
        
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

        if response.status_code != 200:
            print("Something went wrong, Agent class load_ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)

        return response.json()

    def orbit(self):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/orbit",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if response.status_code != 200:
            print("Something went wrong, orbit class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        self._registration()
    
    def navigate(self, waypoint):
        response = requests.post(
            MY_SHIPS + f"/{self.symbol}/navigate",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"waypointSymbol": waypoint}  )
    

        if response.status_code != 200:
            print("Something went wrong, orbit class ship")
            print(response.text)
            raise Exception(response.status_code, response.reason)
        
        self._registration(response["data"])
        

    


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
    def _get_agent_data(self):
        response = requests.get(MY_ACCOUNT, headers=self._headers())

        if response.status_code != 200:
            print("Something went wrong, Agent class get_agent_data")
            print(response.text)# Only for debugging 
            raise Exception(response.status_code, response.reason + " maybe token has expired?")
        
        data = response.json()["data"]

        response = requests.get(MY_CONTRACTS, headers=self._headers())

        if response.status_code != 200:
            print("Something went wrong, Agent class get_agent_data, contracts")
            raise Exception(response.status_code, response.reason)
        
        data2 = response.json()["data"]

        response = requests.get(MY_SHIPS, headers=self._headers())
        if response.status_code != 200:
            print("Something went wrong, Agent class get_agent_data, ships")
            raise Exception(response.status_code, response.reason)
        
        data3 = response.json()["data"]

        data = {**data, "contracts": data2, "ships": data3}
        return data
