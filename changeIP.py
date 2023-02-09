#!/usr/bin/env python3

import os
from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

os.system('touch lastmodem')
file = open("lastmodem", "r")
lastmodem_id = int(file.readline())     # получим номер модема, которому в предыдущий раз обновляли IP-адрес
file.close

if lastmodem_id == 0  or lastmodem_id == 5:                #если это первый запуск скрипта или если это был последний модем, то обнуляем счет
  lastmodem_id = 0

currentmodem_id = lastmodem_id + 1         #берем в качестве текущего следующий номер модема для обновления IP-адреса
os.system('echo ' + str(currentmodem_id) + ' > lastmodem')  #запоминаем номер текущего модема для следующего запуска скрипта.

server_alias = "server" + str(currentmodem_id) + "/s" + str(currentmodem_id)          # сформируем имя сервера, который надо вывести в drain mode в конфиге haproxy
os.system('echo "set server ' + server_alias + ' state drain" | socat stdio tcp4-connect:127.0.0.1:1350') # выведем текущий сервер из пула haproxy

with Connection("http://admin:Password01*@192.168.13.1/") as connection:
    client = Client(connection)
    client.net.set_net_mode("7FFFFFFFFFFFFFFF", "3FFFFFFF", "02") # 3G
    client.net.set_net_mode("7FFFFFFFFFFFFFFF", "3FFFFFFF", "03") # LTE

os.system('echo "set server ' + server_alias + ' state ready" | socat stdio tcp4-connect:127.0.0.1:1350') # введем текущий сервер в пул haproxy
