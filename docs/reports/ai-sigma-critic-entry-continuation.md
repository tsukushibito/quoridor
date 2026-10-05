# SIGMA-ORT-ENTRY-CRITIC / .43 / 試行1・契約1
critic → coordinator。契約fc2a75d6…3c9df/親継続枠を全文確認。判定no-go：実backendのbounded cleanup→PID0→freshが独立再現できなかった。actual_go=false、新事前登録未完、新対局/holdout0を維持。

入力：指定83dcd870…d04aはentry-manifest.json。manifest-final.jsonは別総括(ed57275d…a3ccc)。report e3d3fb51…ecf7a/source hashes73929ae4…6a980を固定し、原38checksを含む381入力hashは検証前後不変。原process記録から190 PID/starttickを独立収集しzombieを含め不在確認。原source/artifact編集0。

実行前にinitial-p1のみ、500/g91の両engine→候補10/g0(delay500)→stop→fresh両engineの5要求を固定。自己同bytes copyへ絶対入力・自己出力・期限10:45・temp/guardだけpatch、差分/hash保存。最終diagnosticGoldenMainの正tokenを通した。

独立runtimeでは通常候補/参照とも合法Action13、owned cp/fallback0、最終postvalidation stamp期限内（447.823/433.704ms）。T10はNO_RESPONSE_TIMEOUT、公開Action=null/checkpoint=false（14.828ms）で拒否。その後immutable cleanup.cjsのboundedStopがOWN_CLEANUP_FAILEDとなりexit1。原mainはここで停止し、fresh2要求・正経路後の既run拒否まで未実行。失敗時の残identity一覧を原helperが出さないため、監視負荷/子回収race等の原因は未確定。正常2件とdummy成功でこの必須失敗を救済しない。

独立mockは20人工採番・同prefix先後・seed1979・pairretry1/global2、pause/expired、正診断token/旧foreign/hash/偽受入れ/既run拒否、actual_go=falseの実CLI拒否を確認。候補NN/model/fallbackはloss、固定参照のみinvalid、IPC/refereeはinvalid、期限/crashは当該engine loss。producer全identity、boolean/finite/prior/owned cp、postvalidation期限後Action=null、取消旧応答拒否、cleanup永続pendingでもwatchdog公開破棄を確認。dummy detached TERM→KILL/wait/idempotent、既signalCodeのabort/close、自然終了は通過。実対局中pause/実NN freshの証明ではない。

旧rawを版別に独立集計：原32は28採用/4拒否、補足5と最終5は各4/1、自己未完3は2/1。全版boolean・拒否Action=null・最終stamp期限後採用0。42を速度/標本に合算しない。数値checkerは元3888featurebits/822NN/386prior対応比較を試みたが、比較数を値数と二重計上して失敗。1回修正後、P2でraw Sigma136とcanonical索引を誤同一視する追加assertが失敗し再修正せず停止。原数値不一致の主張ではなくcritic helper失敗であり、全面数値gateは未完了。元logと再構成初版source/索引診断を保存、閾値変更0。

自己処理停止JSON10:33:25.997を本文前保存、追跡55 identity残存0。runtime NN終了10:16:07.462、以後NN再試行0。全観測TID CPU2、RSS標本最大2,071,625,728B<2.5GiB、保存約1.2MiB<112MiB。privateTMP/XDG、command/exit/PID/starttick/hashを記録。外部job停止・瞬間peak・正式無競合を認定0。build/取得/委譲/GPU/他者kill0。

引渡し：continuation-20261001/CRITIC-ORT-ENTRY/summary.json、runtime-stopped.json、全process/log/copy-patches/独立mock/版別集計を保持。writerは別契約でcleanup失敗時の残PID/starttick/stateを保存し、実PID0→freshを再成立させる必要がある。critic数値checkerの修正も別許可範囲で必要。元syntax/分類/scope/zombie修正失敗、全session強制停止、T10 NN開始数欠測、旧時計/GUARD/来歴・ORTheap等未確認、旧32局/正式NI未立証/Sigma同等未達を保持。.43受入れ待ち、goal/他者close0。
