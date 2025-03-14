#!/usr/bin/env python3

import os
import subprocess
import time
import json
import syslog
from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

proxyhome = '/home/dmitry/ipchanger/' #домашняя папка, где будет лежать скрипт на линуксе
from huawei_lte_api.enums.net import NetworkModeEnum
from huawei_lte_api.enums.cradle import ConnectionStatusEnum

max_ip_life_time = 300  # время жизни IP-адреса модема
wait_time = 20  # количество секунд ожидания поднятия модема после смены IP
modempassword = 'Password01*' # Пароль доступа к вебке модемов


# Функция вывода модема из пула балансировки haproxy
def removeModemFromPull(modem):
    result = os.system(
        'echo "set server ' + modem + '/' + modem + ' state drain" | socat stdio tcp4-connect:127.0.0.1:1350')  # выведем текущий сервер из пула haproxy
    time.sleep(1)

# Функция возврата модема в пул балансировки haproxy
def returnModemToPull(modem):
    result = os.system(
        'echo "set server ' + modem + '/' + modem + ' state ready" | socat stdio tcp4-connect:127.0.0.1:1350')  # вернем текущий сервер в пул haproxy
    time.sleep(1)

# Возвразащает True если подключение висит больше 5 минут или не подключено, иначе False
def isModemNeedChangeIP(modem, client) -> bool:
    currentworktime = int(client.monitoring.traffic_statistics().get('CurrentConnectTime'))
    if currentworktime >= max_ip_life_time or currentworktime == 0: # если currentworktime равно 0, то значит модем отключен и надо его принудительно дернуть
        return True
    else:
        return False


# Функция смены IP-адреса модема. При успешном выполнении возвращает True, иначе False
def changeModemIP(modem, client) -> bool:
    # сменим IP-адрес модему
    client.net.set_net_mode("7FFFFFFFFFFFFFFF", "3FFFFFFF", NetworkModeEnum.MODE_3G_ONLY)  # 3G
    client.net.set_net_mode("7FFFFFFFFFFFFFFF", "3FFFFFFF", NetworkModeEnum.MODE_4G_ONLY)  # LTE
    # подождем wait_time секунд, чтобы модем подключился к сети. Если за половину отведенного времени не подключился,
    # то делаем модему выкл/вкл и ждем оставшуюся половину времени
    for i in range(wait_time):
        status = client.monitoring.status()
        if status.get('ConnectionStatus') == str(ConnectionStatusEnum.CONNECTED):
            break
        if i >= wait_time / 2:
            client.dial_up.set_mobile_dataswitch(0)
            time.sleep(1)
            client.dial_up.set_mobile_dataswitch(1)
        time.sleep(1)
    # если все ок, то возвращаем True
    # если так и не дождались подключения к сети, то сдаемся и возвращаем False
    if status.get('ConnectionStatus') == str(ConnectionStatusEnum.CONNECTED):
        syslog.syslog(syslog.LOG_ERR, 'Success changeModemIP')
        return True
    else:
        syslog.syslog(syslog.LOG_ERR, 'Failed changeModemIP')
        return False

# Проверяет на уникальность выделенный опператором белый IP
def checkModemConnection(modem) -> bool:
    # srv_addr, srv_port
    command1 = "echo \"show servers state\" | socat stdio tcp4-connect:127.0.0.1:1350 | grep -E \"(" + modem + ".*){2}\" | cut -d \" \" -f 5,19"
    response1 = subprocess.check_output(command1, shell=True, text=True)
    proxy = response1.split()
    command2 = "curl -sx http://" + proxy[0] + ":" + proxy[1] + " telnetmyip.com | jq -r .ip"
    print(command2)
    response2 = subprocess.check_output(command2, shell=True, text=True).rstrip()
    if not response2:
        return False
    elif not os.path.exists(proxyhome + "externalIPs.txt"):
        d = {modem: response2}
    else:
        with open(proxyhome + 'externalIPs.txt') as f1:
            d: object = json.load(f1)
        for key, value in d.items():
            if value == response2:
                return False
        d[modem] = response2
    with open(proxyhome + 'externalIPs.txt', 'w') as f1:
        f1.write(json.dumps(d))
    return True

# Основной сценарий

# получим список модемов из конфиг файла ltemodems.cfg
with open(proxyhome + 'ltemodems.cfg', 'r') as f:
    Modems = list([line.rstrip() for line in f])

# для каждого модема по списку, если после последней смены IP-адреса прошло более 5 минут, выполним вывод из пула haproxy, сменим IP-адрес,
# удостоверимся, что модем точно подключен к интернету и что полученный IP-адрес уникален, и вернем его в пул.
# Если модем не подключился или адрес не уникален, то повторим процедуру смены адреса (максимум 3 повтора).
for modem in Modems:
    print("start ipchanging modem " + modem)
    with Connection("http://admin:" + modempassword + "@" + modem) as connection:
        client = Client(connection)
        if isModemNeedChangeIP(modem, client):
            removeModemFromPull(modem)
            for i in range(3):
                if changeModemIP(modem, client):
                    if checkModemConnection(modem):
                        returnModemToPull(modem)
                        print("modem " + modem + " ipchange result: Success")
                        break
                else:
                    print("Modem " + modem + " - ipchange result: Fail")
                    break
        else:
             print("Modem " + modem + " - ipchange result: not yet")
