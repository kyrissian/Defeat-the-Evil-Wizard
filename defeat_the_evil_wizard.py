"""Run a turn-based hero-vs-boss fantasy battle game."""  # pylint: disable=too-many-lines

import argparse
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable

if os.name == "nt" and sys.flags.utf8_mode != 1 and os.environ.get("WIZARD_UTF8_REEXEC") != "1":
    script_path = os.path.abspath(sys.argv[0])
    cmd = [sys.executable, "-X", "utf8", script_path, *sys.argv[1:]]
    env = os.environ.copy()
    env["WIZARD_UTF8_REEXEC"] = "1"
    reexec = subprocess.run(cmd, check=False, env=env)
    sys.exit(reexec.returncode)

# ─────────────────────────────────────────────
#  DEBUG FLAG  (set once by main() from --debug arg)
# ─────────────────────────────────────────────

DEBUG: bool = False


class BattleResult(Enum):
    """Possible outcomes of a single battle."""
    WIN     = auto()
    LOSS    = auto()
    RESTART = auto()

# ─────────────────────────────────────────────
#  NAMED CONSTANTS
# ─────────────────────────────────────────────

# Combat
ATTACK_ROLL_LOW          = 0.75  # lower bound of normal attack damage roll
ATTACK_ROLL_HIGH         = 1.25  # upper bound of normal attack damage roll
MOONFIRE_DAMAGE          = 7     # damage Moonfire deals to its owner per turn
POISON_DAMAGE            = 9     # damage poison deals at start of target's turn
BLINDED_MISS_CHANCE      = 0.5   # probability of missing while Blinded

# Print delays (seconds per character in slow_print)
DELAY_NORMAL             = 0.018
DELAY_SLOW               = 0.025
DELAY_DRAMATIC           = 0.030
DELAY_FAST               = 0.012

# Warrior
WARRIOR_HP               = 170
WARRIOR_ATK              = 26
WARRIOR_HEAL             = 20
WARRIOR_SHIELD_BASH_MULT = 1.5
WARRIOR_WHIRLWIND_MULT   = 2.0
WARRIOR_BATTLE_CRY_BONUS = 8
WARRIOR_RALLYING_MULT    = 1.2   # damage multiplier for Rallying Strike
WARRIOR_RALLYING_HEAL    = 0.5   # fraction of damage dealt returned as healing

# Mage
MAGE_HP                  = 115
MAGE_ATK                 = 38
MAGE_HEAL                = 15
MAGE_FIREBALL_MULT       = 1.8
MAGE_SURGE_BONUS         = 12
MAGE_SURGE_HEAL          = 35   # HP restored when choosing heal as the surge follow-up
MAGE_MANA_SHIELD_COST    = 30    # HP sacrificed to raise Mana Shield

# Archer
ARCHER_HP                = 130
ARCHER_ATK               = 32
ARCHER_HEAL              = 18
ARCHER_QUICK_SHOT_MULT   = 0.7
ARCHER_SNIPER_MULT       = 1.7
ARCHER_RAIN_MULT         = 0.5   # damage per arrow in Rain of Arrows
ARCHER_RAIN_COUNT        = 3     # number of arrows in Rain of Arrows

# Paladin
PALADIN_HP               = 160
PALADIN_ATK              = 27
PALADIN_HEAL             = 28
PALADIN_HOLY_STRIKE_MULT = 1.5
PALADIN_CONSEC_MULT      = 0.9
PALADIN_CONSEC_HEAL      = 15

# Death Knight
DK_HP                    = 170
DK_ATK                   = 31
DK_HEAL                  = 16
DK_DEATH_COIL_DRAIN      = 18
DK_BLOOD_BOIL_COST       = 18
DK_BLOOD_BOIL_MULT       = 2.1
DK_CORPSE_EXPLOSION_COST = 25    # HP sacrificed for Corpse Explosion
DK_CORPSE_EXPLOSION_MULT = 1.8   # damage multiplier for Corpse Explosion

# Holy Priest
PRIEST_HP                = 180
PRIEST_ATK               = 29
PRIEST_HEAL              = 30
PRIEST_SMITE_MULT        = 1.25
PRIEST_SMITE_BONUS       = 6
PRIEST_PRAYER_HEAL       = 40
PRIEST_HOLY_NOVA_MULT    = 1.1   # damage multiplier for Holy Nova
PRIEST_HOLY_NOVA_HEAL    = 0.5   # fraction of damage returned as healing
PRIEST_RESURRECTION_HP   = 0.5  # fraction of max HP restored on resurrection

# Rogue
ROGUE_HP                 = 130
ROGUE_ATK                = 34
ROGUE_HEAL               = 15
ROGUE_BACKSTAB_MULT      = 2.6
ROGUE_BACKSTAB_CHANCE    = 0.65
# Shadow Step guarantees next backstab hits (no new constant needed)

# Druid
DRUID_HP                 = 140
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
BETWEEN_BOSS_HEAL_RATIO  = 0.50

# UI
HP_BAR_WIDTH             = 24
HP_BAR_NAME_COL          = 16

# ─────────────────────────────────────────────
#  DISPLAY CONSTANTS
# ─────────────────────────────────────────────

WIZARD_TAUNTS = [
    "You dare challenge ME?! 😈",
    "Your suffering amuses me... 🌑",
    "The darkness will consume you! 🌑",
    "Tremble before my power! 💜",
    "You cannot win... give up now! 😈",
    "Pathetic mortal. 🖤",
    "I have destroyed armies. You are nothing. 💀",
    "Every spell you cast only delays the inevitable! ⚡",
    "The realm will bow to me... one grave at a time. 🌑",
]

WIZARD_ENRAGE_TAUNTS = [
    "You've made me angry. BIG mistake. 😡",
    "ENOUGH! Feel my true wrath! 🔥",
    "Now you die in earnest! ⚡",
]

DRAGON_TAUNTS = [
    "You enter my lair and expect mercy? 🐲",
    "I have burned kingdoms to ash. 🔥",
    "Feel the heat of the abyss! 🌋",
    "Your bones will line my nest. 🦴",
    "I have slept for a thousand years. Your death wakes me gently. 🐉",
    "Puny creature. I exhale harder than you fight. 💨",
    "Run. It makes the hunt more interesting. 👁️",
]

DRAGON_ENRAGE_TAUNTS = [
    "NOW you have angered me! 🔥",
    "RAMPAGE! 🐉🔥",
    "You drew BLOOD?! Unforgivable! 😡",
]

TOMBSTONE = [
    ".------------.",
    "|            |",
    "|   R. I. P  |",
    "|            |",
    "|{name:^12}|",
    "|            |",
    "__|____________|__",
    "|                |",
    "__|______________|__",
]

TROPHY = [
    "   .-=========-.",
    "   ||  VICTOR  ||",
    "   ||  {name:^7}  ||",
    "   '-=========-'",
    "       \\ | /  ",
    "        \\|/   ",
    "    .----+----.",
    "    |  \\   /  |",
    "    '--.   .--'",
    "        | |   ",
    "      .-+-+-.  ",
    "      |_____|  ",
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


@dataclass
class _DragonScaling:
    """Groups the difficulty-dependent scaling values for AncientDragon."""

    aura_damage:         int
    aura_damage_priest:  int
    inferno_mult:        float
    inferno_mult_priest: float
    tail_mult:           float
# ─────────────────────────────────────────────
#  IO HELPERS
# ─────────────────────────────────────────────


def prompt_input(prompt: str = "") -> str:
    """Read a line from stdin; exit gracefully on EOF or keyboard interrupt."""
    try:
        return input(prompt)
    except EOFError:
        print("\n  ❌ No interactive input is available.")
        print("  Run this game in an interactive terminal (PowerShell/VS Code Terminal).")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  👋 Game interrupted.")
        sys.exit(0)


def slow_print(text: str, delay: float = DELAY_NORMAL) -> None:
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
    slow_print("", delay=DELAY_NORMAL)
    slow_print("    ██████╗ ███████╗███████╗███████╗ █████╗ ████████╗", delay=0.001)
    slow_print("    ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗╚══██╔══╝", delay=0.001)
    slow_print("    ██║  ██║█████╗  █████╗  █████╗  ███████║   ██║   ", delay=0.001)
    slow_print("    ██║  ██║██╔══╝  ██╔══╝  ██╔══╝  ██╔══██║   ██║   ", delay=0.001)
    slow_print("    ██████╔╝███████╗██║     ███████╗██║  ██║   ██║   ", delay=0.001)
    slow_print("    ╚═════╝ ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ", delay=0.001)
    slow_print("", delay=DELAY_NORMAL)
    slow_print("        ⚔️  THE EVIL WIZARD  ⚔️", delay=DELAY_SLOW)
    slow_print("   Defeat the Dark Wizard before he destroys the realm.", delay=DELAY_NORMAL)
    print("═" * 50)
    pause(0.6)


def print_victory(player: "Character", boss: "Character", final_boss: bool = True) -> None:
    """Print the victory screen after defeating a boss."""
    print("\n" + "═" * 50)
    if final_boss:
        for line in TROPHY:
            slow_print("  " + line.format(name=player.name[:12]), delay=DELAY_FAST)
            pause(0.05)
        pause(0.3)
        slow_print(f"\n  🏆  {player.name} has defeated {boss.name}!", delay=DELAY_DRAMATIC)
        slow_print("  The darkness recedes. Light returns to the realm. ✨", delay=DELAY_SLOW)
    else:
        slow_print(f"  🏆  {player.name} has defeated {boss.name}!")
        slow_print("  A new threat stirs... this war is not over yet. ⚔️")
    print("═" * 50)


def print_defeat(player: "Character", boss: "Character") -> None:
    """Print the defeat screen with a tombstone and GAME OVER banner."""
    print("\n" + "═" * 50)
    for line in TOMBSTONE:
        slow_print("  " + line.format(name=player.name[:12]), delay=DELAY_FAST)
        pause(0.05)
    pause(0.3)
    slow_print("\n  * * * G A M E   O V E R * * *")
    slow_print(f"  {boss.name} cackles in triumph... the realm is lost. 🌑")
    print("═" * 50)
# ─────────────────────────────────────────────
#  BASE CHARACTER
# ─────────────────────────────────────────────


class Character:  # pylint: disable=too-many-instance-attributes
    """Shared stats, combat methods, and status-effect logic for all characters."""

    emoji:    str = "❓"   # overridden in each subclass
    intro:    str = '"{name}" steps forward.'  # overridden in each hero subclass
    base_hp:  int = 0     # overridden in each hero subclass (used for display only)
    base_atk: int = 0     # overridden in each hero subclass (used for display only)

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
        self.abilities:      list[Ability] = []
        self.status_effects: set[str]      = set()
        self._used_once:     set[str]      = set()
        # Battle stat trackers (reset each fresh instance)
        self.total_damage_dealt:  int = 0
        self.total_damage_taken:  int = 0
        self.total_healed:        int = 0

    @property
    def resistance_profile(self) -> ResistanceProfile:
        """Return this character's resistance profile for boss interaction.

        Override in hero subclasses that have special boss interactions.
        The default profile has no special resistances or vulnerabilities.
        """
        return ResistanceProfile()

    def attack(self, opponent: "Character") -> None:
        """Deal randomised physical damage; respect Moonfire, Evade, and Shield."""
        if STATUS_MOONFIRE in self.status_effects:
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
        self.total_damage_dealt  += damage
        opponent.total_damage_taken += damage
        slow_print(f"  ⚔️  {self.name} attacks {opponent.name} for {damage} damage!")
        if opponent.health <= 0:
            slow_print(f"  💥 {opponent.name} has been defeated!")

    def heal(self) -> None:
        """Restore HP up to max using this character's heal_power."""
        before = self.health
        self.health = min(self.health + self.heal_power, self.max_health)
        healed = self.health - before
        self.total_healed += healed
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
        slow_print(f"\n  ✨ {self.name} uses {ab.name}!", delay=DELAY_DRAMATIC)
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
        if STATUS_EVADE in self.status_effects:
            slow_print(f"  💨 {self.name} evades {attacker_name}'s attack!")
            self.status_effects.discard(STATUS_EVADE)
            return True
        if STATUS_SHIELD in self.status_effects:
            slow_print(f"  🛡️  {self.name}'s shield absorbs the attack!")
            self.status_effects.discard(STATUS_SHIELD)
            return True
        return False

    def reset(self) -> "Character":
        """Return a fresh instance of the same class with the same name."""
        return type(self)(self.name)  # pylint: disable=no-value-for-parameter,missing-kwoa

    def try_resurrect(self) -> bool:
        """Return True and restore HP if a resurrection is pending; False otherwise."""
        return False

    def should_skip_turn_from_control(self) -> bool:
        """Return True and print a message if Frozen or Blinded causes a lost turn."""
        if STATUS_FROZEN in self.status_effects:
            self.status_effects.discard(STATUS_FROZEN)
            slow_print(f"  ❄️  {self.name} is frozen and cannot act this turn!")
            return True
        if STATUS_BLINDED in self.status_effects:
            self.status_effects.discard(STATUS_BLINDED)
            if random.random() < BLINDED_MISS_CHANCE:
                slow_print(f"  😵 {self.name} is blinded and stumbles — misses!")
                return True
        return False

    def display_stats(self) -> None:
        """Print a detailed stat block including HP bar and active status effects."""
        bar_len = 20
        filled  = int(bar_len * max(self.health, 0) / self.max_health)
        hp_bar  = "█" * filled + "░" * (bar_len - filled)
        print(
            f"\n  {self.emoji} {self.name} | [{hp_bar}] {self.health}/{self.max_health} HP"
            f" | ⚔️  ATK {self.attack_power}"
        )
        active = [
            STATUS_LABELS.get(k, k.replace("_", " ").title())
            for k in self.status_effects
        ]
        if active:
            print(f"     🔮 Active effects: {', '.join(active)}")

    def _deal_damage(self, opponent: "Character", damage: int) -> None:
        """Apply a fixed damage value to opponent and report remaining HP."""
        opponent.health -= damage
        self.total_damage_dealt += damage
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

    emoji   = "⚔️"
    base_hp = WARRIOR_HP
    base_atk = WARRIOR_ATK
    intro = "🗡️  '{name}' cracks knuckles. 'Let's make this quick.'"

    def __init__(self, name: str) -> None:
        """Set up Warrior stats and abilities."""
        super().__init__(
            name,
            health=WARRIOR_HP,
            attack_power=WARRIOR_ATK,
            heal_power=WARRIOR_HEAL,
        )
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
            Ability(
                "💢 Rallying Strike",
                "Strike for 1.2× damage and heal yourself for half the damage dealt.",
                self._rallying_strike, max_cooldown=2,
            ),
        ]

    def _shield_bash(self, opponent: Character) -> None:
        """Raise a shield then deal 1.5× damage; shield is guaranteed regardless of outcome."""
        self.status_effects.add(STATUS_SHIELD)
        slow_print(f"  🛡️  {self.name} raises shield — next attack will be blocked!")
        self._deal_damage(opponent, int(self.attack_power * WARRIOR_SHIELD_BASH_MULT))

    def _whirlwind(self, opponent: Character) -> None:
        """Spin and deal 2× damage to the opponent."""
        self._deal_damage(opponent, int(self.attack_power * WARRIOR_WHIRLWIND_MULT))

    def _battle_cry(self, _opponent: Character) -> None:
        """Permanently raise attack power by 8; usable only once per battle."""
        if "battle_cry" in self._used_once:
            slow_print("  ❌ Battle Cry can only be used once per battle!")
            return
        self.attack_power += WARRIOR_BATTLE_CRY_BONUS
        self._used_once.add("battle_cry")
        slow_print(f"  📣 {self.name} roars! Attack power raised to {self.attack_power}.")

    def _rallying_strike(self, opponent: Character) -> None:
        """Deal 1.2× damage and heal self for half the damage dealt."""
        damage = int(self.attack_power * WARRIOR_RALLYING_MULT)
        self._deal_damage(opponent, damage)
        healed = int(damage * WARRIOR_RALLYING_HEAL)
        self.health = min(self.health + healed, self.max_health)
        slow_print(
            f"  💢 {self.name} rallies! Healed {healed} HP."
            f" ({self.health}/{self.max_health})"
        )


class Mage(Character):
    """Glass cannon with a surge mechanic for double-action turns."""

    emoji   = "🔮"
    base_hp = MAGE_HP
    base_atk = MAGE_ATK
    intro = "🔮  '{name}' crackles with arcane energy."

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
                "Boost ATK by 12, then follow-up: attack, fireball, or arcane recovery.",
                self._arcane_surge, max_cooldown=3,
            ),
            Ability(
                "🔵 Mana Shield",
                f"Sacrifice {MAGE_MANA_SHIELD_COST} HP to block the next attack and evade.",
                self._mana_shield, max_cooldown=3,
            ),
        ]

    def _fireball(self, opponent: Character) -> None:
        """Hurl a fireball dealing 1.8× attack damage."""
        self._deal_damage(opponent, int(self.attack_power * MAGE_FIREBALL_MULT))

    def _frost_nova(self, opponent: Character) -> None:
        """Freeze the opponent so they skip their next turn."""
        opponent.status_effects.add(STATUS_FROZEN)
        slow_print(f"  ❄️  {opponent.name} is frozen and will skip their next turn!")

    def _arcane_surge(self, _opponent: Character) -> None:
        """Temporarily boost attack power and enable a follow-up action."""
        self.attack_power  += MAGE_SURGE_BONUS
        self._surge_active  = True
        slow_print(
            f"  ⚡ Arcane Surge! Attack power surges to {self.attack_power}.\n"
            f"  💡 Choose your follow-up: boosted attack, fireball, or arcane recovery.\n"
            f"  ⚠️  The ATK bonus expires at the end of your turn."
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
        """Prompt the player to choose a surge-powered follow-up action."""
        fireball_ready = self.abilities[0].is_ready()
        slow_print("\n  ⚡ Surge follow-up — choose your action:")
        print("  1. ⚔️  Attack (surge-boosted)")
        if fireball_ready:
            print("  2. 🔥 Fireball (surge-boosted)")
        print("  3. 💊 Arcane Recovery (restore"
              f" {MAGE_SURGE_HEAL} HP from the surge energy)")
        while True:
            choice = prompt_input("\n  Follow-up: ").strip()
            if choice == "1":
                self.attack(opponent)
                return
            if choice == "2" and fireball_ready:
                slow_print(f"\n  ✨ {self.name} uses 🔥 Fireball!", delay=DELAY_DRAMATIC)
                pause(0.3)
                self.abilities[0].trigger(opponent)
                return
            if choice == "3":
                before = self.health
                self.health = min(self.health + MAGE_SURGE_HEAL, self.max_health)
                slow_print(
                    f"  💊 Arcane Recovery! {self.name} absorbs surge energy"
                    f" and restores {self.health - before} HP."
                    f" ({self.health}/{self.max_health})"
                )
                return
            print("  ❌ Invalid choice — try again.")

    def _mana_shield(self, _opponent: Character) -> None:
        """Sacrifice HP to raise both a shield and an evade."""
        if self.health <= MAGE_MANA_SHIELD_COST:
            slow_print("  ❌ Not enough HP to conjure a Mana Shield!")
            return
        self.health -= MAGE_MANA_SHIELD_COST
        self.status_effects.add(STATUS_SHIELD)
        self.status_effects.add(STATUS_EVADE)
        slow_print(
            f"  🔵 Mana Shield flares! Sacrificed {MAGE_MANA_SHIELD_COST} HP."
            f" Next attack blocked AND evaded. HP: {self.health}/{self.max_health}"
        )


class Archer(Character):
    """Speed and range specialist with a guaranteed-dodge utility."""

    emoji   = "🏹"
    base_hp = ARCHER_HP
    base_atk = ARCHER_ATK
    intro = "🏹  '{name}' notches an arrow. 'I never miss.'"

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
            Ability(
                "🌧️ Rain of Arrows",
                f"Loose {ARCHER_RAIN_COUNT} arrows at 0.5× damage each.",
                self._rain_of_arrows, max_cooldown=3,
            ),
        ]

    def _quick_shot(self, opponent: Character) -> None:
        """Fire two arrows, each dealing 0.7× damage."""
        for i in range(1, 3):
            slow_print(f"  🏹 Arrow {i}:", delay=DELAY_FAST)
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
        self.status_effects.add(STATUS_EVADE)
        slow_print(f"  💨 {self.name} readies a dodge — next attack will miss!")

    def _rain_of_arrows(self, opponent: Character) -> None:
        """Fire a volley of arrows, each dealing 0.5× damage."""
        slow_print(f"  🌧️ {self.name} looses a volley of arrows!")
        for i in range(1, ARCHER_RAIN_COUNT + 1):
            if opponent.health <= 0:
                return
            slow_print(f"  🏹 Arrow {i}:", delay=DELAY_FAST)
            self._deal_damage(opponent, int(self.attack_power * ARCHER_RAIN_MULT))


class Paladin(Character):
    """Holy defender with strong heals and a damage-absorbing shield."""

    emoji   = "🛡️"
    base_hp = PALADIN_HP
    base_atk = PALADIN_ATK
    intro = "🛡️  '{name}' raises their shield."

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
            Ability(
                "🤲 Lay on Hands",
                "One-time miracle: fully restore your HP.",
                self._lay_on_hands, max_cooldown=0,
            ),
        ]

    def _holy_strike(self, opponent: Character) -> None:
        """Strike with holy power for 1.5× damage."""
        self._deal_damage(opponent, int(self.attack_power * PALADIN_HOLY_STRIKE_MULT))

    def _divine_shield(self, _opponent: Character) -> None:
        """Raise a divine shield that absorbs the next incoming attack."""
        self.status_effects.add(STATUS_SHIELD)
        slow_print(f"  🛡️  {self.name} is shielded — the next attack will be absorbed!")

    def _consecration(self, opponent: Character) -> None:
        """Deal 0.9× damage and heal self for 15 HP."""
        self._deal_damage(opponent, int(self.attack_power * PALADIN_CONSEC_MULT))
        self.health = min(self.health + PALADIN_CONSEC_HEAL, self.max_health)
        slow_print(
            f"  🔥 Holy ground heals {self.name} for {PALADIN_CONSEC_HEAL}."
            f" HP: {self.health}/{self.max_health}"
        )

    def _lay_on_hands(self, _opponent: Character) -> None:
        """Fully restore HP; usable only once per battle."""
        if "lay_on_hands" in self._used_once:
            slow_print("  ❌ Lay on Hands can only be used once per battle!")
            return
        self._used_once.add("lay_on_hands")
        self.health = self.max_health
        slow_print(
            f"  🤲 Divine light surges through {self.name}! HP fully restored."
            f" ({self.health}/{self.max_health})"
        )


class DeathKnight(Character):
    """Dark drainer who trades and steals HP to stay alive."""

    emoji   = "💀"
    base_hp = DK_HP
    base_atk = DK_ATK
    intro = "💀  '{name}' rises from shadow."

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
                "💀 Army of the Dead",
                "One-time summon: raise undead to shield AND evade the next attack.",
                self._army_of_the_dead, max_cooldown=0,
            ),
            Ability(
                "💥 Corpse Explosion",
                f"Sacrifice {DK_CORPSE_EXPLOSION_COST} HP to deal 1.8× damage, poison AND blind.",
                self._corpse_explosion, max_cooldown=4,
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

    def _army_of_the_dead(self, _opponent: Character) -> None:
        """One-time summon: grant shield and evade simultaneously."""
        if "army_of_the_dead" in self._used_once:
            slow_print("  ❌ The dead have already answered your call — once per battle only!")
            return
        self._used_once.add("army_of_the_dead")
        self.status_effects.add(STATUS_SHIELD)
        self.status_effects.add(STATUS_EVADE)
        slow_print(
            f"  💀 {self.name} raises the dead! Undead warriors surround you —"
            " the next attack will be both blocked AND evaded!"
        )

    def _corpse_explosion(self, opponent: Character) -> None:
        """Sacrifice HP to deal damage and apply poison and blind."""
        if self.health <= DK_CORPSE_EXPLOSION_COST:
            slow_print("  ❌ Not enough HP to fuel Corpse Explosion!")
            return
        self.health -= DK_CORPSE_EXPLOSION_COST
        slow_print(
            f"  💥 Corpse Explosion! {self.name} sacrifices {DK_CORPSE_EXPLOSION_COST} HP..."
            f" HP: {self.health}/{self.max_health}"
        )
        self._deal_damage(opponent, int(self.attack_power * DK_CORPSE_EXPLOSION_MULT))
        opponent.status_effects.add(STATUS_POISONED)
        opponent.status_effects.add(STATUS_BLINDED)
        slow_print(f"  ☠️  {opponent.name} is poisoned and blinded!")


class HolyPriest(Character):
    """Light-sustain healer who weakens opponents over time."""

    emoji   = "✨"
    base_hp = PRIEST_HP
    base_atk = PRIEST_ATK
    intro = "✨  '{name}' glows with divine radiance."

    def __init__(self, name: str) -> None:
        """Set up HolyPriest stats and abilities."""
        super().__init__(
            name,
            health=PRIEST_HP,
            attack_power=PRIEST_ATK,
            heal_power=PRIEST_HEAL,
        )
        self._resurrection_triggered = False
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
                "💫 Holy Nova",
                "Burst of holy light: deal 1.1× damage and heal for half of it.",
                self._holy_nova, max_cooldown=2,
            ),
            Ability(
                "✝️  Resurrection",
                "One-time miracle: if you would die, survive at 50% HP instead.",
                self._resurrection, max_cooldown=0,
            ),
        ]

    @property
    def resistance_profile(self) -> ResistanceProfile:
        """HolyPriest has reduced dragon aura and triggers wizard Dark Suppression."""
        return ResistanceProfile(
            holy_aura_reduced=True,
            dark_suppressed=STATUS_DARK_SUPPRESSED in self.status_effects,
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

    def _holy_nova(self, opponent: Character) -> None:
        """Deal 1.1× damage and heal self for half the damage dealt."""
        damage = int(self.attack_power * PRIEST_HOLY_NOVA_MULT)
        self._deal_damage(opponent, damage)
        healed = int(damage * PRIEST_HOLY_NOVA_HEAL)
        self.health = min(self.health + healed, self.max_health)
        slow_print(
            f"  💫 Holy light radiates! {self.name} healed {healed} HP."
            f" HP: {self.health}/{self.max_health}"
        )

    def _resurrection(self, _opponent: Character) -> None:
        """Arm the one-time resurrection safety net."""
        if "resurrection" in self._used_once:
            slow_print("  ❌ Resurrection can only be used once per battle!")
            return
        self._resurrection_triggered = True
        slow_print(
            f"  ✝️  {self.name} invokes Resurrection! If slain, will rise at"
            f" {int(PRIEST_RESURRECTION_HP * 100)} % HP."
        )

    def try_resurrect(self) -> bool:
        """Trigger resurrection if armed and HP has dropped to zero."""
        if self._resurrection_triggered and self.health <= 0:
            self._used_once.add("resurrection")
            self._resurrection_triggered = False
            self.health = int(self.max_health * PRIEST_RESURRECTION_HP)
            slow_print(
                f"\n  ✝️  {self.name} rises from the brink of death!"
                f" HP restored to {self.health}/{self.max_health}!",
                delay=DELAY_DRAMATIC,
            )
            return True
        return False

    def start_of_turn(self) -> None:
        """Nothing to tick at start of turn for HolyPriest."""


class Rogue(Character):
    """Assassin with high-risk burst, poison, and smoke utility."""

    emoji   = "🗡️"
    base_hp = ROGUE_HP
    base_atk = ROGUE_ATK
    intro = "🗡️  '{name}' melts from the shadows."

    def __init__(self, name: str) -> None:
        """Set up Rogue stats and abilities."""
        super().__init__(
            name,
            health=ROGUE_HP,
            attack_power=ROGUE_ATK,
            heal_power=ROGUE_HEAL,
        )
        self._shadow_step_active = False
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
            Ability(
                "🌑 Shadow Step",
                "Guarantee your next Backstab hits — no miss chance.",
                self._shadow_step, max_cooldown=3,
            ),
        ]

    def _backstab(self, opponent: Character) -> None:
        """Deal high damage; guaranteed hit if Shadow Step is active."""
        if self._shadow_step_active or random.random() < ROGUE_BACKSTAB_CHANCE:
            if self._shadow_step_active:
                slow_print("  🌑 Shadow Step ensures the hit!", delay=DELAY_DRAMATIC)
                self._shadow_step_active = False
            slow_print("  🗡️  Critical backstab!", delay=DELAY_DRAMATIC)
            pause(0.3)
            self._deal_damage(opponent, int(self.attack_power * ROGUE_BACKSTAB_MULT))
        else:
            slow_print(f"  ❌ {self.name} missed! The opponent sidesteps.")

    def _smoke_bomb(self, opponent: Character) -> None:
        """Grant self Evade and apply Blinded to the opponent."""
        self.status_effects.add(STATUS_EVADE)
        opponent.status_effects.add(STATUS_BLINDED)
        slow_print(
            f"  💨 Smoke fills the air! {self.name} will evade the next attack."
            f" {opponent.name} is blinded ({int(BLINDED_MISS_CHANCE * 100)} % miss"
            " next turn)."
        )

    def _poison_blade(self, opponent: Character) -> None:
        """Apply Poisoned to the opponent; deals damage at start of their next turn."""
        opponent.status_effects.add(STATUS_POISONED)
        slow_print(
            f"  ☠️  {opponent.name} is poisoned!"
            f" Takes {POISON_DAMAGE} damage at the start of the next boss action."
        )

    def _shadow_step(self, _opponent: Character) -> None:
        """Guarantee the next Backstab hits."""
        self._shadow_step_active = True
        slow_print(
            f"  🌑 {self.name} vanishes into shadow"
            " — next Backstab is guaranteed to hit!"
        )


class Druid(Character):
    """Nature shaman with a delayed heal-over-time and a bear form."""

    emoji   = "🌿"
    base_hp = DRUID_HP
    base_atk = DRUID_ATK
    intro = "🌿  '{name}' communes with nature."

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
            Ability(
                "🌱 Entangle",
                "Root the opponent (frozen next turn) and apply Moonfire DoT.",
                self._entangle, max_cooldown=4,
            ),
        ]

    def _wrath(self, opponent: Character) -> None:
        """Call nature's fury for 1.5× damage."""
        self._deal_damage(opponent, int(self.attack_power * DRUID_WRATH_MULT))

    def _bear_form(self, _opponent: Character) -> None:
        """Gain temporary HP and shield the next incoming attack."""
        self.health = min(self.health + DRUID_BEAR_HP_BONUS, self.max_health + DRUID_BEAR_HP_BONUS)
        self.status_effects.add(STATUS_SHIELD)
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

    def _entangle(self, opponent: Character) -> None:
        """Freeze the opponent and apply Moonfire damage-over-time."""
        opponent.status_effects.add(STATUS_FROZEN)
        opponent.status_effects.add(STATUS_MOONFIRE)
        slow_print(
            f"  🌱 Roots burst from the ground! {opponent.name} is entangled and frozen."
            f" Moonfire will burn them each turn!"
        )
# ─────────────────────────────────────────────
#  BASE BOSS
# ─────────────────────────────────────────────


class Boss(Character):
    """Shared logic for all boss types: regen, poison tick, and direct hit."""

    _regen_per_turn: int = 0

    def reset(self) -> "Boss":
        """Return a fresh boss instance preserving name and difficulty."""
        difficulty = getattr(self, "difficulty", "normal")
        return type(self)(  # pylint: disable=no-value-for-parameter,missing-kwoa,unexpected-keyword-arg
            self.name, difficulty=difficulty
        )

    def regenerate(self, emoji: str = "💜") -> None:
        """Restore a fixed amount of HP at the start of each boss turn."""
        self.health = min(self.health + self._regen_per_turn, self.max_health)
        slow_print(
            f"  {emoji} {self.name} regenerates {self._regen_per_turn} HP."
            f" HP: {self.health}/{self.max_health}"
        )

    def _tick_statuses(self) -> None:
        """Resolve any active status effects on this boss before it acts."""
        if STATUS_POISONED in self.status_effects:
            self.health -= POISON_DAMAGE
            slow_print(
                f"  ☠️  Poison deals {POISON_DAMAGE} damage to {self.name}!"
                f" HP: {self.health}/{self.max_health}"
            )
            self.status_effects.discard(STATUS_POISONED)

    def _hit_player(self, player: Character, damage: int) -> None:
        """Apply damage directly to the player, bypassing the standard attack roll."""
        if player.try_negate_incoming_attack(self.name):
            return
        player.health -= damage
        player.total_damage_taken += damage
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

    emoji = "🧙"

    _STATS: dict = {
        "normal": (
            WIZARD_HP_NORMAL, WIZARD_ATK_NORMAL,
            WIZARD_REGEN_NORMAL, WIZARD_DARK_DMG_NORMAL,
        ),
        "challenging": (
            WIZARD_HP_HARD, WIZARD_ATK_HARD,
            WIZARD_REGEN_HARD, WIZARD_DARK_DMG_HARD,
        ),
    }

    def __init__(self, name: str, difficulty: str = "normal") -> None:
        """Set up EvilWizard stats scaled to the chosen difficulty."""
        health, attack, regen, dark_dmg = self._STATS.get(
            difficulty, self._STATS["normal"]
        )
        super().__init__(name, health=health, attack_power=attack, heal_power=5)
        self.difficulty         = difficulty
        self._regen_per_turn    = regen
        self._dark_bonus_damage = dark_dmg
        self._enraged           = False

    def take_turn(self, player: Character) -> None:
        """Regenerate, tick statuses, then execute the wizard's combat action."""
        self.regenerate(emoji="🧙")
        self._tick_statuses()

        if self.should_skip_turn_from_control():
            return

        slow_print(f"\n  🧙 {self.name}: \"{random.choice(WIZARD_TAUNTS)}\"", delay=DELAY_SLOW)
        pause(0.4)

        if not self._enraged and self.health <= self.max_health * WIZARD_ENRAGE_THRESHOLD:
            self._enraged      = True
            self.attack_power += WIZARD_ENRAGE_BONUS
            slow_print(
                f"\n  ⚡ {self.name}: \"{random.choice(WIZARD_ENRAGE_TAUNTS)}\"",
                delay=DELAY_DRAMATIC,
            )
            slow_print(
                f"  ⚡ {self.name} becomes ENRAGED!"
                f" Attack power → {self.attack_power}!",
                delay=DELAY_DRAMATIC,
            )
            pause(0.4)

        profile = player.resistance_profile
        if profile.dark_bonus_damage > 0:
            if STATUS_DARK_SUPPRESSED not in player.status_effects:
                player.status_effects.add(STATUS_DARK_SUPPRESSED)
                player.heal_power = player.heal_power // 2
                slow_print(
                    f"\n  🌑 {self.name} senses the Light within {player.name}"
                    " and unleashes DARK SUPPRESSION! Healing is halved!",
                    delay=DELAY_DRAMATIC,
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

        if "void_surge" not in self._used_once and \
                self.health <= self.max_health * WIZARD_VOID_THRESHOLD:
            self._used_once.add("void_surge")
            slow_print(f"\n  🌑 {self.name} channels VOID SURGE!", delay=DELAY_DRAMATIC)
            pause(0.5)
            self._hit_player(player, int(self.attack_power * WIZARD_VOID_MULT))
            return

        if self.health <= self.max_health * WIZARD_SHADOW_THRESHOLD:
            slow_print(f"\n  💜 {self.name} hurls a SHADOW BOLT!", delay=DELAY_DRAMATIC)
            pause(0.3)
            self._hit_player(player, int(self.attack_power * WIZARD_SHADOW_MULT))
        else:
            self.attack(player)


class AncientDragon(Boss):
    """Relentless bruiser with fury cycles, aura damage, and inferno breath."""

    emoji = "🐉"

    _STATS: dict = {
        "normal": (
            DRAGON_HP_NORMAL, DRAGON_ATK_NORMAL, DRAGON_REGEN_NORMAL,
            _DragonScaling(
                aura_damage=DRAGON_AURA_NORMAL,
                aura_damage_priest=DRAGON_AURA_PRIEST_NORMAL,
                inferno_mult=DRAGON_INFERNO_NORMAL,
                inferno_mult_priest=DRAGON_INFERNO_PRIEST_NORMAL,
                tail_mult=DRAGON_TAIL_NORMAL,
            ),
        ),
        "challenging": (
            DRAGON_HP_HARD, DRAGON_ATK_HARD, DRAGON_REGEN_HARD,
            _DragonScaling(
                aura_damage=DRAGON_AURA_HARD,
                aura_damage_priest=DRAGON_AURA_PRIEST_HARD,
                inferno_mult=DRAGON_INFERNO_HARD,
                inferno_mult_priest=DRAGON_INFERNO_PRIEST_HARD,
                tail_mult=DRAGON_TAIL_HARD,
            ),
        ),
    }

    def __init__(self, name: str, difficulty: str = "normal") -> None:
        """Set up AncientDragon stats scaled to the chosen difficulty."""
        health, attack, regen, scaling = self._STATS.get(
            difficulty, self._STATS["normal"]
        )
        super().__init__(name, health=health, attack_power=attack, heal_power=0)
        self.difficulty      = difficulty
        self._regen_per_turn = regen
        self._scaling        = scaling
        self._enraged        = False
        self._fury           = 0

    def take_turn(self, player: Character) -> None:
        """Tick statuses, regenerate, then execute the dragon's combat pattern."""
        self._tick_statuses()
        if self.health <= 0:
            return

        self.regenerate(emoji="🐉")
        if self.should_skip_turn_from_control():
            return

        slow_print(f"\n  🐉 {self.name}: \"{random.choice(DRAGON_TAUNTS)}\"", delay=DELAY_SLOW)
        pause(0.4)

        if not self._enraged and self.health <= self.max_health * DRAGON_ENRAGE_THRESHOLD:
            self._enraged      = True
            self.attack_power += DRAGON_ENRAGE_BONUS
            slow_print(
                f"\n  🔥 {self.name}: \"{random.choice(DRAGON_ENRAGE_TAUNTS)}\"",
                delay=DELAY_DRAMATIC,
            )
            slow_print(
                f"  🔥 {self.name} enters RAMPAGE!"
                f" Attack power → {self.attack_power}!",
                delay=DELAY_DRAMATIC,
            )
            pause(0.4)

        profile = player.resistance_profile
        aura    = self._scaling.aura_damage_priest if profile.holy_aura_reduced \
                  else self._scaling.aura_damage
        player.health -= aura
        slow_print(f"  🌋 Scorching aura burns {player.name} for {aura} damage!")
        if player.health <= 0:
            slow_print(f"  ☠️  {player.name} has been defeated!")
            return

        self._fury += 1

        if "inferno" not in self._used_once and \
                self.health <= self.max_health * DRAGON_INFERNO_THRESHOLD:
            self._used_once.add("inferno")
            mult = self._scaling.inferno_mult_priest if profile.holy_aura_reduced \
                   else self._scaling.inferno_mult
            slow_print("\n  🔥 INFERNO BREATH engulfs the battlefield!", delay=DELAY_DRAMATIC)
            pause(0.5)
            self._hit_player(player, int(self.attack_power * mult))
            return

        if self._fury >= DRAGON_FURY_THRESHOLD:
            self._fury = 0
            slow_print("\n  🐲 Tail Slam crashes down with crushing force!", delay=DELAY_DRAMATIC)
            pause(0.3)
            self._hit_player(player, int(self.attack_power * self._scaling.tail_mult))
            return

        slow_print("  🐾 The dragon lashes out with a claw swipe!")
        if player.health > 0:
            damage = random.randint(
                int(self.attack_power * DRAGON_CLAW_LOW),
                int(self.attack_power * DRAGON_CLAW_HIGH),
            )
            self._hit_player(player, damage)
# ─────────────────────────────────────────────
#  GAME DATA
# ─────────────────────────────────────────────

# (display_name, role, class_obj) — HP, ATK and emoji are read from the class directly
HERO_REGISTRY: list[tuple[str, str, type[Character]]] = [
    ("Warrior",      "Tank & sustain",  Warrior),
    ("Mage",         "Glass cannon",    Mage),
    ("Archer",       "Speed & range",   Archer),
    ("Paladin",      "Holy defender",   Paladin),
    ("Death Knight", "Dark drainer",    DeathKnight),
    ("Holy Priest",  "Light sustain",   HolyPriest),
    ("Rogue",        "Assassin burst",  Rogue),
    ("Druid",        "Nature shaman",   Druid),
]

BOSS_OPTIONS: dict[str, tuple[str, str, type[Boss]]] = {
    "1": (
        "The Dark Wizard",
        "Regenerating spellcaster with suppression, enrage, and void burst.",
        EvilWizard,
    ),
    "2": (
        "Ashmaw, Ancient Dragon",
        "Relentless bruiser with fury cycles, aura damage, and inferno breath.",
        AncientDragon,
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
    slow_print("  🧭   CHOOSE GAME MODE   🧭", delay=DELAY_SLOW)
    print("═" * 50)
    print("  1. Single Boss (recommended)")
    print("     Classic run: one hero vs one boss.")
    print("  2. Gauntlet Challenge")
    print("     Defeat one boss, then face the second with partial healing.")
    print("  q. Quit")
    print("═" * 50)
    while True:
        choice = prompt_input("\n  Press 1, 2, or q: ").strip().lower()
        if choice == "q":
            slow_print("\n  👋 Thanks for playing. Farewell, hero! ⚔️\n", delay=DELAY_NORMAL)
            sys.exit(0)
        if choice in GAME_MODES:
            return GAME_MODES[choice]
        print("  ❌ Invalid choice — enter 1, 2, or q.")


def choose_difficulty() -> str:
    """Display the difficulty menu and return the player's choice."""
    print("\n" + "═" * 50)
    slow_print("  🎚️   CHOOSE DIFFICULTY   🎚️", delay=DELAY_SLOW)
    print("═" * 50)
    print("  1. Normal (recommended)")
    print("     More forgiving boss values and priest-friendly dragon tuning.")
    print("  2. Challenging")
    print("     Harder bosses with higher damage and stronger pressure.")
    print("═" * 50)
    while True:
        choice = prompt_input("\n  Press 1 or 2: ").strip()
        if choice in DIFFICULTY_MODES:
            return DIFFICULTY_MODES[choice]
        print("  ❌ Invalid choice — enter 1 or 2.")


def _print_hero_list() -> None:
    """Print the numbered hero selection table."""
    print("\n" + "═" * 50)
    slow_print("  ⚔️   CHOOSE YOUR HERO   ⚔️", delay=DELAY_SLOW)
    print("═" * 50)
    for i, (cname, role, cls) in enumerate(HERO_REGISTRY, start=1):
        print(
            f"  {i}. {cname:<13}| HP: {cls.base_hp:<4}"
            f"| ATK: {cls.base_atk:<3}| {role:<16} {cls.emoji}"
        )
    print("═" * 50)


def _pick_hero_class() -> type[Character]:
    """Prompt until a valid hero number is entered; return the chosen class."""
    valid = {str(i) for i in range(1, len(HERO_REGISTRY) + 1)}
    while True:
        choice = prompt_input(f"\n  Enter a number (1-{len(HERO_REGISTRY)}): ").strip()
        if choice in valid:
            _name, _role, cls = HERO_REGISTRY[int(choice) - 1]
            return cls
        print(f"  ❌ Invalid choice — enter a number between 1 and {len(HERO_REGISTRY)}.")


def create_character() -> Character:
    """Display the hero-selection menu, prompt for a name, and return a new player."""
    _print_hero_list()
    cls    = _pick_hero_class()
    name   = prompt_input("Enter your character's name: ").strip() or "Hero"
    player = cls(name)
    pause(0.3)
    slow_print("\n  " + cls.intro.replace("{name}", name), delay=DELAY_SLOW)
    pause(0.6)
    return player


def choose_boss(difficulty: str = "normal") -> Boss:
    """Display the boss-selection menu and return a new boss instance."""
    print("\n" + "═" * 50)
    slow_print("  ☠️   CHOOSE YOUR FOE   ☠️", delay=DELAY_SLOW)
    print("═" * 50)
    for key, (name, style, cls) in BOSS_OPTIONS.items():
        print(f"  {key}. {name:<24} {cls.emoji}")
        print(f"     {style}")
    print("═" * 50)
    while True:
        choice = prompt_input("\n  Press 1 or 2: ").strip()
        if choice in BOSS_OPTIONS:
            break
        print("  ❌ Invalid choice — enter 1 or 2.")
    name, _style, cls = BOSS_OPTIONS[choice]
    return cls(name, difficulty=difficulty)


def _remaining_boss_option(current_boss: Boss) -> tuple[str, str, type[Boss]] | None:
    """Return the BOSS_OPTIONS entry for whichever boss was not chosen, or None."""
    for name, style, cls in BOSS_OPTIONS.values():
        if not isinstance(current_boss, cls):
            return name, style, cls
    return None


def _between_boss_heal(player: Character) -> None:
    """Restore 50 % of max HP between gauntlet fights and print a respite message."""
    heal_amount   = max(1, int(player.max_health * BETWEEN_BOSS_HEAL_RATIO))
    before        = player.health
    player.health = min(player.health + heal_amount, player.max_health)
    print("\n" + "═" * 50)
    slow_print("  🕊️  Brief respite between battles...", delay=DELAY_SLOW)
    slow_print(
        f"  💚 {player.name} recovers {player.health - before} HP"
        f" ({player.health}/{player.max_health}).",
        delay=DELAY_SLOW,
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
    if raw == "0":
        print("  ↩️  Cancelled — returning to action menu.")
        return -1
    if not raw.isdigit():
        print("  ❌ Invalid input — returning to action menu.")
        return -1
    idx = int(raw) - 1
    if idx < 0 or idx >= len(player.abilities):
        print("  ❌ Out of range — returning to action menu.")
        return -1
    return idx


def _print_run_summary(
    mode:             str,
    difficulty:       str,
    first_boss:       Boss,
    remaining_option: tuple[str, str, type[Boss]] | None = None,
) -> None:
    """Print a summary of the chosen mode, difficulty, and boss order."""
    mode_label       = "Single Boss"  if mode == "single"      else "Gauntlet Challenge"
    difficulty_label = "Normal"       if difficulty == "normal" else "Challenging"
    print("\n" + "═" * 50)
    slow_print("  🧾   RUN SETTINGS   🧾", delay=DELAY_NORMAL)
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
    slow_print("  🎮  Play again?", delay=DELAY_SLOW)
    print("═" * 50)
    print("  1. Yes — start a new run")
    print("  2. No  — quit")
    print("═" * 50)
    while True:
        choice = prompt_input("\n  Press 1 or 2: ").strip()
        if choice in ("", "1"):
            return True
        if choice == "2":
            return False
        print("  ❌ Enter 1 or 2.")


def _handle_player_turn(player: Character, boss: Boss) -> BattleResult | None:
    """Handle the player's action for one turn; return 'restart' or None."""
    print(f"\n  🎮 Your turn, {player.name}:")
    print("  1. ⚔️  Attack")
    print("  2. ✨ Use Special Ability")
    print("  3. 💚 Heal")
    print("  4. 📊 View Stats")
    print("  5. 🏳️  Admit Defeat")
    print("  6. 🔄 Restart (same hero & boss)")

    while True:
        choice = prompt_input("\n  Action: ").strip()
        if choice == "1":
            player.attack(boss)
            return None
        if choice == "2":
            idx = _show_ability_menu(player)
            if idx >= 0:
                player.use_ability(idx, boss)
                if player.wants_follow_up_after_ability(idx):
                    player.follow_up_action(boss)
                return None
            print("  Returning to action menu...")
        elif choice == "3":
            player.heal()
            return None
        elif choice == "4":
            print("\n  📊 --- Player ---")
            player.display_stats()
            print("  📊 --- Boss ---")
            boss.display_stats()
        elif choice == "5":
            confirm = prompt_input("\n  Really admit defeat? (y/n): ").strip().lower()
            if confirm == "y":
                slow_print(f"\n  🏳️  {player.name} lays down their weapon...")
                player.health = 0
                return None
        elif choice == "6":
            confirm = prompt_input("\n  Restart with same hero & boss? (y/n): ").strip().lower()
            if confirm == "y":
                slow_print("\n  🔄 Restarting the battle...\n")
                return BattleResult.RESTART
        else:
            print("  ❌ Invalid choice — try again.")


def _print_battle_summary(player: Character, turns: int) -> None:
    """Print a compact post-battle stat breakdown."""
    print("\n" + "─" * 50)
    slow_print("  📊  BATTLE SUMMARY", delay=DELAY_NORMAL)
    print("─" * 50)
    print(f"  Turns fought   : {turns}")
    print(f"  Damage dealt   : {player.total_damage_dealt}")
    print(f"  Damage taken   : {player.total_damage_taken}")
    print(f"  HP healed      : {player.total_healed}")
    if player.total_damage_taken > 0:
        ratio = round(player.total_damage_dealt / player.total_damage_taken, 2)
        print(f"  Dmg ratio      : {ratio}x")
    print("─" * 50)


def battle(player: Character, boss: Boss, final_boss: bool = True) -> BattleResult:
    """Run a single combat loop; return 'win', 'loss', or 'restart'."""
    pause(0.5)
    boss_emoji = boss.emoji
    slow_print(f"\n  {boss_emoji} {boss.name} appears from the shadows...", delay=DELAY_DRAMATIC)
    pause(0.5)
    slow_print("  Prepare for battle! ⚔️", delay=DELAY_DRAMATIC)
    pause(0.8)

    turn = 0
    while boss.health > 0 and player.health > 0:
        turn += 1
        print(f"\n{'═' * 50}")
        pct   = int(100 * max(player.health, 0) / player.max_health)
        state = "💀 CRITICAL" if pct < 20 else ("⚠️  LOW" if pct < 40 else "✅ OK")
        slow_print(f"  ⚔️   TURN {turn}  │  {player.name}: {state}   ⚔️", delay=DELAY_NORMAL)
        print(f"{'═' * 50}")
        print_hp_bars(player, boss)
        if player.health <= int(player.max_health * 0.25):
            slow_print(
                "  ⚠️  WARNING: You are critically low on HP! Consider healing!",
                delay=DELAY_FAST,
            )
        player.start_of_turn()
        if player.health <= 0:
            break

        action_result = _handle_player_turn(player, boss)
        if action_result == BattleResult.RESTART:
            return BattleResult.RESTART

        player.tick_cooldowns()
        player.end_of_turn()

        if boss.health > 0 and player.health > 0:
            pause(0.5)
            print(f"\n{'─' * 50}")
            slow_print(f"  {boss_emoji} {boss.name}'s turn...", delay=DELAY_SLOW)
            print(f"{'─' * 50}")
            pause(0.3)
            boss.take_turn(player)

        if player.health <= 0:
            player.try_resurrect()

        if player.health <= 0:
            break

    pause(0.8)
    _print_battle_summary(player, turn)
    print(f"\n{'═' * 50}")
    if boss.health <= 0:
        print_victory(player, boss, final_boss=final_boss)
        print(f"{'═' * 50}\n")
        return BattleResult.WIN
    print_defeat(player, boss)
    print(f"{'═' * 50}\n")
    return BattleResult.LOSS


def _battle_with_restart(
    player: Character, boss: Boss, final_boss: bool = True
) -> tuple[BattleResult, Character]:
    """Run battle, resetting on player-requested restart; return (result, survivor)."""
    combatant = player
    while True:
        result = battle(combatant, boss.reset(), final_boss=final_boss)
        if result != BattleResult.RESTART:
            return result, combatant
        combatant = player.reset()


def _run_gauntlet(difficulty: str, player: Character, first_boss: Boss) -> None:
    """Run the gauntlet: two sequential bosses with a respite heal between them."""
    remaining = _remaining_boss_option(first_boss)
    _print_run_summary("gauntlet", difficulty, first_boss, remaining_option=remaining)

    if not _confirm_or_restart():
        slow_print("\n  🔄 Starting over...\n", delay=DELAY_NORMAL)
        return

    # If somehow no second boss exists, treat it as a single fight
    if remaining is None:
        _battle_with_restart(player.reset(), first_boss, final_boss=True)
        return

    result, survivor = _battle_with_restart(player.reset(), first_boss, final_boss=False)
    if result != BattleResult.WIN:
        return

    _between_boss_heal(survivor)
    next_name, _style, next_cls = remaining  # remaining is guaranteed non-None here
    slow_print(
        f"\n  ⚠️  The gauntlet continues... {next_name} descends upon you!",
        delay=DELAY_SLOW,
    )
    second_boss = next_cls(next_name, difficulty=difficulty)
    _battle_with_restart(survivor, second_boss, final_boss=True)


def _run_once(difficulty: str, mode: str, player: Character, first_boss: Boss) -> None:
    """Route a run to the appropriate mode handler."""
    if mode == "gauntlet":
        _run_gauntlet(difficulty, player, first_boss)
        return

    _print_run_summary(mode, difficulty, first_boss)
    if not _confirm_or_restart():
        slow_print("\n  🔄 Starting over...\n", delay=DELAY_NORMAL)
        return
    _battle_with_restart(player.reset(), first_boss, final_boss=True)


def main() -> None:
    """Entry point — parse args, show title, then loop through runs until quit."""
    parser = argparse.ArgumentParser(description="Hero vs Boss fantasy battle game.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Skip all delays and slow-print effects for fast testing.",
    )
    global DEBUG  # pylint: disable=global-statement
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
            slow_print("\n  👋 Thanks for playing. Farewell, hero! ⚔️\n", delay=DELAY_NORMAL)
            break
if __name__ == "__main__":
    main()
