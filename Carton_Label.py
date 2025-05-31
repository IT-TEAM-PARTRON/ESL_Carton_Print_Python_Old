import sys
import os
from PySide6.QtWidgets import QApplication, QDialog, QAbstractItemView, QTableWidgetItem, QMessageBox
from CartonLableUI import Ui_Dialog
from CartonSearchDlg import CartonSearchDialog as ctnDlg
from INIConfig import INIConfig as INI  # lib for INI Config file
from pymysql.connections import Connection
from SerialScanInfo import SerialScanInfo
from zebra import Zebra
from MessageBox import MessageBoxClass as MessageBox
import pymysql
import socket

DEBUG = False
VERSION = '[ESL] Carton Print V1.1.1'

# V1.0.9(20240812)
#  1. 법인 출장가서 마지막 배포 버전
#
# V1.1.0(아직 미배포)
#  1. 우측 상단 Convayor 오타 수정(Conveyor)
# ㅇ V1.1.1(20250524)
#     1. database thêm cột model_change trong model_info_v2
#      xử lý trường hợp in label có thêm panid ở tên model

class MainDialog(QDialog, Ui_Dialog):

    def __init__(self, *args, **kwargs):
        super(MainDialog, self).__init__(*args, **kwargs)
        self.conveyor_mode = None
        self.scanThread = None
        self.setupUi(self)
        self.setWindowTitle(VERSION)
        # MAC(size, mcu code, tag type), SN(size, origin_code, model code), CTN(model code, option code) ,model_name_change
        self.model_info = [0, '', '', 0, '', '', '', '','','','','']
        self.model_name = 'Select Model'
        self.model_index = 0
        self.nowDay = ''
        self.dbConn: Connection = self.__database_connect()  # DB 연결
        self.__make_ModelList()  # Model List 가져오기
        self.__make_table_layout()  # Table 생성 함수
        self.pc_name = socket.gethostname()
        self.NG_SN = ''  # 컨베이어에 NG 전송할 때 SN을 보내기 위한 임시 변수

        # ini 파일에서 디버그 모드 변경(True / False)
        if config.getINI('SETTING', 'debug_mode') == 'True':
            global DEBUG
            DEBUG = True

        self.__Init_UI()

    def __Init_UI(self):
        # F/W Version, PAN ID 화면에 셋팅
        self.edit_FW.setText(config.getINI('SETTING', 'FW'))
        self.edit_PanID.setText(config.getINI('SETTING', 'PANID'))
        self.conveyor_mode = config.getINI('SETTING', 'conveyor_mode')
        self.comport = config.getINI('SETTING', 'conveyor_comport')  # 수작업 일 경우 해당 값을 ini에서 공백 처리
        self.scanDelay = float(config.getINI('SETTING', 'scan_delay'))
        self.edit_Comport.setText(self.comport)

        if self.conveyor_mode == 'True':
            self.check_Conveyor.toggle()
            # COMPORT 연결 로직은 setCheckComportChanged() 함수에서 실행 됨
            # 위에 toggle() 함수를 호출했기 때문에 CheckBox 상태값이 바껴서 해당 함수가 호출 됨.
            # 그래서 여기에 Comport 연결 로직을 넣으면 이중 처리되서 오류남

        self.btn_Test.setVisible(False)

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
        self.tableWidget.setHorizontalHeaderLabels(["CTN No.", "MAC", "S/N", "WORK DATE"])
        self.tableWidget.horizontalHeader().setStyleSheet("QHeaderView::section {background-color:#401040;color:#FFFFFF;}")
        # self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # table 헤더 컬럼 사이즈 조절
        self.tableWidget.setColumnWidth(0, self.width() * 15 / 100)
        self.tableWidget.setColumnWidth(1, self.width() * 23 / 100)
        self.tableWidget.setColumnWidth(2, self.width() * 27 / 100)
        self.tableWidget.setColumnWidth(3, self.width() * 27 / 100)

        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # edit 금지 모드

    def comboModelChanged(self):
        if self.combo_ModelList.currentText() == 'Select Model':
            return

        ##############################################################################################################
        #모델 선택이 달라질 때 R154모델 같은 경우는 모델명 뒤에 Type이 붙어서 Tokenize를 해서 비교가 필요하다.
        strModelName = self.combo_ModelList.currentText()
        strTokenName =''
        if ' [' in strModelName:  # 모델명에 ' ['이 있다면... type앞에 모델명만 가져오도록 처리
            strTokenName = strModelName[0:strModelName.find(' [')]
        else:
            strTokenName = strModelName
        ##############################################################################################################

        ##############################################################################################################
        # 모델명을 다른걸 선택 했을 경우 현재 작업한 데이터들은 삭제 처리한다.
        # 만일 'No'를 누르게 되면 이전에 선택한 모델명으로 다시 셋팅을 해 준다.
        if self.tableWidget.rowCount() != 0 and self.model_name != strTokenName:
            ans = QMessageBox.question(self, "Data Delete", "The current information will be deleted.\n\nDo you want to continue?", QMessageBox.Yes | QMessageBox.No,
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
        strModelType = ''
        if ' [' in strModelName:  # 모델명에 ' ['이 있다면... type을 분리하기 위해서
            self.model_name = strModelName[0:strModelName.find(' [')]
            strModelType = strModelName[strModelName.find(':')+1:strModelName.find(']')]
        else:
            self.model_name = self.combo_ModelList.currentText()
        self.model_index = self.combo_ModelList.currentIndex()
        ##############################################################################################################

        ##############################################################################################################
        # model 전체 정보를 배열에 저장한다.
        try:
            with self.dbConn.cursor() as cursor:
                sql = f"select * from model_info where model_name = '{self.model_name}' and model_type = '{strModelType}'"
                cursor.execute(sql)

                if cursor.rowcount == 0:
                    return

                for row in cursor.fetchall():
                    self.model_info = [int(row['mac_size']), row['mcu_code'], row['tag_type'], int(row['sn_size']),
                                       row['origin_code'], row['sn_model_code'], row['ctn_model_code'], row['ctn_opt_code'],
                                       row['prd_fer_box'], row['tray_fer_box'], row['box_fer_pallet'], row['model_name_change']]
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Model Changed Error', str(e))
            # sys.exit(0)  # 프로그램 종료
            os._exit(os.EX_OK)
            return
        ##############################################################################################################

        self.edit_ChoicedModel.setText(self.model_name)
        self.lcd_PrdBoxCnt.display(self.model_info[8])
        self.lcd_TrayBoxCnt.display(self.model_info[9])
        self.lcd_RemainTray.display(self.model_info[9])

        self.edit_InputMac.setText('')
        self.edit_InputSN.setText('')
        self.edit_InputMac.setFocus()
        self.__dataSetting()

    def __dataSetting(self):

        self.dbConn.commit()

        #########################################################################################################
        # 모델별 Today Product/Box 카운트 셋팅
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute('''  
                    select count(0) as box_cnt , sum(cnt) as prd_cnt
                    from (
                        select CTN_No, count(0) as cnt
                        from product_info pi2
                        where 
                            work_date > curdate()
                        and model_name = %s
                        and pc_name = %s
                        and ctn_no in (	select ctn_no /*라벨 출력 완료한 박스만*/
                                        from carton_info 
                                        where 
                                            regist_date > curdate()
                                        and model_name = %s
                                        and pc_name = %s
                                        and label_print_YN = 'Y')	
                        group by CTN_No
                        order by ctn_no desc 
                    ) pi	
                    ''', (self.model_name, self.pc_name, self.model_name, self.pc_name))

                for row in cursor.fetchall():
                    if row['box_cnt'] != 0:  # 오늘 작업한게 한건 이상일 경우만 카운트 표시
                        self.lcd_TodayProduct.display(int(row['prd_cnt']))
                        self.lcd_TodayBox.display(int(row['box_cnt']))
                    else:
                        self.lcd_TodayProduct.display(0)
                        self.lcd_TodayBox.display(0)
            #########################################################################################################

            #########################################################################################################
            # DB에 당일 작업중인 모델별 제품 정보를 그리드에 데이터 채우기
            with self.dbConn.cursor() as cursor:
                cursor.execute('''  
                    select pi2.*
                    from	
                        product_info pi2 	
                    where                        
                        work_date > curdate()
                    and model_name = %s
                    and pc_name = %s
                    and pi2.CTN_No =(select CTN_No 
                                        from carton_info
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
                    self.tableWidget.setItem(i, 0, QTableWidgetItem(row['CTN_No']))
                    self.tableWidget.setItem(i, 1, QTableWidgetItem(row['MAC']))
                    self.tableWidget.setItem(i, 2, QTableWidgetItem(row['SN']))
                    self.tableWidget.setItem(i, 3, QTableWidgetItem(str(row['work_date'])))
            ##########################################################################################################
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Data Setting Error', str(e))
            return

        # F/W Version, PAN ID 화면에 셋팅
        self.edit_FW.setText(config.getINI('SETTING', 'FW'))
        self.edit_PanID.setText(config.getINI('SETTING', 'PANID'))

    def InputMacCheck(self):
        strMac = self.edit_InputMac.text()
        if strMac == '':
            return False

        if self.combo_ModelList.currentText() == 'Select Model':
            if self.conveyor_mode == 'True':
                self.scanThread.mac = ''
                self.scanThread.sn = ''

            # self.scanThread.isWorking = False  # Thread 일시 중지. 쓰레드를 잠시 멈추기 위해서 사용
            MessageBox.information(self, 'Not Select Model', 'Please select a model')
            self.edit_InputMac.setText('')
            # self.scanThread.isWorking = True  # Thread 다시 시작
            return False

        model_mac_size = self.model_info[0]
        model_mcu_code = self.model_info[1]
        model_tag_type = self.model_info[2]

        ###############################################################################################################
        # Mac 인터락 체크
        # ex data)R213 모델 : 25B6D3EBA
        if len(strMac) != model_mac_size:
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.warning(self, 'MacAddress Check', 'Invalid size, Please Check Agin.')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                self.edit_InputMac.setText('')
            else:
                self.scanThread.write_bits_data(self.NG_SN + 'NG')
                if DEBUG == True:  print('Because NG :: model_mac_size({0})'.format(strMac))
            return False
        elif strMac[0:1] != model_mcu_code:
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.warning(self, 'MacAddress Check', 'Invalid MCU Code, Please Check Agin.')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                self.edit_InputMac.setText('')
            else:
                try:
                    self.scanThread.write_bits_data(self.NG_SN + 'NG')
                except Exception as e:
                    print("error : {0}".format(e))
                if DEBUG == True:  print('Because NG :: model_mcu_code({0})'.format(strMac))
            return False
        elif strMac[7:9] != model_tag_type:
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.warning(self, 'MacAddress Check', 'Invalid Tag Type, Please Check Agin.')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                self.edit_InputMac.setText('')
            else:
                self.scanThread.write_bits_data(self.NG_SN + 'NG')
                if DEBUG == True:  print('Because NG :: model_tag_type({0})'.format(strMac))
            return False

        try:
            # DB에 같은 MAC이 있는지 체크
            with self.dbConn.cursor() as cursor:
                cursor.execute("select mac from product_info where mac = '{0}'".format(strMac))

                if cursor.rowcount > 0:
                    if self.conveyor_mode != 'True':
                        # self.scanThread.isWorking = False  # Thread 일시 중지
                        MessageBox.critical(self, 'Duplicate errors', 'MAC :: ['+strMac+'] A matching MAC already exists!!!')
                        # self.scanThread.isWorking = True  # Thread 다시 시작
                        self.edit_InputMac.setText('')
                    else:
                        self.scanThread.write_bits_data(self.NG_SN + 'NG')
                        if DEBUG == True:  print('Because NG :: Duplicate({0})'.format(strMac))

                    return False

        except Exception as e:
            print("error : {0}".format(e))
            # self.scanThread.isWorking = False  # Thread 일시 중지
            QMessageBox.critical(self, 'Mac Chek Error', str(e))
            # self.scanThread.isWorking = True  # Thread 다시 시작
            self.edit_InputMac.setText('')
            return
        ###############################################################################################################

        self.edit_InputSN.setFocus()

    def InputSnCheck(self):
        # 모델 선택했는지 체크
        if self.model_name == 'Select Model':
            # self.scanThread.isWorking = False  # Thread 일시 중지
            MessageBox.information(self, 'Not Select Model', 'Please select a model')
            # self.scanThread.isWorking = True  # Thread 다시 시작
            self.edit_InputMac.setText('')
            self.edit_InputSN.setText('')
            return False

        if self.edit_InputMac.text() == '':
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.information(self, 'Mac Check', 'Please Mac Check')
                self.edit_InputSN.setText('')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                return

        strSN = self.edit_InputSN.text()

        model_sn_size = self.model_info[3]
        model_origin_code = self.model_info[4]
        model_sn_model_code = self.model_info[5]

        # Mac Check 수행
        # ex data)R213 모델 : ZDHKC0135C3
        if len(strSN) != model_sn_size:
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.warning(self, 'SerialNumber Check', 'Invalid size, Please Check Agin.')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                self.edit_InputSN.setText('')
            else:
                self.scanThread.write_bits_data(strSN + 'NG')
                if DEBUG == True: print('Because NG :: model_sn_size({0})'.format(strSN))
            return False
        elif strSN[1:2] != model_origin_code:
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.warning(self, 'SerialNumber Check', 'Invalid Origin Code, Please Check Agin.')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                self.edit_InputSN.setText('')
            else:
                self.scanThread.write_bits_data(strSN + 'NG')
                if DEBUG == True: print('Because NG :: model_origin_code({0})'.format(strSN))
            return False
        elif strSN[4:5] != model_sn_model_code:
            if self.conveyor_mode != 'True':
                # self.scanThread.isWorking = False  # Thread 일시 중지
                MessageBox.warning(self, 'SerialNumber Check', 'Invalid Model Code, Please Check Agin.')
                # self.scanThread.isWorking = True  # Thread 다시 시작
                self.edit_InputSN.setText('')
            else:
                self.scanThread.write_bits_data(strSN + 'NG')
                if DEBUG == True: print('Because NG :: model_sn_model_code({0})'.format(strSN))
            return False

        ###############################################################################################################
        # DB에 같은 SN이 있는지 체크
        now_date = ''
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute("select count(0) as cnt, now() as nowdate, date_format(now(), '%Y%m%d') as nowday from product_info where sn = '{0}'".format(strSN))

                for row in cursor.fetchall():
                    now_date = str(row['nowdate'])

                    # 그리드를 초기화 하기 위해서 하루가 지날 경우 프로그램 재 실행
                    if self.nowDay != '' and self.nowDay != row['nowday']:
                        # self.scanThread.isWorking = False  # Thread 일시 중지
                        MessageBox.warning(self, 'Program Restart', 'Please Program Restarting Now!!!')
                        # self.scanThread.isWorking = True  # Thread 다시 시작
                        sys.exit(0)  # 프로그램 종료
                        return
                    elif self.nowDay == '':  # self.nowDay가 공백일 경우(첫 실행)
                        self.nowDay = row['nowday']  # 당일 날짜를 넣어준다.

                    if int(row['cnt']) > 0:
                        if self.conveyor_mode != 'True':
                            # self.scanThread.isWorking = False  # Thread 일시 중지
                            MessageBox.critical(self, 'Duplicate errors',
                                                 'SN :: [' + strSN + '] A matching SN already exists!!!')
                            # self.scanThread.isWorking = True  # Thread 다시 시작
                            self.edit_InputSN.setText('')
                        else:
                            self.scanThread.write_bits_data(strSN + 'NG')
                            if DEBUG == True: print('Because NG :: Duplicate({0})'.format(strSN))
                        return False

        except Exception as e:
            print("error : {0}".format(e))
            # self.scanThread.isWorking = False  # Thread 일시 중지
            MessageBox.critical(self, 'Critical Error-SN Check::1', str(e))
            # self.scanThread.isWorking = True  # Thread 다시 시작
            self.edit_InputSN.setText('')
            return
        ###############################################################################################################

        ###############################################################################################################
        # CTN No 구하기
        try:
            rowCount = self.tableWidget.rowCount()
            ctn_no = ''
            ctnInsert_Flag = False

            # 제품 정보가 화면 테이블에 없을 경우 DB의 당일 기준으로 마지막 CTN No를 가져와서 +1을 한다.
            # 만일 당일 기준으로 첫 작업이라면 Z001을 부여한다.
            if rowCount == 0:  # 그리드에 제품이 없을 경우
                # 모델명 뒤에 MP를 붙인 동일한 모델정보가 있어서 CTN_No를 구할때는 MP를 제거하고 조회
                # 같은 모델명인데 MP가 붙은거와 안 붙은거는 같은 모델임(고객 요청 사항
                # ex) R266NRCLB_HW, R266NRCLB_HWMP <== 같은 기준 정보를 가진 모델(현품표 모델코드와 옵션코드도 동일)
                # 이렇게 모델명만 사용하지 않는다면, 모델별로 CTN_No를 구하기 때문에 카톤 라벨이 중복 발생이 가능함
                nIndex = self.model_name.find('_')
                model_name = self.model_name[:nIndex + 3]

                with self.dbConn.cursor() as cursor:
                    sql = '''  
                        select CTN_No 
                        from 
                            carton_info  
                        where 
                            regist_date > curdate()
                        and model_name like '{0}%'                            
                        order by CTN_No desc limit 1
                        '''.format(model_name)
                    cursor.execute(sql)

                    # 당일 첫 작업일 경우...
                    if cursor.rowcount == 0:
                        ctn_no = 'Z001'
                        ctnInsert_Flag = True

                    # 당일 CTN No가 있을 경우 뒷 3자리 숫자에서 +1을 한다.
                    for row in cursor.fetchall():
                        ctn_no = 'Z' + str(int(row['CTN_No'][1:4])+1).zfill(3)
                        ctnInsert_Flag = True
            else:
                ctn_no = self.tableWidget.item(0, 0).text()  # 첫번째 열의 CTN No를 가져온다.

        except Exception as e:
            print("error : {0}".format(e))
            # self.scanThread.isWorking = False  # Thread 일시 중지
            MessageBox.critical(self, 'Critical Error-SN Check::2', str(e))
            # self.scanThread.isWorking = True  # Thread 다시 시작
            self.edit_InputSN.setText('')
            return
        ###############################################################################################################

        ###############################################################################################################
        # DB와 그리드에 데이터 저장하기
        # DB carton_info, product_info 테이블에 저장
        try:
            sql = ''
            # CTN No를 새로 발번할 경우 carton_info 테이블에 저장한다.
            if ctnInsert_Flag:
                with self.dbConn.cursor() as cursor:
                    cursor.execute('''insert into carton_info (pc_name, model_name, CTN_No, label_print_YN, regist_date)
                                                      values(%s, %s, %s, 'N', %s)''',
                                                   (self.pc_name, self.model_name, ctn_no, now_date))

            # carton_info 테이블에 데이터를 넣고 product_info 테이블에도 저장한다.
            with self.dbConn.cursor() as cursor:
                cursor.execute('''  insert into product_info (model_name, pc_name, CTN_No, MAC, sn, work_date)
                                    values(%s, %s, %s, %s, %s, %s)''',
                                    (self.model_name, self.pc_name, ctn_no, self.edit_InputMac.text(), self.edit_InputSN.text(), now_date))

            self.dbConn.commit()

        except Exception as e:
            print("error : {0}".format(e))
            # self.scanThread.isWorking = False  # Thread 일시 중지
            MessageBox.critical(self, 'Critical Error-SN Check::3', str(e))
            # self.scanThread.isWorking = True  # Thread 다시 시작
            return

        if self.conveyor_mode == 'True':
            self.scanThread.write_bits_data(strSN + 'OK')

        # 화면 테이블에 제품정보 추가하기
        self.tableWidget.insertRow(0)
        self.tableWidget.setItem(0, 0, QTableWidgetItem(ctn_no))
        self.tableWidget.setItem(0, 1, QTableWidgetItem(self.edit_InputMac.text()))
        self.tableWidget.setItem(0, 2, QTableWidgetItem(self.edit_InputSN.text()))
        self.tableWidget.setItem(0, 3, QTableWidgetItem(now_date))
        ###############################################################################################################

        self.edit_Grid_Cnt.setText(str(rowCount+1))

        # 한 박스당 남은 Tray 수량 보여주기
        nTray = int(self.edit_Grid_Cnt.text()) % (self.lcd_PrdBoxCnt.intValue() / self.lcd_TrayBoxCnt.intValue())
        if nTray == 0:
            nRemainTray = self.lcd_RemainTray.intValue() - 1
            if nRemainTray == 0:
                nRemainTray = self.lcd_TrayBoxCnt.intValue()

            self.lcd_RemainTray.display(nRemainTray)

        # 특정 갯수(300개)가 검증 완료되면 라벨 프린트 진행
        if self.tableWidget.rowCount() == self.lcd_PrdBoxCnt.intValue():
            self.__cartonLabelPrint()

        # 입력 값 초기화
        self.edit_InputMac.setText('')
        self.edit_InputSN.setText('')
        self.edit_InputMac.setFocus()

    def __cartonLabelPrint(self):
        if config.getINI('SETTING', 'FW') != self.edit_FW.text() or config.getINI('SETTING',
                                                                                  'PANID') != self.edit_PanID.text():
            QMessageBox.warning(self, 'Matching Check', 'FW or PAN ID Not Matched.\n\n Please Save Button Push')
            return

        strDate = ''  # 라벨에 당일 년월일(2024.06.17
        strCtnDate = ''  # 라벨에 CTN No.에 찍힐 년월일(240617)

        with self.dbConn.cursor() as cursor:
            cursor.execute(
                '''select date_format(now(), '%Y.%m.%d') as date, date_format(now(), '%y%m%d') as ctn_date  from dual''')

            for row in cursor.fetchall():
                strDate = row['date']
                strCtnDate = row['ctn_date']

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

        # thong tin model name
        if self.model_info[11] == 'Y':
            model_name_view = self.model_name + "_" + str(config.getINI('SETTING', 'panid'))
        else:
            model_name_view = self.model_name

        # 그리드 첫번째 열에 있는 CTN No 가져오기
        strCTN_No = self.tableWidget.item(0, 0).text()

        nIndex = self.model_name.find('_')
        strColorType = self.model_name[nIndex + 1:nIndex + 3]

        # 라벨(현품표) 바코드 만들기
        strBarcode = ('PM' + strYear + strMonth + strDay + self.model_info[6] + self.model_info[7] +
                      strColorType + self.edit_Grid_Cnt.text().zfill(3) + strCTN_No)

        # 600dpi 기준
        zpl_code = '''
            ^XA

            //Darkness, Print Speed, Label Width
            ~SD{0}^PR{1}^PW{2}

            //Label Position
            ^LH{3}^LT{4}FS

            //Label layout
            ^FO230,150^GB2000,3300,12^FS
            ^FO230,900^GB2000,0,12^FS
            ^FO1800,150^GB0,3300,12^FS
            ^FO1400,150^GB0,3300,12^FS
            ^FO1100,150^GB0,3300,12^FS
            ^FO800,150^GB0,3300,12^FS
            ^FO800,1750^GB300,0,12^FS
            ^FO800,2450^GB300,0,12^FS
            ^FO1400,1750^GB400,0,12^FS
            ^FO1400,2450^GB400,0,12^FS

            //model name
            ^FO1950,350^AQR,120,120^FDModel^FS
            ^FO1950,1650^AQR,120,120^FD{5}^FS

            //PAN ID, F/W Ver in ini file loading
            ^FO1550,230^AQR,110,110^FDF/W Version^FS
            ^FO1550,1270^AQR,120,120^FD{6}^FS
            ^FO1550,1900^AQR,120,120^FDPAN ID^FS
            ^FO1550,2800^AQR,120,120^FD{7}^FS

            //Print Count
            ^FO1200,300^AQR,120,120^FDQuantity^FS
            ^FO1200,1900^AQR,120,120^FD{8}EA^FS

            //Print Date
            ^FO900,400^AQR,120,120^FDDate^FS
            ^FO900,1050^AQR,120,120^FD{9}^FS

            //CTN No.
            ^FO900,1900^AQR,120,120^FDCTN No.^FS
            ^FO900,2600^AQR,120,120^FD{10} {11}^FS

            //Carton Barcode
            ^FO450,300^AQR,120,120^FDBarcode^FS
            ^FO400,1125^BY10^BCR,270,Y,N,N,N^FD{12}^FS

            ^XZ
            '''.format(config.getINI('PRINT_SETTING', 'darkness'),
                       config.getINI('PRINT_SETTING', 'speed'),
                       config.getINI('PRINT_SETTING', 'prn_width'),
                       config.getINI('PRINT_SETTING', 'label_pos_x'),
                       config.getINI('PRINT_SETTING', 'label_pos_y'),
                       model_name_view, config.getINI('SETTING', 'FW'),
                       config.getINI('SETTING', 'panid'),
                       self.edit_Grid_Cnt.text(), strDate, strCtnDate, strCTN_No,
                       strBarcode)

        if config.getINI('SETTING', 'label_msg') == 'Y':
            QMessageBox.information(self, 'ZPL Code', zpl_code)

        # Zebra Print를 이용해서 프린트 출력
        try:
            if DEBUG == True:
                QMessageBox.information((self, 'Zebra Print Code', zpl_code))
            else:
                printer = Zebra(config.getINI('SETTING', 'print_name'))
                printer.output(zpl_code)  # generate_zpl 함수에서 생성한 ZPL 코드를 사용

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Zebra Print Check', 'The print name is invalid.\n\n' + str(e))
            return

        ###############################################################################################################
        # 프린트 출력하고 나서 출력 이력 남기고 carton_info Y로 업데이트
        try:
            with self.dbConn.cursor() as cursor:
                # 라벨 출력 완료되면 CTN_No 기준으로 라벨 출력값을 Y로 변경하고 다음 CTN_No를 발번할수 있게 한다.
                cursor.execute('''
                    update carton_info 
                    set label_print_YN = 'Y'
                    where
                        regist_date > curdate()
                    and model_name = %s
                    and pc_name = %s
                    and CTN_No = %s
                ''', (self.model_name, self.pc_name, strCTN_No))

                # 출력하는 zplcode를 테이블에 저장
                # 추후 이력을 추적하기 위해서 사용
                cursor.execute('''
                    insert into carton_print (pc_name, model_name, CTN_No, carton_id, zplcode)
                    values(%s, %s, %s, %s, %s)
                ''', (self.pc_name, self.model_name, strCTN_No, strBarcode, zpl_code))
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

    def btnBaseInfoSaveClicked(self):

        if self.edit_FW.text() == '' or self.edit_PanID.text() == '':
            QMessageBox.warning(self, 'Blank', 'FW Version or PAN ID is Blank')
            return

        config.setINI('SETTING', 'FW', self.edit_FW.text())
        config.setINI('SETTING', 'PanID', self.edit_PanID.text())

        QMessageBox.information(self, 'Save', 'Save Complet!!')
        self.edit_InputMac.setFocus()

    def btnDataClearCllicked(self):
        if self.tableWidget.rowCount() < 1:
            QMessageBox.information(self, 'No Data', 'The data you want to delete doesnt exist.')
            return

        ans = QMessageBox.question(self, "Data Delete", "Do you want to delete it?", QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.Yes)

        # Yes 버튼과 No 버튼을 생성하고, No일 경우 아무것도 안한다.
        if ans == QMessageBox.No:
            return

        self.__dataClear()
        self.lcd_RemainTray.display(self.lcd_TrayBoxCnt.intValue())
        self.edit_InputMac.setFocus()

    def __dataClear(self):
        # 그리드 삭제하기 전 DB 데이터를 먼저 삭제한다.
        # 당일/작업PC/작업CTN_No 기준으로 삭제
        try:
            with self.dbConn.cursor() as cursor:
                cursor.execute('''
                            delete 
                            from carton_info
                            where 
                                regist_date > curdate()
                            and model_name = %s
                            and CTN_No = %s
                            and pc_name = %s
                           ''', (self.model_name, self.tableWidget.item(0, 0).text(), self.pc_name))

                cursor.execute('''
                            delete
                            from product_info
                            where
                                work_date > curdate() 
                            and model_name = %s
                            and CTN_No = %s
                            and pc_name = %s
                           ''', (self.model_name, self.tableWidget.item(0, 0).text(), self.pc_name))
                self.dbConn.commit()

                self.__dataSetting()  # 데이터 삭제 후 화면 다시 셋팅

        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Data Delete Error', str(e))
            return

    def btnPrdSearchClicked(self):
        win = ctnDlg()
        win.dbConn = self.dbConn
        win.showModal()

    def btnRePrintClicked(self):
        strZplcode = ''

        try:
            # 현재 pc name & 당일 기준으로 마지막 라벨 프린트 한 이력 찾기
            with self.dbConn.cursor() as cursor:
                sql = '''
                    select zplcode  
                    from carton_print cp
                    where 
                        create_date > curdate()
                    and model_name = '{0}'
                    and pc_name = '{1}'
                    order by create_date desc limit 1
                ''' .format(self.model_name, self.pc_name)
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
            if config.getINI('SETTING', 'label_msg') == 'Y':
                QMessageBox.information(self, 'msg', strZplcode)
            else:
                printer = Zebra(config.getINI('SETTING', 'print_name'))
                printer.output(strZplcode)  # generate_zpl 함수에서 생성한 ZPL 코드를 사용
        except Exception as e:
            print("error : {0}".format(e))
            QMessageBox.critical(self, 'Zebra Print Check', 'The print name is invalid.\n\n' + str(e))
            return

        self.edit_InputMac.setFocus()

    def btnPrintNowClicked(self):

        if self.tableWidget.rowCount() == 0:
            QMessageBox.warning(self, 'No Item', 'There is no printable data.')
            return

        self.__cartonLabelPrint()
        self.edit_InputMac.setFocus()

    def btnTestClicked(self):
        if self.check_Conveyor.isChecked():
            print(True)
        else:
            print(False)

        # QMessageBox.information(self, 'aa', )
        return
        strModel = 'R420NRCLB_HWMP'
        nIndex = strModel.find('_')
        model_name = self.model_name[:nIndex + 3]
        strModel = strModel[nIndex+1:nIndex+3]

        return
        data = 'ZCIJA01149FOK'
        sendData = data[-2:]
        if sendData == 'OK':
            sendData = data[:-2] + chr(0x4F) + chr(0x4B)   # 16진수 ASCII 코드값
        elif sendData == 'NG':
            sendData = data[:-2] + chr(0x4E) + chr(0x47)   # 16진수 ASCII 코드값
        else:
            sendData = ''
        return

        # _F2893A81B6\x00\x00\x00\x00\x00_RZCIJA01149F\x00\x00\x00
        bScan = b'_F2893A81B6\x00\x00\x00\x00\x00_RZCIJA01149F\x00\x00\x00_E\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        strScan = str(bScan, 'utf-8').translate(str.maketrans("", "", '\x00'))
        print(strScan)
        nFront = strScan.find('_F')
        if strScan.find('_E') != -1:
            nRearE = strScan[strScan.find('_R')+2:strScan.find('_E')]
        else:
            nRear = strScan.find('_R')
        print('Mac :: {0} // SN :: {1}'.format(strScan[nFront+2:nRear], strScan[nRear+2:]))

        return

        if self.scanThread.isRun:
            self.scanThread.close()
        else:
            self.scanThread.run()
            self.scanThread.mac = '25B6D63DA'
            self.scanThread.sn = 'ZCHKQ013563'

        return

    def setCheckComportChanged(self):
        if self.check_Conveyor.isChecked():
            try:
                self.edit_ChoicedModel.setStyleSheet("background-color : green")
                self.conveyor_mode = 'True'
                config.setINI('SETTING', 'conveyor_mode', 'True')

                # 로직 처리 부분에서 쓰레드 객체에 대한 변수를 사용하기 때문에 일단 인스턴스는 생성
                # 만일 인스턴스를 생성하지 않으면 컨베이어용과 수작업용을 모두 분기 처리해야함
                self.scanThread = SerialScanInfo(self, self.comport, 115200, self.scanDelay)

            except Exception as e:
                # sys.exit(0)
                print(e)
        else:
            self.conveyor_mode = 'False'
            config.setINI('SETTING', 'conveyor_mode', 'False')
            self.edit_ChoicedModel.setStyleSheet("background-color : white")
            try:
                self.scanThread.close()
            except Exception as e:
                print(e)

    def reject(self):

        # ESC를 누르면 창이 닫겨서 안 닫히도록 처리
        # ESC를 누를 때 reject() 이벤트가 발생하게 되고 이때 return으로 아무것도 안하게 처리
        # sys.exit(0)  # ESC 누를 때 종료 처리
        return

    def closeEvent(self, event):
        ans = QMessageBox.question(self, "Close Window", "Do you want to exit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        # Yes 버튼과 No 버튼을 생성하고, 기본 값으로 Yes 값이 클릭되어 있음
        if ans == QMessageBox.Yes:
            # DB Connection 종료 처리(cursor는 with문을 쓰면서 자동 종료되어 별도 처리 안해도 됨)
            self.dbConn.close()
            if self.conveyor_mode == 'True':
                # Thread 종료
                try:
                    self.scanThread.close()
                except Exception as e:
                    print(e)
            event.accept()  # Yes 를 누르면 closeEvent
        else:
            event.ignore()  # No 를 누르면 closeEvent 무시

    def __database_connect(self):
        # ===========DB Connection =================================================================================
        # mariaDB를 접속하기 위해서 mariaDB 라이브러리를 사용하지 않고 mysql 라이브러리 사용
        # mariaDB 라이브러리를 사용하면 이상하게 debug 모드에서 오류가 남
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
        config = INI("./carton_config.ini")  # 해당 파일이 없으면 False 값을 리턴해서 강제로 Exception으로 빠짐

    except Exception as e:
        # print(pg.alert(text='실행파일 폴더에 Config.ini 파일이 없습니다.', title='Not Read Config.ini', button='OK'))
        QMessageBox.warning(None, 'Not Read Config.ini', '실행파일 폴더에 Carton_config.ini 파일이 없습니다.')
        sys.exit(0)

    window = MainDialog()
    window.show()
    app.exec()