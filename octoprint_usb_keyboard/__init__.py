# coding=utf-8
from __future__ import absolute_import
import octoprint.plugin

import re
import json
import os
import uuid
import time
import json

from .usb_keyboard.listener import KeyboardListenerThread
from octoprint.events import eventManager


class UsbKeyboardPlugin(
	octoprint.plugin.StartupPlugin,
	octoprint.plugin.ShutdownPlugin,
	octoprint.plugin.SettingsPlugin,
	octoprint.plugin.SimpleApiPlugin,
	octoprint.plugin.EventHandlerPlugin
):
	def on_after_startup(self):
		self._logger.info("USB Keyboard Plugin starting")
		self.load_settings()
		self.listener = KeyboardListenerThread('USB Keyboard Listener Thread', self._device_path)
		self.listener.start()
		self._logger.info("Started Keyboard Listener")
		eventManager().subscribe("plugin_usb_keyboard_key_event", self._key_event)
		self._logger.info("Key event handler subscribed.")

	def on_shutdown(self):
		self.listener.stop()
		self._logger.info("Stopped Keyboard Listener")

	def _key_event(self, event, payload):
		key = payload.get("key")
		key_state = payload.get("key_state")

		# Placeholder: Define key actions here
		if key_state == "pressed":
			self._handle_key_press(key)

	def _handle_key_press(self, key):
		keymap = {}

		with open("octoprint_usb_keyboard/usb_keyboard/util/keys/example.json") as json_file:
			keymap = json.load(json_file)
			json_file.close()

		self._logger.info(f"Key pressed: {key}")

		if key in keymap:
			key_action = keymap[key]
			self._printer.commands(key_action.get("command"))
			self._logger.info(f"Local: {key_action.get('action')}")

	def gcode_received(self, comm, line, *args, **kwargs):
		self._logger.info(f"G-code response received: {line}")
		return line

	def get_hooks(self):
		self._logger.info("Registering gcode_received hook.")
		return {
			"octoprint.comm.protocol.gcode.received": self.gcode_received
		}

	def load_settings(self):
		self._device_path = self._settings.get(["device_path"])

	def get_settings_defaults(self):
		return dict(
			device_path="/dev/input/event1"
		)

	def get_api_commands(self):
		return dict(
			change_device_path=["device_path"]
		)

	def on_api_command(self, command, data):
		if command == "change_device_path":
			device_path = data.get("device_path")
			if device_path and device_path != self._device_path:
				self._device_path = device_path
				self.listener.stop()
				self.listener = KeyboardListenerThread('USB Keyboard Listener Thread',
													   self._device_path)
				self.listener.start()
				self._logger.info(f"Device path changed to: {self._device_path}")

	def get_update_information(self):
		return dict(
			usb_keyboard=dict(
				displayName="USB Keyboard Plugin",
				displayVersion=self._plugin_version,
				type="github_release",
				user="7591yj",
				repo="OctoPrint-Usb_keyboard",
				current=self._plugin_version,
				pip="https://github.com/7591yj/OctoPrint-Usb_keyboard/archive/{target_version}.zip"
			)
		)


# Plugin metadata
__plugin_name__ = "USB Keyboard"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = UsbKeyboardPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.gcode_received,
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
