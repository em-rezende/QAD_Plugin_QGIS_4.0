# -*- coding: utf-8 -*-
# QGIS: 4.0.0
# Qt: 6 / PyQt6 6.11.0
# Modificado em: 2026-09-06

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

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtCore import Qt, QTimer, QPoint, QRect
from qgis.PyQt.QtGui import QIcon, QColor, QTextCursor, QTextCharFormat, QFont, \
                        QFontMetrics, QStandardItemModel, QStandardItem
from qgis.PyQt.QtWidgets import QDockWidget, QListView, QAbstractItemView, QApplication, QWidget, QTextEdit, QMessageBox, QSizePolicy
from qgis.core import QgsPointXY, QgsSettings

import sys
import string
import difflib

from .qad_ui_textwindow import Ui_QadTextWindow, Ui_QadCmdSuggestWindow
from .qad_msg import QadMsg
from . import qad_utils
from .qad_snapper import str2snapTypeEnum, str2snapParams
from .qad_variables import QadVariables, QadINPUTSEARCHOPTIONSEnum


# ===============================================================================
# Compatibilidade Qt6 para QTextCursor
# ===============================================================================
if not hasattr(QTextCursor, 'End'):
    QTextCursor.End = QTextCursor.MoveOperation.End
    QTextCursor.Start = QTextCursor.MoveOperation.Start
    QTextCursor.Right = QTextCursor.MoveOperation.Right
    QTextCursor.Left = QTextCursor.MoveOperation.Left
    QTextCursor.WordLeft = QTextCursor.MoveOperation.WordLeft
    QTextCursor.WordRight = QTextCursor.MoveOperation.WordRight
    QTextCursor.StartOfBlock = QTextCursor.MoveOperation.StartOfBlock
    QTextCursor.EndOfBlock = QTextCursor.MoveOperation.EndOfBlock

if not hasattr(QTextCursor, 'MoveAnchor'):
    QTextCursor.MoveAnchor = QTextCursor.MoveMode.MoveAnchor
    QTextCursor.KeepAnchor = QTextCursor.MoveMode.KeepAnchor


# ===============================================================================
# QadInputTypeEnum class.
# ===============================================================================
class QadInputTypeEnum():
   NONE     = 0    # nessuno
   COMMAND  = 1    # nome di un comando
   POINT2D  = 2    # punto 
   POINT3D  = 4    # punto 
   KEYWORDS = 8    # una parola chiave
   STRING   = 16   # una stringa
   INT      = 32   # un numero intero
   LONG     = 64   # un numero intero
   FLOAT    = 128  # un numero reale
   BOOL     = 256  # un valore booleano
   ANGLE    = 512  # un valore reale in gradi


# ===============================================================================
# QadInputModeEnum class.
# ===============================================================================
class QadInputModeEnum():
   NONE         = 0
   NOT_NULL     = 1   # inserimento nullo non permesso
   NOT_ZERO     = 2   # valore zero non permesso 
   NOT_NEGATIVE = 4   # valore negativo non permesso 
   NOT_POSITIVE = 8   # valore positivo non permesso  

      
# ===============================================================================
# QadCmdOptionPos
# ===============================================================================
class QadCmdOptionPos():      
   def __init__(self, name = "", initialPos = 0, finalPos = 0):
      self.name = name
      self.initialPos = initialPos
      self.finalPos = finalPos
   
   def isSelected(self, pos):
      return True if pos >= self.initialPos and pos <= self.finalPos else False


# ===============================================================================
# QadTextWindow
# ===============================================================================
class QadTextWindow(QDockWidget, Ui_QadTextWindow):
   """This class"""
   
   def __init__(self, plugin):
      """The constructor."""

      QDockWidget.__init__(self, plugin.iface.mainWindow())
      
      # Inicializa primeiro para evitar erros de atributo em eventos
      self.plugin = plugin
      self.cmdSuggestWindow = None

      self.setupUi(self)
      
      # Cria um alias/ponteiro dinâmico caso o arquivo .ui defina o widget com outro nome
      if hasattr(self, 'lineEdit') and not hasattr(self, 'edit'):
         self.edit = self.lineEdit

      self.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
      
      # MODIFICAÇÃO: Remove restrições de tamanho mínimo
      self.setMinimumSize(0, 0)
      self.setMaximumSize(QtCore.QSize(16777215, 16777215))
      
      # MODIFICAÇÃO: Configura o widget interno sem restrições
      if hasattr(self, 'widget') and self.widget():
         self.widget().setMinimumSize(0, 0)
         self.widget().setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
      
      self.topLevelChanged['bool'].connect(self.onTopLevelChanged)

      # Restaura o título correto com a versão original do plugin
      title = self.windowTitle()
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + title + " - " + plugin.version())
      
      # Garante a compatibilidade das flags do DockWidget entre PyQt5 e PyQt6
      dock_features = 0
      if hasattr(QDockWidget, 'DockWidgetFeature'):
          dock_features = (
              QDockWidget.DockWidgetFeature.DockWidgetClosable | 
              QDockWidget.DockWidgetFeature.DockWidgetMovable | 
              QDockWidget.DockWidgetFeature.DockWidgetFloatable
          )
      else:
          dock_features = (
              QDockWidget.DockWidgetClosable | 
              QDockWidget.DockWidgetMovable | 
              QDockWidget.DockWidgetFloatable
          )
      self.setFeatures(dock_features)

   def minimumSizeHint(self):
      """Força o tamanho mínimo para zero, permitindo redução total."""
      return QtCore.QSize(0, 0)

   def onTopLevelChanged(self, floating):
      """Ajusta o comportamento de tamanho dinamicamente ao acoplar ou desacoplar."""
      if floating:
         self.setMinimumSize(0, 0)
         self.setMaximumSize(QtCore.QSize(16777215, 16777215))
         self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
      else:
         self.setMinimumSize(0, 0)
         self.setMaximumSize(QtCore.QSize(16777215, 16777215))
         if hasattr(self, 'widget') and self.widget():
            self.widget().setMinimumSize(0, 0)
            self.widget().setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
      
      self.resizeEdits()

   def __del__(self):
      """The destructor."""

      self.topLevelChanged['bool'].disconnect(self.onTopLevelChanged)
                  
      QDockWidget.__del__(self)

   def initGui(self):
      self.chronologyEdit = QadChronologyEdit(self)
      self.chronologyEdit.setObjectName("QadChronologyEdit")
      # Remove restrições de tamanho mínimo
      self.chronologyEdit.setMinimumSize(0, 0)
      self.chronologyEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
      
      self.edit = QadEdit(self, self.chronologyEdit)
      self.edit.setObjectName("QadTextEdit")
      
      # Remove restrições de tamanho mínimo
      self.edit.setMinimumSize(0, 0)
      # MODIFICAÇÃO: Fixa a altura da linha de comando em UMA LINHA
      self.edit.setFixedHeight(self.edit.getOptimalHeight())
      self.edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
      
      self.edit.displayPrompt(QadMsg.translate("QAD", "Command: "))
      
      # Creo la finestra per il suggerimento dei comandi
      # lista composta da elementi con:
      # <nome locale comando>, <nome inglese comando>, <icona>, <note>
      infoCmds = []
      for cmdName in self.getCommandNames():
         cmd = self.getCommandObj(cmdName[0])
         if cmd is not None:
            infoCmds.append([cmdName[0], cmd.getEnglishName(), cmd.getIcon(), cmd.getNote()])
            
      # Creo la finestra per il suggerimento delle variabili di ambiente
      # lista composta da elementi con:
      # <nome variabile>, "", <icona>, <note>
      infoVars = []
      icon = QIcon(":/plugins/qad/icons/variable.svg")
      for varName in QadVariables.getVarNames():
         var = QadVariables.getVariable(varName)
         infoVars.append([varName, "", icon, var.descr])
  
      self.cmdSuggestWindow = QadCmdSuggestWindow(self, self.edit, infoCmds, infoVars)
      self.cmdSuggestWindow.initGui()
      self.cmdSuggestWindow.show(False)
  
      self.refreshColors()
      
      # MODIFICAÇÃO IMPORTANTE: Força a atualização do tamanho mínimo após a inicialização
      # Isso resolve o problema de largura mínima que só desaparece após destacar/encaixar
      self.setMinimumSize(0, 0)
      if hasattr(self, 'widget') and self.widget():
          self.widget().setMinimumSize(0, 0)
          self.widget().setMaximumSize(QtCore.QSize(16777215, 16777215))
          self.widget().setMinimumWidth(0)
          self.widget().setMaximumWidth(16777215)
      
      # Força a atualização do layout
      QApplication.processEvents()
      self.resizeEdits()
      self.updateGeometry()

   # ============================================================================
   # writeDockWidgetSettings
   # ============================================================================
   def writeDockWidgetSettings(self):
      s = QgsSettings()
      s.setValue("qad/text_window_x", self.x())         
      s.setValue("qad/text_window_y", self.y())         
      s.setValue("qad/text_window_width", self.width())         
      s.setValue("qad/text_window_height", self.height())         
      s.setValue("qad/text_window_floating", self.isFloating())         
      
      # Salva o valor numérico (int) do Enum da área do Dock
      area = self.plugin.iface.mainWindow().dockWidgetArea(self)
      s.setValue("qad/text_window_area", int(area.value) if hasattr(area, 'value') else int(area)) 

   
   # ============================================================================
   # readDockWidgetSettings
   # ============================================================================
   def readDockWidgetSettings(self):
      s = QgsSettings()
      x = s.value("qad/text_window_x", 0, type=int)         
      y = s.value("qad/text_window_y", 0, type=int)         
      width = s.value("qad/text_window_width", 400, type=int)    
      height = s.value("qad/text_window_height", 400, type=int)         
      isFloating = s.value("qad/text_window_floating", False, type=bool)         
      
      # Lê o valor do registro e converte para o Enum seguro do Qt
      raw_area = s.value("qad/text_window_area", None)
      if raw_area is not None:
         try:
            dockWidgetArea = Qt.DockWidgetArea(int(raw_area))
         except (ValueError, TypeError):
            dockWidgetArea = Qt.DockWidgetArea.BottomDockWidgetArea
      else:
         dockWidgetArea = Qt.DockWidgetArea.BottomDockWidgetArea
               
      return isFloating, QRect(x, y, width, height), dockWidgetArea

   # ============================================================================
   # refreshColors
   # ============================================================================
   def refreshColors(self):
      if not hasattr(self, 'edit') or self.edit is None or not hasattr(self, 'chronologyEdit') or self.chronologyEdit is None:
         return

      hist_fore = QadVariables.get(QadMsg.translate("Environment variables", "CMDHISTORYFORECOLOR")) or "black"
      hist_back = QadVariables.get(QadMsg.translate("Environment variables", "CMDHISTORYBACKCOLOR")) or "lightgray"
      
      history_ForegroundColor = QColor(hist_fore)
      history_BackGroundColor = QColor(hist_back)
      self.chronologyEdit.set_Colors(history_ForegroundColor, history_BackGroundColor)

      cmd_fore = QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEFORECOLOR")) or "black"
      cmd_back = QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR")) or "white"
      
      foregroundColor = QColor(cmd_fore)
      backGroundColor = QColor(cmd_back)
      self.edit.set_Colors(foregroundColor, backGroundColor)

      opt_fore = QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEOPTCOLOR")) or "blue"
      opt_back = QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEOPTBACKCOLOR")) or "lightgray"
      opt_hl_back = QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEOPTHIGHLIGHTEDCOLOR")) or "gray"

      upperKeyWord_ForegroundColor = QColor(opt_fore)
      KeyWord_BackgroundColor = QColor(opt_back)
      highlightKeyWord_BackGroundColor = QColor(opt_hl_back)

      self.edit.set_keyWordColors(KeyWord_BackgroundColor, upperKeyWord_ForegroundColor, highlightKeyWord_BackGroundColor)
      
   def getDockWidgetArea(self):
      return self.parentWidget().dockWidgetArea(self)
                  
   def setFocus(self):
        # Correção robusta para evitar o AttributeError caso 'edit' não exista diretamente
        if hasattr(self, 'edit') and self.edit is not None:
            self.edit.setFocus()
        elif hasattr(self, 'lineEdit') and self.lineEdit is not None:
            self.lineEdit.setFocus()
        else:
            super().setFocus()
      
   def keyPressEvent(self, e):
      if hasattr(self, 'edit') and self.edit is not None:
         self.edit.keyPressEvent(e)
      else:
         super().keyPressEvent(e)

   def hideEvent(self, e):
      self.showCmdSuggestWindow(False)
      
   def toggleShow(self):
      if self.isVisible():
         self.hide()
      else:
         self.show()
   
   def showEvent(self, e):
      QDockWidget.showEvent(self, e)
      if hasattr(self, 'edit') and self.edit is not None:
          self.refreshColors()
      
      # MODIFICAÇÃO: Força a atualização do tamanho mínimo sempre que a janela é exibida
      self.setMinimumSize(0, 0)
      if hasattr(self, 'widget') and self.widget():
          self.widget().setMinimumSize(0, 0)
          self.widget().setMaximumSize(QtCore.QSize(16777215, 16777215))
          self.widget().setMinimumWidth(0)
          self.widget().setMaximumWidth(16777215)
      
      # MODIFICAÇÃO: Força a altura da linha de comando a ser fixa
      if hasattr(self, 'edit') and self.edit is not None:
          self.edit.setFixedHeight(self.edit.getOptimalHeight())
      
      QApplication.processEvents()
      self.resizeEdits()
      self.updateGeometry()
         
   def showMsg(self, msg, displayPromptAfterMsg = False, append = True):
      if hasattr(self, 'edit') and self.edit is not None:
         self.edit.showMsg(msg, displayPromptAfterMsg, append)

   def showInputMsg(self, inputMsg = None, inputType = QadInputTypeEnum.COMMAND, \
                    default = None, keyWords = "", inputMode = QadInputModeEnum.NONE):
      if hasattr(self, 'edit') and self.edit is not None:
         self.edit.showInputMsg(inputMsg, inputType, default, keyWords, inputMode)

   def showErr(self, err):
      if hasattr(self, 'edit') and self.edit is not None:
         self.edit.showErr(err)
         
   def showMsgOnChronologyEdit(self, msg):
      """Exibe mensagem no histórico."""
      if hasattr(self, 'chronologyEdit') and self.chronologyEdit is not None:
         self.chronologyEdit.insertText(msg)

   def isVisibleCmdSuggestWindow(self):
      if self.cmdSuggestWindow is None:
         return False
      return self.cmdSuggestWindow.isVisible()
   
   def showCmdSuggestWindow(self, mode = True, filter = ""):
      if self.cmdSuggestWindow is None:
         return
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      if inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST:
         if mode == True:
            if self.cmdSuggestWindow.setFilter(filter) == 0:
               self.cmdSuggestWindow.show(False)
               return
            
            dataHeight = self.cmdSuggestWindow.getDataHeight()
            if dataHeight > 0:
               self.cmdSuggestWindow.cmdNamesListView.setMinimumHeight(self.cmdSuggestWindow.cmdNamesListView.sizeHintForRow(0))
                        
            if self.isFloating():
               ptUp = self.edit.mapToGlobal(QPoint(0,0))
               spaceUp = ptUp.y() if ptUp.y() - dataHeight < 0 else dataHeight
                  
               ptDown = QPoint(ptUp.x(), ptUp.y() + self.edit.height())
               rect = QApplication.primaryScreen().geometry()
               spaceDown = rect.height() - ptDown.y() if ptDown.y() + dataHeight > rect.height() else dataHeight
      
               if spaceUp > spaceDown:
                  pt = QPoint(ptUp.x(), ptUp.y() - spaceUp)
                  dataHeight = spaceUp
               else:
                  pt = QPoint(ptDown.x(), ptDown.y())
                  dataHeight = spaceDown
            elif self.getDockWidgetArea() == Qt.DockWidgetArea.BottomDockWidgetArea:
               pt = self.edit.mapToGlobal(QPoint(0,0))
               if pt.y() - dataHeight < 0:
                  dataHeight = pt.y()
               pt.setY(pt.y() - dataHeight)
            elif self.getDockWidgetArea() == Qt.DockWidgetArea.TopDockWidgetArea:
               pt = self.edit.mapToGlobal(QPoint(0,0))
               pt.setY(pt.y() + self.edit.height())
               rect = QApplication.primaryScreen().geometry()
               if pt.y() + dataHeight > rect.height():
                  dataHeight = rect.height() - pt.y()
      
            if pt.x() < 0:
               pt.setX(0)
         
            self.cmdSuggestWindow.move(pt)
            self.cmdSuggestWindow.resize(200, dataHeight)
         
         self.cmdSuggestWindow.show(mode)
      else:
         self.cmdSuggestWindow.show(False)

  
   def showEvaluateMsg(self, msg = None, append = True):
      if hasattr(self, 'edit') and self.edit is not None:
         self.edit.showEvaluateMsg(msg, append)

   def getCurrMsg(self):
      if hasattr(self, 'edit') and self.edit is not None:
         return self.edit.getCurrMsg()
      return ""

   def updateHistory(self, command):
      if hasattr(self, 'edit') and self.edit is not None:
         return self.edit.updateHistory(command)
               
   def runCommand(self, cmd):
      self.plugin.runCommand(cmd)      
      
   def continueCommand(self, cmd):
      self.plugin.continueCommandFromTextWindow(cmd)      
      
   def abortCommand(self):
      self.plugin.abortCommand()      

   def clearCurrentObjsSelection(self):
      self.plugin.clearCurrentObjsSelection()

   def isValidCommand(self, cmd):
      return self.plugin.isValidCommand(cmd)

   def getCommandNames(self):
      return self.plugin.getCommandNames()

   def getCommandObj(self, cmdName):
      return self.plugin.getCommandObj(cmdName)

   def isValidEnvVariable(self, variable):
      return self.plugin.isValidEnvVariable(variable)

   def forceCommandMapToolSnapTypeOnce(self, snapType, snapParams = None):
      return self.plugin.forceCommandMapToolSnapTypeOnce(snapType, snapParams)     
   
   def forceCommandMapToolM2P(self):
      return self.plugin.forceCommandMapToolM2P()        

   def toggleOsMode(self):
      return self.plugin.toggleOsMode()

   def toggleOrthoMode(self):
      return self.plugin.toggleOrthoMode()      

   def togglePolarMode(self):
      return self.plugin.togglePolarMode()

   def toggleObjectSnapTracking(self):
      return self.plugin.toggleObjectSnapTracking()

   def getLastPoint(self):
      return self.plugin.lastPoint

   def setLastPoint(self, pt):
      return self.plugin.setLastPoint(pt)

   def getCurrenPointFromCommandMapTool(self):
      return self.plugin.getCurrenPointFromCommandMapTool()

   def resizeEdits(self):
      """Redimensiona os widgets internos baseado no tamanho disponível."""
      if not hasattr(self, 'edit') or not hasattr(self, 'chronologyEdit') or self.edit is None or self.chronologyEdit is None:
          return
              
      rect = self.rect()
      h = rect.height()
      w = rect.width()
      
      # MODIFICAÇÃO: Calcula a altura ideal para UMA LINHA de comando
      editHeight = self.edit.getOptimalHeight()  # Altura de uma única linha
      minChronologyHeight = 20
      
      # Espaço disponível para o histórico
      if self.isFloating():
          offsetY = 5  # Margem quando flutuante
      else:
          offsetY = 5  # Margem quando anexado
      
      availableHeight = h - offsetY
      
      # MODIFICAÇÃO: A linha de comando tem altura FIXA (uma linha)
      # O histórico ocupa TODO o resto do espaço
      chronologyEditHeight = availableHeight - editHeight
      
      # Garante tamanho mínimo para o histórico
      if chronologyEditHeight < minChronologyHeight:
          chronologyEditHeight = minChronologyHeight
          # Se não houver espaço suficiente, reduz a linha de comando
          if chronologyEditHeight + editHeight > availableHeight:
              editHeight = max(20, availableHeight - chronologyEditHeight)
      
      # Garante que a linha de comando tenha no mínimo sua altura ideal
      if editHeight < self.edit.getOptimalHeight():
          editHeight = self.edit.getOptimalHeight()
          chronologyEditHeight = availableHeight - editHeight
          if chronologyEditHeight < minChronologyHeight:
              chronologyEditHeight = minChronologyHeight
              # Se ainda não houver espaço, reduz a linha de comando
              if chronologyEditHeight + editHeight > availableHeight:
                  editHeight = availableHeight - chronologyEditHeight
      
      # Posiciona e redimensiona os widgets
      self.chronologyEdit.move(0, offsetY)
      self.chronologyEdit.resize(w, chronologyEditHeight)     
      self.chronologyEdit.ensureCursorVisible()
      
      self.edit.resize(w, editHeight)
      self.edit.move(0, chronologyEditHeight + offsetY)
      self.edit.ensureCursorVisible()

   def resizeEvent(self, e):
      """Manipula o evento de redimensionamento da janela."""
      QDockWidget.resizeEvent(self, e)
      
      # MODIFICAÇÃO: Garante que o widget interno use toda a largura disponível
      if hasattr(self, 'widget') and self.widget():
          self.widget().setMinimumWidth(0)
          self.widget().setMaximumWidth(16777215)
      
      self.resizeEdits()
      if hasattr(self, 'cmdSuggestWindow') and self.cmdSuggestWindow is not None:
          self.cmdSuggestWindow.resizeEvent(e)

        
# ===============================================================================
# QadChronologyEdit
# ===============================================================================
class QadChronologyEdit(QTextEdit):
   
   def __init__(self, parent):
      QTextEdit.__init__(self, parent)
      
      self.set_Colors()
      self.setReadOnly(True)
      self.setMinimumSize(0, 1)
   
   def set_Colors(self, foregroundColor = Qt.GlobalColor.black, backGroundColor = Qt.GlobalColor.lightGray):
      f = QColor(foregroundColor)
      b = QColor(backGroundColor)
      rgbStrForeColor = "rgb({0},{1},{2})"
      rgbStrForeColor = rgbStrForeColor.format(str(f.red()), str(f.green()), str(f.blue()))
      rgbStrBackColor = "rgb({0},{1},{2})"
      rgbStrBackColor = rgbStrBackColor.format(str(b.red()), str(b.green()), str(b.blue()))
      
      fmt = "color: " + rgbStrForeColor + ";" + \
            "background-color: " + rgbStrBackColor + ";" + \
            "selection-color: " + rgbStrBackColor + ";" + \
            "selection-background-color: " + rgbStrForeColor + ";"
      self.setStyleSheet(fmt)

   def insertText(self, txt):
      cursor = self.textCursor()
      for line in txt.split('\n'):
         if len(line) > 0:
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
            self.setTextCursor(cursor)
            self.insertPlainText('\n' + line)
      cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
      self.setTextCursor(cursor)
      self.ensureCursorVisible()
  
           
# ===============================================================================
# QadEdit
# ===============================================================================
class QadEdit(QTextEdit):
   PROMPT, KEY_WORDS = range(2)
   
   def __init__(self, parent, chronologyEdit):
      QTextEdit.__init__(self, parent)

      self.currentPrompt = ""
      self.currentPromptLength = 0

      self.inputType = QadInputTypeEnum.COMMAND
      self.default = None 
      self.inputMode = QadInputModeEnum.NONE

      self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
      self.setMinimumSize(10, 5)
      self.setUndoRedoEnabled(False)
      self.setAcceptRichText(False)
      self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
      self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
   
      self.historyIndex = 0

      self.englishKeyWords = [] 
      self.cmdOptionPosList = [] 
      self.currentCmdOptionPos = None

      self.upperKeyWordForegroundColor = Qt.GlobalColor.blue
      self.keyWordBackGroundColor = QColor(210, 210, 210)
      self.keyWordHighlightBackGroundColor = Qt.GlobalColor.gray
      
      self.tcf_normal = QTextCharFormat()
      self.tcf_keyWord = QTextCharFormat()
      self.tcf_upperKeyWord = QTextCharFormat()
      self.tcf_highlightKeyWord = QTextCharFormat()
      self.tcf_highlightUpperKeyWord = QTextCharFormat()
      
      self.set_Colors()
      self.set_keyWordColors()

      self.setMouseTracking(True)
      self.textChanged.connect(self.onTextChanged)
      
      self.timerForCmdSuggestWindow = QTimer()
      self.timerForCmdSuggestWindow.setSingleShot(True)
      self.timerForCmdAutoComplete = QTimer()
      self.timerForCmdAutoComplete.setSingleShot(True)

   def set_Colors(self, foregroundColor = Qt.GlobalColor.black, backGroundColor = Qt.GlobalColor.white):
      f = QColor(foregroundColor)
      b = QColor(backGroundColor)
      rgbStrForeColor = "rgb({0},{1},{2})"
      rgbStrForeColor = rgbStrForeColor.format(str(f.red()), str(f.green()), str(f.blue()))
      rgbStrBackColor = "rgb({0},{1},{2})"
      rgbStrBackColor = rgbStrBackColor.format(str(b.red()), str(b.green()), str(b.blue()))

      fmt = "color: " + rgbStrForeColor + ";" + \
            "background-color: " + rgbStrBackColor + ";" + \
            "selection-color: " + rgbStrBackColor + ";" + \
            "selection-background-color: " + rgbStrForeColor + ";"
      self.setStyleSheet(fmt)
      
      self.tcf_normal.setForeground(foregroundColor)     
      self.tcf_normal.setBackground(backGroundColor)
      self.tcf_normal.setFontWeight(QFont.Weight.Normal)

   def set_keyWordColors(self, backGroundColor = QColor(210, 210, 210), upperKeyWord_ForegroundColor = Qt.GlobalColor.blue, \
                         highlightKeyWord_BackGroundColor = Qt.GlobalColor.gray):
      self.tcf_keyWord.setBackground(backGroundColor)
      self.tcf_upperKeyWord.setForeground(upperKeyWord_ForegroundColor)
      self.tcf_upperKeyWord.setBackground(backGroundColor)
      self.tcf_upperKeyWord.setFontWeight(QFont.Weight.Bold)
               
      self.tcf_highlightKeyWord.setBackground(highlightKeyWord_BackGroundColor)         
      self.tcf_highlightUpperKeyWord.setForeground(upperKeyWord_ForegroundColor)
      self.tcf_highlightUpperKeyWord.setBackground(highlightKeyWord_BackGroundColor)
      self.tcf_highlightUpperKeyWord.setFontWeight(QFont.Weight.Bold)

   def setFormat(self, start, count, fmt): 
      if count == 0:
         return
      cursor = QTextCursor(self.textCursor())
      cursor.movePosition(QTextCursor.MoveOperation.Start, QTextCursor.MoveMode.MoveAnchor) 
      cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, start)
      cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, count)
      cursor.setCharFormat(fmt)
      self.setCurrentCharFormat(self.tcf_normal)

   def highlightKeyWords(self):
      lastBlock = self.document().lastBlock()
      txt = lastBlock.text()
      size = len(txt)
            
      i = txt.find("[")
      final = txt.rfind("]")
      if i >= 0 and final > i: 
         i = i + 1
         pos = lastBlock.position() + i
         while i < final:
            if txt[i] != "/":
               if self.currentCmdOptionPos is not None and \
                  pos >= self.currentCmdOptionPos.initialPos and \
                  pos <= self.currentCmdOptionPos.finalPos:                  
                  if txt[i].isupper():
                     self.setFormat(pos, 1, self.tcf_highlightUpperKeyWord)
                  else:
                     self.setFormat(pos, 1, self.tcf_highlightKeyWord)            
               else:
                  if txt[i].isupper():
                     self.setFormat(pos, 1, self.tcf_upperKeyWord)
                  else:
                     self.setFormat(pos, 1, self.tcf_keyWord)            
            i = i + 1
            pos = pos + 1

   def isCursorInEditionZone(self, newPos = None):
      cursor = self.textCursor()
      if newPos is None:
         pos = cursor.position()
      else:
         pos = newPos
      block = self.document().lastBlock()
      last = block.position() + self.currentPromptLength
      return pos >= last

   def currentCommand(self):
      block = self.textCursor().block()
      text = block.text()
      return text[self.currentPromptLength:]

   def getTextUntilPrompt(self):
      cursor = self.textCursor()
      text = cursor.block().text()
      return text[self.currentPromptLength : cursor.position()]

   def showMsgOnChronologyEdit(self, msg):
      self.parentWidget().showMsgOnChronologyEdit(msg)           

   def showCmdSuggestWindow(self, mode = True, filter = ""):
      if mode == False: 
         self.timerForCmdSuggestWindow.stop()
      self.parentWidget().showCmdSuggestWindow(mode, filter)

   def showCmdAutoComplete(self, filter = ""):
      self.timerForCmdAutoComplete.stop()

      filterLen = len(filter)
      if filterLen < 2:
         return
      
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      
      if inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE:
         cmdName, qty = self.parentWidget().plugin.getMoreUsedCmd(filter)
         self.appendCmdTextForAutoComplete(cmdName, filterLen)
   
   def appendCmdTextForAutoComplete(self, cmdName, filterLen):
         cursor = self.textCursor()
         self.setTextCursor(cursor)
         if filterLen < len(cmdName): 
            self.insertPlainText(cmdName[filterLen:])
         else:
            self.insertPlainText("")
         cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
         cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(cmdName) - filterLen)
         self.setTextCursor(cursor)
   
   def showMsg(self, msg, displayPromptAfterMsg = False, append = True):
      if len(msg) > 0:
         cursor = self.textCursor()
         sep = msg.rfind("\n")
         if sep >= 0:
            self.showMsgOnChronologyEdit(self.toPlainText() + msg[0:sep])
            newMsg = msg[sep + 1:]
            cursor.movePosition(QTextCursor.MoveOperation.Start, QTextCursor.MoveMode.MoveAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
         else:
            if append == True:
               cursor = self.textCursor()
               cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor) 
               newMsg = msg
            else:
               cursor.movePosition(QTextCursor.MoveOperation.Start, QTextCursor.MoveMode.MoveAnchor)
               cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
               newMsg = self.currentPrompt + msg

         self.setTextCursor(cursor)
         self.insertPlainText(newMsg)         

         if self.inputType & QadInputTypeEnum.KEYWORDS:         
            self.textCursor().block().setUserState(QadEdit.KEY_WORDS)
            self.setCmdOptionPosList() 
            self.highlightKeyWords()
         else:            
            self.textCursor().block().setUserState(QadEdit.PROMPT)
            del self.cmdOptionPosList[:] 
            
      if displayPromptAfterMsg:
         self.displayPrompt() 

   def showErr(self, err):
      self.showMsg(err, True) 
      mt = self.parentWidget().plugin.getCurrentMapTool()
      if (mt is not None) and mt.getDynamicInput().isVisible:
         mt.getDynamicInput().showErr(err)

   def displayPrompt(self, prompt = None):
      if prompt is not None:
         self.currentPrompt = prompt        
      self.currentPromptLength = len(self.currentPrompt)     
      self.showMsg("\n" + self.currentPrompt)

   def displayKeyWordsPrompt(self, prompt = None):
      if prompt is not None:
         self.currentPrompt = prompt
      self.currentPromptLength = len(self.currentPrompt)
      self.showMsg("\n" + self.currentPrompt)

   def showNextCmd(self):
      cmdsHistory = self.parentWidget().plugin.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if self.historyIndex < cmdsHistoryLen and cmdsHistoryLen > 0:
         self.historyIndex += 1
         if self.historyIndex < cmdsHistoryLen:
            self.showMsg(cmdsHistory[self.historyIndex], False, False)

   def showPreviousCmd(self):
      cmdsHistory = self.parentWidget().plugin.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if self.historyIndex > 0 and cmdsHistoryLen > 0:
         self.historyIndex -= 1
         if self.historyIndex < cmdsHistoryLen:
            self.showMsg(cmdsHistory[self.historyIndex], False, False)

   def showLastCmd(self):
      cmdsHistory = self.parentWidget().plugin.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if cmdsHistoryLen > 0:
         self.showMsg(cmdsHistory[cmdsHistoryLen - 1])
         return cmdsHistory[cmdsHistoryLen - 1]
      else:
         return ""

   def showInputMsg(self, inputMsg = None, inputType = QadInputTypeEnum.COMMAND, \
                    default = None, keyWords = "", inputMode = QadInputModeEnum.NONE):      
      if inputMsg is None: 
         inputMsg = QadMsg.translate("QAD", "Command: ")

      cursor = self.textCursor()
      actualPos = cursor.position()
         
      self.inputType = inputType
      self.default = default
      self.inputMode = inputMode
      if inputType & QadInputTypeEnum.KEYWORDS and (keyWords is not None):
         localEnglishKeyWords = keyWords.split("_")
         self.keyWords = localEnglishKeyWords[0].split("/") 
         if len(localEnglishKeyWords) > 1:
            self.englishKeyWords = localEnglishKeyWords[1].split("/") 
         else:
            del self.englishKeyWords[:]
         self.displayKeyWordsPrompt(inputMsg)
      else:
        self.displayPrompt(inputMsg)

      mt = self.parentWidget().plugin.getCurrentMapTool()
      if (mt is not None):
         if inputType != QadInputTypeEnum.COMMAND:
            mt.getDynamicInput().showInputMsg(inputMsg, inputType, default, keyWords, inputMode)

      return

   def setCmdOptionPosList(self):
      del self.cmdOptionPosList[:] 
      lenKeyWords = len(self.keyWords)
      if lenKeyWords == 0 or len(self.currentPrompt) == 0:
         return
      prompt = self.currentPrompt
      initialPos = prompt.find("[", 0)
      finalDelimiter = prompt.find("]", initialPos)
      if initialPos == -1 or finalDelimiter == -1:
         return
      i = 0
      while i < lenKeyWords:
         keyWord = self.keyWords[i]
         initialPos = prompt.find(keyWord, initialPos + 1, finalDelimiter)
         if initialPos >= 0:
            finalPos = initialPos + len(keyWord)
            self.cmdOptionPosList.append(QadCmdOptionPos(keyWord, initialPos, finalPos))         
            initialPos = prompt.find("/", finalPos)
            if initialPos == -1:
               return
         i = i + 1

   def getCmdOptionPosUnderMouse(self, pos):
      cursor = self.cursorForPosition(pos)
      pos = cursor.position()
      for cmdOptionPos in self.cmdOptionPosList:
         if cmdOptionPos.isSelected(pos):
            return cmdOptionPos
      return None

   def mouseMoveEvent(self, event):
      cursor = self.cursorForPosition(event.pos())
      pos = cursor.position()
      if self.isCursorInEditionZone(pos):
         QTextEdit.mouseMoveEvent(self, event)
         
      self.currentCmdOptionPos = self.getCmdOptionPosUnderMouse(event.pos())
      self.highlightKeyWords()
      self.currentCmdOptionPos = None

   def mouseDoubleClickEvent(self, event):
      cursor = self.cursorForPosition(event.pos())
      pos = cursor.position()
      if self.isCursorInEditionZone(pos):
         QTextEdit.mouseDoubleClickEvent(self, event)

   def mousePressEvent(self, event):
      cursor = self.cursorForPosition(event.pos())
      pos = cursor.position()
      if self.isCursorInEditionZone(pos):
         QTextEdit.mousePressEvent(self, event)

   def mouseReleaseEvent(self, event):
      QTextEdit.mouseReleaseEvent(self, event)
      if self.textCursor().position() >= self.document().lastBlock().position():
         if event.button() == Qt.MouseButton.LeftButton:
            cmdOptionPos = self.getCmdOptionPosUnderMouse(event.pos())
            if cmdOptionPos is not None:
               upperPart = qad_utils.extractUpperCaseSubstr(cmdOptionPos.name)
               self.showEvaluateMsg(upperPart, False)

   def updateHistory(self, command):
      self.parentWidget().plugin.updateCmdsHistory(command)
      cmdsHistory = self.parentWidget().plugin.cmdsHistory
      self.historyIndex = len(cmdsHistory)

   def keyPressEvent(self, e):      
      if self.parentWidget().plugin.shortCutManagement(e): 
         return

      cursor = self.textCursor()

      if self.inputType & QadInputTypeEnum.COMMAND:
         if self.parentWidget().isVisibleCmdSuggestWindow() and \
            (e.key() == Qt.Key.Key_Down or e.key() == Qt.Key.Key_Up or e.key() == Qt.Key.Key_PageDown or e.key() == Qt.Key.Key_PageUp or
             e.key() == Qt.Key.Key_End or e.key() == Qt.Key.Key_Home):
            self.parentWidget().cmdSuggestWindow.keyPressEvent(e)
            return
         else:  
            self.showCmdSuggestWindow(False)

      if not self.isCursorInEditionZone():
         if e.modifiers() & Qt.KeyboardModifier.ControlModifier or e.modifiers() & Qt.KeyboardModifier.MetaModifier:
            if e.key() == Qt.Key.Key_C or e.key() == Qt.Key.Key_A:
               QTextEdit.keyPressEvent(self, e)
         else:
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
            self.setTextCursor(cursor)
            QTextEdit.keyPressEvent(self, e)
                                    
         self.setTextCursor(cursor)
         self.ensureCursorVisible()
      else:
         if e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter:
            self.entered()
         elif e.key() == Qt.Key.Key_Space and \
              (self.inputType & QadInputTypeEnum.COMMAND or not(self.inputType & QadInputTypeEnum.STRING)):
            self.entered()
            return
         elif e.key() == Qt.Key.Key_Down:
            self.showNextCmd()
            return 
         elif e.key() == Qt.Key.Key_Up:
            self.showPreviousCmd()
            return 
         elif e.key() == Qt.Key.Key_Backspace:
            if not cursor.hasSelection() and cursor.columnNumber() == self.currentPromptLength:
               return
            QTextEdit.keyPressEvent(self, e)
         elif e.key() == Qt.Key.Key_Left and cursor.position() > self.document().lastBlock().position() + self.currentPromptLength:
            anchor = QTextCursor.MoveMode.KeepAnchor if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor
            move = QTextCursor.MoveOperation.WordLeft if e.modifiers() & Qt.KeyboardModifier.ControlModifier or e.modifiers() & Qt.KeyboardModifier.MetaModifier else QTextCursor.MoveOperation.Left
            cursor.movePosition(move, anchor)
         elif e.key() == Qt.Key.Key_Right:
            anchor = QTextCursor.MoveMode.KeepAnchor if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor
            move = QTextCursor.MoveOperation.WordRight if e.modifiers() & Qt.KeyboardModifier.ControlModifier or e.modifiers() & Qt.KeyboardModifier.MetaModifier else QTextCursor.MoveOperation.Right
            cursor.movePosition(move, anchor)
         elif e.key() == Qt.Key.Key_Home:
            anchor = QTextCursor.MoveMode.KeepAnchor if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, anchor, 1)
            cursor.movePosition(QTextCursor.MoveOperation.Right, anchor, self.currentPromptLength)
         elif e.key() == Qt.Key.Key_End:
            anchor = QTextCursor.MoveMode.KeepAnchor if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, anchor, 1)
         else:
            QTextEdit.keyPressEvent(self, e)

         self.setTextCursor(cursor)
         self.ensureCursorVisible()
   
         if self.inputType & QadInputTypeEnum.COMMAND:
            inputSearchDelay = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHDELAY"))
            
            currMsg = self.getCurrMsg()
            shot1 = lambda: self.showCmdSuggestWindow(True, currMsg)

            del self.timerForCmdSuggestWindow
            self.timerForCmdSuggestWindow = QTimer()
            self.timerForCmdSuggestWindow.setSingleShot(True)
            self.timerForCmdSuggestWindow.timeout.connect(shot1)
            self.timerForCmdSuggestWindow.start(inputSearchDelay)

            if e.text().isalnum(): 
               self.textUntilPrompt = self.getTextUntilPrompt()
               shot2 = lambda: self.showCmdAutoComplete(self.textUntilPrompt)
               del self.timerForCmdAutoComplete
               self.timerForCmdAutoComplete = QTimer()
               self.timerForCmdAutoComplete.setSingleShot(True)
               
               self.timerForCmdAutoComplete.timeout.connect(shot2)
               self.timerForCmdAutoComplete.start(inputSearchDelay)

   def entered(self):
      if self.inputType & QadInputTypeEnum.COMMAND:
         self.showCmdSuggestWindow(False) 
      
      cmdsHistory = self.parentWidget().plugin.cmdsHistory
      self.historyIndex = len(cmdsHistory)
      cursor = self.textCursor()
      cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
      self.setTextCursor(cursor)
      self.evaluate(str(self.currentCommand()))

   def showEvaluateMsg(self, msg = None, append = True):
      if msg is not None:
         self.showMsg(msg, False, append)
      self.entered()

   def getCurrMsg(self):
      cursor = self.textCursor()
      prevPos = cursor.position()
      cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.MoveAnchor)
      self.setTextCursor(cursor)
      msg = str(self.currentCommand())
      cursor.setPosition(prevPos)
      self.setTextCursor(cursor)
      return msg

   def getInvalidInputMsg(self):
      if self.inputType & QadInputTypeEnum.POINT2D or \
         self.inputType & QadInputTypeEnum.POINT3D:
         if self.inputType & QadInputTypeEnum.KEYWORDS and \
            (self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE):
            return QadMsg.translate("QAD", "\nEnter a point, a real number or a keyword.\n")
         elif self.inputType & QadInputTypeEnum.KEYWORDS:
            return QadMsg.translate("QAD", "\nEnter a point or a keyword.\n")
         elif self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
            return QadMsg.translate("QAD", "\nEnter a point or a real number.\n")
         else:
            return QadMsg.translate("QAD", "\nPoint not valid.\n")         
      elif self.inputType & QadInputTypeEnum.KEYWORDS:
         return QadMsg.translate("QAD", "\nKeyword not valid.\n")
      elif self.inputType & QadInputTypeEnum.STRING:
         return QadMsg.translate("QAD", "\nString not valid.\n")
      elif self.inputType & QadInputTypeEnum.INT:
         return QadMsg.translate("QAD", "\nInteger number not valid.\n")
      elif self.inputType & QadInputTypeEnum.LONG:
         return QadMsg.translate("QAD", "\nLong integer number not valid.\n")
      elif self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         return QadMsg.translate("QAD", "\nReal number not valid.\n")
      elif self.inputType & QadInputTypeEnum.BOOL:
         return QadMsg.translate("QAD", "\nBoolean not valid.\n")
      else:
         return ""

   def evaluateKeyWords(self, cmd):
      if cmd == "": 
         return None
      
      if cmd[0] == "_": 
         keyWord, Msg = qad_utils.evaluateCmdKeyWords(cmd[1:], self.englishKeyWords)
         if keyWord is None:
            if Msg is not None:
               self.showMsg(Msg)
            return None
         i = 0
         for k in self.englishKeyWords:
            if k == keyWord:
               return self.keyWords[i]
            i = i + 1
         return None
      else:
         keyWord, Msg = qad_utils.evaluateCmdKeyWords(cmd, self.keyWords)
         if keyWord is None:
            if Msg is not None:
               self.showMsg(Msg)
         return keyWord
      
   def evaluate(self, cmd):      
      if self.inputType & QadInputTypeEnum.COMMAND:
         if cmd == "":
            cmd = str(self.showLastCmd()) 
            if cmd == "":
               return
         
         if self.parentWidget().isValidCommand(cmd) or self.parentWidget().isValidEnvVariable(cmd):
            self.updateHistory(cmd)
            self.parentWidget().runCommand(cmd)
         else:
            msg = QadMsg.translate("QAD", "\nInvalid command \"{0}\".")
            self.showErr(msg.format(cmd.encode('utf-8','ignore').decode('utf-8'))) 
         return

      if cmd == "":
         if self.default is not None:
            if type(self.default) == QgsPointXY:
               cmd = self.default.toString()
            else:
               cmd = str(self.default)             
               
         if cmd == "" and \
            not (self.inputMode & QadInputModeEnum.NOT_NULL): 
            self.parentWidget().continueCommand(None)         
            return
                       
      if self.inputType & QadInputTypeEnum.POINT2D:
         snapType = str2snapTypeEnum(cmd)
         if snapType != -1:
            snapParams = str2snapParams(cmd)
            self.parentWidget().forceCommandMapToolSnapTypeOnce(snapType, snapParams)
            self.showMsg(QadMsg.translate("QAD", "\n(temporary snap)\n"), True) 
            return
         
         if cmd.upper() == QadMsg.translate("Snap", "M2P") or cmd.upper() == "_M2P":
            self.parentWidget().forceCommandMapToolM2P()
            return
         
         if (self.inputType & QadInputTypeEnum.INT) or \
            (self.inputType & QadInputTypeEnum.LONG) or \
            (self.inputType & QadInputTypeEnum.FLOAT) or \
            (self.inputType & QadInputTypeEnum.ANGLE) or \
            (self.inputType & QadInputTypeEnum.BOOL):
            oneNumberAllowed = False
         else:
            oneNumberAllowed = True
            
         pt = qad_utils.str2QgsPoint(cmd, \
                                     self.parentWidget().getLastPoint(), \
                                     self.parentWidget().getCurrenPointFromCommandMapTool(), \
                                     oneNumberAllowed)
                      
         if pt is not None:
            self.parentWidget().setLastPoint(pt)
            self.parentWidget().continueCommand(pt)
            return
            
      if self.inputType & QadInputTypeEnum.POINT3D: 
         pass
      
      if self.inputType & QadInputTypeEnum.KEYWORDS:
         keyWord = self.evaluateKeyWords(cmd)
               
         if keyWord is not None:
            self.parentWidget().continueCommand(keyWord)
            return
                      
      if self.inputType & QadInputTypeEnum.STRING:
         if cmd is not None:            
            self.parentWidget().continueCommand(cmd)
            return       
                     
      if self.inputType & QadInputTypeEnum.INT:
         num = qad_utils.str2int(cmd)
         if num is not None:
            if num == 0 and (self.inputMode & QadInputModeEnum.NOT_ZERO):              
               num = None
            elif num < 0 and (self.inputMode & QadInputModeEnum.NOT_NEGATIVE):              
               num = None
            elif num > 0 and (self.inputMode & QadInputModeEnum.NOT_POSITIVE):              
               num = None
                  
            if num is not None:
               self.parentWidget().continueCommand(int(num))
               return       
                     
      if self.inputType & QadInputTypeEnum.LONG:
         num = qad_utils.str2long(cmd)
         if num is not None:
            if num == 0 and (self.inputMode & QadInputModeEnum.NOT_ZERO):              
               num = None
            elif num < 0 and (self.inputMode & QadInputModeEnum.NOT_NEGATIVE):              
               num = None
            elif num > 0 and (self.inputMode & QadInputModeEnum.NOT_POSITIVE):              
               num = None
            
            if num is not None:
               self.parentWidget().continueCommand(int(num))
               return       
                     
      if self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         num = qad_utils.str2float(cmd)
         if num is not None:
            if num == 0 and (self.inputMode & QadInputModeEnum.NOT_ZERO):              
               num = None
            elif num < 0 and (self.inputMode & QadInputModeEnum.NOT_NEGATIVE):              
               num = None
            elif num > 0 and (self.inputMode & QadInputModeEnum.NOT_POSITIVE):              
               num = None
               
            if num is not None:
               self.parentWidget().continueCommand(num)
               return       

      elif self.inputType & QadInputTypeEnum.BOOL:
         value = qad_utils.str2bool(cmd)
            
         if value is not None:
            self.parentWidget().continueCommand(value)
            return       

      self.showMsg(self.getInvalidInputMsg())
      
      if self.inputType & QadInputTypeEnum.KEYWORDS:
         self.displayKeyWordsPrompt()
      else:
         self.displayPrompt()
         
      return
      
   def getOptimalHeight(self):
      """Retorna a altura fixa para UMA LINHA de comando."""
      fm = QFontMetrics(self.currentFont())
      pixelsHeight = fm.height()
      # MODIFICAÇÃO: Retorna a altura exata de uma linha + uma pequena margem
      return pixelsHeight + 4  # Reduzi a margem para 4 pixels
      
   def onTextChanged(self):
      self.parentWidget().resizeEdits()
      self.timerForCmdAutoComplete.stop()

         
# ===============================================================================
# QadCmdSuggestWindow
# ===============================================================================
class QadCmdSuggestWindow(QWidget, Ui_QadCmdSuggestWindow, object):
         
   def __init__(self, parent, editWidget, infoCmds, infoVars):
      QWidget.__init__(self, parent, Qt.WindowType.ToolTip)

      self.editWidget = editWidget 
      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      self.infoCmds = infoCmds[:] 
      self.infoVars = infoVars[:] 
      self.filter = ""
                 
   def initGui(self):
      self.cmdNamesListView = QadCmdSuggestListView(self)
      self.cmdNamesListView.setObjectName("QadCmdNamesListView")
      self.vboxlayout.addWidget(self.cmdNamesListView)
      
   def setFocus(self):
      self.cmdNamesListView.setFocus()
      
   def keyPressEvent(self, e):
      self.cmdNamesListView.keyPressEvent(e)

   def inFilteredInfoList(self, filteredInfoList, cmdName):
      for filteredInfo in filteredInfoList:
         if filteredInfo[0] == cmdName:
            return True
      return False

   def getFilteredInfoList(self, infoList):
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      dispIcons = inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_ICON

      filteredInfoList = []
      upperFilter = self.filter
      if len(upperFilter) > 0:
         if self.filter == "*": 
            for info in infoList:
               if not self.inFilteredInfoList(filteredInfoList, info[0]):
                  filteredInfoList.append([info[0], info[2] if dispIcons else None, info[3]])
         else:
            if upperFilter[0] == "_": 
               upperFilter = upperFilter[1:]
               for info in infoList:
                  if info[1].upper().find(upperFilter) == 0 or \
                     difflib.SequenceMatcher(None, info[1].upper(), upperFilter).ratio() > 0.6:
                     if not self.inFilteredInfoList(filteredInfoList, "_" + info[1]):
                        filteredInfoList.append(["_" + info[1], info[2] if dispIcons else None, info[3]])
            else: 
               for info in infoList:
                  if info[0].upper().find(upperFilter) == 0 or \
                     difflib.SequenceMatcher(None, info[0].upper(), upperFilter).ratio() > 0.6:
                     if not self.inFilteredInfoList(filteredInfoList, info[0]):
                        filteredInfoList.append([info[0], info[2] if dispIcons else None, info[3]])
      
      return filteredInfoList
   
   def setFilter(self, filter = ""):
      itemList = []
      itemList.extend(self.infoCmds)
         
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      if inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and (not inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.EXCLUDE_SYS_VAR):
          itemList.extend(self.infoVars)

      self.filter = filter.strip().upper()

      filteredInfo = self.getFilteredInfoList(itemList)
      
      l = len(filteredInfo)
      if l > 0:
         self.cmdNamesListView.set(filteredInfo)
         items = self.cmdNamesListView.model.findItems(self.filter, Qt.MatchFlag.MatchStartsWith)
         if len(items) > 0:
            self.cmdNamesListView.setCurrentIndex(self.cmdNamesListView.model.indexFromItem(items[0]))
      
      return l
   
   def show(self, mode = True):
      if mode == True:
         inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
         if inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and (not inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.EXCLUDE_SYS_VAR):
            self.setVisible(True)
            cmdName = self.cmdNamesListView.selectionModel().currentIndex().data()
            if cmdName is not None:
               self.appendCmdTextForAutoComplete(cmdName)
      else:
         self.setVisible(False)

   def getDataHeight(self):
      n = self.cmdNamesListView.model.rowCount()
      if n == 0:
         return 0

      OffSet = 4 
      return self.cmdNamesListView.sizeHintForRow(0) * n + OffSet
      
   def showEvaluateMsg(self, cmd = None, append = True):
      self.show(False)
      self.editWidget.setFocus()
      self.editWidget.showEvaluateMsg(cmd, append)

   def showMsg(self, cmd):
      parent = self.parentWidget()
      cursor = self.editWidget.textCursor()
      prevPos = cursor.position()
      self.editWidget.showMsg(cmd, False, False)
      cursor.setPosition(prevPos)
      self.editWidget.setTextCursor(cursor)
      self.editWidget.setFocus()

   def keyPressEventToParent(self, e):
      self.editWidget.keyPressEvent(e)

   def appendCmdTextForAutoComplete(self, cmdName):
      if self.filter == "*":
         self.editWidget.appendCmdTextForAutoComplete(cmdName, 0)
      else:
         self.editWidget.appendCmdTextForAutoComplete(cmdName, len(self.filter))
      

# ===============================================================================
# QadCmdListView
# ===============================================================================
class QadCmdSuggestListView(QListView):

   def __init__(self, parent):
      QListView.__init__(self, parent)
      
      self.setViewMode(QListView.ViewMode.ListMode)
      self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
      self.setUniformItemSizes(True)
      self.model = QStandardItemModel()
      self.setModel(self.model)
      self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
   def set(self, filteredCmdNames):
      self.model.clear()

      for infoCmd in filteredCmdNames:
         cmdName = infoCmd[0]
         cmdIcon = infoCmd[1]
         cmdNote = infoCmd[2]
         if cmdIcon is None:        
            item = QStandardItem(cmdName)
         else:
            item = QStandardItem(cmdIcon, cmdName)
         
         if cmdNote is not None and len(cmdNote) > 0:
            item.setToolTip(cmdNote)
            
         item.setEditable(False)
         self.model.appendRow(item)
         
      self.model.sort(0)

   def keyPressEvent(self, e):
      if e.key() == Qt.Key.Key_Up or e.key() == Qt.Key.Key_Down or \
         e.key() == Qt.Key.Key_PageUp or e.key() == Qt.Key.Key_PageDown or \
         e.key() == Qt.Key.Key_End or e.key() == Qt.Key.Key_Home:         
         QListView.keyPressEvent(self, e)
         cmdName = self.selectionModel().currentIndex().data()
         self.parentWidget().showMsg(cmdName)
      elif e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter:
         cmd = self.selectionModel().currentIndex().data()
         if cmd is not None:
            self.parentWidget().showMsg(cmd)
         self.parentWidget().showEvaluateMsg()
      else:
         self.parentWidget().keyPressEventToParent(e)

   def mouseReleaseEvent(self, e):
      cmd = self.selectionModel().currentIndex().data()
      self.parentWidget().showEvaluateMsg(cmd, False)
      