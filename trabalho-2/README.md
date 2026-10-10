# Trabalho 2 — WordPress com Nginx e três instâncias

O Compose cria cinco contêineres: Nginx, três WordPress e um MySQL. As três instâncias compartilham o banco e a pasta html da máquina hospedeira. O Nginx monta a mesma pasta em /usr/share/nginx/html e encaminha as requisições às instâncias. Somente o Nginx publica uma porta no host. As redes frontend e backend separam o Nginx do MySQL.

As imagens seguem as versões especificadas no enunciado: mysql:5.7, wordpress:5.4.2-php7.2-apache e nginx:1.19.0.

## Executar

Com o Docker Desktop em funcionamento, abra um terminal nesta pasta e execute:

    docker-compose up -d
    docker-compose ps

Acesse http://localhost/ e conclua a instalação inicial do WordPress. A pasta html será criada automaticamente e está excluída do Git porque contém arquivos gerados e configuração do site.

## Verificar o balanceamento

Execute o comando abaixo várias vezes. O cabeçalho X-Upstream deve mostrar três endereços de contêiner ao longo das chamadas.

    1..12 | ForEach-Object { curl.exe -sI http://localhost/ | Select-String 'X-Upstream' }

Os WordPress e o MySQL não têm portas publicadas no host. Confirme com docker-compose ps. As evidências visuais serão colocadas em [screenshots](screenshots/).

Para encerrar sem apagar os dados, execute docker-compose down.

## Evidências

- [Cinco contêineres em execução, logo após a partida](screenshots/01-containers.png)
- [Balanceamento entre três IPs](screenshots/02-balanceamento.png)
- [Tela de instalação do WordPress pelo Nginx](screenshots/03-instalacao-wordpress.png)
