import urllib.request, json 
import requests
from lzma import FORMAT_AUTO, LZMAError, LZMADecompressor
import re
import string
import os
from pathlib import Path

def download_weapons(save_file=False):
    current_folder = Path(__file__).parent.resolve()
    endpoints = get_endpoints(["ExportWeapons_en.json", "ExportUpgrades_en.json"])

    if "ExportWeapons_en.json" not in endpoints:
        raise Exception("Failed to download ExportWeapons_en.json")
    
    if "ExportUpgrades_en.json" not in endpoints:
        raise Exception("Failed to download ExportUpgrades_en.json")
    
    weeklyRivensURL = 'https://n9e5v4d8.ssl.hwcdn.net/repos/weeklyRivensPC.json'
    upgradesURL = f'http://content.warframe.com/PublicExport/Manifest/{endpoints["ExportUpgrades_en.json"]}'
    exportWeaponsURL = f'http://content.warframe.com/PublicExport/Manifest/{endpoints["ExportWeapons_en.json"]}'

    with urllib.request.urlopen(weeklyRivensURL) as url:
        text = url.read().decode()
        regex = re.compile(r'[\n\r\t]')
        text = regex.sub(" ", text)
        weeklyRivensData = json.loads(text)

    with urllib.request.urlopen(upgradesURL) as url:
        text = url.read().decode()
        regex = re.compile(r'[\n\r\t]')
        text = regex.sub(" ", text)
        upgradesData = json.loads(text)

    with urllib.request.urlopen(exportWeaponsURL) as url:
        text = url.read().decode()
        regex = re.compile(r'[\n\r\t]')
        text = regex.sub(" ", text)
        exportWeaponsData = json.loads(text)

    export_rivens = []
    for elem in upgradesData["ExportUpgrades"]:
        if "upgradeEntries" not in elem: 
            continue
        if 'Riven Mod' not in elem.get('name', ''):
            continue
        export_rivens.append(elem)

    # save to file
    with open(os.path.join(current_folder, "data", "ExportRivenUpgrades.json"), 'w') as fout:
        json.dump(export_rivens, fout)

    # with open(os.path.join(current_folder, "data", "weeklyRivens.json"), 'w') as fout:
    #     json.dump(weeklyRivensData, fout)

    weapon_list = exportWeaponsData["ExportWeapons"]
    reformat_data = {}
    for wep in weapon_list:
        if wep['totalDamage'] == 0:
            #weapon does 0 damage, skip
            continue
        useless_property = ['codexSecret', 'description', 'masteryReq', 'slot']
        for prop in useless_property:
            wep.pop(prop, None)

        wepname = string.capwords(wep['name'])
        generic_property = ['name', 'uniqueName', "productCategory", "omegaAttenuation"]
        reformat_data[wepname] = {key:value for key,value in wep.items() if key in generic_property}
        for prop in generic_property:
            wep.pop(prop, None)

        wep["ammoCost"] = 0.5 if "HELD" in wep.get("trigger","") else 1
        wep["chargeTime"] = 0
        wep["forcedProc"] = []
        wep["secondaryEffects"] = {}

        # add riven type
        for elem in weeklyRivensData:
            s1 = elem.get("compatibility", ",.~~~~`")
            if s1 is None:
                continue
            s2 = " " + s1
            s3 = s1 + " "
            if s1 == wepname or s2 in wepname or s3 in wepname:
                reformat_data[wepname]["rivenType"] = elem["itemType"]
                break

        reformat_data[wepname]["fireModes"] = {"default":wep}

    if save_file:
        with open(os.path.join(current_folder, "data", "ExportWeapons.json"), 'w') as fout:
            json.dump(reformat_data, fout)

    return reformat_data


def get_endpoints(endpoint_list):
    response = requests.get('http://content.warframe.com/PublicExport/index_en.txt.lzma')
    data = response.content
    byt = bytes(data)
    length = len(data)
    for i in range(length-1, 0, -1):
        try:
            decompress_lzma(byt[:i])
        except LZMAError:
            length -= 1
            continue
        break

    spl = decompress_lzma(byt[:i]).decode().split("\r\n")
    result = {}
    for endpoint in endpoint_list:
        for line in spl:
            if endpoint in line:
                result[endpoint] = line
                break
    return result

def decompress_lzma(data):
    results = []
    while True:
        decomp = LZMADecompressor(FORMAT_AUTO, None, None)
        try:
            res = decomp.decompress(data)
        except LZMAError:
            if results:
                break  # Leftover data is not a valid LZMA/XZ stream; ignore it.
            else:
                raise  # Error on the first iteration; bail out.
        results.append(res)
        data = decomp.unused_data
        if not data:
            break
        if not decomp.eof:
            raise LZMAError("Compressed data ended before the end-of-stream marker was reached")
    return b"".join(results)

download_weapons(save_file=True)