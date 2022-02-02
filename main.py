import base64
from typing import List
import zlib
import httpx
import pprint
import xml.etree.cElementTree as ET

PASSIVES_URL = "https://www.pathofexile.com/character-window/get-passive-skills?character={character}&accountName={account}"
ITEMS_URL = "https://www.pathofexile.com/character-window/get-items?character={character}&accountName={account}"
RARITY = ["NORMAL", "MAGIC", "RARE", "UNIQUE"]
VERSION = "3.17"


def fetch_passives(account: str, character: str) -> dict:
    passives_for_profile_url = PASSIVES_URL.format(character=character, account=account)
    response = httpx.get(
        passives_for_profile_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
        },
    )
    # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
    return response.json()


def fetch_items(account: str, character: str) -> dict:
    items_for_profile_url = ITEMS_URL.format(character=character, account=account)
    response = httpx.get(
        items_for_profile_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
        },
    )
    # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
    return response.json()


def pob_code_to_xml(pobcode: str):
    base64_decode = base64.urlsafe_b64decode(pobcode)
    decompressed_xml = zlib.decompress(base64_decode)
    return decompressed_xml.decode("utf8")


def add_skills_to_xml(xml, items: List):
    skills = ET.SubElement(
        xml,
        "Skills",
        defaultGemQuality="nil",
        defaultGemLevel="nil",
        sortGemsByDPS="true",
    )
    for item in items:
        if "socketedItems" in item:
            skill = ET.SubElement(
                skills,
                "Skill",
                mainActiveSkillCalcs="nil",
                mainActiveSkill="nil",
                enabled="true",
                slot=fix_name(item["inventoryId"]),
            )
            for socketed_item in item["socketedItems"]:
                if socketed_item["frameType"] != 4:
                    continue

                gem_name = socketed_item["typeLine"]
                if "Support" in gem_name:
                    fixed_name = gem_name.replace(" Support", "")
                    gem_name = f"Support {fixed_name}"
                    name_spec = gem_name.replace("Support ", "")
                else:
                    name_spec = gem_name

                skill_id = gem_name.replace(" ", "")

                level = "1"
                quality = "0"

                for property in socketed_item["properties"]:
                    pass

                ET.SubElement(
                    skill,
                    "Gem",
                    level=str(level),
                    skillId=str(skill_id),
                    quality=str(quality),
                    enabled="true",
                    nameSpec=str(name_spec),
                )


def add_items_to_xml(xml, items: List):
    xml_items = ET.SubElement(xml, "Items", activeItemSet="1", useSecondWeaponSet="nil")
    slots = []

    #### Items
    for i, item in enumerate(items):
        slots.append(fix_name(item["inventoryId"]))
        item_string = f"Rarity: {RARITY[item['frameType']]}\r\n"

        if item["name"]:
            item_string += (
                item["name"].replace("<<set:MS>><<set:M>><<set:S>>", "").lstrip()
                + "\r\n"
            )

        if item["typeLine"]:
            item_string += (
                item["typeLine"].replace("<<set:MS>><<set:M>><<set:S>>", "").lstrip()
                + "\r\n"
            )

        item_string += f"ID: {item['id']}\r\n"

        if "requirements" in item and item["requirements"][0]["name"] == "Level":
            item_string += f"Item Level: {item['requirements'][0]['values'][0][0]}\r\n"

        if "properties" in item and item["properties"][0]["name"] == "Quality":
            item_string += f"Quality: {item['properties'][0]['values'][0][0].replace('%', '').replace('+', '')}\r\n"

        if "sockets" in item:
            # TODO: Does this really work? What about R-R-B R-G R for example
            colors = []
            groups = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
            for socket in item["sockets"]:
                groups[socket["group"]].append(socket["sColour"])
            for _, group in groups.items():
                if not group:
                    continue
                colors.append("-".join(group))
            item_string += f"Sockets: {' '.join(colors)}\r\n"

        item_string += f"Implicits: {len(item.get('implicitMods', []))}\r\n"
        if "implicitMods" in item:
            item_string += item["implicitMods"][0] + "\r\n"

        if "explicitMods" in item:
            for explicit_mod in item["explicitMods"]:
                item_string += explicit_mod + "\r\n"

        # TODO: Implementation says to just use craftedMods[0], sounds wrong?
        if "craftedMods" in item:
            for crafted_mod in item["craftedMods"]:
                item_string += "{crafted}" + crafted_mod + "\r\n"

        xml_item = ET.SubElement(xml_items, "Item")
        xml_item.text = "\r\n" + item_string

    #### Slots
    for i, slot in enumerate(slots):
        if slot == "PassiveJewels":
            continue

        ET.SubElement(xml_items, "Slot", name=slot, itemId=str(i))

    #### Abyss
    items_with_abyss_sockets = ["BodyArmour", "Belt", "Helm", "Boots", "Gloves"]
    abyss_items = filter(
        lambda x: x["inventoryId"] in items_with_abyss_sockets and "socketedItems" in x,
        items,
    )
    abyss_jewels = dict()
    for item in abyss_items:
        for i, socket in enumerate(item["socketedItems"]):
            if socket["properties"][0]["name"] == "Abyss":
                slot_name = f"{fix_name(item['inventoryId'])} Abyssal Socket {i}"
                abyss_jewels[slot_name] = socket

    item_id = len(items)
    for slot_name, item in abyss_jewels.items():
        item_id += 1
        item_string = f"Rarity: {RARITY[item['frameType']]}\r\n"
        if item["name"]:
            item_string += (
                item["name"].replace("<<set:MS>><<set:M>><<set:S>>", "").lstrip()
                + "\r\n"
            )
        if item["typeLine"]:
            item_string += (
                item["typeLine"].replace("<<set:MS>><<set:M>><<set:S>>", "").lstrip()
                + "\r\n"
            )

        item_string += f"ID: {item['id']}\r\n"

        if "requirements" in item and item["requirements"][0]["name"] == "Level":
            item_string += f"Item Level: {item['requirements'][0]['values'][0][0]}\r\n"

        if "explicitMods" in item:
            for explicit_mod in item["explicitMods"]:
                item_string += explicit_mod + "\r\n"

        xml_item = ET.SubElement(xml_items, "Item")
        xml_item.text = "\r\n" + item_string

        ET.SubElement(xml_items, "Slot", name=slot_name, item_id=str(item_id))


def fix_name(name):
    if name == "Weapon2":
        return "Weapon 1 Swap"
    if name == "Ring2":
        return "Ring 2"
    if "Weapon" in name or "Ring" in name:
        return f"{name} 1"
    if name == "Offhand":
        return "Weapon 2"
    if name == "Offhand2":
        return "Weapon 2 Swap"
    if name == "Helm":
        return "Helmet"
    if name == "BodyArmour":
        return "Body Armour"
    return name


def get_jewel_coords(tree_data):
    jewel_ids = {
        0: {"location": "Marauder", "id": 26725},
        1: {"location": "Templar_Witch", "id": 36634},
        2: {"location": "Shadow_Ranger", "id": 33989},
        3: {"location": "Witch_Shadow", "id": 41263},
        4: {"location": "Ranger", "id": 60735},
        5: {"location": "Shadow", "id": 61834},
        6: {"location": "Scion_Bottom", "id": 31683},
        7: {"location": "Duelist_Marauder", "id": 28475},
        8: {"location": "Scion_Left", "id": 6230},
        9: {"location": "Scion_Right", "id": 48768},
        10: {"location": "Ranger_Duelist", "id": 34483},
        11: {"location": "Templar_Witch2", "id": 7960},
        12: {"location": "Ranger_Duelist2", "id": 46882},
        13: {"location": "Marauder_Templar2", "id": 55190},
        14: {"location": "Witch", "id": 61419},
        15: {"location": "Duelist_Marauder2", "id": 2491},
        16: {"location": "Duelist", "id": 54127},
        17: {"location": "Shadow_Ranger2", "id": 32763},
        18: {"location": "Templar", "id": 26196},
        19: {"location": "Marauder_Templar", "id": 33631},
        20: {"location": "Witch_Shadow2", "id": 21984},
    }
    jewels = dict()

    for i, item in enumerate(tree_data["items"]):
        if item["x"] > 20:
            continue

        jewel_id = jewel_ids[item["x"]]["id"]
        jewels[jewel_id] = i + 1

    return jewels


def get_tree_url(char_details, passives):
    header = [
        0,
        0,
        0,
        4,
        int(char_details["classId"]),
        int(char_details["ascendancyClass"]),
        0,
    ]
    bytes = bytearray(header)
    for node in passives:
        bytes.append(node // 256)
        bytes.append(node % 256)

    return (
        "https://www.pathofexile.com/fullscreen-passive-skill-tree/"
        + base64.b64encode(bytes, altchars=b"-_").decode("utf-8")
    )


def add_tree_to_xml(xml, items_data, tree_data, jewel_coords):
    char_details = items_data["character"]
    tree = ET.SubElement(xml, "Tree", activeSpec="1")
    spec = ET.SubElement(tree, "Spec", treeVersion=VERSION.replace(".", "_"))
    url = ET.SubElement(spec, "URL")
    tree_url = get_tree_url(char_details, tree_data["hashes"])
    url.text = tree_url
    sockets = ET.SubElement(spec, "Sockets")
    for coord in jewel_coords:
        ET.SubElement(
            sockets,
            "Socket",
            nodeId=str(coord),
            itemId=str(jewel_coords[coord]) if coord in jewel_coords else "0",
        )


def pob_profile_to_pob_code(items_data, tree_data):
    class_ids = ["Scion", "Marauder", "Ranger", "Witch", "Duelist", "Templar", "Shadow"]

    root = ET.Element("PathOfBuilding")
    ET.SubElement(
        root,
        "Build",
        level=str(items_data["character"]["level"]),
        targetVersion=VERSION.replace(".", "_"),
        bandit="None",
        className=class_ids[items_data["character"]["classId"]],
        ascendClassName=items_data["character"]["class"],
        mainSocketGroup="1",
        viewMode="CALCS",
    )
    ET.SubElement(root, "Import")
    ET.SubElement(root, "Calcs")
    add_skills_to_xml(root, items_data["items"])
    all_items = [*items_data["items"], *tree_data["items"]]
    add_items_to_xml(root, all_items)
    add_tree_to_xml(root, items_data, tree_data, get_jewel_coords(tree_data))
    ET.SubElement(root, "Notes")
    ET.SubElement(
        root,
        "TreeView",
        searchStr="",
        zoomY="-70.680703089277",
        zoomX="-274.36201953303",
        showHeatMap="false",
        zoomLevel="2",
        showStatDifference="true",
    )
    ET.SubElement(root, "Config")

    tree = ET.ElementTree(root)
    ET.indent(root, space=" ", level=0)
    tree.write("testing.xml")


# print(fetch_items("roxalot", "HodorHeist")["character"])
# print(fetch_items("roxalot", "HodorHeist")["items"])
# print(fetch_passives("aaaaroxalot", "HodorHeist"))

acc = "comoestoy"
char = "ChaseUniqueChaser"

pob_profile_to_pob_code(fetch_items(acc, char), fetch_passives(acc, char))
