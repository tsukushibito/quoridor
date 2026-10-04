# 現在のNNUE研究優先順位（frame16連続延長17）

ユーザー明示の2時間追加を適用。開始2026-10-04 05:55:50 UTCは維持し、終了09:55:50 UTC/18:55:50 JST、通算4時間。新heavy09:45:50、監督09:50:50、monitor09:53:50、最終証拠09:55:50は92所有。CPU4/RAM8GiB/保存12GiB/GPU推論6GiB job30分/同saved六role・model-effort・既GPU学習確認未使用残のみで、資源・累積上限reset0。親17main/mirror writerは92一人。最高棋力goal未達、旧test選定復帰0・173正式198局非学習。

## 現在の主配分

ユーザーの「規模を大きくする前に生成速度を十分高速化」の指示を採用。最大の未解決点は、小規模trainのfit/gapだけではデータ不足を除外できず、桁の違う独立局数検証を現教師生成費で実用にできるか。保存分析が示したearly訓練適合不足/late汎化不足と、raw CVの弱いOOF利益・fixedvalで距離未達は次の量/多様性検証へ残す。旧24/48/96量比較は高LR/粗い初期曲線の交絡があり、小比較negativeを十分量としない。

216を必要保存境界で停止。追加phase6 OOF安定性は実行前にUSER_PRIORITY_REORDER、fit/NN/GPU/childspawn0のNOT_STARTEDを保存。phase1～5履歴を保持し、source/子停止・必要Gitbytes・backupを有限受入れ。本人216close+backupから新221へ移る。追加診断を漫然と継続しない。

主221 experimentへ07:39:23実配送し同saved turn/start accepted、Beads in_progressを確認。成立済み187/194のGPU24active/maxB8/heldprovider多handleをreadonly再用し、queue/IPC/encoding/記録/初期化/尾部/GPU処理の支配費を短く測る。最小変更1方式を現在GPU24/B8基準と比較し、必要な同条件確認まで一課題内で実装・測定へ進む。B/active増は候補で固定義務でなく、B>8partial/full数値ID対応/RAM/VRAMを新確認する。教師K64/モデル/RuleA/π/z資格/多様性を維持し、主指標はRjoint/全attempt guardian jobwall、game秒、actualbatch分布と実資源。K削減/低品質/重複兄弟量を質保持高速化と呼ばない。[実契約](../../research-data/ai-sigma/frame16-coordinator/teacher-throughput-contract.md)。

221上界は最大2主条件＋同条件確認1job、各登録96game以下/active48/B32以下、各hard600s、累積heavy1800s/NN900000(数値確認/startup/失敗含む)、source/math180s/保存管理600s。実量は支配費と費用で絞る。CPU同時計算4論理、jobRAM6GiBguard5.5・親8GiBcurrent、GPU6GiB、新scope128MiB予約/112guardを既experiment1980MiBの確認unused内へ計上、旧保持減額なし。science/currentownership/pause/物理RAM/GPU/正monitor owned/quietを直前admit。新job開始09:25:50/科学停止09:35:50/保存09:45:50/submit09:50:50、親より早く回収。benchmark教師は学習へ自動混合しない。

独立222 criticへ07:39:43実配送/start accepted。対照の仕事量/hostwarm/管理CPU/尾部交絡、品質・新batch数値対応、将来生成の所要時間・保存量と改善総費の回収を問い、主配分変更も提案できる。新static60s/128KiBを既critic112MiB残内、旧219120等reset0。主221の静的開始/実測は全文承認/root再確認待ちにしない。

## 保存分析から残す知見

| 同rootmean/gameequalの観測 | 支持範囲と残る問い |
| --- | --- |
| D train .405944/val .485147、standard200 .548567/.613916、standard400 .257283/.648772 | earlyfit不足とlater汎化差は共存。データ不足や全特徴無効は未判定 |
| standard400 valgap .163625=.192934変位−.029310 alignment、平均bias/clip小 | 未見残差方向の一致が弱い。単一teacher/history原因は未判定 |
| learnedhidden固定ridge.01 train .208594/val .612799、scalar参照val .484540 | readout変更の有限改善でも距離未達。217必要算術独立PASS |
| raw626.01 train .161374/val .781449 | 加法的rawfitの転移不足。このλ/geometryのowner-only診断 |
| raw5gamefold CV λ1 OOF .382828<foldD .408041、fulltrain .215837/val .548893>D .485147 | 正則化関与の有限支持、λ選択/単partition/少数valを保持。219独立必要算術PASS、旧test/棋力利益なし |
| OOF→val差 .088960=構成 .002346+within .086704−片側 .000090。OOF/val/差の固定game区間すべて0跨ぎ | 同セル内関係差の記述点推定、OOFfit72/78対full96・小標本で分布因果は不確か。phase5 owner-only |

216実NN29505、重forwardwall4.815048s。NN0 phase3成功.895876+parsefailure.053226、phase4 2.463894、phase5 .215337。保守static144.628333/180、phase6実未開始。旧成功/失敗/期限/Git保存境界は変更せず、wallと保守chargeと全team費未集計を分ける。walls binsはremainingstockで配置壁複雑さとしない。

## 競合案・打切りと次判断

独立fresh test、standard200 hiddenage、別foldOOF再現、syntheticdistance sanity、追加LR/幅/arenaは保留。今はこれらの小診断を増やすより、データ量/多様性を現実的な費用で検証する生成経路の改善がユーザーの優先である。低コストの保存分析は既報告を再用し、生成の支配費が変わらない時や品質/費用不成立の時に対照を見直す。言語移植/巨大基盤/全RuleA再実装は先行しない。

十分高速化を固定倍率のgate/無限最適化にしない。見込独立局数100/1000/10000は費用シナリオで今枠の実生成必須・許可数ではない。候補速度/保持量/準備と有限検証総費から回収局数と増量所要時間を見積もり、改善継続/打切り/将来量比較へ移る判断を具体化する。適格率/速度/学習価値/棋力は別。

## 実運用

92へ延長17を07:31:41実配送、本人受領開始を受信。旧exact2を秩序停止し親17 main/mirror/Git f893cb82507b921f7572d0581b7d1b5ad1332feb同SHA ae2eda81909c298bf83d72dd9c37809c02841b0f5fec35c30d333ab3bae044e1、実config/contract/prompt/watch/guardへ09時台期限を反映。07:38:42通常freshstart・running loaded、scheduler4133634/35249387・monitor4133648/35249412/同boot、既24hash不一致0/current6digest一致、period1200/turn180維持。rootも07:39:44に独立受入れ。正live pathはframe16-extension17-49170cb6-b27b-4fed-8be1-36f441f2df63、次通常07:58:39。旧停止/turn_limit/点検意味内容unknownは保持し、loaded成功を意味点検/未来停止/外部NN停止へ変換しない。

221本人07:41:47 claim/static実開始を受領。保存205のjob73.55s/pipe61.62s/forward38.14s(重複和非wall)から同active24でmaxB8→24だけを変える薄い案を固定、同fresh48opening/actionseed・baseline→candidate順を保存。新B1..24 heterogeneous CPUORT/CUDA600sample/ID/f32partial確認後のみ候補測定。現NN科学未開始、hostwarm固定順と数値差の経路交絡は保持。現在待つ観測は221実数値確認・quality-preserving測定、222独立選定・必要結果算術。92は新期限で長期責任を継続。219/220の有限保存は受入closed。意味のある結果でこの主配分を更新し、実験完走を最高棋力達成へ読み替えない。
