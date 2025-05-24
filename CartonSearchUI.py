# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'CartonSearchUI.ui'
##
## Created by: Qt User Interface Compiler version 6.7.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QGroupBox, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QWidget)

class Ui_dlgProductSearch(object):
    def setupUi(self, dlgProductSearch):
        if not dlgProductSearch.objectName():
            dlgProductSearch.setObjectName(u"dlgProductSearch")
        dlgProductSearch.setWindowModality(Qt.ApplicationModal)
        dlgProductSearch.resize(1033, 463)
        dlgProductSearch.setModal(False)
        self.groupBox = QGroupBox(dlgProductSearch)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(10, 20, 1001, 71))
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 30, 61, 19))
        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(277, 30, 61, 19))
        self.edit_InputMac = QLineEdit(self.groupBox)
        self.edit_InputMac.setObjectName(u"edit_InputMac")
        self.edit_InputMac.setGeometry(QRect(81, 24, 111, 31))
        self.edit_InputSN = QLineEdit(self.groupBox)
        self.edit_InputSN.setObjectName(u"edit_InputSN")
        self.edit_InputSN.setGeometry(QRect(327, 24, 111, 31))
        self.btnSearch = QPushButton(self.groupBox)
        self.btnSearch.setObjectName(u"btnSearch")
        self.btnSearch.setGeometry(QRect(860, 19, 121, 41))
        self.btnSearch.setAutoDefault(False)
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(540, 31, 101, 19))
        self.edit_CartonID = QLineEdit(self.groupBox)
        self.edit_CartonID.setObjectName(u"edit_CartonID")
        self.edit_CartonID.setGeometry(QRect(638, 25, 151, 31))
        self.tableWidget = QTableWidget(dlgProductSearch)
        self.tableWidget.setObjectName(u"tableWidget")
        self.tableWidget.setGeometry(QRect(10, 120, 1011, 331))
        self.tableWidget.setFocusPolicy(Qt.WheelFocus)
        self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QWidget.setTabOrder(self.edit_InputMac, self.edit_InputSN)
        QWidget.setTabOrder(self.edit_InputSN, self.edit_CartonID)
        QWidget.setTabOrder(self.edit_CartonID, self.btnSearch)
        QWidget.setTabOrder(self.btnSearch, self.tableWidget)

        self.retranslateUi(dlgProductSearch)
        self.btnSearch.clicked.connect(dlgProductSearch.btnSearchClicked)
        self.edit_InputSN.returnPressed.connect(dlgProductSearch.editSNPressed)
        self.edit_InputMac.returnPressed.connect(dlgProductSearch.editMACPressed)
        self.edit_CartonID.returnPressed.connect(dlgProductSearch.editCartonIDPressed)

        QMetaObject.connectSlotsByName(dlgProductSearch)
    # setupUi

    def retranslateUi(self, dlgProductSearch):
        dlgProductSearch.setWindowTitle(QCoreApplication.translate("dlgProductSearch", u"Dialog", None))
        self.groupBox.setTitle(QCoreApplication.translate("dlgProductSearch", u"Search Info", None))
        self.label.setText(QCoreApplication.translate("dlgProductSearch", u"MAC ::", None))
        self.label_2.setText(QCoreApplication.translate("dlgProductSearch", u"SN ::", None))
        self.btnSearch.setText(QCoreApplication.translate("dlgProductSearch", u"Search...", None))
        self.label_3.setText(QCoreApplication.translate("dlgProductSearch", u"Carton ID ::", None))
    # retranslateUi

