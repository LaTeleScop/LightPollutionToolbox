# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BioDispersal
                                 A QGIS plugin
 Computes ecological continuities based on environments permeability
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2018-04-12
        git sha              : $Format:%H$
        copyright            : (C) 2018 by IRSTEA
        email                : mathieu.chailloux@irstea.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from .qgis_lib_mc import utils
#import helps
from PyQt5.QtCore import QUrl, QFile, QIODevice, QTextStream
from PyQt5.QtGui import QTextDocument

class TabItem:

    def __init__(self,idx,name,helpFile):
        self.idx = idx
        self.name = name
        self.descr = "TODO"
        self.helpFile = helpFile
        
    def setDescr(self,descr):
        self.descr = descr

    def getHelpFile(self):
        plugin_dir = os.path.dirname(__file__)
        help_dir = os.path.join(plugin_dir,"help")
        helpFile = os.path.join(help_dir,self.helpFile + "-" + utils.curr_language + ".html")
        return helpFile
        
radianceTabItem = TabItem(0,"Radiance","radianceHelp")
blueTabItem = TabItem(1,"Blue","blueHelp")
logTabItem = TabItem(2,"Log","logHelp")

class TabConnector:
    
    def __init__(self,dlg):
        self.tabs = [radianceTabItem,
                     blueTabItem,
                     logTabItem]
        self.dlg = dlg
        self.curr_tab = 0
        
    def initGui(self):
        self.dlg.textShortHelp.setOpenLinks(True)
        self.loadNTab(0)
        
    def loadNTab(self,n):
        print("loadNTab")
        utils.debug("[loadNTab] " + str(n))
        nb_tabs = len(self.tabs)
        self.curr_tab = n
        if n >= nb_tabs:
            utils.internal_error("[loadNTab] loading " + str(n) + " tab but nb_tabs = " + str(nb_tabs))
        else:
            self.loadHelpFile()
            #utils.debug("source : " + str(self.dlg.textShortHelp.source()))

    def loadHelpFile(self):
        tabItem = self.tabs[self.curr_tab]
        helpFile = tabItem.getHelpFile()
        utils.debug("Help file = " + str(helpFile))
        utils.checkFileExists(helpFile)
        with open(helpFile) as f:
            msg = f.read()
        self.dlg.textShortHelp.setHtml(msg)
        
            
    def connectComponents(self):
        self.dlg.tabWidget.currentChanged.connect(self.loadNTab)
            
