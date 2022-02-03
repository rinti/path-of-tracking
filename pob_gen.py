from typing import List
import base64
import xml.etree.cElementTree as ET
import httpx
import zlib
from typing import List

PASSIVES_URL = "https://www.pathofexile.com/character-window/get-passive-skills?character={character}&accountName={account}"
ITEMS_URL = "https://www.pathofexile.com/character-window/get-items?character={character}&accountName={account}"
RARITY = ["NORMAL", "MAGIC", "RARE", "UNIQUE"]
VERSION = "3.17"


class PobGen:
    def __init__(self, pob_code=None, account_name=None, character_name=None):
        self.root = ET.Element("PathOfBuilding")

        if pob_code:
            pass
        else:
            self.passives = self.fetch_passives(account_name, character_name)
            self.items = self.fetch_items(account_name, character_name)
            self.pob_profile_to_pob_code()

    def write_xml(self, name="generated.xml"):
        tree = ET.ElementTree(self.root)
        ET.indent(self.root, space=" ", level=0)
        tree.write(name)

    def fetch_passives(self, account: str, character: str) -> dict:
        passives_for_profile_url = PASSIVES_URL.format(
            character=character, account=account
        )
        response = httpx.get(
            passives_for_profile_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
            },
        )
        # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
        return response.json()

    def fetch_items(self, account: str, character: str) -> dict:
        items_for_profile_url = ITEMS_URL.format(character=character, account=account)
        response = httpx.get(
            items_for_profile_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
            },
        )
        # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
        return response.json()

    def pob_profile_to_pob_code(self) -> ET.ElementTree:
        class_ids = [
            "Scion",
            "Marauder",
            "Ranger",
            "Witch",
            "Duelist",
            "Templar",
            "Shadow",
        ]

        ET.SubElement(
            self.root,
            "Build",
            level=str(self.items["character"]["level"]),
            targetVersion=VERSION.replace(".", "_"),
            bandit="None",
            className=class_ids[self.items["character"]["classId"]],
            ascendClassName=self.items["character"]["class"],
            mainSocketGroup="1",
            viewMode="CALCS",
        )
        ET.SubElement(self.root, "Import")
        ET.SubElement(self.root, "Calcs")
        self.add_skills_to_xml(self.items["items"])
        all_items = [*self.items["items"], *self.passives["items"]]
        self.add_items_to_xml(all_items)
        self.add_tree_to_xml(self.get_jewel_coords())
        ET.SubElement(self.root, "Notes")
        ET.SubElement(
            self.root,
            "TreeView",
            searchStr="",
            zoomY="-70.680703089277",
            zoomX="-274.36201953303",
            showHeatMap="false",
            zoomLevel="2",
            showStatDifference="true",
        )
        ET.SubElement(self.root, "Config")

        tree = ET.ElementTree(self.root)
        ET.indent(self.root, space=" ", level=0)
        return tree

    def get_jewel_coords(self):
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

        for i, item in enumerate(self.passives["items"]):
            if item["x"] > 20:
                continue

            jewel_id = jewel_ids[item["x"]]["id"]
            jewels[jewel_id] = i + 1

        return jewels

    def add_items_to_xml(self, items):
        root_items = ET.SubElement(
            self.root, "Items", activeItemSet="1", useSecondWeaponSet="nil"
        )
        slots = []

        #### Items
        for i, item in enumerate(items):
            slots.append(self.fix_name(item["inventoryId"]))
            item_string = f"Rarity: {RARITY[item['frameType']]}\r\n"

            if item["name"]:
                item_string += (
                    item["name"].replace("<<set:MS>><<set:M>><<set:S>>", "").lstrip()
                    + "\r\n"
                )

            if item["typeLine"]:
                item_string += (
                    item["typeLine"]
                    .replace("<<set:MS>><<set:M>><<set:S>>", "")
                    .lstrip()
                    + "\r\n"
                )

            item_string += f"ID: {item['id']}\r\n"

            if "requirements" in item and item["requirements"][0]["name"] == "Level":
                item_string += (
                    f"Item Level: {item['requirements'][0]['values'][0][0]}\r\n"
                )

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

            xml_item = ET.SubElement(root_items, "Item")
            xml_item.text = "\r\n" + item_string

        #### Slots
        for i, slot in enumerate(slots):
            if slot == "PassiveJewels":
                continue

            ET.SubElement(root_items, "Slot", name=slot, itemId=str(i))

        #### Abyss
        items_with_abyss_sockets = ["BodyArmour", "Belt", "Helm", "Boots", "Gloves"]
        abyss_items = filter(
            lambda x: x["inventoryId"] in items_with_abyss_sockets
            and "socketedItems" in x,
            items,
        )
        abyss_jewels = dict()
        for item in abyss_items:
            for i, socket in enumerate(item["socketedItems"]):
                if socket["properties"][0]["name"] == "Abyss":
                    slot_name = (
                        f"{self.fix_name(item['inventoryId'])} Abyssal Socket {i}"
                    )
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
                    item["typeLine"]
                    .replace("<<set:MS>><<set:M>><<set:S>>", "")
                    .lstrip()
                    + "\r\n"
                )

            item_string += f"ID: {item['id']}\r\n"

            if "requirements" in item and item["requirements"][0]["name"] == "Level":
                item_string += (
                    f"Item Level: {item['requirements'][0]['values'][0][0]}\r\n"
                )

            if "explicitMods" in item:
                for explicit_mod in item["explicitMods"]:
                    item_string += explicit_mod + "\r\n"

            xml_item = ET.SubElement(root_items, "Item")
            xml_item.text = "\r\n" + item_string

            ET.SubElement(root_items, "Slot", name=slot_name, item_id=str(item_id))

    def add_tree_to_xml(self, jewel_coords):
        masteries = self.get_masteries()

        tree = ET.SubElement(self.root, "Tree", activeSpec="1")
        spec = ET.SubElement(
            tree,
            "Spec",
            treeVersion=VERSION.replace(".", "_"),
            ascendClassId=str(self.items["character"]["ascendancyClass"]),
            masteryEffects=masteries,
            nodes=",".join(map(str, self.passives["hashes"])),
        )
        url = ET.SubElement(spec, "URL")
        tree_url = self.get_tree_url()
        url.text = tree_url
        sockets = ET.SubElement(spec, "Sockets")
        for coord in jewel_coords:
            ET.SubElement(
                sockets,
                "Socket",
                nodeId=str(coord),
                itemId=str(jewel_coords[coord]) if coord in jewel_coords else "0",
            )

    def get_masteries(self):
        masteries = []

        for k, v in self.passives["jewel_data"].items():
            if "subgraph" in v:
                masteries.extend(
                    map(
                        lambda x: (x[0], x[1]["skill"]),
                        filter(
                            lambda x: x[1].get("isMastery"),
                            v["subgraph"]["nodes"].items(),
                        ),
                    )
                )

        return f",".join(
            "{" + "{one},{two}".format(one=x[0], two=x[1]) + "}" for x in masteries
        )

    def get_tree_url(self):
        header = [
            0,
            0,
            0,
            4,
            int(self.items["character"]["classId"]),
            int(self.items["character"]["ascendancyClass"]),
            0,
        ]
        bytes = bytearray(header)
        for node in self.passives["hashes"]:
            bytes.append(node // 256)
            bytes.append(node % 256)

        return (
            "https://www.pathofexile.com/fullscreen-passive-skill-tree/"
            + base64.b64encode(bytes, altchars=b"-_").decode("utf-8")
        )

    def add_skills_to_xml(self, items: List) -> None:
        skills = ET.SubElement(
            self.root,
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
                    slot=self.fix_name(item["inventoryId"]),
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

    def fix_name(self, name: str) -> str:
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

    def pob_code_to_xml(self, pobcode: str) -> str:
        base64_decode = base64.urlsafe_b64decode(pobcode)
        decompressed_xml = zlib.decompress(base64_decode)
        return decompressed_xml.decode("utf8")

    @classmethod
    def from_pob_code(cls, pob_code):
        assert pob_code
        return cls(pob_code=pob_code)

    @classmethod
    def from_poe_profile(cls, account_name, character_name):
        assert account_name and character_name
        return cls(account_name=account_name, character_name=character_name)
