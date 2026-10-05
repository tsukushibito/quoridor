# Sigmaモデル出所・規約/特徴/Action参照fixture

Beads issue / 実験ID / 試行 / 契約版 / 報告元スレッド:
目標 quoridor-4lc、子 quoridor-4lc.6 / SIGMA-PARITY-PLAN / 1 / 1 / hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418。
報告先 coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。目標契約 [版1](../design/ai-sigma-research-goal.md)、[子契約](../design/ai-sigma-contract-hypothesis-parity.md)を継承する。

## 判別した問い / 仮説

固定SigmaのWebルールから、後続Rust変換/規約adapterの診断に使えるfixtureを生成できるという仮説は、**参照側の生成可能性の範囲で支持**。28件を保存し、20件は合法prefixのreplay、8件は明記したsynthetic context。Rustとの一致、NN出力一致、棋力到達は未試験。

統括が選んだ比較専用規約A（3回目反復手禁止/200 total ply/goal優先/合法手なしdrawを内部探索まで揃える）に向けた入力資料。製品standard-2p-v1の変更はない。初期参照のWeb NN-MCTSを保持する判断、および「Rust-native対固定Sigma-WebのローカルCPU対局」という比較名を継承し、C++ native成績へ読み替えない。

## 実施内容 / コード・差分・環境・入力の参照

開始2026-09-30 18:23 UTC頃、当役30分枠の停止期限は18:53 UTC頃、最後3分を提出に確保。場所 /workspaces/quoridor/.worktree/ai-sigma、branch codex/ai-sigma、HEAD 1482df8da6dd91c95db211aeaa914af775b2bc76。未コミット基準と他担当の進行中変更は保持。ready、目標/.2/.6のshowでpauseなしを確認。統括による.2調査再現性の受入れとcritic .4の独立照合を根拠に、自分所有.2だけ追記/closeし、.6だけclaimした。目標や他者issueは変更していない。

AGENTS/目標全文/common/role、team design、AI設計/storage policy/handoffは前契約から継承し、今回契約と入力を再確認。初期報告SHA256 8b4938e6bd1774a5313f808f8c5c0de3a67618c00cc63a4cd6efd404fde9a032、critic報告607618c36454a18bb4f9ba2ec954b074a58e82214648e7991f5030b8400c74cf、steward報告52b8d53b07cf725f1b53510048abfd0c4d4d13b03461f0c814e16695cb4ff5a5と一致。その他の入力・lockfile・launch.jsonの実hashは成果物 local-inputs.json。

唯一のソースadapterは、固定game.jsをNode VMで評価した後に、State/actionToIndex/vertPolicyPermutation/ALL_PAWN_DIRECTIONSを外へ渡す文字列suffix。原文snapshotは変更せず、adapter文字列をfixtureにも保存。AI探索・Rust・共有docs・registry・主checkoutは編集していない。生成・取得scriptと原文snapshotは許可された以下の範囲のみ。

成果物ディレクトリ: [.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN](../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/)。
主ファイル: [fixtures.json](../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json)、[generate.mjs](../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/generate.mjs)、[schema.json](../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/schema.json)、[model-manifest.json](../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/model-manifest.json)、[artifact-manifest.json](../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/artifact-manifest.json)。

## 問い1: モデル出所と配布条件

固定commit **751186344fc52ad0c29bc65922e62c6fa915f006**の原文11ファイル315,881 bytesを取得・保存。binary/全体cloneは0件。固定treeのlicense/manifest/pretrain/copyrightという名前の限定検索、およびexport_onnx.pyの直近6commit metadataをsource-manifest.jsonへ保存した。この限定調査で追加のモデル固有licenseや第三者pretrained由来を示す明示資料は見つからなかった。網羅的不存在や、モデルの権利関係をすべて確認したという意味ではない。

[root LICENSE](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/LICENSE)はMIT、Copyright 2026 Bartosz Pokora、実SHA256 b5e277822da3c9eb54eb04e9ee3c4f93bfeb769c829d5d0f70c99835a2f6733d。原文noticeをsnapshotに保持。READMEも同LICENSEへ参照する。追加条件の証拠を見つけなかったことから、モデルの採用・製品再配布の包括的許可を断定しない。

[export source](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/export_onnx.py#L24) は9×9既定ONNXの出所を runs/models_9x9_pcr/best.pt とし、PCR lineageはscratchのcycle160からのfork、公開headは250と説明する。[固定commitの変更履歴](https://github.com/bartolomeo3000/SigmaQuoridor/commit/751186344fc52ad0c29bc65922e62c6fa915f006)にもPCR 250へWeb配布モデルを切り替えた旨がある。作者の対戦数字は今回再現していない。過去scratch321を現在固定ONNXの出所と扱わない。

| 固定モデルpath/URL | API tree size | Git blob SHA1 |
| --- | ---: | --- |
| [docs/models_9x9/best.onnx](https://raw.githubusercontent.com/bartolomeo3000/SigmaQuoridor/751186344fc52ad0c29bc65922e62c6fa915f006/docs/models_9x9/best.onnx) | 11,663,428 bytes | f23802a83dc9054b5227da74b3771698854535f0 |
| [runs/models_9x9_pcr/best.pt](https://raw.githubusercontent.com/bartolomeo3000/SigmaQuoridor/751186344fc52ad0c29bc65922e62c6fa915f006/runs/models_9x9_pcr/best.pt) | 11,718,115 bytes | eed997da36e5bf758cbc46080fcca13b47bb4f87 |

この表はmetadataのみで、URLのbinaryを取得していない。実SHA256/graph/dtype/PT↔ONNX numerical parityは未確認。export scriptが宣言するopset17・input/output名・埋込weightsも、実binary検査と区別する。

[READMEのfrom-scratch説明](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/README.md#L135)とrandom init/resumeを備えた[train.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/train.py#L1467)は、project内の学習由来という説明を支持する。ただしcheckpoint chainをweights/dataで検証していない。KataGo風構造への言及は第三者重みを利用した証拠ではない。[head redesign notes](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/markdown_notes/HEAD_REDESIGN_PLAN.md#L17)には別のheads lineageへのproject内warm-startがあるが、その記録をPCR 250の完全provenanceへ流用しない。7×7 supervised exportも9×9 PCRと混同しない。

**ローカル研究比較用取得**は次契約で資源を配分し、固定URL/size/blobとの照合、binary SHA256、実graph、数値、出所条件を検証する段階。**製品再配布**はその確認・notice/manifest整備と採用判断が別途必要。本契約でモデル取得も再配布も実施/承認していない。未確定情報を理由に許可されたtext調査を止めず、断定は避けて記録した。

## 問い2: 参照fixtureの観測

全28件は**変換/規約診断専用**。正式棋力holdoutに転用しない。固定生成seed20261001は20壁の合法prefix選択に使用し、temperatureや棋力を測るseedではない。期待値は固定参照JSを実行して得たもので、LLMによる手書き数値を正本にしていない。

各fixtureに保存した情報: 合法prefix、分類とsynthetic変更理由、盤面/P1/P2/壁anchor/残壁/手番/total ply、Rust cell/anchor番号、history key文字列と全position-count、全合法direction/壁手、着地点、Sigma136↔Rust209、648個Float32値をJSON数値化した特徴、136個P2 permutation、canonical policy indices、禁止手probe、terminal/result。terminal side_to_move_valueは勝敗からadapterが計算する規約値で、NN出力ではない。byte単位の期待値hashはfixtures.json全体に対して記録する。

| 範囲 | 保存case |
| --- | --- |
| 初期・P2・非対称特徴 | initial-p1/p2、asym-h-p2、asym-hv-p1/p2 |
| jump/遮断 | straight-jump-p2、behind-wall-diagonal-p2、adjacent-wall-blocked、board-edge-diagonal-p2 |
| 壁条件 | asym caseのH/V overlap/crossing probes、reachability-closure-forbidden、all-walls-spent、one-wall-in-hand |
| 反復・履歴 | first-return、initial-count2、third-return、overlay-count2、sibling-a/b/root-restored、synthetic-root-double-count |
| 境界・終局 | synthetic-total-ply198/199/200、goal-before-last-step、synthetic-ply198-before-goal、goal-win-legal-replay、synthetic-goal-at200、synthetic-no-legal-move-draw |

20件のlegal-replayは、初期9×9/各10壁から**getLegalActions()集合のmembership**を各手でassertした。terminal後のprefix継続も拒否する。source next()は呼び出しただけではこの制約を守らないので、次実装でunchecked transitionをそのまま合法性の根拠にしない。

8件のsyntheticはhistory3件/total ply5件。overlay merged counts、二重root countのerror-injection、合法手なしdrawの強制counts、198/199/200境界を短いprefixから生成するために使った。prefixそのものは合法だが、変更後contextは実際にそこまで到達する合法replayという主張ではない。200手までの完全合法棋譜や履歴をこの調査で探し切っていない。synthetic-total-ply199にはcurrent key count=0の人工的contextもあり、整合する実対局履歴のfixtureとして使わない。

実行で確認した重要観測:
- 3回目の初期局面へ戻す手はgetLegalActions()で除外されるが、isActionLegal()はtrueを返す。後者は反復規約の代用にならない。reference fixtureではこの差をそのまま保存。
- P2直線jumpの着地は[4,3]。後壁/盤端のcaseでは直線手がなく斜め手がある。
- V(3,0),V(4,0)の合法prefixからH(3,1)を試すと、到達遮断のため集合membershipもisActionLegalもfalse。
- siblingをそれぞれsource copy/nextで生成してもbase historyが変わらないことをassert。overlayをbaseへ合算したsyntheticでは戻り手が除外される。
- synthetic-goal-at200はwinner=2、raw isDrawn=trueだが、goal優先effective resultはP2 win、手番側terminal value=-1。raw関数と優先した結果を混同しない。
- **終局のgetLegalActions()自体は空とは限らない**（保存した合法goal caseでもraw手集合が残る）。fixtureのlegal_actionsはraw参照関数の出力。adapterはwinner/terminalを先に判定し、終局から展開しない。これはRustの終局maskと素朴に比較して不一致とする前に区別すべき点。

根拠原文: [game.js](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/game.js#L296)、[Web NN-MCTSのterminal処理](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/mcts_worker.js#L272)。今回はNN-MCTS探索そのものを実行していない。

### 変換と検査の範囲

全caseで合法写像のinjectivityをassert。pawnのRust着地点からown位置との差を取り、2マス直線jumpを元の直交方向へ戻す逆変換、およびH/V offsetの逆変換でroundtripをassertした。P2 permutationは136要素の自己逆写像。特徴はsource Float32Arrayを取り、648値すべてfiniteをassert。schema構造/分類/prefix lengthとtotal plyの一致（legal-replayだけ）も別Python読取で確認した。外部JSON schema検証器を導入・実行したわけではない。

Sigma H8+a→Rust81+a、V72+a→145+a、a=y×8+x。P2のcell y→8-y、anchor/H segment y→7-y、V segment y→8-yをconversion-contract.jsonに分離記録。H plane最終行0、残壁/10、wall-only BFS距離/80、手番側channel順。wall anchorビットをsegment planeへ直接置かない。sourceのkeyは駒位置/side parity/lexicographically sorted H/V anchor集合の文字列で、wall countsを別途混入していない。盤面だけでhistory/countを復元できると考えない。

この参照側の写像assertは、Rust実装のparity検証ではない。次担当はraw state/合法prefixを入力してRust研究contextを構築し、全合法集合・遷移・特徴/終端を比較する。policy logits、legal priors、valueのfinite/range/数値誤差、backup/cancel/deadlineは次契約のgateに残る。root不正手拒否だけでは内部探索parityを満たさない。

## 再現コマンド / 独立再実行の状況

依存追加なし、既存Node v24.21.0/Python標準ライブラリ。Linux/WSL2 x86_64、同worktree、taskset CPU0。Node heap上限128MiB、短いtimeout。モデル・Rust build・対戦・正式速度測定・GPU・学習0。

取得scriptは各raw text responseを最大250,000 bytes、socket timeout10秒で制限し、固定tree metadata/API export履歴だけを取得。モデルURLを読まず、11原文hashを保存。fetch PID633925、exit0、affinity[0]、peak RSS22,076KiB。

```bash
timeout 45s taskset -c 0 env PYTHONDONTWRITEBYTECODE=1 python3 .artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fetch_sources.py
timeout 35s taskset -c 0 env PYTHONDONTWRITEBYTECODE=1 python3 .artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/reexecute.py
```

取得済みsnapshotだけで生成し直すなら後者のみ。reexecute.pyは各Node childに15秒timeout、終了/kill待ち、PID/exit/time/RSS/CPU/hashを記録。2つの別Nodeプロセス PID637301/637309、両方exit0、affinity[0]で、**同一出力hash**を得た。最終fixtureの独立「役」による再実行はまだない。これは自己再生成の決定性確認であり、criticによる受入れとは区別する。

| artifact | SHA256 |
| --- | --- |
| generate.mjs | de9b60f531113cc5c92911a6988a8c255de467c3e7be6dcbfb6d68de88aaef44 |
| inputs.json | 1c3a0040d7eab9aba4050bc476a4315bce8062142a28db79cb2899cfe404f038 |
| schema.json | 45b610e7c73667805f6eef5d81be62999f87e23ec13326731ff07a0fa094ee1a |
| fixtures.json（1,325,825 bytes） | 206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb |
| source-manifest.json | fb7bbc4658f52e6a5d34c8e2c7bbebf6fbad3fd52b93300b66c0f78353a3dec2 |
| model-manifest.json | 07b29a65ceacabdac2981d12736a2d28c26a265bd2604a7f2b8c9de80290c604 |
| artifact-manifest.json | 16b03455e7e6822566b3d7fe112b375dba8295070f5ab07ebd61af83542762da |

原文game.js実SHA256 dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5を生成前にassert。全30ファイルのpath/size/hashとその他script/log/source hashはartifact-manifest.json。manifest自身のhashは上表で固定。hashに関わる生成物を手編集していない。

## 支持する結論 / 支持しない結論 / 未確認

支持: 固定sourceから28件を再生成でき、2独立processのbytesが一致した。モデルのexport先/出所の宣言、PCR切替履歴、root MIT text/hash、限定検索結果は保存済み。
不支持/未確認: 重みchainの完全provenance、モデル追加条件の網羅的不存在、製品採用・再配布の包括的許可、binary実SHA256/graph、PT/ONNX/Rust数値一致、Rust規約parity、棋力と速度向上。
未完了case: 完全合法200手replay、実対局から合法手なしdrawへ至る履歴、実検索stackのoverlay/push-pop/兄弟復帰はRust未実行。対応syntheticがあることを完了扱いしない。全体ネット配信版や同PC比較の実行条件の確認も別課題。

## 実装失敗・実験不成立・negative resultの区別

初回generatorはduplicate root識別子のSyntaxErrorでexit1（参照実行前）。次回はaction objectのJSON property順に依存した補助比較でmembership assertが失敗、field比較へ修正した（referenceとRustの不一致ではない）。generate-attempt1/2.logを保持。27件成功後、到達遮断caseを追加して28件にし、最終scriptをhash固定した。これらはfixture補助実装の失敗・修正であり、研究のnegative resultやSigmaバグの再現ではない。

参照出力が異なる際は仮説修正という契約に沿い、反復検査関数の差と終局raw手集合の非空を発見・明記した。生成器は原文を変更して期待に合わせていない。Rust/モデルに関する実験は未実施なので、その成功/失敗を主張しない。

## 書き込み停止 / プロセス・資源の残存

本報告と指定artifact範囲だけを書き、報告保存後に書込み停止。取得・全Node childは終了し、バックグラウンドjobなし。reexecuteのPID/exitはexecution.json、Node自己resourceUsageはrerunログ。全体ホスト/他者processを停止していない。送信直前に目標/自子issueのpauseをshowし、backup sync後に主checkout入口からreportする。自子は統括受入れ待ちin_progress、目標はcloseしない。

保存実績はartifact30files **1,687,831 bytes**＋本報告の実size（提出直前に合算してBeads notesへ記録）。32MiB割当以内。モデル取得0 bytes、clone/依存cache更新/build/GPU/学習/追加エージェント0。
計測された最終2再生成のchild CPU時間合計 **0.150923秒**、peak RSS **75,452KiB**（約73.7MiB）、affinity CPU0。RAM1GiB以内の観測。Node128MiB heap capと短いtimeoutを使用し、OS全体/cgroupのmemory更新はしていない。過去試行と短いread/DB操作を含む総累積CPU秒は未集計、0使用とはしない。正式性能指標ではなくfixture診断の資源記録。
18:48 UTC頃の保存停止で当役約25分、全体残り約6時間30分（締切01:17:58 UTC/JST10:17:58）。全体保存/計算の実績とexperimentの4GiB予約は統括/基盤台帳へ合算する。当役が他者保存量を推測して残枠を消費していない。

## 保持する証拠 / 次の提案

原文snapshots/notice、生成input/script/schema/fixture、manifest、失敗log、PID/exit記録と本報告を保持。削除なし。自己再生成は既存snapshotのみで可能。受入れ前に他役がartifactを変更せず、hashを独立照合することを提案する。

次契約候補はexperimentの規約A研究context/136↔209・8-plane変換へこの診断fixtureを渡し、criticが合法replayとsyntheticを分けてRust内部展開/終端を検証すること。モデル取得を配分する場合は別gateで実bytes hash/graph/PT↔ONNX→Rust parity/出所条件を確認する。通常の研究判断は統括へ提出し、当役は追加実験や委譲を起動していない。報告配送acceptedと、.6の研究受入れを区別する。
