from time import sleep
from datetime import datetime
import threading
import serial
import pyautogui as pg


class SerialScanInfo:
    def __init__(self, obj, comport, baud_rate, sleepTime):
        self.scan_th = None
        self.comport = comport
        self.baud_rate = baud_rate
        self.sleepTime = sleepTime
        self.isRun = False
        self.isWorking = True
        self.mac = ''
        self.sn = ''
        self.mainDlg = obj

        try:
            if self.comport != '':
                print('\nClass SerialScanInfo Init() :: {0} // {1}'.format(self.comport, self.baud_rate))
                self.serialConn = serial.serial_for_url(self.comport, baudrate=self.baud_rate, timeout=self.sleepTime)

                self.run()

        except serial.serialutil.SerialException as e:
            print('Serial Connection Error :: {0}'.format(e))
            print(pg.alert(text='Serial Connection Error :: {0}'.format(e), title='Conntection Error', button='OK'))
            if self.serialConn.is_open:
                self.serialConn.close()
            return e

    def run(self):
        self.scan_th = threading.Thread(target=self.ScanInfoThread, args=())
        # 새로운 쓰레드에서 해당 소켓을 사용하여 통신.
        self.isRun = True
        self.scan_th.start()  # 쓰레드 실행

        print('*' * 30)
        print('Thead Start!!!!')

    def close(self):
        self.isRun = False
        self.serialConn.close()

    def ScanInfoThread(self):
        i = 0
        while self.isRun:
            if self.isWorking:
                try:
                    self.mainDlg.NG_SN = ''

                    # self.get_bits_data(str(i))

                    # 컨베이어에서 들어오는 값에서 \x00 제거하고 bytes를 스트링으로 변환
                    # b'_F2893A81B6\x00\x00\x00\x00\x00_RZCIJA01149F\x00\x00\x00 ==> _F2893A81B6_RZCIJA01149F
                    strScanValue = str(self.get_bits_data(''), 'utf-8').translate(str.maketrans("", "", '\x00'))
                    if len(strScanValue) < 5 or strScanValue == '_E':
                        continue

                    # print('data_received22({0}) :: {1}'.format(datetime.now(), strScanValue))
                    nFront = strScanValue.find('_F')
                    nRear = strScanValue.find('_R')
                    nEnd = strScanValue.find('_E')

                    self.mac = strScanValue[nFront + 2:nRear]
                    # 시리얼 넘버 뒤에 _E가 붙어서 들어와서 별도 처리 필요(제품 투입 간격이 빠르면 이렇게 붙어서 나오게 됨)
                    # b'_F2893A81B6\x00\x00\x00\x00\x00_RZCIJA01149F\x00\x00\x00_E\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                    if nEnd != -1:
                        self.sn = strScanValue[nRear+2:nEnd]
                    else:
                        self.sn = strScanValue[nRear + 2:]

                    print('Mac :: {0} // SN :: {1} // SN Size :: {2}'.format(self.mac, self.sn, len(self.sn)))

                except Exception as e:
                    print('error : {0}'.format(e))
                    continue

                try:
                    if len(self.mac) > 5:
                        self.mainDlg.edit_InputMac.setFocus()
                        # self.mac = self.mac[0:5] + str(int(self.mac[5:7]) + 1) + self.mac[-2:]
                        self.mainDlg.edit_InputMac.setText(self.mac)

                        self.mainDlg.NG_SN = self.sn  # 컨베이어에 NG 전송할 때 SN을 보내기 위한 임시 변수
                        # if not을 사용하면 안됨. 해당 함수에서 그냥 return을 하면 'None'이 되기 때문에 무조건 False로만 비교해서 continue 해야됨
                        if self.mainDlg.InputMacCheck() == False:
                            self.mainDlg.edit_InputMac.setText('')
                            continue

                        # if self.isWorking:  # 팝업창이 떴을때 다시 enter key가 발생해서 팝업창이 자동으로 닫혀버려서 체크함
                        #     pg.press('enter')
                        # self.mac = ''  # 실제 동작할때는 주석 풀어야 됨
                        sleep(1)
                        self.mac = ''

                    if len(self.sn) > 5:
                        self.mainDlg.edit_InputSN.setFocus()
                        # self.sn = self.sn[0:-2] + str(int(self.sn[-2:]) + 1)
                        self.mainDlg.edit_InputSN.setText(self.sn)
                        # self.mainDlg.edit_InputMac.returnPressed
                        if self.mainDlg.InputSnCheck() == False:
                            self.mainDlg.edit_InputSN.setText('')
                            continue

                        # if self.isWorking:  # 팝업창이 떴을때 다시 enter key가 발생해서 팝업창이 자동으로 닫혀버려서 체크함
                        #     pg.press('enter')
                        # self.sn = ''  # 실제 동작할때는 주석 풀어야 됨
                        sleep(1)
                        self.sn = ''
                except Exception as e:
                    print('error : {0}'.format(e))
                    continue

                i += 1

            sleep(self.sleepTime)

        print('#' * 30)
        print('Thread Close!!!!!')

    def get_bits_data(self, input_value):

        try:
            # read all that is there or wait for one byte (blocking)
            strResult = self.serialConn.readline()  # 값을 줄로 받음(byte형식)
            if len(strResult) < 5:
                return ''
            # print('Received Data({0}) :: {1}'.format(datetime.now(), strResult))

            strLog = 'Received Data({0}) :: {1}'.format(datetime.now(), strResult)
            f = open('conveyor.log', 'a')
            f.write(strLog + '\n')
            f.close()
        except serial.SerialException as e:
            # probably some I/O problem such as disconnected USB serial
            # adapters -> exit
            print('get_bits_data :: {0}'.format(e))
            strLog = 'get_bits_data :: {0}'.format(e)
            f = open('conveyor.log', 'a')
            f.write(strLog + '\n')
            f.close()
        finally:
            return strResult

    def write_bits_data(self, data):

        try:
            sendData = data[-2:]
            if sendData == 'OK':
                sendData = data[:-2] + chr(0x4F) + chr(0x4B)   # 16진수 ASCII 코드값
            elif sendData == 'NG':
                sendData = data[:-2] + chr(0x4E) + chr(0x47)   # 16진수 ASCII 코드값
            else:
                sendData = ''

            self.serialConn.write(sendData.encode())
        except serial.SerialException as e:
            # probably some I/O problem such as disconnected USB serial
            # adapters -> exit
            print('write_bits_data :: {0}'.format(e))
            strLog = 'write_bits_data :: {0}'.format(e)
            f = open('conveyor.log', 'a')
            f.write(strLog + '\n')
            f.close()
            return

        strLog = "Write Data({0}) : {1}".format(datetime.now(), data)
        print(strLog)
        self.mainDlg.edit_ChoicedModel.setText(data)

        f = open('conveyor.log', 'a')
        f.write(strLog + '\n')
        f.close()
