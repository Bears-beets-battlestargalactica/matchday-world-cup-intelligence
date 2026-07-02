#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("backend/static_rosters.json")
OVERWRITE_EXISTING = True  # change to True if you want to replace Jordan too


def p(number, name, position):
    return {
        "id": None,
        "name": name,
        "age": None,
        "number": number,
        "position": position,
        "photo": None,
        "rating": None,
        "source": "manual-static-roster",
    }


def team(players):
    return {
        "provider": "Manual static roster snapshot",
        "cached": True,
        "players": players,
        "rating_note": (
            "This is a manual static roster snapshot used for visual roster context only. "
            "It does not affect the prediction model."
        ),
    }


MANUAL = {
    "South Africa": team([
        p(1,"Ronwen Williams","Goalkeeper"), p(16,"Sipho Chaine","Goalkeeper"), p(22,"Ricardo Goss","Goalkeeper"),
        p(2,"Thabang Matuludi","Defender"), p(3,"Khulumani Ndamane","Defender"), p(14,"Mbekezeli Mbokazi","Defender"), p(18,"Samukele Kabini","Defender"), p(19,"Nkosinathi Sibisi","Defender"), p(20,"Khuliso Mudau","Defender"), p(21,"Ime Okon","Defender"), p(24,"Olwethu Makhanya","Defender"), p(25,"Kamogelo Sebelebele","Defender"), p(26,"Bradley Cross","Defender"),
        p(4,"Teboho Mokoena","Midfielder"), p(5,"Thalente Mbatha","Midfielder"), p(6,"Aubrey Modiba","Midfielder"), p(13,"Sphephelo Sithole","Midfielder"), p(23,"Jayden Adams","Midfielder"),
        p(7,"Oswin Appollis","Forward"), p(8,"Tshepang Moremi","Forward"), p(9,"Lyle Foster","Forward"), p(10,"Relebohile Mofokeng","Forward"), p(11,"Themba Zwane","Forward"), p(12,"Thapelo Maseko","Forward"), p(15,"Iqraam Rayners","Forward"), p(17,"Evidence Makgopa","Forward"),
    ]),
    "South Korea": team([
        p(1,"Kim Seung-gyu","Goalkeeper"), p(12,"Song Bum-keun","Goalkeeper"), p(21,"Jo Hyeon-woo","Goalkeeper"),
        p(2,"Lee Han-beom","Defender"), p(3,"Lee Ki-hyuk","Defender"), p(4,"Kim Min-jae","Defender"), p(5,"Kim Tae-hyeon","Defender"), p(13,"Lee Tae-seok","Defender"), p(14,"Cho Wi-je","Defender"), p(15,"Kim Moon-hwan","Defender"), p(16,"Park Jin-seob","Defender"), p(22,"Seol Young-woo","Defender"), p(23,"Jens Castrop","Defender"),
        p(6,"Hwang In-beom","Midfielder"), p(8,"Paik Seung-ho","Midfielder"), p(10,"Lee Jae-sung","Midfielder"), p(20,"Yang Hyun-jun","Midfielder"), p(24,"Kim Jin-gyu","Midfielder"), p(26,"Lee Dong-gyeong","Midfielder"),
        p(7,"Son Heung-min","Forward"), p(9,"Cho Gue-sung","Forward"), p(11,"Hwang Hee-chan","Forward"), p(17,"Bae Jun-ho","Forward"), p(18,"Oh Hyeon-gyu","Forward"), p(19,"Lee Kang-in","Forward"), p(25,"Eom Ji-sung","Forward"),
    ]),
    "Czechia": team([
        p(1,"Matej Kovar","Goalkeeper"), p(16,"Jindrich Stanek","Goalkeeper"), p(23,"Lukas Hornicek","Goalkeeper"),
        p(2,"David Zima","Defender"), p(3,"Tomas Holes","Defender"), p(4,"Robin Hranac","Defender"), p(5,"Vladimir Coufal","Defender"), p(6,"Stepan Chaloupek","Defender"), p(7,"Ladislav Krejci","Defender"), p(14,"David Jurasek","Defender"), p(20,"Jaroslav Zeleny","Defender"), p(21,"David Doudera","Defender"),
        p(8,"Vladimír Darida","Midfielder"), p(12,"Lukas Cerv","Midfielder"), p(15,"Pavel Sulc","Midfielder"), p(18,"Michal Sadilek","Midfielder"), p(22,"Tomas Soucek","Midfielder"), p(24,"Alexandr Sojka","Midfielder"), p(25,"Hugo Sochurek","Midfielder"), p(26,"Denis Visinsky","Midfielder"),
        p(9,"Adam Hlozek","Forward"), p(10,"Patrik Schick","Forward"), p(11,"Jan Kuchta","Forward"), p(13,"Mojmir Chytil","Forward"), p(17,"Lukas Provod","Forward"), p(19,"Tomas Chory","Forward"),
    ]),
    "Bosnia and Herzegovina": team([
        p(1,"Nikola Vasilj","Goalkeeper"), p(12,"Mladen Jurkas","Goalkeeper"), p(22,"Martin Zlomislic","Goalkeeper"),
        p(2,"Nihad Mujakic","Defender"), p(3,"Dennis Hadzikadunic","Defender"), p(4,"Tarik Muharemovic","Defender"), p(5,"Sead Kolasinac","Defender"), p(7,"Amar Dedic","Defender"), p(18,"Nikola Katic","Defender"), p(21,"Stjepan Radeljic","Defender"), p(24,"Arjan Malic","Defender"),
        p(6,"Benjamin Tahirovic","Midfielder"), p(8,"Armin Gigovic","Midfielder"), p(13,"Ivan Basic","Midfielder"), p(14,"Ivan Sunjic","Midfielder"), p(16,"Amir Hadziahmetovic","Midfielder"), p(17,"Dzenis Burnic","Midfielder"), p(26,"Ermin Mahmic","Midfielder"),
        p(9,"Samed Bazdar","Forward"), p(10,"Ermedin Demirovic","Forward"), p(11,"Edin Dzeko","Forward"), p(15,"Amar Memic","Forward"), p(19,"Kerim Alajbegovic","Forward"), p(20,"Esmir Bajraktarevic","Forward"), p(23,"Haris Tabakovic","Forward"), p(25,"Jovo Lukic","Forward"),
    ]),
    "Qatar": team([
        p(1,"Mahmoud Abunada","Goalkeeper"), p(21,"Salah Zakaria","Goalkeeper"), p(22,"Meshaal Barsham","Goalkeeper"),
        p(2,"Pedro Miguel","Defender"), p(3,"Lucas Mendes","Defender"), p(4,"Issa Laye","Defender"), p(13,"Ayoub Alawi","Defender"), p(14,"Homam Ahmed","Defender"), p(16,"Boualem Khoukhi","Defender"), p(18,"Sultan Al-Brake","Defender"), p(25,"Hashmi Hussein","Defender"),
        p(5,"Jassem Gaber","Midfielder"), p(6,"Abdulaziz Hatem","Midfielder"), p(12,"Karim Boudiaf","Midfielder"), p(20,"Ahmed Fathy","Midfielder"), p(23,"Assim Madibo","Midfielder"), p(26,"Mohamed Al-Mannai","Midfielder"),
        p(7,"Ahmed Alaaeldin","Forward"), p(8,"Edmilson Junior","Forward"), p(9,"Mohammed Muntari","Forward"), p(10,"Hassan Al-Haydos","Forward"), p(11,"Akram Afif","Forward"), p(15,"Yusuf Abdurisag","Forward"), p(17,"Ahmed Al-Ganehi","Forward"), p(19,"Almoez Ali","Forward"), p(24,"Tahsin Mohammed Jamshid","Forward"),
    ]),
    "Haiti": team([
        p(1,"Johny Placide","Goalkeeper"), p(12,"Alexandre Pierre","Goalkeeper"), p(23,"Josué Duverger","Goalkeeper"),
        p(2,"Carlens Arcus","Defender"), p(3,"Keeto Thermoncy","Defender"), p(4,"Ricardo Adé","Defender"), p(5,"Hannes Delcroix","Defender"), p(8,"Martin Expérience","Defender"), p(13,"Duke Lacroix","Defender"), p(14,"Garven Metusala","Defender"), p(22,"Jean-Kévin Duverne","Defender"), p(24,"Wilguens Paugain","Defender"),
        p(6,"Carl Fred Sainté","Midfielder"), p(10,"Jean-Ricner Bellegarde","Midfielder"), p(17,"Danley Jean Jacques","Midfielder"), p(25,"Dominique Simon","Midfielder"), p(26,"Woodensky Pierre","Midfielder"),
        p(7,"Derrick Etienne Jr","Forward"), p(9,"Duckens Nazon","Forward"), p(11,"Louicius Deedson","Forward"), p(15,"Ruben Providence","Forward"), p(16,"Lenny Joseph","Forward"), p(18,"Wilson Isidor","Forward"), p(19,"Yassin Fortuné","Forward"), p(20,"Frantzdy Pierrot","Forward"), p(21,"Josué Casimir","Forward"),
    ]),
    "Scotland": team([
        p(1,"Angus Gunn","Goalkeeper"), p(12,"Liam Kelly","Goalkeeper"), p(21,"Craig Gordon","Goalkeeper"),
        p(2,"Aaron Hickey","Defender"), p(3,"Andy Robertson","Defender"), p(5,"Grant Hanley","Defender"), p(6,"Kieran Tierney","Defender"), p(13,"Jack Hendry","Defender"), p(15,"John Souttar","Defender"), p(16,"Dominic Hyam","Defender"), p(22,"Nathan Patterson","Defender"), p(24,"Anthony Ralston","Defender"), p(26,"Scott McKenna","Defender"),
        p(4,"Scott McTominay","Midfielder"), p(7,"John McGinn","Midfielder"), p(8,"Tyler Fletcher","Midfielder"), p(11,"Ryan Christie","Midfielder"), p(19,"Lewis Ferguson","Midfielder"), p(23,"Kenny McLean","Midfielder"),
        p(9,"Lyndon Dykes","Forward"), p(10,"Ché Adams","Forward"), p(14,"Ross Stewart","Forward"), p(17,"Ben Gannon-Doak","Forward"), p(18,"George Hirst","Forward"), p(20,"Lawrence Shankland","Forward"), p(25,"Findlay Curtis","Forward"),
    ]),
    "Turkey": team([
        p(1,"Mert Gunok","Goalkeeper"), p(12,"Altay Bayindir","Goalkeeper"), p(23,"Ugurcan Cakir","Goalkeeper"),
        p(2,"Zeki Celik","Defender"), p(3,"Merih Demiral","Defender"), p(4,"Caglar Soyuncu","Defender"), p(13,"Eren Elmali","Defender"), p(14,"Abdulkerim Bardakci","Defender"), p(15,"Ozan Kabak","Defender"), p(18,"Mert Muldur","Defender"), p(20,"Ferdi Kadioglu","Defender"), p(22,"Kaan Ayhan","Defender"), p(25,"Samet Akaydin","Defender"),
        p(5,"Salih Ozcan","Midfielder"), p(6,"Orkun Kokcu","Midfielder"), p(8,"Arda Guler","Midfielder"), p(10,"Hakan Calhanoglu","Midfielder"), p(16,"Ismail Yuksek","Midfielder"), p(26,"Can Uzun","Midfielder"),
        p(7,"Kerem Akturkoglu","Forward"), p(9,"Deniz Gul","Forward"), p(11,"Kenan Yildiz","Forward"), p(17,"Irfan Can Kahveci","Forward"), p(19,"Yunus Akgun","Forward"), p(21,"Baris Alper Yilmaz","Forward"), p(24,"Oguz Aydin","Forward"),
    ]),
    "Curacao": team([
        p(1,"Eloy Room","Goalkeeper"), p(25,"Tyrick Bodak","Goalkeeper"), p(26,"Trevor Doornbusch","Goalkeeper"),
        p(2,"Shurandy Sambo","Defender"), p(3,"Juriën Gaari","Defender"), p(4,"Roshon van Eijma","Defender"), p(5,"Sherel Floranus","Defender"), p(18,"Armando Obispo","Defender"), p(20,"Joshua Brenet","Defender"), p(23,"Riechedly Bazoer","Defender"), p(24,"Deveron Fonville","Defender"),
        p(6,"Godfried Roemeratoe","Midfielder"), p(7,"Juninho Bacuna","Midfielder"), p(8,"Livano Comenencia","Midfielder"), p(10,"Leandro Bacuna","Midfielder"), p(13,"Tyrese Noslin","Midfielder"), p(15,"Ar'jany Martha","Midfielder"), p(22,"Kevin Felida","Midfielder"),
        p(9,"Jürgen Locadia","Forward"), p(11,"Jeremy Antonisse","Forward"), p(12,"Sontje Hansen","Forward"), p(14,"Kenji Gorré","Forward"), p(16,"Jearl Margaritha","Forward"), p(17,"Brandley Kuwas","Forward"), p(19,"Gervane Kastaneer","Forward"), p(21,"Tahith Chong","Forward"),
    ]),
    "Ecuador": team([
        p(1,"Hernán Galíndez","Goalkeeper"), p(12,"Moisés Ramírez","Goalkeeper"), p(22,"Gonzalo Valle","Goalkeeper"),
        p(2,"Félix Torres","Defender"), p(3,"Piero Hincapié","Defender"), p(4,"Joel Ordóñez","Defender"), p(6,"Willian Pacho","Defender"), p(7,"Pervis Estupiñán","Defender"), p(17,"Ángelo Preciado","Defender"), p(25,"Jackson Porozo","Defender"), p(26,"Yaimar Medina","Defender"),
        p(5,"Jordy Alcívar","Midfielder"), p(18,"Denil Castillo","Midfielder"), p(21,"Alan Franco","Midfielder"), p(23,"Moisés Caicedo","Midfielder"),
        p(8,"Anthony Valencia","Forward"), p(9,"John Yeboah","Forward"), p(10,"Kendry Páez","Forward"), p(11,"Kevin Rodríguez","Forward"), p(13,"Enner Valencia","Forward"), p(14,"Alan Minda","Forward"), p(15,"Pedro Vite","Forward"), p(16,"Jordy Caicedo","Forward"), p(19,"Gonzalo Plata","Forward"), p(20,"Nilson Angulo","Forward"), p(24,"Jeremy Arévalo","Forward"),
    ]),
    "Sweden": team([
        p(1,"Jacob Widell Zetterström","Goalkeeper"), p(12,"Viktor Johansson","Goalkeeper"), p(23,"Kristoffer Nordfeldt","Goalkeeper"),
        p(2,"Gustaf Lagerbielke","Defender"), p(3,"Victor Lindelöf","Defender"), p(4,"Isak Hien","Defender"), p(5,"Gabriel Gudmundsson","Defender"), p(6,"Herman Johansson","Defender"), p(8,"Daniel Svensson","Defender"), p(14,"Hjalmar Ekdal","Defender"), p(15,"Carl Starfelt","Defender"), p(20,"Eric Smith","Defender"), p(24,"Elliot Stroud","Defender"),
        p(7,"Lucas Bergvall","Midfielder"), p(13,"Ken Sema","Midfielder"), p(16,"Jesper Karlström","Midfielder"), p(18,"Yasin Ayari","Midfielder"), p(19,"Mattias Svanberg","Midfielder"), p(21,"Alexander Bernhardsson","Midfielder"), p(22,"Besfort Zeneli","Midfielder"),
        p(9,"Alexander Isak","Forward"), p(10,"Benjamin Nygren","Forward"), p(11,"Anthony Elanga","Forward"), p(17,"Viktor Gyökeres","Forward"), p(25,"Gustaf Nilsson","Forward"), p(26,"Taha Ali","Forward"),
    ]),
    "Tunisia": team([
        p(1,"Mouhib Chamakh","Goalkeeper"), p(16,"Aymen Dahmen","Goalkeeper"), p(22,"Sabri Ben Hessen","Goalkeeper"),
        p(2,"Ali Abdi","Defender"), p(3,"Montassar Talbi","Defender"), p(4,"Omar Rekik","Defender"), p(5,"Adem Arous","Defender"), p(6,"Dylan Bronn","Defender"), p(20,"Yan Valery","Defender"), p(21,"Mohamed Amine Ben Hmida","Defender"), p(23,"Moutaz Neffati","Defender"), p(24,"Raed Chikhaoui","Defender"),
        p(10,"Hannibal Mejbri","Midfielder"), p(11,"Ismaël Gharbi","Midfielder"), p(12,"Mortadha Ben Ouanes","Midfielder"), p(13,"Rani Khedira","Midfielder"), p(15,"Hadj Mahmoud","Midfielder"), p(17,"Ellyes Skhiri","Midfielder"), p(25,"Anis Ben Slimane","Midfielder"),
        p(7,"Elias Achouri","Forward"), p(8,"Elias Saad","Forward"), p(9,"Hazem Mastouri","Forward"), p(14,"Khalil Ayari","Forward"), p(18,"Rayan Elloumi","Forward"), p(19,"Firas Chaouat","Forward"), p(26,"Sebastien Tounekti","Forward"),
    ]),
    "Iran": team([
        p(1,"Alireza Beiranvand","Goalkeeper"), p(12,"Payam Niazmand","Goalkeeper"), p(22,"Seyed Hossein Hosseini","Goalkeeper"),
        p(2,"Saleh Hardani","Defender"), p(3,"Ehsan Hajsafi","Defender"), p(4,"Shoja Khalilzadeh","Defender"), p(5,"Milad Mohammadi","Defender"), p(13,"Hossein Kanaani-Zadegan","Defender"), p(17,"Aria Yousefi","Defender"), p(19,"Ali Nemati","Defender"), p(23,"Ramin Rezaeian","Defender"), p(25,"Danial Eiri","Defender"),
        p(6,"Saeid Ezatolahi","Midfielder"), p(14,"Saman Ghoddos","Midfielder"), p(15,"Rouzbeh Cheshmi","Midfielder"), p(21,"Mohammad Ghorbani","Midfielder"), p(26,"Amirmohammad Razzaghinia","Midfielder"),
        p(7,"Alireza Jahanbakhsh","Forward"), p(8,"Mohammad Mohebi","Forward"), p(9,"Mehdi Taremi","Forward"), p(10,"Mehdi Ghaedi","Forward"), p(11,"Ali Alipour","Forward"), p(16,"Mehdi Torabi","Forward"), p(18,"Amirhossein Hosseinzadeh","Forward"), p(20,"Shahriar Moghanloo","Forward"), p(24,"Dennis-Yerai Eckert Ayensa","Forward"),
    ]),
    "New Zealand": team([
        p(1,"Max Crocombe","Goalkeeper"), p(12,"Alex Paulsen","Goalkeeper"), p(22,"Michael Woud","Goalkeeper"),
        p(2,"Tim Payne","Defender"), p(3,"Francis de Vries","Defender"), p(4,"Tyler Bindon","Defender"), p(5,"Michael Boxall","Defender"), p(13,"Liberato Cacace","Defender"), p(15,"Nando Pijnaker","Defender"), p(16,"Finn Surman","Defender"), p(24,"Callan Elliot","Defender"), p(26,"Tommy Smith","Defender"),
        p(6,"Joe Bell","Midfielder"), p(8,"Marko Stamenic","Midfielder"), p(10,"Sarpreet Singh","Midfielder"), p(14,"Alex Rufer","Midfielder"), p(23,"Ryan Thomas","Midfielder"), p(25,"Lachlan Bayliss","Midfielder"),
        p(7,"Logan Rogerson","Forward"), p(9,"Chris Wood","Forward"), p(11,"Eli Just","Forward"), p(17,"Kosta Barbarouses","Forward"), p(18,"Ben Waine","Forward"), p(19,"Ben Old","Forward"), p(20,"Callum McCowatt","Forward"), p(21,"Jesse Randall","Forward"),
    ]),
    "Saudi Arabia": team([
        p(1,"Nawaf al-Aqidi","Goalkeeper"), p(21,"Mohammed al-Owais","Goalkeeper"), p(22,"Ahmed al-Kassar","Goalkeeper"),
        p(2,"Ali Majrashi","Defender"), p(3,"Ali Lajami","Defender"), p(4,"Abdulelah al-Amri","Defender"), p(5,"Hassan al-Tambakti","Defender"), p(12,"Saud Abdulhamid","Defender"), p(13,"Nawaf Boushal","Defender"), p(14,"Hassan Kadesh","Defender"), p(24,"Moteb al-Harbi","Defender"), p(25,"Jehad Thakri","Defender"), p(26,"Mohammed Abu al-Shamat","Defender"),
        p(6,"Nasser al-Dawsari","Midfielder"), p(7,"Musab al-Juwayr","Midfielder"), p(8,"Ayman Yahya","Midfielder"), p(15,"Abdullah al-Khaibari","Midfielder"), p(16,"Ziyad al-Johani","Midfielder"), p(17,"Khalid al-Ghannam","Midfielder"), p(18,"Alaa al-Hejji","Midfielder"), p(23,"Mohamed Kanno","Midfielder"),
        p(9,"Firas al-Buraikan","Forward"), p(10,"Salem al-Dawsari","Forward"), p(11,"Saleh al-Shehri","Forward"), p(19,"Abdullah al-Hamdan","Forward"), p(20,"Sultan Mandash","Forward"),
    ]),
    "Iraq": team([
        p(1,"Fahad Talib","Goalkeeper"), p(12,"Jalal Hassan","Goalkeeper"), p(22,"Ahmed Basil","Goalkeeper"),
        p(2,"Rebin Sulaka","Defender"), p(3,"Hussein Ali","Defender"), p(4,"Zaid Tahseen","Defender"), p(5,"Akam Hashim","Defender"), p(6,"Manaf Younis","Defender"), p(15,"Ahmed Maknzi","Defender"), p(23,"Merchas Doski","Defender"), p(25,"Mustafa Saadoon","Defender"), p(26,"Frans Putros","Defender"),
        p(7,"Youssef Amyn","Midfielder"), p(8,"Ibrahim Bayesh","Midfielder"), p(11,"Ahmed Qasem","Midfielder"), p(14,"Zidane Iqbal","Midfielder"), p(16,"Amir Al-Ammari","Midfielder"), p(19,"Kevin Yakob","Midfielder"), p(20,"Aimar Sher","Midfielder"), p(24,"Zaid Ismail","Midfielder"),
        p(9,"Ali Al-Hamadi","Forward"), p(10,"Mohanad Ali","Forward"), p(13,"Ali Yousif","Forward"), p(17,"Ali Jasim","Forward"), p(18,"Aymen Hussein","Forward"), p(21,"Marko Farji","Forward"),
    ]),
    "Jordan": team([
        p(1,"Yazeed Abulaila","Goalkeeper"), p(12,"Nour Bani Attiah","Goalkeeper"), p(22,"Abdallah al-Fakhouri","Goalkeeper"),
        p(2,"Mohammad Abu Hashish","Defender"), p(3,"Abdallah Nasib","Defender"), p(4,"Husam Abu Dahab","Defender"), p(5,"Yazan al-Arab","Defender"), p(16,"Mohammad Abualnadi","Defender"), p(17,"Salim Obaid","Defender"), p(19,"Saed al-Rosan","Defender"), p(20,"Mohannad Abu Taha","Defender"), p(23,"Ehsan Haddad","Defender"), p(26,"Anas Badawi","Defender"),
        p(6,"Amer Jamous","Midfielder"), p(8,"Noor al-Rawabdeh","Midfielder"), p(14,"Rajaei Ayed","Midfielder"), p(15,"Ibrahim Sadeh","Midfielder"), p(21,"Nizar al-Rashdan","Midfielder"), p(25,"Mohammad al-Dawoud","Midfielder"),
        p(7,"Mohammad Abu Zrayq","Forward"), p(9,"Ali Olwan","Forward"), p(10,"Musa al-Taamari","Forward"), p(11,"Odeh al-Fakhouri","Forward"), p(13,"Mahmoud al-Mardi","Forward"), p(18,"Mohammad Abu Ghoush","Forward"), p(24,"Ali Azaizeh","Forward"),
    ]),
    "Uzbekistan": team([
        p(1,"Utkir Yusupov","Goalkeeper"), p(12,"Abduvokhid Nematov","Goalkeeper"), p(16,"Botirali Ergashev","Goalkeeper"),
        p(2,"Abdukodir Khusanov","Defender"), p(3,"Khojiakbar Alijonov","Defender"), p(4,"Farrukh Sayfiev","Defender"), p(5,"Rustam Ashurmatov","Defender"), p(13,"Sherzod Nasrullaev","Defender"), p(15,"Umar Eshmurodov","Defender"), p(18,"Abdulla Abdullaev","Defender"), p(24,"Bekhruz Karimov","Defender"), p(25,"Avazbek Ulmasaliev","Defender"), p(26,"Jakhongir Urozov","Defender"),
        p(6,"Akmal Mozgovoy","Midfielder"), p(7,"Otabek Shukurov","Midfielder"), p(8,"Jamshid Iskanderov","Midfielder"), p(9,"Odiljon Khamrobekov","Midfielder"), p(19,"Azizjon Ganiev","Midfielder"), p(20,"Azizbek Amonov","Midfielder"), p(22,"Abbosbek Fayzullaev","Midfielder"), p(23,"Sherzod Esanov","Midfielder"),
        p(10,"Ruslanbek Jiyanov","Forward"), p(11,"Oston Urunov","Forward"), p(14,"Eldor Shomurodov","Forward"), p(17,"Dostonbek Khamdamov","Forward"), p(21,"Igor Sergeev","Forward"),
    ]),
    "Panama": team([
        p(1,"Luis Mejía","Goalkeeper"), p(12,"César Samudio","Goalkeeper"), p(22,"Orlando Mosquera","Goalkeeper"),
        p(2,"César Blackman","Defender"), p(3,"José Córdoba","Defender"), p(4,"Fidel Escobar","Defender"), p(5,"Edgardo Fariña","Defender"), p(13,"Jiovany Ramos","Defender"), p(15,"Eric Davis","Defender"), p(16,"Andrés Andrade","Defender"), p(23,"Michael Amir Murillo","Defender"), p(25,"Roderick Miller","Defender"), p(26,"Jorge Gutiérrez","Defender"),
        p(6,"Cristian Martínez","Midfielder"), p(8,"Adalberto Carrasquilla","Midfielder"), p(14,"Carlos Harvey","Midfielder"), p(20,"Aníbal Godoy","Midfielder"),
        p(7,"José Luis Rodríguez","Forward"), p(9,"Tomás Rodríguez","Forward"), p(10,"Ismael Díaz","Forward"), p(11,"Édgar Yoel Bárcenas","Forward"), p(17,"José Fajardo","Forward"), p(18,"Cecilio Waterman","Forward"), p(19,"Alberto Quintero","Forward"), p(21,"César Yanis","Forward"), p(24,"Azarías Londoño","Forward"),
    ]),
}

data = json.loads(OUT.read_text()) if OUT.exists() else {}

added = []
skipped = []
for name, roster in MANUAL.items():
    if name in data and not OVERWRITE_EXISTING:
        skipped.append(name)
        continue
    roster["team"] = name
    data[name] = roster
    added.append(name)

OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

print(f"Added/updated: {len(added)}")
for name in added:
    print("✅", name, len(data[name]["players"]))

if skipped:
    print(f"Skipped existing: {len(skipped)}")
    for name in skipped:
        print("↪", name)

print(f"Total static teams now: {len(data)}")
