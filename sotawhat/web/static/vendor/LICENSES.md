# Bibliotecas JavaScript da interface

Os arquivos ficam no pacote para que a interface funcione sem CDN e sem internet (SDD §2.3, local-first). Foram baixados do jsDelivr em 2026-11-08. O teste `tests/test_web.py` confere cada SHA-256 abaixo.

| Arquivo | Pacote npm | Versão | Licença | Origem | SHA-256 |
|---|---|---|---|---|---|
| `graphology.umd.min.js` | graphology | 0.26.0 | MIT (`graphology.LICENSE.txt`) | https://cdn.jsdelivr.net/npm/graphology@0.26.0/dist/graphology.umd.min.js | `dc337efa23903f61e064c8e7e7f93a429e6855dccfc2458802b4ed30c621c087` |
| `graphology-library.min.js` | graphology-library | 0.8.0 | MIT (`graphology-library.LICENSE.txt`) | https://cdn.jsdelivr.net/npm/graphology-library@0.8.0/dist/graphology-library.min.js | `5323729ec6d4ac5d98a245873646c27fd80c7234df13972faec5869f3c54a105` |
| `three/three.module.js` | three | r186 | MIT (`three/LICENSE.txt`) | já no pacote desde as aulas 3D (commit f864e03) | `211760950dc7bddeb46b09ca7fa4d3620ddde43168a4fba8560489f86a92548f` |
| `three/three.core.js` | three | r186 | MIT (`three/LICENSE.txt`) | idem | `8bf68efebbef2b6f162a5bc5746ec88a60523254c4ae0b042277ed0ce0b30a07` |
| `three/OrbitControls.js` | three (examples/jsm) | r186 | MIT (`three/LICENSE.txt`) | idem | `97c6ad5c5b19d958be1652c7b3f920062ad1be836850008327ae463b16d91ef5` |

O grafo é desenhado em 3D pelo three.js desde 2026-11-20 (`graph3d.js`, carregado como módulo; o `importmap` do `index.html` aponta `three` para `three/three.module.js`). O sigma.js 3.0.3, que desenhava o grafo em 2D, saiu do pacote. O graphology continua: guarda o grafo no navegador e calcula as comunidades (Louvain).
