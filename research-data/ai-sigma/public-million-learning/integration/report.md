公開Sigma original-only v2の基準runと凍結最終評価を完了した。保存T1,000,000/V50,000/E50,000行、model入力distinct366,638/32,263/32,143。43shardすべてに機会のある固定規則でoriginal前半のみを採用し、z0終了理由UNKNOWNを除外。同入力の異なる有効勝敗観測は保持し、train/validation盤面一致によるtrain削除はしなかった。game/history/過去露出UNKNOWNを未見gameへ昇格しない。

QF1+固定D logit残差H32、route4off、FP32 Adam wd0、LR3e-5、batch128、epoch shuffle、rowmonitor。20epoch/156,260更新/20,000,000seen、全train行20回、毎epoch末尾64行。229実観測点と20fulltrain観測。20epoch endpointがBEST=LAST。fulltrain rowMSE0.517122594、validation0.526443771（initial0.856605583）、gap0.009321177。epoch境界validationは低下を続け、収束・最適LR・過学習がないという認定はしない。初期trainはdiag2048でありfulltrainではない。PNG/SVGはscopeとD/定数/BESTを区別して実点のみを描画し、画像確認済みのPNG SHAを最終handoffでも再照合した。

凍結後のsealed50,000行一巡: BEST rowMSE0.529793889/D0.860192179/訓練由来定数1.000029818、BEST符号正解率0.80374・飽和0.2821。secondary入力群等重みMSE0.498099721。既知train入力35,887行MSE0.514865732、未知入力14,113行0.567753698。source43/phase3 secondaryは同forwardの保存値から集計した。legacy `games`/`game_equal`の32,143は公開model入力群で、独立game数ではない。primaryはrow平均。BEST一候補だけ、50,000modelrowforward、追加initialなし、評価後の候補再選定・再fitなし。

同BEST native資格は19状態P1/P2・16children/16inplaceundo、Scalar/Simd FT full/delta、親accumulator/history/ply復元PASS。CPUmaxerr3.13e-7、AVX2あり、headはScalar。元phase deadline失敗・numeric親directwait欠測は保持し、Root受入れ済み限定数値PASSと区別する。速度・棋力証明ではない。新private ELF、BEST/scale/config/cache/freeze bindingと完全停止receiptを添付する。

最終job ba1e4254 succeeded/exit0、whole3.278198345秒、guardian直接子wait/cleanup/remaining[]、正確科学PID/start不在。CPU2,3/RAM4/GPU0。費はlearner3600の前向き240評価namespaceへ、prep/collection<=60込み上限63.278198345秒。旧NEW120118.360786210/CPU300・compile600 UNKNOWN/旧失敗費は不変。samples8061480残。前Root容量WITHINを利用し、全域/共有target走査は再実行しなかった。optional growth guard/testと完了済み実験制御を現役sourceから撤去。raw/cache/models/predictionはignored資産、small manifest/必要圧縮証拠のみmainへRootが統合する。

変更15pathの厳密一覧/SHAはintegration-source-paths.json、成果/全費/限界/slot停止はintegration-results.jsonとfinal-stop-receipt.jsonを正本とする。source writer STOP、次sciencejobなし。main/index/ref/commitはRoot担当。参照用の旧source snapshotは未保存実行版の科学provenanceとしてignoredで保持し、現役sourceのmirror/shimとして持ち込まない。
