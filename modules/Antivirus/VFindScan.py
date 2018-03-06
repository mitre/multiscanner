import os
import re
import sys
import subprocess

__author__ = "Alec Hussey"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "VFind"

DEFAULTCONF = {
	"ENABLED": True,
	"vstk_home": "/opt/vstk",
	"uad_cmdline": [],
	"vfind_cmdline": []
}

def check(conf=DEFAULTCONF):
	if not conf['ENABLED']:
		return False
	if not os.path.isdir(conf['vstk_home']):
		return False
	return True

def scan(filelist, conf=DEFAULTCONF):
	results = []
	uad_command = [os.path.join(conf['vstk_home'], "bin/uad"), "-n", "-ssw"] + conf['uad_cmdline'] + filelist
	vfind_command = [os.path.join(conf['vstk_home'], "bin/vfind"), "-ssr"] + conf['vfind_cmdline']
	
	try:
		uad = subprocess.Popen(uad_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
		vfind = subprocess.Popen(vfind_command, stdin=uad.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
		output = vfind.communicate(timeout=21600)[0].decode("utf-8", errors="replace")
	except subprocess.CalledProcessError as error:
		return None
	
	results = re.findall("^##==>>>> VIRUS POSSIBLE IN FILE: \"(.+)\"\n##==>>>> VIRUS ID: (\w+ .+)", output, re.MULTILINE)
	
	vfind_version = ""
	try:
		vfind_version = re.search("^##==> VFind Version: (\d+), Release: (\d+), Patchlevel: (\d+) .+", output)
		vfind_version = "{}.{}.{}".format(
			vfind_version.group(1), 
			vfind_version.group(2), 
			vfind_version.group(3)
		)
	except:
		pass
	
	vdl_version = ""
	with open(os.path.join(conf['vstk_home'], "data/vfind/VERSION"), "r") as vdl_version_file:
		vdl_version = vdl_version_file.read().strip()
	
	metadata = {
		"Type": TYPE,
		"Name": NAME,
		"Program version": vfind_version,
		"Definition version": vdl_version
	}
	
	return (results, metadata)
