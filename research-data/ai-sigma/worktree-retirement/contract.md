# .worktreeを共有DB・作業中checkout・必要資産へ整理

ユーザーの実行指示に基づく保守作業。親 `quoridor-1d2` はrootが最終受入れ、実作業 `quoridor-1d2.1` は既saved steward。研究frame21の新科学・延長・再開を許可する指示ではない。保守の終了は現在の研究枠と独立し、使用中入力の移行は自然停止・書込停止を確認して行う。

## 到達構成と所有

- `.worktree/.beads-state` と共有アクセスlockを保持する。DBの移動・初期化・直接編集・削除はしない。
- `frame21-search` / `frame21-features` 等の実作業中managed worktreeを保持する。今回の研究writer・jobを中断しない。
- 必要モデル・checkpoint・入力は、同じ永続volume内の `.worktree/assets/` へ分類して移す。現役コードはmain、実験検証データの保存正本はmain Gitの `research-data/ai-sigma/`。assetsに旧source tree一式や再生成cacheを移して温存しない。
- 未使用 `webapp-presentation` / `research-team` / `scheduler` / 未登録 `ai-sigma-frame18-data-learning`、最後に旧 `ai-sigma` を撤去する。未保存情報を特定・保存・復元確認してから、登録worktreeは `scripts/dev/manage_worktree.sh remove` を使う。枝・共有Git履歴は削除しない。
- 実作業ownerはsteward。mainの `research-paths.json`、`scripts/dev` の資産解決に必要な限定変更、storage-policy / ai-research-code / 関係README / 整理報告、`.worktree`の旧5対象とassetsは今回の編集範囲。rootは同pathに並行編集しない。現研究2WT、NNUE・探索のscience source、役/common/registryの定義・モデル設定は対象外。
- mainの通常Git index/commitはcoordinatorの既単一所有を維持し、停止path/hashを引き渡す。worktree撤去に必要なGit操作も同ownerと操作窓を合わせる。coordinatorが統合を完了して所有を解放した後の最終保存はrootへ引き渡せる。無条件reset/clean/add-Aや未検証forceは使わない。

## 必須確認と実施

1. Beads ready/show/担当claimと、各旧対象のstatus・未追跡/ignored資産・branch/HEAD・現在process/cwd/open inputの必要範囲を確認する。rootの先行診断では `research-team` に3変更と未追跡、`scheduler` に未追跡、`ai-sigma` に29変更と未追跡の実験receipt/棋譜等、未登録frame18には5Python fileがある。これをGit保存済みと仮定しない。
2. Gitで再構成できる旧sourceと、Gitで再構成できない必要モデル・入力・未保存変更・観測を区別する。既main commit/圧縮archiveとのSHA/byte一致と復元を確認し、既保存重複は新archiveへ重複保存しない。保存が不足するunique情報は小さな圧縮記録とmanifestへ一度保存する。未保存ファイルを消してcleanにする手順は不可。
3. 266/267/268/coordinatorへ必要な読取対象と移行停止点を通知する。科学中のモデル・入力pathを変えず、先に使用終了済みの旧3WT/未登録dirを整理する。使用中assetはownerの自然stop/関連child wait後に同volumeで移し、SHA/size一致を確認する。source移動でモデル/データ内容を変えない。
4. `research-paths.json` と現役のasset resolver、必要な手順/READMEを新管理先へ更新する。historical原結果・manifestの絶対pathや原SHAを遡及書換えせず、旧path→新assetの対応manifestを保存する。旧worktree名を維持するための互換symlinkや巨大凍結treeを残さない。
5. 未使用build/cache/旧source重複を保存方針に沿って削除し、必要unique資産だけを残す。old `:memory:.ses` があれば既ORT telemetry sidecarとして未使用確認後削除可能。共有依存・DB・モデル・原実験データを無断で削除しない。
6. current codeの資産解決、必要assetのSHA/size、Git復元、worktree登録/lockと残置tree、DB wrapper ready/show、source構文・formatter/必要限定テスト、current保持量を確認する。実NN/学習/GPU/gameによる移行検証は起動しない。

## 実行量と連絡

管理CPU1・RAM1GiB以内、研究の重job中は大読取・圧縮・CPUテストを避け、既ownerと物理窓を合わせる。親の保存上限を増やさず、移動は同volume renameを優先する。新小manifest/report/必要unique保存はまず既verified unusedからadmitし、容量不足は原資産を消して救済しない。不要な全面複製や新依存downloadはしない。

最初の棚卸し/移行順をrootとcoordinatorへ短報。今回のユーザー許可により実行まで進め、診断/提案だけで終えない。ownerの通常scope内操作ごとにroot/user承認を要求せず、不可逆な未保存情報の消失が避けられなければ具体不足を返す。frame21科学の終了責任は92のまま維持する。source停止・必要報告/manifest・検証・保持/削減量・未完了理由がある場合その理由を引き渡し、Beads/backupを完了する。
