# 99.1 データGit保存・不要生成物整理

受領03:13:05UTC、本人claim。規約3正本全文継承。研究ローカルGitのみ、他者index/主checkout/push変更0。保存commit `6710b177387f2d9f49d6509a051b8d36213a3a6f`。93/95と過去実験・独立検証の75archive:元555,563,415B→63,983,416B。設定・要約103件は直接Git。モデル/依存/全sourcecopyはarchive対象外。全8850memberをGitからstream復元し元bytesとの一致、93/95代表ファイルの実展開を確認。正式成績/失敗/採否は不変。

97実測03:16:39終了/remaining0、本人使用path/旧build不使用/新NN予定0の通知後CPU[0]で直列圧縮。既保存旧原データ7396件を整理し、Cargo cache16dir→残り旧build全体、source/lock/commandを保持した未使用旧ELF/Wasm23件121,863,247Bも削除。現在使うORT-SEARCH/final.wasmは残した。現在App Serverはcoordinator/hypothesis/critic idle、supervisor notLoaded、experiment/steward active。旧原dataのfile/map/cwd利用は読取snapshotなし、proc race9は不確実性として保持。rootは保存/復元を独立受入れ、元コピー整理を明示指示。新検証層なし。

研究artifacts allocated 2,007,863,296→302,116,864B、差1,705,746,432B。Git増分約62,996,480B＋移管working70,496,256B、計約133,492,736Bで512MiB内。差から移管分を引いた純削減概算1,572,253,696B。現97writerによる変動とsharedGitの同時commit寄与は区別、per-dir削除sumはhardlink二重計上があるので純削減と呼ばない。旧保守課金＋現在全artifacts＋既有効予約envelope＋Git＋512MiBで12GiB内の条件付き余裕1,220,721,197B、過去baseline/sharedcache欠測を維持し全面証明しない。未使用予約約400MiBは返却可能、最終値は統括会計で合わせる。

残すもの:93/95は97が03:44:25まで小読取する現在展開path、97は本人writer・Git保存担当、92は現運用。fixedmodel/license/provenance、ORT/Chromium、fixture/ort-a.outputsは共有再現入力。旧非Git source/lockは削除binaryの再生成に必要で、本課題でGit復元版を特定できないものは削除しない。その他旧dataは保存archiveから同元pathへ展開できる。93/95の参照終了後は通常担当で展開重複を削除でき、新課題不要。

短期jobは終了、self-stop.jsonを本文前保存。archive/restore peakRSS 38,490,112/25,903,104B（通信/監視合算の瞬間peakや削除子PIDは欠測、全RAM遵守へ外挿0）。99.1 source/data書込停止、最後は記録/backup/close/既active root報告だけ。92の将来停止責任を維持し未来の停止成功は未認定。NN/build/取得/対局/他者kill0。詳細はmanifest.json/restore-check.json/old-data-cleanup.json/unused-binaries-cleanup.json/capacity-after.json、再現展開commandはmanifestに記載。
