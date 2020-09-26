# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.printer
import re
import json
from pynput import keyboard
from octoprint.events import Events, eventManager, all_events

key_dict = {}


def on_key(key, key_state, key_dict = key_dict):
  try:
    # print('alphanumeric key {0} pressed'.format(key.char))
    # repr(key).len() > 2 and 
    if key and key.char and "Key." in key.char:
      key_string = key.char
    else:
      key_string = repr(key)
      if key_string:
        key_string = key_string.replace("'", "")
        key_string = key_string.replace('""', """'""")

    # key_string = key.char if "Key." in key.char else repr(key)[1:-1]
    
    # print(f"WHAT IS THIS normal '{key}' vs '{key_string}'")
  except AttributeError:
    # print('special key {0} pressed'.format(key))
    key_string =  f"{key}"
    # print(f"WHAT IS THIS special '{key}' vs '{key_string}'")
  
  key_string = key_string.replace("Key.", "")
  
  
  
  
  
  
  if key_dict.get(key_string) == key_state:
    return
  else:
    key_dict[key_string] = key_state
    eventManager().fire("plugin_usb_keyboard_key_event", dict(key=key_string, key_state=key_state))
    # eventManager().fire("SomeOtherUSBEvent", dict(key=key_string, key_state=key_state))


def on_press(key):  # The function that's called when a key is pressed
  # print(f"key [{key_string}] pressed")
  on_key(key, "pressed")
  
  
  
  # eventManager().fire("Usb_keyboard_key_event", dict(key=key, action="pressed"))
  # print("Key pressed: {0}".format(key))

def on_release(key):  # The function that's called when a key is released
  on_key(key, "released")
  # eventManager().fire("Usb_keyboard_key_event", dict(key=key, action="released"))
  # print("Key released: {0}".format(key))

class Usb_keyboardPlugin(octoprint.plugin.StartupPlugin,
                         octoprint.plugin.SettingsPlugin,
                         octoprint.plugin.SimpleApiPlugin,
                         octoprint.plugin.EventHandlerPlugin,
                         octoprint.plugin.AssetPlugin,
                         octoprint.plugin.TemplatePlugin):

  ##~~EventHandlerPlugin mixin
  
  # def on_event(self, event, payload):
  #   self._logger.info(f"********* ON EVENT ********** {event}")
    # if event == "Usb_keyboard_key_event":
#       key = payload["key"]
#       action = payload["action"]
#
#       if self.key_status.get(key) == action:
#         return
#       else:
#         self.key_status[key] = action
#         self._logger.info(f"Key '{key}' {action}")
    
    
  def variable_sub(self, command):
    if not command:
      return command
    sub_command = command
    vars_found = re.findall("<.*>", sub_command)
    
    if vars_found:
      for variable in vars_found:
        # print(f"variable '{variable}'")
        clean_variable = variable[1:-1]
        # see https://github.com/OctoPrint/OctoPrint/blob/3ab84ed7e4c3aaaf71fe0f184b465f25d689f929/src/octoprint/plugin/__init__.py#L255
        active_profile = self._settings.get(["active_profile"])
        setting_var = self._settings.get(["profiles", active_profile, "variables", clean_variable], merged=False)
        if setting_var:
          sub_command = sub_command.replace(variable, setting_var)
        else:
          self._logger.error(f"No value for variable '{clean_variable}'... Is this intentional?")
          return None
    return sub_command
    
  def send_key_discovery(self, data):
    self._plugin_manager.send_plugin_message(self._identifier, data)

  ## It's better to subscribe to our event than to get them all and ignore most.
  def _key_event(self, event, payload):
    # self._logger.info(f"********* SUBSCRIBE ********** {event}")
    key = payload["key"]
    key_state = payload["key_state"]
    
    # print(all_events())
    if key_state is "pressed":
      self.last_key_pressed = key
      if self.key_discovery:
        self.key_discovery["name"] = key
        self._logger.info(f"Frontend asked for key, detecting keypress '{key}'")
        self.send_key_discovery(self.key_discovery)
        self.key_discovery = {}
        return
    
    
    active_profile = self._settings.get(["active_profile"])
    # self._logger.info(f"Key '{key}' {key_state}")
    
    commands = self._settings.get(["profiles", active_profile, "commands"])
    if not commands:
      # self._logger.info("Commands Empty......")
      return
      
      
    key_actions = commands.get(key)
    # print(f"commands '{commands}'")
    if not key_actions:
      return
    
    # print(f"key_actions '{key_actions}'")
    
    current_action = key_actions.get(key_state, {})
    # print(f"current_action '{current_action}'")
    
    if current_action:
      save_variable_commands = current_action.get("save_vars", [])
      # print(f"save_variable_commands '{save_variable_commands}'")
      
      for save_variable_command in save_variable_commands:
        # print(f"save_variable_command '{save_variable_command}'")
        # print(f"self.listening_variables '{self.listening_variables}'")
        
        if save_variable_command in self.listening_variables:
          
          saving_var = self.listening_variables.get(save_variable_command, None)
          
          if saving_var:
            self._logger.info(f"Saving value '{saving_var}' to variable '{save_variable_command}'.")
            self._settings.set(["profiles", active_profile, "variables", save_variable_command], saving_var)
            # self._settings.save()
            del self.listening_variables[save_variable_command]
          else:
            self._logger.info(f"Found nothing to save to variable '{save_variable_command}'.")
            del self.listening_variables[save_variable_command]
                  
      # handle if listening variables
      if self.listening_variables:
        self._logger.info(f"Listening for variables {self.listening_variables.keys()}.")
        key_values = key_actions.get("variable_values", None)
        
        if key_values:
          for variable in self.listening_variables:
            variable_value = key_values.get(variable)
            if variable_value:
              self._logger.info(f"Found variable value for key '{key}'. Setting variable '{variable}' as value '{variable_value}'.")
              self.listening_variables[variable] = variable_value
          
        return # if we're listening for variables, don't do anything else
        
      listen_variable_commands = current_action.get("listen_vars", [])
      for listen_variable_command in listen_variable_commands:
        self._logger.info(f"Started listening for variable '{listen_variable_command}'.")
        self.listening_variables[listen_variable_command] = None
      
      printer_commands = current_action.get("printer", [])
      for printer_command in printer_commands:
        subbed_command = self.variable_sub(printer_command)
        self._logger.info(f"Found printer command for key '{key}'. Sending '{subbed_command}'")
        self._printer.commands(subbed_command)
        
      logger_command = current_action.get("logger", False)
      if logger_command:
        self._logger.info(f"*---- Found logger command for key '{key}'. ----*")
        self._logger.info(f"Current Key Detection Binding '{self._settings.get(['key_discovery'])}'")
        self._logger.info(f"Current Setting for variables: {self._settings.get(['profiles', active_profile, 'variables'])}")
        self._logger.info(f"Current Setting for commands: {commands}")
        self._logger.info(f"Logging value of keyboard.")
        i = 0
        for row in self._settings.get(['profiles', active_profile, 'keyboard', 'rows']):
          self._logger.info(f"Current Setting for {i}: {row['keys']}")
          i = i + 1
        


  ##~~ StartupPlugin mixin
  
  def on_after_startup(self):
    self._logger.info("Hello USB!")
    self.key_status = dict()
    self.key_discovery = {}
    self.last_key_pressed = None
    self.listening_variables = dict()
    self._settings.set(["key_discovery"], {})
    
    eventManager().subscribe("plugin_usb_keyboard_key_event", self._key_event)
    self.listener = keyboard.Listener(on_press=on_press,on_release=on_release,suppress=False)
    self.listener.start()

  ##~~ SettingsPlugin mixin

  def get_settings_defaults(self):
    # put your plugin's default settings here
    return dict(
      active_profile="default",
      
      profiles={
        "default":{
          "commands":{
            # "Key.ctrl":{"pressed":{"printer":["M117 Howdy!"]}, "released":{"printer":["M117 Bye!"]}},
            
            "0":{"pressed":{"printer":["G28 X Y"]}, "variable_values":{"distance":"0.1", "bed":"50", "hotend":"200"}},  # homing x, y
            ".":{"pressed":{"listen_vars":["distance"]}, "released":{"save_vars":["distance"]}},  # making this my variable modifier
            "\\x03":{"pressed":{"printer":["G28 Z"]}}, # homing z
            
            "1":{"pressed":{"printer":["G0 X10 Y10"]}, "variable_values":{"distance":"1", "bed":"60", "hotend":"210"}},  # front left corner, 10x10 in
            "2":{"pressed":{"printer":["G0 Y-<distance>"]}, "variable_values":{"distance":"10"}},  # move south
            "3":{"pressed":{"printer":["G0 X290 Y10"]}, "variable_values":{"distance":"100"}},  # front right corner, 10x10 in
            "4":{"pressed":{"printer":["G0 X-<distance>"]}},  # move west
            "5":{"pressed":{"printer":["G0 X150 Y150"]}},  # center
            "6":{"pressed":{"printer":["G0 X+<distance>"]}},  # move east
            "7":{"pressed":{"printer":["G0 X10 Y290"]}},  # rear left corner, 10x10 in
            "8":{"pressed":{"printer":["G0 Y+<distance>"]}},  # move north
            "9":{"pressed":{"printer":["G0 X290 Y290"]}},  # rear right corner, 10x10 in
            
            "+":{"pressed":{"printer":["G0 Z-<distance>"]}},  # move down
            "-":{"pressed":{"printer":["G0 Z+<distance>"]}},  # move up
            
            
            "tab":{"pressed":{"listen_vars":["bed","hotend"]}, "released":{"save_vars":["bed","hotend"]}},  # set temperatures for hotend and bed
            "=":{"pressed":{"printer":["M104 S<hotend>","M140 S<bed>"]}},  # rear right corner, 10x10 in
            "esc":{"pressed":{"logger":True}},
          },
          "keyboard":{
            "rows":[
              {"keys":["esc", None, "tab", "="]},
              {"keys":[None, "/", "*", "backspace"]},
              {"keys":["7", "8", "9", "-"]},
              {"keys":["4", "5", "6", "+"]},
              {"keys":["1", "2", "3", None]},
              {"keys":[None, "0", ".", "\\x03"]}
            ]
          },
          "variables":{
            "distance":"1",
            "bed":"60",
            "hotend":"210"
          }
        }
      }
    )
    
    
  ##~~ SimpleApi mixin
  
  def get_api_commands(self):
          return dict(
              key_discovery=["row", "key"]
          )

  def on_api_command(self, command, data):      
      if command == "key_discovery":
        self._logger.info(f"key_discovery called, row is {data['row']}, key is {data['key']}")
        self.key_discovery = data

  def on_api_get(self, request):
      return 'f{"last_key_pressed"="{self.last_key_pressed}"}'

  ##~~ AssetPlugin mixin

  def get_assets(self):
    # Define your plugin's asset files to automatically include in the
    # core UI here.
    return dict(
      js=["js/usb_keyboard.js"],
      css=["css/usb_keyboard.css"],
      # less=["less/usb_keyboard.less"]
    )

  ##~~ TemplatePlugin mixin
  
  def get_template_configs(self):
    return [
      # dict(type="navbar", custom_bindings=False),
      # dict(type="settings", custom_bindings=False)
    ]

  ##~~ Softwareupdate hook

  def get_update_information(self):
    # Define the configuration for your plugin to use with the Software Update
    # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
    # for details.
    return dict(
      usb_keyboard=dict(
        displayName="Usb_keyboard Plugin",
        displayVersion=self._plugin_version,

        # version check: github repository
        type="github_release",
        user="barrettford",
        repo="OctoPrint-Usb_keyboard",
        current=self._plugin_version,

        # update method: pip
        pip="https://github.com/barrettford/OctoPrint-Usb_keyboard/archive/{target_version}.zip"
      )
    )
    
  


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "USB Keyboard Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def register_custom_events(*args, **kwargs):
  print("Registering event...")
  return ["key_event"]

def __plugin_load__():
  plugin = Usb_keyboardPlugin()
  
  global __plugin_implementation__
  __plugin_implementation__ = plugin

  global __plugin_hooks__
  __plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": plugin.get_update_information,
    "octoprint.events.register_custom_events": register_custom_events
  }
