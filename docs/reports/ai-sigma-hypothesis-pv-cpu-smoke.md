# CPU toy PVパイプライン / quoridor-4lc.162

固定5 diagnostic rootから、CPU loss/backward→checkpoint→weights_only再読込→ONNX→CPU ORT forwardの1runが成立した。これはtrainer/保存/変換の小さい機能経路の支持であり、学習用教師集合の完成・独立holdout・本PVモデルの棋力・Sigma非劣性・NNUE/αβ実装を支持しない。

契約80ac5493/枠10。受領観測03:30:30UTC、ready/show goal+self/pauseなし本人担当確認後03:31:23 claim/static開始、coordinatorへ実配送。160 source hash一致と自己子current exact identity不在を確認した。159 science-stop SHA f1ed53ca0137932fca331d082b845c552671136387d954fb532c2bf0b3c4a034にbind。03:39:29の自己admissionで原6job process hashと558記録identityの現在不在を確認、remaining/unknown空。foreign current研究RSS 138035200B、162予約1GiBと任意161 CPU2/RAM2GiBを含むforecast 3359260672B<親8GiB。CPU0単1と任意161 CPU2単1で親4logical内。実host MemAvailable 21045821440B。これはその入口の有限確認で全host/全期間/自然終了保証ではない。159 pack/report helpersの継続はheavy再開と混同しない。

科学入力は160保存JSONL SHA 978b3a9eb51e9b994e8d5c56bd97bbd1281797be0e3d925b42b9dfcb2c71cd2e、5根 initial/asym/jump/prefix13/14、4train1validation/5groupをそのまま使用。原648 f32bitsと合法対応/π136/history/side/ply/keyは160 validatorの再読込で確認。πはK32 rootN32/edge和31の訪問分布、NNpriorではない。value targetはrootmean_stmというK32探索予算付き蒸留で、game z欠測を付替えていない。既人工golden3根/同じ5根の選定偏りを保持し、validation1も診断だけ。今回新教師・game・Chrome・build・download・install・環境update・GPUは0。

事前固定はpreregister.json SHA 3cf99678accbfe3e81eb92be28af4f8127df8d0e2e5cb74d270632188ff5ebbb。初期重みseed80311、648→16 ReLU→policy136 logits/value1 tanh、float32 CPU、12713 parameters。Sigma重みの継続学習ではない。masked合法cross entropy(π) + MSE(rootmean)を4train全minibatchで20step、SGD lr.01/momentum0/decay0。CPU no_grad add_(grad,alpha=-.01)で同じSGD更新を明示し、optimizer CUDA graph hookを避けた。CPU generatorだけをseedし、torch intra-op1/inter-op1、OMP/MKL/OpenBLAS1、CUDA_VISIBLE_DEVICES空、自己sourceのCUDA API呼出し0。CUDA/GPU初期化を必要経路にしない。PyTorch 2.14.0+cu130、ONNX 1.23.0、ORT 1.30.0を既専用環境から使用、共有環境は更新していない。

全20 loss/gradient finite、全6 parameter tensorsが更新された。checkpoint 53929B SHA 52aa17fcb29113e85264a1d1740adac616750bf6208270d8313f369d60c8800c。state_dictのみをCPU weights_only=Trueで再読込し、全weightと固定5行forwardがbit一致した。ONNX 51619B SHA 6763321690ec595ff4e0f40090987d85a0e8ee34a2cf3f3d7720ca3b4b26e895、既legacy dynamo=False/opset17でexportしcheckerが通る。CPUExecutionProviderのみ/intra1/inter1/sequential。固定5行のpolicy[5,136]最大abs誤差 1.192092896e-07、value[5,1] 6.705522537e-08、事前tol abs1e-5+rtol1e-4を全要素満たす。実Wasm/provider比較や5行以外の数値保証ではない。

診断train lossは 4.818754673→4.395173550、validation lossは 4.966817856→4.832641602。下降は観測だけで採用thresholdではない。損失低下・教師一致・同じ5行fit・短い実時間を棋力又は本学習費用に変換しない。

実科学jobは03:39:31.776→03:39:34.273、2.496414秒、学習actual1run/20stepで再学習0。観測manager+子peak RSS 729448448B（約695.66MiB）<896MiB guard、所有TIDはCPU0に限定。終了後current子RSS0、outer wait完了、remainingunknown空。import/学習/export/ORT込みのこのjob費であり、本モデル速度や正式性能測定ではない。全必要metricと20step ledgerはresults.json/training-results.json、開始/終了/版/source/identity/資源はstarted/job/admissionに保存。

失敗r0は自己private index328312Bを含めた保存forecastによるspawn前拒否。そのエラー記録器__name typoも発生した。科学child/import/training未開始を記録し、Git b331f330の版を保持。自己未使用indexだけを削除し、修正Git1aefc128で新admissionを行った。後段Gitはindexを作らないtree/object方式、共有default indexはreadonly検証。科学成功への付替えではなく、未開始の入口修復で実trainは1run。報告生成にも一度f-string SyntaxErrorがありreport-debug-r0.jsonへ保存、科学再実行0で本writerを修復。ORTのtelemetry device ID保存失敗警告（in-memory）とlegacy export警告、自己TMPDIRの空mat-debug logはそのまま保持し、環境修復や再学習はしない。

停止正本science-stop.jsonへ03:39終了後のsource hash/版/結果/モデルhash/current exact identity不在を保存し、heavy停止をcoordinatorへ先報。sourceはtoy.py/launch.py書込停止、Git/復元/report helperは別。現在不在を自然終了/全期間へ格上げしない。自己保持＋Git forecast512KiB内、旧conservative13974439Bを減額せず本scope512KiBを加えcombined14498727B<14MiB、親新予約0/既hyp16MiB内。複数checkpoint/ONNX copyを保持しない。静的管理は60秒内を保守計上し、CPUtoy総120秒・job90秒を維持した。

次判断は1つ：別配分で、結果前に固定した少数新selfplay教師からπ/z/rootmean/予算を保存し、fullstate+prefixとgame lineageを同groupにしたtrain/validationへ接続する。担当experiment/private生成・trainer scope、GPU追加なしならCPU1/4pair8game×最大200ply×500ms=対局時計800秒＋init/停止/保存、teacher保持8MiB・model4MiB・log4MiBを見積りの出発点にする。toy smokeはCPU1/RAM1GiB/120秒程度で限定し、writer45分・独立schema確認10分。これは新許可ではない。本PV構造/本学習の必要data数・CPU/GPU費はこのtoyから推定できず、次実配分で固定・計測する。初期重み学習とSigma継続学習を分け、元PyTorch構造/state_dict移送がない限りONNXだけを継続学習readyとしない。

新教師schema/group漏洩/π合法mass/z視点が不成立なら最小修復へ戻り本学習/arenaを保留。接続成立なら実費を基に本PV構造・教師生成量と独立同wall arena計画を選定する。学習lossが下がっても棋力は固定モデルの独立評価で別に判定し、NIには158の事前正式条件を使う。NNUEは後続候補でPV全完成の恒久gateにしない。今回goal/他者close0、受入れcoordinator。

最終保存data/report Git `4f0e14a748eda2030ba5f85838e691128ffdaa15`。必要8path（checkpoint/ONNX含む）はGitからstreamしSHA/size/current一致を確認、全copy/展開0。自己ファイル保持178677B＋Git保守forecast229376B＋metadata余裕8192B=416245B<524288B。初回未使用privateindex328312Bの一時peak/削除を別記、旧carry減額0。科学command開始終了は正確、初期管理commandの個別UTCは未保存でtool transcriptのexit/wallを残し欠測扱い。管理tool wall概算30秒＋残上限15秒を静的60秒枠内で保守計上する。
