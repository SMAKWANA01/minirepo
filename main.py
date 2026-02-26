import json
import requests

#------------------------CONSTANTS------------------------#
API_STATUS = "https://api.spacetraders.io/v2/"
LIST_FACTIONS = "https://api.spacetraders.io/v2/factions"
CLAIM_USER = "https://api.spacetraders.io/v2/register"
MY_ACCOUNT = "https://api.spacetraders.io/v2/my/agent"
MY_CONTRACTS = "https://api.spacetraders.io/v2/my/contracts"
MY_SHIPS = "https://api.spacetraders.io/v2/my/ships"

def register_agent(): 
    try:
        username = agent_name.get()
        faction = next(
            iter(
                [
                    symbol
                    for symbol, name in get_faction_lookups().items()
                    if name == agent_faction.get()
                ]
            )
        )

        response = requests.post(
            CLAIM_USER,
            data={"faction": faction, "symbol": username},
        )
        if response.status_code < 400:
            result = response.json()
            # used to hold the token for later
            result["data"]["agent"]["token"] = result["data"]["token"]
            store_agent_login(result["data"]["agent"])
            show_agent_summary(result["data"]["agent"])
            agent_name.set("")
        else:
            print("Failed:", response.status_code, response.reason, response.text)

    except StopIteration:
        print("Did they pick a faction?")

    except ConnectionError as ce:
        print("Failed:", ce)