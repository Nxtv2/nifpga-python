import time
import platform
import os.path
#if typeerror. change 'w' to 'wb'
def pollHelper(fn,
               totalMSToWait=5000,
               sleepMSBetweenTries=5,
               exceptionMsg="Predicate failed to return True within the time limit"):
   """Runs some arbitrary function every so often (sleepBetweenTries) until it
   returns a non Falsy value, or we hit the time limit (totalTimeToWait)."""
   kMillisecondsPerSecond = 1000.0
   endtime = time.time() + totalMSToWait / kMillisecondsPerSecond
   while True:
      if fn():
         break
      elif (time.time() - endtime) > 0:
         raise AssertionError(exceptionMsg)
      else:
         time.sleep(sleepMSBetweenTries / kMillisecondsPerSecond)


if platform.system().lower() in ['windows']:
   import winreg as winreg
   kKeyName = 'SYSTEM\\CurrentControlSet\\Services\\nistreamk\\Config'
   kItemName = 'SkipLinkPathValidation'

   def _keyIsEmpty(key):
      """ True if a registry key has no values. """
      try:
         # throws WindowsError if there are no values
         winreg.EnumValue(key, 0)
      except WindowsError:
         return True
      return False

   def setLinkPathValidationOverride(value=True):
      """ Set the configuration time setting to override Link Path Validation.
      Setting this to True will disable link path validation.  Setting it to
      false will enable link path validation. """
      with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, kKeyName) as key:
         winreg.SetValueEx(key, kItemName, 0, winreg.REG_DWORD, value)

   def clearLinkPathValidationOverride():
      """ Clear the configuration option for link path validation override. """
      try:
         with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             kKeyName,
                             0,
                             winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, kItemName)
            empty = _keyIsEmpty(key)

         if empty:
            # The key is empty.  Attempt to delete it
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                os.path.dirname(kKeyName),
                                0,
                                winreg.KEY_ALL_ACCESS) as key:
               winreg.DeleteKey(key, os.path.basename(kKeyName))

      except WindowsError:
         pass

elif platform.system().lower() in ['linux', 'pharlap']:
   from configparser import ConfigParser

   kSectionName = 'NI-P2P'
   kItemName = 'SkipLinkPathValidation'

   iniPaths = {'linux': '/etc/natinst/nip2p/config.ini',
               'pharlap': 'c:/ni-rt.ini'}
   iniPath = iniPaths[platform.system().lower()]

   def setLinkPathValidationOverride(value=True):
      """ Set the configuration time setting to override Link Path Validation.
      Setting this to True will disable link path validation.  Setting it to
      false will enable link path validation. """

      parser = ConfigParser()
      parser.optionxform = str

      if os.path.exists(iniPath):
         parser.read(iniPath)
      if kSectionName not in parser.sections():
         parser.add_section(kSectionName)
      parser.set(kSectionName, kItemName, value)

      with open(iniPath, 'w') as f:
         parser.write(f)

   def clearLinkPathValidationOverride():
      """ Clear the configuration option for link path validation override. """

      if not os.path.exists(iniPath):
         # Configuration file isn't present
         return

      # Create a config parser that doesn't lowercase everything.
      parser = ConfigParser()
      parser.optionxform = str

      parser.read(iniPath)

      if kSectionName not in parser.sections():
         return
      parser.remove_option(kSectionName, kItemName)
      if not parser.items(kSectionName):
         # The section is empty
         parser.remove_section(kSectionName)

      with open(iniPath, 'w') as f:
         parser.write(f)

else:
   assert False, platform.system() + ' is unsupported'
