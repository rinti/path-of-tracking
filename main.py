import base64
import zlib
import httpx
import xml.etree.cElementTree as ET

PASSIVES_URL = "https://www.pathofexile.com/character-window/get-passive-skills?character={character}&accountName={account}"
ITEMS_URL = "https://www.pathofexile.com/character-window/get-items?character={character}&accountName={account}"


def fetch_passives(account: str, character) -> dict:
    passives_for_profile_url = PASSIVES_URL.format(character=character, account=account)
    response = httpx.get(
        passives_for_profile_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
        },
    )
    # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
    return response.json()


def fetch_items(account: str, character) -> dict:
    items_for_profile_url = ITEMS_URL.format(character=character, account=account)
    response = httpx.get(
        items_for_profile_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
        },
    )
    # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
    return response.json()


def pob_code_to_xml(pobcode):
    base64_decode = base64.urlsafe_b64decode(pobcode)
    decompressed_xml = zlib.decompress(base64_decode)
    return decompressed_xml.decode("utf8")


def add_skills_to_xml(xml, items):
    ET.SubElement(xml, "Skills")


def add_items_to_xml(xml):
    ET.SubElement(xml, "Items")


def add_tree_to_xml(xml):
    ET.SubElement(xml, "Tree")


def pob_profile_to_pob_code(items_data, tree_data):
    class_ids = ["Scion", "Marauder", "Ranger", "Witch", "Duelist", "Templar", "Shadow"]

    root = ET.Element("PathOfBuilding")
    ET.SubElement(
        root,
        "Build",
        level=items_data["character"]["level"],
        targetVersion="3_17",
        bandit="None",
        className=class_ids[items_data["character"]["classId"]],
        ascendClassName=items_data["character"]["class"],
        mainSocketGroup="1",
        viewMode="CALCS",
    )
    ET.SubElement(root, "Import")
    ET.SubElement(root, "Calcs")
    all_items = [*items_data["items"], *tree_data["tree_data"]]
    add_skills_to_xml(root, all_items)
    add_items_to_xml(root)
    add_tree_to_xml(root)
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
    tree.write("testing.xml")


print(fetch_items("roxalot", "HodorHeist")["character"])
print(fetch_items("roxalot", "HodorHeist")["items"])
# print(fetch_passives("aaaaroxalot", "HodorHeist"))

acc = "roxalot"
char = "HodorHeist"

pob_profile_to_pob_code(fetch_items(acc, char), fetch_passives(acc, char))
