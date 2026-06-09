# Flight Monitor ✈️

Monitor pessoal de preços de passagens aéreas. Roda de graça no GitHub Actions,
busca o voo mais barato das rotas configuradas (via Aviasales Data API /
Travelpayouts) e me avisa no Telegram quando o preço cai.

É um MVP pessoal: sem backend, só um script Python agendado e um dashboard
Next.js que lê o `history.csv` gerado pelo monitor.

## Como funciona

A cada execução (padrão: a cada 3 horas), o `monitor.py`:

1. Busca o voo mais barato de cada rota em `config.json`.
2. Registra o resultado em `data/history.csv`.
3. Compara com o menor preço já visto, salvo em `data/state.json`.
4. Manda uma mensagem no Telegram se o preço estiver dentro do limite (`max_price`)
   ou se for um novo recorde de baixa.
5. Atualiza `data/state.json` e o GitHub Actions comita as mudanças de volta no repo.

## Setup passo a passo

### 1. Criar o token da Travelpayouts

1. Crie uma conta em https://www.travelpayouts.com/
2. Acesse o painel e gere um token de API ("API token") em
   https://www.travelpayouts.com/program/developer
3. Guarde esse valor — ele vai virar o secret `TRAVELPAYOUTS_TOKEN`.
4. (Opcional) Se você tiver um "marker" de afiliado, guarde também — ele vira o
   secret `TRAVELPAYOUTS_MARKER` e é incluído nos links das passagens.

### 2. Criar o bot no Telegram e pegar o chat id

1. No Telegram, fale com [@BotFather](https://t.me/BotFather) e use `/newbot`
   para criar um bot novo. Ele vai te dar um **token** — esse é o
   `TELEGRAM_BOT_TOKEN`.
2. Envie qualquer mensagem para o seu bot recém-criado (ele precisa ter
   recebido pelo menos uma mensagem sua).
3. No navegador, acesse:
   `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
   (troque `<SEU_TOKEN>` pelo token do bot).
4. Procure no JSON retornado o campo `"chat":{"id": ...}` — esse número é o seu
   `TELEGRAM_CHAT_ID`.

### 3. Cadastrar os secrets no GitHub

No repositório, vá em **Settings → Secrets and variables → Actions → New
repository secret** e cadastre:

- `TRAVELPAYOUTS_TOKEN`
- `TRAVELPAYOUTS_MARKER` (opcional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Nunca coloque esses valores direto no código ou no `config.json`.

### 4. Editar as rotas

Abra `config.json` e ajuste a lista `routes`. Cada rota tem:

- `name`: nome livre, usado nas mensagens e como chave no `state.json`.
- `origin` / `destination`: códigos IATA dos aeroportos (ex: `REC`, `LIS`).
- `departure_at`: mês (`"2026-09"`) ou data exata (`"2026-09-15"`).
- `return_at`: igual ao `departure_at`, ou `null` para passagem só de ida.
- `one_way`: `true` para só ida, `false` para ida e volta.
- `direct`: `true` para considerar só voos diretos.
- `max_price`: preço (na moeda definida em `currency`) a partir do qual eu
  quero ser avisado.

### 5. Ligar o workflow e testar

1. Faça o commit e push do projeto para o GitHub (sem nenhum secret real nos
   arquivos!).
2. Vá na aba **Actions** do repositório, escolha o workflow "Monitor de preços
   de passagens" e clique em **Run workflow** para testar manualmente.
3. Acompanhe o log da execução e confira se o alerta chegou no Telegram (ou se
   ao menos os logs mostram os preços encontrados).
4. Depois disso, o agendamento automático (`cron: "0 */3 * * *"`, a cada 3
   horas) assume sozinho.

## Gotchas (coisas para ter em mente)

- **Preços em cache**: a Aviasales Data API retorna preços de cache, não
  cotação ao vivo. Serve bem para detectar tendência de queda, mas confirme o
  valor real no site/agência antes de comprar.
- **Atraso no agendamento**: o `schedule` do GitHub Actions roda "best effort"
  — em horários de pico pode atrasar bastante (minutos a horas). Não conte com
  precisão de horário.
- **Workflows agendados são desativados após 60 dias sem atividade**: se o
  repositório ficar 60 dias sem nenhum commit/push, o GitHub desativa o
  schedule automaticamente. Como o próprio workflow comita o histórico, ele
  tende a se manter ativo sozinho — mas vale checar de vez em quando na aba
  Actions se está rodando.
- **Rate limits**: tanto a Travelpayouts quanto o Telegram têm limites de
  requisições. Não diminua demais o intervalo do cron nem adicione dezenas de
  rotas de uma vez.

## Rodando localmente (monitor Python)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# defina as variáveis de ambiente antes de rodar:
set TRAVELPAYOUTS_TOKEN=...
set TELEGRAM_BOT_TOKEN=...
set TELEGRAM_CHAT_ID=...

python monitor.py
```

---

## Dashboard Web (Fase 2)

Painel Next.js 14 que lê o `data/history.csv` gerado pelo monitor e exibe:

- Seletor de rota, gráfico de evolução de preço (Recharts), cards de resumo
  (menor preço / atual / variação) e tabela dos últimos registros.

### Rodando o dashboard localmente

```bash
cd dashboard
npm install
npm run dev
# Acesse http://localhost:3000
```

Em desenvolvimento, o dashboard lê `../data/history.csv` direto do disco. Não
é necessário nenhuma variável de ambiente (o CSV vazio exibe um estado amigável
no lugar dos gráficos).

### Deploy gratuito na Vercel

1. Crie uma conta em https://vercel.com e conecte seu repositório GitHub.
2. No momento de importar o projeto, defina o **Root Directory** como `dashboard`
   (é onde fica o `package.json` do Next.js).
3. Configure as **Environment Variables** no painel da Vercel
   (**Project → Settings → Environment Variables**):

   | Variável          | Obrigatória | Descrição                                                                                         |
   |-------------------|-------------|---------------------------------------------------------------------------------------------------|
   | `HISTORY_CSV_URL` | **Sim**     | URL "raw" do `data/history.csv` no GitHub. Ex: `https://raw.githubusercontent.com/<user>/<repo>/main/data/history.csv` |
   | `GITHUB_TOKEN`    | Só se privado | Personal Access Token com escopo de leitura `repo`. Necessário apenas se o repositório for privado. |

   > **Nunca** coloque os valores reais no código ou em arquivos comitados.
   > Use sempre as variáveis de ambiente da Vercel (ou `.env.local` localmente,
   > que o `.gitignore` já ignora).

4. Clique em **Deploy**. A Vercel faz o build automaticamente.

**Revalidação de cache**: o painel revalida os dados a cada 15 minutos
(`export const revalidate = 900` em `app/page.tsx`), alinhado com a frequência
do monitor (a cada 3 horas). Você pode reduzir esse valor se quiser dados mais
frescos, mas lembre que os preços da API já são de cache de qualquer forma.

**Gotcha de repositório privado**: se o repo for privado, o token precisa ter o
escopo `repo` (não apenas `public_repo`). Gere em
https://github.com/settings/tokens?type=beta e escolha "Only select
repositories" apontando para o seu repo de monitoramento.
