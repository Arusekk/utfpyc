import binascii
import marshal

actual_payload = '''
610d0d0a0000000001e20d60eb030000e30000000000000000000000000000000007000000400000
00735c00000064005a0069005a01640144005d325a0265036402830144005d245a04650565046403
1700640216006502170083016501650565046502170083013c007118710c65066404a00764056406
8400650044008301a101830101006407530029086158030000477572204d726120627320436c6775
62612c206f6c2047767a204372677265660a0a4f726e686776736879207666206f72676772652067
756e61206874796c2e0a526b637976707667207666206f72676772652067756e6120767a63797670
76672e0a46767a637972207666206f72676772652067756e612070627a6379726b2e0a50627a6379
726b207666206f72676772652067756e612070627a637976706e6772712e0a53796e67207666206f
72676772652067756e61206172666772712e0a46636e656672207666206f72676772652067756e61
2071726166722e0a45726e716e6f767976676c207062686167662e0a46637270766e7920706e6672
66206e65726127672066637270766e7920726162687475206762206f65726e782067757220656879
72662e0a4e796775626874752063656e706776706e7976676c206f726e67662063686576676c2e0a
5265656265662066756268797120617269726520636e666620667679726167796c2e0a4861797266
6620726b637976707667796c2066767972617072712e0a56612067757220736e7072206273206e7a
6f76746876676c2c20657273686672206775722067727a63676e677662612067622074687266662e
0a477572657220667562687971206f72206261722d2d206e6171206365727372656e6f796c206261
796c20626172202d2d626f6976626866206a6e6c2067622071622076672e0a4e7967756268747520
67756e67206a6e6c207a6e6c20616267206f7220626f6976626866206e6720737665666720686179
726666206c62682765722051686770752e0a41626a207666206f72676772652067756e6120617269
72652e0a4e79677562687475206172697265207666206273677261206f72676772652067756e6120
2a65767475672a2061626a2e0a56732067757220767a6379727a7261676e6776626120766620756e
657120676220726b63796e76612c2076672766206e206f6e71207671726e2e0a5673206775722076
7a6379727a7261676e6776626120766620726e666c20676220726b63796e76612c207667207a6e6c
206f72206e2074626271207671726e2e0a416e7a7266636e707266206e6572206261722075626178
766174207465726e67207671726e202d2d207972672766207162207a626572206273206775626672
212902e941000000e961000000e91a000000e90d000000da00630100000000000000000000000200
00000600000043000000731800000067007c005d107d017400a0017c017c01a102910271045300a9
002902da0164da036765742902da022e30da016372060000007206000000fa1a2f7573722f6c6962
2f707974686f6e332e392f746869732e7079da0a3c6c697374636f6d703e1c000000f30000000072
0c0000004e2908da01737207000000720a000000da0572616e6765da0169da03636872da05707269
6e74da046a6f696e720600000072060000007206000000720b000000da083c6d6f64756c653e0100
0000730a0000000416040108010c012402
535353535353
'''.replace('\n', '') # hexlified PYC file, padded to encodable length
eval(marshal.loads(binascii.unhexlify(actual_payload)[16:]))