import json
import os
import requests


#------------------------CONSTANTS------------------------#
API_STATUS = "https://api.spacetraders.io/v2/"
LIST_FACTIONS = "https://api.spacetraders.io/v2/factions"
CLAIM_USER = "https://api.spacetraders.io/v2/register"
MY_ACCOUNT = "https://api.spacetraders.io/v2/my/agent"
MY_CONTRACTS = "https://api.spacetraders.io/v2/my/contracts"
MY_SHIPS = "https://api.spacetraders.io/v2/my/ships"



class Contracts():
    def __init__(self, data):
        self.id = data["id"]
        self.faction = data["factionSymbol"]
        self.type = data["type"]
        self.deadline = data["terms"]["deadline"]
        self.paymet_onAccepted = data["terms"]["onAccepted"]
        self.paymet_onFulfilled = data["terms"]["onFulfilled"]

        self.accepted = data["accepted"]
        self.fulfilled = data["fulfilled"]
        self.expiration = data["expiration"]
        self.deadlineToAccept = data["deadlineToAccept"]

        #These are for where we need to deliver!
        self.tradeSymbol = data["deliver"]["tradeSymbol"]
        self.destinationSymbol = data["deliver"]["destinationSymbol"]
        self.unitsRequired = data["deliver"]["unitsRequired"]
        self.unitsFulfilled = data["deliver"]["unitsFulfilled"]

        


class Agent:
    TOKEN_FILE = "agents.json"  

    def __init__(self,  token= ""):
        if token:
            self.token = token
            self._save_token(token)
        else:
            saved = self._load_token()
            if saved:
                self.token = saved
            else:
                self.error = "No token provided and no saved token found."
        
        self.error = None
        self.accountId = None
        self.symbol = None
        self.headquarters = None
        self.credits = None
        self.faction = None
        self.shipCount = None

    # Using internal functions 
    def _load_token(self):
        if not os.path.exists(self.TOKEN_FILE):
            return None
        
        try:
            with open(self.TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("token")
            
        except Exception as e:
            print("Error in class agent, loading token: ", e)
            return None

    def _save_token(self, token):
        with open(self.TOKEN_FILE, "w") as f:
            json.dump({"token": token}, f)


    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    #NOT internal function, I'll call this once in main.
    def get_agent_data(self):
        response = requests.get(MY_ACCOUNT, headers=self._headers())

        if response.status_code != 200:
            print("Something went wrong, Agent class get_agent_data")
            self.error = {
                "error": True,
                "status": response.status_code,
                "message": response.text   
            }
            print(self.error)# Using this because its not working..
            return False
        
        data = response.json()["data"]
        self.accountId = data["accountId"]
        self.symbol = data["symbol"]
        self.headquarters = data["headquarters"]
        self.credits = data["credits"]
        self.faction = data["startingFaction"]
        self.shipCount = data["shipCount"]
        return True
