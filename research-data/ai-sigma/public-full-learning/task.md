# 公開Sigma全量・正しい反転・GPU収束学習

担当issue: `quoridor-4lc.323`。

2026-10-07、ユーザーは公開全量の学習、正しい左右反転、ハイパーパラメータ調整、その後のSigma MSE比較を主方針に選択し、学習側も時間枠・実行時間制限を設けず進めるよう指示した。旧曲線の再分析と100万行の延長は主作業から外す。旧100万行issueは完了のまま、新しい実仕事を同じ担当セッションで進める。研究状態は docs/research-findings.md、担当状態はBeads。

## 目的と許可済み実作業

- 固定source751186344fc52ad0c29bc65922e62c6fa915f006の43 NPZを利用。前半original9,457,039保存観測を全域処理し、観測ごとのnative不正と終了理由不明z0を理由・分母つきで除外する。後半naiveLRを教師に再使用せず、有効な同盤面の別勝敗は保持する。必要な同blobの取得、shardごとのstream decode、compact供給の実装と実行は許可済み。全raw常駐はしない。
- 既original alias seed/splitを可能な限り維持して全適格観測をT/V/Eへ分配し、旧bottom-rank件数による100万行への切詰めを外す。原観測と反転兄弟は同split。同盤面の別観測による一致は許容し、validation一致を理由にTを削除しない。既開封の評価観測は新選定に戻さず、旧開封集合と新未開封Eを識別する。結果前に具体分割規則・各既露出・主指標・選定/停止規則を固定する。全データ利用は評価用labelsのtrain投入を意味しない。
- 正しい左右反転をnative幾何から定義。非対称壁anchor/境界、両側視点、distance/QF1、二回反転、合法Action/遷移/ゴール/手番/同zを独立referenceで確認する。まずonline augmentationで保存二重化を避ける。固定元行順shuffleと別seed RNGを束縛し、validationは固定original。兄弟を独立gameや新原観測量に数えない。
- 主模型は現QF1+D/FT32/H32、route4off、FP32、同z/STM尺度、Adamを保つ。新主corpus上でGPU batch・LR・warmup/decay等scheduleを少数の根拠ある条件で比較し、有力条件をvalidation収束まで進める。既20epochや旧batch128を完了条件に固定しない。最初に供給/初期数値と有限更新を確認し、本学習へ直接つなぐ。学習率の線形batch倍率を正解として仮定しない。科学的なpatience/min_delta/収束や非finiteによる停止は設定可能だが、wall timeや恣意的な計算量上限で打ち切らない。旧test結果をハイパーパラメータ選択に使わない。
- 曲線はstep/seen/effective epochs/wall、固定train診断とvalidation、epoch境界の必要集計を保存し、初期を細かく、後半を間引く。全V評価を過剰頻度にせず、頻度/全費を計画に束縛する。CSV/PNG/SVG、checkpoint INITIAL/BEST/LAST、dataset/scale/config/model/seed bindingを維持。記録済み最小と連続最適点を区別する。
- 最終候補/config/評価規則をfreeze後、新未開封Eで一候補/D/train定数と固定Sigma value NNを同じSTM/±1教師尺度にして比較する。SigmaのMCTS rootmeanをNN単体MSEへ混ぜない。Sigmaの過去公開data露出UNKNOWN、game/history欠測を保持。MSE/符号/校正/局面層とnativeモデル推論・whole-search費を別々に報告し、MSEだけで特徴不足/容量不足を確定しない。表現力拡張/縮小・特徴・量子化・新探索方式は実装せず、人間の次判断に具体根拠を返す。

## 担当・所有・資源

同saved thread01a1100f-6d45-78e0-8a87-84503ff0fbf6、同model/effort、同managed WT /workspaces/quoridor/.worktree/learning-millionを再用。create/resumeはdanger-full-access/approvalPolicy neverを明示確認。最初にready/show/本人claim/cwdを確認する。RootがmainとGit/index/ref/commitの唯一writer。担当はWTのdata/compact producer/loader/trainer/native qualifier/config/testsに限定し、現在main採用版と必要依存だけ整合、恒常mirror・全tree同期・他WT編集はしない。モデルfeature/math/layout、core/AI探索への変更は未配分。

CPU2,3最大2logical、RAMfamily4GiB、VRAM6GiB、親CPU4/RAM8/保存12GiB/UNKNOWN128MiB維持。end_at/notify_until/max_runtime_seconds、累積CPU/GPU時間、epoch固定上限、MAXjob/forward予算による停止は設けずnull。旧GPU3600/7200・旧600/300/NEW120等の費・失敗・UNKNOWNは歴史として保存し、新作業の実残証明や入口auditへ使わない。日時や巨大有限値で無制限を偽装しない。ログ容量、RAM/VRAM/保存、pause/cancel/本人所有/正確子回収の実制御は維持する。自然完了イベント一度で再開、計算中Idle、定期LLM監督は設けない。

旧learning319の736MiBは保全用予約であり、全量の追加配分を意味しない。まず全量compact/stream/scratch/weights/evidence/Gitまでの保存予測と具体rootを準備し、Rootへ必要量・供給案を一度戻す。Rootが現在資産と旧未知予約を保全して前向き配分する。新rootは容量成立前にheavy取得/生成しないが、source実装・fixture・準備は進める。全域/共有targetの繰返しwalk、旧全史audit、細かな読取/整形/LLM作業時計を追加しない。必要な容量確認は完成したbinding対応observer結果を再用し、coverage/予約が変わる場合だけ更新する。全量保存が成立しない場合はstream/compact構成を工夫し、データを少数subsetへ勝手に戻さない。

共有Cargo writer一人。初期source整合/buildは探索担当の現在job exactSTOP後に直接調整する。GPU学習/重decode/推論は探索の公平clockとは非重複。学習中に他担当の静的source準備とprivate binaryを使うNN0限定compileは別CPUで可能だが、elapsedを公平性能比較に使わない。RootACK/全役ACK待ちを設けず、開始STOPを相手へ一度届け、Root経由で必要な次slotを具体調整する。

## 関連境界の独立確認

データ選定/正しい反転/ラベル/凍結評価は結果妥当性を左右すため、既reviewer319.1 thread01a1103c-fbe0-7412-a406-fbee697a1392を関連差分だけの別仕事で再用できる。担当から直接、問い・一次source・版/SHA・独立oracle・fixtureを渡す。fullaccess/never、read-only、CPU1/RAM512MiB、既evidence内2MiBを基本とし、時間予算は設けない。必要境界の導入前に重大指摘の解消を確認、通常修正は同reviewerへ戻す。毎runレビュー/追加roles/再帰委譲/全稿ACKは不要。Rootが採用・統合、重要意味変更のみ人間へ戻す。

## 到達点と停止

全適格公開originalを供給し、正しい反転を含むGPU本学習と新corpus上のhyperparameter比較・収束観測、凍結未開封評価のSigma/D比較、必要native資格/画像/全工程費/限界・停止paths/SHAを引き渡す。旧曲線分析や1m延長を入口にしない。ユーザーの停止/pause、真正な資源不足、非finite/不正対応などは明示して止め、原結果を成功化しない。scope内の未成立候補から別候補へ進み、次設計が全て人間判断だけなら具体質問を返す。最高棋力を達成・default重み採用と先取りしない。必要原data/model/evidence保全、small report/manifests/圧縮evidenceのみmainへRoot統合。

## 人間指定の高学習率比較への継続

全3LRの結果を確認後、ユーザーは「もっと大きい学習率を試して欲しい。上限の確認はしてないよね？」と明示した。旧3e-5/1e-4/3e-4 cohortの観測・最小選定・失敗を保存し、3e-4を旧範囲内の暫定最良とする。続いてユーザーは「最初は極端に大きくて良いよ。二分探索のように検索していく方が効率良いでしょう」と指定し、初案1e-3→3e-3の順次拡張を置き換えた。初期LRだけを変え、同qualified INITIAL/batch2048/全T/fixed original V/Adam FP32/尺度/seed/反転RNG/257warmup/plateau/科学的停止規則で、まず0.1を大きな上側候補として試す。悪化または非finiteなら旧良好値3e-4との倍率中点（sqrt(.1\*.0003)≈.005477）などで範囲を絞る。良好な上端が続けば上側候補を拡張する。MSEの単調性は未証明なので厳密な二分探索による全域最適保証とはせず、実validation最小・有限性・収束を根拠に対数尺度で探索する。有限の初期振動だけで不安定上限を認定せず、減衰後に回復した場合も初期LRと実LR推移を区別する。候補ごとの判定と精度基準を結果前固定する。有限振動と非finite失敗を区別し、失敗を条件変更で救済しない。普遍的最大LR・最適値とは主張しない。

新候補config/input/guard/job/validation選定規則とinclusive保存予測を結果前に固定する。旧出力/費/UNKNOWNを保持し、現1040MiB等の資源内成立またはRootの具体的な前向き容量配分後に実行する。時間/epoch/forward/job上限は設けない。重要な意味変更を含まないLR比較で毎fitレビューを追加せず、同セッションで継続する。最終Sigma/newE開封は拡張比較・最終選定・global freezeと関連入力境界確認まで保留し、評価labelsを追加LR選定に用いない。

## 初期0.01固定・減衰倍率比較への最新方針

ユーザーは初期LR0.01を候補に固定し、減衰率の調整で短いepochで速く収束させる方針を指定した。実行中midpoint3 cdf72ec0は設定を変更/取消せず自然停止を保存し、その後の機械的な初期LR二分探索は継続しない。まず減衰倍率0.5対0.25を、同qualified INITIAL/全T/固定original V/model/尺度/batch/Adam/RNG/反転/warmup257/plateau patience2/minLR/earlystop/null horizonで比較する。倍率以外を同時に変更しない。結果前にfixed pair/config/input/control/選定規則と全旧outputsを保全するinclusive容量を束縛する。初回fullV .44/.435/.43や結果前固定のincumbent+0.001到達、updates/seen/wholewall/実LR曲線と最終精度を併記する。epoch数だけで速さを認定せず、trigger/patienceによる到達時間の限界も区別する。これは準備案であり新fit開始/2候補分20MiBの自動配分ではない。最終Sigma/newEは選定/freeze/境界確認まで保留する。
