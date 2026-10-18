<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### 📦 Detetar, instalar e atualizar manualmente todo o ecossistema HYDRA-UMC

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only CLI core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
</p>

> **Modo visual de desktop:** a interface de desktop por defeito é agora
> construída com **Qt Quick / QML** através do runtime gráfico opcional
> `PySide6`. O núcleo do atualizador e o modo `--cli` continuam a usar apenas
> a biblioteca padrão, para uma CM5 sem ecrã.
>
> **Arranque no Windows e evidência da atualização:** faça duplo clique em
> `run-gui.vbs` (ou use o `run.bat` simples) para o cliente de desktop sem
> consola. O seu painel de Atualização segura mostra pontos de controlo reais
> de Verificação prévia, Atualização da origem, Validação do manifesto,
> Build-test e Concluído, com a evidência dos comandos capturada;
> `run.bat --cli ...` mantém deliberadamente um terminal para diagnóstico.
> A instalação só está disponível para uma cópia em falta; a atualização só
> quando o GitHub é mais recente. Durante uma ação aprovada, os pontos de
> controlo substituem os controlos do projeto selecionado e selecionar outro
> projeto restaura-os.
> **Instalar todos os em falta** e **Atualizar todos os desatualizados** são
> ações em lote sequenciais, confirmadas em separado, construídas a partir do
> mesmo estado em direto e do mesmo caminho de segurança.

**Verificação de honestidade - o que realmente funciona hoje:** a lógica de descoberta/versões de todo o ecossistema (`registry.py`, `project_manifest.py`, `ecosystem_catalog.py`, `version_parse.py`, `detect.py`), o cliente real de conteúdo bruto do GitHub com repetição/backoff (`github_client.py`) e a lógica de clonar-preparar-verificar-promover do pipeline de instalação/atualização (`install.py`) são reais e testados - 140 testes a passar (`pytest tests/`), incluindo um servidor HTTP de fixture que prova o isolamento entre catálogo malformado e projeto malformado e idas e voltas reais de git clone/build em diretorias temporárias. `--cli status`/`install`/`update` exercitam este mesmo núcleo testado de ponta a ponta contra o anfitrião real e em direto de conteúdo bruto do GitHub (não uma simulação) sempre que os executa de facto. A GUI de desktop Qt Quick (`qt_gui.py`, `qml/Main.qml`) e o recurso Tkinter legado (`gui.py`) ligam esse mesmo núcleo testado a uma janela real e foram executados em cópias reais do ecossistema, mas nenhum tem teste automático próprio - não existe `test_gui.py`/`test_qt_gui.py`, já que não se tenta conduzir um ciclo de eventos Qt/Tk real. A cobertura de 8 idiomas do `i18n.py` é imposta por teste (`test_i18n.py`), mas apenas quanto à paridade de chaves e de `{marcadores}` entre idiomas, não quanto à qualidade da tradução. Consulte o `CHANGELOG.md` para saber exatamente o que já foi entregue.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado. Ainda não existe um caminho de E-STOP por hardware, nem limites ou interlocks impostos pelo firmware, nem um comando de movimento verificado; as imagens de firmware são verificadas com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica; TLS e TLS mútuo são opcionais e estão desativados por defeito; nenhuma placa própria foi ainda montada ou testada. Leia a [base de segurança](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.4.8` |
| Maturidade | Estabelecido |
| Testes | 140 (`pytest tests/`) |
| Tecnologia | Python 3.10+ / PySide6 / Qt Quick (QML) / Tkinter (legacy fallback) / Git / GitHub raw content |
| Destino | O PC de quem o usa |
| Em hardware real | Não aplicável: nada aqui corre em hardware |

## 1. 🛠️ VISÃO TÉCNICA GERAL

O HYDRA-UMC-UPDATER é uma pequena ferramenta - GUI com janela por defeito,
CLI completa com `--cli` - pensada para correr na própria CM5 real ou numa
máquina Windows/Linux/macOS de um programador (qualquer espaço de trabalho
obtido da mesma forma) que responde a três perguntas para cada outro projeto
real que descobre através do `hydra-umc.project.json` de cada cópia irmã - o
número em si nunca é codificado aqui, já que cresce com o ecossistema:

1. **O que está realmente instalado aqui, e em que versão?**
2. **Qual é a versão mais recente publicada no GitHub?**
3. **Se o GitHub for mais recente, deixe-me escolher um projeto ou um lote sequencial confirmado.**

Este último ponto é deliberado e inegociável: esta ferramenta nunca altera um
projeto por sua própria iniciativa. Uma ação sobre um projeto selecionado
exige sempre uma confirmação explícita. A GUI pode também oferecer **Instalar
todos os em falta** ou **Atualizar todos os desatualizados**; cada uma é um
lote sequencial confirmado em separado, cujos projetos seguem as mesmas
portas de manifesto, versão e segurança. Uma célula de controlo de robôs
nunca deve atualizar-se automaticamente de um dia para o outro sem que uma
pessoa aprove a ação exata.

Nem todos os projetos descobertos pertencem à própria CM5 - alguns são ferramentas que um programador executa a partir do seu próprio PC (o firmware é compilado e gravado A PARTIR de um posto de trabalho, não compilado NA célula) ou aplicações instaladas num telemóvel/relógio. O manifesto de cada projeto regista qual é o caso (ver secção 3) e a tabela de projetos da GUI pode filtrar por ele - por omissão são mostrados todos os projetos, pelo que nem o próprio atualizador nem o SDK ficam escondidos.

Exemplo ilustrativo (o número exato de projetos e todos os números de versão
abaixo são inventados para dar a forma da saída, não uma execução real
capturada - o número real é o que o `registry.py` descobrir hoje, nunca um
número fixo escrito neste documento):

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
PROJECT           MATURITY     ROLE      STACK       LOCAL     GITHUB    STATE
-----------------------------------------------------------------------------
HYDRA-UMC         functional   firmware  firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER  functional   service   node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO  functional   client    node        0.0.8     0.1.3     OUTDATED
...
59/59 installed, 2 outdated
Run `hydra-umc-updater update <project>` to update one by hand - never automatic, see this tool's own README.

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Updated /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER to v0.0.9 (commit 1a2b3c4d5e6f) after a verified build; previous installation kept at /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER.backup-9f3c2d1a
```

Executar `hydra-umc-updater` sem argumentos (ou fazer duplo clique) abre antes
a mesma informação numa superfície de controlo de desktop escura: um painel
**Ecossistema local** com métricas em direto de descoberta/instalação/
atualização, uma árvore **Registo de projetos** guiada por manifesto e um
painel de **Atualização segura** para o projeto selecionado. A disposição torna
visíveis as proteções reais: descoberta por manifesto, uma única ação
explícita sobre um projeto, confirmação manual, compilação opcional e um
rasto de atividade no ecrã; a evidência completa dos comandos continua a ser
escrita no terminal de arranque.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="HYDRA-UMC-UPDATER real desktop overview" width="100%">
</p>

## 2. 🔄 COMO FUNCIONA REALMENTE UMA VERIFICAÇÃO/ATUALIZAÇÃO

- **Fonte da versão**: a convenção de «odómetro» com subida automática deste
  ecossistema (cada compilação real incrementa um número de versão que vive
  NUM ficheiro de código - `pyproject.toml`, `Cargo.toml`, `version.go`,
  `package.json`, `version.properties`, `pubspec.yaml` ou um `#define` de
  firmware, consoante a stack do projeto) nunca criou uma etiqueta git nem uma
  Release do GitHub para essa subida. Por isso esta ferramenta lê o MESMO
  ficheiro que o `bump_version.py`/script de compilação de cada projeto já
  escreve, diretamente do ramo por defeito do repositório através do anfitrião
  de conteúdo bruto do GitHub - não a API de Releases, que reportaria cada
  projeto como sem qualquer release.
- **Deteção local**: para cada projeto descoberto, verifica se existe uma
  diretoria com esse nome exato sob a raiz do espaço de trabalho (a disposição
  padrão do ecossistema - cada projeto como diretoria irmã, exatamente o que o
  `build-frontend.sh`/a descoberta do próprio HYDRA-UMC-SUITE já assumem) e,
  se sim, lê a SUA própria cópia local desse mesmo ficheiro de versão.
- **Uma única implementação de análise** (`version_parse.py`) é partilhada
  entre a leitura local e a obtenção do GitHub, pelo que uma cópia local e uma
  obtenção do GitHub nunca são interpretadas por duas regex que derivam de
  forma independente.
- **Instalar/atualizar**: o `git clone` (instalação) compila depois como um
  passo separado. Atualizar uma cópia EXISTENTE é, em vez disso, atómico por
  verificação: o candidato é clonado, fundido em fast-forward (nunca um
  reset forçado, para que edições locais reais falhem de forma ruidosa em vez
  de serem descartadas) e compilado/verificado primeiro num clone de staging
  totalmente independente - a instalação em uso só é tocada (através de duas
  mudanças de nome de diretoria consecutivas, ficando a instalação anterior
  em `<name>.backup-xxxxxxxx`, não apagada) se essa compilação de staging realmente
  tiver êxito. Uma falha de compilação, uma cópia divergente/suja, uma falha
  ou um disco cheio em qualquer ponto antes dessa promoção final deixam a
  instalação anterior completamente intacta e ainda operativa - ver o
  docstring do próprio `clone_or_pull` do `install.py`. O remoto git do
  próprio clone de staging é restaurado para o upstream real do GitHub logo
  depois de criado (um clone local simples apontá-lo-ia, de outro modo, para o
  caminho da instalação antiga, pondo fim em silêncio a todas as
  atualizações futuras depois de promovido), e os dados locais reais da
  cópia instalada (tudo o que o git considera não rastreado ou ignorado -
  `data/settings.json` e semelhantes, excluindo artefactos de compilação
  regeneráveis) são levados para o clone de staging antes de compilar, para
  que o estado operacional real de um projeto sobreviva a uma atualização em
  vez de ficar encalhado na cópia `.backup` guardada.
  De qualquer forma, isto executa o `build-test.sh`/`build-test.bat` do
  próprio projeto (a verificação que não sobe versões - ver a secção 3) que
  ele realmente tiver. Esta ferramenta nunca reimplementa os passos de
  compilação de um projeto.
- **Porta de assinatura opcional**: o script `build-test` de um candidato é
  código que o próprio candidato traz consigo e que é executado aqui antes de
  alguma coisa ter provado que o commit é do mantenedor. Com
  `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1` o atualizador executa primeiro o
  `git verify-commit` sobre o candidato aceite no clone de staging e, se o
  commit não tiver uma assinatura em que esta máquina confie (uma chave gpg no
  porta-chaves, ou um signatário ssh em `gpg.ssh.allowedSignersFile`), pára
  aí: nada é compilado nem executado, e a instalação em uso fica intacta.
  Desativada por defeito, porque exige na máquina um porta-chaves que confie
  na chave do mantenedor.

- **Mais redes de segurança**: uma só instalação ou atualização de cada vez por área de trabalho (ficheiro de bloqueio); limite de tempo em cada comando git e em cada build-test, sem nunca pedir credenciais; um erro inesperado é um resultado falhado na janela e no ficheiro de evidências, nunca uma janela presa em "a trabalhar"; a barreira de assinatura abrange também uma primeira instalação e pode ser ativada nas definições guardadas (`require_signed_commits`; um ficheiro de definições ilegível conta como ativada), com um aviso vermelho na janela enquanto estiver desativada; um commit local que impede o avanço rápido é indicado na recusa; uma instalação nova cuja compilação falha é removida de novo; as pastas de staging antigas são limpas no início de uma execução, e `--cli prune-backups [--keep N] [--dry-run]` remove as pastas `<nome>.backup-xxxxxxxx` antigas apenas a pedido.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="HYDRA-UMC-UPDATER installation or update checkpoints in progress" width="100%">
</p>

## 3. 🧱 ARQUITETURA E DECISÕES DE DESIGN

- **GUI Qt Quick por defeito, `--cli` para sem cabeça.** O `main.py` verifica
  o `--cli` antes de importar o runtime opcional PySide6, pelo que o modo CLI
  funciona numa CM5 genuinamente sem cabeça, sem ecrã nem dependência de
  desktop. A invocação simples arranca o cliente QML onde o runtime estiver
  instalado; o shell Tkinter mais antigo permanece apenas como recurso
  temporário de compatibilidade.
- **A GUI com janela é real e multilingue em 8 idiomas (`i18n.py`) - o `--cli` deliberadamente não é.** Cada widget real volta a etiquetar-se em direto a partir de uma `Combobox` de idioma (en/es/fr/it/de/zh/ja/pt, os mesmos 8 que o painel público e cada README distribuem), detetado a partir de uma preferência guardada ou do próprio locale do SO. Os nomes de projetos/famílias e o texto real de `notes`/`tech` de cada projeto ficam por traduzir - o `registry.py` é a sua fonte única de verdade, e 8 cópias paralelas de documentação de engenharia real deixariam de o ser. A saída do `--cli` fica só em inglês de propósito: destina-se a ser usada em scripts/encadeada, onde um texto estável e fácil de procurar importa mais do que a localização.
- **O `deploy` é uma classificação, não uma restrição.** Tratar cada projeto
  descoberto como «algo que pertence à CM5» estava errado - os repositórios de
  firmware compilam-se e gravam-se A PARTIR de um PC (a CM5 só precisa do
  binário resultante por CAN-OTA, nunca do código-fonte deste repositório), e
  várias ferramentas (URTC-FLASHER, HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...)
  destinam-se a correr na estação de trabalho do operador, não dentro da
  própria célula. O campo `deploy` do `registry.py` («cm5» / «user-pc» /
  «mobile» / «wearable» / «dev-server») regista isso, e o filtro da GUI usa-o
  como ponto de partida sensato - nunca uma restrição rígida, já que esta
  mesma ferramenta se destina também a correr no PC de um programador, onde
  todo o projeto descoberto é legítimo de inspecionar.
- **Esta ferramenta não tem lógica de compilação por stack.** O ecossistema abrange 7 toolchains (Python, Rust, Go, Node/TS, Android/Kotlin, Flutter, firmware ARM). Reimplementar `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` / etc. AQUI criaria um segundo lugar que afirma saber compilar cada projeto, garantidamente a divergir das verificações reais (e já corretas) do próprio projeto. Em vez disso, o `install.py` executa apenas o `build-test.sh` não versionante do próprio projeto (`build-test.bat` no Windows), que verifica sem incrementar nenhuma versão; um projeto que não o tenha é recusado com "No non-versioning build-test.sh/.bat found".
- **Conteúdo bruto do GitHub, não a API de Releases.** Ver a secção 2 acima -
  a convenção de versionamento deste ecossistema nunca cria uma
  etiqueta/release, pelo que a API de Releases estaria ativamente errada
  aqui, e não apenas menos conveniente.
- **Uma falha de rede transitória recebe uma repetição real; uma resposta definitiva nunca.** Cada pedido real ao GitHub (o `_urlopen_with_retries` do `github_client.py`) repete até 3 vezes com backoff, mas só para uma ligação que nunca obteve resposta (DNS/timeout/reset). Um estado HTTP real que o GitHub realmente devolveu - 404, 403, 500 - nunca é repetido: o GitHub já respondeu, e martelá-lo outra vez apenas gastaria mais do limite de pedidos pelo mesmo resultado.
- **Um catálogo remoto malformado falha de forma ruidosa; um projeto malformado não.** Se a própria listagem de repositórios do GitHub for inalcançável ou impossível de analisar, o `discover_remote_projects()` levanta erro e a ponte de desktop recorre a uma lista de projetos descoberta localmente em vez de mostrar uma análise quebrada/vazia. O manifesto malformado de um único repositório, pelo contrário, é isolado na lista `errors` dessa análise e nunca aborta a descoberta do resto - um teste real com servidor de fixture (`tests/test_github_client.py`) prova ambos os caminhos.
- **As ações da CLI continuam explícitas; os lotes da GUI continuam confirmados.** Os comandos `install`/`update` da CLI recebem o nome de um projeto. A GUI de desktop pode também executar **Instalar todos os em falta** ou **Atualizar todos os desatualizados**, mas só depois de uma confirmação separada e em sequência através das mesmas portas de segurança. Não existe nenhuma atualização automática sem supervisão.
- **Só biblioteca padrão.** `urllib` para as obtenções do GitHub
  (`github_client.py`), `subprocess` para as chamadas ao git/scripts de
  compilação (`install.py`), nada mais - uma ferramenta responsável por manter
  sãs as dependências de todos os OUTROS projetos permanecer ela própria sem
  dependências é deliberado.
- **Simplificação conhecida**: o HYDRA-UMC é um repositório de firmware real
  de vários componentes (6 binários com versão independente - ver o seu
  `VERSION_CHECKLIST.txt`/`build_firmware.sh`) sem um único número de versão
  «o». O `registry.py` acompanha UM componente representativo por
  repositório - suficientemente bom para responder a «este repositório está
  mais ou menos atualizado», não um substituto do `firmware_manifest.json` do
  próprio `build_firmware.sh` para uma gravação real.

## 📂 ESTRUTURA DE DIRETORIAS

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py         # ProjectEntry - sem catálogo estático; construído na descoberta a partir do manifesto de cada repositório
│   ├── project_manifest.py # Lê/valida um hydra-umc.project.json pertencente ao repositório
│   ├── ecosystem_catalog.py # Analisador do catálogo público de descoberta do ecossistema JuanenRac
│   ├── version_parse.py   # UMA só implementação de extração por regex, local+GitHub
│   ├── detect.py          # Analisa uma raiz de espaço de trabalho para ver o que está instalado
│   ├── github_client.py   # Obtenção concorrente de conteúdo bruto + repetição/backoff real para erros de rede transitórios
│   ├── install.py         # git clone/pull + delegação no script de compilação do próprio projeto
│   ├── i18n.py             # Traduções reais e completas da GUI (8 idiomas)
│   ├── qt_gui.py           # Ponte Qt Quick sobre os serviços reais de descoberta/atualização
│   ├── qml/Main.qml        # Shell de desktop com tema: controlos, pontos de controlo e Acerca de
│   ├── gui.py              # Recurso Tkinter legado se o PySide6 não estiver disponível
│   └── main.py             # Despacho: GUI por defeito, --cli para status/install/update
├── tests/                  # Testes reais: github_client, i18n, install, project_manifest, registry
├── docs/
│   ├── CLI_REFERENCE.md     # Referência de comandos
│   └── QML_DESKTOP_GUI.md   # Arquitetura da GUI Qt Quick
├── images/                 # Multimédia, ícones da aplicação e capturas da interface
├── tools/
│   ├── build_test.py        # Verificação de compilação sem alterar versões
│   ├── ci_validate.py       # Validação de manifesto/CHANGELOG/docs usada pelo CI
│   ├── generate_app_icon.py # Renderiza o SVG público do HYDRA-UMC no ícone consumido pelo Windows
│   ├── migrate_project_manifests.py  # Audita um espaço de trabalho depois da migração única de manifestos
│   └── validate_project_manifests.py # Valida os manifestos pertencentes aos repositórios + versões nativas de compilação
├── .env.example            # Modelo de variáveis de ambiente
├── build.sh / build.bat    # venv + instalação editável + verificação de compilação
├── run.sh / run.bat        # GUI por defeito / ponto de entrada da CLI
├── run-gui.vbs             # Lançador gráfico para Windows sem janela de consola
├── bump_version.py         # Subida de versão em odómetro de todo o ecossistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Sincroniza a versão do hydra-umc.project.json com a nativa (--sync)
```

## ⚙️ GUIA DE COMPILAÇÃO E EXECUÇÃO

```bash
chmod +x build.sh   # uma única vez
./build.sh          # cria o .venv, pip install -e ., verifica a compilação de tudo
./run.sh                              # GUI com janela (por defeito)
./run.sh --cli status                 # o que está instalado, versão local vs. GitHub
./run.sh --cli status --offline       # o mesmo, saltando a verificação no GitHub
./run.sh --cli install <PROJECT-NAME> # clona + compila um projeto ainda não instalado
./run.sh --cli update  <PROJECT-NAME> # obtém + recompila um projeto já instalado
./run.sh --cli prune-backups --keep 2  # remove as pastas <nome>.backup-xxxxxxxx antigas (mantém as 2 mais recentes de cada)
```

No Windows: `build.bat` e depois `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli install <name>` / `run.bat --cli update <name>`.

A GUI preferida precisa do runtime Qt opcional (`pip install -e ".[gui]"`; o
`build.bat`/`build.sh` já o instalam). O `--cli` não tem dependência de GUI e é
o ponto de entrada correto para uma CM5 sem cabeça. Se o Qt não estiver
disponível, o shell Tkinter mais antigo é apenas um recurso de compatibilidade.

**Resolução de problemas**

- O `status` mostra `?` na versão local ou do GitHub de um projeto: o seu ficheiro de versão existe, mas a entrada `native_version` do `hydra-umc.project.json` desse projeto já não corresponde ao sítio onde a versão realmente está - corrija o manifesto desse projeto.
- O `status` mostra `-` para o GitHub sem erro visível: execute o `status`
  (sem `--offline`) - o `-` só aparece quando a verificação no GitHub foi
  totalmente saltada.
- O `install`/`update` falha com "No non-versioning build-test.sh/.bat found": esse projeto ainda não tem `build-test.sh`/`build-test.bat` - acrescente-lhe o padrão do ecossistema (tem de verificar sem aumentar nenhuma versão).
- O `git merge --ff-only failed`: a cópia local tem um histórico divergente ou commits locais (a mensagem indica-os) - mova-os ou descarte-os (`git status`/`git log` na pasta desse projeto) antes de repetir o `update`. As alterações por confirmar em ficheiros seguidos são recusadas logo de início. Esta ferramenta nunca força o reset de uma cópia.

## 🚀 ROTEIRO

- Um executável autónomo da GUI empacotado (PyInstaller, em linha com a
  convenção `build_exe.bat`/`.sh` do próprio HYDRA-UMC-SUITE) para uma
  instalação com duplo clique sem qualquer passo de `pip`/venv - a GUI de hoje
  ainda precisa primeiro do `./build.sh`, tal como a CLI.
- Verificação prévia opcional de dependências por projeto (reportar cadeias
  de ferramentas em falta - sem Rust/Go/Android SDK/Flutter instalados - antes
  de um `install` falhar a meio).
- Acompanhamento por componente para o firmware de vários binários do próprio
  HYDRA-UMC (ver a «simplificação conhecida» na secção 3), quando houver uma
  necessidade real para lá do único componente representativo que hoje se
  acompanha.

---

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Diretamente relacionados**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame para desktop (PySide6) para vários servidores ao mesmo tempo, empacotado como executável independente — outra ferramenta Python autónoma pensada para correr ao lado do controlador da célula, a irmã mais próxima em papel (um utilitário focado do lado da CM5, não parte do caminho de controlo do robô em si).
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — depende deste projeto como biblioteca real para a sua própria descoberta do ecossistema no GitHub ao construir uma imagem nova da CM5, em vez de uma segunda implementação a derivar de forma independente.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).


*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Nó de IA cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integração do pipeline cognitivo do Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé para o relógio limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

*Orquestração e enxame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integração com um contrato real de relatório de saúde gRPC/Protobuf e uma máquina de estados de missões.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integração do motor de gémeo digital, com um contrato real de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedural real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integração que retransmite para protocolos industriais, com uma camada real de lista de comandos permitidos e contrapressão.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão de cliente real do protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML MTConnect `/probe` e `/current` reais com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).

---

## 📚 Documentação e comunidade

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando `--cli`, saída real capturada de uma execução instalada e o contrato dos códigos de saída.
- **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — como o cliente de desktop Qt Quick/QML está estruturado e como continua a ser uma superfície de controlo real sobre o mesmo back-end que o `--cli` usa, e não uma segunda implementação.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pilha tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como comunicar uma vulnerabilidade e as áreas de segurança em que este projeto se concentra.
- **[SUPPORT.md](SUPPORT.md)** — onde fazer perguntas e comunicar erros.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA

GPL-3.0 (software) / CC BY-SA 4.0 (documentação) - veja [LICENSE.md](LICENSE.md).

