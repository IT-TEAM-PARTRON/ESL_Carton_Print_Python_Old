from PySide6.QtWidgets import QApplication, QDialog, QAbstractItemView, QTableWidgetItem, QMessageBox
from CartonSearchUI import Ui_dlgProductSearch
from pymysql.connections import Connection


class CartonSearchDialog(QDialog, Ui_dlgProductSearch):

    def __init__(self, *args, **kwargs):
        super(CartonSearchDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.__make_table_layout()
        self.setWindowTitle('Product Search Window')
        self.dbConn: Connection = ''

    def __make_table_layout(self):
        # table 헤더 컬럼 속성 부여
        self.tableWidget.setColumnCount(8)
        self.tableWidget.setHorizontalHeaderLabels(["CTN No.", "Model Name", "MAC", "S/N", "PC Name", "WORK DATE", "Carton ID", "Print Date"])
        self.tableWidget.horizontalHeader().setStyleSheet("QHeaderView::section {background-color:#401040;color:#FFFFFF;}")
        # self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # table 헤더 컬럼 사이즈 조절
        self.tableWidget.setColumnWidth(0, self.width() * 10 / 100)
        self.tableWidget.setColumnWidth(1, self.width() * 11 / 100)
        self.tableWidget.setColumnWidth(2, self.width() * 11 / 100)
        self.tableWidget.setColumnWidth(3, self.width() * 11 / 100)
        self.tableWidget.setColumnWidth(4, self.width() * 13 / 100)
        self.tableWidget.setColumnWidth(5, self.width() * 13 / 100)
        self.tableWidget.setColumnWidth(6, self.width() * 13 / 100)
        self.tableWidget.setColumnWidth(7, self.width() * 13 / 100)

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

    def editMACPressed(self):
        if self.edit_InputMac.text() == '':
            return

        self.btnSearchClicked()

    def editSNPressed(self):
        if self.edit_InputSN.text() == '':
            return

        self.btnSearchClicked()

    def editCartonIDPressed(self):
        if self.edit_CartonID.text() == '':
            return

        # Carton ID로 검색할 때는 MAC과 SN을 초기화 한다.
        self.edit_InputMac.setText('')
        self.edit_InputSN.setText('')

        self.btnSearchClicked()

    def btnSearchClicked(self):
        if self.edit_InputMac.text() == '' and self.edit_InputSN.text() == '' and self.edit_CartonID.text() == '':
            QMessageBox.warning(self, 'No Input Data', 'Please Input (MAC or SN or CartonID)')
            self.edit_InputMac.setFocus()
            return

        if self.dbConn == '':
            QMessageBox.warning(self, 'DB connection.', 'DB connection failed.')
            self.edit_InputMac.setFocus()
            return

        # 그리드 초기화
        for i in range(self.tableWidget.rowCount()):
            self.tableWidget.removeRow(0)

        try:
            ##########################################################################################################
            # MAC, SN 검색할 때와 Carton ID로 검색할때의 쿼리가 다르기 때문에 분기 처리하여 조회한다.
            with self.dbConn.cursor() as cursor:
                # MAC, SN 둘중에 하나라도 입력 값이 있다면 제품 검색 쿼리를 실행한다.
                if self.edit_InputMac.text() != '' or self.edit_InputSN.text() != '':
                    # MAC, SN으로 검색할 때는 CartonID를 공백 처리한다.
                    self.edit_CartonID.setText('')
                    sql = '''
                        select *,
                            (	select carton_id 
                                from carton_print cp
                                where 
                                    date(create_date) = date(pi2.work_date)
                                and	cp.CTN_No = pi2.CTN_No 
                                and cp.model_name = pi2.model_name
                                order by create_date desc limit 1
                            ) as carton_barcode,
                            (	select create_date
                                from carton_print cp
                                where 
                                    date(create_date) = date(pi2.work_date)
                                and	cp.CTN_No = pi2.CTN_No 
                                and cp.model_name = pi2.model_name
                                order by create_date desc limit 1
                            ) as print_date
                        from product_info pi2 
                        where 1 = 1
                        '''
                    if self.edit_InputMac.text() != '':  # Mac 검색값을 입력했을때 sql문 추가
                        sql += '''and MAC = '{0}'
                                '''.format(self.edit_InputMac.text())

                    if self.edit_InputSN.text() != '':  # SN 검색값을 입력했을때 sql문 추가
                        sql += '''and SN = '{0}'
                                '''.format(self.edit_InputSN.text())

                    sql += 'limit 10'

                # Carton ID에 입력 값이 있다면, Carton ID와 연결된 모든 제품 정보를 보여준다.
                elif self.edit_CartonID.text() != '':
                    sql = '''
                        select pi2.CTN_No, pi2.model_name, pi2.MAC, pi2.SN, cp.pc_name, pi2.work_date, cp.carton_id as carton_barcode, cp.create_date as print_date
                        from product_info pi2 
                        join carton_print cp
                        on 
                            cp.carton_id = '{0}'
                        and	date_format(work_date, '%Y%m%d') = date_format(cp.create_date, '%Y%m%d')
                        and pi2.model_name = cp.model_name 
                        and pi2.CTN_No = cp.CTN_No  
                        '''.format(self.edit_CartonID.text())

                cursor.execute(sql)

                if cursor.rowcount == 0:
                    QMessageBox.information(self, 'No Data', 'No Search Data!!')
                    return

                for i, row in enumerate(cursor.fetchall()):
                    self.tableWidget.insertRow(i)
                    self.tableWidget.setItem(i, 0, QTableWidgetItem(row['CTN_No']))
                    self.tableWidget.setItem(i, 1, QTableWidgetItem(row['model_name']))
                    self.tableWidget.setItem(i, 2, QTableWidgetItem(row['MAC']))
                    self.tableWidget.setItem(i, 3, QTableWidgetItem(row['SN']))
                    self.tableWidget.setItem(i, 4, QTableWidgetItem(row['pc_name']))
                    self.tableWidget.setItem(i, 5, QTableWidgetItem(str(row['work_date'])))
                    self.tableWidget.setItem(i, 6, QTableWidgetItem(row['carton_barcode']))
                    self.tableWidget.setItem(i, 7, QTableWidgetItem(str(row['print_date'])))
            ##########################################################################################################
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Data Searching Error', str(e))
            return

        self.edit_InputMac.setFocus()

    def showModal(self):
        return self.exec()


if __name__ == '__main__':
    app = QApplication()
    window = CartonSearchDialog()
    window.show()
    app.exec()