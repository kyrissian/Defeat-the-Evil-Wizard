"""Gameplay regression tests for Defeat the Evil Wizard."""

import unittest

import defeat_the_evil_wizard as game


class GameplayRegressionTests(unittest.TestCase):
    """Covers critical combat behavior that should not regress."""

    def setUp(self) -> None:
        """Enable debug mode so tests run without animation delays."""
        game.set_debug_mode(True)

    def test_battle_cry_failed_reuse_does_not_start_cooldown(self) -> None:
        """Battle Cry reuse failure should not consume cooldown."""
        player = game.Warrior("Tank")
        boss = game.EvilWizard("Wizard")

        player.use_ability(2, boss)
        player.abilities[2].cooldown = 0

        player.use_ability(2, boss)

        self.assertEqual(player.abilities[2].cooldown, 0)

    def test_blood_boil_insufficient_hp_does_not_start_cooldown(self) -> None:
        """Blood Boil should not go on cooldown when the cast is invalid."""
        player = game.DeathKnight("DK")
        boss = game.EvilWizard("Wizard")
        player.health = game.DK_BLOOD_BOIL_COST

        player.use_ability(1, boss)

        self.assertEqual(player.abilities[1].cooldown, 0)

    def test_arcane_surge_expires_after_enemy_turn(self) -> None:
        """Arcane Surge bonus should remain through player end and expire after enemy turn."""
        mage = game.Mage("Caster")
        opponent = game.Warrior("Dummy")
        base_attack = mage.attack_power

        mage.use_ability(2, opponent)
        self.assertEqual(mage.attack_power, base_attack + game.MAGE_SURGE_BONUS)

        mage.end_of_turn()
        self.assertEqual(mage.attack_power, base_attack + game.MAGE_SURGE_BONUS)

        mage.after_enemy_turn()
        self.assertEqual(mage.attack_power, base_attack)

    def test_between_boss_cleanup_clears_dark_suppression(self) -> None:
        """Gauntlet cleanup should clear suppression and restore base heal power."""
        priest = game.HolyPriest("Healer")
        wizard = game.EvilWizard("Wizard")
        base_heal_power = priest.base_heal_power

        wizard.take_turn(priest)
        self.assertTrue(priest.has_effect(game.STATUS_DARK_SUPPRESSED))
        self.assertEqual(priest.heal_power, base_heal_power // 2)

        game.between_boss_heal(priest)

        self.assertFalse(priest.has_effect(game.STATUS_DARK_SUPPRESSED))
        self.assertEqual(priest.heal_power, base_heal_power)

    def test_registry_uses_typed_templates(self) -> None:
        """Hero and boss registries should use typed template objects."""
        self.assertTrue(all(isinstance(hero, game.HeroTemplate) for hero in game.HERO_REGISTRY))
        self.assertTrue(all(isinstance(boss, game.BossTemplate) for boss\
            in game.BOSS_OPTIONS.values()))

    def test_reset_for_new_battle_reopens_battle_cry(self) -> None:
        """Per-battle reset should allow Battle Cry to be used again."""
        warrior = game.Warrior("Tank")
        boss = game.EvilWizard("Wizard")

        warrior.use_ability(2, boss)
        warrior.abilities[2].cooldown = 0
        warrior.use_ability(2, boss)
        self.assertEqual(warrior.abilities[2].cooldown, 0)

        warrior.reset_for_new_battle()
        warrior.use_ability(2, boss)
        self.assertEqual(warrior.abilities[2].cooldown, warrior.abilities[2].max_cooldown)

    def test_reset_for_new_battle_clears_surge_and_regrowth(self) -> None:
        """Per-battle reset should clear pending Mage and Druid temporary state."""
        mage = game.Mage("Caster")
        dummy = game.Warrior("Dummy")
        base_attack = mage.attack_power
        mage.use_ability(2, dummy)
        self.assertTrue(mage.wants_follow_up_after_ability(2))
        self.assertEqual(mage.attack_power, base_attack + game.MAGE_SURGE_BONUS)
        mage.reset_for_new_battle()
        self.assertFalse(mage.wants_follow_up_after_ability(2))
        self.assertEqual(mage.attack_power, base_attack)

        druid = game.Druid("Leaf")
        base_hp = druid.health
        druid.use_ability(2, dummy)
        instant_hp = druid.health
        self.assertGreaterEqual(instant_hp, base_hp)
        druid.reset_for_new_battle()
        hp_before_start = druid.health
        druid.start_of_turn()
        self.assertEqual(druid.health, hp_before_start)

    def test_reset_for_new_battle_resets_cooldowns(self) -> None:
        """Per-battle reset should clear existing ability cooldowns."""
        archer = game.Archer("Arrow")
        dummy = game.Warrior("Dummy")
        archer.use_ability(0, dummy)
        self.assertGreater(archer.abilities[0].cooldown, 0)
        archer.reset_for_new_battle()
        self.assertEqual(archer.abilities[0].cooldown, 0)


if __name__ == "__main__":
    unittest.main()
