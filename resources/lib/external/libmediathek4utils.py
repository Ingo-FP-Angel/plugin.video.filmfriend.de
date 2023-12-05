# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

temp = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'temp')
dict = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'dict.py')



def log(msg):
	xbmc.log(msg)

def getTranslation(id):
	return xbmcaddon.Addon().getLocalizedString(id)
			
def pathUserdata(path):
	special = xbmcaddon.Addon().getAddonInfo('profile')+path
	special = special.replace('//','/').replace('special:/','special://')
	return special
	
def pathAddon(path):
	special = xbmc.validatePath(xbmcaddon.Addon().getAddonInfo('path').replace('\\','/')+path.replace('\\','/'))
	special = special.replace('//','/').replace('special:/','special://')
	return special
	
def f_open(path):
	try:
		f = xbmcvfs.File(path)
		result = f.read()
	except: pass
	finally:
		f.close()
	return result

def f_write(path,data):
	try:
		#f_mkdir(path)
		f = xbmcvfs.File(path, 'w')
		result = f.write(data)
	except: pass
	finally:
		f.close()
	return True

def f_remove(path):
	return xbmcvfs.delete(path)
	
def f_exists(path):
	exists = xbmcvfs.exists(path)
	if exists == 0:
		return False
	elif exists == False:
		return False
	else:
		return True
	
def f_mkdir(path):
	return xbmcvfs.mkdir(path)

def setSetting(k,v):
	return xbmcplugin.setSetting(int(sys.argv[1]), k, v)
	
def getSetting(k):
	return xbmcplugin.getSetting(int(sys.argv[1]), id=k)
def executeJSONRPC(cmd):
	xbmc.executeJSONRPC(cmd)
def getISO6391():
	return xbmc.getLanguage(xbmc.ISO_639_1) 

def displayMsg(a,b):
	xbmcgui.Dialog().notification(a,b)
	