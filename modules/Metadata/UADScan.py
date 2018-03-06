import os
import re
import sys
import subprocess

__author__ = "Alec Hussey"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "UAD"

DEFAULTCONF = {
	"ENABLED": True,
	"vstk_home": "/opt/vstk",
	"cmdline": []
}

def check(conf=DEFAULTCONF):
	if not conf['ENABLED']:
		return False
	if not os.path.isdir(conf['vstk_home']):
		return False
	return True

def scan(filelist, conf=DEFAULTCONF):
	results = []
	command = [os.path.join(conf['vstk_home'], "bin/uad"), "-k", "-t", multiscanner.write_dir]

	for input_file in filelist:
		command2 = command[:]
		command2.append(input_file)

		try:
			output = subprocess.check_output(command2)
			output = output.decode("utf-8", errors="replace")
		except subprocess.CalledProcessError as error:
			return None

		# find and submit expanded files for scanning
		components = re.findall("^(\d+): Tmpfile: (.+)$", output, re.MULTILINE)

		for item in components:
			# skip base level items to avoid rescanning files already expanded
			# this happens when passing in a component to a new instance of UAD
			if int(item[0]) == 0:
				continue

			try:
				multiscanner.scan_file(item[1], input_file)
			except:
				pass

		results += re.findall("^0: Name: (.+)\n^\d+: Type: (.+)$", output, re.MULTILINE)

	metadata = {
		"Type": TYPE,
		"Name": NAME
	}

	return (results, metadata)
