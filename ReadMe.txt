
    Общие сведения

    Для реализации функционала мобильных прокси используются два и более LTE-модема Huawei 3372h, подключаемых напрямую или
через USB-хаб к компьютеру (коим может быть и Raspberry PI) под управлением ОС Linux (желательно, но необязательно, Ubuntu).
На компьютере поднимаются три docker-контейнера: haproxy, 3proxy и ipchanger.
    Основную работу по проксированию HTTP-трафика (т.н. "прямое проксирование") выполняет 3proxy, который принимает трафик,
приходящий на компьтер из интернета через домашний роутер, и передает этот трафик обратно в интернет, но уже через LTE-модемы
с sim-картами. Поэтому социальные сети ВК и ОК "видят" этот трафик как трафик от мобильных абонентов, что для ВК и ОК затрудняет
распознавание ботов и, следовательно, блокирование их работы антиспам-алгоритмами.
    Все бы ничего, и одного 3proxy нам было бы достаточно, но внешний IP-адрес, с которым каждый LTE-модем ходит в интернет,
необходимо менять в среднем раз в 5 минут. Иначе антиспам-алгоритмы ВК и ОК успеют "найти нас по IP-адресу" и забанят
наших ботов. Это как артиллеристы, отстрелявшиеся по врагу, обязаны оперативно сменить место дислокации во избежании
прилета ответочки. Или как в фильме "Матрица" герои в матрице всегда должны были действовать, не мешкая, и еще быстрее сваливать,
пока их не поймали Агенты. Поэтому мы вынуждены применить еще два docker-контейнера haproxy и ipchanger.
    Haproxy выполняет функцию проксирования входящего от ботов трафика в сторону 3proxy (т.н. "обратное проксирование").
Т.е. входящий трафик сначала попадает на haproxy, который в свою очередь перебрасывает трафик на 3proxy, а последний уже
отправляет трафик на LTE-модемы. Haproxy мы применяем из-за того, что он предоставляет возможность гибко управлять собой
через API, чего не предоставляет 3proxy. Если бы 3proxу мог так же гибко управляться извне, как haproxy, то haproxy нам бы
не понадобился. Зачем нам это управление? А вот зачем.
    Для того, чтобы раз в 5 минут сменить внешний IP-адрес LTE-модему, необходимо примерно на 10-20 секунд вывести
его из работы. Если просто так выводить модем из работы, то на эти 10-20 секунд боты, которые работали через этот модем,
отвалятся, из-за чего будут пропущены какие-нибудь важные рассылки, и, возможно, восстанавливать работу ботов придется вручную.
Чтобы такого не происходило и боты не чувствовали перебоев, перед тем, как вывести один модем из работы для смены IP-адреса,
весь приходящий на этот модем трафик необходимо перенаправить на другие работающие модемы, а после возвращения модема в
работу вернуть трафик обратно. Haproxy позволяет делать такое перенаправление трафика по командам извне, а в нашем случае
от ipchanger.
    Iphanger, как было сказано выше, посылает команды на haproxy, чтобы тот перенаправлял трафик с одного модема на другие
и обратно. То есть iphanger нужен для того, чтобы по графику менять IP-адреса LTE-модемам и координировать работу всех
элементов системы во время этого процесса. Если коротко, то на ipchanger раз в минуту запускается python-скрипт, который
последовательно опрашивает все LTE-модемы на предмет, не пора ли им менять IP-адрес. Для каждого модема, которому настала
пора сменить IP-адрес, скрипт командует haproxy перевести трафик этого модема на другие модемы, перезапускает модем для
смены его IP-адреса, проверяет вернулся ли модем в рабочий режим, проверяет есть ли через этот модем связь с интернетом и
не совпадает ли его новый IP-адрес с IP-адресами других модемов. Если все проверки проходят, то ipchanger командует haproxy
вернуть трафик на данный модем. Если проверки не проходят, то модем отправляется на еще один цикл смены IP-адреса, и так
пока все проверки не будут пройдены, но не более трех циклов.
    Вот, собственно, и все.


    Инструкция по установке

1. Установить Linux. Провереная конфигурация - последняя версия сервера Ubuntu
2. Подключить модемы и если ОС на виртуализации, то пробросить подключение USB модемов в виртуалку.
3. Настроить через веб-интерфесы IP-адреса модемам, и вход в вебку по логину/паролю
4. При правильном подключении модемы в линуксе должны получить каждый свой IP-интерфейс с IP-адресом,
который вы задали в вебке каждого модема. Список IP-интерфейсов можно получить командой ifconfig -a
В примере ниже видны два модема на интерфейсах enp1s27u1 и enp1s27u2 с IP-адресами 192.168.8.100 и
192.168.9.100

jaka@netbot:~$ ifconfig -a
docker0: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        inet 172.17.0.1  netmask 255.255.0.0  broadcast 172.17.255.255
        ether 02:42:ea:20:f8:e1  txqueuelen 0  (Ethernet)
        RX packets 0  bytes 0 (0.0 B)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 0  bytes 0 (0.0 B)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

enp1s27u1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.8.100  netmask 255.255.255.0  broadcast 192.168.8.255
        inet6 fe80::e5b:8fff:fe27:9a63  prefixlen 64  scopeid 0x20<link>
        ether 0c:5b:8f:27:9a:63  txqueuelen 1000  (Ethernet)
        RX packets 119201  bytes 89989223 (89.9 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 116845  bytes 18888764 (18.8 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

enp1s27u2: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.9.100  netmask 255.255.255.0  broadcast 192.168.9.255
        inet6 fe80::e5b:8fff:fe27:9a64  prefixlen 64  scopeid 0x20<link>
        ether 0c:5b:8f:27:9a:64  txqueuelen 1000  (Ethernet)
        RX packets 85192  bytes 81966158 (81.9 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 72949  bytes 9786675 (9.7 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

ens18: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.63  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::e478:70ff:fe8a:ef75  prefixlen 64  scopeid 0x20<link>
        ether e6:78:70:8a:ef:75  txqueuelen 1000  (Ethernet)
        RX packets 298954  bytes 218301197 (218.3 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 164093  bytes 180353572 (180.3 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1000  (Local Loopback)
        RX packets 341249  bytes 178598067 (178.5 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 341249  bytes 178598067 (178.5 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

jaka@netbot:~$

Если видите все интерфейсы, то переходите к п.7. Это значит модемы определились, но теперь надо настроить сетевые параметры.

Если вы видите не все интерфейсы, или вообще ни одного не видите, то это значит, что они либо определились как флешки, а не как модемы (описано в п.6), или у некоторых или у всех модемов одинаковый MAC-адрес (описано в п.7), что запрещено. Обычно у модемов одинаковый мак-адрес, так как они прошиваются одной и той же прошивкой.

5. Бывает, что изначально модемы в линуксе определяются как флешки, а не как модемы. Если по команде "dmesg -T | grep -i usb" вы не видите сетевых интерфесов модемов - значит они определились как флешки. Чтобы перевести их в режим модемов нужно сделать следующее. 
- Установить, если не установлен, пакет sudo apt install usb_modeswitch 
- В файл etc/usb_modeswitch.conf добавить вот такие строки:
DefaultVendor = 0x12d1
DefaultProduct = 0x1f01

- выполнить несколько раз команду sudo usb_modeswitch -c /etc/usb_modeswitch.conf -J пока все модемы не будут переведены в режим модема. Каждый запуск команды переводит в нужный режим один модем. То есть если надо перевести в нужный режим пять модемов, то и команду надо выполнить пять раз. 

6. Удостовериться, что у вас действительно есть проблема одинаковых MAC-адресов, можно дав команду:
dmesg -T | grep -i usb
В примере ниже в последних двух строках вывода этой команды видно, что два модема имеют одинаковые MAC-и

[Thu Feb 16 10:18:08 2023] usb 2-2: Product: HUAWEI_MOBILE
[Thu Feb 16 10:18:08 2023] usb 2-2: Manufacturer: HUAWEI_MOBILE
[Thu Feb 16 10:18:08 2023] usb-storage 2-1:1.2: USB Mass Storage device detected
[Thu Feb 16 10:18:08 2023] scsi host3: usb-storage 2-1:1.2
[Thu Feb 16 10:18:08 2023] usb-storage 2-2:1.2: USB Mass Storage device detected
[Thu Feb 16 10:18:08 2023] scsi host4: usb-storage 2-2:1.2
[Thu Feb 16 10:18:08 2023] usbcore: registered new interface driver usb-storage
[Thu Feb 16 10:18:08 2023] usbcore: registered new interface driver uas
[Thu Feb 16 10:18:10 2023] cdc_ether 2-1:1.0 eth0: register 'cdc_ether' at usb-0000:01:1b.0-1, CDC Ethernet Device, 0c:5b:8f:27:9a:64
[Thu Feb 16 10:18:10 2023] cdc_ether 2-2:1.0 eth1: register 'cdc_ether' at usb-0000:01:1b.0-2, CDC Ethernet Device, 0c:5b:8f:27:9a:64

чтобы исправить это, необходимо сначала определить значение параметра ID_PATH для каждого модема. Это можно сделать
выгрузив вывод команды
udevadm info --export-db > udevadm.txt

В выгруженном файле udevadm.txt надо найти значения параметра ID_PATH для всех модемов. В файле они должны находиться
вблизи вот таких строк "DRIVER=cdc_ether". Значения должны быть похожи на эти:
	ID_PATH=pci-0000:01:1b.0-usb-0:1:1.0
	ID_PATH=pci-0000:01:1b.0-usb-0:2:1.0

Далее в папке /etc/systemd/network/ для каждого модема создаем по одном конфигурационному файлу с такими именами
01-huawei-e3372h.link - для первого модема
02-huawei-e3372h.link - для второго модема
и т.п.

В каждом файле должен быть такой конфиг:
[Match]
Path=pci-0000:01:1b.0-usb-0:2:1.0
Driver=cdc_ether

[Link]
Description=Huawei E3372h-607 in HiLink mode
Name=<имя сетевого интерфейса, которое надо присвоить данному модему, например modem8>
MACAddress=0c:5b:8f:27:9a:64

где в поле Path указывается найденное ранее значение ID_PATH модема, а в поле MACAddress значение мак-адреса, которое
надо присвоить этому модему. Можно взять мак-адрес исходный и просто менять последнюю цифру, чтобы у каждого модема
был уникальный мак-адрес.

После того, как для каждого модема создан такой конфг-файл, выполняем команду:
sudo ln -s /lib/udev/rules.d/80-net-setup-link.rules /etc/udev/rules.d/80-net-setup-link.rules

и перезапускаем сервер, после чего должны появиться IP-интерфейсы всех модемов с теми именами, которые вы прописали в вышеуказанных конфиг файлах.
Доп информация по этой проблеме тут: https://askubuntu.com/questions/1076798/how-to-avoid-same-duplicate-mac-address-for-huawei-e3372h-607-4g-modems?noredirect=1

Если после рестарта появились интерфесы и у них есть IP-адреса, то идем в п. 8. Если адресов нет, то продолжаем со следующего пункта

7. Настраиваем такой сетевой конфиг

Для Ubuntu:

jaka@netbot:~$ cat /etc/netplan/00-installer-config.yaml
network:
  ethernets:
    ens18:
      dhcp4: false
      addresses: [192.168.1.63/24]
      routes:
        - to: 0.0.0.0/0
          via: 192.168.1.1
          metric: 50
    enp1s27u1:
      dhcp4: false
      addresses: [192.168.8.100/24]
      routing-policy:
        - from: 192.168.8.100
          table: 8
      routes:
        - to: 0.0.0.0/0
          via: 192.168.8.1
          table: 8
          metric: 101
    enp1s27u2:
      dhcp4: false
      addresses: [192.168.9.100/24]
      routing-policy:
        - from: 192.168.9.100
          table: 9
      routes:
        - to: 0.0.0.0/0
          via: 192.168.9.1
          table: 9
          metric: 102
  version: 2
jaka@netbot:~$


Для версий линукса, где сетью управляет пакет Network Manager (утилита nmcli):
Вывести текущий список connections можно командой 
sudo nmcli c
Из вывода команды надо взять идентификаторы тех коннекшинов, которые отвечают за модемы, и далее выполнить следующие команды для каждого коннекшина:

nmcli connection modify 1bd12218-2b11-3b78-a08e-d50eeb64f51c ipv4.routes "0.0.0.0/0 192.168.8.1 table=8" ipv4.routing-rules "priority 108 from 192.168.8.100 table 8"
nmcli connection modify 1bd12218-2b11-3b78-a08e-d50eeb64f52c ipv4.routes "0.0.0.0/0 192.168.9.1 table=9" ipv4.routing-rules "priority 109 from 192.168.9.100 table 9"
nmcli connection modify 1bd12218-2b11-3b78-a08e-d50eeb64f53c ipv4.routes "0.0.0.0/0 192.168.10.1 table=10" ipv4.routing-rules "priority 110 from 192.168.10.100 table 10"
nmcli connection modify 1bd12218-2b11-3b78-a08e-d50eeb64f54c ipv4.routes "0.0.0.0/0 192.168.11.1 table=11" ipv4.routing-rules "priority 111 from 192.168.11.100 table 11"
nmcli connection modify 1bd12218-2b11-3b78-a08e-d50eeb64f55c ipv4.routes "0.0.0.0/0 192.168.12.1 table=12" ipv4.routing-rules "priority 112 from 192.168.12.100 table 12"


если коннекшины не созданы и не выводятся в списке nmcli c, то их надо создать. Ниже вариант создания со статическим назначением им IP-адресов, хотя можно и динамически.
nmcli connection add type ethernet con-name modem8 ifname enp0s20f0u5u1u1 ipv4.method manual ipv4.addresses 192.168.8.100/24 ipv4.routes "0.0.0.0/0 192.168.8.1 table=8" ipv4.routing-rules "priority 108 from 192.168.8.100 table 8"
nmcli connection add type ethernet con-name modem9 ifname enp0s20f0u5u1u3 ipv4.method manual ipv4.addresses 192.168.9.100/24 ipv4.routes "0.0.0.0/0 192.168.9.1 table=9" ipv4.routing-rules "priority 109 from 192.168.9.100 table 9"
nmcli connection add type ethernet con-name modem10 ifname enp0s20f0u5u2 ipv4.method manual ipv4.addresses 192.168.10.100/24 ipv4.routes "0.0.0.0/0 192.168.10.1 table=10" ipv4.routing-rules "priority 110 from 192.168.10.100 table 10"
nmcli connection add type ethernet con-name modem11 ifname enp0s20f0u5u4 ipv4.method manual ipv4.addresses 192.168.11.100/24 ipv4.routes "0.0.0.0/0 192.168.11.1 table=11" ipv4.routing-rules "priority 111 from 192.168.11.100 table 11"
nmcli connection add type ethernet con-name modem12 ifname enp0s20f0u2 ipv4.method manual ipv4.addresses 192.168.12.100/24 ipv4.routes "0.0.0.0/0 192.168.12.1 table=12" ipv4.routing-rules "priority 112 from 192.168.12.100 table 12"

для варианта с nmcli, чтобы зафиксировать имя основного интерфейса ethernet, дабы оно после каждого рестарта не менялось со сбросом всех настроек, надо сделать так:
echo 'SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="02:00:00:24:1c:01", NAME="eth0"' | sudo tee /etc/udev/rules.d/70-persistent-net.rules
где надо подставить мак-адрес вашего сетевого интерфейса. После чего надо сделать рестарт

После этого можно присвоить данному интерфейсу постоянное имя и статические IP-параметры через nmcli:
nmcli connection mod "eth0" ipv4.method manual ipv4.addresses 192.168.1.50/24 ipv4.routes "0.0.0.0/0 192.168.1.1" ipv4.route-metric 50
nmcli connection reload;nmcli connection down "eth0";nmcli connection up "eth0"

Очень важно установить метрику более выского приоритета для основного маршрута через данный интерфейс, иначе дефолтный маршрут может установиться через какой-нибудь модем и основной трафик пойдет не через домашний интернет-канал, а через один из модемов.

8. Если слетел адрес ДНС, то прописать 8.8.8.8 в /etc/resolv.conf

9. На линуксе установить doker по инструкции https://docs.docker.com/engine/install/ubuntu/

10. Поднятие контейнера 3proxy:

Перед выполнением нижеприведенной команды docker run надо настроить конфигурационный файл 3proxy.cfg, и положить его в домашнюю папку пользователя /home/<имя пользователя>/3proxy. Зайти в эту папку и выполнить команду:

Для Intel платформ:
sudo docker run -dt --restart always --network host -v $(pwd):/usr/local/3proxy/conf --name 3proxy 3proxy/3proxy

Для raspberry или armbian (процессоры с ARM-архитектурой):
sudo docker run -dt --restart always --network host -v $(pwd):/usr/local/3proxy/conf --name 3proxy victorrds/3proxy


11. Поднятие контейнера haproxy:

Перед выполнением нижеприведенной команды docker run надо настроить конфигурационный файл haproxy.cfg, и положить его в домашнюю папку пользователя /home/<имя пользователя>/haproxy. Зайти в эту папку и выполнить команду:

Для Intel:
sudo docker run -dt --restart always --name haproxy --network host -v $(pwd):/usr/local/etc/haproxy:ro haproxytech/haproxy-ubuntu

Для raspberry или armbian (процессоры с ARM-архитектурой):
sudo docker run -dt --restart always --name haproxy --network host -v $(pwd):/usr/local/etc/haproxy:ro haproxytech/haproxy-alpine:2.4
   
полная инструкция HAProxy https://www.haproxy.com/blog/how-to-run-haproxy-with-docker/


12. Скрипт управления модемами написан на Python. Его можно запускать либо в отдельном контейнере с Python, либо установить прямо на хосте.
Чтобы установить Docker-контейнер выполняем команду:
docker run -dt --restart always --name ipchanger --network host python
и дальнейшие настройки уже производим внутри контейнера. 

Я подумал, что контейнер тут излишний, поэтому проще скрипт устанавливать прямо на хосте и по сей день на всех проксях ставлю его прямо на хост.

- Если не установлен Python, то ставим его sudo apt install python, а также программу pip (sudo apt install pip).

- Далее устанавливаем библиотеки управления модемами через API:
pip install huawei-lte-api

- а также программу socat:
sudo apt install socat

- ну и программу jq
sudo apt install jq

- копируем скрипт ipchanger.py https://github.com/RAbuzyarov/MProxy/blob/master/ipchanger/ipchanger.py в папку /home/<имя пользователя>/ipchanger
- копируем и настраиваем список модемов в виде файла ltemodems.cfg https://github.com/RAbuzyarov/MProxy/blob/master/ipchanger/ltemodems.cfg  в ту же папку.
- настраиваем в параметрах скрипта ipchanger.py (в самом начале скрипта) правильный пароль доступа к модемам и указываем со слешом на конце полный путь к папке, где лежит скрипт ipchanger.py.
- добавляем задание на ежеминутный запуск скрипта:
crontab -e
*/1 * * * * /home/<имя пользователя>/ipchanger.py >/dev/null 2>&1


13. Как найти лог определенного контейнера Docker
Сначала найдите путь к файлу журнала целевого контейнера.

Вы можете получить путь к файлу лога контейнера под названием my-app, выполнив следующую команду:

docker inspect --format='{{.LogP
Очистка файла лога
Вы можете очистить содержимое журнала, не удаляя его, передав echo пустую строку в его содержимое.

Владельцем файла будет root, поэтому вам нужно будет выполнить эту операцию в оболочке root.

Следующая команда очистит файл журнала:

sudo sh -c 'echo "" > $(docker inspect --format="{{.LogPath}}" my-app)'
Интерполяция оболочки используется для динамического получения пути к файлу журнала для контейнера my-app.

Вместо этого вы можете вручную подставить путь, полученный ранее.

Когда вы запустите docker logs my-app, вы увидите пустой вывод, если только контейнер не возобновил запись строк за прошедшее время.

14. Настройка ротации логов

Многие драйверы логирования Docker, включая json-file, имеют опциональную поддержку ротации логов, которую можно включить глобально для демона Docker или на основе каждого контейнера.

Параметры демона настраиваются в файле /etc/docker/daemon.json.

Вот пример, который ротирует логи контейнеров, когда они достигают 8 МБ.

В каждый момент времени сохраняется до пяти файлов, при этом старые файлы автоматически удаляются при новой ротации.

{
    "log-opts": {
        "max-size": "8m",
        "max-file": "5"
    }
}
Перезапустите демон Docker, чтобы применить изменения:

sudo service docker restart
Ротация на уровне демона применяется ко всем вновь созданным контейнерам.

Изменения не затронут контейнеры, которые уже существуют на вашем хосте.

Ротация может быть настроена для отдельных контейнеров с помощью флагов –log-opts.

Они отменяют настройки демона Docker по умолчанию.

Чтобы отключить логирование контейнеров нужно создать, либо отредактировать файл /etc/docker/daemon.json добавив в него строки: {"log-driver": "none"}. После чего потребуется перезапуск docker и всех контейнеров: service docker restart.
