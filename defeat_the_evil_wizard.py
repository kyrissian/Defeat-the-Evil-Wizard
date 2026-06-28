"""Run a turn-based hero-vs-boss fantasy battle game."""

import os
import random
import subprocess
import sys
import time
import builtins
from typing import Any

if os.name == "nt" and sys.flags.utf8_mode != 1 and os.environ.get("WIZARD_UTF8_REEXEC") != "1":
    script_path = os.path.abspath(sys.argv[0])
    cmd = [sys.executable, "-X", "utf8", script_path, *sys.argv[1:]]
    env = os.environ.copy()
    env["WIZARD_UTF8_REEXEC"] = "1"
    result = subprocess.run(cmd, check=False, env=env)
    sys.exit(result.returncode)

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

Ability = dict[str, Any]


def ability(name: str, desc: str, method, cd: int = 0) -> Ability:
    """Build an ability dict, keeping hero __init__ methods to one line per ability."""
    return {"name": name, "desc": desc, "method": method, "max_cooldown": cd, "cooldown": 0}


def prompt_input(prompt=""):
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


def slow_print(text, delay=0.03):
    """Print text one character at a time for a dramatic effect."""
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def pause(seconds=0.6):
    """Sleep for the given number of seconds."""
    time.sleep(seconds)


def print_hp_bars(player, boss):
    """Print side-by-side HP bars scaled to each character's max health."""
    max_bar  = 24
    name_col = 16
    highest  = max(player.max_health, boss.max_health)

    def make_bar(label, character):
        """Build a single labelled HP bar string."""
        bar_width = max(1, int(max_bar * character.max_health / highest))
        filled    = int(bar_width * max(character.health, 0) / character.max_health)
        hp_bar    = "█" * filled + "░" * (bar_width - filled)
        name      = character.name[:name_col].ljust(name_col)
        return f"{label} {name} [{hp_bar}] {character.health}/{character.max_health}"

    print(f"\n  {make_bar('YOU', player)}")
    print(f"  {make_bar('FOE', boss)}\n")


def print_title():
    """Print the game title banner."""
    print("\n" + "═" * 50)
    slow_print("  ⚔️   DEFEAT THE EVIL WIZARD   ⚔️", delay=0.04)
    slow_print("  Defeat the Evil Wizard before he destroys the realm...", delay=0.03)
    print("═" * 50)
    pause(0.8)


def print_victory(player, boss, final_boss=True):
    """Print the victory screen after defeating a boss."""
    print("\n" + "═" * 50)
    slow_print(f"  🏆  {player.name} has defeated {boss.name}!")
    if final_boss:
        slow_print("  The darkness recedes. Light returns to the realm. ✨")
    else:
        slow_print("  A new threat stirs... this war is not over yet. ⚔️")
    print("═" * 50)


def print_defeat(player, boss):
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

    def __init__(self, name, health, attack_power, heal_power=20):
        """Initialise core stats and empty ability/status containers."""
        self.name            = name
        self.health          = health
        self.attack_power    = attack_power
        self.max_health      = health
        self.heal_power      = heal_power
        self.abilities: list[Ability]        = []
        self.status_effects: dict[str, bool] = {}

    def attack(self, opponent):
        """Deal randomised physical damage; respect Moonfire, Evade, and Shield."""
        if self.status_effects.get(STATUS_MOONFIRE):
            self.health -= 8
            slow_print(f"  🌙 Moonfire burns {self.name} for 8 damage!")
            if self.health <= 0:
                slow_print(f"  ☠️  {self.name} is consumed by Moonfire!")
                return

        if opponent.try_negate_incoming_attack(self.name):
            return

        damage = random.randint(
            int(self.attack_power * 0.8),
            int(self.attack_power * 1.2),
        )
        opponent.health -= damage
        slow_print(f"  ⚔️  {self.name} attacks {opponent.name} for {damage} damage!")
        if opponent.health <= 0:
            slow_print(f"  💥 {opponent.name} has been defeated!")

    def heal(self):
        """Restore HP up to max using this character's heal_power."""
        before = self.health
        self.health = min(self.health + self.heal_power, self.max_health)
        healed = self.health - before
        slow_print(f"  💚 {self.name} heals for {healed} HP! ({self.health}/{self.max_health})")

    def use_ability(self, index, opponent):
        """Fire the ability at the given index if it exists and is off cooldown."""
        if index < 0 or index >= len(self.abilities):
            print("  ❌ Invalid ability choice.")
            return
        ab        = self.abilities[index]
        remaining = ab.get("cooldown", 0)
        if remaining > 0:
            slow_print(f"  ⏳ {ab['name']} is on cooldown for {remaining} more turn(s)!")
            return
        slow_print(f"\n  ✨ {self.name} uses {ab['name']}!", delay=0.05)
        pause(0.3)
        ab["method"](opponent)
        if "max_cooldown" in ab:
            ab["cooldown"] = ab["max_cooldown"]

    def tick_cooldowns(self):
        """Reduce every ability's remaining cooldown by one at end of turn."""
        for ab in self.abilities:
            if ab.get("cooldown", 0) > 0:
                ab["cooldown"] -= 1

    def start_of_turn(self):
        """Hook called at the start of this character's turn (override in subclasses)."""
        return None

    def end_of_turn(self):
        """Hook called at the end of this character's turn (override in subclasses)."""
        return None

    def wants_follow_up_after_ability(self, _ability_index):
        """Return True if this character gets a bonus action after the given ability."""
        return False

    def follow_up_action(self, _opponent):
        """Execute the bonus follow-up action (override in subclasses that need it)."""
        return None

    def try_negate_incoming_attack(self, attacker_name):
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

    def should_skip_turn_from_control(self):
        """Return True and print a message if Frozen or Blinded causes a lost turn."""
        if self.status_effects.get(STATUS_FROZEN):
            self.status_effects[STATUS_FROZEN] = False
            slow_print(f"  ❄️  {self.name} is frozen and cannot act this turn!")
            return True
        if self.status_effects.get(STATUS_BLINDED):
            self.status_effects[STATUS_BLINDED] = False
            if random.random() < 0.5:
                slow_print(f"  😵 {self.name} is blinded and stumbles — misses!")
                return True
        return False

    def display_stats(self):
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

    def _deal_damage(self, opponent, damage):
        """Apply a fixed damage value to opponent and report remaining HP."""
        opponent.health -= damage
        slow_print(
            f"  💥 {opponent.name} takes {damage} damage!"
            f" ({opponent.health}/{opponent.max_health} HP remaining)"
        )
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _drain_life(self, opponent, amount):
        """Remove HP from opponent and add it to self; return (opponent_hp, self_hp)."""
        opponent.health -= amount
        self.health = min(self.health + amount, self.max_health)
        return opponent.health, self.health


# ─────────────────────────────────────────────
#  HERO CLASSES
# ─────────────────────────────────────────────

class Warrior(Character):
    """Tank with sustain, shields, and a permanent attack buff."""

    def __init__(self, name):
        """Set up Warrior stats and abilities."""
        super().__init__(name, health=160, attack_power=26, heal_power=20)
        self._battle_cry_used = False
        self.abilities = [
            ability(
                "⚔️  Shield Bash",
                "Deal 1.5× damage and block the opponent's next attack.",
                self._shield_bash, cd=2,
            ),
            ability(
                "🌀 Whirlwind",
                "Spin attack dealing 2× damage.",
                self._whirlwind, cd=2,
            ),
            ability(
                "📣 Battle Cry",
                "One-time war cry: raise your attack power by 8 permanently.",
                self._battle_cry, cd=3,
            ),
        ]

    def _shield_bash(self, opponent):
        """Deal 1.5× damage then raise a shield against the next incoming hit."""
        self._deal_damage(opponent, int(self.attack_power * 1.5))
        self.status_effects[STATUS_SHIELD] = True
        slow_print(f"  🛡️  {self.name} raises shield — next attack will be blocked!")

    def _whirlwind(self, opponent):
        """Spin and deal 2× damage to the opponent."""
        self._deal_damage(opponent, self.attack_power * 2)

    def _battle_cry(self, _opponent):
        """Permanently raise attack power by 8; usable only once per battle."""
        if self._battle_cry_used:
            slow_print("  ❌ Battle Cry can only be used once per battle!")
            return
        self.attack_power += 8
        self._battle_cry_used = True
        slow_print(f"  📣 {self.name} roars! Attack power raised to {self.attack_power}.")


class Mage(Character):
    """Glass cannon with a surge mechanic for double-action turns."""

    def __init__(self, name):
        """Set up Mage stats and abilities."""
        super().__init__(name, health=105, attack_power=38, heal_power=15)
        self._surge_active = False
        self._surge_bonus  = 12
        self.abilities = [
            ability(
                "🔥 Fireball",
                "Hurl a fireball for 1.8× damage.",
                self._fireball, cd=2,
            ),
            ability(
                "❄️  Frost Nova",
                "Freeze the opponent; they lose their next attack.",
                self._frost_nova, cd=4,
            ),
            ability(
                "⚡ Arcane Surge",
                "Boost attack power by 12 — then pick a follow-up action.",
                self._arcane_surge, cd=3,
            ),
        ]

    def _fireball(self, opponent):
        """Hurl a fireball dealing 1.8× attack damage."""
        self._deal_damage(opponent, int(self.attack_power * 1.8))

    def _frost_nova(self, opponent):
        """Freeze the opponent so they skip their next turn."""
        opponent.status_effects[STATUS_FROZEN] = True
        slow_print(f"  ❄️  {opponent.name} is frozen and will skip their next turn!")

    def _arcane_surge(self, _opponent):
        """Temporarily boost attack power by 12 and enable a follow-up action."""
        self.attack_power  += self._surge_bonus
        self._surge_active  = True
        slow_print(
            f"  ⚡ Arcane Surge active! Your attack power is now {self.attack_power}.\n"
            f"  💡 Your NEXT attack or ability this turn hits at full surge power.\n"
            f"  ⚠️  The bonus expires automatically after the wizard's turn."
        )

    def end_of_turn(self):
        """Expire the Arcane Surge bonus at the end of the Mage's turn."""
        if self._surge_active:
            self.attack_power  -= self._surge_bonus
            self._surge_active  = False

    def wants_follow_up_after_ability(self, ability_index):
        """Return True when Arcane Surge is active so the player gets a bonus action."""
        return self._surge_active and ability_index == 2

    def follow_up_action(self, opponent):
        """Prompt the player to attack or pass as the surge follow-up."""
        slow_print("\n  ⚡ Surge is active — pick your follow-up action!")
        if prompt_input("\n  Follow-up (1=Attack, skip=pass): ").strip() == "1":
            self.attack(opponent)


class Archer(Character):
    """Speed and range specialist with a guaranteed-dodge utility."""

    def __init__(self, name):
        """Set up Archer stats and abilities."""
        super().__init__(name, health=120, attack_power=32, heal_power=18)
        self.abilities = [
            ability(
                "🏹 Quick Shot",
                "Two fast arrows — each deals 0.7× damage.",
                self._quick_shot, cd=2,
            ),
            ability(
                "🎯 Sniper Shot",
                "Bypasses all defenses for 1.7× damage.",
                self._sniper_shot, cd=2,
            ),
            ability(
                "💨 Evade",
                "Guarantee a dodge on the next attack aimed at you.",
                self._evade, cd=3,
            ),
        ]

    def _quick_shot(self, opponent):
        """Fire two arrows, each dealing 0.7× damage."""
        for i in range(1, 3):
            slow_print(f"  🏹 Arrow {i}:", delay=0.02)
            self._deal_damage(opponent, int(self.attack_power * 0.7))

    def _sniper_shot(self, opponent):
        """Deal 1.7× damage that bypasses Evade and Shield."""
        damage = int(self.attack_power * 1.7)
        opponent.health -= damage
        slow_print(
            f"  🎯 Sniper Shot pierces defenses! {opponent.name} takes {damage} damage."
            f" ({opponent.health}/{opponent.max_health} HP)"
        )
        if opponent.health <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _evade(self, _opponent):
        """Set the Evade status so the next incoming attack is dodged."""
        self.status_effects[STATUS_EVADE] = True
        slow_print(f"  💨 {self.name} readies a dodge — next attack will miss!")


class Paladin(Character):
    """Holy defender with strong heals and a damage-absorbing shield."""

    def __init__(self, name):
        """Set up Paladin stats and abilities."""
        super().__init__(name, health=150, attack_power=27, heal_power=28)
        self.abilities = [
            ability(
                "✝️  Holy Strike",
                "A blessed strike for 1.5× damage.",
                self._holy_strike, cd=2,
            ),
            ability(
                "🛡️  Divine Shield",
                "Block the next attack aimed at you.",
                self._divine_shield, cd=3,
            ),
            ability(
                "🔥 Consecration",
                "Deal moderate damage and heal yourself 15 HP.",
                self._consecration, cd=2,
            ),
        ]

    def _holy_strike(self, opponent):
        """Strike with holy power for 1.5× damage."""
        self._deal_damage(opponent, int(self.attack_power * 1.5))

    def _divine_shield(self, _opponent):
        """Raise a divine shield that absorbs the next incoming attack."""
        self.status_effects[STATUS_SHIELD] = True
        slow_print(f"  🛡️  {self.name} is shielded — the next attack will be absorbed!")

    def _consecration(self, opponent):
        """Deal 0.9× damage and heal self for 15 HP."""
        self._deal_damage(opponent, int(self.attack_power * 0.9))
        self.health = min(self.health + 15, self.max_health)
        slow_print(
            f"  🔥 Holy ground heals {self.name} for 15."
            f" HP: {self.health}/{self.max_health}"
        )


class DeathKnight(Character):
    """Dark drainer who trades and steals HP to stay alive."""

    def __init__(self, name):
        """Set up DeathKnight stats and abilities."""
        super().__init__(name, health=160, attack_power=31, heal_power=16)
        self.abilities = [
            ability(
                "💀 Death Coil",
                "Dark bolt that steals 18 HP from the opponent.",
                self._death_coil, cd=2,
            ),
            ability(
                "🩸 Blood Boil",
                "Sacrifice 18 HP to unleash 2.1× damage.",
                self._blood_boil, cd=2,
            ),
            ability(
                "🌑 Dark Pact",
                "Drain 20 HP from opponent directly into your own pool.",
                self._dark_pact, cd=3,
            ),
        ]

    def _death_coil(self, opponent):
        """Steal 18 HP from the opponent and add it to self."""
        opp_hp, self_hp = self._drain_life(opponent, 18)
        slow_print(
            f"  💀 Death Coil drains 18 HP from {opponent.name}!"
            f" {self.name} absorbs the life. HP: {self_hp}/{self.max_health}"
        )
        if opp_hp <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")

    def _blood_boil(self, opponent):
        """Sacrifice 18 HP to deal 2.1× damage; blocked if HP is too low."""
        if self.health <= 18:
            slow_print("  ❌ Not enough HP to sacrifice for Blood Boil!")
            return
        self.health -= 18
        slow_print(f"  🩸 {self.name} sacrifices 18 HP... HP: {self.health}/{self.max_health}")
        self._deal_damage(opponent, int(self.attack_power * 2.1))

    def _dark_pact(self, opponent):
        """Drain 20 HP directly from the opponent into self."""
        opp_hp, self_hp = self._drain_life(opponent, 20)
        slow_print(
            f"  🌑 Dark Pact! Drained 20 HP from {opponent.name}."
            f" {self.name} HP: {self_hp}/{self.max_health}"
        )
        if opp_hp <= 0:
            slow_print(f"  ☠️  {opponent.name} has been defeated!")


class HolyPriest(Character):
    """Light-sustain healer who weakens opponents over time."""

    def __init__(self, name):
        """Set up HolyPriest stats and abilities."""
        super().__init__(name, health=170, attack_power=29, heal_power=30)
        self.abilities = [
            ability(
                "✨ Smite",
                "Channel the Light for 1.25× holy damage.",
                self._smite, cd=2,
            ),
            ability(
                "🙏 Prayer of Healing",
                "Restore 40 HP through divine grace.",
                self._prayer_of_healing, cd=3,
            ),
            ability(
                "🎵 Divine Hymn",
                "Holy chant: heal 25 HP and weaken opponent's attack by 4.",
                self._divine_hymn, cd=4,
            ),
        ]

    def _smite(self, opponent):
        """Channel the Light for 1.25× damage plus a flat 6 bonus."""
        self._deal_damage(opponent, int(self.attack_power * 1.25) + 6)

    def _prayer_of_healing(self, _opponent):
        """Restore up to 40 HP through divine prayer."""
        before = self.health
        self.health = min(self.health + 40, self.max_health)
        slow_print(
            f"  🙏 {self.name} prays... restored {self.health - before} HP."
            f" HP: {self.health}/{self.max_health}"
        )

    def _divine_hymn(self, opponent):
        """Heal 25 HP and permanently reduce the opponent's attack power by 4."""
        before = self.health
        self.health = min(self.health + 25, self.max_health)
        opponent.attack_power = max(0, opponent.attack_power - 4)
        slow_print(
            f"  🎵 Divine Hymn resonates! {self.name} healed {self.health - before} HP."
            f" {opponent.name}'s attack weakened to {opponent.attack_power}."
        )


class Rogue(Character):
    """Assassin with high-risk burst, poison, and smoke utility."""

    def __init__(self, name):
        """Set up Rogue stats and abilities."""
        super().__init__(name, health=120, attack_power=34, heal_power=15)
        self.abilities = [
            ability(
                "🗡️  Backstab",
                "60 % chance of 3× damage. Miss on 40 %.",
                self._backstab, cd=2,
            ),
            ability(
                "💨 Smoke Bomb",
                "Evade next attack and reduce opponent precision.",
                self._smoke_bomb, cd=3,
            ),
            ability(
                "☠️  Poison Blade",
                "Coat your blade — opponent takes 12 damage next turn.",
                self._poison_blade, cd=2,
            ),
        ]

    def _backstab(self, opponent):
        """65 % chance to deal 2.6× damage; otherwise miss entirely."""
        if random.random() < 0.65:
            slow_print("  🗡️  Critical backstab!", delay=0.05)
            pause(0.3)
            self._deal_damage(opponent, int(self.attack_power * 2.6))
        else:
            slow_print(f"  ❌ {self.name} missed! The opponent sidesteps.")

    def _smoke_bomb(self, opponent):
        """Grant self Evade and apply Blinded to the opponent."""
        self.status_effects[STATUS_EVADE]       = True
        opponent.status_effects[STATUS_BLINDED] = True
        slow_print(
            f"  💨 Smoke fills the air! {self.name} will evade the next attack."
            f" {opponent.name} is blinded (50 % miss next turn)."
        )

    def _poison_blade(self, opponent):
        """Apply Poisoned to the opponent; deals 12 damage at start of their next turn."""
        opponent.status_effects[STATUS_POISONED] = True
        slow_print(
            f"  ☠️  {opponent.name} is poisoned!"
            " Takes 12 damage at the start of the next wizard action."
        )


class Druid(Character):
    """Nature shaman with a delayed heal-over-time and a bear form."""

    def __init__(self, name):
        """Set up Druid stats and abilities."""
        super().__init__(name, health=130, attack_power=30, heal_power=25)
        self._regrowth_tick = False
        self.abilities = [
            ability(
                "⚡ Wrath",
                "Call down nature's fury for 1.5× damage.",
                self._wrath, cd=2,
            ),
            ability(
                "🐻 Bear Form",
                "Hulk out: +24 temp HP and shield the next attack.",
                self._bear_form, cd=3,
            ),
            ability(
                "🌿 Regrowth",
                "Heal 20 now; automatically heal 12 more next turn.",
                self._regrowth, cd=2,
            ),
        ]

    def _wrath(self, opponent):
        """Call nature's fury for 1.5× damage."""
        self._deal_damage(opponent, int(self.attack_power * 1.5))

    def _bear_form(self, _opponent):
        """Gain 24 temporary HP and shield the next incoming attack."""
        self.health = min(self.health + 24, self.max_health + 24)
        self.status_effects[STATUS_SHIELD] = True
        slow_print(
            f"  🐻 {self.name} transforms into a bear!"
            f" +24 HP (now {self.health}) and next hit blocked."
        )

    def _regrowth(self, _opponent):
        """Heal 20 HP now and queue a 12 HP tick for the start of the next turn."""
        self.health = min(self.health + 20, self.max_health)
        self._regrowth_tick = True
        slow_print(
            f"  🌿 Regrowth blooms! {self.name} healed 20 HP."
            f" Another 12 HP will restore next turn. HP: {self.health}/{self.max_health}"
        )

    def start_of_turn(self):
        """Apply the queued Regrowth tick at the start of the Druid's turn."""
        if self._regrowth_tick:
            self.health = min(self.health + 12, self.max_health)
            slow_print(
                f"  🌿 Regrowth heals {self.name} for 12 HP."
                f" HP: {self.health}/{self.max_health}"
            )
            self._regrowth_tick = False


# ─────────────────────────────────────────────
#  BASE BOSS
# ─────────────────────────────────────────────

class Boss(Character):
    """Shared logic for all boss types: regen, poison tick, and direct hit."""

    _regen_per_turn = 0

    def regenerate(self, emoji="💜"):
        """Restore a fixed amount of HP at the start of each boss turn."""
        self.health = min(self.health + self._regen_per_turn, self.max_health)
        slow_print(
            f"  {emoji} {self.name} regenerates {self._regen_per_turn} HP."
            f" HP: {self.health}/{self.max_health}"
        )

    def _tick_statuses(self):
        """Resolve any active status effects on this boss before it acts."""
        if self.status_effects.get(STATUS_POISONED):
            self.health -= 12
            slow_print(
                f"  ☠️  Poison deals 12 damage to {self.name}!"
                f" HP: {self.health}/{self.max_health}"
            )
            self.status_effects[STATUS_POISONED] = False

    def _hit_player(self, player, damage):
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


# ─────────────────────────────────────────────
#  BOSS CLASSES
# ─────────────────────────────────────────────

class EvilWizard(Boss):
    """Regenerating spellcaster with suppression, enrage, and void burst."""

    def __init__(self, name, difficulty="normal"):
        """Set up EvilWizard stats scaled to the chosen difficulty."""
        health                  = 200
        attack                  = 20
        self._regen_per_turn    = 3
        self._dark_bonus_damage = 10
        if difficulty == "challenging":
            health                  = 210
            attack                  = 21
            self._regen_per_turn    = 3
            self._dark_bonus_damage = 11
        super().__init__(name, health=health, attack_power=attack, heal_power=5)
        self.difficulty = difficulty
        self._enraged   = False
        self._void_used = False

    def take_turn(self, player):
        """Regenerate, tick statuses, then execute the wizard's combat action."""
        self.regenerate(emoji="🧙")
        self._tick_statuses()

        if self.should_skip_turn_from_control():
            return

        slow_print(f"\n  🧙 {self.name}: \"{random.choice(WIZARD_TAUNTS)}\"", delay=0.04)
        pause(0.4)

        if not self._enraged and self.health <= self.max_health * 0.4:
            self._enraged      = True
            self.attack_power += 5
            slow_print(
                f"\n  ⚡ {self.name} becomes ENRAGED!"
                f" Attack power → {self.attack_power}!",
                delay=0.05,
            )
            pause(0.4)

        if isinstance(player, HolyPriest):
            if not player.status_effects.get(STATUS_DARK_SUPPRESSED):
                player.status_effects[STATUS_DARK_SUPPRESSED] = True
                player.heal_power = player.heal_power // 2
                slow_print(
                    f"\n  🌑 {self.name} senses the Light within {player.name}"
                    " and unleashes DARK SUPPRESSION! Her healing is halved!",
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

        if not self._void_used and self.health <= self.max_health * 0.2:
            self._void_used = True
            slow_print(f"\n  🌑 {self.name} channels VOID SURGE!", delay=0.05)
            pause(0.5)
            self._hit_player(player, self.attack_power * 2)
            return

        if self.health <= self.max_health * 0.4:
            slow_print(f"\n  💜 {self.name} hurls a SHADOW BOLT!", delay=0.05)
            pause(0.3)
            self._hit_player(player, self.attack_power * 2)
        else:
            self.attack(player)


class AncientDragon(Boss):
    """Relentless bruiser with fury cycles, aura damage, and inferno breath."""

    def __init__(self, name, difficulty="normal"):
        """Set up AncientDragon stats scaled to the chosen difficulty."""
        health                    = 210
        attack                    = 17
        self._regen_per_turn      = 2
        self._aura_damage         = 5
        self._priest_aura_damage  = 3
        self._inferno_mult        = 2.8
        self._priest_inferno_mult = 2.2
        self._tail_slam_mult      = 1.9
        if difficulty == "challenging":
            health                    = 210
            attack                    = 17
            self._regen_per_turn      = 2
            self._aura_damage         = 5
            self._priest_aura_damage  = 3
            self._inferno_mult        = 2.5
            self._priest_inferno_mult = 2.0
            self._tail_slam_mult      = 2.0
        super().__init__(name, health=health, attack_power=attack, heal_power=0)
        self.difficulty    = difficulty
        self._enraged      = False
        self._inferno_used = False
        self._fury         = 0

    def take_turn(self, player):
        """Tick statuses, regenerate, then execute the dragon's combat pattern."""
        self._tick_statuses()
        if self.health <= 0:
            return

        self.regenerate(emoji="🐉")
        if self.should_skip_turn_from_control():
            return

        slow_print(f"\n  🐉 {self.name}: \"{random.choice(DRAGON_TAUNTS)}\"", delay=0.04)
        pause(0.4)

        if not self._enraged and self.health <= self.max_health * 0.4:
            self._enraged      = True
            self.attack_power += 6
            slow_print(
                f"\n  🔥 {self.name} enters RAMPAGE!"
                f" Attack power → {self.attack_power}!",
                delay=0.05,
            )
            pause(0.4)

        aura = self._priest_aura_damage if isinstance(player, HolyPriest) \
               else self._aura_damage
        player.health -= aura
        slow_print(f"  🌋 Scorching aura burns {player.name} for {aura} damage!")
        if player.health <= 0:
            slow_print(f"  ☠️  {player.name} has been defeated!")
            return

        self._fury += 1

        if not self._inferno_used and self.health <= self.max_health * 0.2:
            self._inferno_used = True
            mult = self._priest_inferno_mult if isinstance(player, HolyPriest) \
                   else self._inferno_mult
            slow_print("\n  🔥 INFERNO BREATH engulfs the battlefield!", delay=0.05)
            pause(0.5)
            self._hit_player(player, int(self.attack_power * mult))
            return

        if self._fury >= 3:
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
                int(self.attack_power * 0.6),
                int(self.attack_power * 0.9),
            )
            self._hit_player(player, damage)


# ─────────────────────────────────────────────
#  GAME DATA
# ─────────────────────────────────────────────

# (display_name, hp, atk, role, emoji, class_obj)
HERO_REGISTRY = [
    ("Warrior",      160, 26, "Tank & sustain",  "⚔️",  Warrior),
    ("Mage",         105, 38, "Glass cannon",    "🔮",  Mage),
    ("Archer",       120, 32, "Speed & range",   "🏹",  Archer),
    ("Paladin",      150, 27, "Holy defender",   "🛡️",  Paladin),
    ("Death Knight", 160, 31, "Dark drainer",    "💀",  DeathKnight),
    ("Holy Priest",  170, 29, "Light sustain",   "✨",  HolyPriest),
    ("Rogue",        120, 34, "Assassin burst",  "🗡️",  Rogue),
    ("Druid",        130, 30, "Nature shaman",   "🌿",  Druid),
]

BOSS_OPTIONS = {
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

BETWEEN_BOSS_HEAL_RATIO = 0.35
GAME_MODES       = {"": "single",  "1": "single",  "2": "gauntlet"}
DIFFICULTY_MODES = {"": "normal",  "1": "normal",  "2": "challenging"}


# ─────────────────────────────────────────────
#  GAME FUNCTIONS
# ─────────────────────────────────────────────

def choose_game_mode():
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


def choose_difficulty():
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


def create_character():
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


def choose_boss(difficulty="normal"):
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


def _remaining_boss_option(current_boss):
    """Return the BOSS_OPTIONS entry for whichever boss was not chosen, or None."""
    for name, style, cls, emoji in BOSS_OPTIONS.values():
        if not isinstance(current_boss, cls):
            return name, style, cls, emoji
    return None


def _between_boss_heal(player):
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


def _show_ability_menu(player):
    """Print the ability list and return the chosen 0-based index, or -1 to cancel."""
    print("\n  ✨ Choose an ability:")
    for i, ab in enumerate(player.abilities, start=1):
        cd     = ab.get("cooldown", 0)
        status = f"  ⏳ {cd} turn(s)" if cd > 0 else "  ✅ Ready"
        print(f"    {i}. {ab['name']}{status} — {ab['desc']}")
    print("    0. Cancel")
    raw = prompt_input("  Ability number: ").strip()
    if raw == "0" or not raw.isdigit():
        return -1
    idx = int(raw) - 1
    if idx < 0 or idx >= len(player.abilities):
        print("  ❌ Out of range.")
        return -1
    return idx


def _print_run_summary(mode, difficulty, first_boss, remaining_option=None):
    """Print a summary of the chosen mode, difficulty, and boss order."""
    mode_label       = "Single Boss"  if mode == "single"     else "Gauntlet Challenge"
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


def battle(player, boss, final_boss=True):
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


def main():
    """Entry point — run menus, create the player, then start the battle(s)."""
    print_title()
    pause(0.5)
    mode       = choose_game_mode()
    difficulty = choose_difficulty()
    player     = create_character()
    first_boss = choose_boss(difficulty=difficulty)
    remaining  = _remaining_boss_option(first_boss) if mode == "gauntlet" else None

    _print_run_summary(mode, difficulty, first_boss, remaining_option=remaining)

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


if __name__ == "__main__":
    main()
