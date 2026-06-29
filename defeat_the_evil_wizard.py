"""Run a turn-based hero-vs-boss fantasy battle game."""

import argparse
import os
import random
import subprocess
import sys
import time
import builtins
from dataclasses import dataclass, field
from typing import Callable

if os.name == "nt" and sys.flags.utf8_mode != 1 and os.environ.get("WIZARD_UTF8_REEXEC") != "1":
    script_path = os.path.abspath(sys.argv[0])
    cmd = [sys.executable, "-X", "utf8", script_path, *sys.argv[1:]]
    env = os.environ.copy()
    env["WIZARD_UTF8_REEXEC"] = "1"
    result = subprocess.run(cmd, check=False, env=env)
    sys.exit(result.returncode)

# ─────────────────────────────────────────────
#  DEBUG FLAG  (set by --debug CLI arg)
# ─────────────────────────────────────────────

DEBUG: bool = False

# ─────────────────────────────────────────────
#  NAMED CONSTANTS
# ─────────────────────────────────────────────

# Combat
ATTACK_ROLL_LOW          = 0.8    # lower bound of normal attack damage roll
ATTACK_ROLL_HIGH         = 1.2    # upper bound of normal attack damage roll
MOONFIRE_DAMAGE          = 8      # damage Moonfire deals to its owner per turn
POISON_DAMAGE            = 12     # damage poison deals at start of target's turn
BLINDED_MISS_CHANCE      = 0.5    # probability of missing while Blinded

# Warrior
WARRIOR_HP               = 160
WARRIOR_ATK              = 26
WARRIOR_HEAL             = 20
WARRIOR_SHIELD_BASH_MULT = 1.5
WARRIOR_WHIRLWIND_MULT   = 2.0
WARRIOR_BATTLE_CRY_BONUS = 8

# Mage
MAGE_HP                  = 105
MAGE_ATK                 = 38
MAGE_HEAL                = 15
MAGE_FIREBALL_MULT       = 1.8
MAGE_SURGE_BONUS         = 12

# Archer
ARCHER_HP                = 120
ARCHER_ATK               = 32
ARCHER_HEAL              = 18
ARCHER_QUICK_SHOT_MULT   = 0.7
ARCHER_SNIPER_MULT       = 1.7

# Paladin
PALADIN_HP               = 150
PALADIN_ATK              = 27
PALADIN_HEAL             = 28
PALADIN_HOLY_STRIKE_MULT = 1.5
PALADIN_CONSEC_MULT      = 0.9
PALADIN_CONSEC_HEAL      = 15

# Death Knight
DK_HP                    = 160
DK_ATK                   = 31
DK_HEAL                  = 16
DK_DEATH_COIL_DRAIN      = 18
DK_BLOOD_BOIL_COST       = 18
DK_BLOOD_BOIL_MULT       = 2.1
DK_DARK_PACT_DRAIN       = 20

# Holy Priest
PRIEST_HP                = 170
PRIEST_ATK               = 29
PRIEST_HEAL              = 30
PRIEST_SMITE_MULT        = 1.25
PRIEST_SMITE_BONUS       = 6
PRIEST_PRAYER_HEAL       = 40
PRIEST_HYMN_HEAL         = 25
PRIEST_HYMN_DEBUFF       = 4

# Rogue
ROGUE_HP                 = 120
ROGUE_ATK                = 34
ROGUE_HEAL               = 15
ROGUE_BACKSTAB_MULT      = 2.6
ROGUE_BACKSTAB_CHANCE    = 0.65

# Druid
DRUID_HP                 = 130
DRUID_ATK                = 30
DRUID_HEAL               = 25
DRUID_WRATH_MULT         = 1.5
DRUID_BEAR_HP_BONUS      = 24
DRUID_REGROWTH_INSTANT   = 20
DRUID_REGROWTH_TICK      = 12

# EvilWizard (normal / challenging)
WIZARD_HP_NORMAL         = 200
WIZARD_ATK_NORMAL        = 20
WIZARD_REGEN_NORMAL      = 3
WIZARD_DARK_DMG_NORMAL   = 10
WIZARD_HP_HARD           = 210
WIZARD_ATK_HARD          = 21
WIZARD_REGEN_HARD        = 3
WIZARD_DARK_DMG_HARD     = 11
WIZARD_ENRAGE_THRESHOLD  = 0.4   # fraction of max HP that triggers enrage
WIZARD_ENRAGE_BONUS      = 5
WIZARD_VOID_THRESHOLD    = 0.2   # fraction of max HP that triggers Void Surge
WIZARD_VOID_MULT         = 2.0
WIZARD_SHADOW_THRESHOLD  = 0.4   # fraction of max HP where Shadow Bolt phase begins
WIZARD_SHADOW_MULT       = 2.0

# AncientDragon (normal / challenging)
DRAGON_HP_NORMAL             = 210
DRAGON_ATK_NORMAL            = 17
DRAGON_REGEN_NORMAL          = 2
DRAGON_AURA_NORMAL           = 5
DRAGON_AURA_PRIEST_NORMAL    = 3
DRAGON_INFERNO_NORMAL        = 2.8
DRAGON_INFERNO_PRIEST_NORMAL = 2.2
DRAGON_TAIL_NORMAL           = 1.9
DRAGON_HP_HARD               = 210
DRAGON_ATK_HARD              = 17
DRAGON_REGEN_HARD            = 2
DRAGON_AURA_HARD             = 5
DRAGON_AURA_PRIEST_HARD      = 3
DRAGON_INFERNO_HARD          = 2.5
DRAGON_INFERNO_PRIEST_HARD   = 2.0
DRAGON_TAIL_HARD             = 2.0
DRAGON_ENRAGE_THRESHOLD      = 0.4
DRAGON_ENRAGE_BONUS          = 6
DRAGON_INFERNO_THRESHOLD     = 0.2
DRAGON_FURY_THRESHOLD        = 3    # tail slam fires every N fury stacks
DRAGON_CLAW_LOW              = 0.6
DRAGON_CLAW_HIGH             = 0.9

# Gauntlet
BETWEEN_BOSS_HEAL_RATIO  = 0.35

# UI
HP_BAR_WIDTH             = 24
HP_BAR_NAME_COL          = 16

# ─────────────────────────────────────────────
#  DISPLAY CONSTANTS
# ─────────────────────────────────────────────

CLASS_EMOJI = {
    "Warrior":       "⚔️",
    "Mage":          "🔮",
    "Archer":        "🏹",
    "Paladin":       "🛡️",
    "DeathKnight":   "💀",
    "HolyPriest":    "✨",
    "Rogue":         "🗡️",
    "Druid":         "🌿",
    "EvilWizard":    "🧙",
    "AncientDragon": "🐉",
}

WIZARD_TAUNTS = [
    "You dare challenge ME?! 😈",
    "Your suffering amuses me... 🌑",
    "The darkness will consume you! 🌑",
    "Tremble before my power! 💜",
    "You cannot win... give up now! 😈",
]

DRAGON_TAUNTS = [
    "You enter my lair and expect mercy? 🐲",
    "I have burned kingdoms to ash. 🔥",
    "Feel the heat of the abyss! 🌋",
]

CLASS_INTROS = {
    "Warrior":     "🗡️  \"{name}\" cracks their knuckles. \"Let's make this quick.\"",
    "Mage":        "🔮  \"{name}\" crackles with arcane energy.",
    "Archer":      "🏹  \"{name}\" notches an arrow. \"I never miss.\"",
    "Paladin":     "🛡️  \"{name}\" raises their shield.",
    "DeathKnight": "💀  \"{name}\" rises from shadow.",
    "HolyPriest":  "✨  \"{name}\" glows with divine radiance.",
    "Rogue":       "🗡️  \"{name}\" melts from the shadows.",
    "Druid":       "🌿  \"{name}\" communes with nature.",
}

TOMBSTONE = [
    ".-------.",
    "|       |",
    "| R.I.P |",
    "|       |",
    "|{name:^7}|",
    "|       |",
    "__|_______|__",
    "|             |",
    "__|___________|__",
]

# ─────────────────────────────────────────────
#  STATUS EFFECT KEYS & LABELS
# ─────────────────────────────────────────────

STATUS_EVADE           = "evade"
STATUS_SHIELD          = "shield"
STATUS_FROZEN          = "frozen"
STATUS_BLINDED         = "blinded"
STATUS_POISONED        = "poisoned"
STATUS_MOONFIRE        = "moonfire"
STATUS_DARK_SUPPRESSED = "dark_suppressed"

STATUS_LABELS = {
    STATUS_EVADE:           "Evade",
    STATUS_SHIELD:          "Shield",
    STATUS_FROZEN:          "Frozen",
    STATUS_BLINDED:         "Blinded",
    STATUS_POISONED:        "Poisoned",
    STATUS_MOONFIRE:        "Moonfire",
    STATUS_DARK_SUPPRESSED: "Dark Suppressed",
}

# ─────────────────────────────────────────────
#  ABILITY DATACLASS
# ─────────────────────────────────────────────

@dataclass
class Ability:
    """Represents a single hero ability with metadata and cooldown tracking."""

    name:         str
    desc:         str
    method:       Callable
    max_cooldown: int  = 0
    cooldown:     int  = field(default=0, init=False)

    def is_ready(self) -> bool:
        """Return True if this ability is off cooldown and can be used."""
        return self.cooldown == 0

    def trigger(self, opponent) -> None:
        """Fire the ability against the given opponent and start its cooldown."""
        self.method(opponent)
        self.cooldown = self.max_cooldown

    def tick(self) -> None:
        """Reduce the remaining cooldown by one, floored at zero."""
        if self.cooldown > 0:
            self.cooldown -= 1


# ─────────────────────────────────────────────
#  RESISTANCE PROFILE
# ─────────────────────────────────────────────

@dataclass
class ResistanceProfile:
    """Describes how a hero interacts with boss-specific mechanics.

    Bosses read this profile instead of doing isinstance checks, keeping
    boss code decoupled from specific hero classes.
    """

    holy_aura_reduced:  bool  = False   # AncientDragon deals reduced aura damage
    dark_suppressed:    bool  = False   # EvilWizard applies Dark Suppression
    dark_bonus_damage:  int   = 0       # extra damage EvilWizard deals each turn


# ─────────────────────────────────────────────
#  IO HELPERS
# ─────────────────────────────────────────────

def prompt_input(prompt="") -> str:
    """Read a line from stdin; exit gracefully on EOF or keyboard interrupt."""
    try:
        return builtins.input(prompt)
    except EOFError:
        print("\n  ❌ No interactive input is available.")
        print("  Run this game in an interactive terminal (PowerShell/VS Code Terminal).")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  👋 Game interrupted.")
        sys.exit(0)


def slow_print(text: str, delay: float = 0.03) -> None:
    """Print text one character at a time for a dramatic effect."""
    if DEBUG:
        print(text)
        return
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def pause(seconds: float = 0.6) -> None:
    """Sleep for the given number of seconds (skipped in debug mode)."""
    if not DEBUG:
        time.sleep(seconds)


# ─────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────

def print_hp_bars(player: "Character", boss: "Character") -> None:
    """Print side-by-side HP bars scaled to each character's max health."""
    highest = max(player.max_health, boss.max_health)

    def make_bar(label: str, character: "Character") -> str:
        """Build a single labelled HP bar string."""
        bar_width = max(1, int(HP_BAR_WIDTH * character.max_health / highest))
        filled    = int(bar_width * max(character.health, 0) / character.max_health)
        hp_bar    = "█" * filled + "░" * (bar_width - filled)
        name      = character.name[:HP_BAR_NAME_COL].ljust(HP_BAR_NAME_COL)
        return f"{label} {name} [{hp_bar}] {character.health}/{character.max_health}"

    print(f"\n  {make_bar('YOU', player)}")
    print(f"  {make_bar('FOE', boss)}\n")


def print_title() -> None:
    """Print the game title banner."""
    print("\n" + "═" * 50)
    slow_print("  ⚔️   DEFEAT THE EVIL WIZARD   ⚔️", delay=0.04)
    slow_print("  Defeat the Evil Wizard before he destroys the realm...", delay=0.03)
    print("═" * 50)
    pause(0.8)


def print_victory(player: "Character", boss: "Character", final_boss: bool = True) -> None:
    """Print the victory screen after defeating a boss."""
    print("\n" + "═" * 50)
    slow_print(f"  🏆  {player.name} has defeated {boss.name}!")
    if final_boss:
        slow_print("  The darkness recedes. Light returns to the realm. ✨")
    else:
        slow_print("  A new threat stirs... this war is not over yet. ⚔️")
    print("═" * 50)


def print_defeat(player: "Character", boss: "Character") -> None:
    """Print the defeat screen with a tombstone and GAME OVER banner."""
    print("\n" + "═" * 50)
    for line in TOMBSTONE:
        slow_print("  " + line.format(name=player.name[:7]), delay=0.02)
        pause(0.05)
    pause(0.3)
    slow_print("\n  * * * G A M E   O V E R * * *")
    slow_print(f"  {boss.name} cackles in triumph... the realm is lost. 🌑")
    print("═" * 50)


# ─────────────────────────────────────────────
#  BASE CHARACTER
# ─────────────────────────────────────────────

class Character:
    """Shared stats, combat methods, and status-effect logic for all characters."""

    def __init__(
        self,
        name:         str,
        *,
        health:       int,
        attack_power: int,
        heal_power:   int = 20,
    ) -> None:
        """Initialise core stats and empty ability/status containers."""
        self.name                              = name
        self.health                            = health
        self.attack_power                      = attack_power
        self.max_health                        = health
        self.heal_power                        = heal_power
        self.abilities:     list[Ability]      = []
        self.status_effects: dict[str, bool]   = {}

    @property
    def resistance_profile(self) -> ResistanceProfile:
        """Return this character's resistance profile for boss interaction.

        Override in hero subclasses that have special boss interactions.
        The default profile has no special resistances or vulnerabilities.
        """
        return ResistanceProfile()

    def attack(self, opponent: "Character") -> None:
        """Deal randomised physical damage; respect Moonfire, Evade, and Shield."""
        if self.status_effects.get(STATUS_MOONFIRE):
            self.health -= MOONFIRE_DAMAGE
            slow_print(f"  🌙 Moonfire burns {self.name} for {MOONFIRE_DAMAGE} damage!")
            if self.health <= 0:
                slow_print(f"  ☠️  {self.name} is consumed by Moonfire!")
                return

        if opponent.try_negate_incoming_attack(self.name):
            return

        damage = random.randint(
            int(self.attack_power * ATTACK_ROLL_LOW),
            int(self.attack_power * ATTACK_ROLL_HIGH),
        )
        opponent.health -= damage
        slow_print(f"  ⚔️  {self.name} attacks {opponent.name} for {damage} damage!")
        if opponent.health <= 0:
            slow_print(f"  💥 {opponent.name} has been defeated!")

    def heal(self) -> None:
        """Restore HP up to max using this character's heal_power."""
        before = self.health
        self.health = min(self.health + self.heal_power, self.max_health)
        healed = self.health - before
        slow_print(
            f"  💚 {self.name} heals for {healed} HP!"
            f" ({self.health}/{self.max_health})"
        )

    def use_ability(self, index: int, opponent: "Character") -> None:
        """Fire the ability at the given index if it exists and is off cooldown."""
        if index < 0 or index >= len(self.abilities):
            print("  ❌ Invalid ability choice.")
            return
        ab = self.abilities[index]
        if not ab.is_ready():
            slow_print(
                f"  ⏳ {ab.name} is on cooldown for {ab.cooldown} more turn(s)!"
            )
            return
        slow_print(f"\n  ✨ {self.name} uses {ab.name}!", delay=0.05)
        pause(0.3)
        ab.trigger(opponent)

    def tick_cooldowns(self) -> None:
        """Reduce every ability's remaining cooldown by one at end of turn."""
        for ab in self.abilities:
            ab.tick()

    def start_of_turn(self) -> None:
        """Hook called at the start of this character's turn (override in subclasses)."""

    def end_of_turn(self) -> None:
        """Hook called at the end of this character's turn (override in subclasses)."""

    def wants_follow_up_after_ability(self, _ability_index: int) -> bool:
        """Return True if this character gets a bonus action after the given ability."""
        return False

    def follow_up_action(self, _opponent: "Character") -> None:
        """Execute the bonus follow-up action (override in subclasses that need it)."""

    def try_negate_incoming_attack(self, attacker_name: str) -> bool:
        """Consume Evade or Shield to block an incoming hit; return True if blocked."""
        if self.status_effects.get(STATUS_EVADE):
            slow_print(f"  💨 {self.name} evades {attacker_name}'s attack!")
            self.status_effects[STATUS_EVADE] = False
            return True
        if self.status_effects.get(STATUS_SHIELD):
            slow_print(f"  🛡️  {self.name}'s shield absorbs the attack!")
            self.status_effects[STATUS_SHIELD] = False
            return True
        return False

    def should_skip_turn_from_control(self) -> bool:
        """Return True and print a message if Frozen or Blinded causes a lost turn."""
        if self.status_effects.get(STATUS_FROZEN):
            self.status_effects[STATUS_FROZEN] = False
            slow_print(f"  ❄️  {self.name} is frozen and cannot act this turn!")
            return True
        if self.status_effects.get(STATUS_BLINDED):
            self.status_effects[STATUS_BLINDED] = False
            if random.random() < BLINDED_MISS_CHANCE:
                slow_print(f"  😵 {self.name} is blinded and stumbles — misses!")
                return True
        return False

    def display_stats(self) -> None:
        """Print a detailed stat block including HP bar and active status effects."""
        bar_len = 20
        filled  = int(bar_len * max(self.health, 0) / self.max_health)
        hp_bar  = "█" * filled + "░" * (bar_len - filled)
        emoji   = CLASS_EMOJI.get(type(self).__name__, "❓")
        print(
            f"\n  {emoji} {self.name} | [{hp_bar}] {self.health}/{self.max_health} HP"
            f" | ⚔️  ATK {self.attack_power}"
        )
        active = [
            STATUS_LABELS.get(k, k.replace("_", " ").title())
            for k, v in self.status_effects.items() if v
        ]
        if active:
            print(f"     🔮 Active effects: {', '.join(active)}")

    def _deal_damage(self, opponent: "Character", damage: int) -> None:
        """Apply a fixed damage value to opponent and report remaining HP."""
        opponent.health -= damage
        slow_print(
            f"  💥 {opponent.name} takes {damage} damage!"
            f" ({opponent.health}/{opponent.max_health} HP remaining)"
        )
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _drain_life(
        self, opponent: "Character", amount: int
    ) -> tuple[int, int]:
        """Remove HP from opponent and add it to self; return (opponent_hp, self_hp)."""
        opponent.health -= amount
        self.health = min(self.health + amount, self.max_health)
        return opponent.health, self.health


# ─────────────────────────────────────────────
#  HERO CLASSES
# ─────────────────────────────────────────────

class Warrior(Character):
    """Tank with sustain, shields, and a permanent attack buff."""

    def __init__(self, name: str) -> None:
        """Set up Warrior stats and abilities."""
        super().__init__(
            name,
            health=WARRIOR_HP,
            attack_power=WARRIOR_ATK,
            heal_power=WARRIOR_HEAL,
        )
        self._battle_cry_used = False
        self.abilities = [
            Ability(
                "⚔️  Shield Bash",
                "Deal 1.5× damage and block the opponent's next attack.",
                self._shield_bash, max_cooldown=2,
            ),
            Ability(
                "🌀 Whirlwind",
                "Spin attack dealing 2× damage.",
                self._whirlwind, max_cooldown=2,
            ),
            Ability(
                "📣 Battle Cry",
                "One-time war cry: raise your attack power by 8 permanently.",
                self._battle_cry, max_cooldown=3,
            ),
        ]

    def _shield_bash(self, opponent: Character) -> None:
        """Deal 1.5× damage then raise a shield against the next incoming hit."""
        self._deal_damage(opponent, int(self.attack_power * WARRIOR_SHIELD_BASH_MULT))
        self.status_effects[STATUS_SHIELD] = True
        slow_print(f"  🛡️  {self.name} raises shield — next attack will be blocked!")

    def _whirlwind(self, opponent: Character) -> None:
        """Spin and deal 2× damage to the opponent."""
        self._deal_damage(opponent, int(self.attack_power * WARRIOR_WHIRLWIND_MULT))

    def _battle_cry(self, _opponent: Character) -> None:
        """Permanently raise attack power by 8; usable only once per battle."""
        if self._battle_cry_used:
            slow_print("  ❌ Battle Cry can only be used once per battle!")
            return
        self.attack_power += WARRIOR_BATTLE_CRY_BONUS
        self._battle_cry_used = True
        slow_print(f"  📣 {self.name} roars! Attack power raised to {self.attack_power}.")


class Mage(Character):
    """Glass cannon with a surge mechanic for double-action turns."""

    def __init__(self, name: str) -> None:
        """Set up Mage stats and abilities."""
        super().__init__(
            name,
            health=MAGE_HP,
            attack_power=MAGE_ATK,
            heal_power=MAGE_HEAL,
        )
        self._surge_active = False
        self.abilities = [
            Ability(
                "🔥 Fireball",
                "Hurl a fireball for 1.8× damage.",
                self._fireball, max_cooldown=2,
            ),
            Ability(
                "❄️  Frost Nova",
                "Freeze the opponent; they lose their next attack.",
                self._frost_nova, max_cooldown=4,
            ),
            Ability(
                "⚡ Arcane Surge",
                "Boost attack power by 12 — then pick a follow-up action.",
                self._arcane_surge, max_cooldown=3,
            ),
        ]

    def _fireball(self, opponent: Character) -> None:
        """Hurl a fireball dealing 1.8× attack damage."""
        self._deal_damage(opponent, int(self.attack_power * MAGE_FIREBALL_MULT))

    def _frost_nova(self, opponent: Character) -> None:
        """Freeze the opponent so they skip their next turn."""
        opponent.status_effects[STATUS_FROZEN] = True
        slow_print(f"  ❄️  {opponent.name} is frozen and will skip their next turn!")

    def _arcane_surge(self, _opponent: Character) -> None:
        """Temporarily boost attack power and enable a follow-up action."""
        self.attack_power  += MAGE_SURGE_BONUS
        self._surge_active  = True
        slow_print(
            f"  ⚡ Arcane Surge active! Your attack power is now {self.attack_power}.\n"
            f"  💡 Your NEXT attack or ability this turn hits at full surge power.\n"
            f"  ⚠️  The bonus expires automatically after the boss's turn."
        )

    def end_of_turn(self) -> None:
        """Expire the Arcane Surge bonus at the end of the Mage's turn."""
        if self._surge_active:
            self.attack_power  -= MAGE_SURGE_BONUS
            self._surge_active  = False

    def wants_follow_up_after_ability(self, ability_index: int) -> bool:
        """Return True when Arcane Surge is active so the player gets a bonus action."""
        return self._surge_active and ability_index == 2

    def follow_up_action(self, opponent: Character) -> None:
        """Prompt the player to attack or pass as the surge follow-up."""
        slow_print("\n  ⚡ Surge is active — pick your follow-up action!")
        if prompt_input("\n  Follow-up (1=Attack, skip=pass): ").strip() == "1":
            self.attack(opponent)


class Archer(Character):
    """Speed and range specialist with a guaranteed-dodge utility."""

    def __init__(self, name: str) -> None:
        """Set up Archer stats and abilities."""
        super().__init__(
            name,
            health=ARCHER_HP,
            attack_power=ARCHER_ATK,
            heal_power=ARCHER_HEAL,
        )
        self.abilities = [
            Ability(
                "🏹 Quick Shot",
                "Two fast arrows — each deals 0.7× damage.",
                self._quick_shot, max_cooldown=2,
            ),
            Ability(
                "🎯 Sniper Shot",
                "Bypasses all defenses for 1.7× damage.",
                self._sniper_shot, max_cooldown=2,
            ),
            Ability(
                "💨 Evade",
                "Guarantee a dodge on the next attack aimed at you.",
                self._evade, max_cooldown=3,
            ),
        ]

    def _quick_shot(self, opponent: Character) -> None:
        """Fire two arrows, each dealing 0.7× damage."""
        for i in range(1, 3):
            slow_print(f"  🏹 Arrow {i}:", delay=0.02)
            self._deal_damage(opponent, int(self.attack_power * ARCHER_QUICK_SHOT_MULT))

    def _sniper_shot(self, opponent: Character) -> None:
        """Deal 1.7× damage that bypasses Evade and Shield."""
        damage = int(self.attack_power * ARCHER_SNIPER_MULT)
        opponent.health -= damage
        slow_print(
            f"  🎯 Sniper Shot pierces defenses! {opponent.name} takes {damage} damage."
            f" ({opponent.health}/{opponent.max_health} HP)"
        )
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _evade(self, _opponent: Character) -> None:
        """Set the Evade status so the next incoming attack is dodged."""
        self.status_effects[STATUS_EVADE] = True
        slow_print(f"  💨 {self.name} readies a dodge — next attack will miss!")


class Paladin(Character):
    """Holy defender with strong heals and a damage-absorbing shield."""

    def __init__(self, name: str) -> None:
        """Set up Paladin stats and abilities."""
        super().__init__(
            name,
            health=PALADIN_HP,
            attack_power=PALADIN_ATK,
            heal_power=PALADIN_HEAL,
        )
        self.abilities = [
            Ability(
                "✝️  Holy Strike",
                "A blessed strike for 1.5× damage.",
                self._holy_strike, max_cooldown=2,
            ),
            Ability(
                "🛡️  Divine Shield",
                "Block the next attack aimed at you.",
                self._divine_shield, max_cooldown=3,
            ),
            Ability(
                "🔥 Consecration",
                "Deal moderate damage and heal yourself 15 HP.",
                self._consecration, max_cooldown=2,
            ),
        ]

    def _holy_strike(self, opponent: Character) -> None:
        """Strike with holy power for 1.5× damage."""
        self._deal_damage(opponent, int(self.attack_power * PALADIN_HOLY_STRIKE_MULT))

    def _divine_shield(self, _opponent: Character) -> None:
        """Raise a divine shield that absorbs the next incoming attack."""
        self.status_effects[STATUS_SHIELD] = True
        slow_print(f"  🛡️  {self.name} is shielded — the next attack will be absorbed!")

    def _consecration(self, opponent: Character) -> None:
        """Deal 0.9× damage and heal self for 15 HP."""
        self._deal_damage(opponent, int(self.attack_power * PALADIN_CONSEC_MULT))
        self.health = min(self.health + PALADIN_CONSEC_HEAL, self.max_health)
        slow_print(
            f"  🔥 Holy ground heals {self.name} for {PALADIN_CONSEC_HEAL}."
            f" HP: {self.health}/{self.max_health}"
        )


class DeathKnight(Character):
    """Dark drainer who trades and steals HP to stay alive."""

    def __init__(self, name: str) -> None:
        """Set up DeathKnight stats and abilities."""
        super().__init__(
            name,
            health=DK_HP,
            attack_power=DK_ATK,
            heal_power=DK_HEAL,
        )
        self.abilities = [
            Ability(
                "💀 Death Coil",
                f"Dark bolt that steals {DK_DEATH_COIL_DRAIN} HP from the opponent.",
                self._death_coil, max_cooldown=2,
            ),
            Ability(
                "🩸 Blood Boil",
                f"Sacrifice {DK_BLOOD_BOIL_COST} HP to unleash 2.1× damage.",
                self._blood_boil, max_cooldown=2,
            ),
            Ability(
                "🌑 Dark Pact",
                f"Drain {DK_DARK_PACT_DRAIN} HP from opponent directly into your pool.",
                self._dark_pact, max_cooldown=3,
            ),
        ]

    def _death_coil(self, opponent: Character) -> None:
        """Steal HP from the opponent and add it to self."""
        opp_hp, self_hp = self._drain_life(opponent, DK_DEATH_COIL_DRAIN)
        slow_print(
            f"  💀 Death Coil drains {DK_DEATH_COIL_DRAIN} HP from {opponent.name}!"
            f" {self.name} absorbs the life. HP: {self_hp}/{self.max_health}"
        )
        if opp_hp <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _blood_boil(self, opponent: Character) -> None:
        """Sacrifice HP to deal 2.1× damage; blocked if HP is too low."""
        if self.health <= DK_BLOOD_BOIL_COST:
            slow_print("  ❌ Not enough HP to sacrifice for Blood Boil!")
            return
        self.health -= DK_BLOOD_BOIL_COST
        slow_print(
            f"  🩸 {self.name} sacrifices {DK_BLOOD_BOIL_COST} HP..."
            f" HP: {self.health}/{self.max_health}"
        )
        self._deal_damage(opponent, int(self.attack_power * DK_BLOOD_BOIL_MULT))

    def _dark_pact(self, opponent: Character) -> None:
        """Drain HP directly from the opponent into self."""
        opp_hp, self_hp = self._drain_life(opponent, DK_DARK_PACT_DRAIN)
        slow_print(
            f"  🌑 Dark Pact! Drained {DK_DARK_PACT_DRAIN} HP from {opponent.name}."
            f" {self.name} HP: {self_hp}/{self.max_health}"
        )
        if opp_hp <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")


class HolyPriest(Character):
    """Light-sustain healer who weakens opponents over time."""

    def __init__(self, name: str) -> None:
        """Set up HolyPriest stats and abilities."""
        super().__init__(
            name,
            health=PRIEST_HP,
            attack_power=PRIEST_ATK,
            heal_power=PRIEST_HEAL,
        )
        self.abilities = [
            Ability(
                "✨ Smite",
                "Channel the Light for 1.25× holy damage.",
                self._smite, max_cooldown=2,
            ),
            Ability(
                "🙏 Prayer of Healing",
                f"Restore {PRIEST_PRAYER_HEAL} HP through divine grace.",
                self._prayer_of_healing, max_cooldown=3,
            ),
            Ability(
                "🎵 Divine Hymn",
                f"Heal {PRIEST_HYMN_HEAL} HP and weaken opponent's attack by"
                f" {PRIEST_HYMN_DEBUFF}.",
                self._divine_hymn, max_cooldown=4,
            ),
        ]

    @property
    def resistance_profile(self) -> ResistanceProfile:
        """HolyPriest has reduced dragon aura and triggers wizard Dark Suppression."""
        return ResistanceProfile(
            holy_aura_reduced=True,
            dark_suppressed=self.status_effects.get(STATUS_DARK_SUPPRESSED, False),
            dark_bonus_damage=WIZARD_DARK_DMG_NORMAL,
        )

    def _smite(self, opponent: Character) -> None:
        """Channel the Light for 1.25× damage plus a flat bonus."""
        self._deal_damage(
            opponent,
            int(self.attack_power * PRIEST_SMITE_MULT) + PRIEST_SMITE_BONUS,
        )

    def _prayer_of_healing(self, _opponent: Character) -> None:
        """Restore HP through divine prayer."""
        before = self.health
        self.health = min(self.health + PRIEST_PRAYER_HEAL, self.max_health)
        slow_print(
            f"  🙏 {self.name} prays... restored {self.health - before} HP."
            f" HP: {self.health}/{self.max_health}"
        )

    def _divine_hymn(self, opponent: Character) -> None:
        """Heal HP and permanently reduce the opponent's attack power."""
        before = self.health
        self.health = min(self.health + PRIEST_HYMN_HEAL, self.max_health)
        opponent.attack_power = max(0, opponent.attack_power - PRIEST_HYMN_DEBUFF)
        slow_print(
            f"  🎵 Divine Hymn resonates! {self.name} healed {self.health - before} HP."
            f" {opponent.name}'s attack weakened to {opponent.attack_power}."
        )


class Rogue(Character):
    """Assassin with high-risk burst, poison, and smoke utility."""

    def __init__(self, name: str) -> None:
        """Set up Rogue stats and abilities."""
        super().__init__(
            name,
            health=ROGUE_HP,
            attack_power=ROGUE_ATK,
            heal_power=ROGUE_HEAL,
        )
        self.abilities = [
            Ability(
                "🗡️  Backstab",
                f"{int(ROGUE_BACKSTAB_CHANCE * 100)} % chance of 2.6× damage."
                f" Miss on {int((1 - ROGUE_BACKSTAB_CHANCE) * 100)} %.",
                self._backstab, max_cooldown=2,
            ),
            Ability(
                "💨 Smoke Bomb",
                "Evade next attack and reduce opponent precision.",
                self._smoke_bomb, max_cooldown=3,
            ),
            Ability(
                "☠️  Poison Blade",
                f"Coat your blade — opponent takes {POISON_DAMAGE} damage next turn.",
                self._poison_blade, max_cooldown=2,
            ),
        ]

    def _backstab(self, opponent: Character) -> None:
        """Deal high damage on a hit chance; otherwise miss entirely."""
        if random.random() < ROGUE_BACKSTAB_CHANCE:
            slow_print("  🗡️  Critical backstab!", delay=0.05)
            pause(0.3)
            self._deal_damage(opponent, int(self.attack_power * ROGUE_BACKSTAB_MULT))
        else:
            slow_print(f"  ❌ {self.name} missed! The opponent sidesteps.")

    def _smoke_bomb(self, opponent: Character) -> None:
        """Grant self Evade and apply Blinded to the opponent."""
        self.status_effects[STATUS_EVADE]       = True
        opponent.status_effects[STATUS_BLINDED] = True
        slow_print(
            f"  💨 Smoke fills the air! {self.name} will evade the next attack."
            f" {opponent.name} is blinded ({int(BLINDED_MISS_CHANCE * 100)} % miss"
            " next turn)."
        )

    def _poison_blade(self, opponent: Character) -> None:
        """Apply Poisoned to the opponent; deals damage at start of their next turn."""
        opponent.status_effects[STATUS_POISONED] = True
        slow_print(
            f"  ☠️  {opponent.name} is poisoned!"
            f" Takes {POISON_DAMAGE} damage at the start of the next boss action."
        )


class Druid(Character):
    """Nature shaman with a delayed heal-over-time and a bear form."""

    def __init__(self, name: str) -> None:
        """Set up Druid stats and abilities."""
        super().__init__(
            name,
            health=DRUID_HP,
            attack_power=DRUID_ATK,
            heal_power=DRUID_HEAL,
        )
        self._regrowth_tick = False
        self.abilities = [
            Ability(
                "⚡ Wrath",
                "Call down nature's fury for 1.5× damage.",
                self._wrath, max_cooldown=2,
            ),
            Ability(
                "🐻 Bear Form",
                f"Hulk out: +{DRUID_BEAR_HP_BONUS} temp HP and shield the next attack.",
                self._bear_form, max_cooldown=3,
            ),
            Ability(
                "🌿 Regrowth",
                f"Heal {DRUID_REGROWTH_INSTANT} now; heal {DRUID_REGROWTH_TICK} more"
                " next turn.",
                self._regrowth, max_cooldown=2,
            ),
        ]

    def _wrath(self, opponent: Character) -> None:
        """Call nature's fury for 1.5× damage."""
        self._deal_damage(opponent, int(self.attack_power * DRUID_WRATH_MULT))

    def _bear_form(self, _opponent: Character) -> None:
        """Gain temporary HP and shield the next incoming attack."""
        self.health = min(self.health + DRUID_BEAR_HP_BONUS, self.max_health + DRUID_BEAR_HP_BONUS)
        self.status_effects[STATUS_SHIELD] = True
        slow_print(
            f"  🐻 {self.name} transforms into a bear!"
            f" +{DRUID_BEAR_HP_BONUS} HP (now {self.health}) and next hit blocked."
        )

    def _regrowth(self, _opponent: Character) -> None:
        """Heal HP now and queue a tick for the start of the next turn."""
        self.health = min(self.health + DRUID_REGROWTH_INSTANT, self.max_health)
        self._regrowth_tick = True
        slow_print(
            f"  🌿 Regrowth blooms! {self.name} healed {DRUID_REGROWTH_INSTANT} HP."
            f" Another {DRUID_REGROWTH_TICK} HP will restore next turn."
            f" HP: {self.health}/{self.max_health}"
        )

    def start_of_turn(self) -> None:
        """Apply the queued Regrowth tick at the start of the Druid's turn."""
        if self._regrowth_tick:
            self.health = min(self.health + DRUID_REGROWTH_TICK, self.max_health)
            slow_print(
                f"  🌿 Regrowth heals {self.name} for {DRUID_REGROWTH_TICK} HP."
                f" HP: {self.health}/{self.max_health}"
            )
            self._regrowth_tick = False


# ─────────────────────────────────────────────
#  BASE BOSS
# ─────────────────────────────────────────────

class Boss(Character):
    """Shared logic for all boss types: regen, poison tick, and direct hit."""

    _regen_per_turn: int = 0

    def regenerate(self, emoji: str = "💜") -> None:
        """Restore a fixed amount of HP at the start of each boss turn."""
        self.health = min(self.health + self._regen_per_turn, self.max_health)
        slow_print(
            f"  {emoji} {self.name} regenerates {self._regen_per_turn} HP."
            f" HP: {self.health}/{self.max_health}"
        )

    def _tick_statuses(self) -> None:
        """Resolve any active status effects on this boss before it acts."""
        if self.status_effects.get(STATUS_POISONED):
            self.health -= POISON_DAMAGE
            slow_print(
                f"  ☠️  Poison deals {POISON_DAMAGE} damage to {self.name}!"
                f" HP: {self.health}/{self.max_health}"
            )
            self.status_effects[STATUS_POISONED] = False

    def _hit_player(self, player: Character, damage: int) -> None:
        """Apply damage directly to the player, bypassing the standard attack roll."""
        if player.try_negate_incoming_attack(self.name):
            return
        player.health -= damage
        slow_print(
            f"  💥 {player.name} takes {damage} damage!"
            f" HP: {player.health}/{player.max_health}"
        )
        if player.health <= 0:
            slow_print(f"  ☠️  {player.name} has been defeated!")

    def take_turn(self, player: Character) -> None:
        """Execute the boss's full turn; subclasses must implement this."""
        raise NotImplementedError


# ─────────────────────────────────────────────
#  BOSS CLASSES
# ─────────────────────────────────────────────

class EvilWizard(Boss):
    """Regenerating spellcaster with suppression, enrage, and void burst."""

    def __init__(self, name: str, difficulty: str = "normal") -> None:
        """Set up EvilWizard stats scaled to the chosen difficulty."""
        if difficulty == "challenging":
            health  = WIZARD_HP_HARD
            attack  = WIZARD_ATK_HARD
            regen   = WIZARD_REGEN_HARD
            dark_dmg = WIZARD_DARK_DMG_HARD
        else:
            health  = WIZARD_HP_NORMAL
            attack  = WIZARD_ATK_NORMAL
            regen   = WIZARD_REGEN_NORMAL
            dark_dmg = WIZARD_DARK_DMG_NORMAL
        super().__init__(name, health=health, attack_power=attack, heal_power=5)
        self.difficulty         = difficulty
        self._regen_per_turn    = regen
        self._dark_bonus_damage = dark_dmg
        self._enraged           = False
        self._void_used         = False

    def take_turn(self, player: Character) -> None:
        """Regenerate, tick statuses, then execute the wizard's combat action."""
        self.regenerate(emoji="🧙")
        self._tick_statuses()

        if self.should_skip_turn_from_control():
            return

        slow_print(f"\n  🧙 {self.name}: \"{random.choice(WIZARD_TAUNTS)}\"", delay=0.04)
        pause(0.4)

        if not self._enraged and self.health <= self.max_health * WIZARD_ENRAGE_THRESHOLD:
            self._enraged      = True
            self.attack_power += WIZARD_ENRAGE_BONUS
            slow_print(
                f"\n  ⚡ {self.name} becomes ENRAGED!"
                f" Attack power → {self.attack_power}!",
                delay=0.05,
            )
            pause(0.4)

        profile = player.resistance_profile
        if profile.dark_bonus_damage > 0:
            if not player.status_effects.get(STATUS_DARK_SUPPRESSED):
                player.status_effects[STATUS_DARK_SUPPRESSED] = True
                player.heal_power = player.heal_power // 2
                slow_print(
                    f"\n  🌑 {self.name} senses the Light within {player.name}"
                    " and unleashes DARK SUPPRESSION! Healing is halved!",
                    delay=0.05,
                )
                pause(0.4)
            player.health -= self._dark_bonus_damage
            slow_print(
                f"  🌑 Dark energy sears {player.name}"
                f" for {self._dark_bonus_damage} bonus damage!"
            )
            if player.health <= 0:
                slow_print(f"  ☠️  {player.name} has been defeated!")
                return

        if not self._void_used and self.health <= self.max_health * WIZARD_VOID_THRESHOLD:
            self._void_used = True
            slow_print(f"\n  🌑 {self.name} channels VOID SURGE!", delay=0.05)
            pause(0.5)
            self._hit_player(player, int(self.attack_power * WIZARD_VOID_MULT))
            return

        if self.health <= self.max_health * WIZARD_SHADOW_THRESHOLD:
            slow_print(f"\n  💜 {self.name} hurls a SHADOW BOLT!", delay=0.05)
            pause(0.3)
            self._hit_player(player, int(self.attack_power * WIZARD_SHADOW_MULT))
        else:
            self.attack(player)


class AncientDragon(Boss):
    """Relentless bruiser with fury cycles, aura damage, and inferno breath."""

    def __init__(self, name: str, difficulty: str = "normal") -> None:
        """Set up AncientDragon stats scaled to the chosen difficulty."""
        if difficulty == "challenging":
            health       = DRAGON_HP_HARD
            attack       = DRAGON_ATK_HARD
            regen        = DRAGON_REGEN_HARD
            aura         = DRAGON_AURA_HARD
            aura_priest  = DRAGON_AURA_PRIEST_HARD
            inferno      = DRAGON_INFERNO_HARD
            inf_priest   = DRAGON_INFERNO_PRIEST_HARD
            tail         = DRAGON_TAIL_HARD
        else:
            health       = DRAGON_HP_NORMAL
            attack       = DRAGON_ATK_NORMAL
            regen        = DRAGON_REGEN_NORMAL
            aura         = DRAGON_AURA_NORMAL
            aura_priest  = DRAGON_AURA_PRIEST_NORMAL
            inferno      = DRAGON_INFERNO_NORMAL
            inf_priest   = DRAGON_INFERNO_PRIEST_NORMAL
            tail         = DRAGON_TAIL_NORMAL
        super().__init__(name, health=health, attack_power=attack, heal_power=0)
        self.difficulty           = difficulty
        self._regen_per_turn      = regen
        self._aura_damage         = aura
        self._priest_aura_damage  = aura_priest
        self._inferno_mult        = inferno
        self._priest_inferno_mult = inf_priest
        self._tail_slam_mult      = tail
        self._enraged             = False
        self._inferno_used        = False
        self._fury                = 0

    def take_turn(self, player: Character) -> None:
        """Tick statuses, regenerate, then execute the dragon's combat pattern."""
        self._tick_statuses()
        if self.health <= 0:
            return

        self.regenerate(emoji="🐉")
        if self.should_skip_turn_from_control():
            return

        slow_print(f"\n  🐉 {self.name}: \"{random.choice(DRAGON_TAUNTS)}\"", delay=0.04)
        pause(0.4)

        if not self._enraged and self.health <= self.max_health * DRAGON_ENRAGE_THRESHOLD:
            self._enraged      = True
            self.attack_power += DRAGON_ENRAGE_BONUS
            slow_print(
                f"\n  🔥 {self.name} enters RAMPAGE!"
                f" Attack power → {self.attack_power}!",
                delay=0.05,
            )
            pause(0.4)

        profile = player.resistance_profile
        aura    = self._priest_aura_damage if profile.holy_aura_reduced \
                  else self._aura_damage
        player.health -= aura
        slow_print(f"  🌋 Scorching aura burns {player.name} for {aura} damage!")
        if player.health <= 0:
            slow_print(f"  ☠️  {player.name} has been defeated!")
            return

        self._fury += 1

        if not self._inferno_used and \
                self.health <= self.max_health * DRAGON_INFERNO_THRESHOLD:
            self._inferno_used = True
            mult = self._priest_inferno_mult if profile.holy_aura_reduced \
                   else self._inferno_mult
            slow_print("\n  🔥 INFERNO BREATH engulfs the battlefield!", delay=0.05)
            pause(0.5)
            self._hit_player(player, int(self.attack_power * mult))
            return

        if self._fury >= DRAGON_FURY_THRESHOLD:
            self._fury = 0
            slow_print("\n  🐲 Tail Slam crashes down with crushing force!", delay=0.05)
            pause(0.3)
            self._hit_player(player, int(self.attack_power * self._tail_slam_mult))
            return

        slow_print("  🐾 The dragon lashes out with twin claw swipes!")
        for _ in range(2):
            if player.health <= 0:
                return
            damage = random.randint(
                int(self.attack_power * DRAGON_CLAW_LOW),
                int(self.attack_power * DRAGON_CLAW_HIGH),
            )
            self._hit_player(player, damage)


# ─────────────────────────────────────────────
#  GAME DATA
# ─────────────────────────────────────────────

# (display_name, hp, atk, role, emoji, class_obj)
HERO_REGISTRY: list[tuple] = [
    ("Warrior",      WARRIOR_HP, WARRIOR_ATK, "Tank & sustain",  "⚔️",  Warrior),
    ("Mage",         MAGE_HP,    MAGE_ATK,    "Glass cannon",    "🔮",  Mage),
    ("Archer",       ARCHER_HP,  ARCHER_ATK,  "Speed & range",   "🏹",  Archer),
    ("Paladin",      PALADIN_HP, PALADIN_ATK, "Holy defender",   "🛡️",  Paladin),
    ("Death Knight", DK_HP,      DK_ATK,      "Dark drainer",    "💀",  DeathKnight),
    ("Holy Priest",  PRIEST_HP,  PRIEST_ATK,  "Light sustain",   "✨",  HolyPriest),
    ("Rogue",        ROGUE_HP,   ROGUE_ATK,   "Assassin burst",  "🗡️",  Rogue),
    ("Druid",        DRUID_HP,   DRUID_ATK,   "Nature shaman",   "🌿",  Druid),
]

BOSS_OPTIONS: dict[str, tuple] = {
    "1": (
        "The Dark Wizard",
        "Regenerating spellcaster with suppression, enrage, and void burst.",
        EvilWizard,
        "🧙",
    ),
    "2": (
        "Ashmaw, Ancient Dragon",
        "Relentless bruiser with fury cycles, aura damage, and inferno breath.",
        AncientDragon,
        "🐉",
    ),
}

GAME_MODES:       dict[str, str] = {"": "single",  "1": "single",  "2": "gauntlet"}
DIFFICULTY_MODES: dict[str, str] = {"": "normal",  "1": "normal",  "2": "challenging"}


# ─────────────────────────────────────────────
#  GAME FUNCTIONS
# ─────────────────────────────────────────────

def choose_game_mode() -> str:
    """Display the game-mode menu and return the player's choice."""
    print("\n" + "═" * 50)
    slow_print("  🧭   CHOOSE GAME MODE   🧭", delay=0.04)
    print("═" * 50)
    print("  1. Single Boss (recommended)")
    print("     Classic run: one hero vs one boss.")
    print("  2. Gauntlet Challenge")
    print("     Defeat one boss, then face the second with partial healing.")
    print("═" * 50)
    while True:
        choice = prompt_input("Choose mode (Enter=1, 1-2): ").strip()
        if choice in GAME_MODES:
            return GAME_MODES[choice]
        print("  ❌ Invalid choice — enter 1 or 2.")


def choose_difficulty() -> str:
    """Display the difficulty menu and return the player's choice."""
    print("\n" + "═" * 50)
    slow_print("  🎚️   CHOOSE DIFFICULTY   🎚️", delay=0.04)
    print("═" * 50)
    print("  1. Normal (recommended)")
    print("     More forgiving boss values and priest-friendly dragon tuning.")
    print("  2. Challenging")
    print("     Harder bosses with higher damage and stronger pressure.")
    print("═" * 50)
    while True:
        choice = prompt_input("Choose difficulty (Enter=1, 1-2): ").strip()
        if choice in DIFFICULTY_MODES:
            return DIFFICULTY_MODES[choice]
        print("  ❌ Invalid choice — enter 1 or 2.")


def create_character() -> Character:
    """Display the hero-selection menu, prompt for a name, and return a new player."""
    print("\n" + "═" * 50)
    slow_print("  ⚔️   CHOOSE YOUR HERO   ⚔️", delay=0.04)
    print("═" * 50)
    for i, (cname, hp, atk, role, emoji, _cls) in enumerate(HERO_REGISTRY, start=1):
        print(f"  {i}. {cname:<13}| HP: {hp:<4}| ATK: {atk:<3}| {role:<16} {emoji}")
    print("═" * 50)

    valid_choices = {str(i) for i in range(1, len(HERO_REGISTRY) + 1)}
    while True:
        choice = prompt_input("Enter the number of your class: ").strip()
        if choice in valid_choices:
            break
        print(f"  ❌ Invalid choice — enter a number between 1 and {len(HERO_REGISTRY)}.")

    _cname, _hp, _atk, _role, _emoji, cls = HERO_REGISTRY[int(choice) - 1]
    name   = prompt_input("Enter your character's name: ").strip() or "Hero"
    player = cls(name)
    pause(0.3)
    intro = CLASS_INTROS.get(cls.__name__, f'  "{name}" steps forward.')
    slow_print("\n  " + intro.replace("{name}", name), delay=0.04)
    pause(0.6)
    return player


def choose_boss(difficulty: str = "normal") -> Boss:
    """Display the boss-selection menu and return a new boss instance."""
    print("\n" + "═" * 50)
    slow_print("  ☠️   CHOOSE YOUR FOE   ☠️", delay=0.04)
    print("═" * 50)
    for key, (name, style, _cls, emoji) in BOSS_OPTIONS.items():
        print(f"  {key}. {name:<24} {emoji}")
        print(f"     {style}")
    print("═" * 50)
    while True:
        choice = prompt_input("Choose your boss (1-2): ").strip()
        if choice in BOSS_OPTIONS:
            break
        print("  ❌ Invalid choice — enter 1 or 2.")
    name, _style, cls, _emoji = BOSS_OPTIONS[choice]
    return cls(name, difficulty=difficulty)


def _remaining_boss_option(current_boss: Boss) -> tuple | None:
    """Return the BOSS_OPTIONS entry for whichever boss was not chosen, or None."""
    for name, style, cls, emoji in BOSS_OPTIONS.values():
        if not isinstance(current_boss, cls):
            return name, style, cls, emoji
    return None


def _between_boss_heal(player: Character) -> None:
    """Restore 35 % of max HP between gauntlet fights and print a respite message."""
    heal_amount   = max(1, int(player.max_health * BETWEEN_BOSS_HEAL_RATIO))
    before        = player.health
    player.health = min(player.health + heal_amount, player.max_health)
    print("\n" + "═" * 50)
    slow_print("  🕊️  Brief respite between battles...", delay=0.04)
    slow_print(
        f"  💚 {player.name} recovers {player.health - before} HP"
        f" ({player.health}/{player.max_health}).",
        delay=0.04,
    )
    print("═" * 50)


def _show_ability_menu(player: Character) -> int:
    """Print the ability list and return the chosen 0-based index, or -1 to cancel."""
    print("\n  ✨ Choose an ability:")
    for i, ab in enumerate(player.abilities, start=1):
        status = f"  ⏳ {ab.cooldown} turn(s)" if not ab.is_ready() else "  ✅ Ready"
        print(f"    {i}. {ab.name}{status} — {ab.desc}")
    print("    0. Cancel")
    raw = prompt_input("  Ability number: ").strip()
    if raw == "0" or not raw.isdigit():
        return -1
    idx = int(raw) - 1
    if idx < 0 or idx >= len(player.abilities):
        print("  ❌ Out of range.")
        return -1
    return idx


def _print_run_summary(
    mode:             str,
    difficulty:       str,
    first_boss:       Boss,
    remaining_option: tuple | None = None,
) -> None:
    """Print a summary of the chosen mode, difficulty, and boss order."""
    mode_label       = "Single Boss"  if mode == "single"      else "Gauntlet Challenge"
    difficulty_label = "Normal"       if difficulty == "normal" else "Challenging"
    print("\n" + "═" * 50)
    slow_print("  🧾   RUN SETTINGS   🧾", delay=0.03)
    print("═" * 50)
    print(f"  Mode      : {mode_label}")
    print(f"  Difficulty: {difficulty_label}")
    print(f"  First Boss: {first_boss.name}")
    if remaining_option is not None:
        print(f"  Next Boss : {remaining_option[0]}")
    print("═" * 50)
    pause(0.4)


def _confirm_or_restart() -> bool:
    """Show a confirm/restart prompt after the run summary; return True to proceed."""
    print("\n  Press Enter to begin, or type 'r' to start over.")
    return prompt_input("  > ").strip().lower() != "r"


def _ask_play_again() -> bool:
    """Ask the player if they want to start a new run; return True if yes."""
    print("\n" + "═" * 50)
    slow_print("  🎮  Play again?", delay=0.04)
    print("═" * 50)
    print("  1. Yes — start a new run")
    print("  2. No  — quit")
    print("═" * 50)
    while True:
        choice = prompt_input("  Choice (Enter=1): ").strip()
        if choice in ("", "1"):
            return True
        if choice == "2":
            return False
        print("  ❌ Enter 1 or 2.")


def battle(player: Character, boss: Boss, final_boss: bool = True) -> bool:
    """Run a single combat loop between player and boss; return True if player wins."""
    pause(0.5)
    boss_emoji = CLASS_EMOJI.get(type(boss).__name__, "👹")
    slow_print(f"\n  {boss_emoji} {boss.name} appears from the shadows...", delay=0.05)
    pause(0.5)
    slow_print("  Prepare for battle! ⚔️", delay=0.05)
    pause(0.8)

    turn = 0
    while boss.health > 0 and player.health > 0:
        turn += 1
        print(f"\n{'═' * 50}")
        slow_print(f"  ⚔️   TURN {turn}   ⚔️", delay=0.03)
        print(f"{'═' * 50}")
        print_hp_bars(player, boss)
        player.start_of_turn()

        print(f"\n  🎮 Your turn, {player.name}:")
        print("  1. ⚔️  Attack")
        print("  2. ✨ Use Special Ability")
        print("  3. 💚 Heal")
        print("  4. 📊 View Stats")

        valid = False
        while not valid:
            choice = prompt_input("\n  Action: ").strip()
            if choice == "1":
                player.attack(boss)
                valid = True
            elif choice == "2":
                idx = _show_ability_menu(player)
                if idx >= 0:
                    player.use_ability(idx, boss)
                    if player.wants_follow_up_after_ability(idx):
                        player.follow_up_action(boss)
                    valid = True
                else:
                    print("  Returning to action menu...")
            elif choice == "3":
                player.heal()
                valid = True
            elif choice == "4":
                print("\n  📊 --- Player ---")
                player.display_stats()
                print("  📊 --- Boss ---")
                boss.display_stats()
            else:
                print("  ❌ Invalid choice — try again.")

        player.tick_cooldowns()
        player.end_of_turn()

        if boss.health > 0:
            pause(0.5)
            print(f"\n{'─' * 50}")
            slow_print(f"  {boss_emoji} {boss.name}'s turn...", delay=0.04)
            print(f"{'─' * 50}")
            pause(0.3)
            boss.take_turn(player)

        if player.health <= 0:
            break

    pause(0.8)
    print(f"\n{'═' * 50}")
    if boss.health <= 0:
        print_victory(player, boss, final_boss=final_boss)
        print(f"{'═' * 50}\n")
        return True
    print_defeat(player, boss)
    print(f"{'═' * 50}\n")
    return False


def _run_once(difficulty: str, mode: str, player: Character, first_boss: Boss) -> None:
    """Execute one full run (single or gauntlet) for the given settings."""
    remaining = _remaining_boss_option(first_boss) if mode == "gauntlet" else None

    _print_run_summary(mode, difficulty, first_boss, remaining_option=remaining)

    if not _confirm_or_restart():
        slow_print("\n  🔄 Starting over...\n", delay=0.03)
        return

    if mode == "single":
        battle(player, first_boss, final_boss=True)
        return

    is_only_boss = remaining is None
    won_first    = battle(player, first_boss, final_boss=is_only_boss)
    if not won_first or is_only_boss:
        return

    _between_boss_heal(player)
    next_name, _style, next_cls, _emoji = remaining
    slow_print(
        f"\n  ⚠️  The gauntlet continues... {next_name} descends upon you!",
        delay=0.04,
    )
    second_boss = next_cls(next_name, difficulty=difficulty)
    battle(player, second_boss, final_boss=True)


def main() -> None:
    """Entry point — parse args, show title, then loop through runs until quit."""
    global DEBUG
    parser = argparse.ArgumentParser(description="Hero vs Boss fantasy battle game.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Skip all delays and slow-print effects for fast testing.",
    )
    DEBUG = parser.parse_args().debug

    print_title()
    pause(0.5)

    while True:
        mode       = choose_game_mode()
        difficulty = choose_difficulty()
        player     = create_character()
        first_boss = choose_boss(difficulty=difficulty)

        _run_once(difficulty, mode, player, first_boss)

        if not _ask_play_again():
            slow_print("\n  👋 Thanks for playing. Farewell, hero! ⚔️\n", delay=0.03)
            break


if __name__ == "__main__":
    main()