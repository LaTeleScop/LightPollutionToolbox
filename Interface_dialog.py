# -*- coding: utf-8 -*-
"""
/***************************************************************************
 InterfaceDialog
                                 A QGIS plugin
 Interface
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2023-03-08
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Interface
        email                : Interface
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

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from PyQt5.QtCore import QTranslator, qVersion, QCoreApplication
from .qgis_lib_mc import utils, qgsUtils, log, qgsTreatments, feedbacks, styles
from qgis.core import QgsApplication, QgsProcessingContext, QgsProject, QgsProcessing
from .algs import LightPollutionToolbox_provider
from . import controller
from . import tabs

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Interface_dialog_base.ui'))


class InterfaceDialog(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(InterfaceDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        
    def initConnectors(self):
        #global progressFeedback, paramsModel
        logConnector = log.LogConnector(self)
        logConnector.initGui()
        self.feedback =  feedbacks.ProgressFeedback(self)
        self.feedback.connectComponents()
        
        self.context = QgsProcessingContext()
        utils.print_func = self.txtLog.append
        
        self.controllerConnector = controller.ControllerConnector(self)
        self.tabConnector = tabs.TabConnector(self)
        self.tabConnector.initGui()
        self.tabConnector.connectComponents()
        
        self.langEn.clicked.connect(self.switchLangEn)
        self.langFr.clicked.connect(self.switchLangFr)
        if QgsApplication.locale() in ['fr','FR']:
            self.switchLangFr()
        else:
            self.switchLangEn()
        
    def initInterface(self):
        self.txtLog.clear()
        self.progressBar.setValue(0)

        self.tabWidget.setCurrentWidget(self.tabRadiance)
        self.tabWidgetVisibility.setCurrentWidget(self.tabMNS)
        
        
    def switchLangEn(self):
        self.switchLang("en")
        self.langEn.setChecked(True)
        self.langFr.setChecked(False)       
        
    def switchLangFr(self):
        self.switchLang("fr")
        self.langEn.setChecked(False)
        self.langFr.setChecked(True)
          
    def switchLang(self,lang):
        #assert(False)
        plugin_dir = os.path.dirname(__file__)
        lang_path = os.path.join(plugin_dir,'i18n','LightPollutionToolbox_' + lang + '.qm')
        if os.path.exists(lang_path):
            #assert(False)
            self.translator = QTranslator()
            self.translator.load(lang_path)
            if qVersion() > '4.3.3':
                #assert(False)
                QCoreApplication.installTranslator(self.translator)
            else:
                return
        else:
            raise QgsProcessingException("No translation file : " + str(en_path))
        self.retranslateUi(self)
        utils.curr_language = lang
        self.tabConnector.loadHelpFile()