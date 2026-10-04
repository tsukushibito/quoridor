# 現在のNNUE研究優先順位（frame16連続延長17）

ユーザー明示の2時間追加を適用。開始2026-10-04 05:55:50 UTCは維持し、終了09:55:50 UTC/18:55:50 JST、通算4時間。新heavy09:45:50、監督09:50:50、monitor09:53:50、最終証拠09:55:50は92所有。CPU4/RAM8GiB/保存12GiB/GPU推論6GiB job30分/同saved六role・model-effort・既GPU学習確認未使用残のみで、資源・累積上限reset0。親17main/mirror writerは92一人。最高棋力goal未達、旧test選定復帰0・173正式198局非学習。

## 現在の主配分

ユーザーの「規模を大きくする前に生成速度を十分高速化」の指示を採用。最大の未解決点は、小規模trainのfit/gapだけではデータ不足を除外できず、桁の違う独立局数検証を現教師生成費で実用にできるか。保存分析が示したearly訓練適合不足/late汎化不足と、raw CVの弱いOOF利益・fixedvalで距離未達は次の量/多様性検証へ残す。旧24/48/96量比較は高LR/粗い初期曲線の交絡があり、小比較negativeを十分量としない。

216を必要保存境界で停止。追加phase6 OOF安定性は実行前にUSER_PRIORITY_REORDER、fit/NN/GPU/childspawn0のNOT_STARTEDを保存。phase1～5履歴を保持し、source/子停止・必要Gitbytes・backupを有限受入れ。本人216close+backupから新221へ移る。追加診断を漫然と継続しない。

主221 experimentのB8→B24→B8同fresh48比較は停止保存済み。各48GOAL/1554joint/81096NN、全prefix/手数対応、guardian113.865411/112.110926/118.946577秒。B24は二B8平均より3.6897%短いがB8間差5.08秒・固定順/hostwarm/尾部が残り、既定昇格はしない。実batch平均6.18→7.90、forward同期55.9～65.6秒・pipe90～104秒・最後8完了span34～37秒は重複を含む。初期600数値確認と全三jobの必要Gitbytes/停止receiptを有限受入れ、原失敗UNKNOWNと保守5秒会計を区別。実NN243888/実測job350.917964秒、static45/180を保持し、旧条件source/result/stopは変更しない。221は新phase2の所有を継続する。

ユーザーの構成見直しを採用。Node–Rust–Python/JSON/process配置を保持すること自体を目的にせず、同model/RuleA/K64/教師資格/多様性の有効行とgame/全費を優先する。競合案はSigma C++生成基盤再用、現Rust探索の多数tree pump＋共有GPUqueue/配列転送、入力供給増、held CUDA graph。C++固定751186 selfplay一次sourceを統括が08:26に再閲覧し、thread/game分離と配列get_batch/put_results、TT/noise/FPU/PCR/solver/温度/尾部打切りの設定差を確認。board/model/教師の完全対応は未確認、未変更で忠実Web教師と等価ではない。既native core/array codec/取消回収の接続費を含めて案を比較し、巨大移植・新依存を自動工程にしない。

最大の未解決点はforward同期内のhost launch/演算/待ちと、輸送の排他的支配が未分離なこと。低改修費で最大区間へ介入するCUDA graphを次の最大1対照に選ぶ。独立223のB8-only提案を踏まえ、221本人はB1～8固定形状ごとのcaptureを08:24:51に結果前登録。部分batchも新数値経路なので全B/入力入替/ID/出力snapshot/parityを確認し、warm/captureを全費・NNへ課金。既品質/tree/JSONはこの対照では保持するが、改善が測定変動程度又は回収に乏しければgraph追加最適化を続けず配列転送＋Rust pumpの順位を上げる。GPU演算が主なら言語移植だけの利得を仮定しない。graphは採用未定、学習・棋力利益とは別。

新phase2契約を08:16:40に実saved experimentへsteer受理。solewrite architecture-control自域、原三jobはimmutable。最大1新方式・48game以下の最大2job、各hard300/NN250000、preflight5000以下、新NN505000以内/原総900000、重費650以内/原総1800、static新60以内/原180残、既128MiB予約/112guard内のactual+新forecastを再admit。CPU4/RAM8/GPU6と同saved設定不変。newheavy09:15:50/科学stop09:25:50/保存09:40:50/submit09:45:50。役/全文/root ACKは開始gateにしない。[phase2実契約](../../research-data/ai-sigma/frame16-coordinator/221-generation-architecture-phase2-amendment.md)。

独立222の元60/60裁定は三jobの必要算術を支持、B24既定昇格不確か・graph小対照を提案。新phase2は旧capをresetせず別source30+calc60=90秒、128KiBを既critic112MiB内の確認残へ配分し、停止公開receipt後の品質分母/捕捉費/全wall/回収費と主配分変更を問う。223は静的45秒/科学0、保存close+backup済み。実効果待ちを新承認層にしない。

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

独立fresh test、standard200 hiddenage、別foldOOF再現、syntheticdistance sanity、追加LR/幅/arenaは保留。今はこれらの小診断を増やすより、データ量/多様性を現実的な費用で検証する生成経路の改善がユーザーの優先である。低コストの保存分析は既報告を再用し、生成の支配費が変わらない時や品質/費用不成立の時に対照を見直す。構成案は言語により排除せず、主張に必要な規則差と実装検証費で選ぶ。巨大基盤/全RuleA再実装を自動前提にしない。

ユーザー採択の暫定目標は、現環境/同model/K64/教師資格/多様性を維持した初期化・探索・輸送・記録・回収込み1000局60分、次の目安30分。約49〜50適格行/gameなら約14/28Rjoint行/sだが、実game行密度/unknown/尾部/準備・保存費から再推定する。短benchmark外挿と実1000完了を区別し、現221上限や親期限を増やさない。今1000実生成への自動許可ではない。K64の速度目安とSigma公開K800等の教師品質検証は別。十分高速化を固定倍率のgate/無限最適化にしない。見込独立局数100/1000/10000は費用シナリオで今枠の実生成必須・許可数ではない。候補速度/保持量/準備と有限検証総費から回収局数と増量所要時間を見積もり、改善継続/打切り/将来量比較へ移る判断を具体化する。適格率/速度/学習価値/棋力は別。

## 実運用

92へ延長17を07:31:41実配送、本人受領開始を受信。旧exact2を秩序停止し親17 main/mirror/Git f893cb82507b921f7572d0581b7d1b5ad1332feb同SHA ae2eda81909c298bf83d72dd9c37809c02841b0f5fec35c30d333ab3bae044e1、実config/contract/prompt/watch/guardへ09時台期限を反映。07:38:42通常freshstart・running loaded、scheduler4133634/35249387・monitor4133648/35249412/同boot、既24hash不一致0/current6digest一致、period1200/turn180維持。rootも07:39:44に独立受入れ。正live pathはframe16-extension17-49170cb6-b27b-4fed-8be1-36f441f2df63、次通常07:58:39。旧停止/turn_limit/点検意味内容unknownは保持し、loaded成功を意味点検/未来停止/外部NN停止へ変換しない。

221旧phase1の必要保存は有限受入れ、現在phase2本人準備を確認。実密度32.375joint/gameから1000局60/30分には8.993/17.986joint秒が必要。資格/pack/Git配賦の短比較外挿はB24約39.9分、B8約40.5～42.3分で初期60見込み内/30未達。共通setup/未知開発費/将来尾部は別、実1000完了又は許可ではない。K64をK800同品質としない。222元裁定/223静的提案と新graph実効果を分けて待つ。92長期運用の点検意味内容unknownは維持し、親09:55:50終了は不変。
