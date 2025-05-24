import configparser  # lib for INI File
from pathlib import Path


class INIConfig:
    def __init__(self, name):
        """

        :rtype: object
        """
        self.ini_path = name

        my_file = Path(self.ini_path)  # Path는 string을 return하는것 아님.window에서만 사용하능함.
        if not my_file.is_file():
            return False

        self.config = configparser.ConfigParser()
        self.config.read(self.ini_path)

    def getINI(self, section, key):
        self.config.read(self.ini_path)
        strResult = ''
        try:
            strResult = self.config.get(section, key)  # Key값이 없으면 오류가 나서 예외처리
        except Exception as e:
            print(e)

        return strResult

    def setINI(self, section, key, value):
        # config 변수를 다시 초기화 시켜준다.
        # 초기화 안하면 이전 config에 저장된 값을 ini 파일에 다시 write 해버린다.
        self.config = configparser.ConfigParser()
        self.config.read(self.ini_path)

        self.config.set(section, key, value)

        #with open('Config.ini', 'w') as configfile:
        with open(self.ini_path, 'w') as configfile:
            self.config.write(configfile)

    def getKeyList(self, section):
        keys = self.config[section].keys()

        return keys
