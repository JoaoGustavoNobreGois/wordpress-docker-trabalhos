# Trabalho 1 — WordPress e MySQL

Implementação em Docker Compose do tutorial de instalação. O Compose cria dois contêineres, configura o banco WordPress no MySQL 5.7 e publica o WordPress em http://localhost:8080. O MySQL fica disponível apenas no host local, na porta 3306.

## Executar

Com o Docker Desktop em funcionamento, abra um terminal nesta pasta e execute:

    docker-compose up -d
    docker-compose ps

Acesse http://localhost:8080 e conclua a instalação de cinco minutos do WordPress. Na primeira execução, a inicialização do banco pode levar alguns segundos.

## Verificar

    docker-compose ps
    curl.exe -I http://localhost:8080/

As evidências visuais serão colocadas em [screenshots](screenshots/). Para encerrar, execute docker-compose down. Esse comando preserva os volumes.
