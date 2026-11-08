# Embeddings locais e deduplicação "mesma história" — medições (2026-11-07/08)

Base das decisões da P1 sobre embeddings (SDD §6.3, §6.7, D3). Tudo medido nesta máquina (AMD Ryzen 5 5500, 12 threads, 32 GB, Windows 11), com `fastembed` 0.9.1 e `onnxruntime` 1.31 em CPU.

## Resultado em um parágrafo

O BGE-M3, previsto no SDD v1.1, não está na lista de modelos densos do `fastembed` 0.9. Entre os multilíngues disponíveis, o **EmbeddingGemma-300m** tem a melhor relação entre qualidade e custo: 768 dimensões, contexto de 2.048 tokens, ~1,2 GB baixados uma vez e ~2,4 itens/s em CPU, o que dá ~1 min por dia. Nenhum dos cinco modelos testados separa "a mesma história contada de outro jeito" de "mesmo tema, trabalho diferente" por cosseno. Por isso a fusão automática usa títulos quase idênticos, e o embedding alimenta a novidade (D) e o classificador.

## Velocidade e separação (40 itens reais do run de 2026-11-07, título + 1.500 caracteres)

"Mesma história" são 6 pares redigidos de forma diferente, um deles EN↔PT. "Mesmo tema, outro trabalho" são 6 pares do mesmo assunto. Gap é o mínimo de "mesma história" menos o máximo de "outro trabalho": positivo significa que existe um limiar que separa os dois.

| Modelo | Itens/s | Dim | Mesma história (mín · média) | Outro trabalho (máx · média) | Gap | Itens distintos (média · máx) |
|---|---|---|---|---|---|---|
| google/embeddinggemma-300m (prefixo "task: clustering") | 2,4 | 768 | 0,829 · 0,903 | 0,918 · 0,802 | −0,089 | 0,656 · 0,861 |
| Qwen/Qwen3-Embedding-0.6B-Q | 0,5 | 1024 | — | — | — | 0,650 · 0,936 |
| BAAI/bge-small-en-v1.5 | 7,3 | 384 | 0,775 · 0,873 | 0,892 · 0,732 | −0,117 | 0,671 · 0,859 |
| BAAI/bge-base-en-v1.5 | 2,7 | 768 | 0,763 · 0,855 | 0,835 · 0,692 | −0,073 | 0,608 · 0,832 |
| snowflake/snowflake-arctic-embed-m-long | 2,1 | 768 | 0,827 · 0,898 | 0,876 · 0,772 | −0,049 | 0,523 · 0,824 |
| minishlab/potion-multilingual-128M (estático) | 367 | 256 | 0,539 · 0,717 | 0,479 · 0,347 | +0,061 | 0,450 · 0,795 |

Leitura:
- O limiar de cosseno ≥ 0,85 para "mesma história", previsto no SDD v1.1, fundiria trabalhos diferentes em todos os modelos densos.
- O modelo estático separa o conjunto pequeno de teste porque é quase lexical, mas dois itens distintos reais chegaram a 0,795.
- O Qwen3-0.6B é 5× mais lento que o EmbeddingGemma sem ganho visível aqui.

## Deduplicação por título no vault antigo (2.893 notas)

Regra:
- normaliza o título (minúsculas, sem acento, só alfanuméricos);
- é a mesma história se o título normalizado for igual, ou se o Jaccard de tokens for ≥ 0,8, ou se o SequenceMatcher for ≥ 0,92;
- exige pelo menos 4 tokens informativos ou 25 caracteres;
- números no título precisam coincidir.

Resultado:
- 11 duplicatas em 0,43 s, com índice invertido de tokens; a primeira versão, comparando todos com todos, levou 21,9 s.
- 9 das 11 vieram de fontes diferentes, quase todas o mesmo artigo no RSS do JMIR e no PubMed.
- A única fusão aproximada juntou um editorial ao artigo que ele comenta, aceitável como "mesma história".
- Nenhum falso positivo entre trabalhos diferentes.
- Os testes acharam um caso que a primeira versão errava: títulos que só diferem num número ("Qwen3.8" × "Qwen3.9", "Part 1" × "Part 2") eram fundidos. Daí a regra dos números.

## Novidade (D)

D vem da maior similaridade com os itens dos últimos 30 dias: 5 abaixo de 0,70; 0 acima de 0,94; limiares intermediários 0,76, 0,82 e 0,88. Com o EmbeddingGemma, itens distintos ficam em média em 0,65 e no p95 em 0,80, então um item típico recebe D = 3–5. Com o acúmulo de itens a similaridade máxima tende a subir; recalibrar os limiares depois de 2 semanas de dados (`config/rubric.yaml`).

## Ressalvas

- Os pares "mesma história" e "outro trabalho" foram escritos à mão: 6 + 6, indicativos, não um benchmark.
- Downloads do Hugging Face falharam com `CERTIFICATE_VERIFY_FAILED` sem o `truststore`. O CLI injeta o `truststore` desde a P0, mas scripts avulsos precisam fazer o mesmo.
- Um download interrompido deixa o cache do `fastembed` inconsistente ("No such file or directory" ao carregar). Nesse caso, apague a pasta do modelo em `data/models/fastembed/`.
