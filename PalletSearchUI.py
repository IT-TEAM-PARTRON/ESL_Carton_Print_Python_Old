# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PalletSearchUI.ui'
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

class Ui_dlgPalletSearch(object):
    def setupUi(self, dlgPalletSearch):
        if not dlgPalletSearch.objectName():
            dlgPalletSearch.setObjectName(u"dlgPalletSearch")
        dlgPalletSearch.setWindowModality(Qt.ApplicationModal)
        dlgPalletSearch.resize(902, 435)
        self.tableWidget = QTableWidget(dlgPalletSearch)
        self.tableWidget.setObjectName(u"tableWidget")
        self.tableWidget.setGeometry(QRect(10, 120, 881, 301))
        self.groupBox = QGroupBox(dlgPalletSearch)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(10, 10, 881, 80))
        self.btnSearch = QPushButton(self.groupBox)
        self.btnSearch.setObjectName(u"btnSearch")
        self.btnSearch.setGeometry(QRect(750, 24, 121, 41))
        self.btnSearch.setAutoDefault(False)
        self.edit_PalletID = QLineEdit(self.groupBox)
        self.edit_PalletID.setObjectName(u"edit_PalletID")
        self.edit_PalletID.setGeometry(QRect(465, 30, 161, 31))
        self.edit_CartonID = QLineEdit(self.groupBox)
        self.edit_CartonID.setObjectName(u"edit_CartonID")
        self.edit_CartonID.setGeometry(QRect(140, 30, 171, 31))
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(60, 36, 101, 19))
        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(390, 36, 101, 19))
        QWidget.setTabOrder(self.edit_CartonID, self.edit_PalletID)
        QWidget.setTabOrder(self.edit_PalletID, self.btnSearch)
        QWidget.setTabOrder(self.btnSearch, self.tableWidget)

        self.retranslateUi(dlgPalletSearch)
        self.btnSearch.clicked.connect(dlgPalletSearch.btnSearchClicked)
        self.edit_CartonID.returnPressed.connect(dlgPalletSearch.editCartonIDPressed)
        self.edit_PalletID.returnPressed.connect(dlgPalletSearch.editPalletIDPressed)

        QMetaObject.connectSlotsByName(dlgPalletSearch)
    # setupUi

    def retranslateUi(self, dlgPalletSearch):
        dlgPalletSearch.setWindowTitle(QCoreApplication.translate("dlgPalletSearch", u"Dialog", None))
        self.groupBox.setTitle(QCoreApplication.translate("dlgPalletSearch", u"Search Info", None))
        self.btnSearch.setText(QCoreApplication.translate("dlgPalletSearch", u"Search...", None))
        self.label_3.setText(QCoreApplication.translate("dlgPalletSearch", u"Carton ID ::", None))
        self.label_4.setText(QCoreApplication.translate("dlgPalletSearch", u"Pallet ID ::", None))
    # retranslateUi

