Поднятие контейнера 3proxy:
Перед выполнением нижеприведенной команды docker run надо настроить конфигурационный файл 3proxy.cfg, положить его в папку /etc/dockerapp/3proxy
docker run -dt --restart always --network host -v /etc/dockerapp/3proxy:/usr/local/3proxy/conf --name 3proxy victorrds/3proxy


Поднятие контейнера haproxy:
Перед выполнением команды в текущем каталоге должен лежать конфиг файл haproxy.cfg
sudo docker run -dt --restart always --name haproxy --network host -v $(pwd):/usr/local/etc/haproxy:ro haproxytech/haproxy-alpine:2.4
   
полная инструкция HAProxy https://www.haproxy.com/blog/how-to-run-haproxy-with-docker/
