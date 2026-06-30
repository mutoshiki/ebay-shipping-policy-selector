from __future__ import annotations
import pandas as pd, re, json, math, statistics, os, textwrap, csv, unicodedata, hashlib
from pathlib import Path

OUT=Path('/mnt/data/film-camera-shipping-assistant')
(OUT/'data').mkdir(parents=True, exist_ok=True)

# Reference body weights compiled from published specifications and commonly cited manuals/catalogues.
# Values are used as shipping estimates; variants and included batteries/finder/back can change the actual weight.
CAMERA_TSV = r'''brand|name|weight|genre|format|focus|lens|year|condition|aliases
Nikon|Nikon F|685|35mm MF SLR|35mm|MF|interchangeable|1959|body with eye-level finder|Nikkor F
Nikon|Nikon F2|730|35mm MF SLR|35mm|MF|interchangeable|1971|body with eye-level finder|F2 Photomic
Nikon|Nikon F3|715|35mm MF SLR|35mm|MF|interchangeable|1980|body with DE-2 finder|F3HP;F3 HP
Nikon|Nikon FM|590|35mm MF SLR|35mm|MF|interchangeable|1977|body only|FM
Nikon|Nikon FM2|540|35mm MF SLR|35mm|MF|interchangeable|1982|body only|FM2n;New FM2
Nikon|Nikon FE|590|35mm MF SLR|35mm|MF|interchangeable|1978|body only|FE
Nikon|Nikon FE2|550|35mm MF SLR|35mm|MF|interchangeable|1983|body only|FE2
Nikon|Nikon FA|625|35mm MF SLR|35mm|MF|interchangeable|1983|body only|FA
Nikon|Nikon EM|460|35mm MF SLR|35mm|MF|interchangeable|1979|body only|EM
Nikon|Nikon FG|490|35mm MF SLR|35mm|MF|interchangeable|1982|body only|FG
Nikon|Nikon FG-20|440|35mm MF SLR|35mm|MF|interchangeable|1984|body only|FG20
Nikon|Nikon F-301|570|35mm MF SLR|35mm|MF|interchangeable|1985|body only|N2000
Nikon|Nikon F-501|625|35mm AF SLR|35mm|AF|interchangeable|1986|body only|N2020
Nikon|Nikon F-601|650|35mm AF SLR|35mm|AF|interchangeable|1990|body only|N6006
Nikon|Nikon F-801|695|35mm AF SLR|35mm|AF|interchangeable|1988|body only|N8008
Nikon|Nikon F90|755|35mm AF SLR|35mm|AF|interchangeable|1992|body only|N90
Nikon|Nikon F100|785|35mm AF SLR|35mm|AF|interchangeable|1999|body with batteries|F100
Nikon|Nikon F4|1090|35mm AF SLR|35mm|AF|interchangeable|1988|F4 body with MB-20|F4S;F4E
Nikon|Nikon F5|1210|35mm AF SLR|35mm|AF|interchangeable|1996|body without batteries|F5
Nikon|Nikon F6|975|35mm AF SLR|35mm|AF|interchangeable|2004|body without batteries|F6
Nikon|Nikon N80|515|35mm AF SLR|35mm|AF|interchangeable|2000|body without batteries|F80
Nikon|Nikon N75|380|35mm AF SLR|35mm|AF|interchangeable|2003|body without batteries|F75
Nikon|Nikon Nikonos V|700|Underwater film camera|35mm|MF|interchangeable|1984|body only|Nikonos 5
Nikon|Nikon S2|565|35mm interchangeable rangefinder|35mm|MF|interchangeable|1954|body only|S2
Nikon|Nikon S3|590|35mm interchangeable rangefinder|35mm|MF|interchangeable|1958|body only|S3
Nikon|Nikon SP|610|35mm interchangeable rangefinder|35mm|MF|interchangeable|1957|body only|SP
Nikon|Nikon 35Ti|310|Premium 35mm compact|35mm|AF|fixed|1993|with battery|35Ti
Nikon|Nikon 28Ti|335|Premium 35mm compact|35mm|AF|fixed|1994|with battery|28Ti
Nikon|Nikon L35AF|345|35mm AF compact|35mm|AF|fixed|1983|without batteries|Pikaichi;One Touch
Nikon|Nikon L35AD|390|35mm AF compact|35mm|AF|fixed|1983|without batteries|L35AF Date
Nikon|Nikon Lite Touch Zoom 150ED|200|35mm zoom compact|35mm|AF|fixed|2000|without battery|Lite Touch 150ED
Nikon|Nikon Pronea S|390|APS SLR|APS|AF|interchangeable|1998|body only|Pronea S
Nikon|Nikon Pronea 6i|595|APS SLR|APS|AF|interchangeable|1996|body only|Pronea 6i
Canon|Canon F-1|820|35mm MF SLR|35mm|MF|interchangeable|1971|body with eye-level finder|Old F-1
Canon|Canon New F-1|795|35mm MF SLR|35mm|MF|interchangeable|1981|body with eye-level finder|F-1N;New F1
Canon|Canon A-1|620|35mm MF SLR|35mm|MF|interchangeable|1978|body only|A1
Canon|Canon AE-1|590|35mm MF SLR|35mm|MF|interchangeable|1976|body only|AE1
Canon|Canon AE-1 Program|565|35mm MF SLR|35mm|MF|interchangeable|1981|body only|AE1 Program
Canon|Canon AV-1|490|35mm MF SLR|35mm|MF|interchangeable|1979|body only|AV1
Canon|Canon AT-1|590|35mm MF SLR|35mm|MF|interchangeable|1976|body only|AT1
Canon|Canon AL-1|490|35mm MF SLR|35mm|MF|interchangeable|1982|body only|AL1
Canon|Canon T50|490|35mm MF SLR|35mm|MF|interchangeable|1983|body only|T50
Canon|Canon T70|580|35mm MF SLR|35mm|MF|interchangeable|1984|body only|T70
Canon|Canon T90|800|35mm MF SLR|35mm|MF|interchangeable|1986|body only|T90
Canon|Canon EOS 650|660|35mm AF SLR|35mm|AF|interchangeable|1987|body only|EOS650
Canon|Canon EOS 620|700|35mm AF SLR|35mm|AF|interchangeable|1987|body only|EOS620
Canon|Canon EOS 10|625|35mm AF SLR|35mm|AF|interchangeable|1990|body only|EOS 10S
Canon|Canon EOS 100|580|35mm AF SLR|35mm|AF|interchangeable|1991|body only|Elan
Canon|Canon EOS 5|675|35mm AF SLR|35mm|AF|interchangeable|1992|body only|EOS A2;EOS A2E
Canon|Canon EOS 3|780|35mm AF SLR|35mm|AF|interchangeable|1998|body only|EOS3
Canon|Canon EOS-1|890|35mm AF SLR|35mm|AF|interchangeable|1989|body only|EOS 1
Canon|Canon EOS-1N|855|35mm AF SLR|35mm|AF|interchangeable|1994|body only|EOS 1N
Canon|Canon EOS-1V|945|35mm AF SLR|35mm|AF|interchangeable|2000|body without batteries|EOS 1V
Canon|Canon EOS 7|575|35mm AF SLR|35mm|AF|interchangeable|2000|body without batteries|Elan 7;EOS 30
Canon|Canon EOS Kiss|370|35mm AF SLR|35mm|AF|interchangeable|1993|body only|EOS 500;Rebel XS
Canon|Canon P|640|35mm interchangeable rangefinder|35mm|MF|interchangeable|1959|body only|Canon P
Canon|Canon 7|620|35mm interchangeable rangefinder|35mm|MF|interchangeable|1961|body only|Canon Seven
Canon|Canon VI-L|620|35mm interchangeable rangefinder|35mm|MF|interchangeable|1958|body only|VI-L
Canon|Canonet QL17 G-III|620|35mm fixed-lens rangefinder|35mm|MF|fixed|1972|with battery|QL17 GIII;Canonet GIII
Canon|Canonet QL19|620|35mm fixed-lens rangefinder|35mm|MF|fixed|1965|body with fixed lens|QL19
Canon|Canon AF35M|405|35mm AF compact|35mm|AF|fixed|1979|without batteries|Autoboy;Sure Shot
Canon|Canon Autoboy 2|300|35mm AF compact|35mm|AF|fixed|1983|without batteries|AF35M II;Sure Shot 2
Canon|Canon Autoboy 3|315|35mm AF compact|35mm|AF|fixed|1986|without batteries|Sure Shot Supreme
Canon|Canon AF35ML|440|35mm AF compact|35mm|AF|fixed|1981|without batteries|Super Sure Shot
Canon|Canon Prima Mini|160|35mm AF compact|35mm|AF|fixed|1992|without battery|Autoboy F;Sure Shot M
Canon|Canon IXUS L-1|180|APS compact|APS|AF|fixed|1997|without battery|IXY 10;ELPH 10
Pentax|Pentax Spotmatic|621|35mm MF SLR|35mm|MF|interchangeable|1964|body only|Spotmatic SP
Pentax|Pentax Spotmatic F|625|35mm MF SLR|35mm|MF|interchangeable|1973|body only|SPF
Pentax|Pentax K1000|620|35mm MF SLR|35mm|MF|interchangeable|1976|body only|K1000
Pentax|Pentax KM|622|35mm MF SLR|35mm|MF|interchangeable|1975|body only|KM
Pentax|Pentax KX|631|35mm MF SLR|35mm|MF|interchangeable|1975|body only|KX
Pentax|Pentax MX|495|35mm MF SLR|35mm|MF|interchangeable|1976|body only|MX
Pentax|Pentax ME|460|35mm MF SLR|35mm|MF|interchangeable|1976|body only|ME
Pentax|Pentax ME Super|460|35mm MF SLR|35mm|MF|interchangeable|1979|body only|ME Super
Pentax|Pentax LX|570|35mm MF SLR|35mm|MF|interchangeable|1980|body only|LX
Pentax|Pentax Super A|490|35mm MF SLR|35mm|MF|interchangeable|1983|body only|Super Program
Pentax|Pentax Program A|520|35mm MF SLR|35mm|MF|interchangeable|1984|body only|Program Plus
Pentax|Pentax P30|500|35mm MF SLR|35mm|MF|interchangeable|1985|body only|P3
Pentax|Pentax Z-1|650|35mm AF SLR|35mm|AF|interchangeable|1991|body only|PZ-1
Pentax|Pentax MZ-5|400|35mm AF SLR|35mm|AF|interchangeable|1995|body only|ZX-5
Pentax|Pentax MZ-S|520|35mm AF SLR|35mm|AF|interchangeable|2001|body only|MZ-S
Pentax|Pentax PC35AF|305|35mm AF compact|35mm|AF|fixed|1982|without batteries|PC35AF
Pentax|Pentax Espio Mini|190|Premium 35mm compact|35mm|AF|fixed|1994|without battery|UC-1
Pentax|Pentax Auto 110|172|110 SLR|110|MF|interchangeable|1978|body only|Auto110
Pentax|Pentax 645|1280|Medium-format SLR|120|MF|interchangeable|1984|body without lens|645
Pentax|Pentax 645N|1280|Medium-format SLR|120|AF|interchangeable|1997|body without lens|645N
Pentax|Pentax 67|1660|Medium-format SLR|120|MF|interchangeable|1969|body with prism, without lens|6x7;Pentax 6x7
Pentax|Pentax 67II|1210|Medium-format SLR|120|MF|interchangeable|1998|body without lens|67 II
Olympus|Olympus OM-1|510|35mm MF SLR|35mm|MF|interchangeable|1972|body only|OM1
Olympus|Olympus OM-2|520|35mm MF SLR|35mm|MF|interchangeable|1975|body only|OM2
Olympus|Olympus OM-3|510|35mm MF SLR|35mm|MF|interchangeable|1983|body only|OM3
Olympus|Olympus OM-4|540|35mm MF SLR|35mm|MF|interchangeable|1983|body only|OM4
Olympus|Olympus OM-10|430|35mm MF SLR|35mm|MF|interchangeable|1979|body only|OM10
Olympus|Olympus OM-20|450|35mm MF SLR|35mm|MF|interchangeable|1983|body only|OM-G
Olympus|Olympus OM-30|430|35mm MF SLR|35mm|MF|interchangeable|1982|body only|OM-F
Olympus|Olympus OM-40|460|35mm MF SLR|35mm|MF|interchangeable|1985|body only|OM-PC
Olympus|Olympus Pen F|560|Half-frame SLR|35mm half-frame|MF|interchangeable|1963|body only|Pen F
Olympus|Olympus Pen FT|600|Half-frame SLR|35mm half-frame|MF|interchangeable|1966|body only|Pen FT
Olympus|Olympus 35 SP|600|35mm fixed-lens rangefinder|35mm|MF|fixed|1969|with fixed lens|35SP
Olympus|Olympus 35 RC|410|35mm fixed-lens rangefinder|35mm|MF|fixed|1970|with fixed lens|35RC
Olympus|Olympus XA|225|Premium 35mm compact|35mm|MF|fixed|1979|with batteries|XA
Olympus|Olympus XA2|200|35mm compact MF|35mm|zone|fixed|1980|with batteries|XA2
Olympus|Olympus XA4|230|35mm compact MF|35mm|zone|fixed|1985|with batteries|XA4
Olympus|Olympus mju|170|35mm AF compact|35mm|AF|fixed|1991|without battery|Stylus;µ[mju:]
Olympus|Olympus mju II|135|Premium 35mm compact|35mm|AF|fixed|1997|without battery|Stylus Epic;Mju 2
Minolta|Minolta SRT-101|705|35mm MF SLR|35mm|MF|interchangeable|1966|body only|SR-T 101
Minolta|Minolta SRT-102|705|35mm MF SLR|35mm|MF|interchangeable|1973|body only|SR-T 102
Minolta|Minolta XE-7|750|35mm MF SLR|35mm|MF|interchangeable|1974|body only|XE-1
Minolta|Minolta XD-11|560|35mm MF SLR|35mm|MF|interchangeable|1977|body only|XD;XD-7
Minolta|Minolta XG-M|515|35mm MF SLR|35mm|MF|interchangeable|1981|body only|XG-M
Minolta|Minolta X-700|505|35mm MF SLR|35mm|MF|interchangeable|1981|body only|X700
Minolta|Minolta X-570|480|35mm MF SLR|35mm|MF|interchangeable|1983|body only|X-500
Minolta|Minolta X-370|470|35mm MF SLR|35mm|MF|interchangeable|1984|body only|X-300
Minolta|Minolta Maxxum 7000|555|35mm AF SLR|35mm|AF|interchangeable|1985|body only|Dynax 7000;Alpha 7000
Minolta|Minolta Maxxum 9000|645|35mm AF SLR|35mm|AF|interchangeable|1985|body only|Dynax 9000
Minolta|Minolta Alpha 7|575|35mm AF SLR|35mm|AF|interchangeable|2000|body without batteries|Dynax 7;Maxxum 7
Minolta|Minolta Alpha 9|910|35mm AF SLR|35mm|AF|interchangeable|1998|body without batteries|Dynax 9;Maxxum 9
Minolta|Minolta Dynax 5|335|35mm AF SLR|35mm|AF|interchangeable|2001|body only|Maxxum 5;Alpha Sweet II
Minolta|Minolta CLE|375|35mm interchangeable rangefinder|35mm|MF|interchangeable|1981|body only|CLE
Minolta|Minolta Hi-Matic 7SII|460|35mm fixed-lens rangefinder|35mm|MF|fixed|1977|with fixed lens|HiMatic 7SII
Minolta|Minolta TC-1|185|Premium 35mm compact|35mm|AF|fixed|1996|without battery|TC1
Minolta|Minolta AF-C|220|35mm AF compact|35mm|AF|fixed|1983|without batteries|AF-C
Minolta|Minolta 110 Zoom SLR|430|110 SLR|110|MF|fixed|1976|with fixed lens|110 Zoom
Leica|Leica M3|580|35mm interchangeable rangefinder|35mm|MF|interchangeable|1954|body only|M3
Leica|Leica M2|560|35mm interchangeable rangefinder|35mm|MF|interchangeable|1957|body only|M2
Leica|Leica M4|560|35mm interchangeable rangefinder|35mm|MF|interchangeable|1967|body only|M4
Leica|Leica M5|700|35mm interchangeable rangefinder|35mm|MF|interchangeable|1971|body only|M5
Leica|Leica M4-P|520|35mm interchangeable rangefinder|35mm|MF|interchangeable|1980|body only|M4P
Leica|Leica M6|560|35mm interchangeable rangefinder|35mm|MF|interchangeable|1984|body only|M6 Classic;M6 TTL
Leica|Leica M7|610|35mm interchangeable rangefinder|35mm|MF|interchangeable|2002|body with battery|M7
Leica|Leica MP|585|35mm interchangeable rangefinder|35mm|MF|interchangeable|2003|body with battery|MP
Leica|Leica CL|365|35mm interchangeable rangefinder|35mm|MF|interchangeable|1973|body only|Leitz Minolta CL
Leica|Leica Minilux|330|Premium 35mm compact|35mm|AF|fixed|1995|with battery|Minilux
Leica|Leica CM|300|Premium 35mm compact|35mm|AF|fixed|2004|with battery|CM
Leica|Leica Mini II|160|35mm AF compact|35mm|AF|fixed|1993|without battery|Mini 2
Contax|Contax RTS|700|35mm MF SLR|35mm|MF|interchangeable|1975|body only|RTS
Contax|Contax RTS II|735|35mm MF SLR|35mm|MF|interchangeable|1982|body only|RTS II
Contax|Contax RTS III|1150|35mm MF SLR|35mm|MF|interchangeable|1990|body only|RTS III
Contax|Contax 139 Quartz|500|35mm MF SLR|35mm|MF|interchangeable|1979|body only|139Q
Contax|Contax 167MT|620|35mm MF SLR|35mm|MF|interchangeable|1986|body only|167 MT
Contax|Contax Aria|460|35mm MF SLR|35mm|MF|interchangeable|1998|body only|Aria
Contax|Contax RX|810|35mm MF SLR|35mm|MF|interchangeable|1994|body only|RX
Contax|Contax AX|1080|35mm AF SLR|35mm|AF|interchangeable|1996|body only|AX
Contax|Contax G1|460|35mm interchangeable rangefinder|35mm|AF|interchangeable|1994|body only|G1
Contax|Contax G2|560|35mm interchangeable rangefinder|35mm|AF|interchangeable|1996|body only|G2
Contax|Contax T2|295|Premium 35mm compact|35mm|AF|fixed|1991|with battery|T2
Contax|Contax T3|230|Premium 35mm compact|35mm|AF|fixed|2001|with battery|T3
Contax|Contax TVS|375|Premium 35mm compact|35mm|AF|fixed|1993|with battery|TVS
Contax|Contax Tix|365|APS compact|APS|AF|fixed|1997|with battery|Tix
Konica|Konica Autoreflex T3|750|35mm MF SLR|35mm|MF|interchangeable|1973|body only|T3
Konica|Konica Autoreflex T4|530|35mm MF SLR|35mm|MF|interchangeable|1978|body only|T4
Konica|Konica TC|490|35mm MF SLR|35mm|MF|interchangeable|1976|body only|Autoreflex TC
Konica|Konica FS-1|665|35mm MF SLR|35mm|MF|interchangeable|1979|body only|FS1
Konica|Konica FT-1|720|35mm MF SLR|35mm|MF|interchangeable|1983|body only|FT1
Konica|Konica Hexar AF|495|Premium 35mm compact|35mm|AF|fixed|1993|with battery|Hexar
Konica|Konica Hexar RF|560|35mm interchangeable rangefinder|35mm|MF|interchangeable|1999|body with batteries|Hexar RF
Konica|Konica Big Mini BM-201|180|35mm AF compact|35mm|AF|fixed|1990|without battery|Big Mini
Konica|Konica A4|230|35mm AF compact|35mm|AF|fixed|1989|without battery|Big Mini A4
Yashica|Yashica FX-3|450|35mm MF SLR|35mm|MF|interchangeable|1979|body only|FX3;FX-3 Super 2000
Yashica|Yashica FX-D Quartz|455|35mm MF SLR|35mm|MF|interchangeable|1980|body only|FX-D
Yashica|Yashica FR I|660|35mm MF SLR|35mm|MF|interchangeable|1977|body only|FR1
Yashica|Yashica Electro AX|740|35mm MF SLR|35mm|MF|interchangeable|1972|body only|Electro AX
Yashica|Yashica Electro 35 GSN|750|35mm fixed-lens rangefinder|35mm|MF|fixed|1973|with fixed lens|Electro 35
Yashica|Yashica Electro 35 GX|580|35mm fixed-lens rangefinder|35mm|MF|fixed|1975|with fixed lens|Electro GX
Yashica|Yashica T4|170|Premium 35mm compact|35mm|AF|fixed|1990|without battery|T4 Super;T4 Safari
Yashica|Yashica T5|200|Premium 35mm compact|35mm|AF|fixed|1995|without battery|T5
Ricoh|Ricoh GR1|175|Premium 35mm compact|35mm|AF|fixed|1996|with battery|GR1s;GR1v
Ricoh|Ricoh R1|145|35mm AF compact|35mm|AF|fixed|1994|with battery|R1
Ricoh|Ricoh FF-90|300|35mm AF compact|35mm|AF|fixed|1988|without batteries|FF90
Ricoh|Ricoh XR-7|570|35mm MF SLR|35mm|MF|interchangeable|1980|body only|XR7
Voigtlander|Voigtlander Bessa R|395|35mm interchangeable rangefinder|35mm|MF|interchangeable|2000|body only|Bessa-R
Voigtlander|Voigtlander Bessa R2|430|35mm interchangeable rangefinder|35mm|MF|interchangeable|2002|body only|Bessa R2
Voigtlander|Voigtlander Bessa R3A|430|35mm interchangeable rangefinder|35mm|MF|interchangeable|2004|body only|Bessa R3A
Voigtlander|Voigtlander Bessa R4A|440|35mm interchangeable rangefinder|35mm|MF|interchangeable|2006|body only|Bessa R4A
Rollei|Rollei 35|370|35mm compact MF|35mm|MF|fixed|1966|with battery|Rollei 35T
Rollei|Rollei 35S|350|35mm compact MF|35mm|MF|fixed|1974|with battery|35 S
Rollei|Rolleiflex 2.8F|1220|Twin-lens reflex|120|MF|fixed|1960|camera with fixed lenses|2.8F
Rollei|Rolleiflex 3.5F|1200|Twin-lens reflex|120|MF|fixed|1958|camera with fixed lenses|3.5F
Rollei|Rolleicord V|920|Twin-lens reflex|120|MF|fixed|1954|camera with fixed lenses|Rolleicord V
Mamiya|Mamiya RB67 Pro S|2690|Medium-format SLR|120|MF|interchangeable|1974|standard kit with 90mm lens, finder and back|RB67
Mamiya|Mamiya RZ67 Pro II|2490|Medium-format SLR|120|MF|interchangeable|1993|body, finder and back without lens|RZ67
Mamiya|Mamiya 645 1000S|1300|Medium-format SLR|120|MF|interchangeable|1976|standard body with finder and insert, no lens|645 1000S
Mamiya|Mamiya 645 Super|1100|Medium-format SLR|120|MF|interchangeable|1985|body with finder and back, no lens|645 Super
Mamiya|Mamiya 645 Pro|1100|Medium-format SLR|120|MF|interchangeable|1992|body with finder and back, no lens|645 Pro
Mamiya|Mamiya 645AF|1340|Medium-format SLR|120|AF|interchangeable|1999|body without lens|645 AF
Mamiya|Mamiya 6|900|Medium-format rangefinder|120|MF|interchangeable|1989|body without lens|Mamiya Six New
Mamiya|Mamiya 7|920|Medium-format rangefinder|120|MF|interchangeable|1995|body without lens|Mamiya 7II
Mamiya|Mamiya C220|1540|Twin-lens reflex|120|MF|interchangeable|1968|body with standard 80mm lens|C220
Mamiya|Mamiya C330|1700|Twin-lens reflex|120|MF|interchangeable|1969|body with standard 80mm lens|C330
Bronica|Bronica ETRSi|1500|Medium-format SLR|120|MF|interchangeable|1989|standard kit with finder, back and 75mm lens|ETRSi
Bronica|Bronica SQ-A|1500|Medium-format SLR|120|MF|interchangeable|1982|standard kit with finder, back and 80mm lens|SQ-A
Bronica|Bronica GS-1|1800|Medium-format SLR|120|MF|interchangeable|1983|standard kit with finder, back and 100mm lens|GS1
Bronica|Bronica RF645|1000|Medium-format rangefinder|120|MF|interchangeable|2000|body without lens|RF645
Hasselblad|Hasselblad 500C/M|1370|Medium-format SLR|120|MF|interchangeable|1970|standard kit with finder, back and 80mm lens|500CM
Hasselblad|Hasselblad 503CW|1510|Medium-format SLR|120|MF|interchangeable|1996|standard kit with finder, back and 80mm lens|503 CW
Hasselblad|Hasselblad 501C/M|1370|Medium-format SLR|120|MF|interchangeable|1997|standard kit with finder, back and 80mm lens|501CM
Fujifilm|Fujifilm GA645|815|Medium-format rangefinder|120|AF|fixed|1995|with fixed lens and batteries|Fuji GA645
Fujifilm|Fujifilm GA645i|815|Medium-format rangefinder|120|AF|fixed|1997|with fixed lens and batteries|Fuji GA645i
Fujifilm|Fujifilm GS645S|645|Medium-format rangefinder|120|MF|fixed|1984|with fixed lens|Fuji GS645S
Fujifilm|Fujifilm GS645W|820|Medium-format rangefinder|120|MF|fixed|1983|with fixed lens|Fuji GS645W
Fujifilm|Fujifilm GW690III|1510|Medium-format rangefinder|120|MF|fixed|1992|with fixed lens|Fuji GW690 III
Fujifilm|Fujifilm GSW690III|1480|Medium-format rangefinder|120|MF|fixed|1992|with fixed lens|Fuji GSW690 III
Fujifilm|Fujifilm Klasse|270|Premium 35mm compact|35mm|AF|fixed|2001|with battery|Fuji Klasse
Fujifilm|Fujifilm Klasse W|265|Premium 35mm compact|35mm|AF|fixed|2006|with battery|Fuji Klasse W
Fujifilm|Fujifilm Natura S|195|Premium 35mm compact|35mm|AF|fixed|2001|with battery|Natura S
Fujifilm|Fujifilm Natura Classica|225|Premium 35mm compact|35mm|AF|fixed|2004|with battery|Natura Classica
Fujifilm|Fujifilm Cardia Mini Tiara|155|35mm AF compact|35mm|AF|fixed|1994|with battery|Tiara;DL Super Mini
Hasselblad|Hasselblad XPan|720|Panoramic film camera|35mm panorama|MF|interchangeable|1998|body without lens|Fujifilm TX-1;XPan II
Plaubel|Plaubel Makina 67|1350|Medium-format rangefinder|120|MF|fixed|1979|with fixed lens|Makina 67
Yashica|Yashica Mat-124G|1100|Twin-lens reflex|120|MF|fixed|1970|camera with fixed lenses|Mat 124G
Minolta|Minolta Autocord|960|Twin-lens reflex|120|MF|fixed|1955|camera with fixed lenses|Autocord
Ricoh|Ricohflex VII|800|Twin-lens reflex|120|MF|fixed|1954|camera with fixed lenses|Ricohflex
Polaroid|Polaroid SX-70|790|Instant camera|SX-70|MF|fixed|1972|camera without film pack|SX70
Polaroid|Polaroid 600 OneStep|600|Instant camera|600|fixed|fixed|1981|camera without film pack|OneStep 600
Polaroid|Polaroid Spectra|650|Instant camera|Spectra|AF|fixed|1986|camera without film pack|Image System
Fujifilm|Fujifilm Instax Mini 90|296|Instant camera|Instax Mini|AF|fixed|2013|with battery, no film|Instax Mini 90 Neo Classic
Fujifilm|Fujifilm Instax Wide 300|612|Instant camera|Instax Wide|AF|fixed|2014|without batteries and film|Instax Wide 300
Holga|Holga 120N|200|Toy camera|120|fixed|fixed|1982|camera without film|Holga
Lomography|Lomography Diana F+|350|Toy camera|120|fixed|fixed|2007|camera without flash|Diana F Plus
Kodak|Kodak Brownie Hawkeye|560|Box camera|620|fixed|fixed|1949|camera only|Brownie Hawkeye Flash
Kodak|Kodak Retina IIIC|680|35mm fixed-lens rangefinder|35mm|MF|fixed|1958|with fixed lens|Retina IIIc
Zeiss Ikon|Zeiss Ikon Super Ikonta 532/16|780|Medium-format folding camera|120|MF|fixed|1938|with fixed lens|Super Ikonta
Agfa|Agfa Isolette III|620|Medium-format folding camera|120|MF|fixed|1950|with fixed lens|Isolette III
Graflex|Graflex Crown Graphic 4x5|2300|Large-format camera|4x5|MF|interchangeable|1947|camera with standard lens and holder|Crown Graphic
Intrepid|Intrepid 4x5|1200|Large-format camera|4x5|MF|interchangeable|2014|camera body only|Intrepid 4x5
'''

ACCESSORY_TSV = r'''brand|name|weight|genre|format|focus|lens|year|condition|aliases
Nikon|Nikon AR-2 Cable Release|20|Cable release|accessory|||1960|reference weight|AR-2;AR2
Nikon|Nikon AR-3 Cable Release|15|Cable release|accessory|||1970|reference weight|AR-3;AR3
Nikon|Nikon AS-1 Flash Unit Coupler|25|Flash adapter|accessory|||1970|reference weight|AS-1;AS1
Nikon|Nikon DG-2 Eyepiece Magnifier|65|Finder accessory|accessory|||1970|reference weight|DG-2;DG2
Nikon|Nikon DR-3 Right Angle Finder|150|Finder accessory|accessory|||1970|reference weight|DR-3;DR3
Nikon|Nikon DR-4 Right Angle Finder|170|Finder accessory|accessory|||1980|reference weight|DR-4;DR4
Nikon|Nikon MD-4 Motor Drive|480|Motor drive / winder|accessory|||1980|without batteries|MD-4;MD4
Nikon|Nikon MD-12 Motor Drive|410|Motor drive / winder|accessory|||1980|without batteries|MD-12;MD12
Nikon|Nikon DW-3 Waist-Level Finder|190|Interchangeable finder|accessory|||1980|reference weight|DW-3;DW3
Nikon|Nikon DW-4 6x High-Magnification Finder|380|Interchangeable finder|accessory|||1980|reference weight|DW-4;DW4
Nikon|Nikon DA-2 Action Finder|375|Interchangeable finder|accessory|||1980|reference weight|DA-2;DA2
Nikon|Nikon SB-15 Speedlight|185|Flash|accessory|||1982|without batteries|SB-15;SB15
Nikon|Nikon SB-16A Speedlight|485|Flash|accessory|||1983|without batteries|SB-16A;SB16A
Nikon|Nikon SB-20 Speedlight|250|Flash|accessory|||1986|without batteries|SB-20;SB20
Nikon|Nikon SB-24 Speedlight|390|Flash|accessory|||1988|without batteries|SB-24;SB24
Nikon|Nikon SB-28 Speedlight|320|Flash|accessory|||1997|without batteries|SB-28;SB28
Nikon|Nikon SB-800 Speedlight|350|Flash|accessory|||2003|without batteries|SB-800;SB800
Canon|Canon Power Winder A|300|Motor drive / winder|accessory|||1976|without batteries|Power Winder A
Canon|Canon Motor Drive MA|705|Motor drive / winder|accessory|||1978|without batteries|Motor Drive MA
Canon|Canon Speedlite 155A|190|Flash|accessory|||1976|without batteries|155A
Canon|Canon Speedlite 199A|310|Flash|accessory|||1978|without batteries|199A
Canon|Canon Speedlite 300TL|370|Flash|accessory|||1986|without batteries|300TL
Canon|Canon Speedlite 430EZ|350|Flash|accessory|||1989|without batteries|430EZ
Minolta|Minolta Auto Winder G|220|Motor drive / winder|accessory|||1980|without batteries|Auto Winder G
Minolta|Minolta Motor Drive 1|355|Motor drive / winder|accessory|||1977|without batteries|Motor Drive 1
Minolta|Minolta Program Flash 360PX|315|Flash|accessory|||1981|without batteries|360PX
Pentax|Pentax Winder ME II|250|Motor drive / winder|accessory|||1980|without batteries|Winder ME II
Pentax|Pentax Motor Drive LX|480|Motor drive / winder|accessory|||1980|without batteries|Motor Drive LX
Pentax|Pentax AF280T Flash|240|Flash|accessory|||1980|without batteries|AF280T
Olympus|Olympus Winder 2|210|Motor drive / winder|accessory|||1978|without batteries|Winder 2
Olympus|Olympus Motor Drive 2|320|Motor drive / winder|accessory|||1983|without batteries|Motor Drive 2
Olympus|Olympus T32 Flash|260|Flash|accessory|||1975|without batteries|T32
Nikon|Nikkor 50mm f/1.8 AI-S|145|35mm manual-focus lens|35mm|MF|lens|1981|lens only, without caps|50 1.8 AIS;Pancake Nikkor
Nikon|Nikkor 50mm f/1.4 AI-S|250|35mm manual-focus lens|35mm|MF|lens|1981|lens only, without caps|50 1.4 AIS
Nikon|Nikkor 35mm f/2 AI-S|280|35mm manual-focus lens|35mm|MF|lens|1981|lens only, without caps|35 2 AIS
Nikon|Nikkor 28mm f/2.8 AI-S|250|35mm manual-focus lens|35mm|MF|lens|1981|lens only, without caps|28 2.8 AIS
Nikon|AF Nikkor 35mm f/2D|205|35mm autofocus lens|35mm|AF|lens|1989|lens only, without caps|AF 35 2D
Nikon|AF Nikkor 50mm f/1.8D|155|35mm autofocus lens|35mm|AF|lens|2002|lens only, without caps|AF 50 1.8D
Nikon|AF Nikkor 50mm f/1.4D|230|35mm autofocus lens|35mm|AF|lens|1995|lens only, without caps|AF 50 1.4D
Nikon|AF Nikkor 85mm f/1.8D|380|35mm autofocus lens|35mm|AF|lens|1994|lens only, without caps|AF 85 1.8D
Nikon|AF Nikkor 35-70mm f/2.8D|665|35mm autofocus zoom lens|35mm|AF|lens|1992|lens only, without caps|35-70 2.8D
Nikon|AF Nikkor 70-300mm f/4-5.6D ED|505|35mm autofocus zoom lens|35mm|AF|lens|1998|lens only, without caps|70-300 ED
Canon|Canon FD 50mm f/1.8|170|35mm manual-focus lens|35mm|MF|lens|1979|lens only, without caps|New FD 50 1.8
Canon|Canon FD 50mm f/1.4|235|35mm manual-focus lens|35mm|MF|lens|1979|lens only, without caps|New FD 50 1.4
Canon|Canon FD 35mm f/2.8|165|35mm manual-focus lens|35mm|MF|lens|1979|lens only, without caps|New FD 35 2.8
Canon|Canon FD 28mm f/2.8|170|35mm manual-focus lens|35mm|MF|lens|1979|lens only, without caps|New FD 28 2.8
Canon|Canon EF 50mm f/1.8 II|130|35mm autofocus lens|35mm|AF|lens|1990|lens only, without caps|EF 50 1.8 II
Canon|Canon EF 50mm f/1.4 USM|290|35mm autofocus lens|35mm|AF|lens|1993|lens only, without caps|EF 50 1.4
Canon|Canon EF 28-80mm f/3.5-5.6 II|200|35mm autofocus zoom lens|35mm|AF|lens|1993|lens only, without caps|EF 28-80
Canon|Canon EF 70-200mm f/4L USM|705|35mm autofocus zoom lens|35mm|AF|lens|1999|lens only, without caps|70-200 f4L
Minolta|Minolta MD Rokkor 50mm f/1.7|185|35mm manual-focus lens|35mm|MF|lens|1978|lens only, without caps|MD 50 1.7
Minolta|Minolta MD Rokkor 50mm f/1.4|235|35mm manual-focus lens|35mm|MF|lens|1978|lens only, without caps|MD 50 1.4
Minolta|Minolta MD Rokkor 45mm f/2|125|35mm manual-focus lens|35mm|MF|lens|1978|lens only, without caps|MD 45 2
Minolta|Minolta AF 50mm f/1.7|185|35mm autofocus lens|35mm|AF|lens|1985|lens only, without caps|Maxxum 50 1.7
Pentax|SMC Pentax-M 50mm f/1.7|185|35mm manual-focus lens|35mm|MF|lens|1977|lens only, without caps|Pentax M 50 1.7
Pentax|SMC Pentax-M 50mm f/1.4|235|35mm manual-focus lens|35mm|MF|lens|1977|lens only, without caps|Pentax M 50 1.4
Pentax|SMC Pentax-M 28mm f/2.8|156|35mm manual-focus lens|35mm|MF|lens|1977|lens only, without caps|Pentax M 28 2.8
Olympus|Olympus Zuiko 50mm f/1.8|170|35mm manual-focus lens|35mm|MF|lens|1972|lens only, without caps|OM 50 1.8
Olympus|Olympus Zuiko 50mm f/1.4|230|35mm manual-focus lens|35mm|MF|lens|1972|lens only, without caps|OM 50 1.4
Olympus|Olympus Zuiko 35mm f/2.8|180|35mm manual-focus lens|35mm|MF|lens|1972|lens only, without caps|OM 35 2.8
Olympus|Olympus Zuiko 28mm f/2.8|170|35mm manual-focus lens|35mm|MF|lens|1972|lens only, without caps|OM 28 2.8
Contax|Carl Zeiss Planar 50mm f/1.7 C/Y|190|35mm manual-focus lens|35mm|MF|lens|1975|lens only, without caps|Planar 50 1.7
Contax|Carl Zeiss Planar 50mm f/1.4 C/Y|275|35mm manual-focus lens|35mm|MF|lens|1975|lens only, without caps|Planar 50 1.4
Leica|Leica Summicron-M 50mm f/2|240|Rangefinder lens|35mm|MF|lens|1979|lens only, without caps|Summicron 50
Leica|Leica Summicron-M 35mm f/2 ASPH|255|Rangefinder lens|35mm|MF|lens|1996|lens only, without caps|Summicron 35 ASPH
Leica|Leica Elmarit-M 28mm f/2.8|180|Rangefinder lens|35mm|MF|lens|1979|lens only, without caps|Elmarit 28
Fujifilm|Fujinon GF 80mm f/3.5 for GA645|0|Built-in lens reference|120|AF|fixed|1995|included in camera weight|GA645 lens
Mamiya|Mamiya Sekor C 90mm f/3.8 RB|790|Medium-format lens|120|MF|lens|1974|lens only, without caps|RB67 90mm
Mamiya|Mamiya Sekor Z 110mm f/2.8 RZ|610|Medium-format lens|120|MF|lens|1982|lens only, without caps|RZ67 110mm
Mamiya|Mamiya Sekor C 80mm f/2.8 645|310|Medium-format lens|120|MF|lens|1975|lens only, without caps|Mamiya 645 80mm
Bronica|Zenzanon PE 75mm f/2.8|460|Medium-format lens|120|MF|lens|1980|lens only, without caps|ETR 75mm
Bronica|Zenzanon PS 80mm f/2.8|490|Medium-format lens|120|MF|lens|1982|lens only, without caps|SQ 80mm
Hasselblad|Carl Zeiss Planar 80mm f/2.8 CF|510|Medium-format lens|120|MF|lens|1982|lens only, without caps|Hasselblad 80mm
Pentax|SMC Pentax 67 105mm f/2.4|590|Medium-format lens|120|MF|lens|1969|lens only, without caps|Pentax 67 105mm
Generic|35mm body cap|12|Cap / small accessory|accessory||||typical measured range|body cap
Generic|35mm rear lens cap|18|Cap / small accessory|accessory||||typical measured range|rear cap
Generic|49mm front lens cap|12|Cap / small accessory|accessory||||typical measured range|49mm cap
Generic|52mm front lens cap|15|Cap / small accessory|accessory||||typical measured range|52mm cap
Generic|Camera neck strap|70|Strap / case|accessory||||typical nylon strap|neck strap
Generic|Leather camera case for compact|180|Strap / case|accessory||||typical fitted case|ever-ready case
Generic|Small soft lens pouch|45|Strap / case|accessory||||typical pouch|lens pouch
Generic|35mm film roll|30|Film / consumable|35mm||||one boxed 36-exposure roll|film roll
Generic|120 film roll|28|Film / consumable|120||||one boxed roll|120 roll
Generic|AA alkaline battery x4|96|Battery / power|accessory||||four batteries|4 AA
Generic|CR123A battery x2|34|Battery / power|accessory||||two batteries|2 CR123A
'''

# Additional published-specification references. Marked C because variants can differ.
ADDITIONAL_REFERENCE_TSV = 'brand|name|weight|genre|format|focus|lens|year|condition|aliases|confidence|sourceId\nNikon|Nikon F55|350|35mm AF SLR|35mm|AF|interchangeable|2002|body without batteries; date version is heavier|N55;Nikon Us|C|published-secondary\nNikon|Nikon F65|395|35mm AF SLR|35mm|AF|interchangeable|2001|body without batteries|N65;Nikon U|C|published-secondary\nNikon|Nikon F70|585|35mm AF SLR|35mm|AF|interchangeable|1994|body without batteries|N70|C|published-secondary\nNikon|Nikon F90X|755|35mm AF SLR|35mm|AF|interchangeable|1994|body only|N90s;F90X|C|published-secondary\nNikon|Nikon Lite Touch Zoom 70W|185|35mm zoom compact|35mm|AF|fixed|2000|without battery|Lite Touch 70W|C|published-secondary\nNikon|Nikon S4|540|35mm interchangeable rangefinder|35mm|MF|interchangeable|1959|body only|S4|C|published-secondary\nNikon|Nikonos I|700|Underwater film camera|35mm|MF|interchangeable|1963|body only, approximate published specification|Calypso/Nikkor|C|published-secondary\nNikon|Nikonos III|700|Underwater film camera|35mm|MF|interchangeable|1975|body only, approximate published specification|Nikonos 3|C|published-secondary\nNikon|Nikonos IV-A|700|Underwater film camera|35mm|MF|interchangeable|1980|body only, approximate published specification|Nikonos IVa;Nikonos 4A|C|published-secondary\nNikon|Nikkormat FTn|765|35mm MF SLR|35mm|MF|interchangeable|1967|body only|Nikomat FTn|C|published-secondary\nNikon|Nikkormat FT2|745|35mm MF SLR|35mm|MF|interchangeable|1975|body only|Nikomat FT2|C|published-secondary\nNikon|Nikkormat FT3|715|35mm MF SLR|35mm|MF|interchangeable|1977|body only|Nikomat FT3|C|published-secondary\nNikon|Nikkormat EL|780|35mm MF SLR|35mm|MF|interchangeable|1972|body only|Nikomat EL|C|published-secondary\nNikon|Nikon EL2|780|35mm MF SLR|35mm|MF|interchangeable|1977|body only|Nikkormat EL2;Nikomat EL2|C|published-secondary\nCanon|Canon T60|500|35mm MF SLR|35mm|MF|interchangeable|1990|body without batteries|T60|C|published-secondary\nCanon|Canon T80|555|35mm AF SLR|35mm|AF|interchangeable|1985|body without batteries|T80|C|published-secondary\nCanon|Canon FTb-N|750|35mm MF SLR|35mm|MF|interchangeable|1973|body only|FTb New;FTbN|C|published-secondary\nCanon|Canon FT QL|740|35mm MF SLR|35mm|MF|interchangeable|1966|body only|FTQL|C|published-secondary\nCanon|Canon FX|660|35mm MF SLR|35mm|MF|interchangeable|1964|body only|FX|C|published-secondary\nCanon|Canon FP|650|35mm MF SLR|35mm|MF|interchangeable|1964|body only|FP|C|published-secondary\nCanon|Canon TX|620|35mm MF SLR|35mm|MF|interchangeable|1975|body only|TX|C|published-secondary\nCanon|Canon TLb|620|35mm MF SLR|35mm|MF|interchangeable|1976|body only|TLb|C|published-secondary\nCanon|Canon EOS Elan 7N|580|35mm AF SLR|35mm|AF|interchangeable|2004|body without batteries|EOS 30V;EOS 33V|C|published-secondary\nCanon|Canon EOS Rebel GII|365|35mm AF SLR|35mm|AF|interchangeable|2003|body without batteries|EOS 3000N|C|published-secondary\nCanon|Canon EOS IX|570|APS SLR|APS|AF|interchangeable|1996|body without batteries|EOS IX E|C|published-secondary\nCanon|Canon EOS IX Lite|390|APS SLR|APS|AF|interchangeable|1996|body without batteries|EOS IX 7;EOS IX Lite|C|published-secondary\nCanon|Canon Demi S|380|35mm compact MF|35mm half-frame|MF|fixed|1964|with fixed lens|Demi S|C|published-secondary\nCanon|Canon Dial 35|410|35mm compact MF|35mm half-frame|MF|fixed|1963|with fixed lens|Dial 35|C|published-secondary\nCanon|Canon New Canonet 28|540|35mm fixed-lens rangefinder|35mm|MF|fixed|1971|with fixed lens|Canonet 28|C|published-secondary\nPentax|Pentax K2|680|35mm MF SLR|35mm|MF|interchangeable|1975|body only|K2|C|published-secondary\nPentax|Pentax MG|423|35mm MF SLR|35mm|MF|interchangeable|1982|body only|MG|C|published-secondary\nPentax|Pentax MV|425|35mm MF SLR|35mm|MF|interchangeable|1979|body only|MV|C|published-secondary\nPentax|Pentax MV-1|425|35mm MF SLR|35mm|MF|interchangeable|1980|body only|MV1|C|published-secondary\nPentax|Pentax MZ-3|380|35mm AF SLR|35mm|AF|interchangeable|1997|body without batteries|ZX-5N|C|published-secondary\nPentax|Pentax MZ-6|400|35mm AF SLR|35mm|AF|interchangeable|2001|body without batteries|ZX-L|C|published-secondary\nPentax|Pentax MZ-7|395|35mm AF SLR|35mm|AF|interchangeable|1999|body without batteries|ZX-7|C|published-secondary\nPentax|Pentax MZ-10|420|35mm AF SLR|35mm|AF|interchangeable|1996|body without batteries|ZX-10|C|published-secondary\nPentax|Pentax MZ-30|400|35mm AF SLR|35mm|AF|interchangeable|2000|body without batteries|ZX-30|C|published-secondary\nPentax|Pentax MZ-60|325|35mm AF SLR|35mm|AF|interchangeable|2002|body without batteries|ZX-60|C|published-secondary\nPentax|Pentax MZ-M|400|35mm MF SLR|35mm|MF|interchangeable|1997|body without batteries|ZX-M|C|published-secondary\nPentax|Pentax P5|525|35mm MF SLR|35mm|MF|interchangeable|1986|body without batteries|P50|C|published-secondary\nPentax|Pentax SF-10|590|35mm AF SLR|35mm|AF|interchangeable|1988|body without batteries|SFXn|C|published-secondary\nPentax|Pentax SF1|665|35mm AF SLR|35mm|AF|interchangeable|1987|body without batteries|SFX|C|published-secondary\nPentax|Pentax SF1n|665|35mm AF SLR|35mm|AF|interchangeable|1988|body without batteries|SFXn|C|published-secondary\nPentax|Pentax ZX-10|410|35mm AF SLR|35mm|AF|interchangeable|1996|body without batteries|MZ-10|C|published-secondary\nPentax|Pentax ZX-30|380|35mm AF SLR|35mm|AF|interchangeable|2000|body without batteries|MZ-30|C|published-secondary\nPentax|Pentax ZX-60|325|35mm AF SLR|35mm|AF|interchangeable|2002|body without batteries|MZ-60|C|published-secondary\nPentax|Pentax ZX-7|395|35mm AF SLR|35mm|AF|interchangeable|1999|body without batteries|MZ-7|C|published-secondary\nPentax|Pentax ZX-M|400|35mm MF SLR|35mm|MF|interchangeable|1997|body without batteries|MZ-M|C|published-secondary\nPentax|Pentax *ist|335|35mm AF SLR|35mm|AF|interchangeable|2003|body without batteries|Pentax ist film|C|published-secondary\nOlympus|Olympus Trip 35|390|35mm compact MF|35mm|zone|fixed|1967|with fixed lens|Trip 35|C|published-secondary\nOlympus|Olympus Pen EE-2|335|35mm compact MF|35mm half-frame|zone|fixed|1968|with fixed lens|Pen EE2|C|published-secondary\nOlympus|Olympus Pen EE-S|350|35mm compact MF|35mm half-frame|zone|fixed|1962|with fixed lens|Pen EES|C|published-secondary\nOlympus|Olympus Pen EE-S2|350|35mm compact MF|35mm half-frame|zone|fixed|1968|with fixed lens|Pen EES2|C|published-secondary\nOlympus|Olympus 35 EC|410|35mm compact MF|35mm|MF|fixed|1969|with fixed lens|35EC|C|published-secondary\nOlympus|Olympus 35 RD|530|35mm fixed-lens rangefinder|35mm|MF|fixed|1975|with fixed lens|35RD|C|published-secondary\nOlympus|Olympus Ecru|350|35mm AF compact|35mm|AF|fixed|1991|without battery|Ecru|C|published-secondary\nOlympus|Olympus O-Product|570|35mm AF compact|35mm|AF|fixed|1989|without batteries|O Product|C|published-secondary\nMinolta|Minolta SRT-100|690|35mm MF SLR|35mm|MF|interchangeable|1971|body only|SR-T 100|C|published-secondary\nMinolta|Minolta SRT-200|690|35mm MF SLR|35mm|MF|interchangeable|1975|body only|SR-T 200|C|published-secondary\nMinolta|Minolta SRT-202|690|35mm MF SLR|35mm|MF|interchangeable|1975|body only|SR-T 202|C|published-secondary\nMinolta|Minolta SR-1|650|35mm MF SLR|35mm|MF|interchangeable|1959|body only|SR1|C|published-secondary\nMinolta|Minolta SR-2|670|35mm MF SLR|35mm|MF|interchangeable|1958|body only|SR2|C|published-secondary\nMinolta|Minolta SR-7|700|35mm MF SLR|35mm|MF|interchangeable|1962|body only|SR7|C|published-secondary\nMinolta|Minolta XD-5|560|35mm MF SLR|35mm|MF|interchangeable|1978|body only|XD5|C|published-secondary\nMinolta|Minolta XG-1|505|35mm MF SLR|35mm|MF|interchangeable|1978|body only|XG1|C|published-secondary\nMinolta|Minolta Maxxum 3000i|460|35mm AF SLR|35mm|AF|interchangeable|1988|body without batteries|Dynax 3000i|C|published-secondary\nMinolta|Minolta Maxxum 3xi|400|35mm AF SLR|35mm|AF|interchangeable|1991|body without batteries|Dynax 3xi|C|published-secondary\nMinolta|Minolta Maxxum 8000i|600|35mm AF SLR|35mm|AF|interchangeable|1990|body without batteries|Dynax 8000i|C|published-secondary\nMinolta|Minolta Maxxum 600si|620|35mm AF SLR|35mm|AF|interchangeable|1995|body without batteries|Dynax 600si|C|published-secondary\nMinolta|Minolta Maxxum 800si|660|35mm AF SLR|35mm|AF|interchangeable|1997|body without batteries|Dynax 800si|C|published-secondary\nMinolta|Minolta Maxxum 300si|390|35mm AF SLR|35mm|AF|interchangeable|1995|body without batteries|Dynax 300si|C|published-secondary\nMinolta|Minolta Maxxum QTsi|365|35mm AF SLR|35mm|AF|interchangeable|1998|body without batteries|Dynax 303si|C|published-secondary\nMinolta|Minolta Hi-Matic 9|720|35mm fixed-lens rangefinder|35mm|MF|fixed|1966|with fixed lens|Hi-Matic 9|C|published-secondary\nMinolta|Minolta Hi-Matic E|560|35mm fixed-lens rangefinder|35mm|MF|fixed|1971|with fixed lens|Hi-Matic E|C|published-secondary\nMinolta|Minolta Hi-Matic F|360|35mm fixed-lens rangefinder|35mm|MF|fixed|1972|with fixed lens|Hi-Matic F|C|published-secondary\nMinolta|Minolta Hi-Matic G|330|35mm fixed-lens rangefinder|35mm|MF|fixed|1974|with fixed lens|Hi-Matic G|C|published-secondary\nMinolta|Minolta Hi-Matic GF|330|35mm fixed-lens rangefinder|35mm|MF|fixed|1974|with fixed lens|Hi-Matic GF|C|published-secondary\nMinolta|Minolta Hi-Matic S|375|35mm fixed-lens rangefinder|35mm|MF|fixed|1977|with fixed lens|Hi-Matic S|C|published-secondary\nMinolta|Minolta Hi-Matic C|305|35mm fixed-lens rangefinder|35mm|MF|fixed|1969|with fixed lens|Hi-Matic C|C|published-secondary\nLeica|Leica M1|545|35mm interchangeable rangefinder|35mm|MF|interchangeable|1959|body only|M1|C|published-secondary\nLeica|Leica MDa|510|35mm interchangeable rangefinder|35mm|MF|interchangeable|1966|body only|MDa|C|published-secondary\nLeica|Leica Ic|425|35mm interchangeable rangefinder|35mm|MF|interchangeable|1949|body only|Ic|C|published-secondary\nLeica|Leica If|435|35mm interchangeable rangefinder|35mm|MF|interchangeable|1952|body only|If|C|published-secondary\nLeica|Leica II|410|35mm interchangeable rangefinder|35mm|MF|interchangeable|1932|body only|Leica II D|C|published-secondary\nLeica|Leica IIf|430|35mm interchangeable rangefinder|35mm|MF|interchangeable|1951|body only|IIf|C|published-secondary\nLeica|Leica IIIa|430|35mm interchangeable rangefinder|35mm|MF|interchangeable|1935|body only|IIIa|C|published-secondary\nLeica|Leica IIIb|430|35mm interchangeable rangefinder|35mm|MF|interchangeable|1938|body only|IIIb|C|published-secondary\nLeica|Leica IIIc|430|35mm interchangeable rangefinder|35mm|MF|interchangeable|1940|body only|IIIc|C|published-secondary\nLeica|Leica IIIf|435|35mm interchangeable rangefinder|35mm|MF|interchangeable|1950|body only|IIIf|C|published-secondary\nLeica|Leica IIIg|480|35mm interchangeable rangefinder|35mm|MF|interchangeable|1957|body only|IIIg|C|published-secondary\nLeica|Leica R-E|625|35mm MF SLR|35mm|MF|interchangeable|1990|body only|R-E|C|published-secondary\nLeica|Leica R3|780|35mm MF SLR|35mm|MF|interchangeable|1976|body only|R3|C|published-secondary\nLeica|Leica R4|630|35mm MF SLR|35mm|MF|interchangeable|1980|body only|R4|C|published-secondary\nLeica|Leica R4s|625|35mm MF SLR|35mm|MF|interchangeable|1983|body only|R4s|C|published-secondary\nLeica|Leica R6|625|35mm MF SLR|35mm|MF|interchangeable|1988|body only|R6|C|published-secondary\nLeica|Leica R7|670|35mm MF SLR|35mm|MF|interchangeable|1992|body only|R7|C|published-secondary\nLeica|Leica R8|890|35mm MF SLR|35mm|MF|interchangeable|1996|body only|R8|C|published-secondary\nLeica|Leicaflex|770|35mm MF SLR|35mm|MF|interchangeable|1964|body only|Original Leicaflex|C|published-secondary\nLeica|Leicaflex SL|770|35mm MF SLR|35mm|MF|interchangeable|1968|body only|SL|C|published-secondary\nLeica|Leicaflex SL2|770|35mm MF SLR|35mm|MF|interchangeable|1974|body only|SL2|C|published-secondary\nFujifilm|Fujifilm GF670|1000|Medium-format rangefinder|120|MF|fixed|2010|with fixed lens and battery, published representative value|Bessa III;GF670 Professional|C|published-secondary\nFujifilm|Fujifilm GF670W|1100|Medium-format rangefinder|120|MF|fixed|2012|with fixed lens and battery, published representative value|GF670W Professional|C|published-secondary\nFujifilm|Fujifilm Instax Mini 70|281|Instant camera|Instant|AF|fixed|2015|without film pack, approximate published specification|Instax Mini 70|C|published-secondary\nFujifilm|Fujifilm Instax Mini LiPlay|255|Instant camera|Instant|AF|fixed|2019|without film pack, approximate published specification|Instax LiPlay|C|published-secondary\nFujifilm|Fujifilm Instax Square SQ10|450|Instant camera|Instant|AF|fixed|2017|without film pack, approximate published specification|Instax SQ10|C|published-secondary\nFujifilm|Fujifilm Instax Square SQ20|440|Instant camera|Instant|AF|fixed|2018|without film pack, approximate published specification|Instax SQ20|C|published-secondary\n'

GENRE_META = {
'35mm MF SLR': ('35mm一眼レフ（MF）', 260, 380),
'35mm AF SLR': ('35mm一眼レフ（AF）', 280, 430),
'35mm interchangeable rangefinder': ('35mmレンジファインダー（レンズ交換式）', 220, 340),
'35mm fixed-lens rangefinder': ('35mmレンジファインダー（固定レンズ）', 220, 340),
'Premium 35mm compact': ('高級35mmコンパクト', 150, 240),
'35mm AF compact': ('35mm AFコンパクト', 150, 250),
'35mm zoom compact': ('35mmズームコンパクト', 180, 280),
'35mm compact MF': ('35mm MFコンパクト', 150, 240),
'Half-frame SLR': ('ハーフサイズ一眼レフ', 220, 340),
'Medium-format SLR': ('中判一眼レフ', 400, 700),
'Medium-format rangefinder': ('中判レンジファインダー', 350, 600),
'Twin-lens reflex': ('二眼レフ', 300, 500),
'Medium-format folding camera': ('中判フォールディング', 220, 380),
'Panoramic film camera': ('パノラマカメラ', 280, 450),
'Large-format camera': ('大判カメラ', 500, 900),
'APS SLR': ('APS一眼レフ', 240, 380),
'APS compact': ('APSコンパクト', 140, 240),
'110 SLR': ('110一眼レフ', 130, 240),
'Underwater film camera': ('水中フィルムカメラ', 300, 500),
'Instant camera': ('インスタントカメラ', 260, 480),
'Toy camera': ('トイカメラ', 140, 260),
'Box camera': ('ボックスカメラ', 200, 360),
'Vintage film camera': ('その他・クラシックカメラ', 230, 420),
'35mm manual-focus lens': ('35mm MFレンズ', 130, 230),
'35mm autofocus lens': ('35mm AFレンズ', 140, 260),
'35mm autofocus zoom lens': ('35mm AFズームレンズ', 180, 330),
'Rangefinder lens': ('レンジファインダーレンズ', 120, 220),
'Medium-format lens': ('中判レンズ', 220, 420),
'Lens (unclassified)': ('交換レンズ（未分類）', 160, 300),
'Flash': ('フラッシュ', 100, 190),
'Motor drive / winder': ('モータードライブ・ワインダー', 130, 240),
'Finder accessory': ('ファインダーアクセサリー', 70, 150),
'Interchangeable finder': ('交換ファインダー', 110, 200),
'Flash adapter': ('フラッシュアダプター', 60, 120),
'Cable release': ('ケーブルレリーズ', 50, 100),
'Cap / small accessory': ('キャップ・小型アクセサリー', 50, 100),
'Strap / case': ('ストラップ・ケース', 90, 220),
'Film / consumable': ('フィルム・消耗品', 60, 120),
'Battery / power': ('電池・電源用品', 50, 120),
'Built-in lens reference': ('内蔵レンズ（参考）', 0, 0),
}

BRAND_ALIASES = {
'Nikon':['ニコン','Nikkor','ニッコール'], 'Canon':['キヤノン','キャノン'], 'Pentax':['ペンタックス','Asahi Pentax','Honeywell Pentax'],
'Olympus':['オリンパス'], 'Minolta':['ミノルタ'], 'Konica':['コニカ'], 'Fujifilm':['FujiFilm','Fuji','富士フイルム','フジ'],
'Leica':['ライカ','Leitz'], 'Contax':['コンタックス'], 'Yashica':['ヤシカ'], 'Mamiya':['マミヤ'], 'Bronica':['ブロニカ','Zenza Bronica'],
'Hasselblad':['ハッセルブラッド'], 'Rollei':['ローライ'], 'Ricoh':['リコー'], 'Voigtlander':['Voigtländer','フォクトレンダー'],
'Polaroid':['ポラロイド'], 'Kodak':['コダック'], 'Zeiss Ikon':['ツァイス・イコン'], 'Agfa':['アグファ'], 'Graflex':['グラフレックス']
}

def norm(s:str)->str:
    s=unicodedata.normalize('NFKC',str(s)).lower()
    s=s.replace('µ','mju').replace('・',' ')
    return re.sub(r'[^a-z0-9ぁ-んァ-ヶ一-龠]+','',s)

def parse_tsv(txt):
    lines=[l for l in txt.strip().splitlines() if l.strip()]
    header=lines[0].split('|')
    out=[]
    for l in lines[1:]:
        vals=l.split('|')
        vals += ['']*(len(header)-len(vals))
        out.append(dict(zip(header, vals)))
    return out

def genre_ja(g): return GENRE_META.get(g,(g,200,350))[0]

def infer_seed_mount(r, kind):
    brand=r.get('brand',''); name=r.get('name',''); genre=r.get('genre',''); lens=r.get('lens',''); fmt=r.get('format','')
    txt=f"{brand} {name} {genre} {lens} {fmt}"
    if kind=='accessory': return ''
    if kind=='lens':
        if brand=='Nikon': return 'Nikon F'
        if brand=='Canon': return 'Canon EF' if re.search(r'\bEF\b',name,re.I) else 'Canon FD'
        if brand=='Minolta': return 'Minolta A' if re.search(r'\bAF\b|Maxxum',name,re.I) else 'Minolta SR/MD'
        if brand=='Pentax': return 'Pentax 67' if '67' in name else ('Pentax 645' if '645' in name else 'Pentax K')
        if brand=='Olympus': return 'Olympus OM'
        if brand=='Leica': return 'Leica M'
        if brand=='Contax': return 'Contax/Yashica'
        if brand=='Mamiya': return 'Mamiya RB/RZ' if re.search(r'RB|RZ',name,re.I) else 'Mamiya 645'
        if brand=='Bronica': return 'Bronica'
        if brand=='Hasselblad': return 'Hasselblad V'
        return ''
    if 'fixed' in lens.lower(): return 'Fixed lens'
    if brand=='Nikon':
        if 'rangefinder' in genre.lower(): return 'Nikon S'
        if 'Nikonos' in name: return 'Nikonos'
        if 'Pronea' in name: return 'Nikon IX'
        return 'Nikon F'
    if brand=='Canon':
        if 'rangefinder' in genre.lower(): return 'Canon LTM'
        return 'Canon EF' if 'AF SLR' in genre else 'Canon FD'
    if brand=='Pentax':
        if 'Spotmatic' in name: return 'M42'
        if '645' in name: return 'Pentax 645'
        if re.search(r'\b67|6x7',name): return 'Pentax 67'
        if 'Auto 110' in name: return 'Pentax 110'
        return 'Pentax K'
    if brand=='Olympus': return 'Olympus Pen F' if 'Pen F' in name else 'Olympus OM'
    if brand=='Minolta': return 'Minolta A' if 'AF SLR' in genre else 'Minolta SR/MD'
    if brand=='Leica': return 'Leica M' if 'rangefinder' in genre.lower() else 'Leica R'
    if brand=='Contax': return 'Contax G' if 'rangefinder' in genre.lower() else 'Contax/Yashica'
    if brand=='Mamiya': return 'Mamiya RB/RZ' if re.search(r'RB|RZ',name,re.I) else 'Mamiya 645'
    if brand=='Bronica': return 'Bronica'
    if brand=='Hasselblad': return 'Hasselblad V'
    return ''

def record_from_seed(r, kind):
    aliases=[a.strip() for a in r.get('aliases','').split(';') if a.strip()]
    aliases += BRAND_ALIASES.get(r['brand'],[])
    weight=float(r['weight']) if r['weight'] else None
    if weight is not None and weight.is_integer(): weight=int(weight)
    return {
      'id': norm(r['brand']+'-'+r['name'])[:80],
      'kind': kind,
      'brand': r['brand'], 'name': r['name'], 'aliases': sorted(set(aliases)),
      'genre': r['genre'], 'genreJa': genre_ja(r['genre']), 'format': r.get('format') or '',
      'focus': r.get('focus') or '', 'lensType': r.get('lens') or '', 'mount': infer_seed_mount(r,kind),
      'year': int(r['year']) if str(r.get('year','')).isdigit() else None,
      'weightG': weight, 'weightMinG': weight, 'weightMaxG': weight,
      'weightCondition': r.get('condition') or 'reference specification',
      'dataType': 'reference', 'confidence': r.get('confidence') or 'B',
      'sourceId': r.get('sourceId') or 'compiled-specs', 'catalogDetails': ''
    }

seeds=[record_from_seed(r,'camera') for r in parse_tsv(CAMERA_TSV)]
seeds += [record_from_seed(r,'accessory' if 'lens' not in r.get('lens','') else 'lens') for r in parse_tsv(ACCESSORY_TSV)]
seeds += [record_from_seed(r,'camera') for r in parse_tsv(ADDITIONAL_REFERENCE_TSV)]
# Remove zero-weight built-in-lens pseudo row from shipping selection dataset.
seeds=[r for r in seeds if r['weightG'] is None or r['weightG']>0]

# Load broad model catalogue, primarily based on the open film-camera-database sample.
df=pd.read_csv('/mnt/data/cameras_all.csv')
details=df.details.fillna('')
year_num=pd.to_numeric(df.marketed,errors='coerce')
explicit_film=details.str.contains('Film Size',case=False,na=False)
no_mp=~details.str.contains('Megapixels',case=False,na=False)
lens_hint=details.str.contains('Lens:',case=False,na=False) & ~explicit_film
# This intentionally favors recall, then film compatibility is checked model-by-model below.
LENS_NAME_PATTERN=r"(?:\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\s*mm\b.*?(?:f\s*/?\s*\d|F\s*\d)|\b(?:Nikkor|Rokkor|Zuiko|Takumar|Zenzanon|Fujinon|Distagon|Planar|Sonnar|Summicron|Elmarit|Elmar|Biogon|Hologon|Teleconverter|Extender)\b|\b(?:Canon\s+)?(?:EF|FD|FL)\s+\d|\bMinolta\s+(?:AF|MD|MC)\s+\d|\bSMC\s+Pentax[^,]*\d)"
name_series=df.name.fillna('').str.contains(LENS_NAME_PATTERN,case=False,regex=True)
film_cam_mask=no_mp & ~lens_hint & ~name_series & (explicit_film | (year_num<=2002))
lens_mask=no_mp & (lens_hint | name_series)
cat=df[film_cam_mask | lens_mask].copy()

AF_SLR_PAT=r'(EOS|F-?50\d|F-?60\d|F-?70\d|F-?80\d|F90|F100|F4\b|F5\b|F6\b|Maxxum|Dynax|Alpha\s*[579]|MZ-|ZX-|Z-1|PZ-|SF-?\d|Maxxum|Dynax|SA-|RT\s*RT)'
RANGE_PAT=r'(Leica\s*M\d|Canon\s*(P|7|VI|IV|III)|Nikon\s*(S2|S3|S4|SP)|Bessa\s*R|Hexar\s*RF|Contax\s*G[12]|Minolta\s*CLE)'
COMPACT_PREMIUM=r'(Contax\s*T2\b|Contax\s*T3\b|35Ti|28Ti|GR1|TC-1|Hexar\s*AF|mju\s*II|Stylus\s*Epic|Klasse|Natura|Minilux|Leica\s*CM|Espio\s*Mini|Tiara)'
COMPACT_AF=r'(Autoboy|Sure\s*Shot|AF35|L35|Big\s*Mini|Espio|Mju|Stylus|Zoom|Cardia|Riva|Freedom|Prima|Lite\s*Touch|One\s*Touch)'
TLR_PAT=r'(Rolleiflex|Rolleicord|Yashica\s*Mat|Autocord|Ricohflex|Diacord|C220|C330|Flexaret|Seagull\s*4)'
MF_RF_PAT=r'(GA645|GS645|GW690|GSW690|GF670|Mamiya\s*[67]\b|Makina|RF645|XPan|TX-1)'
MF_SLR_PAT=r'(RB67|RZ67|Mamiya\s*645|Pentax\s*645|Pentax\s*6x7|Pentax\s*67|Bronica|Hasselblad\s*(500|501|503|20\d|55\d)|Contax\s*645)'

def infer_format(det,name):
    if re.search(r'instax|Polaroid',name,re.I) or re.search(r'Film Size:\s*Instant',det,re.I): return 'Instant'
    m=re.search(r'Film Size:\s*([^;]+)',det,re.I)
    if m:
        val=m.group(1).strip().lower()
        if '135' in val:return '35mm'
        if '120' in val or '220' in val or '6x6' in val or '6x7' in val or '6x9' in val or '645' in val:return '120'
        if 'aps' in val:return 'APS'
        if '110' in val:return '110'
        if '127' in val:return '127'
        if '4x5' in val:return '4x5'
        return val.upper()
    if re.search(r'645|67\b|6x7|6x6|690|Hasselblad|Bronica|Rolleiflex|Rolleicord|Mamiya RB|Mamiya RZ',name,re.I): return '120'
    return '35mm'

def extract_mount(det):
    m=re.search(r'Lens Mount:\s*([^;]+)',det,re.I)
    return m.group(1).strip() if m else ''

def normalize_mount(mount, brand=''):
    m=mount.strip()
    pairs={
      'F':'Nikon F','AI':'Nikon F (AI)','AI-S':'Nikon F (AI-S)','AF':'Nikon F / Minolta A','AF-D':'Nikon F (AF-D)','AF-S':'Nikon F (AF-S)','AF-P':'Nikon F (AF-P)',
      'EF':'Canon EF','EF-S':'Canon EF-S','EF-M':'Canon EF-M','FD':'Canon FD','FL':'Canon FL','RF':'Nikon S' if brand=='Nikon' else ('Canon RF' if brand=='Canon' else m),
      'K':'Pentax K','KAF':'Pentax KAF','KAF2':'Pentax KAF2','M42':'M42','645':'Pentax 645','645AF2':'Pentax 645AF2',
      'OM':'Olympus OM','MD':'Minolta SR/MD','MC':'Minolta SR/MC','Alpha':'Minolta/Sony A','M':'Leica M','R':'Leica R' if brand=='Leica' else ('Canon R' if brand=='Canon' else m),'Screw':'Leica screw','Leica Screw':'Leica screw',
      'Contax/Yashica':'Contax/Yashica','G':'Fujifilm G' if brand in ('FujiFilm','Fujifilm') else 'Contax G','S,PS':'Bronica S/PS','E,PE':'Bronica E/PE','PG':'Bronica GS-1','E':'Sony E' if brand=='Sony' else 'Bronica E',
      'Z':'Nikon Z','X':'Fujifilm X','Q':'Pentax Q','Micro Four Thirds':'Micro Four Thirds','Panasonic Micro Four Thirds':'Micro Four Thirds',
      'Leica L':'Leica L','L':'Leica L' if brand in ('Leica','Panasonic','Sigma') else m,'XCD':'Hasselblad XCD','1':'Nikon 1','Fixed':'Fixed lens'
    }
    return pairs.get(m,m)

def is_film_compatible_lens(name, det, brand, mount, year):
    txt=f'{name} {det} {mount}'
    ml=mount.lower().strip()
    digital_mounts={'z','rf','ef-s','ef-m','e','x','q','micro four thirds','panasonic micro four thirds','leica l','xcd','1','nx','ex'}
    if ml in digital_mounts:
        if not (brand=='Bronica' and ml=='e'):
            return False
    if ml=='l' and brand in ('Leica','Panasonic','Sigma'): return False
    if ml=='g' and brand in ('FujiFilm','Fujifilm'): return False
    if re.search(r'\b(?:NIKKOR\s+Z|M\.?ZUIKO|LUMIX|SEL\d|Sony\s+E\b|Sony\s+FE\b|Fujinon\s+(?:XF|XC|GF)\b|Samsung\s+NX|Canon\s+RF\b|Canon\s+EF-M\b|Pentax\s+Q\b|Hasselblad\s+XCD\b)',txt,re.I): return False
    if re.search(r'\b(?:DG\s+DN|DC\s+DN|Di\s*II|DX)\b',txt,re.I): return False
    if brand=='Sigma' and re.search(r'\b(?:DC|DN)\b',name,re.I): return False
    if brand=='Canon' and re.search(r'\bEF-S\b|\bEF-M\b|\bRF\s*\d',name,re.I): return False
    if brand=='Pentax' and (re.search(r'PENTAX-DA|\bDA\b',name,re.I) and not re.search(r'\bD[ -]?FA\b',name,re.I)): return False
    if brand=='Leica' and (ml=='s' or re.search(r'-(?:SL|TL|T)\b|Summicron-S\b|Elmarit-S\b',name,re.I)): return False
    if re.search(r'Four Thirds|Micro Four Thirds|APS-C only|digital only',txt,re.I): return False
    if brand in ('Panasonic','Samsung'): return False
    if brand=='Sony' and (ml in ('e','') or re.search(r'SEL[-\s]?\d|\bOSS\b|Conversion Lens|\b(?:E|FE)\s*\d|SAL-?35F18|SAL55300',name,re.I) or ((year or 0)>=2009 and not re.search(r'\bSAL[-\d]|SSM',name,re.I))): return False
    if brand in ('FujiFilm','Fujifilm') and (ml in ('x','') and (year or 9999)>=2009): return False
    if brand=='Olympus' and (re.search(r'M\.?Zuiko|Digital|BCL-\d|MC-20',name,re.I) or ((year or 0)>=2009 and not mount)): return False
    if brand in ('Sigma','Tamron','Tokina','Samyang','Rokinon','Viltrox') and not mount and (year or 0)>=2012: return False
    return True

def infer_lens_genre(name, det):
    txt=name+' '+det
    fmt='120' if re.search(r'(645|67|6x7|6x6|Hasselblad|Bronica|Mamiya|Zenzanon|Pentax 67)',txt,re.I) else '35mm'
    af=bool(re.search(r'\b(AF|EF|USM|Maxxum|Dynax)\b',txt,re.I))
    zoom=bool(re.search(r'\d+\s*-\s*\d+mm|zoom',txt,re.I))
    if fmt=='120':return 'Medium-format lens',fmt,'MF'
    if re.search(r'(Leica|Summicron|Elmarit|Contax G|Voigtlander)',txt,re.I): return 'Rangefinder lens',fmt,'MF'
    if af and zoom:return '35mm autofocus zoom lens',fmt,'AF'
    if af:return '35mm autofocus lens',fmt,'AF'
    return '35mm manual-focus lens',fmt,'MF'

def infer_camera_genre(name, det, fmt):
    txt=name+' '+det
    if re.search(r'instax|Polaroid',name,re.I) or re.search(r'Film Size:\s*Instant',det,re.I): return ('Instant camera','AF' if re.search(r'AF|autofocus',txt,re.I) else 'MF','fixed')
    fixed='Lens Mount:  Fixed' in det or 'Lens Mount: Fixed' in det
    if fmt in ('APS',): return ('APS compact' if fixed else 'APS SLR','AF' if fixed else 'AF','fixed' if fixed else 'interchangeable')
    if fmt=='110': return ('110 SLR' if 'SLR' in txt.upper() or 'AUTO 110' in txt.upper() else 'Vintage film camera','MF','interchangeable' if 'AUTO 110' in txt.upper() else 'fixed')
    if fmt in ('120','220'):
        if re.search(TLR_PAT,txt,re.I): return ('Twin-lens reflex','MF','fixed')
        if re.search(MF_RF_PAT,txt,re.I): return ('Medium-format rangefinder','AF' if 'GA645' in txt else 'MF','fixed' if re.search(r'GA645|GS645|GW690|GSW690|Makina',txt,re.I) else 'interchangeable')
        if re.search(MF_SLR_PAT,txt,re.I): return ('Medium-format SLR','AF' if re.search(r'645AF|Contax 645',txt,re.I) else 'MF','interchangeable')
        if re.search(r'(Ikonta|Isolette|Folder|Folding|Bessa\s*[I1-9]|Moskva)',txt,re.I): return ('Medium-format folding camera','MF','fixed')
        return ('Vintage film camera','MF','fixed' if fixed else 'interchangeable')
    if fmt=='4x5' or re.search(r'(Graphic|4x5|5x7|8x10|view camera)',txt,re.I): return ('Large-format camera','MF','interchangeable')
    if re.search(r'(Pen\s*F|half.?frame|Demi|Dial 35)',txt,re.I): return ('Half-frame SLR' if 'Pen F' in txt else '35mm compact MF','MF','interchangeable' if 'Pen F' in txt else 'fixed')
    if re.search(RANGE_PAT,txt,re.I): return ('35mm interchangeable rangefinder','AF' if 'Contax G' in txt else 'MF','interchangeable')
    if re.search(COMPACT_PREMIUM,txt,re.I): return ('Premium 35mm compact','AF','fixed')
    if fixed:
        if re.search(COMPACT_AF,txt,re.I) or (pd.notna(row_year_global) and row_year_global>=1978): return ('35mm AF compact','AF','fixed')
        if re.search(r'(Canonet|Hi-?Matic|Electro 35|35 SP|35 RC|Retina|Lynx|Auto S|QL17|QL19)',txt,re.I): return ('35mm fixed-lens rangefinder','MF','fixed')
        return ('35mm compact MF','MF','fixed')
    if re.search(AF_SLR_PAT,txt,re.I): return ('35mm AF SLR','AF','interchangeable')
    if re.search(r'(F-1|AE-1|A-1|AV-1|AT-1|T50|T70|T90|OM-|Spotmatic|K1000|Pentax\s*(MX|ME|LX|KM|KX)|SRT|X-\d|XD-|XE-|Contax\s*(RTS|139|167|Aria|RX)|FX-|Autoreflex|Exakta|Praktica|Zenit|Fujica ST)',txt,re.I): return ('35mm MF SLR','MF','interchangeable')
    return ('Vintage film camera','MF','interchangeable')

# Genre prior ranges for unverified model estimates, based on the reference cohort and shipping-oriented conservative intervals.
GENRE_WEIGHT_PRIORS={
'35mm MF SLR':(430,820),'35mm AF SLR':(380,950),'35mm interchangeable rangefinder':(390,700),'35mm fixed-lens rangefinder':(400,780),
'Premium 35mm compact':(150,380),'35mm AF compact':(140,420),'35mm zoom compact':(180,420),'35mm compact MF':(180,550),
'Half-frame SLR':(450,650),'Medium-format SLR':(900,2700),'Medium-format rangefinder':(620,1550),'Twin-lens reflex':(780,1700),
'Medium-format folding camera':(450,950),'Panoramic film camera':(600,1550),'Large-format camera':(1000,3000),'APS SLR':(350,700),'APS compact':(140,360),
'110 SLR':(160,480),'Underwater film camera':(500,900),'Instant camera':(450,900),'Toy camera':(150,450),'Box camera':(350,850),
'Vintage film camera':(350,1000),'35mm manual-focus lens':(120,600),'35mm autofocus lens':(130,750),'35mm autofocus zoom lens':(220,1300),
'Rangefinder lens':(100,550),'Medium-format lens':(300,1200),'Lens (unclassified)':(150,900)
}

# Build brand-aware lookup keys for regional names and aliases.
# Generic brand aliases (e.g. "Nikkor") are excluded from matching to avoid false positives.
def strip_brand_tokens(value, brand):
    text=str(value)
    candidates=[brand, *BRAND_ALIASES.get(brand, [])]
    for token in sorted(candidates, key=len, reverse=True):
        if token:
            text=re.sub(re.escape(token), ' ', text, flags=re.I)
    return norm(text)

seed_by_brand={}
for r in seeds:
    generic={norm(a) for a in BRAND_ALIASES.get(r['brand'], [])}
    keys={norm(r['name']), strip_brand_tokens(r['name'], r['brand'])}
    for a in r['aliases']:
        k=norm(a)
        if k and k not in generic:
            keys.add(k)
            keys.add(strip_brand_tokens(a, r['brand']))
    for k in keys:
        if len(k)>=2:
            seed_by_brand.setdefault(norm(r['brand']), {})[k]=r

catalog=[]
for row_index, rr in cat.iterrows():
    brand=str(rr['brand']).strip(); name=str(rr['name']).replace('\xa0',' ').strip(); det=str(rr['details']) if pd.notna(rr['details']) else ''
    if not name or name=='nan': continue
    mount_raw=extract_mount(det)
    is_lens=bool(re.search(r'Lens:',det,re.I) and not re.search(r'Film Size',det,re.I)) or bool(re.search(LENS_NAME_PATTERN,name,re.I))
    if re.search(r'instax|Polaroid|\bcamera\b',name,re.I) and re.search(r'Lens Mount:\s*Fixed',det,re.I): is_lens=False
    yrmatch=re.search(r'(18|19|20)\d{2}',str(rr['marketed']))
    year=int(yrmatch.group()) if yrmatch else None
    if is_lens and not is_film_compatible_lens(name,det,brand,mount_raw,year):
        continue
    if is_lens:
        genre,fmt,focus=infer_lens_genre(name,det); lens_type='lens'; kind='lens'
        mount=normalize_mount(mount_raw,brand)
    else:
        fmt=infer_format(det,name)
        row_year_global=year
        genre,focus,lens_type=infer_camera_genre(name,det,fmt); kind='camera'
        mount=normalize_mount(mount_raw,brand) if mount_raw else ('Fixed lens' if lens_type=='fixed' else '')
        if genre=='Vintage film camera' and lens_type!='fixed':
            if mount in ('Canon EF','Pentax KAF','Pentax KAF2','Minolta/Sony A','Minolta A','Nikon IX') or re.search(AF_SLR_PAT,name,re.I):
                genre,focus,lens_type='35mm AF SLR','AF','interchangeable'
            elif mount in ('Nikon F','Nikon F (AI)','Nikon F (AI-S)','Canon FD','Canon FL','Canon R','Pentax K','M42','Olympus OM','Minolta SR/MD','Minolta SR/MC','Leica R','Contax/Yashica','Exakta Bayonet','KA','KA2','EX'):
                genre,focus,lens_type='35mm MF SLR','MF','interchangeable'
    # Skip clear digital leftovers or data rows that are only lens accessories with no meaningful model name.
    if re.search(r'(PowerShot|Coolpix|FinePix|Cyber.?shot|Lumix|Digital|megapixel|EOS\s*[RMD]\d|Nikon\s*[DZ]\d|m:robe|EasyShare|Samsung\s+NX|Olympus\s+E-?\d|Sony\s+Alpha\s*[0-9]|ZV-1|Cyber-shot|Mavica|Sigma\s+SD9|Casio\s+QV|Leica\s+(?:SL|TL|T|[CDV]-Lux)\b)',name,re.I): continue
    nkey=norm(name)
    brand_key=norm(brand.replace('FujiFilm','Fujifilm').replace('Fujica','Fujifilm'))
    candidate_keys={nkey, strip_brand_tokens(name, brand.replace('FujiFilm','Fujifilm').replace('Fujica','Fujifilm'))}
    matched=None
    lookup=seed_by_brand.get(brand_key, {})
    for ck in candidate_keys:
        if ck in lookup:
            matched=lookup[ck]; break
    if not matched:
        # Long aliases may include small suffix differences such as date/data variants.
        for ck in candidate_keys:
            if len(ck)<6: continue
            for k, seed in lookup.items():
                if len(k)>=6 and (k in ck or ck in k):
                    matched=seed; break
            if matched: break
    if matched:
        # Keep the regional catalogue name searchable without creating a duplicate row.
        if norm(name)!=norm(matched['name']) and name not in matched['aliases']:
            matched['aliases'].append(name)
        continue
    lo,hi=GENRE_WEIGHT_PRIORS.get(genre,(250,900))
    aliases=[]
    if ' aka ' in name:
        parts=[p.strip() for p in re.split(r'\s+aka\s+',name,flags=re.I)]
        name=parts[0];aliases=parts[1:]
    aliases += BRAND_ALIASES.get(brand,[])
    catalog.append({
      'id': norm(brand+'-'+name)[:80], 'kind':kind, 'brand':brand.replace('FujiFilm','Fujifilm'), 'name':name,
      'aliases':sorted(set(aliases)), 'genre':genre,'genreJa':genre_ja(genre),'format':fmt,'focus':focus,'lensType':lens_type,'mount':mount,
      'year':year,'weightG':None,'weightMinG':lo,'weightMaxG':hi,
      'weightCondition':'同ジャンルの既知機種からの推定範囲','dataType':'genre-estimate','confidence':'D',
      'sourceId':'open-model-catalog','catalogDetails':det[:500]
    })

# Deduplicate by normalized brand/name; reference rows win.
all_records=[]; seen=set()
for r in seeds+catalog:
    key=(norm(r['brand']),norm(r['name']))
    if key in seen: continue
    seen.add(key); all_records.append(r)

# Refine estimate ranges using exact/reference distribution within each genre where enough records exist.
by_genre={}
for r in all_records:
    if r['weightG'] and r['dataType']=='reference': by_genre.setdefault(r['genre'],[]).append(float(r['weightG']))
for r in all_records:
    if r['weightG'] is None and len(by_genre.get(r['genre'],[]))>=4:
        vals=sorted(by_genre[r['genre']])
        q1=vals[max(0,round((len(vals)-1)*.15))]; q9=vals[min(len(vals)-1,round((len(vals)-1)*.85))]
        r['weightMinG']=int(round(q1/5)*5); r['weightMaxG']=int(round(q9/5)*5)

# Search tokens and display metadata.
for r in all_records:
    ja_brand=' '.join(BRAND_ALIASES.get(r['brand'],[]))
    r['searchText']=' '.join([r['brand'],r['name'],*r['aliases'],r['genre'],r['genreJa'],r.get('mount',''),ja_brand]).strip()
    meta=GENRE_META.get(r['genre'],(r['genre'],200,350))
    r['packingMinG']=meta[1];r['packingMaxG']=meta[2]

all_records.sort(key=lambda r:(0 if r['dataType']=='reference' else 1,r['brand'].lower(),r['name'].lower()))

# Genre stats
stats=[]
for g in sorted(set(r['genre'] for r in all_records)):
    rows=[r for r in all_records if r['genre']==g]
    refs=[float(r['weightG']) for r in rows if r['weightG']]
    estimated=[((r['weightMinG']+r['weightMaxG'])/2) for r in rows if not r['weightG']]
    allvals=sorted(refs or estimated)
    def pct(p):
        if not allvals:return None
        return int(round(allvals[round((len(allvals)-1)*p)]))
    stats.append({
      'genre':g,'genreJa':genre_ja(g),'count':len(rows),'referenceCount':len(refs),
      'minG':int(min(allvals)) if allvals else None,'medianG':pct(.5),'maxG':int(max(allvals)) if allvals else None,
      'typicalLowG':pct(.2),'typicalHighG':pct(.8),
      'packingMinG':GENRE_META.get(g,(g,200,350))[1], 'packingMaxG':GENRE_META.get(g,(g,200,350))[2],
      'examples':[r['name'] for r in rows if r['weightG']][:6]
    })

SOURCES=[
 {'id':'compiled-specs','label':'公開仕様・取扱説明書・メーカー資料をもとにした重量リファレンス','url':'','note':'機種の仕様違い、ファインダー、電池、フィルム、ストラップの有無で実物重量は変わります。'},
 {'id':'published-secondary','label':'公開されている二次資料・仕様表の追加リファレンス','url':'','note':'地域名・データバック・電池・ファインダーなどで重量が異なるため、信頼度Cとして収録しています。'},
 {'id':'open-model-catalog','label':'film-camera-database sample（公開モデルカタログ）','url':'https://github.com/w84thesun/film-camera-database-sample','note':'機種名・発売年・フィルム形式・マウントの基礎カタログとして使用。重量がない機種はジャンル推定です。'},
 {'id':'analog-camera-space','label':'analog camera space','url':'https://github.com/analog-photography-space/analog-camera-space','note':'現行アナログカメラの分類・形式設計を参考にしています。'},
 {'id':'user-local','label':'この端末で保存した実測値','url':'','note':'ユーザー実測値はブラウザ内だけに保存されます。'}
]

POLICIES={
 'tiers':[
  {'maxWeight':300,'code':'300G','label':'300g以下','usLow':39.99,'usHigh':69.99,'eu':19.99,'intl':11.99,'fallback':44.99},
  {'maxWeight':500,'code':'500G','label':'301〜500g','usLow':44.99,'usHigh':74.99,'eu':22.99,'intl':13.99,'fallback':49.99},
  {'maxWeight':800,'code':'800G','label':'501〜800g','usLow':49.99,'usHigh':79.99,'eu':26.99,'intl':15.99,'fallback':59.99},
  {'maxWeight':1000,'code':'1000G','label':'801〜1000g','usLow':59.99,'usHigh':89.99,'eu':29.99,'intl':17.99,'fallback':69.99},
  {'maxWeight':1500,'code':'1500G','label':'1001〜1500g','usLow':74.99,'usHigh':104.99,'eu':37.99,'intl':21.99,'fallback':84.99},
  {'maxWeight':2000,'code':'2000G','label':'1501〜2000g','usLow':89.99,'usHigh':119.99,'eu':44.99,'intl':25.99,'fallback':99.99}],
 'priceTiers':[{'maxPrice':100,'code':'100USD','label':'100USD以下'},{'maxPrice':250,'code':'101250USD','label':'101〜250USD'}]
}

meta={
 'generated':'2026-06-30','recordCount':len(all_records),'referenceCount':sum(r['weightG'] is not None for r in all_records),
 'cameraCount':sum(r['kind']=='camera' for r in all_records),'lensCount':sum(r['kind']=='lens' for r in all_records),
 'accessoryCount':sum(r['kind']=='accessory' for r in all_records),'genreCount':len(stats),
 'notice':'送料判定は梱包後の実測が最優先です。重量リファレンスは候補選びと事前見積もり用です。'
}

payload={'meta':meta,'items':all_records,'genres':stats,'sources':SOURCES,'policies':POLICIES}
(OUT/'data'/'database.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(OUT/'data'/'database.js').write_text('window.FILM_DB='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')

# CSV export
cols=['kind','brand','name','aliases','genreJa','genre','format','mount','focus','year','weightG','weightMinG','weightMaxG','weightCondition','dataType','confidence','packingMinG','packingMaxG','sourceId']
with (OUT/'data'/'camera-weight-database.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for r in all_records:
        row={k:r.get(k,'') for k in cols};row['aliases']='; '.join(r['aliases']);w.writerow(row)

print(json.dumps(meta,ensure_ascii=False,indent=2))
print('genres',len(stats))
