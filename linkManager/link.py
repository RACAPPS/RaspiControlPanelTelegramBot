import base64
import pymysql
from time import sleep
import subprocess
import ctypes

with open("./db.pass", "r") as pasw:
    pas = base64.b64decode(pasw.read().rstrip()).decode('UTF-8')

with open("./linker.ip", "r") as config:
    ip = config.read().rstrip()


def log(err):
    with open("./log.txt", "a") as daLog:
        daLog.write(str(err))


def parseInjection(txt):
    return txt.replace('"', '\\"').replace('\'', '\\\'').replace('\\', '\\\\')


def connect():
    err = 0
    while err < 3:
        try:
            return pymysql.connect(ip, 'phpmyadmin', pas, 'PI', autocommit=True)
        except Exception as e:
            log(e)
            err += 1
    ctypes.windll.user32.MessageBoxW(0, u"Algo fallo en la conexión a la base de datos", u"Error (Linker.py)", 0)
    exit()

db = connect()
err = 0
while err < 3:
    try:
        cursor = db.cursor()
    except Exception as e:
        err += 1
        db = connect()
    try:
        cursor.execute("SELECT LINK FROM LINKS")
        rows = cursor.fetchall()
        for row in rows:
            log(row[0])
            result = subprocess.Popen(['C:\Program Files (x86)\Google\Chrome\Application\chrome.exe', row[0]])
            cursor.execute("DELETE FROM LINKS WHERE LINK = '" + parseInjection(row[0]) + "'")
        cursor.close()
        err = 0
    except Exception as e:
        err += 1
        log(e)
    sleep(20)
ctypes.windll.user32.MessageBoxW(0, u"Algo fallo descargando los links de la DDBB", u"Error (Linker.py)", 0)
