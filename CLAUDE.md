# flight-monitor — notas para sessões futuras

## O que é

MVP pessoal de monitoramento de preços de passagens aéreas. Sem
backend/frontend separados: um único script (`monitor.py`) agendado pelo
GitHub Actions, que lê `config.json`, consulta a Aviasales Data API
(Travelpayouts) e manda alertas via Telegram.

## Decisões de arquitetura

- **Persistência em arquivos no próprio repo** (`data/history.csv` e
  `data/state.json`), comitados de volta pelo workflow do Actions. Não há
  banco de dados — simplicidade > robustez aqui, é uso pessoal.
- **`state.json`** guarda só o menor preço já visto por rota (`min_price`),
  para decidir se um preço atual é "novo recorde de baixa".
- **`history.csv`** é um log append-only de todas as checagens — serve para
  análise manual depois (ex: abrir no Excel/planilha).
- **Credenciais sempre via variáveis de ambiente** /
  GitHub Secrets: `TRAVELPAYOUTS_TOKEN`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `TRAVELPAYOUTS_MARKER` (opcional). Nunca hardcode.
- **Try/except por rota**: uma rota com erro (API fora do ar, formato
  inesperado, etc.) não pode interromper o processamento das demais. Erros são
  só logados no stdout (aparecem no log do Actions).
- **Regra de alerta**:
  - Primeira execução de uma rota (sem entrada em `state.json`): só alerta se
    o preço já estiver `<= max_price` (evita spam de notificação ao começar a
    monitorar).
  - Execuções seguintes: alerta se `preço <= max_price` OU se for um novo
    recorde de menor preço (`is_new_low`).

## Pontos de atenção / onde mexer

- **Formato da resposta da API**: a função `fetch_cheapest_flight()` em
  `monitor.py` é o único lugar que entende o JSON da Aviasales Data API. Se a
  Travelpayouts mudar o formato (ex: renomear `data` ou `price`), é só ajustar
  ali — o resto do código trabalha com o dict normalizado que essa função
  devolve.
- **Cron do Actions**: roda a cada 3h (`0 */3 * * *`), mas o agendamento do
  GitHub é "best effort" e pode atrasar. Workflows agendados são desativados
  após 60 dias sem atividade no repositório (o próprio commit automático do
  workflow tende a manter isso ativo).
- **Preços em cache**: a API não retorna cotação ao vivo — é aceitável para
  detectar tendência, mas o valor final precisa ser conferido na hora de
  comprar.

## Como testar localmente

Ver seção "Rodando localmente" do `README.md`. Sem as variáveis de ambiente
definidas, `monitor.py` deve sair com mensagem clara de qual credencial falta
(função `get_required_env`).
