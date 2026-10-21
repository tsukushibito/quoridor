# Othello 外部 baseline と Python 対戦接続

`quoridor-n96.1.2` の初期接続。要求正本は [strong-ai.md](strong-ai.md)。実対局は **UNRUN**。
起動・単一探索・protocol software test は棋力比較ではない。Root が自作 Rust image、実資源、
公平な時計条件を束縛した有限 job にだけ対局設定を渡す。

## 固定した外部入力

| 対象      | 実採用版 / full commit                                        | 比較での入口                                 |
| --------- | ------------------------------------------------------------- | -------------------------------------------- |
| Edax      | `v4.7` / `6c6991bee9a3d31d04f87934b04a7fd23c279f2b`           | 同 tag source の専用 Linux build、GTP        |
| Egaroucid | `console_v7.8.1` / `570d5e0a478c9d720d75de06a5d31995f412704a` | **Console7.8.1-engine + fixed-time adapter** |

公式資料: [Edax tag](https://github.com/abulmo/edax-reversi/tree/v4.7)、
[Egaroucid Console 案内](https://www.egaroucid.nyanyan.dev/ja/console/)、
[Console tag](https://github.com/Nyanyan/Egaroucid/tree/console_v7.8.1)。
GUI `v7.8.3` は Console 採用版ではない。Edax release metadata は既存取得分を再用し、
README の旧版表記を latest の根拠には使っていない。配布7zではなく固定 source build を実起動した。

外部 source/weights/binaries は Git 外の
`/workspaces/quoridor/.worktree/assets/tools/othello-baselines-n96-v1/` にだけ置く。
小さい `provenance.json` が実 build argv、compiler/CPU features、実 binary/source/weight/license の
SHA256・bytes・mode と検証証拠を保持する。195 member、56,916,641 bytes を先に選別して取得し、
全 repository archive、Windows GUI、大 book、学習 data は取得していない。
HTTP は socket/total timeout、member/aggregate size bound、streaming、失敗 partial 保持を使う。
取得上限256MiB、展開 source/weight 上限512MiB、build を含む asset 上限1GiB。
共通 decimal50GB は別に存続し、この上限から現在の空き容量は推定しない。

| 実ファイル                              |    bytes | SHA256                                                             |
| --------------------------------------- | -------: | ------------------------------------------------------------------ |
| Edax `bin/data/eval.dat`                | 13952436 | `f8b2299612d9fa4414157e70e932636e33111c2602d0c2fc382a7d90ef21b792` |
| Egaroucid `bin/resources/eval.egev2`    | 38243826 | `0a8acbcbc23067933627f1bcc83c3f7ae6b7ff3e603d174a3364271fcaeeef2f` |
| Egaroucid `eval_move_ordering_end.egev` |   472392 | `bd908885e8bb85e72a9be2b0399f8ca52ed40a138bcaaecca3d13710945b9a93` |

上の hash は取得後の実 bytes。source と license 本文も同 manifest に別々に固定する。
両 source は GPLv3 系の表記を持つ。Egaroucid README/source は GPL-3.0-or-later、
console の JSON header は同梱 MIT license も保持する。weights には独立した追加許諾を確認できていない。
外部比較への利用と製品への再配布・Rust 評価器への移植の採否は分ける。
[公式学習 data の条件](https://www.egaroucid.nyanyan.dev/ja/technology/train-data/) は再配布禁止。
その data は未取得、hash は null。book も未取得・無効で、未取得物に架空の hash は付けない。
Edax が起動時に内部生成する無効 book があれば、その実ファイルは manifest に別記する。

学習済 weight の再利用はまだ採用していない。Edax の固定 tag は61 ply、47 features、
226315 展開 weights、1 ply あたり114364 個の対称圧縮 int16 を header 後から読む。
Egaroucid Console の固定 tag は60 phase、16 patterns／最大10 cells／64 pattern features、
独自 `.egev2` の int16 packing を展開し、pattern と stone-count table を読み、別の終盤 move-ordering weight も使う。
両方とも STM 視点と色/空きの符号化・対称性・量子化単位の対応確認が必要であり、
source 定数だけで自作形式への互換性や配布可能性を認定しない。初回に全形式を移植せず、少量自前学習と
Python/native/Wasm parity を優先する。

## build と実起動

両 build は `-march=x86-64-v3`、専用 asset tree、CPU12、library threads1、GPU0。
Edax は upstream Makefile を GCC `-O3 -flto=1` で実行した。
Console の公式 direct GCC build は upstream の `<algorithm>` include 不足で最初失敗した。
上流 source は変更せず、`-include algorithm` を明示した `-O2 -pthread -std=c++20` で成功した。
外部固定時間 frontend 自身は `<algorithm>` を include して同じ engine headers を使う。
前回失敗・実 command・cleanup は OWN の `.process.json` / bounded log に保持する。
上流195 member の実 SHA256 を再照合し、engine/evaluator headers の bytes 無変更を確認した。

Edax の launch args は次のとおり。cwd は asset の `edax/bin`。

```text
lEdax-x86-64-v3 -gtp -n 1 -h 20 -book-usage off -ponder off -move-time 1 -l 1 -verbose 0 -nps 0
```

`-l 1` は book 不在時の起動用。book OFF でも `book_new` は初期局面を評価するため、
`-l 60` 起動は最初15秒で timeout した。各 game の reset で `time_settings 1 0 1`、
各探索前に `time_left <black|white> 1 1` を送る。後者で実探索 level60 になる。
Edax は move-time mode でも `options.time=main_time*1000` を使うため、
`time_settings 0 1 1` は1秒設定にはならない。誤設定での約0.101秒の結果も保存し、
修正後の単一要求は約0.991秒だった。`-nps 0` は node 換算時計を無効にし実時計を選ぶ。
内部10ms margin と停止後の応答費を記録する。

TT は同一の **upper32MiB** を基準とする。Edax `-h20` は main24MiB、PV/shallow 各1.5MiB、
小 thread table/align/spin を持ち約27MiB。固定時間 Egaroucid は `hashlevel20`、実 node24 bytes、
active TT25,165,872 bytes。等しい exact table layout/bytes とは呼ばない。
上流の static TT virtual reserve805,306,416 bytes と他の global arrays は別に残る。
Egaroucid 単独 probe の process peak RSS は1,368,186,880 bytes、family peak は既存 guardian で別計測した。
実対局時は Rust processes を含む family2GiB、controller64MiB、child 合計1984MiB、host reserve4GiB を再確認する。

## Console7.8.1-engine + fixed-time adapter

公式 GTP は `time_settings` をサポートせず、`genmove` は `ai_with_settings` の level 探索を呼ぶ。
`-time` を渡しても GTP の1秒/手にはならない。公式 Console GTP は起動・盤面 roundtrip 用に保存する。
通常 Console の `ai_time_limit(remaining_time_msec)` も `calc_time_limit_ply` による対局残時間の配分である。

別 tree `fixed-time/egaroucid_fixed_time.cpp` は同じ固定 engine の
`tree_search_legal(..., time_limit=1000, ...)` を直接呼ぶ。engine/evaluator code を変更しない。
既存 depth5 clog search の実費を引き、既存 iterative deepening に残り時間を渡す。
途中 iteration は upstream が取消後に future を回収し、最後の成功 iteration を保持する。
frontend は completed iteration/合法 move が得られない場合、推測せず error を返す。
`ai_time_limit` の game allocator/時間再配分は通さないため、この入口の timing policy を公式 GTP と同一視しない。

frontend は pool0・`use_multi_thread=false`・book init 無し・ponder 呼出し無し、hash seed20261022。
上流 `std::async` による control/wait thread は残り、実 probe で OS threads 最大2、
全 thread affinity CPU12、一度に探索する worker は1。上流 `tim()` は `high_resolution_clock`、
外側の経過時間/安全期限は Python monotonic。clog は個別の期限を持たず、iteration 取消後 join もあるので
1000ms 厳密停止を保証しない。単一要求で約1003.3ms、completed depth26、選択率74%、未証明だった。
手番時計の要求/応答境界と100ms transport allowance は config に事前固定し、超過は timeout に残す。

frontend は JSONL `info/inspect/reset/search`。`search` は絶対色の Rust `state` と `timeMs:1000`、
bit63-index へ変換し STM engine board を渡す。`reset` は active TT を初期化する。
`inspect` は接続検証用で、対局正本の代わりには使わない。
score は STM、終局の空きを勝者へ割り当てる engine 規約。Rust の実黒白石差とは別である。
heuristic/selective 値を exact と呼ばず、対局勝敗には一切使わない。

## Python 接続と未実行 smoke

入口は `games/othello/python/othello_arena`、test は `games/othello/tests/python/test_arena.py`。
Root は既存 `CPUPlan.from_record` / `CycleResources` / `execute` 内で次の有限 argv を実行する。
独自 job manager や新しい監視 session はない。

```text
<project-python> -m othello_arena --config <Root-bound-config.json> --output <new-owned-output>
```

既存 project-env は共通環境の reader lock と対象 worktree を選ぶ。
現時点で Othello Python root は共通 PYTHONPATH に登録されていないため、既存 execute の子 env に
`<target-worktree>/games/othello/python` を追加する。root pyproject/lock/scripts は変更していない。
実 binary/weights FileRef を確認し、native は persistent JSONL、Edax は persistent GTP、
Egaroucid fixed frontend は persistent JSONL で接続する。送受信/stderr は drain し末尾64KiBを保持する。
EOF・crash・timeout・illegal・cancel は結果に残して停止し、予定分母を維持する。自動補充・再試行しない。
native の `timedOut:true` は、探索 budget を使い切って完了済み iteration の合法手を返す通常動作も含む。
通信 deadline 超過とは区別し、返却された探索 metadata と実 wallMs を手ごとに保存する。
直接子は TERM/KILL/wait と pipe/selector close、子孫は外側の既存 execute が回収する。
実 output の `CANCEL` と外側 guardian の OWN CANCEL の両方を使える。

`new/status/play/pass` の Rust 応答が合法性、forced pass、実終局、石差を決める。
両 baseline の a1=row-major0、絶対黒白、c4 後の非対称盤面・白手番 roundtrip を確認した。
fixed frontend では forced pass、空きのある終局、四つの開局状態も確認した。

OWN `.artifacts/othello-baselines-n96/smoke-config.unrun.json` は結果前の計画。
4 family × 両色8局を各相手へ予定し、purpose は protocol/cost、superiority claim は false。
seed による8手の legal opening を公式 Console から作り、D4/色反転の family hash が四つ異なることを確認した。
この四 family を train/dev/final から除外する。各 game の Rust replay は frozen opening state と照合する。
train/dev/final data 自体は未作成なので、その分割適用は Root が dataset を作る際に束縛する。

`rules` / `candidate` は Root 供給の immutable native image（SHA256
`550b87377274b202056925a39bcfa4164aaf0dff3ff17bb993b6d43517be8975`、712232B、0755）に束縛した。
四 family の Rust replay、Edax 全盤面、fixed frontend の合法手/手番/forced pass/空きのある終局が一致し、
実 native search と fixed frontend の単一要求が合法手を返した。根拠は OWN `native-integration.json`。
`launchBinding` は null のまま。実終局対局と fair resource job は **UNRUN**。
初期 untrained heuristic の敗北でも棋力の結論にはしない。
既存簡易 policy を比較するときは Root が config の `candidate.simple` を true にした別設定を束縛する。

検証証拠は OWN `tests-final-scope.log`、`edax-probe.json`、`egaroucid-probe.json`、
`egaroucid-fixed-probe.json`、各 `.process.json` / `.rss.json`。fake protocol 8 tests が成功した。
C++ frontend は clang-format 未導入のため既存 style で手動整形し、限定 compile/probe を適用した。
Python は共通 Ruff、100桁で対象だけ format/check/lint を行う。
