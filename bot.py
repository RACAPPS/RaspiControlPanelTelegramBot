import telebot
from telebot import types
import logging
from urllib.request import urlopen
import re
import subprocess
import pymysql
import base64
import requests

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)
bot = None
myChatId = 1234 # YOUR CHAT ID

with open("./raspi.tok", "r") as tok:
    token = tok.read().rstrip()
    bot = telebot.TeleBot(token, threaded=False)

with open("./db.pass", "r") as pasw:
    pas = base64.b64decode(pasw.read().rstrip()).decode('UTF-8')

def parseInjection(txt):
    return txt.replace('"', '\\"').replace('\'', '\\\'').replace('\\', '\\\\')


def getIp():
    my_ip = urlopen('http://ip.42.pl/raw').read()
    return my_ip.decode('utf-8')


def ruben(msg):
    return msg.from_user.username == 'rubenaguadoc' # YOUR USERNAME


def getServerStatus(srvrName):
    if srvrName == 'FTP':
        srvrName = 'vsftpd'
    if srvrName == 'VPN':
        srvrName = 'openvpn'
    if srvrName == 'SSH':
        srvrName = 'ssh'
    result = subprocess.run(['sudo', 'service', srvrName, 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response = result.stdout.decode('utf-8')
    response += '\n' + result.stderr.decode('utf-8')
    if ' active (' in response:
        return 'up'
    else:
        return 'down'


def runServerCommand(srvrName, destination):
    if srvrName == 'FTP':
        srvrName = 'vsftpd'
    if srvrName == 'VPN':
        srvrName = 'openvpn'
    if srvrName == 'SSH':
        srvrName = 'ssh'
    if destination == 'UP':
        destination = 'start'
    if destination == 'DOWN':
        destination = 'stop'
    result = subprocess.run(['sudo', 'service', srvrName, destination], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response = result.stdout.decode('utf-8')
    response += '\n' + result.stderr.decode('utf-8')
    if response == '\n':
        return True
    else:
        return response


def runLinuxCommand(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response = result.stdout.decode('utf-8')
    response += '\n' + result.stderr.decode('utf-8')
    return response


def getId(msg):
    return msg.chat.id


def typing(msg):
    bot.send_chat_action(getId(msg), 'typing')


@bot.message_handler(commands=['start', 'help'])
def sendWelcome(message):
    typing(message)
    bot.send_message(getId(message), '''Wellcome to @YOURBOT:

/help      Get help
/ftp         Switch the FTP server
/ssh        Switch the SSH server
/vpn       Switch the VPN server
/ip           Get the pip
/sdown  Shut it down baby
/reboot  Wanna fresh start?''')


@bot.message_handler(commands=['ip'])
def sendIp(msg):
    typing(msg)
    bot.send_message(getId(msg), 'Your Raspberry public Ip is: ' + getIp())


@bot.message_handler(commands=['ftp', 'ssh', 'vpn'])
def showOrSwitch(msg):
    typing(msg)
    if not ruben(msg):
        bot.send_message(getId(msg), 'Sorry, but only Rubén can access this functionallity')
        return
    server = msg.text.lstrip('/').upper()
    status = getServerStatus(server)
    markup = types.ReplyKeyboardMarkup()
    toUp = types.KeyboardButton('Turn ' + server + ' UP')
    toDown = types.KeyboardButton('Turn ' + server + ' DOWN')
    cancel = types.KeyboardButton('Cancel')
    markup.row(toUp, toDown)
    markup.row(cancel)
    bot.send_message(getId(msg), 'The ' + server + ' server is ' + status, reply_markup=markup)


@bot.message_handler(commands=['sdown'])
def shutItDown(msg):
    typing(msg)
    bot.send_message(getId(msg), 'Taking me down...')
    response = runLinuxCommand(['sudo', 'shutdown', '-t', '1'])
    typing(msg)
    bot.send_message(getId(msg), response)


@bot.message_handler(commands=['reboot'])
def reboot(msg):
    typing(msg)
    bot.send_message(getId(msg), 'See you in a sec!')
    response = runLinuxCommand(['sudo', 'shutdown', '-r', '-t', '1'])
    typing(msg)
    bot.send_message(getId(msg), response)


@bot.message_handler(func=lambda msg: msg.text == 'Cancel')
def cancel(msg):
    typing(msg)
    bot.send_message(getId(msg), 'Action cancelled', reply_markup=types.ReplyKeyboardRemove(selective=False))


@bot.message_handler(func=lambda msg: re.match(r'Turn \w{3} \w{2,3}', msg.text if msg.text else ""))
def switchServerState(msg):
    typing(msg)
    server = msg.text.split(' ')[1]
    destination = msg.text.split(' ')[2]
    message = runServerCommand(server, destination)
    if (message is True):
        bot.send_message(getId(msg), 'Done!', reply_markup=types.ReplyKeyboardRemove(selective=False))
    else:
        bot.send_message(getId(msg), 'Ups...\n' + message)


@bot.message_handler(func=lambda msg: re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.text if msg.text else ""))
def storeLink(msg):
    typing(msg)
    if not ruben(msg):
        bot.send_message(getId(msg), 'Sorry, but only Rubén can access this functionallity')
        return
    try:
        db = pymysql.connect('localhost', 'phpmyadmin', pas, 'PI', autocommit=True)
    except Exception as e:
        bot.send_message(getId(msg), 'Something went very wrong... 😅\n')
        return
    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.text)
    for url in urls:
        try:
            cursor = db.cursor()
            sql = "INSERT INTO LINKS (LINK) VALUES ('" + parseInjection(url) + "')"
            cursor.execute(sql)
            cursor.close()
        except Exception as e:
            bot.send_message(getId(msg), 'Something went very wrong... 😅\n')
            return
        bot.send_message(getId(msg), 'The following link will be open on your PC:\n' + url)
    try:
        db.close()
    except Exception:
        return


@bot.message_handler(content_types=["audio", "document", "photo", "video"])
def storeFile(msg):
    typing(msg)
    if msg.content_type == "photo":
        fileId = getattr(msg, msg.content_type)[-1].file_id
        fileName = fileId[-10:] + ".jpg"
    else:
        fileId = getattr(msg, msg.content_type).file_id
        fileName = getattr(msg, msg.content_type).file_name
    fileInfo = bot.get_file(fileId)
    fileResponse = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(token, fileInfo.file_path))
    saveFile = open("/var/www/html/files/" + fileName, "wb")
    saveFile.write(fileResponse.content)
    saveFile.close()
    try:
        db = pymysql.connect('localhost', 'phpmyadmin', pas, 'PI', autocommit=True)
    except Exception as e:
        bot.send_message(getId(msg), 'Something went very wrong... 😅\n')
        return
    url = 'http://' + getIp() + '/filer.php?file=' + fileName
    try:
        cursor = db.cursor()
        sql = "INSERT INTO LINKS (LINK) VALUES ('" + parseInjection(url) + "')"
        cursor.execute(sql)
        cursor.close()
    except Exception as e:
        bot.send_message(getId(msg), 'Something went very wrong... 😅\n')
        return
    bot.reply_to(msg, "File recieved")
    try:
        db.close()
    except Exception:
        return


bot.send_chat_action(myChatId, 'typing')
bot.send_message(myChatId, 'Pi up and running')

bot.polling(True)
