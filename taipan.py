#!/usr/bin/env python3
"""TAIPAN!  A game based on the China trade of the 1800's.

Faithful Python port of Art Canfil's TAIPAN (1982, Apple II).
Recreated from the C source by Jay Link (taipan.c, v0.9).
All prices, probabilities, and formulas match the original.
"""

import os
import random
import sys

# ── Constants ──────────────────────────────────────────────────────

GENERIC = 1
LI_YUEN = 2

BATTLE_NOT_FINISHED = 0
BATTLE_WON = 1
BATTLE_INTERRUPTED = 2
BATTLE_FLED = 3
BATTLE_LOST = 4

ITEMS = ["Opium", "Silk", "Arms", "General Cargo"]

LOCATIONS = [
    "At sea",
    "Hong Kong",
    "Shanghai",
    "Nagasaki",
    "Saigon",
    "Manila",
    "Singapore",
    "Batavia",
]

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# st[i] where i = status // 20  (status is 0..100, so i is 0..5)
SHIP_STATUS = ["Critical", "  Poor", "  Fair", "  Good", " Prime", "Perfect"]

# base_price[good][port] — col 0 is the scale anchor
BASE_PRICE = [
    [1000, 11, 16, 15, 14, 12, 10, 13],   # Opium
    [100,  11, 14, 15, 16, 10, 13, 12],    # Silk
    [10,   12, 16, 10, 11, 13, 14, 15],    # Arms
    [1,    10, 11, 12, 13, 14, 15, 16],    # General
]

WAREHOUSE_CAP = 10000
RETIRE_THRESHOLD = 1000000


# ── Game State ─────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.firm = ""
        self.cash = 0
        self.bank = 0
        self.debt = 0
        self.booty = 0
        self.ec = 20.0       # enemy base health, grows +10/year
        self.ed = 0.5        # enemy base damage, grows +0.5/year
        self.price = [0, 0, 0, 0]
        self.hkw = [0, 0, 0, 0]   # warehouse
        self.hold_ = [0, 0, 0, 0]  # ship cargo
        self.hold = 0             # free hold space
        self.capacity = 60
        self.guns = 0
        self.bp = 0              # pirate encounter basis
        self.damage = 0
        self.month = 1
        self.year = 1860
        self.li = 0             # Li Yuen status: 0=hostile, 1+=cooling
        self.port = 1           # 1=HK, 2=Shanghai, ... 7=Batavia
        self.wu_warn = 0
        self.wu_bailout = 0


# ── Utilities ──────────────────────────────────────────────────────

def fancy_numbers(num):
    """Format a number in TAIPAN's style."""
    n = int(num)
    if n >= 1000000:
        whole = n // 1000000
        frac = (n % 1000000) * 100 // 1000000
        return f"{whole}.{frac:02d} Million"
    else:
        return f"{n:,}"


def get_one(prompt=""):
    """Read a single character."""
    if prompt:
        print(prompt, end="", flush=True)
    while True:
        try:
            ch = sys.stdin.readline()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not ch:  # EOF
            print()
            sys.exit(0)
        ch = ch.strip()
        if ch:
            return ch[0]


def get_num(maxlen):
    """Read a number string; 'A' or 'a' = -1 (means 'all/max')."""
    while True:
        try:
            s = sys.stdin.readline()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not s:  # EOF
            print()
            sys.exit(0)
        s = s.strip()
        if not s:
            continue
        if s == "A" or s == "a":
            return -1
        try:
            return int(s)
        except ValueError:
            continue


def pause(msg="[Press Enter to continue...]"):
    print(msg, end="", flush=True)
    try:
        line = sys.stdin.readline()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if not line:  # EOF
        print()
        sys.exit(0)


# ── Core Functions ─────────────────────────────────────────────────

def set_prices(g):
    """price[i] = base_price[i][port] / 2 * (rand()%3 + 1) * base_price[i][0]
    C integer division throughout."""
    for i in range(4):
        bp = BASE_PRICE[i][g.port]
        scale = BASE_PRICE[i][0]
        g.price[i] = (bp // 2) * (random.randint(0, 2) + 1) * scale


def port_stats(g):
    """Display the main status screen."""
    status = 100 - int((float(g.damage) / g.capacity) * 100)
    if status < 0:
        status = 0
    si = status // 20
    if si > 5:
        si = 5
    in_use = sum(g.hkw)

    print()
    print(f"  Firm: {g.firm}, Hong Kong")
    print(" ______________________________________")
    print("|Hong Kong Warehouse                   |     Date")
    print("|   Opium           In Use:            |")
    print("|   Silk                               |")
    print("|   Arms            Vacant:            |   Location")
    print("|   General                            |")
    print("|______________________________________|")
    print("|Hold               Guns               |     Debt")
    print("|   Opium                              |")
    print("|   Silk                               |")
    print("|   Arms                               |  Ship Status")
    print("|   General                            |")
    print("|______________________________________|")
    print("Cash:               Bank:")
    print("________________________________________")

    # Warehouse items
    print(f"   Opium: {g.hkw[0]:<20d} In Use: {in_use}")
    print(f"   Silk:  {g.hkw[1]:<20d} Vacant: {WAREHOUSE_CAP - in_use}")
    print(f"   Arms:  {g.hkw[2]:<20d} Location: {LOCATIONS[g.port]}")
    print(f"   General: {g.hkw[3]:<16d} Debt: {fancy_numbers(g.debt)}")

    # Hold
    hold_display = f"{g.hold}" if g.hold >= 0 else "OVERLOAD"
    print(f"|Hold: {hold_display:<10s}  Guns: {g.guns:<12d} Ship: {SHIP_STATUS[si]}:{status}%|")
    print(f"|   Opium: {g.hold_[0]:<8d}  Silk: {g.hold_[1]:<8d}  |")
    print(f"|   Arms:  {g.hold_[2]:<8d}  General: {g.hold_[3]:<8d}|")
    print("|______________________________________|")
    print(f"  Cash: {fancy_numbers(g.cash):<20s} Bank: {fancy_numbers(g.bank)}")
    print(f"  Date: 15 {MONTHS[g.month - 1]} {g.year}")
    print("________________________________________")


def fight_stats(g, num_ships, orders):
    """Battle status display."""
    if orders == 1:
        ch = "Fight"
    elif orders == 2:
        ch = "Run"
    else:
        ch = "Throw Cargo"

    if num_ships == 1:
        ship_word = "ship attacking, Taipan!"
    else:
        ship_word = "ships attacking, Taipan!"

    print(f"  {num_ships} {ship_word}")
    print(f"  Your orders are to: {ch}")
    print(f"  We have {g.guns} {'gun' if g.guns == 1 else 'guns'}")
    print("+---------")


def port_choices(g):
    """Show prices and get player's action choice."""
    print()
    print("Comprador's Report")
    print()
    print("Taipan, present prices per unit here are")
    print(f"   Opium: {g.price[0]:<14d} Silk: {g.price[1]}")
    print(f"   Arms:  {g.price[2]:<14d} General: {g.price[3]}")
    print()

    while True:
        if g.port == 1:
            if (g.cash + g.bank) >= RETIRE_THRESHOLD:
                print("Shall I Buy, Sell, Visit bank, Transfer")
                print("cargo, Wheedle Wu, Quit trading, or Retire?")
            else:
                print("Shall I Buy, Sell, Visit bank, Transfer")
                print("cargo, Wheedle Wu, or Quit trading?")
        else:
            print("Shall I Buy, Sell, or Quit trading?")

        choice = get_one("? ").upper()
        valid_hk = ["B", "S", "V", "T", "W", "Q", "R"]
        valid_foreign = ["B", "S", "Q"]
        valid = valid_hk if g.port == 1 else valid_foreign
        if choice in valid:
            return choice


def buy(g):
    """Buy cargo."""
    item_map = {"O": 0, "S": 1, "A": 2, "G": 3}
    while True:
        print("What do you wish me to buy, Taipan?")
        print("  (O)pium, (S)ilk, (A)rms, (G)eneral, or <Enter to cancel>?")
        ch = get_one("? ").upper()
        if ch in item_map:
            choice = item_map[ch]
            break
        return

    while True:
        if g.price[choice] == 0:
            print("Cannot buy this here, Taipan!")
            return
        afford = g.cash // g.price[choice]
        print(f"  You can afford {afford}.")
        print(f"  You have {g.hold} hold space.")
        # C: max you can buy is min(afford, hold)
        max_buy = min(afford, g.hold)
        if max_buy <= 0:
            print("You cannot buy any, Taipan!")
            return
        print(f"  (Max: {max_buy}, or 'A' for max)")
        amount = get_num(9)
        if amount == -1:
            amount = max_buy
        if amount <= afford and amount <= g.hold:
            break
        if amount > afford:
            print("Taipan, you do not have enough cash!!")
        else:
            print("Not enough hold space, Taipan!!")

    g.cash -= amount * g.price[choice]
    g.hold_[choice] += amount
    g.hold -= amount
    port_stats(g)


def sell(g):
    """Sell cargo."""
    item_map = {"O": 0, "S": 1, "A": 2, "G": 3}
    while True:
        print("What do you wish me to sell, Taipan?")
        print("  (O)pium, (S)ilk, (A)rms, (G)eneral, or <Enter to cancel>?")
        ch = get_one("? ").upper()
        if ch in item_map:
            choice = item_map[ch]
            break
        return

    if g.hold_[choice] == 0:
        print(f"You have no {ITEMS[choice]}, Taipan!")
        return

    while True:
        print(f"How much {ITEMS[choice]} shall I sell, Taipan?")
        print(f"  (You have {g.hold_[choice]}, 'A' for all)")
        amount = get_num(9)
        if amount == -1:
            amount = g.hold_[choice]
        if g.hold_[choice] >= amount and amount > 0:
            break
        print(f"You have only {g.hold_[choice]}, Taipan.")

    g.hold_[choice] -= amount
    g.cash += amount * g.price[choice]
    g.hold += amount
    port_stats(g)


def visit_bank(g):
    """Deposit and withdraw from the bank (HK only)."""
    # Deposit
    while True:
        print("Comprador's Report")
        print()
        print(f"How much will you deposit?  (Cash: {fancy_numbers(g.cash)}, 'A' for all)")
        amount = get_num(9)
        if amount == -1:
            amount = g.cash
        if amount <= g.cash:
            g.cash -= amount
            g.bank += amount
            break
        print(f"Taipan, you only have {fancy_numbers(g.cash)} in cash.")

    port_stats(g)

    # Withdraw
    while True:
        print("Comprador's Report")
        print()
        print(f"How much will you withdraw?  (Bank: {fancy_numbers(g.bank)}, 'A' for all)")
        amount = get_num(9)
        if amount == -1:
            amount = g.bank
        if amount <= g.bank:
            g.cash += amount
            g.bank -= amount
            break
        print(f"Taipan, you only have {fancy_numbers(g.bank)} in the bank.")

    port_stats(g)


def transfer(g):
    """Transfer cargo between ship and warehouse (HK only)."""
    if all(g.hkw[i] == 0 and g.hold_[i] == 0 for i in range(4)):
        print("You have no cargo, Taipan.")
        return

    item_map = {"O": 0, "S": 1, "A": 2, "G": 3}

    for i in range(4):
        if g.hold_[i] > 0:
            port_stats(g)
            while True:
                print(f"How much {ITEMS[i]} shall I move to the warehouse, Taipan?")
                print(f"  (You have {g.hold_[i]} aboard, 'A' for all)")
                amount = get_num(9)
                if amount == -1:
                    amount = g.hold_[i]
                if amount <= g.hold_[i]:
                    in_use = sum(g.hkw)
                    if (in_use + amount) <= WAREHOUSE_CAP:
                        g.hold_[i] -= amount
                        g.hkw[i] += amount
                        g.hold += amount
                        break
                    avail = WAREHOUSE_CAP - in_use
                    print(f"Your warehouse will only hold an additional {avail}, Taipan!")
                else:
                    print(f"You have only {g.hold_[i]}, Taipan.")

    for i in range(4):
        if g.hkw[i] > 0:
            port_stats(g)
            while True:
                print(f"How much {ITEMS[i]} shall I move aboard ship, Taipan?")
                print(f"  (Warehouse has {g.hkw[i]}, 'A' for all)")
                amount = get_num(9)
                if amount == -1:
                    amount = g.hkw[i]
                if amount <= g.hkw[i]:
                    g.hkw[i] -= amount
                    g.hold_[i] += amount
                    g.hold -= amount
                    break
                print(f"You have only {g.hkw[i]}, Taipan.")


def elder_brother_wu(g):
    """Elder Brother Wu — moneylender (HK only)."""
    print()
    print("Comprador's Report")
    print()
    print("Do you have business with Elder Brother Wu, the moneylender?")

    while True:
        choice = get_one("(Y/N)? ").upper()
        if choice == "N":
            break
        elif choice == "Y":
            # BAILOUT: totally broke (no cash, bank, guns, cargo, warehouse)
            if (int(g.cash) == 0 and int(g.bank) == 0 and g.guns == 0 and
                    all(g.hold_[i] == 0 and g.hkw[i] == 0 for i in range(4))):
                i = random.randint(0, 1499) + 500
                g.wu_bailout += 1
                j = random.randint(0, 1999) * g.wu_bailout + 1500

                while True:
                    print("Comprador's Report")
                    print()
                    print(f"Elder Brother is aware of your plight, Taipan.")
                    print(f"He is willing to loan you an additional {i} if you will pay back {j}.")
                    print("Are you willing, Taipan?")
                    choice2 = get_one("(Y/N)? ").upper()
                    if choice2 == "N":
                        print("Very well, Taipan, the game is over!")
                        pause()
                        final_stats(g)
                        return
                    elif choice2 == "Y":
                        g.cash += i
                        g.debt += j
                        port_stats(g)
                        print("Very well, Taipan.  Good joss!!")
                        pause()
                        return

            # REPAY: has cash and has debt
            elif g.cash > 0 and g.debt != 0:
                while True:
                    print("Comprador's Report")
                    print()
                    print("How much do you wish to repay him?")
                    print(f"  (Cash: {fancy_numbers(g.cash)}, Debt: {fancy_numbers(g.debt)}, 'A' for max)")
                    wu = get_num(9)
                    if wu == -1:
                        wu = min(g.cash, g.debt)
                    if wu <= g.cash:
                        if wu > g.debt:
                            print(f"Taipan, you owe only {fancy_numbers(g.debt)}.")
                            print("Paid in full.")
                            wu = g.debt
                        g.cash -= wu
                        # C quirk: if wu > debt and debt > 0, debt -= (wu+1); else debt -= wu
                        if wu > g.debt and g.debt > 0:
                            g.debt -= (wu + 1)
                        else:
                            g.debt -= wu
                        if g.debt < 0:
                            g.debt = 0
                        break
                    else:
                        print(f"Taipan, you only have {fancy_numbers(g.cash)} in cash.")
                        pause()
                port_stats(g)

            # BORROW: has cash, no debt (or repaid)
            # After repay loop, fall through to borrow section
            while True:
                print("Comprador's Report")
                print()
                print("How much do you wish to borrow?")
                print(f"  (Max: {g.cash * 2}, 'A' for max)")
                wu = get_num(9)
                if wu == -1:
                    wu = g.cash * 2
                if wu <= (g.cash * 2):
                    g.cash += wu
                    g.debt += wu
                    break
                else:
                    print("He won't loan you so much, Taipan!")
                    pause()
            port_stats(g)
            break

    # Bodyguard robbery: debt > 20000, cash > 0, 1-in-5
    if g.debt > 20000 and g.cash > 0 and random.randint(0, 4) == 0:
        num = random.randint(0, 2) + 1
        g.cash = 0
        port_stats(g)
        print()
        print("Comprador's Report")
        print()
        print("Bad joss!!")
        print(f"{num} of your bodyguards have been killed")
        print("by cutthroats and you have been robbed")
        print("of all of your cash, Taipan!!")
        pause()


def li_yuen_extortion(g):
    """Li Yuen demands a donation (every HK arrival when li==0)."""
    time = ((g.year - 1860) * 12) + g.month
    i = 1.8
    j = 0

    if time > 12:
        j = random.randint(0, 1000 * time - 1) + (1000 * time)
        i = 1

    amount = int((g.cash / i) * random.random()) + j

    print()
    print("Comprador's Report")
    print()
    print(f"Li Yuen asks {fancy_numbers(amount)} in donation")
    print("to the temple of Tin Hau, the Sea")
    print("Goddess, Taipan.  Will you pay?")

    while True:
        choice = get_one("(Y/N)? ").upper()
        if choice in ("Y", "N"):
            break

    if choice == "Y":
        if amount <= g.cash:
            g.cash -= amount
        else:
            # Can't afford — Wu makes up the difference
            print()
            print("Taipan, you do not have enough cash!!")
            print("Do you want Elder Brother Wu to make up")
            print("the difference for you?")
            while True:
                ch2 = get_one("(Y/N)? ").upper()
                if ch2 in ("Y", "N"):
                    break
            if ch2 == "Y":
                diff = amount - g.cash
                g.cash = 0
                g.debt += diff
                print("Elder Brother has given Li Yuen the")
                print("difference between what he wanted and")
                print("your cash on hand and added the same")
                print("amount to your debt.")
            else:
                g.cash = 0
                print("Very well. Elder Brother Wu will not pay")
                print("Li Yuen the difference.  I would be very")
                print("wary of pirates if I were you, Taipan.")
        g.li = 1
    else:
        # Refuse
        print()
        print("Li Yuen smiles at your refusal, Taipan.")
        print("He says, 'You are a brave man.'")
        print("Be very wary of pirates!")
        # li stays 0 (hostile)

    pause()
    port_stats(g)


def good_prices(g):
    """Random price event — 1-in-9 per port arrival."""
    i = random.randint(0, 3)
    j = random.randint(0, 1)

    print()
    print("Comprador's Report")
    print()
    print(f"Taipan!!  The price of {ITEMS[i]}")
    if j == 0:
        g.price[i] = g.price[i] // 5
        print(f"has dropped to {g.price[i]}!!")
    else:
        g.price[i] = g.price[i] * (random.randint(0, 4) + 5)
        print(f"has risen to {g.price[i]}!!")

    pause()
    port_stats(g)


def new_ship(g):
    """Shipyard offers +50 capacity (1-in-4 arrivals, 50% chance)."""
    time = ((g.year - 1860) * 12) + g.month
    # C: rand()%(1000 * (time + 5) / 6) * (capacity / 50) + 1000
    amount = random.randint(0, (1000 * (time + 5)) // 6 - 1) * (g.capacity // 50) + 1000

    if g.cash < amount:
        return

    print()
    print("Comprador's Report")
    print()
    print(f"Do you wish to trade in your {'damaged' if g.damage > 0 else 'fine'}")
    print(f"ship for one with 50 more capacity by")
    print(f"paying an additional {fancy_numbers(amount)}, Taipan?")

    while True:
        choice = get_one("(Y/N)? ").upper()
        if choice in ("Y", "N"):
            break

    if choice == "Y":
        g.cash -= amount
        g.hold += 50
        g.capacity += 50
        g.damage = 0

    # 50% chance of also offering a gun
    if random.randint(0, 1) == 0 and g.guns < 1000:
        port_stats(g)
        new_gun(g)

    port_stats(g)


def new_gun(g):
    """Shipyard offers a gun (1-in-4 arrivals, 50% chance)."""
    time = ((g.year - 1860) * 12) + g.month
    # C: rand()%(1000 * (time + 5) / 6) + 500
    amount = random.randint(0, (1000 * (time + 5)) // 6 - 1) + 500

    if g.cash < amount or g.hold < 10:
        return

    print()
    print("Comprador's Report")
    print()
    print(f"Do you wish to buy a ship's gun for {fancy_numbers(amount)}, Taipan?")

    while True:
        choice = get_one("(Y/N)? ").upper()
        if choice in ("Y", "N"):
            break

    if choice == "Y":
        g.cash -= amount
        g.hold -= 10
        g.guns += 1

    port_stats(g)


def mchenry(g):
    """McHenry from the HK shipyards offers repairs (when damage > 0)."""
    print()
    print("Comprador's Report")
    print()
    print("Taipan, Mc Henry from the Hong Kong")
    print('Shipyards has arrived!!  He says, "I see')
    print('ye\'ve a wee bit of damage to yer ship.')
    print('Will ye be wanting repairs?')

    while True:
        choice = get_one("(Y/N)? ").upper()
        if choice in ("Y", "N"):
            break

    if choice == "Y":
        percent = int((float(g.damage) / g.capacity) * 100)
        time = ((g.year - 1860) * 12) + g.month
        # C: br = ((((60 * (time + 3) / 4) * rand()/RAND_MAX) + 25 * (time + 3) / 4) * capacity / 50)
        br = int((((60 * (time + 3) // 4) * random.random()) +
                  25 * (time + 3) // 4) * g.capacity / 50)
        repair_price = (br * g.damage) + 1

        print(f"Och, 'tis a pity to be {percent}% damaged.")
        print(f"We can fix yer whole ship for {fancy_numbers(repair_price)},")
        print("or make partial repairs if you wish.")
        print("How much will ye spend?")

        while True:
            amount = get_num(9)
            if amount == -1:
                amount = repair_price
            if amount <= g.cash:
                # Partial repair: damage reduced proportionally
                if amount >= repair_price:
                    g.damage = 0
                else:
                    # proportional: damage -= (amount / repair_price) * damage
                    # C: diff = amount - cash handled as Wu difference
                    g.damage = int(g.damage - (float(amount) / repair_price) * g.damage)
                    if g.damage < 0:
                        g.damage = 0
                g.cash -= amount
                break
            else:
                # Wu can make up the difference
                diff = amount - g.cash
                print(f"Taipan, you do not have enough cash!!")
                print("Do you want Elder Brother Wu to make up")
                print("the difference for you?")
                while True:
                    ch2 = get_one("(Y/N)? ").upper()
                    if ch2 in ("Y", "N"):
                        break
                if ch2 == "Y":
                    g.debt += diff
                    amount2 = g.cash
                    g.cash = 0
                    if (amount2 + diff) >= repair_price:
                        g.damage = 0
                    else:
                        g.damage = int(g.damage - (float(amount2 + diff) / repair_price) * g.damage)
                        if g.damage < 0:
                            g.damage = 0
                    break
                else:
                    print("Very well, no repairs.")
                    break

    port_stats(g)


def overload(g):
    """Ship is overloaded warning."""
    print()
    print("Comprador's Report")
    print()
    print("Your ship is overloaded, Taipan!!")
    pause()


def sea_battle(g, id, num_ships):
    """The naval combat engine. Returns BATTLE_* constant."""
    time = ((g.year - 1860) * 12) + g.month
    s0 = num_ships
    ok = 0
    ik = 1
    orders = 0

    # booty = (time / 4 * 1000 * num_ships) + rand()%1000 + 250
    g.booty = ((time // 4) * 1000 * num_ships) + random.randint(0, 999) + 250

    # Enemy ship HP pool (up to 10 on screen)
    ships_hp = [0] * 10
    num_on_screen = 0

    fight_stats(g, num_ships, orders)

    while num_ships > 0:
        # Check if ship is sinking
        status = 100 - int((float(g.damage) / g.capacity) * 100)
        if status <= 0:
            return BATTLE_LOST

        print(f"  Current seaworthiness: {SHIP_STATUS[status // 20]} ({status}%)")

        # Deploy enemy ships onto screen
        while num_ships > num_on_screen and num_on_screen < 10:
            for idx in range(10):
                if ships_hp[idx] == 0 and num_ships > num_on_screen:
                    ships_hp[idx] = int((g.ec * random.random()) + 20)
                    num_on_screen += 1

        # Show ships
        visible = sum(1 for h in ships_hp if h > 0)
        print(f"  [{visible} ships visible]" + ("+" if num_ships > num_on_screen else ""))
        print()

        # Get orders
        if orders == 0:
            print("Taipan, what shall we do??    (f=Fight, r=Run, t=Throw cargo)")
            while True:
                ch = get_one("? ").upper()
                if ch == "F":
                    orders = 1
                    break
                elif ch == "R":
                    orders = 2
                    break
                elif ch == "T":
                    orders = 3
                    break

        fight_stats(g, num_ships, orders)

        # ── FIGHT ──
        if orders == 1 and g.guns > 0:
            ok = 3
            ik = 1
            print("Aye, we'll fight 'em, Taipan.")
            print("We're firing on 'em, Taipan!")
            sk = 0

            for i in range(1, g.guns + 1):
                # Replenish screen if all sunk
                if all(h == 0 for h in ships_hp) and num_ships > num_on_screen:
                    for idx in range(10):
                        if ships_hp[idx] == 0 and num_ships > num_on_screen:
                            ships_hp[idx] = int((g.ec * random.random()) + 20)
                            num_on_screen += 1

                # Target a random active ship
                active = [idx for idx in range(10) if ships_hp[idx] > 0]
                if not active:
                    break
                targeted = random.choice(active)

                print(f"  ({g.guns - i} shots remaining.)")

                # Damage: rand()%30 + 10
                ships_hp[targeted] -= random.randint(0, 29) + 10
                if ships_hp[targeted] <= 0:
                    num_on_screen -= 1
                    num_ships -= 1
                    sk += 1
                    ships_hp[targeted] = 0

                if num_ships == 0:
                    break

            if sk > 0:
                print(f"Sunk {sk} of the buggers, Taipan!")
            else:
                print("Hit 'em, but didn't sink 'em, Taipan!")

            # Some enemies may flee after a volley
            # C: if (rand()%s0 > (num_ships * 0.6 / id)) && (num_ships > 2)
            if s0 > 0 and num_ships > 2:
                if random.randint(0, s0 - 1) > (num_ships * 0.6 / id):
                    divisor = int(num_ships / 3 / id)
                    if divisor == 0:
                        divisor = 1
                    ran = random.randint(0, divisor - 1) if divisor > 1 else 0
                    if ran == 0:
                        ran = 1
                    num_ships -= ran
                    if num_ships < 0:
                        num_ships = 0
                    fight_stats(g, num_ships, orders)
                    print(f"{ran} ran away, Taipan!")

            if num_ships > 0:
                pause()

        elif orders == 1 and g.guns == 0:
            print("We have no guns, Taipan!!")
            orders = 0

        # ── THROW CARGO ──
        elif orders == 3:
            print("You have the following on board, Taipan:")
            print(f"  Opium: {g.hold_[0]}    Silk: {g.hold_[1]}")
            print(f"  Arms:  {g.hold_[2]}    General: {g.hold_[3]}")
            print("What shall I throw overboard, Taipan?")
            print("  (O)pium, (S)ilk, (A)rms, (G)eneral, or (*) everything?")

            while True:
                ch = get_one("? ").upper()
                if ch in ("O", "S", "A", "G", "*"):
                    break

            cargo_map = {"O": 0, "S": 1, "A": 2, "G": 3}
            if ch == "*":
                total = sum(g.hold_)
                if total > 0:
                    print("Let's hope we lose 'em, Taipan!")
                    for idx in range(4):
                        g.hold_[idx] = 0
                    g.hold += total
                    ok += total // 10
            elif ch in cargo_map:
                ci = cargo_map[ch]
                if g.hold_[ci] > 0:
                    print(f"How much {ITEMS[ci]} shall I throw, Taipan?")
                    print(f"  (You have {g.hold_[ci]}, 'A' for all)")
                    amount = get_num(9)
                    if amount == -1 or amount > g.hold_[ci]:
                        amount = g.hold_[ci]
                    if amount > 0:
                        print("Let's hope we lose 'em, Taipan!")
                        g.hold_[ci] -= amount
                        g.hold += amount
                        ok += amount // 10

            # Fall through to run/escape check (orders == 2 || orders == 3)
            # ── RUN / ESCAPE CHECK (orders == 2 or 3) ──
            ok += ik
            ik += 1
            if ok > 0 and random.randint(0, ok - 1) > random.randint(0, num_ships - 1 if num_ships > 0 else 0):
                print("We got away from 'em, Taipan!")
                num_ships = 0
            else:
                print("Couldn't lose 'em.")
                # Some may give up: 1-in-5 if num_ships > 2
                if num_ships > 2 and random.randint(0, 4) == 0:
                    lost = (random.randint(0, num_ships - 1) // 2) + 1
                    num_ships -= lost
                    if num_ships < 0:
                        num_ships = 0
                    fight_stats(g, num_ships, orders)
                    print(f"But we escaped from {lost} of 'em!")
            pause()
            orders = 0

        # ── RUN ──
        elif orders == 2:
            print("Aye, we'll run, Taipan.")
            ok += ik
            ik += 1
            if ok > 0 and random.randint(0, ok - 1) > random.randint(0, num_ships - 1 if num_ships > 0 else 0):
                print("We got away from 'em, Taipan!")
                num_ships = 0
            else:
                print("Couldn't lose 'em.")
                if num_ships > 2 and random.randint(0, 4) == 0:
                    lost = (random.randint(0, num_ships - 1) // 2) + 1
                    num_ships -= lost
                    if num_ships < 0:
                        num_ships = 0
                    fight_stats(g, num_ships, orders)
                    print(f"But we escaped from {lost} of 'em!")
            pause()
            orders = 0

        # ── ENEMY VOLLEY (if ships remain) ──
        if num_ships > 0:
            print("They're firing on us, Taipan!")
            pause()
            print("We've been hit, Taipan!!")

            i = min(num_ships, 15)

            # Gun loss check: if guns > 0 and (rand%100 < damage/cap*100 OR damage/cap*100 > 80)
            if g.guns > 0:
                dmg_pct = (float(g.damage) / g.capacity) * 100
                if random.randint(0, 99) < dmg_pct or dmg_pct > 80:
                    i = 1
                    g.guns -= 1
                    g.hold += 10
                    fight_stats(g, num_ships, orders)
                    print("The buggers hit a gun, Taipan!!")
                    pause()

            # damage += (ed * i * id) * rand + i/2
            g.damage += int((g.ed * i * id) * random.random()) + (i // 2)

            # Li Yuen interrupts (generic only, 1-in-20)
            if id == GENERIC and random.randint(0, 19) == 0:
                return BATTLE_INTERRUPTED

            pause()

    # ── BATTLE END ──
    if orders == 1:
        fight_stats(g, num_ships, orders)
        print("We got 'em all, Taipan!")
        pause()
        return BATTLE_WON
    else:
        return BATTLE_FLED


def quit_trading(g):
    """Quit trading → choose destination → voyage."""
    print()
    print("Comprador's Report")
    print()
    print("Taipan, do you wish me to go to:")
    print("1) Hong Kong, 2) Shanghai, 3) Nagasaki,")
    print("4) Saigon, 5) Manila, 6) Singapore, or")
    print("7) Batavia ?")

    while True:
        choice = get_num(1)
        if choice == g.port:
            print("You're already here, Taipan.")
            continue
        if 1 <= choice <= 7:
            g.port = choice
            break

    print()
    print("  At sea...")
    print()
    print("  Captain's Report")
    print()

    result = BATTLE_NOT_FINISHED

    # Pirate encounter: rand()%bp == 0
    if g.bp > 0 and random.randint(0, g.bp - 1) == 0:
        num_ships = random.randint(0, (g.capacity // 10) + g.guns - 1) + 1
        if num_ships > 9999:
            num_ships = 9999
        print(f"{num_ships} hostile ships approaching, Taipan!")
        pause()
        result = sea_battle(g, GENERIC, num_ships)

    # If interrupted, Li Yuen's fleet drove them off
    if result == BATTLE_INTERRUPTED:
        port_stats(g)
        print()
        print("  At sea...")
        print()
        print("  Captain's Report")
        print()
        print("Li Yuen's fleet drove them off!")
        pause()

    # Li Yuen ambush: (not_finished and rand%(4+8*li)==0) OR interrupted
    if ((result == BATTLE_NOT_FINISHED and random.randint(0, 3 + 8 * g.li) == 0) or
            result == BATTLE_INTERRUPTED):
        print()
        print("Li Yuen's pirates, Taipan!!")
        pause()

        if g.li > 0:
            # Friendly — they let you go
            print("Good joss!! They let us be!!")
            pause()
            # Arrive without further combat
            _arrive(g)
            return
        else:
            num_ships = random.randint(0, (g.capacity // 5) + g.guns - 1) + 5
            print(f"{num_ships} ships of Li Yuen's pirate")
            print("fleet, Taipan!!")
            pause()
            result = sea_battle(g, LI_YUEN, num_ships)

    # Battle results
    if result > BATTLE_NOT_FINISHED:
        port_stats(g)
        print()
        print("  At sea...")
        print()
        print("  Captain's Report")
        print()

        if result == BATTLE_WON:
            print(f"We captured some booty.")
            print(f"It's worth {fancy_numbers(g.booty)}!")
            g.cash += g.booty
            pause()
        elif result == BATTLE_FLED:
            print("We made it!")
            pause()
        elif result == BATTLE_LOST:
            print("The buggers got us, Taipan!!!")
            print("It's all over, now!!!")
            pause()
            final_stats(g)
            return

    # Storm: 1-in-10
    if random.randint(0, 9) == 0:
        print()
        print("Storm, Taipan!!")
        pause()

        # 1-in-30 chance of potential sinking
        if random.randint(0, 29) == 0:
            print("   I think we're going down!!")
            pause()

            # Sinking check: (damage/capacity * 3) * rand >= 1
            if ((float(g.damage) / g.capacity * 3) * random.random()) >= 1:
                print("We're going down, Taipan!!")
                pause()
                final_stats(g)
                return

        print("    We made it!!")
        pause()

        # 1-in-3 blown off course
        if random.randint(0, 2) == 0:
            orig = g.port
            while g.port == orig:
                g.port = random.randint(0, 6) + 1
            print(f"We've been blown off course to {LOCATIONS[g.port]}")
            pause()

    _arrive(g)


def _arrive(g):
    """Arrival at destination — month/year/interest/price reset."""
    g.month += 1
    if g.month == 13:
        g.month = 1
        g.year += 1
        g.ec += 10
        g.ed += 0.5

    # Wu interest: 10%/month on debt
    g.debt = int(g.debt + (g.debt * 0.1))
    # Bank interest: 0.5%/month
    g.bank = int(g.bank + (g.bank * 0.005))

    set_prices(g)

    print()
    print(f"Arriving at {LOCATIONS[g.port]}...")
    pause()


def retire(g):
    """Retire as a millionaire (HK only, cash+bank >= 1M)."""
    print()
    print("Comprador's Report")
    print()
    print("                         ")
    print(" Y o u ' r e    a        ")
    print("                         ")
    print(" M I L L I O N A I R E ! ")
    print("                         ")
    pause()
    final_stats(g)


def final_stats(g):
    """Game over screen with rating and play-again option."""
    years = g.year - 1860
    net_cash = g.cash + g.bank - g.debt

    print()
    print("Your final status:")
    print()
    print(f"Net cash:  {fancy_numbers(net_cash)}")
    print()
    print(f"Ship size: {g.capacity} units with {g.guns} guns")
    print()

    if years == 1:
        year_word = "year"
    else:
        year_word = "years"
    month_word = "month" if g.month == 1 else "months"

    print(f"You traded for {years} {year_word} and {g.month} {month_word}")
    print()
    print(f"Your score is {int(g.cash)}.")
    print()

    if g.cash < 500:
        print("Have you considered a land based job?")
        print()
        print("The crew has requested that you stay on")
        print("shore for their safety!!")
    print()

    # Rating table
    print("Your Rating:")
    print(" _______________________________")

    def rating_row(label, lo, hi, current):
        # Highlight current rating with [brackets]
        marker = " <==" if lo <= current <= hi else ""
        print(f"| {label:<20s} {lo:>7,} to {hi:>6,}|{marker}")

    # Ma Tsu: 50,000+
    print(f"| {'Ma Tsu':<20s}     50,000 and over |{' <==' if g.cash >= 50000 else ''}")
    print(f"| {'Master Taipan':<20s}   8,000 to 49,999|{' <==' if 8000 <= g.cash < 50000 else ''}")
    print(f"| {'Taipan':<20s}   1,000 to  7,999|{' <==' if 1000 <= g.cash < 8000 else ''}")
    print(f"| {'Compradore':<20s}     500 to    999|{' <==' if 500 <= g.cash < 1000 else ''}")
    print(f"| {'Galley Hand':<20s}    less than 500|{' <==' if g.cash < 500 else ''}")
    print("|_______________________________|")
    print()

    while True:
        print("Play again?")
        choice = get_one("(Y/N)? ").upper()
        if choice in ("Y", "N"):
            break

    if choice == "Y":
        _new_game()
    else:
        print()
        sys.exit(0)


def splash_intro():
    """Opening splash screen."""
    print()
    print("         _____  _    ___ ____   _    _   _               ===============")
    print("        |_   _|/ \\  |_ _|  _ \\ / \\  | \\ | |              Created by:")
    print("          | | / _ \\  | || |_) / _ \\ |  \\| |                 Art Canfil")
    print("          | |/ ___ \\ | ||  __/ ___ \\| |\\  |")
    print("          |_/_/   \\_\\___|_| /_/   \\_\\_| \\_|              ===============")
    print("                                                         Programmed by:")
    print("   A game based on the China trade of the 1800's            Jay Link")
    print()
    print("                      ~~|     ,                          jlink@ilbbs.com")
    print("                       ,|`-._/|\\")
    print("                     .' |   /||\\                         ===============")
    print("                   .'   | ./ ||`\\                         Copyright (c)")
    print("                  / `-. |/._ ||  \\                         1978 - 2002")
    print("                 /     `||  `|;-._\\                         Art Canfil")
    print("                 |      ||   ||   \\")
    print("~^~_-~^~=~^~~^= /       ||   ||__  \\~^=~^~-~^~_~^~=      ===============")
    print(" ~=~^~ _~^~ =~ `--------|`---||  `\"-`___~~^~ =_~^=        Press ANY key")
    print("~ ~^~=~^_~^~ =~ \\~~~~~~~'~~~~'~~~~/~~`` ~=~^~ ~^=           to start.")
    print(" ~^=~^~_~-=~^~ ^ `--------------'~^~=~^~_~^=~^~=~")
    print()
    # Web terminal shows no inline prompt box; wait for one focused keystroke.
    # Deterministic: no inference calls, no network, pure Python engine.
    try:
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
    print()


def name_firm(g):
    """Name your trading firm."""
    print(" _______________________________________")
    print("|     Taipan,                           |")
    print("|                                       |")
    print("| What will you name your               |")
    print("|                                       |")
    print("|     Firm:                             |")
    print("|           ----------------------      |")
    print("|_______________________________________|")
    print()

    while True:
        try:
            name = input("Firm name: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if name:
            g.firm = name[:22]
            break
        print("Please enter a name, Taipan.")


def cash_or_guns(g):
    """Starting choice: cash+debt vs guns+no cash."""
    print()
    print("Do you want to start . . .")
    print()
    print("  1) With cash (and a debt)")
    print()
    print("                >> or <<")
    print()
    print("  2) With five guns and no cash")
    print("                (But no debt!)")
    print()

    while True:
        choice = get_one("? ")
        if choice in ("1", "2"):
            break

    if choice == "1":
        g.cash = 400
        g.debt = 5000
        g.hold = 60
        g.guns = 0
        g.li = 0
        g.bp = 10
    else:
        g.cash = 0
        g.debt = 0
        g.hold = 10
        g.guns = 5
        g.li = 1
        g.bp = 7


# ── Main Loop ──────────────────────────────────────────────────────

g = None  # global game state


def _new_game():
    """Start a new game from scratch."""
    global g
    g = Game()
    random.seed(os.getpid())
    splash_intro()
    name_firm(g)
    cash_or_guns(g)
    set_prices(g)
    _main_loop()


def _main_loop():
    global g
    for _ in range(10000):  # safety limit
        choice = 0

        port_stats(g)

        # Li Yuen extortion (HK, li==0, cash>0)
        if g.port == 1 and g.li == 0 and g.cash > 0:
            li_yuen_extortion(g)

        # McHenry repairs (HK, damage>0)
        if g.port == 1 and g.damage > 0:
            mchenry(g)

        # Wu debt warning (HK, debt>=10000, first time)
        if g.port == 1 and g.debt >= 10000 and g.wu_warn == 0:
            braves = random.randint(0, 99) + 50
            print()
            print("Comprador's Report")
            print()
            print(f"Elder Brother Wu has sent {braves} braves")
            print("to escort you to the Wu mansion, Taipan.")
            pause()
            print()
            print("Elder Brother Wu reminds you of the")
            print("Confucian ideal of personal worthiness,")
            print("and how this applies to paying one's")
            print("debts.")
            pause()
            print()
            print("He is reminded of a fabled barbarian")
            print("who came to a bad end, after not caring")
            print("for his obligations.")
            print()
            print("He hopes no such fate awaits you, his")
            print("friend, Taipan.")
            pause()
            g.wu_warn = 1

        # Elder Brother Wu (HK only)
        if g.port == 1:
            elder_brother_wu(g)

        # Shipyard: 1-in-4 arrivals
        if random.randint(0, 3) == 0:
            if random.randint(0, 1) == 0:
                new_ship(g)
            elif g.guns < 1000:
                new_gun(g)

        # Opium seizure (foreign ports, 1-in-18, hold opium>0)
        if g.port != 1 and random.randint(0, 17) == 0 and g.hold_[0] > 0:
            fine = int((g.cash / 1.8) * random.random()) + 1
            if g.cash == 0:
                fine = 0
            g.hold += g.hold_[0]
            g.hold_[0] = 0
            g.cash -= fine

            port_stats(g)
            print()
            print("Comprador's Report")
            print()
            print("Bad Joss!!")
            print("The local authorities have seized your")
            if fine <= 0:
                print("Opium cargo, Taipan!")
            else:
                print(f"Opium cargo and have also fined you")
                print(f"{fancy_numbers(fine)}, Taipan!")
            pause()

        # Warehouse theft (1-in-50, warehouse has goods)
        if random.randint(0, 49) == 0 and sum(g.hkw) > 0:
            for i in range(4):
                g.hkw[i] = int((g.hkw[i] / 1.8) * random.random())

            port_stats(g)
            print()
            print("Comprador's Report")
            print()
            print("Messenger reports large theft")
            print("from warehouse, Taipan.")
            pause()

        # Li cooling tick (1-in-20)
        if random.randint(0, 19) == 0:
            if g.li > 0:
                g.li += 1
            if g.li == 4:
                g.li = 0

        # Li lieutenant (foreign, li==0, 3-in-4)
        if g.port != 1 and g.li == 0 and random.randint(0, 3) != 0:
            print()
            print("Comprador's Report")
            print()
            print("Li Yuen has sent a Lieutenant,")
            print("Taipan.  He says his admiral wishes")
            print("to see you in Hong Kong, posthaste!")
            pause()

        # Good prices event (1-in-9)
        if random.randint(0, 8) == 0:
            good_prices(g)

        # Street robbery (cash>25000, 1-in-20)
        if g.cash > 25000 and random.randint(0, 19) == 0:
            robbed = int((g.cash / 1.4) * random.random())
            g.cash -= robbed
            port_stats(g)
            print()
            print("Comprador's Report")
            print()
            print("Bad Joss!!")
            print("You've been beaten up and")
            print(f"robbed of {fancy_numbers(robbed)} in cash, Taipan!!")
            pause()

        # Trading menu loop
        while True:
            choice = port_choices(g)

            if choice == "B":
                buy(g)
            elif choice == "S":
                sell(g)
            elif choice == "V":
                visit_bank(g)
            elif choice == "T":
                transfer(g)
            elif choice == "W":
                elder_brother_wu(g)
            elif choice == "R":
                retire(g)
            elif choice == "Q":
                break

            port_stats(g)

        # After Q: if not overloaded, travel; else overload warning
        if g.hold >= 0:
            quit_trading(g)
        else:
            overload(g)


if __name__ == "__main__":
    _new_game()
