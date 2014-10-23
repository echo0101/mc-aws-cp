# Based off of https://github.com/esheffield/MCRcon/blob/master/minecraft.py

import argparse
import mcrcon
import sys

parser = argparse.ArgumentParser(description = 'Minecraft RCON Interface')
parser.add_argument('-H', '--host', help = 'Minecraft Server Address', default = 'localhost')
parser.add_argument('-p', '--port', help = 'RCON Listening Port', default = 25575, type = int)
parser.add_argument('-P', '--password', help = 'RCON Server Password', required = True)
parser.add_argument('-c', '--command', help = 'Command to Send, if Ommitted, enter Interactive Mode', default = None, dest = 'command')

RCON = None

def _init_rcon(host, port, password):
  global RCON
  RCON = mcrcon.MCRcon(host, port, password)
  
def _command_loop():
  try:
    while True:
      line = raw_input('[Rcon] ')
      print _process_command(line)
  except KeyboardInterrupt, e:
    print '^C... mannnnnn' # Inspired by Flippeh's Minecraft Multiplexer
    
def _process_command(command):
  global RCON
  return RCON.send(command)
  
if __name__ == '__main__':
  args = parser.parse_args()
  
  try:
    _init_rcon(args.host, args.port, args.password)
  except Exception,e:
    print >> sys.stderr, 'Unable to connect to RCON server, please check host, port, and password'
    sys.exit(1)
    
  if args.command is None:
    _command_loop()
  else:
    print _process_command(args.command)
