# quoridor-4lc.216 phase2 — learned-feature residual ridge一対照

216実23604forward/science停止と同指標残差結果を受け、主計画を更新し同課題/元総予算内の最大1低費用対照を実配分する。fresh独立test・教師・arena・LR幅sweepは保留。最大未解決点は400stepでtrainに合うがvalで移らない補正に、learned hidden情報があるのに読出し/fit方法が活かせていないのか。係数の単純縮小はalignment弱さを示してもhiddenが運ぶ関係を試さないため第二候補に保留。

選定: frozen standard400 learned representationの32hiddenを同5901trainvalで一回だけ抽出し、train-only gameequal residual eD=y-D に一つの固定ridge headを閉形式fitする。旧204randomfeatureshead/全層再学習とは区別する。対象checkpointは216既standard400 exactSHA8f95a44c...、同STM入力/同scale/同D/4653train1248val/mask。各rowweightは1/(96*n_game)、条件選定でval labelfit0。

方式は結果前固定: model.outのpre-hookでpost-ReLU hidden32を既フルforward5901の同passから得る。元standard400予測を同passで取り既perrowとmaxabs<=1e-6を有限照合、追加parityforward0。hidden各列をtrain-only gameweighted population mean/stdで中心化標準化、zero-variance列は0としてmask/係数を保存。Ridge目的sum w*(eD-intercept-Z*beta)^2 + .01*sum(beta²) (intercept非penalty) を32+1閉形式 solve、lambda.01一条件だけ・変更/sweep0。予測 clamp(D+intercept+Zbeta,-1,1) をf32仕様固定、unclipped fitとclipped評価を分ける。trainfit残差/根MSE、validationのD/旧standard400との差、同row/game/group/分解と原重みsigned寄与を保存。truez/signも別診断。有限schema/solve残差/condition number/zero列/不成立理由を保存し、失敗を別λ条件へ救済しない。

実費/所有: solewriterは216既scope、phase2専用subdir residual-head-control と新sourceで旧成功source/result/stop/preregister/Gitを上書き0。追加hiddenNN5901、総NN23604+5901=29505<=元30000、CPU2単1/torch1/RAMguard1.75GiB/jobhard60/元allheavy180内。NN0算術は元allstatic180内、Git/reportと静的時間を別記。新teacher/game/test/GPU/trainoptimizer/backward0。モデル重みimmutable/readout33新係数は分析モデル。現在16MiB reservation/14guard内でfeatures約.8MiB+compressed+source/report/Gittempを直前forecastし、旧保持unknown減額/parent追加0。512MiB rawコピー等0、必要既archive/memberのみ再用。

現在217はphase1独立算術待ち、新phaseの全稿承認をgateにしない。hypothesis独立選定見解を並行依頼するので結果前に重要指摘が届けばNN0で採否を記録し、条件変更時は旧版と新版を明示。全役承認不要。actualheavyは新current owner/PIDtick/RAM/92正frame16owned/quiet+CPU0critic短jobを直前admit。firstscience06:40/stop06:45/結果06:50/保存07:05、親期限16内。phase1pack/Git全文到着をgateにしないが科学使用source/input/model SHAは束縛する。

結論範囲: Dをtrain/valとも改善すれば、このlearned representationの低容量読出しとbaselineanchoringの有用性を再用valで支持し、情報欠如一意を認定しない。train改善だけなら、このhead/representationで残差転移不足、データ/history/teacher/分布/他readoutの競合説明を保持。いずれもval選定後独立testは別判断、higheststrength/棋力0。結果は次主配分を変える根拠、単に次案評で停止しない。現通常新counter実許可、旧further_science_authorized:falseはphase1の停止を保持する。
