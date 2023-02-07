!/usr/bin/env python3

import os

os.system('touch lastmodem')
file = open("lastmodem", "r")
lastmodem_id = int(file.readline())     # получим номер модема, которому в предыдущий раз обновляли IP-адрес
file.close

print("lastmodem_id =" + str(lastmodem_id))

if lastmodem_id == 0  or lastmodem_id == 5:                #если это первый запуск скрипта или если это был последний модем, то обнуляем счет
  lastmodem_id = 0

currentmodem_id = lastmodem_id + 1         #берем в качестве текущего следующий номер модема для обновления IP-адреса
os.system('echo ' + str(currentmodem_id) + ' > lastmodem')  #запоминаем номер текущего модема для следующего запуска скрипта.
print(str(currentmodem_id))
server_alias = "server" + str(currentmodem_id) + "/s" + str(currentmodem_id)          # сформируем имя сервера, который надо вывести в drain mode в конфиге haproxy
os.system('echo "set server ' + server_alias + ' state drain" | socat stdio tcp4-connect:127.0.0.1:1350') # выведем текущий сервер из пула haproxy
