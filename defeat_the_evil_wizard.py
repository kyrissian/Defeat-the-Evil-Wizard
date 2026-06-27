"""
wizard_battle.py
================
A turn-based RPG where a hero battles the Evil Wizard.

Design notes
------------
- All shared behavior (heal, random attack, ability dispatch) lives in the
  base Character class so subclasses stay DRY.
- Each subclass declares `self.abilities` — a list of dicts — and
  `self.status_effects` for passive flags (shield, evade, etc.).
- The battle loop is class-agnostic: it reads those lists at runtime, so
  adding a new class never requires touching battle().
"""
# pylint: disable=too-many-lines

import os
import random
import sys
import time

# Force UTF-8 on Windows before any output is attempted.
# If PYTHONUTF8 is not already set, re-launch this script with it enabled
# so the entire process starts in UTF-8 mode from the very beginning.
if os.name == "nt" and os.environ.get("PYTHONUTF8") != "1":
    os.environ["PYTHONUTF8"] = "1"
    SCRIPT_PATH = f'"{sys.argv[0]}"'
    sys.exit(os.spawnv(os.P_WAIT, sys.executable, [sys.executable, SCRIPT_PATH]))


# ─────────────────────────────────────────────
#  PRESENTATION HELPERS
# ─────────────────────────────────────────────

# Emoji icons used throughout the UI
CLASS_EMOJI = {
    "Warrior":     "⚔️",
    "Mage":        "🔮",
    "Archer":      "🏹",
    "Paladin":     "🛡️",
    "DeathKnight": "💀",
    "HolyPriest":  "✨",
    "Rogue":       "🗡️",
    "Druid":       "🌿",
    "EvilWizard":  "🧙",
}

WIZARD_TAUNTS = [
    "You dare challenge ME?! 😈",
    "Your suffering amuses me... 🌑",
    "Is that all you have?! 💀",
    "I've crushed stronger heroes than you! 😤",
    "Your end is near, fool! ⚡",
    "The darkness will consume you! 🌑",
    "Ha! You fight like a peasant! 😂",
    "Tremble before my power! 💜",
    "You cannot win... give up now! 😈",
    "My magic grows stronger with every passing moment! ✨",
]

# Intro lines spoken when each class enters battle
CLASS_INTROS = {
    "Warrior":     "🗡️  \"{name}\" cracks their knuckles. \"Let's make this quick.\"",
    "Mage":        "🔮  \"{name}\" crackles with arcane energy. "
                  "\"You are merely a footnote in my research.\"",
    "Archer":      "🏹  \"{name}\" notches an arrow. \"I never miss.\"",
    "Paladin":     "🛡️  \"{name}\" raises their shield. \"By the Light, you shall fall.\"",
    "DeathKnight": "💀  \"{name}\" rises from shadow. "
                  "\"Death comes for us all... yours comes first.\"",
    "HolyPriest":  "✨  \"{name}\" glows with divine radiance. \"The Light will prevail.\"",
    "Rogue":       "🗡️  \"{name}\" melts from the shadows. \"You won't see me coming.\"",
    "Druid":       "🌿  \"{name}\" communes with nature. \"The wilds fight with me today.\"",
}


def slow_print(text, delay=0.03):
    """
    Print text one character at a time for a typewriter effect.

    Parameters
    ----------
    text  : str   -- the string to print
    delay : float -- seconds between each character (default 0.03)
    """
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def pause(seconds=0.6):
    """Short pause to let dramatic moments breathe."""
    time.sleep(seconds)


def print_hp_bars(player, wizard):
    """
    Print HP bars scaled to actual HP values, not percentage.

    The bar widths are proportional to each character's max_health relative
    to the highest max_health in the fight — so a 200 HP character gets a
    visually longer bar than a 150 HP one, which is more intuitive than
    both showing full bars at the start.

    Parameters
    ----------
    player : Character subclass instance
    wizard : EvilWizard instance
    """
    max_bar   = 24   # bar width for the highest-HP combatant
    name_col  = 16
    highest   = max(player.max_health, wizard.max_health)

    def make_bar(label, character):
        # Scale bar width proportionally to this character's max HP
        bar_width = max(1, int(max_bar * character.max_health / highest))
        filled    = int(bar_width * max(character.health, 0) / character.max_health)
        hp_bar    = "█" * filled + "░" * (bar_width - filled)
        name      = character.name[:name_col].ljust(name_col)
        return f"{label} {name} [{hp_bar}] {character.health}/{character.max_health}"

    print(f"\n  {make_bar('YOU', player)}")
    print(f"  {make_bar('FOE', wizard)}\n")


def print_title():
    """Print the ASCII art title screen with a dramatic typewriter entrance."""
    title = r"""
  ██╗    ██╗██╗███████╗ █████╗ ██████╗ ██████╗
  ██║    ██║██║╚══███╔╝██╔══██╗██╔══██╗██╔══██╗
  ██║ █╗ ██║██║  ███╔╝ ███████║██████╔╝██║  ██║
  ██║███╗██║██║ ███╔╝  ██╔══██║██╔══██╗██║  ██║
  ╚███╔███╔╝██║███████╗██║  ██║██║  ██║██████╔╝
   ╚══╝╚══╝ ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
  ██████╗  █████╗ ████████╗████████╗██╗     ███████╗
  ██╔══██╗██╔══██╗╚══██╔══╝╚══██╔══╝██║     ██╔════╝
  ██████╔╝███████║   ██║      ██║   ██║     █████╗
  ██╔══██╗██╔══██║   ██║      ██║   ██║     ██╔══╝
  ██████╔╝██║  ██║   ██║      ██║   ███████╗███████╗
  ╚═════╝ ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚══════╝
    """
    print(title)
    slow_print("  ⚔️   Defeat the Evil Wizard before he destroys the realm...  ⚔️", delay=0.04)  # noqa: E501
    pause(0.8)


def print_victory(player, wizard):
    """Print the ASCII art victory screen."""
    art = r"""
    *      *   *    *      *    *    *      *
  *    *      *   *    *      *    *      *
        *   *        *    *       *    *
  .-=========================================-.
  |  \o/  THE REALM IS SAVED  \o/            |
  |   |        HERO VICTORIOUS               |
  |  / \                                     |
  `-==========================================-'
        *   *        *    *       *    *
  *    *      *   *    *      *    *      *
    *      *   *    *      *    *    *      *
    """
    print(art)
    slow_print(f"  🏆  {player.name} has defeated {wizard.name}!", delay=0.05)
    pause(0.4)
    slow_print("  The darkness recedes. Light returns to the realm. ✨", delay=0.04)


def print_defeat(player, wizard):
    """Print the ASCII art defeat screen."""
    art = r"""
  .  .  .  .  .  .  .  .  .  .  .  .  .  .
    .   the darkness wins   .   game over   .
  .  .  .  .  .  .  .  .  .  .  .  .  .  .

         _/|          |\
        / /           | \
       / / ___    ___ | |
       | |/   \  /   \| |
       | |  x  ||  x  | |    ...you have
       | |  __  ||  __  | |       fallen.
       | | /  \ || /  \ | |
        \_\____/  \____/_/

  .  .  .  .  .  .  .  .  .  .  .  .  .  .
    """
    print(art)
    slow_print(f"  💀  {player.name} has fallen...", delay=0.05)
    pause(0.4)
    slow_print(
        f"  {wizard.name} cackles in triumph... the realm is lost. 🌑",
        delay=0.04
    )


# ─────────────────────────────────────────────
#  BASE CLASS
# ─────────────────────────────────────────────

class Character:
    """
    Base class for every character in the game.

    Attributes
    ----------
    name : str
    health : int
    attack_power : int
    max_health : int
    heal_power : int   -- how much health a basic heal restores
    abilities : list   -- list of {'name': str, 'desc': str, 'method': callable}
    status_effects : dict -- passive flags set by abilities (e.g. 'shield', 'evade')
    """

    def __init__(self, name, health, attack_power, heal_power=20):
        self.name         = name
        self.health       = health
        self.attack_power = attack_power
        self.max_health   = health
        self.heal_power   = heal_power
        self.abilities: list    = []   # filled by each subclass
        self.status_effects: dict = {} # e.g. {'shield': True}

    # ── Core actions ────────────────────────────────────────────────────

    def attack(self, opponent):
        """
        Deal randomized damage (±20 % of attack_power) to opponent.
        If opponent has a shield or evade status, the hit is blocked/missed.
        """
        # Check opponent's passive defenses first
        if opponent.status_effects.get("evade"):
            slow_print(f"  💨 {opponent.name} evades {self.name}'s attack!")
            opponent.status_effects["evade"] = False
            return
        if opponent.status_effects.get("shield"):
            slow_print(f"  🛡️  {opponent.name}'s shield absorbs the attack!")
            opponent.status_effects["shield"] = False
            return

        # Random damage ±20 %
        low    = int(self.attack_power * 0.8)
        high   = int(self.attack_power * 1.2)
        damage = random.randint(low, high)

        opponent.health -= damage
        slow_print(f"  ⚔️  {self.name} attacks {opponent.name} for {damage} damage!")
        if opponent.health <= 0:
            slow_print(f"  💥 {opponent.name} has been defeated!")

    def heal(self):
        """Restore heal_power HP without exceeding max_health."""
        before  = self.health
        self.health = min(self.health + self.heal_power, self.max_health)
        restored = self.health - before
        slow_print(f"  💚 {self.name} heals for {restored} HP! "
                   f"({self.health}/{self.max_health})")

    def use_ability(self, index, opponent):
        """
        Dispatch ability by index in self.abilities list.
        Abilities with cooldown > 0 cannot be used until the counter reaches 0.
        After a successful use, the cooldown is reset to its max value.

        Parameters
        ----------
        index    : int       -- 0-based index into self.abilities
        opponent : Character
        """
        if index < 0 or index >= len(self.abilities):
            print("  ❌ Invalid ability choice.")
            return
        ability = self.abilities[index]

        # Check cooldown
        remaining = ability.get("cooldown", 0)
        if remaining > 0:
            slow_print(
                f"  ⏳ {ability['name']} is on cooldown for "
                f"{remaining} more turn(s)!"
            )
            return

        slow_print(f"\n  ✨ {self.name} uses {ability['name']}!", delay=0.05)
        pause(0.3)
        ability["method"](opponent)

        # Reset cooldown after use
        if "max_cooldown" in ability:
            ability["cooldown"] = ability["max_cooldown"]

    def tick_cooldowns(self):
        """
        Decrement all ability cooldowns by 1 at the end of each turn.
        Called by the battle loop automatically.
        """
        for ability in self.abilities:
            if ability.get("cooldown", 0) > 0:
                ability["cooldown"] -= 1

    def display_stats(self):
        """Print current HP, max HP, and attack power."""
        bar_len = 20
        ratio   = max(self.health, 0) / self.max_health
        filled  = int(bar_len * ratio)
        hp_bar  = "█" * filled + "░" * (bar_len - filled)
        emoji   = CLASS_EMOJI.get(type(self).__name__, "❓")
        print(f"\n  {emoji} {self.name} | [{hp_bar}] {self.health}/{self.max_health} HP "
              f"| ⚔️  ATK {self.attack_power}")
        if self.status_effects:
            active = [k for k, v in self.status_effects.items() if v]
            if active:
                print(f"     🔮 Active effects: {', '.join(active)}")

    # ── Helper used by subclass abilities ───────────────────────────────

    def _deal_damage(self, opponent, damage):
        """Internal: deal exact damage (no random spread, bypasses effects)."""
        opponent.health -= damage
        slow_print(f"  💥 {opponent.name} takes {damage} damage! "
                   f"({opponent.health}/{opponent.max_health} HP remaining)")
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")


# ─────────────────────────────────────────────
#  PLAYER CLASSES
# ─────────────────────────────────────────────

class Warrior(Character):
    """
    Warrior — A heavily armored melee fighter.

    Stats   : High HP, moderate attack.
    Flavor  : Bread-and-butter tank. Hard to kill, reliably dangerous.

    Abilities
    ---------
    1. Shield Bash  — Stuns with 1.5× damage; blocks opponent's next hit.
    2. Whirlwind    — Strikes for 2× damage in a wide arc.
    3. Battle Cry   — Boosts own attack_power by 10 for the rest of the battle.
    4. Last Stand   — When below 30 % HP, heals 40 and attacks immediately.
    """

    def __init__(self, name):
        super().__init__(name, health=160, attack_power=28, heal_power=20)
        self.abilities = [
            {
                "name":         "⚔️  Shield Bash",
                "desc":         "Deal 1.5× damage and block the opponent's next attack.",
                "method":       self._shield_bash,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🌀 Whirlwind",
                "desc":         "Spin attack dealing 2× damage.",
                "method":       self._whirlwind,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "📣 Battle Cry",
                "desc":         "Raise your attack power by 10 permanently.",
                "method":       self._battle_cry,
                "max_cooldown": 3,
                "cooldown":     0,
            },
            {
                "name":         "🩸 Last Stand",
                "desc":         "Heal 40 HP and strike back (only when below 30 % HP).",
                "method":       self._last_stand,
                "max_cooldown": 2,
                "cooldown":     0,
            },
        ]

    def _shield_bash(self, opponent):
        damage = int(self.attack_power * 1.5)
        self._deal_damage(opponent, damage)
        self.status_effects["shield"] = True
        slow_print(f"  🛡️  {self.name} raises shield — next attack will be blocked!")

    def _whirlwind(self, opponent):
        damage = self.attack_power * 2
        self._deal_damage(opponent, damage)

    def _battle_cry(self, _opponent):
        self.attack_power += 10
        slow_print(f"  📣 {self.name} roars! Attack power raised to {self.attack_power}.")

    def _last_stand(self, opponent):
        threshold = int(self.max_health * 0.3)
        if self.health <= threshold:
            self.health = min(self.health + 40, self.max_health)
            slow_print(f"  🩸 {self.name} refuses to fall! Healed to {self.health} HP.")
            self._deal_damage(opponent, self.attack_power)
        else:
            slow_print(f"  ❌ Last Stand only triggers below 30 % HP "
                       f"({threshold} HP). Current HP: {self.health}.")


class Mage(Character):
    """
    Mage — Glass cannon spellcaster.

    Stats   : Low HP, highest base attack.
    Flavor  : Fragile but devastating; rewards aggressive play.

    Abilities
    ---------
    1. Fireball     — Deals 2× damage in a blazing explosion.
    2. Frost Nova   — Freezes opponent; they skip their next attack.
    3. Arcane Surge — Temporarily boost attack_power by 15 for 1 turn.
    4. Blink        — Teleport to safety; evade next attack.
    """

    def __init__(self, name):
        super().__init__(name, health=100, attack_power=40, heal_power=15)
        self._surge_active = False
        self._surge_bonus  = 15
        self.abilities = [
            {
                "name":         "🔥 Fireball",
                "desc":         "Hurl a fireball for 2× damage.",
                "method":       self._fireball,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "❄️  Frost Nova",
                "desc":         "Freeze the opponent; they lose their next attack.",
                "method":       self._frost_nova,
                "max_cooldown": 3,
                "cooldown":     0,
            },
            {
                "name":         "⚡ Arcane Surge",
                "desc":         "Boost attack power by 15 — then pick a follow-up action.",
                "method":       self._arcane_surge,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "💨 Blink",
                "desc":         "Teleport — your next incoming attack misses.",
                "method":       self._blink,
                "max_cooldown": 2,
                "cooldown":     0,
            },
        ]

    def _fireball(self, opponent):
        damage = self.attack_power * 2
        self._deal_damage(opponent, damage)

    def _frost_nova(self, opponent):
        opponent.status_effects["frozen"] = True
        slow_print(f"  ❄️  {opponent.name} is frozen and will skip their next turn!")

    def _arcane_surge(self, _opponent):
        self.attack_power += self._surge_bonus
        self._surge_active = True
        slow_print(
            f"  ⚡ Arcane Surge active! Your attack power is now {self.attack_power}.\n"
            f"  💡 Your NEXT attack or ability this turn hits at full surge power.\n"
            f"  ⚠️  The bonus expires automatically after the wizard's turn."
        )

    def _blink(self, _opponent):
        self.status_effects["evade"] = True
        slow_print(f"  💨 {self.name} blinks away — next attack will miss!")

    def end_of_turn(self):
        """Called by battle loop to expire surge."""
        if self._surge_active:
            self.attack_power -= self._surge_bonus
            self._surge_active = False


class Archer(Character):
    """
    Archer — Swift ranged attacker.

    Stats   : Balanced HP and attack; fastest character.
    Flavor  : Excels at consistent damage and avoiding hits.

    Abilities
    ---------
    1. Quick Shot     — Fire two arrows for 0.75× damage each (1.5× total).
    2. Sniper Shot    — Charged shot ignores shield/evade; deals 1.8× damage.
    3. Evade          — Dodge the next incoming attack.
    4. Rain of Arrows — Volley dealing 2.5× damage (one use).
    """

    def __init__(self, name):
        super().__init__(name, health=120, attack_power=32, heal_power=18)
        self._rain_used = False
        self.abilities = [
            {
                "name":         "🏹 Quick Shot",
                "desc":         "Two fast arrows — each deals 0.75× damage.",
                "method":       self._quick_shot,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🎯 Sniper Shot",
                "desc":         "Bypasses all defenses for 1.8× damage.",
                "method":       self._sniper_shot,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "💨 Evade",
                "desc":         "Guarantee a dodge on the next attack aimed at you.",
                "method":       self._evade,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🌧️  Rain of Arrows",
                "desc":         "Devastating volley (2.5×). One-time use.",
                "method":       self._rain_of_arrows,
                "max_cooldown": 0,
                "cooldown":     0,
            },
        ]

    def _quick_shot(self, opponent):
        for i in range(1, 3):
            dmg = int(self.attack_power * 0.75)
            slow_print(f"  🏹 Arrow {i}:", delay=0.02)
            self._deal_damage(opponent, dmg)

    def _sniper_shot(self, opponent):
        damage = int(self.attack_power * 1.8)
        opponent.health -= damage
        slow_print(f"  🎯 Sniper Shot pierces defenses! {opponent.name} takes {damage} damage. "
                   f"({opponent.health}/{opponent.max_health} HP)")
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _evade(self, _opponent):
        self.status_effects["evade"] = True
        slow_print(f"  💨 {self.name} readies a dodge — next attack will miss!")

    def _rain_of_arrows(self, opponent):
        if self._rain_used:
            slow_print("  ❌ Rain of Arrows has already been used!")
            return
        damage = int(self.attack_power * 2.5)
        self._deal_damage(opponent, damage)
        self._rain_used = True


class Paladin(Character):
    """
    Paladin — Defensive holy warrior.

    Stats   : High HP, moderate attack, strong heals.
    Flavor  : Hard to kill. Balances offense with protection.

    Abilities
    ---------
    1. Holy Strike    — Bonus holy damage (1.6×).
    2. Divine Shield  — Block the next incoming attack entirely.
    3. Consecration   — AoE holy ground; deals moderate damage + heals self 15.
    4. Aura of Valor  — Permanently increase max_health by 30 and heal that amount.
    """

    def __init__(self, name):
        super().__init__(name, health=150, attack_power=26, heal_power=28)
        self.abilities = [
            {
                "name":         "✝️  Holy Strike",
                "desc":         "A blessed strike for 1.6× damage.",
                "method":       self._holy_strike,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🛡️  Divine Shield",
                "desc":         "Block the next attack aimed at you.",
                "method":       self._divine_shield,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🔥 Consecration",
                "desc":         "Deal moderate damage and heal yourself 15 HP.",
                "method":       self._consecration,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "✨ Aura of Valor",
                "desc":         "Permanently raise max HP by 30 and restore that HP.",
                "method":       self._aura_of_valor,
                "max_cooldown": 0,
                "cooldown":     0,
            },
        ]

    def _holy_strike(self, opponent):
        damage = int(self.attack_power * 1.6)
        self._deal_damage(opponent, damage)

    def _divine_shield(self, _opponent):
        self.status_effects["shield"] = True
        slow_print(f"  🛡️  {self.name} is shielded — the next attack will be absorbed!")

    def _consecration(self, opponent):
        damage = int(self.attack_power * 0.9)
        self._deal_damage(opponent, damage)
        self.health = min(self.health + 15, self.max_health)
        slow_print(f"  🔥 Holy ground heals {self.name} for 15. "
                   f"HP: {self.health}/{self.max_health}")

    def _aura_of_valor(self, _opponent):
        self.max_health += 30
        self.health = min(self.health + 30, self.max_health)
        slow_print(f"  ✨ {self.name}'s Aura of Valor shines! Max HP → {self.max_health}. "
                   f"HP: {self.health}/{self.max_health}")


class DeathKnight(Character):
    """
    Death Knight — Dark plate warrior who weaponizes their own life force.

    Stats   : Very high HP, high attack.
    Flavor  : WoW-faithful DK: bleeds opponents, sacrifices own HP for power,
              and raises fallen power from the dead.

    Abilities
    ---------
    1. Death Coil      — Dark projectile that steals 20 HP from opponent.
    2. Blood Boil      — Sacrifice 15 own HP to deal 2.5× damage (net gain if it lands).
    3. Dark Pact       — Drain 25 HP from opponent directly into self.
    4. Army of the Dead — One-time ability: summon a spectral strike for massive damage.
    """

    def __init__(self, name):
        super().__init__(name, health=170, attack_power=34, heal_power=16)
        self._army_used = False
        self.abilities = [
            {
                "name":         "💀 Death Coil",
                "desc":         "Dark bolt that steals 20 HP from the opponent.",
                "method":       self._death_coil,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🩸 Blood Boil",
                "desc":         "Sacrifice 15 HP to unleash 2.5× damage.",
                "method":       self._blood_boil,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🌑 Dark Pact",
                "desc":         "Drain 25 HP from opponent directly into your own pool.",
                "method":       self._dark_pact,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "👻 Army of the Dead",
                "desc":         "Unleash spectral warriors for massive damage (one-time).",
                "method":       self._army_of_the_dead,
                "max_cooldown": 0,
                "cooldown":     0,
            },
        ]

    def _death_coil(self, opponent):
        steal = 20
        opponent.health -= steal
        self.health = min(self.health + steal, self.max_health)
        slow_print(f"  💀 Death Coil drains {steal} HP from {opponent.name}! "
                   f"{self.name} absorbs the life. HP: {self.health}/{self.max_health}")
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _blood_boil(self, opponent):
        cost = 15
        if self.health <= cost:
            slow_print("  ❌ Not enough HP to sacrifice for Blood Boil!")
            return
        self.health -= cost
        slow_print(f"  🩸 {self.name} sacrifices {cost} HP... "
                   f"HP: {self.health}/{self.max_health}")
        damage = int(self.attack_power * 2.5)
        self._deal_damage(opponent, damage)

    def _dark_pact(self, opponent):
        drain = 25
        opponent.health -= drain
        self.health = min(self.health + drain, self.max_health)
        slow_print(f"  🌑 Dark Pact! Drained {drain} HP from {opponent.name}. "
                   f"{self.name} HP: {self.health}/{self.max_health}")
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _army_of_the_dead(self, opponent):
        if self._army_used:
            slow_print("  ❌ The dead have already answered the call.")
            return
        damage = self.attack_power * 3
        slow_print("  👻 Spectral warriors rise from the grave!", delay=0.05)
        pause(0.5)
        self._deal_damage(opponent, damage)
        self._army_used = True


class HolyPriest(Character):
    """
    Holy Priest — Servant of the Light; the most resilient class in the game.

    Lore    : Inspired by WoW's Holy Priest spec and themes of divine grace,
              sacrifice, and restoration. Embodies God/Jesus/Light — heals
              abundantly, protects with miracles, and smites evil with holy fire.

    Stats   : Highest max HP, strong attack, massive healing.
    Flavor  : Almost impossible to kill through sheer sustain. Wins long fights.

    Abilities
    ---------
    1. Smite             — Holy bolt for 1.4× damage with bonus light damage.
    2. Prayer of Healing — Restore 50 HP immediately.
    3. Divine Hymn       — Powerful chant: heal 35 HP and reduce opponent ATK by 5.
    4. Holy Nova         — Flash of holy light: deal 1.2× damage and heal self 20.
    """

    def __init__(self, name):
        super().__init__(name, health=200, attack_power=32, heal_power=35)
        self.abilities = [
            {
                "name":         "✨ Smite",
                "desc":         "Channel the Light for 1.4× holy damage.",
                "method":       self._smite,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🙏 Prayer of Healing",
                "desc":         "Restore 50 HP through divine grace.",
                "method":       self._prayer_of_healing,
                "max_cooldown": 3,
                "cooldown":     0,
            },
            {
                "name":         "🎵 Divine Hymn",
                "desc":         "Holy chant: heal 35 HP and weaken opponent's attack by 5.",
                "method":       self._divine_hymn,
                "max_cooldown": 3,
                "cooldown":     0,
            },
            {
                "name":         "💫 Holy Nova",
                "desc":         "Burst of light: deal 1.2× damage and heal yourself 20 HP.",
                "method":       self._holy_nova,
                "max_cooldown": 2,
                "cooldown":     0,
            },
        ]

    def _smite(self, opponent):
        damage = int(self.attack_power * 1.4) + 10
        self._deal_damage(opponent, damage)

    def _prayer_of_healing(self, _opponent):
        before = self.health
        self.health = min(self.health + 50, self.max_health)
        restored = self.health - before
        slow_print(f"  🙏 {self.name} prays... restored {restored} HP. "
                   f"HP: {self.health}/{self.max_health}")

    def _divine_hymn(self, opponent):
        before = self.health
        self.health = min(self.health + 35, self.max_health)
        restored = self.health - before
        opponent.attack_power = max(0, opponent.attack_power - 5)
        slow_print(f"  🎵 Divine Hymn resonates! {self.name} healed {restored} HP. "
                   f"{opponent.name}'s attack weakened to {opponent.attack_power}.")

    def _holy_nova(self, opponent):
        damage = int(self.attack_power * 1.2)
        self._deal_damage(opponent, damage)
        before = self.health
        self.health = min(self.health + 20, self.max_health)
        slow_print(f"  💫 Holy Nova heals {self.name} for {self.health - before} HP. "
                   f"HP: {self.health}/{self.max_health}")


class Rogue(Character):
    """
    Rogue — Stealthy assassin who strikes fast and vanishes.

    Stats   : Moderate HP, high attack, strongest single-hit burst.
    Flavor  : Feast-or-famine. Can one-shot chunk the wizard or waste a turn.

    Abilities
    ---------
    1. Backstab    — High-risk, high-reward: 60 % chance of 3× damage, 40 % miss.
    2. Smoke Bomb  — Evade the next attack AND blind the opponent.
    3. Poison Blade — Apply poison: opponent takes 10 damage next wizard turn.
    4. Shadow Step  — Teleport behind enemy; guaranteed 2× damage ignoring shield.
    """

    def __init__(self, name):
        super().__init__(name, health=115, attack_power=36, heal_power=15)
        self.abilities = [
            {
                "name":         "🗡️  Backstab",
                "desc":         "60 % chance of 3× damage. Miss on 40 %.",
                "method":       self._backstab,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "💨 Smoke Bomb",
                "desc":         "Evade next attack and reduce opponent precision.",
                "method":       self._smoke_bomb,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "☠️  Poison Blade",
                "desc":         "Coat your blade — opponent takes 10 damage next turn.",
                "method":       self._poison_blade,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🌑 Shadow Step",
                "desc":         "Bypass shields; deal guaranteed 2× damage.",
                "method":       self._shadow_step,
                "max_cooldown": 2,
                "cooldown":     0,
            },
        ]

    def _backstab(self, opponent):
        if random.random() < 0.6:
            damage = self.attack_power * 3
            slow_print("  🗡️  Critical backstab!", delay=0.05)
            pause(0.3)
            self._deal_damage(opponent, damage)
        else:
            slow_print(f"  ❌ {self.name} missed! The opponent sidesteps.")

    def _smoke_bomb(self, opponent):
        self.status_effects["evade"] = True
        opponent.status_effects["blinded"] = True
        slow_print(f"  💨 Smoke fills the air! {self.name} will evade the next attack. "
                   f"{opponent.name} is blinded (50 % miss next turn).")

    def _poison_blade(self, opponent):
        opponent.status_effects["poisoned"] = True
        slow_print(f"  ☠️  {opponent.name} is poisoned! Takes 10 damage at the start of "
                   "the next wizard action.")

    def _shadow_step(self, opponent):
        damage = self.attack_power * 2
        opponent.health -= damage
        slow_print(f"  🌑 {self.name} shadow-steps! Deals {damage} damage, ignoring shields.")
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")


class Druid(Character):
    """
    Druid — Shape-shifting guardian of nature.

    Stats   : Moderate HP and attack; strong self-sustain.
    Flavor  : Flexible support-attacker. Can swap between forms each turn.

    Abilities
    ---------
    1. Wrath     — Nature bolt for 1.5× damage.
    2. Bear Form — Transform: gain 30 temporary HP and block the next hit.
    3. Regrowth  — Heal-over-time: restore 25 HP now and 15 next turn.
    4. Moonfire  — Mark opponent: they take 8 bonus damage every time they attack.
    """

    def __init__(self, name):
        super().__init__(name, health=130, attack_power=28, heal_power=25)
        self._regrowth_tick      = False
        self._moonfire_applied   = False
        self.abilities = [
            {
                "name":         "⚡ Wrath",
                "desc":         "Call down nature's fury for 1.5× damage.",
                "method":       self._wrath,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🐻 Bear Form",
                "desc":         "Hulk out: +30 temp HP and shield the next attack.",
                "method":       self._bear_form,
                "max_cooldown": 3,
                "cooldown":     0,
            },
            {
                "name":         "🌿 Regrowth",
                "desc":         "Heal 25 now; automatically heal 15 more next turn.",
                "method":       self._regrowth,
                "max_cooldown": 2,
                "cooldown":     0,
            },
            {
                "name":         "🌙 Moonfire",
                "desc":         "Mark opponent — they take 8 extra damage each time they attack.",
                "method":       self._moonfire,
                "max_cooldown": 0,
                "cooldown":     0,
            },
        ]

    def _wrath(self, opponent):
        damage = int(self.attack_power * 1.5)
        self._deal_damage(opponent, damage)

    def _bear_form(self, _opponent):
        self.health = min(self.health + 30, self.max_health + 30)
        self.status_effects["shield"] = True
        slow_print(f"  🐻 {self.name} transforms into a bear! +30 HP (now {self.health}) "
                   "and next hit blocked.")

    def _regrowth(self, _opponent):
        self.health = min(self.health + 25, self.max_health)
        self._regrowth_tick = True
        slow_print(f"  🌿 Regrowth blooms! {self.name} healed 25 HP. "
                   f"Another 15 HP will restore next turn. HP: {self.health}/{self.max_health}")

    def _moonfire(self, opponent):
        if not self._moonfire_applied:
            opponent.status_effects["moonfire"] = True
            self._moonfire_applied = True
            slow_print(f"  🌙 Moonfire sears {opponent.name}! They take 8 bonus damage "
                       "when they attack.")
        else:
            slow_print(f"  ❌ Moonfire is already burning on {opponent.name}!")

    def start_of_turn(self):
        """Apply regrowth tick if active — called by battle loop."""
        if self._regrowth_tick:
            self.health = min(self.health + 15, self.max_health)
            slow_print(f"  🌿 Regrowth heals {self.name} for 15 HP. "
                       f"HP: {self.health}/{self.max_health}")
            self._regrowth_tick = False


# ─────────────────────────────────────────────
#  EVIL WIZARD (ENHANCED)
# ─────────────────────────────────────────────

class EvilWizard(Character):
    """
    EvilWizard — The final boss.

    Enhancements
    ------------
    - Regenerates 3 HP per turn.
    - At 50 % HP, becomes Enraged (+5 ATK, announced once).
    - At 25 % HP, casts 'Void Surge' once for triple damage.
    - Against HolyPriest: applies Dark Suppression (halves healing, +10 chip damage/turn).
    - Taunts the player each turn.
    """

    def __init__(self, name):
        super().__init__(name, health=200, attack_power=20, heal_power=5)
        self._enraged   = False
        self._void_used = False

    def regenerate(self):
        """Regenerate 3 HP (does not exceed max)."""
        self.health = min(self.health + 3, self.max_health)
        slow_print(f"  🧙 {self.name} regenerates 3 HP. HP: {self.health}/{self.max_health}")

    def wizard_action(self, player):
        """
        Choose wizard's attack based on HP thresholds.
        If the player is a HolyPriest, applies Dark Suppression.
        Also taunts the player each turn.
        """
        # Tick statuses on wizard before acting
        self._tick_statuses()

        # Random taunt
        slow_print(f"\n  🧙 {self.name}: \"{random.choice(WIZARD_TAUNTS)}\"", delay=0.04)
        pause(0.4)

        # Enrage at 50 %
        if not self._enraged and self.health <= self.max_health * 0.5:
            self._enraged = True
            self.attack_power += 5
            slow_print(
                f"\n  ⚡ {self.name} becomes ENRAGED! Attack power → {self.attack_power}!",
                delay=0.05)
            pause(0.4)

        # Dark Suppression — activates only against a HolyPriest
        if isinstance(player, HolyPriest):
            if not player.status_effects.get("dark_suppressed"):
                player.status_effects["dark_suppressed"] = True
                player.heal_power = player.heal_power // 2
                slow_print(f"\n  🌑 {self.name} senses the Light within {player.name} "
                           "and unleashes DARK SUPPRESSION! Her healing is halved!", delay=0.05)
                pause(0.4)
            bonus = 10
            slow_print(f"  🌑 Dark energy sears {player.name} for {bonus} bonus damage!")
            player.health -= bonus
            if player.health <= 0:
                slow_print(f"  ☠️  {player.name} has been defeated!")
                return

        # Void Surge once at 25 %
        if not self._void_used and self.health <= self.max_health * 0.25:
            self._void_used = True
            damage = self.attack_power * 3
            slow_print(f"\n  🌑 {self.name} channels VOID SURGE!", delay=0.05)
            pause(0.5)
            self._hit_player(player, damage)
            return

        # Shadow Bolt at ≤ 50 %
        if self.health <= self.max_health * 0.5:
            damage = self.attack_power * 2
            slow_print(f"\n  💜 {self.name} hurls a SHADOW BOLT!", delay=0.05)
            pause(0.3)
            self._hit_player(player, damage)
        else:
            self.attack(player)

    def _hit_player(self, player, damage):
        """Deal exact damage to player (respects shield/evade)."""
        if player.status_effects.get("evade"):
            slow_print(f"  💨 {player.name} evades the attack!")
            player.status_effects["evade"] = False
            return
        if player.status_effects.get("shield"):
            slow_print(f"  🛡️  {player.name}'s shield absorbs the blow!")
            player.status_effects["shield"] = False
            return
        player.health -= damage
        slow_print(f"  💥 {player.name} takes {damage} damage! "
                   f"HP: {player.health}/{player.max_health}")
        if player.health <= 0:
            slow_print(f"  ☠️  {player.name} has been defeated!")

    def _tick_statuses(self):
        """Apply any status effects on the wizard at the start of its turn."""
        if self.status_effects.get("poisoned"):
            self.health -= 10
            slow_print(f"  ☠️  Poison deals 10 damage to {self.name}! "
                       f"HP: {self.health}/{self.max_health}")
            self.status_effects["poisoned"] = False


# ─────────────────────────────────────────────
#  GAME FUNCTIONS
# ─────────────────────────────────────────────

# Map of all available classes
CHARACTER_CLASSES = {
    "1": ("Warrior",      Warrior),
    "2": ("Mage",         Mage),
    "3": ("Archer",       Archer),
    "4": ("Paladin",      Paladin),
    "5": ("Death Knight", DeathKnight),
    "6": ("Holy Priest",  HolyPriest),
    "7": ("Rogue",        Rogue),
    "8": ("Druid",        Druid),
}


def create_character():
    """
    Display class selection menu and return a new player character instance.

    Returns
    -------
    Character subclass instance
    """
    print("\n" + "═" * 50)
    slow_print("  ⚔️   CHOOSE YOUR HERO   ⚔️", delay=0.04)
    print("═" * 50)

    # Each entry: (emoji, name, hp, atk, role)
    # Printed in fixed columns so everything lines up regardless of emoji width.
    descriptions = [
        ("🗡",  "Warrior",      160, 28, "Tank & sustain"),
        ("🔮",  "Mage",         100, 40, "Glass cannon"),
        ("🏹",  "Archer",       120, 32, "Speed & range"),
        ("🛡",  "Paladin",      150, 26, "Holy defender"),
        ("💀",  "Death Knight", 170, 34, "Dark drainer"),
        ("✨",  "Holy Priest",  200, 32, "Most resilient"),
        ("🌑",  "Rogue",        115, 36, "Assassin burst"),
        ("🌿",  "Druid",        130, 28, "Nature shaman"),
    ]

    for i, (emoji, cname, hp, atk, role) in enumerate(descriptions, start=1):
        print(f"  {i}. {emoji} {cname:<13} | HP: {hp:<3} | ATK: {atk:<2} | {role}")

    print("═" * 50)

    while True:
        choice = input("Enter the number of your class: ").strip()
        if choice in CHARACTER_CLASSES:
            break
        print("  ❌ Invalid choice — enter a number between 1 and 8.")

    name = input("Enter your character's name: ").strip() or "Hero"
    _, cls = CHARACTER_CLASSES[choice]
    player = cls(name)

    pause(0.3)
    intro = CLASS_INTROS.get(cls.__name__, f'  "{name}" steps forward.')
    slow_print("\n  " + intro.replace("{name}", name), delay=0.04)
    pause(0.6)

    return player


def _show_ability_menu(player):
    """
    Print the player's ability list with cooldown status and return their
    chosen index (0-based), or -1 if they cancel.
    """
    print("\n  ✨ Choose an ability:")
    for i, ability in enumerate(player.abilities, start=1):
        cd = ability.get("cooldown", 0)
        if cd > 0:
            status = f"  ⏳ {cd} turn(s)"
        else:
            status = "  ✅ Ready"
        print(f"    {i}. {ability['name']}{status} — {ability['desc']}")
    print("    0. Cancel")

    raw = input("  Ability number: ").strip()
    if raw == "0" or not raw.isdigit():
        return -1
    idx = int(raw) - 1
    if idx < 0 or idx >= len(player.abilities):
        print("  ❌ Out of range.")
        return -1
    return idx


def battle(player, wizard):
    """
    Main turn-based battle loop.

    Each iteration:
      1. HP bars are displayed.
      2. Player chooses an action.
      3. Wizard regenerates, taunts, then acts (if still alive).
      4. DOT / tick effects fire at appropriate times.

    Parameters
    ----------
    player : Character subclass instance
    wizard : EvilWizard instance
    """
    pause(0.5)
    slow_print(f"\n  💀 {wizard.name} appears from the shadows...", delay=0.05)
    pause(0.5)
    slow_print("  Prepare for battle! ⚔️", delay=0.05)
    pause(0.8)

    turn = 0
    while wizard.health > 0 and player.health > 0:
        turn += 1

        # ── Turn header with HP bars ──────────────────────────────────
        print(f"\n{'═' * 50}")
        slow_print(f"  ⚔️   TURN {turn}   ⚔️", delay=0.03)
        print(f"{'═' * 50}")
        print_hp_bars(player, wizard)

        # Some classes have start-of-turn hooks
        if hasattr(player, "start_of_turn"):
            player.start_of_turn()

        # ── Player's action ───────────────────────────────────────────
        print(f"\n  🎮 Your turn, {player.name}:")
        print("  1. ⚔️  Attack")
        print("  2. ✨ Use Special Ability")
        print("  3. 💚 Heal")
        print("  4. 📊 View Stats")

        valid = False
        while not valid:
            choice = input("\n  Action: ").strip()

            if choice == "1":
                player.attack(wizard)
                valid = True

            elif choice == "2":
                idx = _show_ability_menu(player)
                if idx >= 0:
                    player.use_ability(idx, wizard)
                    # Arcane Surge is a buff — give the Mage a follow-up action
                    if (hasattr(player, "_surge_active")
                            and player._surge_active  # pylint: disable=protected-access
                            and idx == 2):
                        slow_print(
                            "\n  ⚡ Surge is active — pick your follow-up action!"
                        )
                        follow = input("\n  Follow-up (1=Attack, skip=pass): ").strip()
                        if follow == "1":
                            player.attack(wizard)
                    valid = True
                else:
                    print("  Returning to action menu...")

            elif choice == "3":
                player.heal()
                valid = True

            elif choice == "4":
                print("\n  📊 --- Player ---")
                player.display_stats()
                print("  📊 --- Wizard ---")
                wizard.display_stats()
                # Don't count viewing stats as taking a turn

            else:
                print("  ❌ Invalid choice — try again.")

        # Tick cooldowns and end-of-turn hooks
        player.tick_cooldowns()
        if hasattr(player, "end_of_turn"):
            player.end_of_turn()

        # ── Wizard's turn (if still alive) ───────────────────────────
        if wizard.health > 0:
            pause(0.5)
            print(f"\n{'─' * 50}")
            slow_print(f"  🧙 {wizard.name}'s turn...", delay=0.04)
            print(f"{'─' * 50}")
            pause(0.3)
            wizard.regenerate()

            # Blinded (Rogue smoke bomb): 50 % miss
            if wizard.status_effects.get("blinded"):
                wizard.status_effects["blinded"] = False
                if random.random() < 0.5:
                    slow_print(f"  😵 {wizard.name} is blinded and stumbles — misses!")
                    continue  # skip wizard attack this turn

            wizard.wizard_action(player)

        if player.health <= 0:
            break

    # ── Outcome ───────────────────────────────────────────────────────
    pause(0.8)
    print(f"\n{'═' * 50}")
    if wizard.health <= 0:
        print_victory(player, wizard)
    else:
        print_defeat(player, wizard)
    print(f"{'═' * 50}\n")


def main():
    """Entry point — show title screen, create hero, and start the battle."""
    print_title()
    pause(0.5)
    player = create_character()
    wizard = EvilWizard("The Dark Wizard")
    battle(player, wizard)


if __name__ == "__main__":
    main()