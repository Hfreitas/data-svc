# Onboarding — N8N e Workflows da MEIrelles

Este documento apresenta o N8N, descreve os fluxos que compõem a MEIrelles e explica por que estamos criando o `data-svc` como camada entre o N8N e o banco de dados.

---

## O que é o N8N

O N8N é uma plataforma de automação de fluxos de trabalho — pense nele como um "construtor de pipelines" visual. Cada fluxo (workflow) é um diagrama onde:

- **Nós (nodes)** são as peças: receber um webhook, executar uma query SQL, chamar uma API, rodar um trecho de código, acionar um agente de IA.
- **Conexões** ligam os nós e definem a ordem de execução.
- **Triggers** são o ponto de partida: um webhook recebido, um horário agendado, ou um clique manual.

Na MEIrelles o N8N faz três papéis ao mesmo tempo: **recebe as mensagens do WhatsApp**, **orquestra o agente de IA** e **dispara os fluxos automáticos** (relatórios, lembretes, dicas semanais).

---

## Arquitetura geral

```
WhatsApp (usuário)
       │
       ▼
    Z-API  ──→  Webhook N8N
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
   MEIrelles Agent      Workflows automáticos
   (agente de IA)       (agendados por cron)
          │                    │
          ▼                    ▼
       Supabase (PostgreSQL)   ◄── hoje: acesso direto
                                    futuro: via data-svc
```

O Supabase é o banco PostgreSQL na nuvem onde ficam todos os dados dos usuários: gastos, vendas, agendamentos, listas de compras e contas recorrentes.

---

## Os fluxos da MEIrelles

### MEIrelles Agent (workflow principal)

**Tipo:** Webhook — dispara a cada mensagem recebida no WhatsApp.

**O que faz:**

1. Recebe a mensagem via webhook da Z-API.
2. Busca o contexto do usuário no banco (`usuarios`, `agendamentos`) para personalizar a resposta.
3. Injeta esse contexto no prompt do agente de IA (Claude).
4. O agente decide o que fazer: responder, registrar um gasto, criar um agendamento, etc.
5. Executa a ação via ferramentas (Postgres Tools): consultar agenda, confirmar agendamento, registrar comprovante.
6. Devolve a resposta ao usuário via Z-API.

**Tabelas acessadas diretamente:** `usuarios`, `agendamentos`, `comprovantes`, `itens_lista`, `lista_compras`, `contas_recorrentes`.

---

### Listas, Comprovantes e Saldos (workflow de suporte)

**Tipo:** Webhook — chamado pelo agente principal como sub-fluxo.

**O que faz:** Gerencia as operações de leitura e escrita relacionadas a finanças e listas:

- Calcula saldo do mês (vendas − gastos).
- Lista comprovantes por período e tipo (gastos, vendas ou relatório completo).
- Registra novos comprovantes com idempotência via `item_hash`.
- Cria, lista, adiciona e remove itens de listas de compras.

**Tabelas acessadas diretamente:** `comprovantes`, `lista_compras`, `itens_lista`.

---

### W1 — Dicas Semanais (toda segunda, 8h)

**Tipo:** Cron — dispara automaticamente toda segunda-feira às 8h.

**O que faz:**

1. Chama o `dicas-svc` (microserviço Node.js) que agrega os dados dos usuários e monta um batch.
2. Recebe o batch via webhook de retorno.
3. Para cada usuário, monta um contexto com vendas, gastos e agenda da semana.
4. Aciona o agente de IA para gerar uma análise personalizada de desempenho.
5. Envia a mensagem via Z-API.

---

### W4 / W5 — Checkup Sexta-feira (toda sexta, 17h)

**Tipo:** Cron — dispara toda sexta-feira às 17h.

**O que faz:** Verifica se o MEI registrou gastos e vendas durante a semana. Se não registrou, estimula o envio. Se registrou, faz um resumo simples com um único insight. Prepara o terreno para a análise de segunda-feira.

---

### W6 — Checkup Quarta-feira

**Tipo:** Cron — dispara toda quarta-feira.

**O que faz:** Versão mais leve do checkup de sexta. Lembra o MEI de manter os registros em dia durante a semana.

---

### Relatorio Mensal (todo dia 1°, 9h)

**Tipo:** Cron — dispara no primeiro dia de cada mês às 9h.

**O que faz:**

1. Chama o `relatorio-svc` (microserviço Node.js) para gerar o PDF do relatório mensal.
2. Recebe o PDF via webhook de retorno.
3. Envia o PDF ao usuário via Z-API.

O `relatorio-svc` acessa o banco diretamente para agregar os dados do mês anterior (comprovantes, saldo, agenda).

---

### Lembretes Automáticos

**Tipo:** Cron — roda a cada hora.

**O que faz:** Verifica agendamentos com início nos próximos 15 minutos. Para cada um, envia um lembrete via WhatsApp e marca o campo `lembrete_enviado = true` para não reenviar.

**Tabela acessada:** `agendamentos`.

---

### Retornar Estado Menu

**Tipo:** Cron — roda periodicamente.

**O que faz:** Reseta `estado_atual → 'menu'` para usuários que ficaram presos em outros estados (ex: aguardando resposta de um fluxo que nunca foi concluído). Evita que o usuário fique travado sem conseguir interagir.

**Tabela acessada:** `usuarios`.

---

### W7 — Sync Sheets Diário (todo dia, 23h)

**Tipo:** Cron — roda todo dia às 23h.

**O que faz:** Exporta os dados da tabela `usuarios` para uma planilha no Google Sheets. Limpa os dados anteriores e insere os atuais. Serve como painel de acompanhamento operacional.

---

### Payment

**Tipo:** Webhook.

**O que faz:** Integração com a Asaas (gateway de pagamentos). Recebe requisição de cobrança, repassa para a API da Asaas e aguarda o callback de confirmação. **Fora do escopo do `data-svc`.**

---

## Por que o N8N não deve acessar o banco diretamente

Hoje todo fluxo usa nós do tipo **Postgres** para ler e escrever no Supabase. Isso funciona, mas cria três problemas que ficam piores conforme o sistema cresce.

### 1. Sem cache — toda mensagem vai ao banco

Cada mensagem recebida dispara pelo menos uma query para buscar o contexto do usuário. Com dezenas de usuários simultâneos, isso significa dezenas de round-trips ao Supabase a cada minuto — para buscar os mesmos dados que, na maioria das vezes, não mudaram desde a última mensagem.

### 2. SQL espalhado pelo sistema

As queries vivem dentro de nós no N8N, misturadas com lógica de roteamento, montagem de prompt e chamadas de API. Não há um lugar centralizado para revisar, otimizar ou testar uma query. Para entender "como o saldo é calculado", é preciso abrir o workflow no editor visual e procurar o nó certo.

### 3. Impossível testar em isolamento

Não existe uma forma simples de rodar uma query do N8N localmente, passar diferentes entradas e verificar o resultado. Toda "mudança" em uma query implica alterar o workflow, publicar, disparar manualmente e observar o log — um ciclo lento e frágil.

---

## O que o `data-svc` resolve

```
Antes:
  N8N  ─── Postgres node ───→  Supabase

Depois:
  N8N  ─── HTTP node ───→  data-svc  ───→  Supabase
                                ↑
                           cache em memória
                           SQL isolado e testável
```

O `data-svc` é um serviço HTTP Flask que o N8N chama no lugar dos nós Postgres. Ele:

| Problema atual | Como o `data-svc` resolve |
|---|---|
| Sem cache | Responde leituras repetidas em < 20 ms usando `TTLCache` em memória |
| SQL espalhado | Todo SQL fica em `src/queries/` — funções puras, testáveis, revisáveis |
| Impossível testar queries | `pytest` roda as queries contra um banco local Docker sem precisar abrir o N8N |

O critério de conclusão do projeto é claro: **nenhum nó do N8N deve chamar o Supabase diretamente**. Todas as leituras e escritas passam pelo `data-svc`.
