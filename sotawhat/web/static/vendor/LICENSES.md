# Bibliotecas JavaScript da interface

Os arquivos ficam no pacote para que a interface funcione sem CDN e sem internet (SDD §2.3, local-first). Foram baixados do jsDelivr em 2026-11-08. O teste `tests/test_web.py` confere cada SHA-256 abaixo.

| Arquivo | Pacote npm | Versão | Licença | Origem | SHA-256 |
|---|---|---|---|---|---|
| `sigma.min.js` | sigma | 3.0.3 | MIT (`sigma.LICENSE.txt`) | https://cdn.jsdelivr.net/npm/sigma@3.0.3/dist/sigma.min.js | `58e30383ab428f832068d9d16a5215c65ba12430d438ed091c5703f398de9e16` |
| `graphology.umd.min.js` | graphology | 0.26.0 | MIT (`graphology.LICENSE.txt`) | https://cdn.jsdelivr.net/npm/graphology@0.26.0/dist/graphology.umd.min.js | `dc337efa23903f61e064c8e7e7f93a429e6855dccfc2458802b4ed30c621c087` |
| `graphology-library.min.js` | graphology-library | 0.8.0 | MIT (`graphology-library.LICENSE.txt`) | https://cdn.jsdelivr.net/npm/graphology-library@0.8.0/dist/graphology-library.min.js | `5323729ec6d4ac5d98a245873646c27fd80c7234df13972faec5869f3c54a105` |

Por que o sigma.js 3 e não o 4: a versão 4.0.0 saiu em outubro de 2026, com outra estrutura de pacote, e ainda é nova demais. A 3.0.3 é madura e tem o build UMD num arquivo só.
