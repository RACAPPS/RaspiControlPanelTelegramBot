import subprocess

ps = subprocess.Popen(('ps', '-u', 'root'), stdout=subprocess.PIPE)
output = subprocess.check_output(('grep', 'python'), stdin=ps.stdout)
ps.wait()

if output.decode('utf-8').count('python') < 2:
    result = subprocess.Popen(['/home/pi/bot-venv/bin/python3', '/home/pi/bot-venv/bot/bot.py'])
