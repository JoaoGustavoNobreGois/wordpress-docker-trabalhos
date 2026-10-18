# Trabalho 3 — testes de carga com Locust

Este ambiente estende o [trabalho 2](../trabalho-2/README.md): MySQL 5.7, até três instâncias WordPress 5.4.2, Nginx 1.19.0 e Locust 2.46.5. O script executa 27 testes (3 conteúdos × 3 quantidades de usuários × 3 quantidades de instâncias).

## Cenários

| Cenário | Conteúdo da publicação | Requisições por tarefa do Locust |
| --- | --- | --- |
| `imagem-1mb` | Imagem PNG de aproximadamente 1 MB | Página e imagem |
| `texto-400kb` | Texto de 400 KB | Página |
| `imagem-300kb` | Imagem PNG de aproximadamente 300 KB | Página e imagem |

O [gerador](generate_fixtures.py) cria os arquivos localmente; o [script de preparação](seed.php) publica o conteúdo no WordPress. O Locust solicita as imagens explicitamente, pois seu cliente HTTP não carrega os recursos de uma página como um navegador. As publicações e a instalação do WordPress persistem em `html/` e no volume do MySQL, que não entram no Git.

## Executar

Requisitos: Docker Desktop/Engine com Compose, Python 3.10 ou superior e portas locais 8090 e 8089 livres. A partir da raiz do repositório:

```powershell
python ".\trabalho 3\run_matrix.py"
```

O comando cria as publicações, valida os três destinos de `X-Upstream`, executa 10, 50 e 100 usuários simultâneos para cada cenário e para 1, 2 e 3 instâncias WordPress, e gera o resumo e os gráficos. Cada execução dura 30 segundos; o tempo total costuma exceder 15 minutos. Para conferir uma execução curta antes da matriz:

```powershell
python ".\trabalho 3\run_matrix.py" --smoke --duration 10s
```

O site fica em <http://localhost:8090>. Para abrir a interface do Locust após a preparação do blog:

```powershell
cd ".\trabalho 3"
docker compose --profile load up -d locust
```

A interface fica em <http://localhost:8089>. Defina, por exemplo, 100 usuários, taxa de entrada 100/s e host `http://nginx`. A variável `SCENARIO` do Compose seleciona a publicação; por padrão, é `imagem-1mb`. O script automatizado usa exatamente o mesmo arquivo [locustfile.py](locustfile.py).

## Resultados

- [Resumo das 27 combinações](results/resumo.csv): requisições, falhas, tempo médio, mediana, p95, vazão e tamanho médio da resposta.
- [Gráficos](results/graficos): para cada cenário, tempo médio de resposta, requisições por segundo e taxa de falhas, com usuários no eixo X e uma linha por quantidade de instâncias.
- [Dados brutos](results/raw): CSVs exportados pelo Locust para cada execução, inclusive histórico.
- [Manifesto das execuções](results/runs.json): parâmetros, horários e códigos de saída do Locust.

Os gráficos usam a linha agregada do CSV do Locust. Nos cenários com imagem, essa linha inclui tanto a página quanto a imagem, portanto a vazão em requisições por segundo deve ser interpretada junto com o número de recursos solicitados por tarefa. Os dados são medições do ambiente onde o script foi executado, não previsões de produção.

## Capturas de tela para evidência

Depois que a matriz terminar, envie duas capturas de tela, caso sejam exigidas na entrega: (1) `docker compose ps` na pasta `trabalho 3`, mostrando MySQL, Nginx e três WordPress ativos; (2) a aba **Charts** do Locust em `http://localhost:8089`, depois de iniciar um teste de 100 usuários pela interface. Para a segunda captura, execute antes `docker compose --profile load up -d locust` na pasta do trabalho. Inclua a barra de endereço e os gráficos. As capturas enviadas serão colocadas em `screenshots/`.

As imagens antigas exigidas pelo enunciado têm atualizações de segurança pendentes. Este Compose publica apenas as interfaces web em `127.0.0.1`; MySQL e WordPress só se comunicam pela rede interna dos contêineres. As credenciais de demonstração devem ser usadas apenas localmente.
