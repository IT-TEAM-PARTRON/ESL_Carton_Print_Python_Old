import sys
from PySide6.QtWidgets import QApplication, QDialog, QAbstractItemView, QTableWidgetItem, QMessageBox
from pymysql.connections import Connection
from PalletLableUI import Ui_Dialog
from PalletAddrDlg import PalletAddresDialog as addrDlg
from PalletSearchDlg import PalletSearchDialog as palletDlg
from INIConfig import INIConfig as INI  # lib for INI Config file
from zebra import Zebra
import pymysql
import socket
import pyautogui

DEBUG = False
VERSION = '[ESL] Pallet Print V1.1.0'

# V1.0.3(20240810)
#  1. 법인 출장가서 마지막 배포 버전
#
# V1.1.0(아직 미배포)
#  1. 주소 수정 팝업에서 모델명 정렬 추가(order by model_name)

class MainDialog(QDialog, Ui_Dialog):

    def __init__(self, *args, **kwargs):
        super(MainDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle(VERSION)
        self.dbConn: Connection = self.__database_connect()
        self.model_name = ''
        self.model_info = ['', '', '', '', '', '', '', '', 0]
        self.model_type = ''
        self.model_index = 0
        self.nowDay = ''

        self.__make_ModelList()
        self.__make_table_layout()
        self.pc_name = socket.gethostname()

        # ini 파일에서 디버그 모드 변경(True / False)
        global DEBUG
        DEBUG = config.getINI('SETTING', 'DEBUG_MODE')

    def __make_ModelList(self):

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

    def __make_table_layout(self):
        # table 헤더 컬럼 속성 부여
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setHorizontalHeaderLabels(["MODEL Name", "PALLET No.", "CARTON ID", "WORK DATE"])
        self.tableWidget.horizontalHeader().setStyleSheet(
            "QHeaderView::section {background-color:#401040;color:#FFFFFF;}")
        # self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # table 헤더 컬럼 사이즈 조절
        self.tableWidget.setColumnWidth(0, self.width() * 17 / 100)
        self.tableWidget.setColumnWidth(1, self.width() * 15 / 100)
        self.tableWidget.setColumnWidth(2, self.width() * 30 / 100)
        self.tableWidget.setColumnWidth(3, self.width() * 30 / 100)

        # i = 0
        # while i < 300:
        #     self.tableWidget.insertRow(i)
        #     i += 1

        # self.tableWidget.insertRow(0)

        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # edit 금지 모드

    def comboModelChanged(self):
        if self.combo_ModelList.currentText() == 'Select Model':
            return

        ##############################################################################################################
        # 모델 선택이 달라질 때 R154모델 같은 경우는 모델명 뒤에 Type이 붙어서 Tokenize를 해서 비교가 필요하다.
        strModelName = self.combo_ModelList.currentText()
        strTokenName = ''
        if ' [' in strModelName:  # 모델명에 ' ['이 있다면... type앞에 모델명만 가져오도록 처리
            strTokenName = strModelName[0:strModelName.find(' [')]
        else:
            strTokenName = strModelName
        ##############################################################################################################

        ##############################################################################################################
        # 모델명을 다른걸 선택 했을 경우 현재 작업한 데이터들은 삭제 처리한다.
        # 만일 'No'를 누르게 되면 이전에 선택한 모델명으로 다시 셋팅을 해 준다.
        if self.tableWidget.rowCount() != 0 and self.model_name != strTokenName:
            ans = QMessageBox.question(self, "Data Delete",
                                       "The current information will be deleted.\n\nDo you want to continue?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.Yes)
            # Yes 버튼과 No 버튼을 생성하고, 기본 값으로 Yes 값이 클릭되어 있음
            if ans == QMessageBox.Yes:
                self.__dataClear()
            else:
                self.combo_ModelList.setCurrentIndex(self.model_index)
                return
        ##############################################################################################################

        ##############################################################################################################
        # 전역 변수에 선택한 모델명과 모델index를 저장한다.
        if ' [' in strModelName:  # 모델명에 ' ['이 있다면... type을 분리하기 위해서
            self.model_name = strModelName[0:strModelName.find(' [')]
            self.model_type = strModelName[strModelName.find(':') + 1:strModelName.find(']')]
        else:
            self.model_name = self.combo_ModelList.currentText()
            self.model_type = ''

        self.model_index = self.combo_ModelList.currentIndex()
        ##############################################################################################################

        ##############################################################################################################
        # model 전체 정보를 배열에 저장한다.
        try:
            with self.dbConn.cursor() as cursor:
                sql = '''
                    select 
                        ctn_model_code ,
                        ctn_opt_code,
                        from_addr1,
                        from_addr2,
                        from_addr3,
                        to_addr1,
                        to_addr2,
                        to_addr3,
                        box_fer_pallet
                    from model_info 
                    where 
                        model_name = '{0}'
                    and model_type = '{1}'
                '''.format(self.model_name, self.model_type)
                cursor.execute(sql)

                if cursor.rowcount == 0:
                    return

                for row in cursor.fetchall():
                    self.model_info = [row['ctn_model_code'], row['ctn_opt_code'], row['from_addr1'], row['from_addr2'],
                                       row['from_addr3'], row['to_addr1'], row['to_addr2'], row['to_addr3'],
                                       row['box_fer_pallet']]
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Model Changed Error', str(e))
            return
        ##############################################################################################################

        if DEBUG == True: QMessageBox.information(self, 'info', str(self.model_info))

        self.edit_ChoicedModel.setText(self.model_name)
        self.edit_CartonID.setFocus()

        self.__dataSetting()

    def __dataSetting(self):

        self.dbConn.commit()

        #########################################################################################################
        # 모델별 Today Carton/Pallet 카운트 셋팅
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute('''
					select count(0) as box_cnt , sum(cnt) as prd_cnt
                    from (
                        select pallet_no, count(0) as cnt
                        from carton_scan_info csi
                        where 
                            work_date > curdate()
                        and model_name = %s
                        and pc_name = %s
                        and pallet_no in (	select pallet_no /*라벨 출력 완료한 박스만*/
                                        from pallet_info 
                                        where 
                                            regist_date > curdate()
                                        and model_name = %s
                                        and pc_name = %s
                                        and label_print_YN = 'Y')	
                        group by pallet_no
                        order by pallet_no desc                    
                    ) pi	''', (self.model_name, self.pc_name, self.model_name, self.pc_name))

                for row in cursor.fetchall():
                    if row['box_cnt'] != 0:  # 오늘 작업한게 한건 이상일 경우만 카운트 표시
                        self.lcd_TodayCarton.display(int(row['prd_cnt']))
                        self.lcd_TodayPallet.display(int(row['box_cnt']))
                    else:
                        self.lcd_TodayCarton.display(0)
                        self.lcd_TodayPallet.display(0)
            #########################################################################################################

            #########################################################################################################
            # DB에 당일 작업중인 모델별 제품 정보를 그리드에 데이터 채우기
            with self.dbConn.cursor() as cursor:
                cursor.execute('''  
                        select *
                        from	
                            carton_scan_info csi
                        where                        
                            work_date > curdate()
                        and model_name = %s
                        and pc_name = %s
                        and pallet_no  =(select pallet_no 
                                            from pallet_info pi2 
                                            where 
                                                regist_date > curdate()
                                            and model_name = %s
                                            and label_print_YN = 'N'
                                            and pc_name = %s
                                            order by regist_date asc limit 1
                                        )
                        order by work_date desc
                    ''', (self.model_name, self.pc_name, self.model_name, self.pc_name))

                self.edit_Grid_Cnt.setText(str(cursor.rowcount))    

                for i in range(self.tableWidget.rowCount()):
                    self.tableWidget.removeRow(0)

                if cursor.rowcount == 0:
                    return

                for i, row in enumerate(cursor.fetchall()):
                    self.tableWidget.insertRow(i)
                    self.tableWidget.setItem(i, 0, QTableWidgetItem(row['model_name']))
                    self.tableWidget.setItem(i, 1, QTableWidgetItem(row['pallet_no']))
                    self.tableWidget.setItem(i, 2, QTableWidgetItem(row['carton_id']))
                    self.tableWidget.setItem(i, 3, QTableWidgetItem(str(row['work_date'])))
            ##########################################################################################################
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Data Setting Error', str(e))
            return
    def InputCartonCheck(self):
        strCartonID = self.edit_CartonID.text()
        if strCartonID == '':
            return

        ###############################################################################################################
        # 기본 interlock 체크
        if self.combo_ModelList.currentText() == 'Select Model':
            QMessageBox.information(self, 'Not Select Model', 'Please select a model')
            self.edit_CartonID.setText('')
            return
        if len(self.edit_CartonID.text()) != 16:
            QMessageBox.warning(self, 'Carton ID Check', 'Invalid CartonID Size, Please Check Agin.')
            self.edit_CartonID.setText('')
            return

        # 모델별 Carton Model Code(model_info.ctn_model_code)와 Carton ID의 6번째 코드와 비교
        if self.model_info[0] != strCartonID[5:6]:
            QMessageBox.warning(self, 'Carton ID Check', 'Invalid Model Code, Please Check Agin.')
            self.edit_CartonID.setText('')
            return

        # 모델별 Carton Option Code(model_info.ctn_opt_code)와 Carton ID의 7번째 코드와 비교
        if self.model_info[1] != strCartonID[6:7]:
            QMessageBox.warning(self, 'Carton ID Check', 'Invalid Option Code, Please Check Agin.')
            self.edit_CartonID.setText('')
            return

        # 모델별 색상/돌기와 Carton ID의 8, 9번째 코드와 비교
        if self.model_name[-2:] != strCartonID[7:9]:
            QMessageBox.warning(self, 'Carton ID Check', 'Invalid Color Code, Please Check Agin.')
            self.edit_CartonID.setText('')
            return
        ###############################################################################################################

        ###############################################################################################################
        # DB에 같은 Carton ID가 있는지 체크
        now_date = ''
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute(
                    "select count(0) as cnt, now() as nowdate, date_format(now(), '%Y%m%d') as nowday from carton_scan_info where carton_id = '{0}'".format(
                        self.edit_CartonID.text()))

                for row in cursor.fetchall():
                    now_date = str(row['nowdate'])

                    # 그리드를 초기화 하기 위해서 하루가 지날 경우 프로그램 재 실행
                    if self.nowDay != '' and self.nowDay != row['nowday']:
                        QMessageBox.warning(self, 'Program Restart', 'Please Program Restarting Now!!!')
                        sys.exit(0)  # 프로그램 종료
                        return
                    elif self.nowDay == '':  # self.nowDay가 공백일 경우(첫 실행)
                        self.nowDay = row['nowday']  # 당일 날짜를 넣어준다.

                    if int(row['cnt']) > 0:
                        QMessageBox.critical(self, 'Duplicate errors',
                                             'MAC :: [' + strCartonID + '] A matching Carton ID already exists!!!')
                        self.edit_CartonID.setText('')
                        return

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Critical Error-Carton Check::1', str(e))
            return
        ###############################################################################################################

        ###############################################################################################################
        # CTN No 구하기
        try:
            rowCount = self.tableWidget.rowCount()
            pallet_no = ''
            palletInsert_Flag = False

            # 제품 정보가 화면 테이블에 없을 경우 DB의 당일 기준으로 마지막 Pallet No를 가져와서 +1을 한다.
            # 만일 당일 기준으로 첫 작업이라면 01을 부여한다.
            if rowCount == 0:  # 그리드에 제품이 없을 경우
                with self.dbConn.cursor() as cursor:
                    # 모델명 뒤에 MP를 붙인 동일한 모델정보가 있어서 CTN_No를 구할때는 MP를 제거하고 조회
                    # 같은 모델명인데 MP가 붙은거와 안 붙은거는 같은 모델임(고객 요청 사항
                    # ex) R266NRCLB_HW, R266NRCLB_HWMP <== 같은 기준 정보를 가진 모델(현품표 모델코드와 옵션코드도 동일)
                    # 이렇게 모델명만 사용하지 않는다면, 모델별로 CTN_No를 구하기 때문에 카톤 라벨이 중복 발생이 가능함
                    nIndex = self.model_name.find('_')
                    model_name = self.model_name[:nIndex + 3]
                    sql = '''  
                        select pallet_no 
                        from 
                            pallet_info  
                        where 
                            regist_date > curdate()
                        and model_name like '{0}%'                            
                        order by pallet_no desc limit 1
                        '''.format(model_name)
                    cursor.execute(sql)

                    # 당일 첫 작업일 경우...
                    if cursor.rowcount == 0:
                        pallet_no = '01'
                        palletInsert_Flag = True

                    # 당일 Pallet No가 있을 경우 뒷 2자리 숫자에서 +1을 한다.
                    for row in cursor.fetchall():
                        pallet_no = str(int(row['pallet_no']) + 1).zfill(2)
                        palletInsert_Flag = True
            else:
                pallet_no = self.tableWidget.item(0, 1).text()  # 첫번째 열의 Pallet No를 가져온다.

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Critical Error-Carton Check::2', str(e))
            return
        ###############################################################################################################

        ###############################################################################################################
        # DB와 그리드에 데이터 저장하기
        # DB carton_info, product_info 테이블에 저장
        try:
            sql = ''
            # Pallet No를 새로 발번할 경우 pallet_info 테이블에 저장한다.
            if palletInsert_Flag:
                with self.dbConn.cursor() as cursor:
                    cursor.execute('''
                        insert into pallet_info (pc_name, model_name, pallet_no, label_print_YN, regist_date)
                        values(%s, %s, %s, 'N', %s)
                    ''', (self.pc_name, self.model_name, pallet_no, now_date))

            # carton_info 테이블에 데이터를 넣고 product_info 테이블에도 저장한다.
            with self.dbConn.cursor() as cursor:
                cursor.execute('''
                    insert into carton_scan_info (model_name, carton_id, pallet_no, pc_name, work_date)
                    values(%s, %s, %s, %s, %s)
                ''', (self.model_name, strCartonID, pallet_no, self.pc_name, now_date))

            self.dbConn.commit()

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Critical Error-Carton Check::3', str(e))
            return

        # 화면 테이블에 제품정보 추가하기
        self.tableWidget.insertRow(0)
        self.tableWidget.setItem(0, 0, QTableWidgetItem(self.model_name))
        self.tableWidget.setItem(0, 1, QTableWidgetItem(pallet_no))
        self.tableWidget.setItem(0, 2, QTableWidgetItem(strCartonID))
        self.tableWidget.setItem(0, 3, QTableWidgetItem(now_date))
        ###############################################################################################################

        self.edit_Grid_Cnt.setText(str(rowCount + 1))

        if self.tableWidget.rowCount() == self.model_info[8]:
            self.__palletLabelPrint()

        self.edit_CartonID.setText('')
        self.edit_CartonID.setFocus()

    def __palletLabelPrint(self):
        strDate = ''  # 라벨에 당일 년월일(2024.06.17

        with self.dbConn.cursor() as cursor:
            cursor.execute('''select date_format(now(), '%Y.%m.%d') as date from dual''')

            for row in cursor.fetchall():
                strDate = row['date']

        nYear = int(strDate[0:4])
        nMonth = int(strDate[5:7])
        nDay = int(strDate[8:10])

        # 라벨(현품표) 바코드 내 년월일 문자열 만들기
        # 참조 파일 : 2.ESL_OQC_Process_Flow.xlsx
        # Year : 2015(A), 2016(B).....2024(J), 2025(K)
        # Month : 1(A), 2(B)....12(L)
        # Day : 1(1), 2(2), 3(3)....9(9), 10(A), 11(B).....31(V)
        strYear = chr(ord("A") + nYear - 2015)  # 아스키코드 값을 캐릭터형으로 변환
        strMonth = chr(ord("A") + nMonth - 1)
        strDay = ''
        if nDay < 10:
            strDay = str(nDay)  # 1~9까지 숫자는 스트링형으로 변환
        else:
            strDay = chr(ord("A") + nDay - 10)

        # 그리드 첫번째 열에 있는 pallet no 가져오기
        strPallet_No = self.tableWidget.item(0, 1).text()

        # 라벨(현품표) 바코드 만들기
        strBarcode = ('PM' + strYear + strMonth + strDay + self.model_info[0] + self.model_info[1] +
                      self.model_name[-2:] + strPallet_No)

        zpl_code = '''
        ^XA

        //Darkness, Print Speed, Label Width
        ~SD{0}^PR{1}^PW{2}
        
        //Label Position
        ^LH{3}^LT{4}FS
        
        //Label layout
        ^FO392,74^GB0,1628,7^FS
        ^FO111,74^GB1036,1628,7^FS
        ^FO111,192^GB1036,0,7^FS
        ^FO111,319^GB1036,0,7^FS
        ^FO111,710^GB1036,0,7^FS
        ^FO111,1095^GB1036,0,7^FS
        ^FO111,1223^GB1036,0,7^FS
        
        //Vendor
        ^FO190,111^AQN,59,59^FDVendor^FS
        ^FO575,111^AQN,59,59^FDPartron VINA CORP.^FS
        
        //Model Name
        ^FO195,237^AQN,59,59^FDModel^FS
        ^FO598,237^AQN,59,59^FD{5}^FS
        
        //Ship From Address
        ^FO160,481^AQN,59,59^FDShip From^FS
        ^FO430,355^AQN,52,52^FD{6}^FS
        ^FO430,481^AQN,52,52^FD{7}^FS
        ^FO430,599^AQN,52,52^FD{8}^FS
        
        //Ship To Address
        ^FO190,865^AQN,59,59^FDShip to^FS
        ^FO430,755^AQN,52,52^FD{9}^FS
        ^FO430,865^AQN,52,52^FD{10}^FS
        ^FO430,983^AQN,52,52^FD{11}^FS
        
        //Box Count
        ^FO183,1139^AQN,59,59^FDBox Qty.^FS
        ^FO720,1139^AQN,59,59^FD{12}EA^FS
        
        //Pallet Barcode
        ^FO168,1433^AQN,59,59^FDPallet ID#^FS
        ^FO630,1353^AQN,59,59^FD{13}^FS
        ^FO540,1480^BY3^BCN,80,Y,N,N,N^FD{14}^FS
        ^XZ
        '''.format(config.getINI('PRINT_SETTING', 'darkness'), config.getINI('PRINT_SETTING', 'speed'),
                   config.getINI('PRINT_SETTING', 'prn_width'), config.getINI('PRINT_SETTING', 'label_pos_x'),
                   config.getINI('PRINT_SETTING', 'label_pos_y'), self.model_name, self.model_info[2],
                   self.model_info[3],
                   self.model_info[4], self.model_info[5], self.model_info[6], self.model_info[7],
                   self.edit_Grid_Cnt.text(), strBarcode, strBarcode)

        if config.getINI('SETTING', 'label_msg') == 'Y':
            QMessageBox.information(self, 'ZPL Code', zpl_code)

        # Zebra Print를 이용해서 프린트 출력
        try:
            if DEBUG == True:
                QMessageBox.information(self, 'Zebra Print Code', zpl_code)
            else:
                printer = Zebra(config.getINI('SETTING', 'print_name'))
                printer.output(zpl_code)  # generate_zpl 함수에서 생성한 ZPL 코드를 사용
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Zebra Print Check', 'The print name is invalid.\n\n' + str(e))
            return

        ###############################################################################################################
        # 프린트 출력하고 나서 출력 이력 남기고 pallet_info Y로 업데이트
        try:
            with self.dbConn.cursor() as cursor:
                # 라벨 출력 완료되면 pallet_no 기준으로 라벨 출력값을 Y로 변경하고 다음 pallet_no를 발번할수 있게 한다.
                cursor.execute('''
                    update pallet_info 
                    set label_print_YN = 'Y'
                    where
                        regist_date > curdate()
                    and model_name = %s
                    and pc_name = %s
                    and pallet_no = %s
                ''', (self.model_name, self.pc_name, strPallet_No))

                # 출력하는 zplcode를 테이블에 저장
                # 추후 이력을 추적하기 위해서 사용
                cursor.execute('''
                    insert into pallet_print (pc_name, model_name, pallet_no, pallet_id, zplcode)
                    values(%s, %s, %s, %s, %s)
                ''', (self.pc_name, self.model_name, strPallet_No, strBarcode, zpl_code))
                self.dbConn.commit()

                self.__dataSetting()  # 프린트 후 화면 다시 셋팅

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Label Insert Error', str(e))
            return
        ###############################################################################################################

        # 그리드 초기화
        for i in range(self.tableWidget.rowCount()):
            self.tableWidget.removeRow(0)

    def btnAddressAddClicked(self):

        if pyautogui.password('Enter password') != '1234':
            QMessageBox.warning(self, 'Password Error', 'Invalid password.')
            return

        win = addrDlg()
        win.showModal()
        self.comboModelChanged()
        return

    def btnDataClearClicked(self):
        if self.tableWidget.rowCount() < 1:
            QMessageBox.information(self, 'No Data', 'The data you want to delete doesnt exist.')
            return

        ans = QMessageBox.question(self, "Data Delete", "Do you want to delete it?", QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.Yes)

        # Yes 버튼과 No 버튼을 생성하고, No일 경우 아무것도 안한다.
        if ans == QMessageBox.No:
            return

        self.__dataClear()

    def __dataClear(self):
        # 그리드 삭제하기 전 DB 데이터를 먼저 삭제한다.
        # 당일/작업PC/작업CTN_No 기준으로 삭제
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute('''
                            delete 
                            from pallet_info
                            where 
                                regist_date > curdate()
                            and model_name = %s
                            and pallet_No = %s
                            and pc_name = %s
                           ''', (self.model_name, self.tableWidget.item(0, 1).text(), self.pc_name))

                cursor.execute('''
                            delete
                            from carton_scan_info
                            where
                                work_date > curdate() 
                            and model_name = %s
                            and pallet_No = %s
                            and pc_name = %s
                           ''', (self.model_name, self.tableWidget.item(0, 1).text(), self.pc_name))
                self.dbConn.commit()

                self.__dataSetting()  # 데이터 삭제 후 화면 다시 셋팅

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Data Delete Error', str(e))
            return

    def btnDataSearchClicked(self):
        win = palletDlg()
        win.dbConn = self.dbConn
        win.showModal()
        return

    def btnRePrintClicked(self):
        strZplcode = ''

        try:
            # 현재 pc name & 당일 기준으로 마지막 라벨 프린트 한 이력 찾기
            with self.dbConn.cursor() as cursor:
                sql = '''
                            select zplcode  
                            from pallet_print cp
                            where 
                                create_date > curdate()
                            and model_name = '{0}'
                            and pc_name = '{1}'
                            order by create_date desc limit 1
                        '''.format(self.model_name, self.pc_name)
                cursor.execute(sql)

                if cursor.rowcount == 0:
                    QMessageBox.information(self, 'Have No Label Print', 'No prints have been made today.')
                    return

                for row in cursor.fetchall():
                    strZplcode = row['zplcode']
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'RePrint Error', str(e))
            return

        try:
            if DEBUG == True:
                QMessageBox.information(self, 'msg', strZplcode)
            else:
                printer = Zebra(config.getINI('SETTING', 'print_name'))
                printer.output(strZplcode)  # generate_zpl 함수에서 생성한 ZPL 코드를 사용
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Zebra Print Check', 'The print name is invalid.\n\n' + str(e))
            return

    def btnPrintNowClicked(self):
        if self.tableWidget.rowCount() == 0:
            QMessageBox.warning(self, 'No Item', 'There is no printable data.')
            return

        self.__palletLabelPrint()

    def reject(self):
        # ESC를 누르면 창이 닫겨서 안 닫히도록 처리
        # ESC를 누를 때 reject() 이벤트가 발생하게 되고 이때 return으로 아무것도 안하게 처리
        # sys.exit(0)  # ESC 누를 때 종료 처리
        return

    def closeEvent(self, event):
        ans = QMessageBox.question(self, "Close Window", "Do you want to exit?", QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.Yes)
        # Yes 버튼과 No 버튼을 생성하고, 기본 값으로 Yes 값이 클릭되어 있음
        if ans == QMessageBox.Yes:
            # DB Connection 종료 처리(cursor는 with문을 쓰면서 자동 종료되어 별도 처리 안해도 됨)
            self.dbConn.close()
            event.accept()  # Yes 를 누르면 closeEvent
        else:
            event.ignore()  # No 를 누르면 closeEvent 무시

    def __database_connect(self):
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
            sys.exit(0)
            return

        return conn


if __name__ == '__main__':
    app = QApplication()

    try:
        # INI 파일을 컨트롤하기 위한 클래스 참조
        config = INI("./Pallet_config_real.ini")  # 해당 파일이 없으면 False 값을 리턴해서 강제로 Exception으로 빠짐

    except Exception as e:
        # print(pg.alert(text='실행파일 폴더에 Config.ini 파일이 없습니다.', title='Not Read Config.ini', button='OK'))
        QMessageBox.warning(None, 'Not Read Config.ini', '실행파일 폴더에 Pallet_config.ini 파일이 없습니다.')
        sys.exit(0)

    window = MainDialog()
    window.show()
    app.exec()
