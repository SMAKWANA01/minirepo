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

    #TODO: Is this just a procedure then ?
    def accept(self):
        response = requests.post(MY_CONTRACTS +f"/{self.id}/accept", headers={"Authorization": f"Bearer {self.token}"})
        if response.status_code != 200:
            print("Something went wrong, Agent class load_contract")
            print(response.text)# Only for debugging
            raise Exception(response.status_code, response.reason)
        self.accepted = True
        self.deadlineToAccept = None
    
    #TODO: get ship info, bring into cargo (from agent?) then fulfill contract.
    #combine orbit with navigate



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
        data = {**data, "contracts": data2}
        return data
