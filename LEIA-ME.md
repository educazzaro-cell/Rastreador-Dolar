# Rastreador Macro do Dólar: atualização automática

Arquivos
- index.html: a página (lê o data.json sozinha)
- fetch_data.py: busca preços (Yahoo Finance + Banco Central), curva DI e notícias
- .github/workflows/update.yml: roda o script todo dia útil às 18:30 (Brasília)
- manual.exemplo.csv: modelo para CDS, minério e fluxo (renomeie para manual.csv e preencha)
- curva_di.csv (opcional): vencimento,hoje,1d,1s,1m

Passo a passo (GitHub, grátis)
1. Crie um repositório e envie todos estes arquivos (mantenha a pasta .github).
2. Settings > Pages > Source: branch main, pasta root. A página fica em usuario.github.io/repositorio.
3. Para classificar as notícias: Settings > Secrets and variables > Actions > New secret, nome ANTHROPIC_API_KEY, valor = sua chave da API. Sem a chave, as notícias aparecem como Neutro.
4. Aba Actions > Atualizar dados > Run workflow para a primeira atualização. Depois roda sozinho.

Limites
- DIFJUROS é um proxy (Selic meta menos juros de 10 anos dos EUA).
- CDS, minério, fluxo estrangeiro e a curva DI não têm fonte gratuita estável: preencha manual.csv e curva_di.csv ou o índice usa só o que existir.
- Yahoo Finance é fonte não oficial e pode falhar; se uma fonte cair, o script mantém o último valor.
