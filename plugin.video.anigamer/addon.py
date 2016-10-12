#! /usr/bin/python
# coding=UTF-8

# anigamer player
# author: YWJamesLin

import os
import sys

import xbmcaddon
import xbmcplugin
import xbmcgui

import re

import requests
import pickle
from bs4 import BeautifulSoup as BS
from urlparse import parse_qsl

# Parse plugin metadata
__url__ = sys.argv[0]
__handle__ = int (sys.argv[1])

# Check temp dir. exists
tempDir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
if not os.path.isdir (tempDir) :
    os.makedirs (tempDir)

# Captcha code input dialog
class CaptchaInputDialog (xbmcgui.WindowDialog) :
    def __init__ (self, captchaPath) :
        self.img = xbmcgui.ControlImage (0, 0, 300, 100, captchaPath)
        self.addControl (self.img)
        self.kbd = xbmc.Keyboard ()

    def __del__ (self) :
        self.removeControl (self.img)

    # show dialog to input and get inputed captcha code
    def get (self) :
        self.show ()
        self.kbd.doModal ()
        if (self.kbd.isConfirmed ()) :
            text = self.kbd.getText ()
            self.close ()
            return text
        self.close ()
        return False

# Class to handle bahamut login, animate data and play video
class GamerAction () :
    def __init__(self) :
        self.this_addon = xbmcaddon.Addon ()
        self.authSite = 'https://user.gamer.com.tw'
        self.animeSite = 'http://ani.gamer.com.tw'

    # Check whether logined or not
    def check_login (self) :
        if os.path.isfile (tempDir + '/cookie') :
            with open (tempDir + '/cookie', 'r') as f :

                # Fetch saved cookie and session info
                cookies = requests.utils.cookiejar_from_dict (pickle.load (f))
                self.sessionAgent = requests.session ()
                self.sessionAgent.cookies = cookies
                f.close ()

                # Check this session
                result = self.sessionAgent.get (self.authSite + '/login.php', allow_redirects = False)
                if result.status_code == 302 :
                    return True
                else :
                    return False
        else :
            return False

    # Login to Bahamut
    def login (self) :
        # get captcha image content
        self.sessionAgent = requests.session ()
        result = self.sessionAgent.get (self.authSite + '/login.php')
        soup = BS (result.content.decode ('utf-8'), 'html.parser')
        imagesrc = soup.find ('img', { 'id' : 'captchaImg' }) ['src']
        result = self.sessionAgent.get (self.authSite + '/' + imagesrc)

        # save captcha image
        self.fptr = open (tempDir + '/captcha.jpg', 'w+b')
        self.fptr.write (result.content)
        self.fptr.close ()

        # get captcha input string
        dialog = CaptchaInputDialog (tempDir + '/captcha.jpg')
        captchaCode = dialog.get () or ""
        del dialog

        # combine userData and captcha code to on-post data
        data = {
                'onlogin' : '0',
                'getFrom' : 'http://www.gamer.com.tw',
                'uidh' : self.this_addon.getSetting ('username'),
                'passwdh' : self.this_addon.getSetting ('password'),
                'kpwd' : captchaCode,
                'saveid' : 'F',
                'autoLogin' : 'T'
                }

        # Post Data and save session
        result = self.sessionAgent.post (self.authSite + '/doLogin.php', data)
        with open (tempDir + '/cookie', 'w+') as f :
            pickle.dump (requests.utils.dict_from_cookiejar (self.sessionAgent.cookies), f)
            f.close ()

    # show main menu
    def list_main (self) :
        __language__ = self.this_addon.getLocalizedString

        thisList = []

        all_item = xbmcgui.ListItem (label = __language__ (33001))
        url = '{0}?action=list_all&page=1'.format (__url__)
        thisList.append ((url, all_item, True))

        favor_item = xbmcgui.ListItem (label = __language__ (33002))
        url = '{0}?action=list_favor'.format (__url__)
        thisList.append ((url, favor_item, True))

        xbmcplugin.addDirectoryItems (__handle__, thisList, len (thisList))
        xbmcplugin.endOfDirectory (__handle__)

    # list all animes separated by page
    def list_all (self, page) :
        __language__ = self.this_addon.getLocalizedString

        thisList = []

        result = self.sessionAgent.get (self.animeSite + '/animeList.php', params = { 'page' : page, 'c' : '0','sort' : '0' })
        soup = BS (result.content.decode ('utf-8'), 'html.parser')
        anime_list = soup.find ('ul', {'class':'anime_list'})


        # create anime list
        for anime_item in anime_list.find_all ('li') :
            nameBlock = anime_item.find ('div', { 'class' : 'info' })
            name = nameBlock.b.text
            ref = anime_item.a ['href']
            sn = re.sub (r"a.+sn=", "", ref)
            list_item = xbmcgui.ListItem (label = name)
            url = "{0}?action=anime_huei&sn={1}".format (__url__, sn)
            thisList.append ((url, list_item, True))

        # create nextpage item
        nextpage_item = xbmcgui.ListItem (label = __language__ (33011))
        url = "{0}?action=list_all&page={1}".format (__url__, int (page) + 1)
        thisList.append ((url, nextpage_item, True))

        xbmcplugin.addDirectoryItems (__handle__, thisList, len (thisList))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    # list favorite animes
    def list_favor (self) :
        result = self.sessionAgent.get (self.animeSite + '/mygather.php')
        soup = BS (result.content.decode ('utf-8'), 'html.parser')
        anime_list = soup.find ('ul', { 'class' : 'anime_list' })

        thisList = []

        # create anime list
        for anime_item in anime_list.find_all ('li') :
            nameBlock = anime_item.find ('div', { 'class' : 'info' })
            name = nameBlock.b.text
            ref = anime_item.a ['href']
            sn = re.sub (r"a.+sn=", "", ref)
            list_item = xbmcgui.ListItem (label = name)
            url = "{0}?action=anime_huei&sn={1}".format (__url__, sn)
            thisList.append ((url, list_item, True))

        xbmcplugin.addDirectoryItems (__handle__, thisList, len (thisList))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    # list vol.
    def anime_huei (self, sn) :
        result = self.sessionAgent.get (self.animeSite + '/animeRef.php?sn=' + sn)
        soup = BS (result.content.decode ('utf-8'), 'html.parser')

        # get anime title
        title = soup.head.title.text
        title = re.sub(r"(\[[0-9]+\])? - .+", "", title)

        anime_list = soup.find ('ul', { 'id' : 'vul0_000' })
        thisList = []
        # handle if has no vol. list
        if anime_list is None :
            singleResult = self.sessionAgent.get (self.animeSite + '/animeRef.php?sn=' + sn, allow_redirects = False)
            newsn = singleResult.headers ['Location']
            newsn = re.sub (r".+\?sn=", "", newsn)
            list_item = xbmcgui.ListItem (label = title)
            url = "{0}?action=play&sn={1}".format (__url__, newsn)
            thisList.append ((url, list_item, False))
        # create vol. list
        else :
            for anime_item in anime_list.find_all ('li') :
                ref = anime_item.a ['href']
                sn = re.sub (r"\?sn=", "", ref)
                name = title + " " + anime_item.a.text
                list_item = xbmcgui.ListItem (label = name)
                url = "{0}?action=play&sn={1}".format (__url__, sn)
                thisList.append ((url, list_item, False))
        xbmcplugin.addDirectoryItems (__handle__, thisList, len (thisList))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    # create video link and play on kodi
    def play (self, sn) :
        result = self.sessionAgent.get (self.animeSite + '/ajax/getdeviceid.php')
        jsonData = result.json ()
        deviceID = jsonData ['deviceid']

        result = self.sessionAgent.get (self.animeSite + '/ajax/m3u8.php?sn=' + sn + '&device=' + deviceID)
        jsonData = result.json ()
        src = "https:" + jsonData ['src']

        result = self.sessionAgent.get (src)
        spstr = result.text.split ()
        newsrc = re.sub (r"\/index.+", "", src)
        xbmc.Player (xbmc.PLAYER_CORE_MPLAYER).play (newsrc + '/' + spstr[-1])

def router (paramstring, action):
    if action.check_login () == False :
        action.login ()
    if action.check_login () == False :
        quit ()
    params = dict (parse_qsl (paramstring[1:]))
    if params :
        if params ['action'] == 'list_all' :
            action.list_all (params ['page'])
        elif params ['action'] == 'list_favor' :
            action.list_favor ()
        elif params ['action'] == 'anime_huei' :
            action.anime_huei (params['sn'])
        elif params ['action'] == 'play' :
            action.play (params['sn'])
    else :
        action.list_main ()

## Main
action = GamerAction ()
if __name__ == '__main__' :
    router (sys.argv[2], action)
