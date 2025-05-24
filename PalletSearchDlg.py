from PySide6.QtWidgets import QApplication, QDialog, QAbstractItemView, QTableWidgetItem, QMessageBox
from PalletSearchUI import Ui_dlgPalletSearch
from pymysql.connections import Connection


class PalletSearchDialog(QDialog, Ui_dlgPalletSearch):

    def __init__(self, *args, **kwargs):
        super(PalletSearchDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.__make_table_layout()
        self.setWindowTitle('Product Search Window')
        self.dbConn: Connection = ''
        self.edit_CartonID.setFocus()

    def __make_table_layout(self):
        # table 헤더 컬럼 속성 부여
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(["Pallet No.", "Model Name", "CartonID", "PC Name", "WORK DATE", "Pallet ID", "Print Date"])
        self.tableWidget.horizontalHeader().setStyleSheet("QHeaderView::section {background-color:#401040;color:#FFFFFF;}")
        # self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # table 헤더 컬럼 사이즈 조절
        self.tableWidget.setColumnWidth(0, self.width() * 8 / 100)
        self.tableWidget.setColumnWidth(1, self.width() * 13 / 100)
        self.tableWidget.setColumnWidth(2, self.width() * 15 / 100)
        self.tableWidget.setColumnWidth(3, self.width() * 13 / 100)
        self.tableWidget.setColumnWidth(4, self.width() * 15 / 100)
        self.tableWidget.setColumnWidth(5, self.width() * 15 / 100)
        self.tableWidget.setColumnWidth(6, self.width() * 15 / 100)

        # for i in range(10):
        #     self.tableWidget.insertRow(i)
            # self.tableWidget.setItem(i, 0, QTableWidgetItem('1111'))
            # self.tableWidget.setItem(i, 1, QTableWidgetItem('22222'))
            # self.tableWidget.setItem(i, 2, QTableWidgetItem('33333'))
            # self.tableWidget.setItem(i, 3, QTableWidgetItem('44444'))
            # self.tableWidget.setItem(i, 4, QTableWidgetItem('55555'))
            # self.tableWidget.setItem(i, 5, QTableWidgetItem('66666'))
            # self.tableWidget.setItem(i, 6, QTableWidgetItem('777777'))

        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # edit 금지 모드

    def editCartonIDPressed(self):
        if self.edit_CartonID.text() == '':
            return

        self.btnSearchClicked()

    def editPalletIDPressed(self):
        if self.edit_PalletID.text() == '':
            return

        self.edit_CartonID.setText('')

        self.btnSearchClicked()

        self.edit_PalletID.setFocus()

    def btnSearchClicked(self):
        if self.edit_CartonID.text() == '' and self.edit_PalletID.text() == '':
            QMessageBox.warning(self, 'No Input Data', 'Please Input (CartronID or Pallet ID)')
            self.edit_CartonID.setFocus()
            return

        if self.dbConn == '':
            QMessageBox.warning(self, 'DB connection.', 'DB connection failed.')
            self.edit_CartonID.setFocus()
            return

        # 그리드 초기화
        for i in range(self.tableWidget.rowCount()):
            self.tableWidget.removeRow(0)

        try:
            ##########################################################################################################
            # Carton ID, Pallet ID로 데이터 검색
            with self.dbConn.cursor() as cursor:
                if self.edit_CartonID.text() != '':
                    # Carton ID로 검색할 때는 Pallet ID를 공백 처리한다.
                    self.edit_PalletID.setText('')
                    sql = '''
                        select *,
                            (	select pallet_id  
                                from pallet_print pp
                                where 
                                    date(create_date) = date(csi.work_date)
                                and	pp.pallet_no = csi.pallet_no 
                                order by create_date desc limit 1
                            ) as pallet_id,
                            (	select create_date
                                from pallet_print pp
                                where 
                                    date(create_date) = date(csi.work_date)
                                and	pp.pallet_no = csi.pallet_no 
                                order by create_date desc limit 1
                            ) as print_date
                        from carton_scan_info csi 
                        where 1 = 1
                        and carton_id = '{0}'
                    '''.format(self.edit_CartonID.text())

                    sql += 'limit 10'

                # Pallet ID에 입력 값이 있다면, Pallet ID와 연결된 모든 제품 정보를 보여준다.
                elif self.edit_PalletID.text() != '':
                    self.edit_CartonID.setText('')
                    sql = '''
                        select csi.pallet_no, csi.model_name, carton_id, pp.pc_name, csi.work_date, pp.pallet_id, pp.create_date as print_date
                        from carton_scan_info csi 
                        join pallet_print pp
                        on 
                            pp.pallet_id = '{0}'
                        and	date_format(csi.work_date, '%Y%m%d') = date_format(pp.create_date, '%Y%m%d')
                        and csi.model_name = pp.model_name 
                        and csi.pallet_no = pp.pallet_no  
                        '''.format(self.edit_PalletID.text())

                cursor.execute(sql)

                if cursor.rowcount == 0:
                    QMessageBox.information(self, 'No Data', 'No Search Data!!')
                    return

                for i, row in enumerate(cursor.fetchall()):
                    self.tableWidget.insertRow(i)
                    self.tableWidget.setItem(i, 0, QTableWidgetItem(row['pallet_no']))
                    self.tableWidget.setItem(i, 1, QTableWidgetItem(row['model_name']))
                    self.tableWidget.setItem(i, 2, QTableWidgetItem(row['carton_id']))
                    self.tableWidget.setItem(i, 3, QTableWidgetItem(row['pc_name']))
                    self.tableWidget.setItem(i, 4, QTableWidgetItem(str(row['work_date'])))
                    self.tableWidget.setItem(i, 5, QTableWidgetItem(row['pallet_id']))
                    self.tableWidget.setItem(i, 6, QTableWidgetItem(str(row['print_date'])))
            ##########################################################################################################
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Data Searching Error', str(e))
            return

        self.edit_CartonID.setFocus()

    def showModal(self):
        return self.exec()


if __name__ == '__main__':
    app = QApplication()
    window = PalletSearchDialog()
    window.show()
    app.exec()