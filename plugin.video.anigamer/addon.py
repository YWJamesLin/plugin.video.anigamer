#! /usr/bin/python
# plugin.video.anigamer
# Author: YWJamesLin

import os
import sys
from datetime import datetime
import time
import math

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

xbmcplugin.setContent (__handle__,'movies')

# Check temp dir. exists

# Class to handle bahamut login session
class GamerSession () :
    animeEndpointBase = 'https://ani.gamer.com.tw'
    gamerEndpointBase = 'https://www.gamer.com.tw'

    thisAddon = None
    headers = None
    updateSessionHeaders = None
    xhrHeaders = None
    storageDir = None
    sessionAgent = None
    requireAuthActionGroup = [
        'list_favor',
        'play',
        'queue',
        'add_to_favorite',
        'remove_from_favorite',
    ]

    def __init__(self) :
        self.thisAddon = xbmcaddon.Addon ()

        # Create cookie storage directory
        self.headers = {
            'user-agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'origin' : self.animeEndpointBase
        }
        self.updateSessionHeaders = {
            'user-agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'referer' : self.gamerEndpointBase,
        }
        self.xhrHeaders = {
            'user-agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'origin' : self.animeEndpointBase,
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.storageDir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
        if not os.path.isdir (self.storageDir) :
            os.makedirs (self.storageDir)
        self.sessionAgent = requests.session ()

    def requireAuth (self, action) :
        return action in self.requireAuthActionGroup

    # Check whether logined or not
    def refreshSession (self) :
        if os.path.isfile (self.storageDir + '/cookie') :
            with open (self.storageDir + '/cookie', 'r') as handle :
                # Fetch saved session info
                cookies = requests.utils.cookiejar_from_dict (pickle.load (handle))
                self.sessionAgent.cookies = cookies
                handle.close ()

            t = int(math.floor(((datetime.today()-datetime.fromtimestamp(0)).total_seconds()) * 1000 + 1))
            self.sessionAgent.get (self.gamerEndpointBase + "/ajax/notify.php?a=1&time={0}".format (t), headers = self.updateSessionHeaders)
            with open (self.storageDir + '/cookie', 'w+') as handle :
                pickle.dump (requests.utils.dict_from_cookiejar (self.sessionAgent.cookies), handle)
                handle.close ()

            return True
        else :
            return False

    # show main menu
    def mainMenu (self) :
        __language__ = self.thisAddon.getLocalizedString

        menuItems = []

        allAnimes = xbmcgui.ListItem (label = __language__ (33001))
        url = '{0}?action=list_all&page=1'.format (__url__)
        menuItems.append ((url, allAnimes, True))

        favoriteAnimes = xbmcgui.ListItem (label = __language__ (33002))
        url = '{0}?action=list_favor&page=1'.format (__url__)
        menuItems.append ((url, favoriteAnimes, True))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.endOfDirectory (__handle__)

    # List all animes separated by page
    def allAnimes (self, page) :
        __language__ = self.thisAddon.getLocalizedString

        menuItems = []

        result = self.sessionAgent.get (self.animeEndpointBase + '/animeList.php', params = { 'page' : page, 'c' : '0','sort' : '0' }, headers = self.headers)
        soup = BS (result.content.decode('utf-8'), 'html.parser')
        animeGroup = soup.find ('ul', {'class':'anime_list'})

        # create anime list
        for animeItem in animeGroup.find_all ('li') :
            imageBlock = animeItem.find ('div', { 'class' : 'pic lazyload' })
            nameBlock = animeItem.find ('div', { 'class' : 'info' })
            FavoriteBlock = animeItem.find ('div', { 'class' : 'order' })
            isFavoriteBlock = animeItem.find ('div', { 'class' : 'order yes' })

            if nameBlock is None:
                continue
            name = nameBlock.b.text
            imageLink = imageBlock['data-bg']
            sn = re.sub (r"a.+sn=", "", animeItem.a['href'])
            acgSnJS = FavoriteBlock['onclick']
            acgSnJS = re.sub (r"a.+\(", "", acgSnJS)
            acgSn = re.sub (r",.+", "", acgSnJS)
            menuItem = xbmcgui.ListItem (label = name)
            menuItem.setArt ({'thumb': imageLink})
            url = "{0}?action=anime_huei&sn={1}&link={2}".format (__url__, sn, imageLink.encode('utf-8'))
            if isFavoriteBlock is not None :
                removeFavoriteUrl = "{0}?action=remove_from_favorite&sn={1}&animeSn={2}".format (__url__, acgSn, sn)
                menuItem.addContextMenuItems([(__language__ (30002), 'RunPlugin({0})'.format(removeFavoriteUrl))])
            else :
                addToFavoriteUrl = "{0}?action=add_to_favorite&sn={1}&animeSn={2}".format (__url__, acgSn, sn)
                menuItem.addContextMenuItems([(__language__ (30001), 'RunPlugin({0})'.format(addToFavoriteUrl))])
            menuItems.append ((url, menuItem, True))

        # Add next page item
        nextPageItem = xbmcgui.ListItem (label = __language__ (30004))
        url = "{0}?action=list_all&page={1}".format (__url__, int (page) + 1)
        menuItems.append ((url, nextPageItem, True))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    # List favorite animes
    def favoriteAnimes (self, page) :
        __language__ = self.thisAddon.getLocalizedString

        menuItems = []

        result = self.sessionAgent.get (self.animeEndpointBase + '/mygather.php', params = { 'page' : page, 'c' : '0','sort' : '0' }, headers = self.headers)
        soup = BS (result.content.decode('utf-8'), 'html.parser')
        animeGroup = soup.find ('ul', { 'class' : 'anime_list' })

        # Create anime list
        if animeGroup is not None :
            for animeItem in animeGroup.find_all ('li') :
                imageBlock = animeItem.find ('div', { 'class' : 'pic lazyload' })
                nameBlock = animeItem.find ('div', { 'class' : 'info' })

                name = nameBlock.b.text
                imageLink = imageBlock['data-bg']
                sn = re.sub (r"a.+sn=", "", animeItem.a['href'])

                menuItem = xbmcgui.ListItem (label = name, iconImage = imageLink)
                menuItem.setArt ({'thumb': imageLink})
                url = "{0}?action=anime_huei&sn={1}&link={2}".format (__url__, sn, imageLink.encode('utf-8'))
                removeFavoriteUrl = "{0}?action=remove_from_favorite&sn={1}".format (__url__, sn)
                menuItem.addContextMenuItems([(__language__ (30002), 'RunPlugin({0})'.format(removeFavoriteUrl))])
                menuItems.append ((url, menuItem, True))

            # Create next page item
            nextPageItem = xbmcgui.ListItem (label = __language__ (30004))
            url = "{0}?action=list_favor&page={1}".format (__url__, int (page) + 1)
            menuItems.append ((url, nextPageItem, True))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    # List Volme volumes
    def animeHuei (self, sn, imageLink) :
        __language__ = self.thisAddon.getLocalizedString

        result = self.sessionAgent.get (self.animeEndpointBase + '/animeRef.php?sn=' + sn, headers = self.headers)
        soup = BS (result.content.decode('utf-8'), 'html.parser')

        # Get anime title
        title = re.sub(r"(\[[0-9]+\])? - .+", "", soup.head.title.text)

        menuItems = []

        sectionField = soup.find ('section', { 'class' : 'season' })
        if sectionField is None :
            result = self.sessionAgent.get (self.animeEndpointBase + '/animeRef.php?sn=' + sn, allow_redirects = False, headers = self.headers)
            newSn = re.sub (r".+\?sn=", "", result.headers['Location'])
            url = "{0}?action=play&sn={1}&name={2}".format (__url__, newSn, title.encode('utf-8'))
            queueUrl = "{0}?action=queue&sn={1}&name={2}".format (__url__, newSn, title.encode('utf-8'))
            menuItem = xbmcgui.ListItem (label = title, path = url)
            menuItem.setInfo ('video', {
                'title': title,
                'genre': 'Animation',
                'mediatype': 'video'
            })
            menuItem.setArt ({'thumb': imageLink})
            menuItem.addContextMenuItems([(__language__ (30003), 'RunPlugin({0})'.format (queueUrl))])
            menuItems.append ((url, menuItem, False))
        else :
            sectionGroup = sectionField.find_all ('ul')
            sectionLength = len (sectionGroup)
            if sectionLength is 1 :
                for section in sectionGroup :
                    for volumeItem in section.find_all ('li') :
                        sn = re.sub (r"\?sn=", "", volumeItem.a['href'])
                        name = "{0} {1}".format (title.encode('utf-8'), volumeItem.a.text)
                        url = "{0}?action=play&sn={1}&name={2}".format (__url__, sn, name)
                        queueUrl = "{0}?action=queue&sn={1}&name={2}".format (__url__, sn, name)
                        menuItem = xbmcgui.ListItem (label = name, path = url)

                        menuItem.setInfo ('video', {
                            'title': name,
                            'genre': 'Animation',
                            'mediatype': 'video'
                            })
                        menuItem.addContextMenuItems([(__language__ (30003), 'RunPlugin({0})'.format (queueUrl))])
                        menuItem.setArt ({'thumb': imageLink})
                        menuItems.append ((url, menuItem, False))
            else :
                for section in sectionGroup :
                    sectionNameField = section.previousSibling
                    sectionName = sectionNameField.text
                    for volumeItem in section.find_all ('li') :
                        sn = re.sub (r"\?sn=", "", volumeItem.a['href'])
                        name = "{0} {1} {2}".format (title.encode('utf-8'), sectionName.encode('utf-8'), volumeItem.a.text)
                        url = "{0}?action=play&sn={1}&name={2}".format (__url__, sn, name)
                        queueUrl = "{0}?action=queue&sn={1}&name={2}".format (__url__, sn, name)
                        menuItem = xbmcgui.ListItem (label = name, path = url)
                        menuItem.setInfo ('video', {
                            'title': name,
                            'genre': 'Animation',
                            'mediatype': 'video'
                        })
                        menuItem.addContextMenuItems([(__language__ (30003), 'RunPlugin({0})'.format (queueUrl))])
                        menuItem.setArt ({'thumb': imageLink})
                        menuItems.append ((url, menuItem, False))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    def addToFavorite (self, sn, animeSn) :
        thisHeaders = self.xhrHeaders.copy ()
        thisHeaders.update ({
            'Referer' : 'https://ani.gamer.com.tw/',
        })

        result = self.sessionAgent.get (self.animeEndpointBase + '/ajax/getCSRFToken.php?_=' + str(int(time.time())), headers = thisHeaders)
        token = result.text

        data = {
            's' : sn,
            'animeSn' : animeSn,
            'token' : token,
        }
        result = self.sessionAgent.post (self.animeEndpointBase + '/ajax/want2play.php', data, headers = thisHeaders)

        xbmc.executebuiltin('Container.Refresh')

    def removeFromFavorite (self, sn, animeSn) :
        thisHeaders = self.xhrHeaders.copy ()
        thisHeaders.update ({
            'Referer' : 'https://ani.gamer.com.tw/',
        })

        result = self.sessionAgent.get (self.animeEndpointBase + '/ajax/getCSRFToken.php?_=' + str(int(time.time())), headers = thisHeaders)
        token = result.text

        data = {
            's' : sn,
            'animeSn' : animeSn,
            'token' : token,
        }
        result = self.sessionAgent.post (self.animeEndpointBase + '/ajax/delgather.php', data, headers = thisHeaders)

        xbmc.executebuiltin('Container.Refresh')

    # create video link and play on kodi
    def play (self, sn, name) :
        result = self.sessionAgent.get (self.animeEndpointBase + '/ajax/getdeviceid.php', headers = self.headers)
        jsonData = result.json ()
        deviceID = jsonData['deviceid']

        self.sessionAgent.get (self.animeEndpointBase + '/ajax/unlock.php?ttl=0&sn=' + sn, headers = self.xhrHeaders)
        result = self.sessionAgent.get (self.animeEndpointBase + '/ajax/m3u8.php?sn=' + sn + '&device=' + deviceID, headers = self.headers)
        jsonData = result.json ()

        src = "https://" + re.sub(r"([a-zA-Z]+:)?//", "", jsonData ['src'])
        result = self.sessionAgent.get (src, headers = self.xhrHeaders)
        spstr = result.text.split ()
        endpoint = '{0}/{1}|Origin={2}'.format (re.sub (r"\/index.+", "", src), spstr[-1], self.animeEndpointBase)
        thisAnime = xbmcgui.ListItem (label = name)
        thisAnime.setInfo ('video', {'title': name, 'genre': 'Animation'})
        xbmc.Player ().play (endpoint , thisAnime)

    def queue (self, sn, name) :
        result = self.sessionAgent.get (self.animeEndpointBase + '/ajax/getdeviceid.php', headers = self.headers)
        jsonData = result.json ()
        deviceID = jsonData['deviceid']

        self.sessionAgent.get (self.animeEndpointBase + '/ajax/unlock.php?ttl=0&sn=' + sn, headers = self.xhrHeaders)
        result = self.sessionAgent.get (self.animeEndpointBase + '/ajax/m3u8.php?sn=' + sn + '&device=' + deviceID, headers = self.headers)
        jsonData = result.json ()
        src = "https://" + re.sub(r"([a-zA-Z]+:)?//", "", jsonData ['src'])

        result = self.sessionAgent.get (src)
        spstr = result.text.split ()
        endpoint = '{0}/{1}|Origin={2}'.format (re.sub (r"\/index.+", "", src), spstr[-1], self.animeEndpointBase)
        thisAnime = xbmcgui.ListItem (label = name, path = endpoint)
        thisAnime.setInfo ('video', {'title': name, 'genre': 'Animation'})
        xbmc.PlayList(1).add (endpoint, thisAnime)

def router (paramString, session):
    # Check this session is available
    params = dict (parse_qsl (paramString[1:]))

    # Check Action
    if params :
        action = params['action']
        if session.refreshSession () is False :
            quit ()
        if action == 'list_all' :
            session.allAnimes (params ['page'])
        elif action == 'list_favor' :
            session.favoriteAnimes (params ['page'])
        elif action == 'anime_huei' :
            session.animeHuei (params ['sn'], params ['link'].decode('utf-8'))
        elif action == 'add_to_favorite' :
            session.addToFavorite (params['sn'], params['animeSn'])
        elif action == 'remove_from_favorite' :
            session.removeFromFavorite (params['sn'], params['animeSn'])
        elif action == 'play' :
            session.play (params['sn'], params['name'])
        elif action == 'queue' :
            session.queue (params['sn'], params['name'])
    else :
        session.mainMenu ()

## Main
session = GamerSession ()

if __name__ == '__main__' :
    router (sys.argv[2], session)
