from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PalletAddrUI import Ui_dlgPalletAddr
from INIConfig import INIConfig as INI  # lib for INI Config file
from pymysql.connections import Connection
import pymysql


class PalletAddresDialog(QDialog, Ui_dlgPalletAddr):

    def __init__(self, *args, **kwargs):
        super(PalletAddresDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('Pallet Address Window')
        self.dbConn: Connection = self.__database_connect()
        self.model_name = ''
        self.model_type = ''

        self.__Init_UI()

    def __Init_UI(self):
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute("select model_name, model_type from model_info where use_YN = 'Y' order by model_name")
                for row in cursor.fetchall():
                    model_nm = row['model_name']
                    if row['model_type'] != '':  # 모델 type이 있을 경우만 더 추가
                        model_nm += ' [type:' + row['model_type'] + ']'

                    self.combo_ModelList.addItem(model_nm)

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Model List Error', str(e))
            return

    def comboModelChanged(self):

        ##############################################################################################################
        # 전역 변수에 선택한 모델명과 모델index를 저장한다.
        strModelName = self.combo_ModelList.currentText()
        if ' [' in strModelName:  # 모델명에 ' ['이 있다면... type을 분리하기 위해서
            self.model_name = strModelName[0:strModelName.find(' [')]
            self.model_type = strModelName[strModelName.find(':') + 1:strModelName.find(']')]
        else:
            self.model_name = self.combo_ModelList.currentText()
            self.model_type = ''
        self.model_index = self.combo_ModelList.currentIndex()
        ##############################################################################################################

        ##############################################################################################################
        # 모델별 주소를 각 컨트롤에 셋팅한다.
        strFromAddr = ''
        try:
            with self.dbConn.cursor() as cursor:
                sql = "select from_addr1, from_addr2, from_addr3, to_addr1, to_addr2, to_addr3 from model_info where model_name = '{0}' and model_type = '{1}'".format(
                    self.model_name, self.model_type)
                cursor.execute(sql)

                if cursor.rowcount == 0:
                    return

                for row in cursor.fetchall():
                    self.edit_FromAddr1.setText(row['from_addr1'])
                    self.edit_FromAddr2.setText(row['from_addr2'])
                    self.edit_FromAddr3.setText(row['from_addr3'])
                    self.edit_ToAddr1.setText(row['to_addr1'])
                    self.edit_ToAddr2.setText(row['to_addr2'])
                    self.edit_ToAddr3.setText(row['to_addr3'])
                    self.edit_FromPreview.setText(row['from_addr1'] + '\n\n' + row['from_addr2'] + '\n\n' + row['from_addr3'])
                    self.edit_ToPreview.setText(row['to_addr1'] + '\n\n' + row['to_addr2'] + '\n\n' + row['to_addr3'])

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Model Changed Error', str(e))
            return
        ##############################################################################################################

    def btnFromPreview(self):
        strPreview = self.edit_FromAddr1.text() + '\n\n'
        strPreview += self.edit_FromAddr2.text() + '\n\n'
        strPreview += self.edit_FromAddr3.text()

        self.edit_FromPreview.setText(strPreview)

    def btnFromSave(self):
        if self.combo_ModelList.currentText() == 'Select Model':
            QMessageBox.information(self, 'Not Select Model', 'Please select a model')
            return

        try:
            with self.dbConn.cursor() as cursor:
                sql = '''
                    update model_info
                    set
                        from_addr1 = '{0}',
                        from_addr2  = '{1}',
                        from_addr3  = '{2}'
                    where
                        model_name = '{3}'
                    and	model_type = '{4}'
                '''.format(self.edit_FromAddr1.text(), self.edit_FromAddr2.text(), self.edit_FromAddr3.text(),
                     self.model_name, self.model_type)
                cursor.execute(sql)
                self.dbConn.commit()

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Model Update Error', str(e))
            return

        QMessageBox.information(self, 'Save Complet.', 'The save is complete.')

    def btnToPreview(self):
        strPreview = self.edit_ToAddr1.text() + '\n\n'
        strPreview += self.edit_ToAddr2.text() + '\n\n'
        strPreview += self.edit_ToAddr3.text()

        self.edit_ToPreview.setText(strPreview)

    def btnToSave(self):
        if self.combo_ModelList.currentText() == 'Select Model':
            QMessageBox.information(self, 'Not Select Model', 'Please select a model')
            return

        try:
            with self.dbConn.cursor() as cursor:
                sql = '''
                    update model_info
                    set
                        to_addr1 = '{0}',
                        to_addr2  = '{1}',
                        to_addr3  = '{2}'
                    where
                        model_name = '{3}'
                    and	model_type = '{4}'
                '''.format(self.edit_ToAddr1.text(), self.edit_ToAddr2.text(), self.edit_ToAddr3.text(),
                           self.model_name, self.model_type)
                cursor.execute(sql)
                self.dbConn.commit()

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Model Update Error', str(e))
            return

        QMessageBox.information(self, 'Save Complet.', 'The save is complete.')

    def showModal(self):
        return self.exec()

    def reject(self):
        # ESC를 누르면 창이 닫겨서 안 닫히도록 처리
        # ESC를 누를 때 reject() 이벤트가 발생하게 되고 이때 return으로 아무것도 안하게 처리
        # sys.exit(0)  # ESC 누를 때 종료 처리
        return

    def closeEvent(self, event):
        # DB Connection 종료 처리(cursor는 with문을 쓰면서 자동 종료되어 별도 처리 안해도 됨)
        self.dbConn.close()

    def __database_connect(self):
        config = INI("./Pallet_config.ini")

        # ===========DB Connection =================================================================================
        # mariaDB를 접속하기 위해서 mariaDB 라이브러리를 사용하지 않고 mysql 라이브러리 사용
        # mariaDB 라이브러리를 사용하면 이상하게 debug 모드에서 오류가 남
        # port 3366으로 변경햇다
        try:
            db_config = {'host': config.getINI("DB_INFO", "host"),
                         'user': config.getINI("DB_INFO", "user"),
                         'passwd': config.getINI("DB_INFO", "passwd"),
                         'database': config.getINI("DB_INFO", "database_name"),
                         'port': int(config.getINI("DB_INFO", "port")),
                         'charset': 'utf8',
                         'autocommit': False,
                         'cursorclass': pymysql.cursors.DictCursor
                         }
            conn = pymysql.connect(**db_config)
        except Exception as e:
            print("error : {0}".format(e))
            # QMessageBox.critical(self, 'DB Connection Error', str(e))
            strErr = '''
=======================================================
DB connection failed.
=======================================================

{0}
            '''.format(str(e))
            QMessageBox.critical(self, 'DB Connection Fail', strErr)
            return

        return conn


if __name__ == '__main__':
    app = QApplication()
    window = PalletAddresDialog()
    window.show()
    app.exec()