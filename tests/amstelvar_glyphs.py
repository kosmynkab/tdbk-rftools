"""Real glyphs from AmstelvarA2-Roman.designspace (SIL Open Font License 1.1), rounded to
whole units. Their same-shape contours fooled the old position-only Contour order
check (issue #13)."""
from tdbk_rftools.cleanup.outlines import Contour, Outline

# won in wght400
WON_DEFAULT = Outline((
    Contour((('line', 0, 1386), ('line', 0, 1500), ('line', 524, 1500), ('line', 524, 1386), ('line', 366, 1345), ('line', 554, 801), ('line', 745, 256), ('line', 902, 673), ('line', 1072, 1169), ('line', 1134, 1004), ('line', 1005, 624), ('line', 779, -8), ('line', 664, -8), ('line', 395, 740), ('line', 168, 1347))),
    Contour((('line', 718, 1394), ('line', 718, 1500), ('line', 1252, 1500), ('line', 1252, 1394), ('line', 1084, 1353), ('line', 1257, 800), ('line', 1435, 256), ('line', 1630, 803), ('line', 1813, 1352), ('line', 1616, 1386), ('line', 1616, 1500), ('line', 2152, 1500), ('line', 2152, 1386), ('line', 1964, 1347), ('line', 1746, 760), ('line', 1471, -8), ('line', 1349, -8), ('line', 1101, 735), ('line', 886, 1355))),
    Contour((('line', 1924, 535), ('line', 1602, 535), ('line', 1602, 561), ('line', 1252, 561), ('line', 1215, 663), ('line', 1641, 663), ('line', 1641, 682), ('line', 1963, 682))),
    Contour((('line', 2013, 886), ('line', 1721, 886), ('line', 1721, 908), ('line', 1127, 908), ('line', 1090, 1015), ('line', 1761, 1015), ('line', 1761, 1034), ('line', 2061, 1034))),
    Contour((('line', 197, 535), ('line', 158, 682), ('line', 500, 682), ('line', 500, 663), ('line', 1216, 663), ('line', 1253, 561), ('line', 559, 561), ('line', 559, 535))),
    Contour((('line', 108, 886), ('line', 60, 1034), ('line', 380, 1034), ('line', 380, 1015), ('line', 1091, 1015), ('line', 1131, 908), ('line', 420, 908), ('line', 420, 886))),
))

# won in YTFI290
WON_YTFI290 = Outline((
    Contour((('line', 0, 430), ('line', 0, 544), ('line', 524, 544), ('line', 524, 430), ('line', 366, 389), ('line', 591, 222), ('line', 743, 101), ('line', 887, 214), ('line', 1053, 329), ('line', 1134, 270), ('line', 1005, 165), ('line', 779, -8), ('line', 664, -8), ('line', 395, 197), ('line', 168, 391))),
    Contour((('line', 718, 438), ('line', 718, 544), ('line', 1252, 544), ('line', 1252, 438), ('line', 1084, 397), ('line', 1262, 233), ('line', 1425, 101), ('line', 1600, 224), ('line', 1813, 396), ('line', 1616, 430), ('line', 1616, 544), ('line', 2152, 544), ('line', 2152, 430), ('line', 1964, 391), ('line', 1746, 203), ('line', 1471, -8), ('line', 1349, -8), ('line', 1101, 196), ('line', 886, 399))),
    Contour((('line', 1924, 185), ('line', 1602, 185), ('line', 1602, 211), ('line', 1253, 211), ('line', 1216, 313), ('line', 1641, 313), ('line', 1641, 332), ('line', 1963, 332))),
    Contour((('line', 2013, 185), ('line', 1721, 185), ('line', 1721, 207), ('line', 1127, 207), ('line', 1090, 314), ('line', 1761, 314), ('line', 1761, 333), ('line', 2061, 333))),
    Contour((('line', 197, 185), ('line', 158, 332), ('line', 500, 332), ('line', 500, 313), ('line', 1216, 313), ('line', 1253, 211), ('line', 559, 211), ('line', 559, 185))),
    Contour((('line', 108, 185), ('line', 60, 333), ('line', 380, 333), ('line', 380, 314), ('line', 1091, 314), ('line', 1131, 207), ('line', 420, 207), ('line', 420, 185))),
))

# o in wght400
O_DEFAULT = Outline((
    Contour((('qcurve', 64, 500), ('offcurve', 64, 717), ('offcurve', 350, 1022), ('qcurve', 582, 1022), ('offcurve', 815, 1022), ('offcurve', 1104, 737), ('qcurve', 1104, 506), ('offcurve', 1104, 290), ('offcurve', 820, -22), ('qcurve', 588, -22), ('offcurve', 355, -22), ('offcurve', 64, 267))),
    Contour((('qcurve', 244, 520), ('offcurve', 245, 339), ('offcurve', 429, 88), ('qcurve', 580, 88), ('offcurve', 742, 88), ('offcurve', 918, 317), ('qcurve', 918, 506), ('offcurve', 918, 680), ('offcurve', 734, 906), ('qcurve', 582, 906), ('offcurve', 418, 906), ('offcurve', 243, 700))),
))

# o in tuning/opsz8_wdth50
O_OPSZ8_WDTH50 = Outline((
    Contour((('qcurve', 63, 503), ('offcurve', 63, 733), ('offcurve', 341, 1026), ('qcurve', 580, 1026), ('offcurve', 822, 1026), ('offcurve', 1096, 753), ('qcurve', 1096, 509), ('offcurve', 1096, 279), ('offcurve', 823, -19), ('qcurve', 581, -19), ('offcurve', 342, -19), ('offcurve', 63, 258))),
    Contour((('qcurve', 243, 519), ('offcurve', 244, 310), ('offcurve', 426, 87), ('qcurve', 583, 87), ('offcurve', 750, 87), ('offcurve', 917, 289), ('qcurve', 917, 505), ('offcurve', 917, 708), ('offcurve', 739, 909), ('qcurve', 582, 909), ('offcurve', 412, 909), ('offcurve', 241, 727))),
))

