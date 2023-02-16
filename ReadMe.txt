
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
2.
3. Подключить модемы и если ОС на виртуализации, то пробросить подключение USB модемов в виртуалку.
4. Настроить через веб-интерфесы IP-адреса модемам, и вход в вебку по логину/паролю
5. При правильном подключении модемы в линуксе должны получить каждый свой IP-интерфейс с IP-адресом,
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

Если вы видите не все интерфейсы, или вообще ни одного не видите, то это значит у некоторых или у всех модемов одинаковый MAC-адрес,
что запрещено. Такое может быть, если на модемы заливалась прошивка с идентичными настройками. Переходите на сл. пункт.

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
NamePolicy=path
MACAddress=0c:5b:8f:27:9a:64

где в поле Path указывается найденное ранее значение ID_PATH модема, а в поле MACAddress значение мак-адреса, которое
надо присвоить этому модему. Можно взять мак-адрес исходный и просто менять последнюю цифру, чтобы у каждого модема
был уникальный мак-адрес.

После того, как для каждого модема создан такой конфг-файл, выполняем команду:
sudo ln -s /lib/udev/rules.d/80-net-setup-link.rules /etc/udev/rules.d/80-net-setup-link.rules

и перезапускаем сервер, после чего должны появиться IP-интерфейсы всех модемов.
Доп информация по этой проблеме тут: https://askubuntu.com/questions/1076798/how-to-avoid-same-duplicate-mac-address-for-huawei-e3372h-607-4g-modems?noredirect=1

Если после рестарта появились интерфесы и у них есть IP-адреса, то идем в п. 8. Если адресов нет, то продолжаем со
следующего пункта

7. Настраиваем такой сетевой конфиг

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

8. Поправить адрес DNS 8.8.8.8 в /etc/resolv.conf

9. На линуксе установить doker по инструкции https://docs.docker.com/engine/install/ubuntu/

10. Поднятие контейнера 3proxy:

Перед выполнением нижеприведенной команды docker run надо настроить конфигурационный файл 3proxy.cfg, и положить его в папку /etc/dockerapp/3proxy

Для Intel платформ:
sudo docker run -dt --restart always --network host -v /etc/dockerapp/3proxy:/usr/local/3proxy/conf --name 3proxy 3proxy/3proxy

Для raspberry:
sudo docker run -dt --restart always --network host -v /etc/dockerapp/3proxy:/usr/local/3proxy/conf --name 3proxy victorrds/3proxy


10. Поднятие контейнера haproxy:

Перед выполнением команды в текущем каталоге должен лежать конфиг файл haproxy.cfg

Для Intel:
sudo docker run -dt --restart always --name haproxy --network host -v $(pwd):/usr/local/etc/haproxy:ro haproxytech/haproxy-ubuntu

Для Raspberry:
sudo docker run -dt --restart always --name haproxy --network host -v $(pwd):/usr/local/etc/haproxy:ro haproxytech/haproxy-alpine:2.4
   
полная инструкция HAProxy https://www.haproxy.com/blog/how-to-run-haproxy-with-docker/


10. Поднятие контейнера Python, на котором будет крутиться скрипт смены IP-адресов changeIP.py (пока не используется):

docker run -dt --restart always --name ipchanger --network host python

Установка Python классов для работы с API Huawei


pip install huawei-lte-api
sudo apt install socat


11. crontab -e
*/1 * * * * /home/jaka/changeIP.py 2> /dev/null 1> /dev/null
установить пакет резолвера

