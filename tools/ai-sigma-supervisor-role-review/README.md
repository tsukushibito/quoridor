# Supervisor role review transition

.61だけの単独writer用。既存専用Python環境とUV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1、CPU0、自己artifact/tmpを使用する。App Serverを起動/再起動せず、モデル/effortをoverrideしない。

実行順はoperate.py stop → edit → refresh → restart → observe。commands.jsonlとRPC原応答を保持。stopはdispatch lock下で既存scheduler stopのみ、未知ownedを拒否。refreshはdispatch/registry lock下でidle同threadへcommon+role+runtime suffixを明示適用し、registryのsupervisor定義hashのみ更新。stop/edit/refreshは冪等ではないので追加契約なしに再実行しない。未知状態は再起動せずfail-closed。

00:55UTCにscheduler/正確ownedturn停止、00:58UTCまでmonitor回収、01:00UTCまで証拠保存。後続自然turnでprompt/body一致・判断/効果点検を同ownerが確認する。今回のRPC成功/digest一致は本文読戻しや全期間成功の証明ではない。既存readguard90/120/180、周期1200、閾値2、累積12GiBを維持。
