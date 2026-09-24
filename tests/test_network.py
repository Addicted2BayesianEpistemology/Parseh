# SPDX-License-Identifier: GPL-3.0-or-later
"""Who may reach Parseh -- the door itself, without a server (lib/network.py).

    python3 -m unittest discover -s tests -p test_network.py

The decisions of 2026-09-23 are here as tests: a fresh install answers to
this computer and to a VPN and NOT to the Wi-Fi; a Wi-Fi device has to be let
in once with a code and is remembered afterwards; only the computer itself
may save; "this computer only" is a closed socket and not a rule; the port
moved off AnkiConnect's 8765.

Nothing here binds a listening server: this is the door, and the door can be
asked its questions with no house behind it.  What the server does with the
answers -- Server.verify_request, Handler._gate, the re-bind -- is driven in
the smoke test, which owns a running Parseh.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import network                                                 # noqa: E402
import settingspage                                            # noqa: E402


class NetworkTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.store = Path(self._td.name) / "config" / "network.json"
        self._was = network.STORE
        network.STORE = str(self.store)
        network._CODE.update({"code": "", "made": 0.0, "wrong": 0})
        network._RESOLVED.clear()

    def tearDown(self):
        network.STORE = self._was
        self._td.cleanup()

    # ---- what a fresh install is
    def test_a_fresh_install_answers_to_this_computer_and_a_vpn_only(self):
        self.assertFalse(self.store.exists(), "nothing is written until something is saved")
        doc = network.settings()
        self.assertEqual(network.DEFAULT_PORT, doc["port"])
        self.assertTrue(doc["vpn"])
        self.assertFalse(doc["lan"], "the Wi-Fi door starts shut")
        self.assertTrue(network.may_connect("127.0.0.1"))
        self.assertTrue(network.may_connect("::1"))
        self.assertTrue(network.may_connect("100.101.102.103"), "a Tailscale address")
        self.assertFalse(network.may_connect("192.168.1.20"), "the Wi-Fi")
        self.assertFalse(network.may_connect("8.8.8.8"), "the internet")

    def test_the_default_port_is_not_ankiconnects(self):
        self.assertEqual(7654, network.DEFAULT_PORT)
        self.assertNotEqual(network.ANKICONNECT_PORT, network.DEFAULT_PORT)

    def test_this_computer_only_is_a_closed_socket(self):
        network.save({"vpn": False, "lan": False})
        self.assertEqual("127.0.0.1", network.bind_host())
        network.save({"vpn": True})
        self.assertEqual("0.0.0.0", network.bind_host())
        network.save({"vpn": False, "lan": True})
        self.assertEqual("0.0.0.0", network.bind_host())

    def test_an_ipv4_address_seen_through_ipv6_is_the_same_device(self):
        # a machine with IPv6 on reports an IPv4 client this way; judged as
        # anything else, the Wi-Fi door would look shut to it and open to nobody
        self.assertEqual(network.LAN, network.where("::ffff:192.168.1.20"))
        self.assertEqual(network.VPN, network.where("::ffff:100.64.0.7"))
        self.assertEqual(network.SELF, network.where("::ffff:127.0.0.1"))

    def test_a_range_added_by_hand_counts_as_a_vpn(self):
        # 172.16/12 is a private range, so without being named it is the Wi-Fi
        self.assertEqual(network.LAN, network.where("172.31.255.1"))
        network.save({"extra": ["172.31.0.0/16"]})
        self.assertEqual(network.VPN, network.where("172.31.255.1"))
        self.assertTrue(network.may_connect("172.31.255.1"), "a VPN needs no code")

    def test_a_range_that_is_neither_a_range_nor_a_name_is_refused(self):
        with self.assertRaises(network.NetworkError):
            network.save({"extra": ["not a range!!"]})
        self.assertEqual([], network.settings()["extra"], "and nothing was written")

    # ---- the code, and being let in
    def test_the_wifi_needs_a_code_and_the_others_do_not(self):
        network.save({"lan": True})
        self.assertTrue(network.needs_code("192.168.1.20"))
        self.assertFalse(network.needs_code("127.0.0.1"))
        self.assertFalse(network.needs_code("100.64.0.7"))

    def test_a_device_that_types_the_code_is_remembered(self):
        network.save({"lan": True})
        c = network.code()["code"]
        token, why = network.check_code(network.say_code(c), "192.168.1.20",
                                        "Mozilla/5.0 (Linux; Android 14; Pixel) "
                                        "AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36")
        self.assertTrue(token, why)
        self.assertTrue(network.let_in(token))
        named = network.devices()[0]["name"]
        self.assertEqual("Android phone · Chrome", named,
                         "named as lib/prefs.js names one")
        # and the file says so, so the device is still in tomorrow
        said = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertIn(token, said["devices"])

    def test_a_code_lets_one_device_in_and_is_then_spent(self):
        c = network.code()["code"]
        token, _ = network.check_code(c)
        self.assertTrue(token)
        again, why = network.check_code(c)
        self.assertFalse(again)
        self.assertIn("run out", why)

    def test_a_run_of_wrong_guesses_throws_the_code_away(self):
        good = network.code()["code"]
        for _ in range(network.CODE_TRIES - 1):
            token, why = network.check_code("AAAAAA" if good != "AAAAAA" else "BBBBBB")
            self.assertFalse(token)
            self.assertIn("wrong", why)
        token, why = network.check_code("AAAAAA" if good != "AAAAAA" else "BBBBBB")
        self.assertFalse(token)
        self.assertIn("thrown", why)
        # the good code is gone too: guessing at it cannot be resumed
        token, why = network.check_code(good)
        self.assertFalse(token, "the code somebody was guessing at is retired")

    def test_a_code_that_has_run_out_is_replaced_by_the_page_asking(self):
        network._CODE.update({"code": "ABCDEF", "made": time.time() - network.CODE_LIFE - 1})
        c = network.code()
        self.assertNotEqual("ABCDEF", c["code"])
        self.assertGreater(c["left"], 0)

    def test_a_token_nobody_was_given_lets_nobody_in(self):
        network.remember("a phone", "192.168.1.20")
        for junk in ("", "x", "../../etc", "é" * 40, "A" * 200):
            self.assertFalse(network.let_in(junk), repr(junk))

    def test_a_device_can_be_forgotten_one_at_a_time_or_all_at_once(self):
        a = network.remember("phone", "192.168.1.20")
        b = network.remember("laptop", "192.168.1.21")
        self.assertEqual(1, network.forget(network.devices()[0]["id"]))
        self.assertEqual(1, len(network.devices()))
        self.assertTrue(network.let_in(a) != network.let_in(b))
        self.assertEqual(1, network.forget(""))
        self.assertEqual([], network.devices())

    # ---- only the computer may save
    def test_only_this_computer_may_save(self):
        self.assertTrue(network.may_save("127.0.0.1"))
        self.assertTrue(network.may_save("::1"))
        self.assertFalse(network.may_save("192.168.1.20"))
        self.assertFalse(network.may_save("100.64.0.7"), "a VPN may read, not save")

    # ---- the port
    def test_a_port_below_1024_is_refused_in_words(self):
        with self.assertRaises(network.NetworkError) as got:
            network.save({"port": 443})
        self.assertIn("administrator", str(got.exception))

    def test_a_port_that_is_taken_is_refused_by_name(self):
        import socket
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        taken = s.getsockname()[1]
        try:
            why = network.free_port(taken, "127.0.0.1")
            self.assertIn("already taken", why)
            with self.assertRaises(network.NetworkError):
                network.save({"port": taken, "vpn": False, "lan": False})
        finally:
            s.close()

    def test_a_saved_port_comes_back(self):
        network.save({"port": 7777})
        self.assertEqual(7777, network.port())
        self.assertEqual(0o600, os.stat(self.store).st_mode & 0o777,
                         "the tokens in it are nobody else's business")

    # ---- the certificate of your own
    def test_a_certificate_of_your_own_must_be_two_files_that_are_there(self):
        with self.assertRaises(network.NetworkError):
            network.save({"cert": {"cert": "/nowhere/cert.pem", "key": "/nowhere/key.pem"}})
        with self.assertRaises(network.NetworkError):
            network.save({"cert": {"cert": __file__, "key": ""}})
        network.save({"cert": {"cert": __file__, "key": __file__}})
        self.assertEqual((__file__, __file__), network.own_cert())
        network.save({"cert": {}})
        self.assertIsNone(network.own_cert())

    # ---- what the pages say about it
    def test_the_one_line_that_says_who_may_reach_it(self):
        self.assertEqual("this computer and a VPN",
                         settingspage.doors_said(network.settings()))
        network.save({"lan": True})
        self.assertEqual("this computer, a VPN and the Wi-Fi",
                         settingspage.doors_said(network.settings()))
        network.save({"vpn": False, "lan": False})
        self.assertEqual("this computer only",
                         settingspage.doors_said(network.settings()))

    def test_the_locked_page_stands_on_its_own(self):
        page = settingspage.locked_page(network.WHERE_SAID[network.LAN])
        self.assertIn("has not been let in", page)
        self.assertIn("/settings/api/pair", page)
        for asset in ("/lib/parseh.css", "/lib/parseh.js", "/lib/mobile.css"):
            self.assertNotIn(asset, page,
                             "a device that is not let in cannot fetch %s" % asset)

    def test_the_network_page_shows_but_does_not_offer_to_save_from_a_phone(self):
        state = {"settings": network.settings(), "may_save": False, "where": network.LAN,
                 "code": network.code(), "code_said": "ABC-123", "left_said": "a while",
                 "own_cert": None, "has_authority": True,
                 "addresses": ["https://localhost:7654/"]}
        page = settingspage.network_page(state)
        self.assertIn("changed from the computer", page)
        self.assertIn("disabled", page)
        may = settingspage.network_page(dict(state, may_save=True, where=network.SELF))
        self.assertNotIn("disabled", may)
        self.assertIn("Save the network settings", may)


if __name__ == "__main__":
    unittest.main()
