import win32api

'''
4번째 인수에 따라서 메시지 박스 Type이 달라진다.
아래 링크를 참고로 추후 필요한 메시지를 추가하면 된다.
https://papazeros.tistory.com/3
'''
class MessageBoxClass:
    def noicon(self, TITLE, TEXT):
        win32api.MessageBox(0, TEXT, TITLE, 0)

    def critical(self, TITLE, TEXT):
        win32api.MessageBox(0, TEXT, TITLE, 16)

    def question(self, TITLE, TEXT):
        win32api.MessageBox(0, TEXT, TITLE, 32)

    def warning(self, TITLE, TEXT):
        win32api.MessageBox(0, TEXT, TITLE, 48)

    def information(self, TITLE, TEXT):
        win32api.MessageBox(0, TEXT, TITLE, 64)
        # print(pg.alert(title = strTitle, text = strMsg, button = 'OK'))


