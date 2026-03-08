import tkinter as tk
from tkinter import ttk

from collections import defaultdict
from datetime import datetime
from itertools import zip_longest

import json
import os.path
import requests

import locale

locale.setlocale(locale.LC_ALL, "")  # Use '' for auto, or force e.g. to 'en_US.UTF-8'

AGENT_FILE = "agents.json"

API_STATUS = "https://api.spacetraders.io/v2/"
LIST_FACTIONS = "https://api.spacetraders.io/v2/factions"
CLAIM_USER = "https://api.spacetraders.io/v2/register"
MY_ACCOUNT = "https://api.spacetraders.io/v2/my/agent"
MY_CONTRACTS = "https://api.spacetraders.io/v2/my/contracts"
MY_SHIPS = "https://api.spacetraders.io/v2/my/ships"

UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
DISPLAY_FORMAT = " %B, %Y"

FACTION_LOOKUPS = {}


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


def get_faction_lookups():
    global FACTION_LOOKUPS
    if len(FACTION_LOOKUPS) > 0:
        return FACTION_LOOKUPS

    try:
        response = requests.get(
            LIST_FACTIONS,
            params={"limit": 20},
        )

        if response.status_code == 200:
            faction_json = response.json()
            for faction in faction_json["data"]:
                FACTION_LOOKUPS[faction["symbol"]] = faction["name"]

        else:
            print("Failed:", response.status_code, response.reason, response.text)

    except ConnectionError as ce:
        print("Failed:", ce)

    return FACTION_LOOKUPS


def generate_faction_combobox():
    faction_combobox["values"] = sorted(get_faction_lookups().values())


def generate_login_combobox():
    known_agents = load_player_logins()
    agent_list = sorted(known_agents.keys(), key=str.casefold)

    id_login["values"] = agent_list


def show_agent_summary(json_result):
    global FACTION_LOOKUPS
    tabs.tab(0, state=tk.DISABLED)
    tabs.tab(1, state=tk.NORMAL)
    tabs.tab(2, state=tk.NORMAL)

    player_token.set(json_result["token"])
    player_login.set(json_result["symbol"])
    player_faction.set(get_faction_lookups()[json_result["startingFaction"]])
    player_worth.set(f"{json_result['credits']:n}")

    tabs.select(1)


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


def login_agent():
    player_token.set(player_login.get())

    # -1 -> user entered a new token, so there won't be a name selected
    if id_login.current() != -1:
        known_agents = load_player_logins()
        player_token.set(known_agents[player_login.get()])

    try:
        response = requests.get(
            MY_ACCOUNT,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {player_token.get()}",
            },
        )
        if response.status_code == 200:
            result = response.json()
            # used to hold the token for later
            result["data"]["token"] = player_token.get()
            show_agent_summary(result["data"])
            # print(result)

            # -1, so now store the agent name / token for future runs
            if id_login.current() == -1:
                store_agent_login(result["data"])

        else:
            print("Failed:", response.status_code, response.reason, response.text)

    except ConnectionError as ce:
        print("Failed:", ce)


def logout_agent():
    tabs.tab(0, state=tk.NORMAL)
    tabs.tab(1, state=tk.DISABLED)
    tabs.tab(2, state=tk.DISABLED)

    player_login.set("")
    player_token.set("")

    tabs.select(0)


def refresh_tabs(event):
    selected_index = tabs.index(tabs.select())
    if selected_index == 1:
        refresh_player_summary()

    elif selected_index == 2:
        refresh_leaderboard()


def refresh_player_summary(*args):
    try:
        response = requests.get(
            MY_ACCOUNT,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {player_token.get()}",
            },
        )
        if response.status_code == 200:
            result = response.json()

            player_worth.set(f"{result['data']['credits']:n}")

        response = requests.get(
            MY_CONTRACTS,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {player_token.get()}",
            },
        )
        if response.status_code == 200:
            result = response.json()
            contract_view.delete(*contract_view.get_children())
            for row in result["data"]:
                if len(row["terms"]["deliver"]) > 0:
                    remaining = (
                        row["terms"]["deliver"][0]["unitsRequired"]
                        - row["terms"]["deliver"][0]["unitsFulfilled"]
                    )
                    contract_view.insert(
                        "",
                        "end",
                        iid=row["id"],
                        text="contract_values",
                        open=True,
                        values=(
                            get_faction_lookups()[row["factionSymbol"]],
                            row["type"],
                            format_datetime(row["terms"]["deadline"]),
                            row["terms"]["deliver"][0]["tradeSymbol"],
                            row["terms"]["deliver"][0]["destinationSymbol"],
                            f"{remaining:n}",
                        ),
                    )
                for subrow, item in enumerate(row["terms"]["deliver"][1:]):
                    contract_view.insert(
                        row["id"],
                        "end",
                        iid=f'{row["id"]}#{subrow}',
                        text="extra_items",
                        values=(
                            "",
                            "",
                            "",
                            item["tradeSymbol"],
                            item["destinationSymbol"],
                            f"{(item['unitsRequired']-item['unitsFulfilled']):n}",
                        ),
                    )

        else:
            print("Failed:", response.status_code, response.reason, response.text)

        response = requests.get(
            MY_SHIPS,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {player_token.get()}",
            },
        )
        if response.status_code == 200:
            result = response.json()
            ship_view.delete(*ship_view.get_children())
            for row in result["data"]:
                modules_and_mounts = list(
                    zip_longest(
                        row["modules"], row["mounts"], fillvalue=defaultdict(str)
                    )
                )
                if len(modules_and_mounts) > 0:
                    module, mount = modules_and_mounts[0]

                ship_view.insert(
                    "",
                    "end",
                    iid=row["symbol"],
                    text="ship_values",
                    open=True,
                    values=(
                        row["symbol"],
                        row["registration"]["role"],
                        row["frame"]["name"],
                        row["reactor"]["name"],
                        row["engine"]["name"],
                        module["name"],
                        mount["name"],
                        f'{row["fuel"]["current"]} / {row["fuel"]["capacity"]}',
                        f'{row["cargo"]["units"]} / {row["cargo"]["capacity"]}',
                    ),
                )
                for subrow, (module, mount) in enumerate(modules_and_mounts[1:]):
                    ship_view.insert(
                        row["symbol"],
                        "end",
                        iid=f'{row["symbol"]}#{subrow}',
                        text="modules_and_mounts",
                        values=(
                            "",
                            "",
                            "",
                            "",
                            "",
                            module["name"],
                            mount["name"],
                            "",
                            "",
                        ),
                    )

        else:
            print("Failed:", response.status_code, response.reason, response.text)

    except ConnectionError as ce:
        print("Failed:", ce)


def display_clicked_contract(*args):
    print(contract_view.index(contract_view.focus()), contract_view.focus())


def display_clicked_ship(*args):
    print(ship_view.index(ship_view.focus()), ship_view.focus())


def refresh_leaderboard(*args):
    try:
        response = requests.get(
            API_STATUS,
            params={"token": player_token.get()},
        )
        if response.status_code == 200:
            result = response.json()
            credits_leaderboard_view.delete(*credits_leaderboard_view.get_children())
            for rank, row in enumerate(result["leaderboards"]["mostCredits"]):
                credits_leaderboard_view.insert(
                    "",
                    "end",
                    text="values",
                    values=(rank + 1, row["agentSymbol"], f"{row['credits']:n}"),
                )

            charts_leaderboard_view.delete(*charts_leaderboard_view.get_children())
            for rank, row in enumerate(result["leaderboards"]["mostSubmittedCharts"]):
                charts_leaderboard_view.insert(
                    "",
                    "end",
                    text="values",
                    values=(rank + 1, row["agentSymbol"], f"{row['chartCount']:n}"),
                )

        else:
            print("Failed:", response.status_code, response.reason, response.text)

    except ConnectionError as ce:
        print("Failed:", ce)


###
# Root window, with app title
#
root = tk.Tk()
root.title("Io Space Trading")

# Main themed frame, for all other widgets to rest upon
main = ttk.Frame(root, padding="3 3 12 12")
main.grid(sticky=tk.NSEW)

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Tabbed widget for rest of the app to run in
tabs = ttk.Notebook(main)
tabs.grid(sticky=tk.NSEW)
tabs.bind("<<NotebookTabChanged>>", refresh_tabs)

main.columnconfigure(0, weight=1)
main.rowconfigure(0, weight=1)

# setup the three main tabs
welcome = ttk.Frame(tabs)
summary = ttk.Frame(tabs)
leaderboard = ttk.Frame(tabs)

tabs.add(welcome, text="Welcome")
tabs.add(summary, text="Summary")
tabs.add(leaderboard, text="Leaderboard")

tabs.tab(1, state=tk.DISABLED)
tabs.tab(2, state=tk.DISABLED)

###
# agent registration/login tab
#

welcome_frame = ttk.Frame(welcome)
welcome_frame.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)

# left hand frame will check/register new agents and return/store the UUID
register = ttk.LabelFrame(welcome_frame, text="Register", relief="groove", padding=5)
register.grid(sticky=tk.NSEW)

# widgets required on the left are a label, an entry, a dropdown, and a button
agent_name = tk.StringVar()
agent_faction = tk.StringVar()
ttk.Label(
    register, text="Enter a new agent name\nto start a new account", anchor=tk.CENTER
).grid(sticky=tk.EW)
faction_combobox = ttk.Combobox(
    register, textvariable=agent_faction, postcommand=generate_faction_combobox
)
faction_combobox.grid(row=1, column=0, sticky=tk.EW)
ttk.Entry(register, textvariable=agent_name).grid(row=2, column=0, sticky=tk.EW)
ttk.Button(register, text="Register new agent", command=register_agent).grid(
    row=3, column=0, columnspan=2, sticky=tk.EW
)

register.columnconfigure(0, weight=1)
register.rowconfigure(0, weight=1)

ttk.Label(welcome_frame, text="or", padding=10, anchor=tk.CENTER).grid(
    row=0, column=1, sticky=tk.EW
)

# right hand frame will allow to choose from known players and/or paste in existing
# UUID to login and play as that agent
login = ttk.LabelFrame(welcome_frame, text="Login", relief=tk.GROOVE, padding=5)
login.grid(row=0, column=2, sticky=tk.NSEW)

# widgets required on the right are a dropdown, and a button
player_login = tk.StringVar()
player_token = (
    tk.StringVar()
)  # going to use this to remember the currently logged in agent
ttk.Label(login, text="Choose the agent to play as\nor paste an existing id").grid(
    sticky=tk.EW
)
id_login = ttk.Combobox(
    login, textvariable=player_login, postcommand=generate_login_combobox
)
id_login.grid(row=1, column=0, sticky=tk.EW)
ttk.Button(login, text="Login agent", command=login_agent).grid(
    row=2, column=0, columnspan=2, sticky=tk.EW
)

login.columnconfigure(0, weight=1)
login.rowconfigure(0, weight=1)

welcome_frame.columnconfigure(0, weight=1)
welcome_frame.columnconfigure(2, weight=1)
welcome_frame.rowconfigure(0, weight=1)

welcome.columnconfigure(0, weight=1)
welcome.rowconfigure(0, weight=1)

###
# summary tab
#

player_summary = ttk.LabelFrame(summary, text="Agent", relief=tk.GROOVE, padding=5)

player_faction = tk.StringVar()
player_worth = tk.StringVar()

ttk.Label(player_summary, textvariable=player_login, anchor=tk.CENTER).grid(
    columnspan=2, sticky=tk.EW
)
ttk.Label(player_summary, text="Faction:").grid(row=1, column=0, sticky=tk.W)
ttk.Label(player_summary, textvariable=player_faction, anchor=tk.CENTER).grid(
    row=1, column=1, sticky=tk.EW
)
ttk.Label(player_summary, text="Credits:").grid(row=2, column=0, sticky=tk.W)
ttk.Label(player_summary, textvariable=player_worth, anchor=tk.CENTER).grid(
    row=2, column=1, sticky=tk.EW
)
ttk.Button(player_summary, text="Logout", command=logout_agent).grid(
    row=3, column=0, columnspan=2, sticky=tk.EW
)

player_summary.columnconfigure(0, weight=1)

contract_summary = ttk.LabelFrame(
    summary, text="Contracts", relief=tk.GROOVE, padding=5
)

contract_view = ttk.Treeview(
    contract_summary,
    height=3,
    columns=("Faction", "Type", "Deadline", "Goods", "Destination", "Owing"),
    show="headings",
)
contract_view.column("Faction", anchor=tk.W, width=20)
contract_view.column("Type", anchor=tk.W, width=20)
contract_view.column("Deadline", anchor=tk.W, width=20)
contract_view.column("Goods", anchor=tk.W, width=30)
contract_view.column("Destination", anchor=tk.W, width=20)
contract_view.column("Owing", anchor=tk.E, width=20)
contract_view.heading("#1", text="Faction")
contract_view.heading("#2", text="Type")
contract_view.heading("#3", text="Deadline")
contract_view.heading("#4", text="Goods")
contract_view.heading("#5", text="Destination")
contract_view.heading("#6", text="Owing")
contract_view.grid(sticky=tk.NSEW)
contract_scroll = ttk.Scrollbar(
    contract_summary, orient=tk.VERTICAL, command=contract_view.yview
)
contract_scroll.grid(column=1, row=0, sticky=tk.NS)
contract_view.config(yscrollcommand=contract_scroll.set)
contract_view.bind("<Double-1>", display_clicked_contract)

contract_summary.columnconfigure(0, weight=1)
contract_summary.rowconfigure(0, weight=1)

ship_summary = ttk.LabelFrame(summary, text="Ships", relief=tk.GROOVE, padding=5)
ship_view = ttk.Treeview(
    ship_summary,
    height=3,
    columns=(
        "Registration",
        "Role",
        "Frame",
        "Reactor",
        "Engine",
        "Modules",
        "Mounts",
        "Fuel",
        "Cargo",
    ),
    show="headings",
)
ship_view.column("Registration", anchor=tk.W, width=30)
ship_view.column("Role", anchor=tk.W, width=30)
ship_view.column("Frame", anchor=tk.W, width=30)
ship_view.column("Reactor", anchor=tk.W, width=30)
ship_view.column("Engine", anchor=tk.W, width=30)
ship_view.column("Modules", anchor=tk.W, width=30)
ship_view.column("Mounts", anchor=tk.W, width=30)
ship_view.column("Fuel", anchor=tk.E, width=20)
ship_view.column("Cargo", anchor=tk.E, width=20)
ship_view.heading("#1", text="Registration")
ship_view.heading("#2", text="Role")
ship_view.heading("#3", text="Frame")
ship_view.heading("#4", text="Reactor")
ship_view.heading("#5", text="Engine")
ship_view.heading("#6", text="Modules")
ship_view.heading("#7", text="Mounts")
ship_view.heading("#8", text="Fuel")
ship_view.heading("#9", text="Cargo")
ship_view.grid(sticky=tk.NSEW)
ship_scroll = ttk.Scrollbar(ship_summary, orient=tk.VERTICAL, command=ship_view.yview)
ship_scroll.grid(column=1, row=0, sticky=tk.NS)
ship_view.config(yscrollcommand=ship_scroll.set)
ship_view.bind("<Double-1>", display_clicked_ship)

ship_summary.columnconfigure(0, weight=1)
ship_summary.rowconfigure(0, weight=1)


player_summary.grid(row=0, column=0, sticky=tk.NSEW)
contract_summary.grid(row=0, column=1, sticky=tk.NSEW)
ship_summary.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)

summary.columnconfigure(0, weight=1)
summary.columnconfigure(1, weight=3)
summary.rowconfigure(0, weight=2)
summary.rowconfigure(1, weight=3)

###
# leaderboard tab
#

credits_leaderboard_view = ttk.Treeview(
    leaderboard, height=6, columns=("Rank", "Agent", "Credits"), show="headings"
)
credits_leaderboard_view.column("Rank", anchor=tk.CENTER, width=10)
credits_leaderboard_view.column("Agent", anchor=tk.W, width=100)
credits_leaderboard_view.column("Credits", anchor=tk.E, width=100)
credits_leaderboard_view.heading("#1", text="Rank")
credits_leaderboard_view.heading("#2", text="Agent")
credits_leaderboard_view.heading("#3", text="Credits")
credits_leaderboard_view.grid(sticky=tk.NSEW)
credits_scroll = ttk.Scrollbar(
    leaderboard, orient=tk.VERTICAL, command=credits_leaderboard_view.yview
)
credits_scroll.grid(column=1, row=0, sticky=tk.NS)
credits_leaderboard_view.config(yscrollcommand=credits_scroll.set)

charts_leaderboard_view = ttk.Treeview(
    leaderboard, height=6, columns=("Rank", "Agent", "Chart Count"), show="headings"
)
charts_leaderboard_view.column("Rank", anchor=tk.CENTER, width=10)
charts_leaderboard_view.column("Agent", anchor=tk.W, width=100)
charts_leaderboard_view.column("Chart Count", anchor=tk.E, width=100)
charts_leaderboard_view.heading("#1", text="Rank")
charts_leaderboard_view.heading("#2", text="Agent")
charts_leaderboard_view.heading("#3", text="Chart Count")
charts_leaderboard_view.grid(sticky=tk.NSEW)
charts_scroll = ttk.Scrollbar(
    leaderboard, orient=tk.VERTICAL, command=charts_leaderboard_view.yview
)
charts_scroll.grid(column=1, row=1, sticky=tk.NS)
charts_leaderboard_view.config(yscrollcommand=charts_scroll.set)

refresh = ttk.Button(leaderboard, text="Refresh", command=refresh_leaderboard)
refresh.grid(column=0, row=2, sticky=tk.EW)

leaderboard.columnconfigure(0, weight=1)
leaderboard.rowconfigure((0, 1), weight=1)

root.mainloop()
