# SIGMA-BROWSER-SAB-INDEPENDENT / quoridor-4lc.109 / 契約1・枠7

**ブラウザmain/SABの最小実経路と保存4局を有限支持する。正式公平性・NI・Sigma同等・actual_goは未認定。** 独立runは7公開＝通常6合法・取消null1、late／未完了0。原4局はブラウザ内合法replayで296公開・goal4・候補W2D0L2を確認した。原対局の新NN再実行、独立fullgame、holdoutは0。

受領07:04:21UTC、契約／親現行版7／common／critic／記録規約全文、ready/show・pauseなし・本人割当を確認して109だけclaimし開始報告accepted。処理07:49／新run07:44／提出07:59を固定。原tested Git ec4e92d68b4b4aabd7d45ae6cf8cb1234abae82b、機能版81401c2、最終handoff Git181ea3932d270a9f0e69145b57577b411ecbab62を区別した。README／報告の停止後追記はruntime変更やNN負例にしない。

独立コードは必要path/configとブラウザ内checkerだけ追加し、元browser-sab→browser-main／sab-worker／SharedBestAction／Numeric経路を使用した。mainのSAB読取は最大2sampleでAtomics.wait／busy waitなし。完成手を通常予算停止後も保持し、取消／旧世代／未完成／不正value・sequenceをブラウザmockと実Worker preflightで反証した。採用はNN／ACKを待たず、次探索は前handles／activeNN／live_searches0 ACK後。公開Actionと採用sequenceの保存publicationを照合し、receiver再選択0。Nodeは起動・外側監視・終了後保存のみで、審判／時計／全棋譜replay／数値判定はブラウザ内で実行した。RuleA共通実装を使うため、ルール実装自体に対する独立性には限界がある。

原機能7とpair296を別集計し、手NN77＋598＋665＝1340／startup18を確認。pairのWorker停止は初期clock区間によるupper<=500が286、lower>500が9、境界1。ACKwall>500は10、最大518.050ms。API開始の確実／可能402後・公開後は保存範囲では0だが、原end drift未測定／機能版Worker clock欠測7を保持する。ACKwallは計算時間ではなく、API awaitは内核命令時刻ではない。合法・期限内採用296件から原因側500ms保証を導かない。

独立109-functional-r3は07:17:40→07:17:57、public最大413.845ms／ACK最大445.945ms、手NN70／startup6、Worker停止upper<=500が7。自身の開始・終了8ping区間は交差したが、原driftを遡及補完しない。保存15 rootは固定参照11／動的自己整合4、独立7 rootは固定参照5／動的2。648bits／137NN、strict[-1,1]、P2、engine固有順、Action別prior、候補edge=sim−1／rootNN値と参照edge=sim／root=sim+1／rootQを別検査した。固定abs1e-4＋rtol1e-4を通過し、選択sampleの最大NN差3.576279e−6。全深部NN・任意finite treeの一般安全性とはしない。

失敗を保全した。r1はPlaywright入力objectのNode heap OOMでNN／public0、JSON textをbrowser内parseへ変更。r2は「ACKは公開後」とする自己checker誤認でNN／public0、完了が411ms前でも有効cacheを採用できるためそのassertだけ訂正し、次t0>=前ACK検査は保持。各予定7未実施を残す。r3の実機能7を失敗runへ付け替えない。探索・時計・SAB意味／モデル変更0。

仕様は有限成立する一方、原Worker停止9件超過と初期時計のみでは同500ms計算公平性／硬いOS期限を支持しない。SABの局面・legal・modelは専用Workerのout-of-band bindingに依存する。またsourceではSAB FAULTがlate分類を上書きし得るため、同時故障の優先順位は未実証。stampはJudge／clone／必要UTF8後だが、freeze・cancel配送・private JSON保存・継続には後続費用がある。これらを硬い公開配送保証へ外挿しない。初回無し／AI fault責任lossとbrowser timer／Judge／automation未完了の個別mockは通過し、同時事象は後続検討とする。

本文前に停止とhashafterを固定。Model drop handles／activeNN0、main timer／pending message0、inner forced controlledPID0とouter sole-root adoption／同identity wait／remaining[]を別確認。監視読取子の終了SIGTERMに伴うBEADS_READ_ERRORを保存しpause／NN negativeへ変換0。自己133 identityと原必要subset417は現在不在であり、原owner519や自然終了・全期間証明とは分母が違う。全3管理run34.507秒、観測全TID CPU2、RSS最大1,531,985,920B<3.5GiB、保存peak8,699,904B<14MiB。終了時archive込み約8.1MB、既critic128MiB内追加予約0。40ms瞬間peak、短い静的commandの全CPU／PID／RSS、背景負荷・全owner現在量は未保証。

[独立summary](../../research-data/ai-sigma/109-browser-sab-independent/independent-summary.json)、[本文前停止](../../research-data/ai-sigma/109-browser-sab-independent/runtime-source-stopped-before-report.json)、[必要証拠](../../research-data/ai-sigma/109-browser-sab-independent/109-run-evidence.tar.gz)、[復元manifest](../../research-data/ai-sigma/109-browser-sab-independent/archive-manifest.json)。archive SHA6fba76ea170c1c76e9be8b226587a24061652365d14797d25555499c17b16624、366724B／83member復元一致。原archive SHAa65f1194…6593aと必要24member、runtime13source＋モデル／Wasm前後hash不変、handoff SHA8317f94f…af3f9を照合した。

再現は現在の許可・新namespace/configで `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 SIGMA77_GIT_COMMIT=<独立Git> python3 -B tools/ai-sigma-browser-sab-independent/runner.py --config <絶対新config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <絶対driver.cjs> --config <絶対新config>`。checker初期Git979afe3、最終source/diff/hashはarchive参照。独立保存解析は終了後ブラウザ処理で、元締切経路へ追加しない。

旧Node成績／103・107の失敗／欠測は非統合。build／取得／GPU／学習／製品統合／push／委譲0。Sigma未達／旧NI未立証、true合法200／no-legal、rawview／entropy／training来歴等の未確認を保持する。109は受入れ待ち、goal／他者close0。停止→Git保存→backup/report後idle。
