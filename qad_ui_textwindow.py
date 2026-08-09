# -*- coding: utf-8 -*-
# QGIS: 4.0.0
# Qt: 6 / PyQt6 6.11.0
# Modificado em: 2026-08-09

"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire la finestra testuale
 
                              -------------------
        begin                : 2014-09-21
        copyright            : 
        email                : 
        developers           : 
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

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtWidgets import QSizePolicy

class Ui_QadTextWindow(object):
    def setupUi(self, QadTextWindow):
        QadTextWindow.setObjectName("QadTextWindow")
        QadTextWindow.resize(642, 193)
        
        # Destrava completamente os limites de tamanho mínimo e máximo
        QadTextWindow.setMinimumSize(QtCore.QSize(0, 0))
        QadTextWindow.setMaximumSize(QtCore.QSize(524287, 524287))
        
        # Força a política de tamanho a ignorar restrições rígidas
        QadTextWindow.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self.dockWidgetContents = QtWidgets.QWidget(QadTextWindow)
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        
        QadTextWindow.setWidget(self.dockWidgetContents)

        self.retranslateUi(QadTextWindow)
        QtCore.QMetaObject.connectSlotsByName(QadTextWindow)

    def retranslateUi(self, QadTextWindow):
        _translate = QtCore.QCoreApplication.translate
        QadTextWindow.setWindowTitle(_translate("QadTextWindow", "QAD Text Window"))


class Ui_QadCmdSuggestWindow(object):
    def setupUi(self, QadCmdSuggestWindow):
        QadCmdSuggestWindow.setObjectName("QadCmdSuggestWindow")
        QadCmdSuggestWindow.resize(200, 100)
        QadCmdSuggestWindow.setMinimumSize(QtCore.QSize(0, 0))
        
        self.vboxlayout = QtWidgets.QVBoxLayout(QadCmdSuggestWindow)
        self.vboxlayout.setContentsMargins(0, 0, 0, 0)
        self.vboxlayout.setSpacing(0)
        self.vboxlayout.setObjectName("vboxlayout")

        self.retranslateUi(QadCmdSuggestWindow)
        QtCore.QMetaObject.connectSlotsByName(QadCmdSuggestWindow)

    def retranslateUi(self, QadCmdSuggestWindow):
        _translate = QtCore.QCoreApplication.translate
        QadCmdSuggestWindow.setWindowTitle(_translate("QadCmdSuggestWindow", "Command Suggest"))
        