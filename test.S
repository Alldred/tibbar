# Tibbar - RISC-V instruction stream
# Assemble with: riscv64-unknown-elf-as -march=rv64gc -o test.o test.S

# Boot: 0x32e70
# Exit: 0x0

  .section .text
  .align 2
  .globl _start

  jal x0, 144  # 0x00000000
  .org 0x00000068
  csrrs x1, x0, 833  # 0x00000068
  addi x1, x1, 4  # 0x0000006c
  csrrw x0, x1, 833  # 0x00000070
  mret  # 0x00000074
  .org 0x00032e70
_start:
  addiw x1, x0, 104  # 0x00032e70
  csrrw x0, x1, 773  # 0x00032e74
  auipc x30, 992017  # 0x00032e78
  andi x4, x15, 1696  # 0x00032e7c
  auipc x12, 615336  # 0x00032e80
  lui x26, 3792  # 0x00032e84
  addiw x26, x26, 1351  # 0x00032e88
  slli x26, x26, 13  # 0x00032e8c
  addi x26, x26, 1615  # 0x00032e90
  slli x26, x26, 13  # 0x00032e94
  addi x26, x26, 765  # 0x00032e98
  slli x26, x26, 14  # 0x00032e9c
  addi x26, x26, 1786  # 0x00032ea0
  lui x3, 3792  # 0x00032ea4
  addiw x3, x3, 1351  # 0x00032ea8
  slli x3, x3, 13  # 0x00032eac
  addi x3, x3, 1615  # 0x00032eb0
  slli x3, x3, 13  # 0x00032eb4
  addi x3, x3, 765  # 0x00032eb8
  slli x3, x3, 14  # 0x00032ebc
  addi x3, x3, 1786  # 0x00032ec0
  beq x26, x3, 4  # 0x00032ec4
  lui x16, 396  # 0x00032ec8
  addiw x16, x16, -835  # 0x00032ecc
  slli x16, x16, 16  # 0x00032ed0
  addi x16, x16, -875  # 0x00032ed4
  slli x16, x16, 12  # 0x00032ed8
  addi x16, x16, -145  # 0x00032edc
  slli x16, x16, 13  # 0x00032ee0
  addi x16, x16, 1888  # 0x00032ee4
  lui x17, 396  # 0x00032ee8
  addiw x17, x17, -835  # 0x00032eec
  slli x17, x17, 16  # 0x00032ef0
  addi x17, x17, -875  # 0x00032ef4
  slli x17, x17, 12  # 0x00032ef8
  addi x17, x17, -145  # 0x00032efc
  slli x17, x17, 13  # 0x00032f00
  addi x17, x17, 1888  # 0x00032f04
  bge x16, x17, 8  # 0x00032f08
  .org 0x00032f10
  lui x26, 5092  # 0x00032f10
  addiw x26, x26, -1237  # 0x00032f14
  slli x26, x26, 13  # 0x00032f18
  addi x26, x26, -1413  # 0x00032f1c
  slli x26, x26, 12  # 0x00032f20
  addi x26, x26, 1077  # 0x00032f24
  slli x26, x26, 12  # 0x00032f28
  addi x26, x26, -1422  # 0x00032f2c
  lui x2, 5092  # 0x00032f30
  addiw x2, x2, -1237  # 0x00032f34
  slli x2, x2, 13  # 0x00032f38
  addi x2, x2, -1413  # 0x00032f3c
  slli x2, x2, 12  # 0x00032f40
  addi x2, x2, 1077  # 0x00032f44
  slli x2, x2, 12  # 0x00032f48
  addi x2, x2, -1422  # 0x00032f4c
  bge x26, x2, 8  # 0x00032f50
  .org 0x00032f58
  lui x1, 594764  # 0x00032f58
  lui x21, 809327  # 0x00032f5c
  sltiu x2, x8, 90  # 0x00032f60
  lui x3, 62144  # 0x00032f64
  slti x24, x9, 1287  # 0x00032f68
  auipc x14, 358345  # 0x00032f6c
  auipc x25, 847241  # 0x00032f70
  lui x3, 930924  # 0x00032f74
  lui x17, 32068  # 0x00032f78
  addiw x17, x17, -35  # 0x00032f7c
  slli x17, x17, 12  # 0x00032f80
  addi x17, x17, 659  # 0x00032f84
  slli x17, x17, 13  # 0x00032f88
  addi x17, x17, -563  # 0x00032f8c
  slli x17, x17, 12  # 0x00032f90
  addi x17, x17, -862  # 0x00032f94
  lui x24, 32068  # 0x00032f98
  addiw x24, x24, -35  # 0x00032f9c
  slli x24, x24, 12  # 0x00032fa0
  addi x24, x24, 659  # 0x00032fa4
  slli x24, x24, 13  # 0x00032fa8
  addi x24, x24, -563  # 0x00032fac
  slli x24, x24, 12  # 0x00032fb0
  addi x24, x24, -862  # 0x00032fb4
  bgeu x17, x24, 8  # 0x00032fb8
  .org 0x00032fc0
  lui x5, 615326  # 0x00032fc0
  lui x23, 885174  # 0x00032fc4
  lui x7, 609506  # 0x00032fc8
  lui x15, 12944  # 0x00032fcc
  addiw x15, x15, -1539  # 0x00032fd0
  slli x15, x15, 13  # 0x00032fd4
  addi x15, x15, -727  # 0x00032fd8
  slli x15, x15, 13  # 0x00032fdc
  addi x15, x15, -1525  # 0x00032fe0
  slli x15, x15, 12  # 0x00032fe4
  addi x15, x15, 828  # 0x00032fe8
  lui x4, 12944  # 0x00032fec
  addiw x4, x4, -1539  # 0x00032ff0
  slli x4, x4, 13  # 0x00032ff4
  addi x4, x4, -727  # 0x00032ff8
  slli x4, x4, 13  # 0x00032ffc
  addi x4, x4, -1525  # 0x00033000
  slli x4, x4, 12  # 0x00033004
  addi x4, x4, 828  # 0x00033008
  bge x15, x4, 4  # 0x0003300c
  auipc x26, 293750  # 0x00033010
  lui x11, 928644  # 0x00033014
  slti x24, x22, 724  # 0x00033018
  auipc x24, 414678  # 0x0003301c
  lui x2, 31267  # 0x00033020
  addiw x2, x2, 1331  # 0x00033024
  slli x2, x2, 12  # 0x00033028
  addi x2, x2, 1421  # 0x0003302c
  slli x2, x2, 12  # 0x00033030
  addi x2, x2, 1881  # 0x00033034
  slli x2, x2, 12  # 0x00033038
  addi x2, x2, 56  # 0x0003303c
  lui x28, 31267  # 0x00033040
  addiw x28, x28, 1331  # 0x00033044
  slli x28, x28, 12  # 0x00033048
  addi x28, x28, 1421  # 0x0003304c
  slli x28, x28, 12  # 0x00033050
  addi x28, x28, 1881  # 0x00033054
  slli x28, x28, 12  # 0x00033058
  addi x28, x28, 104  # 0x0003305c
  beq x2, x28, 8  # 0x00033060
  lui x23, 6536  # 0x00033064
  addiw x23, x23, 513  # 0x00033068
  slli x23, x23, 12  # 0x0003306c
  addi x23, x23, -565  # 0x00033070
  slli x23, x23, 13  # 0x00033074
  addi x23, x23, 267  # 0x00033078
  slli x23, x23, 12  # 0x0003307c
  addi x23, x23, 973  # 0x00033080
  lui x26, 6536  # 0x00033084
  addiw x26, x26, 513  # 0x00033088
  slli x26, x26, 12  # 0x0003308c
  addi x26, x26, -565  # 0x00033090
  slli x26, x26, 13  # 0x00033094
  addi x26, x26, 267  # 0x00033098
  slli x26, x26, 12  # 0x0003309c
  addi x26, x26, 1054  # 0x000330a0
  blt x23, x26, 4  # 0x000330a4
  auipc x2, 236682  # 0x000330a8
  lui x23, 2924  # 0x000330ac
  addiw x23, x23, 143  # 0x000330b0
  slli x23, x23, 12  # 0x000330b4
  addi x23, x23, 1539  # 0x000330b8
  slli x23, x23, 14  # 0x000330bc
  addi x23, x23, -1093  # 0x000330c0
  slli x23, x23, 13  # 0x000330c4
  addi x23, x23, 1888  # 0x000330c8
  lui x21, 2924  # 0x000330cc
  addiw x21, x21, 143  # 0x000330d0
  slli x21, x21, 12  # 0x000330d4
  addi x21, x21, 1539  # 0x000330d8
  slli x21, x21, 14  # 0x000330dc
  addi x21, x21, -1093  # 0x000330e0
  slli x21, x21, 13  # 0x000330e4
  addi x21, x21, 1911  # 0x000330e8
  beq x23, x21, 4  # 0x000330ec
  lui x11, 333713  # 0x000330f0
  ori x21, x23, 1845  # 0x000330f4
  auipc x24, 789853  # 0x000330f8
  slti x9, x14, -1252  # 0x000330fc
  lui x16, 343  # 0x00033100
  addiw x16, x16, 1137  # 0x00033104
  slli x16, x16, 15  # 0x00033108
  addi x16, x16, -1825  # 0x0003310c
  slli x16, x16, 13  # 0x00033110
  addi x16, x16, 17  # 0x00033114
  slli x16, x16, 12  # 0x00033118
  addi x16, x16, -25  # 0x0003311c
  lui x7, 343  # 0x00033120
  addiw x7, x7, 1137  # 0x00033124
  slli x7, x7, 15  # 0x00033128
  addi x7, x7, -1825  # 0x0003312c
  slli x7, x7, 13  # 0x00033130
  addi x7, x7, 17  # 0x00033134
  slli x7, x7, 12  # 0x00033138
  addi x7, x7, 17  # 0x0003313c
  bne x16, x7, 8  # 0x00033140
  .org 0x00033148
  andi x25, x2, 944  # 0x00033148
  lui x19, 8153  # 0x0003314c
  addiw x19, x19, -1441  # 0x00033150
  slli x19, x19, 13  # 0x00033154
  addi x19, x19, -1429  # 0x00033158
  slli x19, x19, 14  # 0x0003315c
  addi x19, x19, 1079  # 0x00033160
  slli x19, x19, 12  # 0x00033164
  addi x19, x19, -494  # 0x00033168
  lui x6, 8153  # 0x0003316c
  addiw x6, x6, -1441  # 0x00033170
  slli x6, x6, 13  # 0x00033174
  addi x6, x6, -1429  # 0x00033178
  slli x6, x6, 14  # 0x0003317c
  addi x6, x6, 1079  # 0x00033180
  slli x6, x6, 12  # 0x00033184
  addi x6, x6, -493  # 0x00033188
  bltu x19, x6, 4  # 0x0003318c
  sltiu x20, x26, -590  # 0x00033190
  auipc x2, 843366  # 0x00033194
  lui x5, 1024256  # 0x00033198
  auipc x7, 811459  # 0x0003319c
  lui x2, 549  # 0x000331a0
  addiw x2, x2, -749  # 0x000331a4
  slli x2, x2, 14  # 0x000331a8
  addi x2, x2, -67  # 0x000331ac
  slli x2, x2, 12  # 0x000331b0
  addi x2, x2, 203  # 0x000331b4
  slli x2, x2, 12  # 0x000331b8
  addi x2, x2, -40  # 0x000331bc
  lui x19, 549  # 0x000331c0
  addiw x19, x19, -749  # 0x000331c4
  slli x19, x19, 14  # 0x000331c8
  addi x19, x19, -67  # 0x000331cc
  slli x19, x19, 12  # 0x000331d0
  addi x19, x19, 203  # 0x000331d4
  slli x19, x19, 12  # 0x000331d8
  addi x19, x19, 13  # 0x000331dc
  bgeu x2, x19, 8  # 0x000331e0
  ori x17, x5, 1994  # 0x000331e4
  addi x16, x26, 674  # 0x000331e8
  lui x31, 382711  # 0x000331ec
  lui x28, 186454  # 0x000331f0
  addi x28, x21, -356  # 0x000331f4
  auipc x2, 319865  # 0x000331f8
  auipc x6, 396736  # 0x000331fc
  lui x11, 11872  # 0x00033200
  addiw x11, x11, -1453  # 0x00033204
  slli x11, x11, 12  # 0x00033208
  addi x11, x11, -1355  # 0x0003320c
  slli x11, x11, 13  # 0x00033210
  addi x11, x11, 729  # 0x00033214
  slli x11, x11, 12  # 0x00033218
  addi x11, x11, 1761  # 0x0003321c
  lui x26, 11872  # 0x00033220
  addiw x26, x26, -1453  # 0x00033224
  slli x26, x26, 12  # 0x00033228
  addi x26, x26, -1355  # 0x0003322c
  slli x26, x26, 13  # 0x00033230
  addi x26, x26, 729  # 0x00033234
  slli x26, x26, 12  # 0x00033238
  addi x26, x26, 1817  # 0x0003323c
  blt x11, x26, 8  # 0x00033240
  .org 0x00033248
  auipc x21, 615422  # 0x00033248
  lui x31, 575462  # 0x0003324c
  auipc x23, 462445  # 0x00033250
  lui x24, 5699  # 0x00033254
  addiw x24, x24, 1721  # 0x00033258
  slli x24, x24, 14  # 0x0003325c
  addi x24, x24, 723  # 0x00033260
  slli x24, x24, 13  # 0x00033264
  addi x24, x24, 1537  # 0x00033268
  slli x24, x24, 12  # 0x0003326c
  addi x24, x24, 897  # 0x00033270
  lui x31, 5699  # 0x00033274
  addiw x31, x31, 1721  # 0x00033278
  slli x31, x31, 14  # 0x0003327c
  addi x31, x31, 723  # 0x00033280
  slli x31, x31, 13  # 0x00033284
  addi x31, x31, 1537  # 0x00033288
  slli x31, x31, 12  # 0x0003328c
  addi x31, x31, 946  # 0x00033290
  beq x24, x31, 4  # 0x00033294
  lui x7, 509  # 0x00033298
  addiw x7, x7, 839  # 0x0003329c
  slli x7, x7, 13  # 0x000332a0
  addi x7, x7, -1641  # 0x000332a4
  slli x7, x7, 13  # 0x000332a8
  addi x7, x7, 727  # 0x000332ac
  slli x7, x7, 12  # 0x000332b0
  addi x7, x7, -1149  # 0x000332b4
  lui x4, 509  # 0x000332b8
  addiw x4, x4, 839  # 0x000332bc
  slli x4, x4, 13  # 0x000332c0
  addi x4, x4, -1641  # 0x000332c4
  slli x4, x4, 13  # 0x000332c8
  addi x4, x4, 727  # 0x000332cc
  slli x4, x4, 12  # 0x000332d0
  addi x4, x4, -1148  # 0x000332d4
  bge x7, x4, 8  # 0x000332d8
  lui x7, 663460  # 0x000332dc
  auipc x20, 361796  # 0x000332e0
  lui x28, 664162  # 0x000332e4
  lui x31, 8101  # 0x000332e8
  addiw x31, x31, -1053  # 0x000332ec
  slli x31, x31, 12  # 0x000332f0
  addi x31, x31, 1277  # 0x000332f4
  slli x31, x31, 12  # 0x000332f8
  addi x31, x31, 865  # 0x000332fc
  slli x31, x31, 15  # 0x00033300
  addi x31, x31, -1087  # 0x00033304
  lui x5, 8101  # 0x00033308
  addiw x5, x5, -1053  # 0x0003330c
  slli x5, x5, 12  # 0x00033310
  addi x5, x5, 1277  # 0x00033314
  slli x5, x5, 12  # 0x00033318
  addi x5, x5, 865  # 0x0003331c
  slli x5, x5, 15  # 0x00033320
  addi x5, x5, -1003  # 0x00033324
  beq x31, x5, 8  # 0x00033328
  auipc x14, 310105  # 0x0003332c
  lui x5, 493689  # 0x00033330
  slti x3, x18, -427  # 0x00033334
  ori x22, x23, -1567  # 0x00033338
  addiw x4, x15, 63  # 0x0003333c
  sltiu x27, x18, -1096  # 0x00033340
  lui x19, 247514  # 0x00033344
  addiw x22, x15, 747  # 0x00033348
  lui x19, 100  # 0x0003334c
  addiw x19, x19, -1155  # 0x00033350
  slli x19, x19, 15  # 0x00033354
  addi x19, x19, -1621  # 0x00033358
  slli x19, x19, 12  # 0x0003335c
  addi x19, x19, 321  # 0x00033360
  slli x19, x19, 14  # 0x00033364
  addi x19, x19, 615  # 0x00033368
  lui x30, 100  # 0x0003336c
  addiw x30, x30, -1155  # 0x00033370
  slli x30, x30, 15  # 0x00033374
  addi x30, x30, -1621  # 0x00033378
  slli x30, x30, 12  # 0x0003337c
  addi x30, x30, 321  # 0x00033380
  slli x30, x30, 14  # 0x00033384
  addi x30, x30, 686  # 0x00033388
  beq x19, x30, 4  # 0x0003338c
  slti x16, x23, -1319  # 0x00033390
  lui x6, 2962  # 0x00033394
  addiw x6, x6, 1463  # 0x00033398
  slli x6, x6, 12  # 0x0003339c
  addi x6, x6, 1231  # 0x000333a0
  slli x6, x6, 14  # 0x000333a4
  addi x6, x6, 945  # 0x000333a8
  slli x6, x6, 13  # 0x000333ac
  addi x6, x6, -408  # 0x000333b0
  lui x29, 2962  # 0x000333b4
  addiw x29, x29, 1463  # 0x000333b8
  slli x29, x29, 12  # 0x000333bc
  addi x29, x29, 1231  # 0x000333c0
  slli x29, x29, 14  # 0x000333c4
  addi x29, x29, 945  # 0x000333c8
  slli x29, x29, 13  # 0x000333cc
  addi x29, x29, -407  # 0x000333d0
  bne x6, x29, 4  # 0x000333d4
  lui x22, 51253  # 0x000333d8
  addiw x22, x22, -1571  # 0x000333dc
  slli x22, x22, 12  # 0x000333e0
  addi x22, x22, -1213  # 0x000333e4
  slli x22, x22, 12  # 0x000333e8
  addi x22, x22, -679  # 0x000333ec
  slli x22, x22, 12  # 0x000333f0
  addi x22, x22, -867  # 0x000333f4
  lui x17, 51253  # 0x000333f8
  addiw x17, x17, -1571  # 0x000333fc
  slli x17, x17, 12  # 0x00033400
  addi x17, x17, -1213  # 0x00033404
  slli x17, x17, 12  # 0x00033408
  addi x17, x17, -679  # 0x0003340c
  slli x17, x17, 12  # 0x00033410
  addi x17, x17, -768  # 0x00033414
  bltu x22, x17, 8  # 0x00033418
  .org 0x00033420
  auipc x21, 580108  # 0x00033420
  lui x3, 11346  # 0x00033424
  addiw x3, x3, -1565  # 0x00033428
  slli x3, x3, 12  # 0x0003342c
  addi x3, x3, -1647  # 0x00033430
  slli x3, x3, 12  # 0x00033434
  addi x3, x3, -871  # 0x00033438
  slli x3, x3, 14  # 0x0003343c
  addi x3, x3, 1812  # 0x00033440
  lui x15, 11346  # 0x00033444
  addiw x15, x15, -1565  # 0x00033448
  slli x15, x15, 12  # 0x0003344c
  addi x15, x15, -1647  # 0x00033450
  slli x15, x15, 12  # 0x00033454
  addi x15, x15, -871  # 0x00033458
  slli x15, x15, 14  # 0x0003345c
  addi x15, x15, 1812  # 0x00033460
  bge x3, x15, 4  # 0x00033464
  addi x3, x21, -185  # 0x00033468
  sltiu x13, x17, -897  # 0x0003346c
  lui x30, 850178  # 0x00033470
  lui x17, 9013  # 0x00033474
  addiw x17, x17, 1779  # 0x00033478
  slli x17, x17, 12  # 0x0003347c
  addi x17, x17, 655  # 0x00033480
  slli x17, x17, 12  # 0x00033484
  addi x17, x17, 951  # 0x00033488
  slli x17, x17, 14  # 0x0003348c
  addi x17, x17, -91  # 0x00033490
  lui x1, 9013  # 0x00033494
  addiw x1, x1, 1779  # 0x00033498
  slli x1, x1, 12  # 0x0003349c
  addi x1, x1, 655  # 0x000334a0
  slli x1, x1, 12  # 0x000334a4
  addi x1, x1, 951  # 0x000334a8
  slli x1, x1, 14  # 0x000334ac
  addi x1, x1, -90  # 0x000334b0
  bne x17, x1, 4  # 0x000334b4
  lui x1, 7691  # 0x000334b8
  addiw x1, x1, 1889  # 0x000334bc
  slli x1, x1, 13  # 0x000334c0
  addi x1, x1, 147  # 0x000334c4
  slli x1, x1, 14  # 0x000334c8
  addi x1, x1, 825  # 0x000334cc
  slli x1, x1, 12  # 0x000334d0
  addi x1, x1, -1728  # 0x000334d4
  lui x5, 7691  # 0x000334d8
  addiw x5, x5, 1889  # 0x000334dc
  slli x5, x5, 13  # 0x000334e0
  addi x5, x5, 147  # 0x000334e4
  slli x5, x5, 14  # 0x000334e8
  addi x5, x5, 825  # 0x000334ec
  slli x5, x5, 12  # 0x000334f0
  addi x5, x5, -1727  # 0x000334f4
  blt x1, x5, 8  # 0x000334f8
  .org 0x00033500
  addi x13, x24, 1741  # 0x00033500
  auipc x28, 570453  # 0x00033504
  andi x12, x25, -1568  # 0x00033508
  lui x26, 25000  # 0x0003350c
  addiw x26, x26, -1541  # 0x00033510
  slli x26, x26, 12  # 0x00033514
  addi x26, x26, 1467  # 0x00033518
  slli x26, x26, 12  # 0x0003351c
  addi x26, x26, 71  # 0x00033520
  slli x26, x26, 12  # 0x00033524
  addi x26, x26, 40  # 0x00033528
  lui x13, 25000  # 0x0003352c
  addiw x13, x13, -1541  # 0x00033530
  slli x13, x13, 12  # 0x00033534
  addi x13, x13, 1467  # 0x00033538
  slli x13, x13, 12  # 0x0003353c
  addi x13, x13, 71  # 0x00033540
  slli x13, x13, 12  # 0x00033544
  addi x13, x13, 55  # 0x00033548
  beq x26, x13, 4  # 0x0003354c
  lui x21, 326519  # 0x00033550
  lui x8, 929915  # 0x00033554
  lui x6, 1015603  # 0x00033558
  lui x15, 874608  # 0x0003355c
  lui x21, 12166  # 0x00033560
  addiw x21, x21, 625  # 0x00033564
  slli x21, x21, 14  # 0x00033568
  addi x21, x21, 907  # 0x0003356c
  slli x21, x21, 12  # 0x00033570
  addi x21, x21, -1819  # 0x00033574
  slli x21, x21, 12  # 0x00033578
  addi x21, x21, -594  # 0x0003357c
  lui x18, 12166  # 0x00033580
  addiw x18, x18, 625  # 0x00033584
  slli x18, x18, 14  # 0x00033588
  addi x18, x18, 907  # 0x0003358c
  slli x18, x18, 12  # 0x00033590
  addi x18, x18, -1819  # 0x00033594
  slli x18, x18, 12  # 0x00033598
  addi x18, x18, -543  # 0x0003359c
  beq x21, x18, 8  # 0x000335a0
  lui x15, 46878  # 0x000335a4
  addiw x15, x15, -507  # 0x000335a8
  slli x15, x15, 12  # 0x000335ac
  addi x15, x15, -337  # 0x000335b0
  slli x15, x15, 12  # 0x000335b4
  addi x15, x15, -1687  # 0x000335b8
  slli x15, x15, 12  # 0x000335bc
  addi x15, x15, 1062  # 0x000335c0
  lui x13, 46878  # 0x000335c4
  addiw x13, x13, -507  # 0x000335c8
  slli x13, x13, 12  # 0x000335cc
  addi x13, x13, -337  # 0x000335d0
  slli x13, x13, 12  # 0x000335d4
  addi x13, x13, -1687  # 0x000335d8
  slli x13, x13, 12  # 0x000335dc
  addi x13, x13, 1062  # 0x000335e0
  bge x15, x13, 4  # 0x000335e4
  lui x6, 523019  # 0x000335e8
  auipc x7, 109668  # 0x000335ec
  auipc x21, 35025  # 0x000335f0
  lui x18, 63975  # 0x000335f4
  addiw x18, x18, -3  # 0x000335f8
  slli x18, x18, 12  # 0x000335fc
  addi x18, x18, 3  # 0x00033600
  slli x18, x18, 12  # 0x00033604
  addi x18, x18, 1115  # 0x00033608
  slli x18, x18, 12  # 0x0003360c
  addi x18, x18, -1565  # 0x00033610
  lui x16, 63975  # 0x00033614
  addiw x16, x16, -3  # 0x00033618
  slli x16, x16, 12  # 0x0003361c
  addi x16, x16, 3  # 0x00033620
  slli x16, x16, 12  # 0x00033624
  addi x16, x16, 1115  # 0x00033628
  slli x16, x16, 12  # 0x0003362c
  addi x16, x16, -1479  # 0x00033630
  bne x18, x16, 4  # 0x00033634
  addiw x1, x0, 0  # 0x00033638
  jalr x0, 0(x1)  # 0x0003363c
