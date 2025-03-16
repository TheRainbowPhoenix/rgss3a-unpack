from rubymarshal.reader import load
from rubymarshal.classes import RubyObject, UserDef, registry
from struct import *
import json

def convert_str(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'ignore') if value else ""
    return str(value) if value is not None else ""

def get_traits(features):
    return [
        {
            "code": i.attributes.get("@code", 0), 
            "dataId": i.attributes.get("@data_id", 0),
            "value": i.attributes.get("@value", 0)
        } for i in features
    ]

def get_learnings(learnings):
    return [{
        "level": lrn.attributes.get("@level", 1),
        "skillId": lrn.attributes.get("@skill_id", 1),
        "note": convert_str(lrn.attributes.get("@note", ""))
    } for lrn in learnings]

def get_params(params):
    if not params:
        offset = 500
        return [list(range(0 + offset, 100 + offset)) for _ in range(8)]
    
    num_groups=8

    return [
        [params.flags[i] for i in range(offset, len(params.flags), 8)]
        for offset in range(8)
    ]

def get_effects(effects):
    """Convert RPG Maker effects to JSON-serializable format"""
    return [
        {
            "code": effect.attributes.get("@code", 0),
            "dataId": effect.attributes.get("@data_id", 0),
            "value1": effect.attributes.get("@value1", 0),
            "value2": effect.attributes.get("@value2", 0)
        }
        for effect in effects
    ]


def get_damage(dmg, LOGSCRIPTS=False, scriptlog=None):
    """Convert damage data with optional formula logging"""
    if not dmg:
        return {"critical":False,"elementId":0,"formula":"0","type":0,"variance":20}
    
    return {
        "critical": dmg.attributes.get("@critical", False),
        "elementId": dmg.attributes.get("@element_id", 0),
        "formula": str(dmg.attributes.get("@formula", "")),
        "type": dmg.attributes.get("@type", 0),
        "variance": dmg.attributes.get("@variance", 0)
    }


class Actor(RubyObject):
    ruby_class_name = "RPG::Actor"

    def tojson(self):
        parameters = self.attributes.get("@parameters", None)

        return {
            "id": self.attributes.get("@id", 0),
            "battlerName": convert_str(self.attributes.get("@battler_name", "")),
            "characterIndex": self.attributes.get("@character_hue", 0),
            "characterName": convert_str(self.attributes.get("@character_name", "")),
            "classId": self.attributes.get("@class_id", 0),
            "equips": self.attributes.get("@equips", []),
            "faceIndex": self.attributes.get("@face_index", 0),
            "faceName": convert_str(self.attributes.get("@battler_name", "")),
            "traits": get_traits(self.attributes.get("@features", [])),
            "initialLevel": self.attributes.get("@initial_level", 1),
            "maxLevel": self.attributes.get("@final_level", 99),
            "name": convert_str(self.attributes.get("@name", "")),
            "nickname": convert_str(self.attributes.get("@nickname", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "profile": convert_str(self.attributes.get("@description", ""))
        }

class Tileset(RubyObject):
    ruby_class_name = "RPG::Tileset"

    def tojson(self):

        #Convert from rubmarshalstr to str
        tilesetNames = []
        
        for i in self.attributes["@tileset_names"]:
            if i == b'':
                tilesetNames.append("")
            else:
                tilesetNames.append(str(i))

        if self.attributes["@name"] == b'':
            self.attributes["@name"] = ""

        if self.attributes["@note"] == b'':
            self.attributes["@note"] = ""
        

        todump = {
            "id": self.attributes["@id"],
            "flags": self.attributes["@flags"].flags,
            "mode": self.attributes["@mode"],
            "name": str(self.attributes["@name"]),
            "note": str(self.attributes["@note"]),
            "tilesetNames": tilesetNames
        }

        return todump
    
class ClassLearning(RubyObject):
    ruby_class_name = "RPG::Class::Learning"

    def tojson(self):
        return {
            "level": self.attributes.get("@level", 1),
            "skillId": self.attributes.get("@skill_id", 1)
        }

class RPG_Class(RubyObject):
    ruby_class_name = "RPG::Class"

    def tojson(self):

        # Convert parameters table (8 params × 100 levels)
        params_table = self.attributes.get("@params", None)
        params = []
        if params_table:
            for p in range(8):
                param_values = []
                for l in range(100):
                    param_values.append(params_table.flags[p * 100 + l])
                params.append(param_values)

        return {
            "id": self.attributes.get("@id", 0),
            "expParams": self.attributes.get("@exp_params", [30, 20, 30, 30]),
            "traits": get_traits(self.attributes.get("@features", [])),
            "learnings": get_learnings(self.attributes.get("@learnings", [])),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "params": get_params(self.attributes.get("@params", None)),
            
            # "elementRanks": self.attributes.get("@element_ranks", Table()).flags,
            # "stateRanks": self.attributes.get("@state_ranks", Table()).flags,
            # "weaponSet": self.attributes.get("@weapon_set", []),
            # "armorSet": self.attributes.get("@armor_set", []),
            # "position": self.attributes.get("@position", 0)
        }

class Skill(RubyObject):
    ruby_class_name = "RPG::Skill"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "animationId": self.attributes.get("@animation_id", 0),
            "damage": get_damage(self.attributes.get("@damage", None)),
            "description": convert_str(self.attributes.get("@description", "")),
            "effects": get_effects(self.attributes.get("@effects", [])),
            "hitType": self.attributes.get("@hit_type", 0),
            "iconIndex": self.attributes.get("@icon_index", 0),
            "message1": convert_str(self.attributes.get("@message1", "")),
            "message2": convert_str(self.attributes.get("@message2", "")),
            "mpCost": self.attributes.get("@mp_cost", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "occasion": self.attributes.get("@occasion", 0),
            "repeats": self.attributes.get("@repeats", 1),
            "requiredWtypeId1": self.attributes.get("@required_wtype_id1", 0),
            "requiredWtypeId2": self.attributes.get("@required_wtype_id2", 0),
            "scope": self.attributes.get("@scope", 0),
            "speed": self.attributes.get("@speed", 0),
            "stypeId": self.attributes.get("@stype_id", 0),
            "successRate": self.attributes.get("@success_rate", 100),
            "tpCost": self.attributes.get("@tp_cost", 0),
            "tpGain": self.attributes.get("@tp_gain", 0)
        }

class Table(UserDef):
    ruby_class_name = "Table"
    flags = []
    
    def _load(self, private_data):
        # Load table data (6 parameters × 100 levels = 600 elements)
        # Format: 8192 unsigned shorts (enough for RPG Maker's tables)
        size = max((len(private_data) - 0x14) // 2, 0) # 8192 ?
        self.flags = list(unpack(f"@{size}H", private_data[0x14:]))
        return

registry.register(Table)
registry.register(Tileset)
registry.register(Actor)
registry.register(ClassLearning)
registry.register(RPG_Class)
registry.register(Skill)
    
import json
import argparse
import sys
from dataclasses import dataclass


def main():

    with open("OUT/Data/Actors.rvdata2", "rb") as f:
        actors = load(f)
        json_data = [None] + [actor.tojson() if actor else None for actor in actors[1:]]
        
    with open("OUT/Data/Actors.json", "w", encoding="utf-8") as out:
        json.dump(json_data, out, ensure_ascii=False, indent=2)

    with open("OUT/Data/Classes.rvdata2", "rb") as f:
        classes = load(f)
        json_data = [None] + [cls.tojson() if cls else None for cls in classes[1:]]
        
        with open("OUT/Data/Classes.json", "w", encoding="utf-8") as out:
            json.dump(json_data, out, ensure_ascii=False, indent=2)
    

    with open("OUT/Data/Skills.rvdata2", "rb") as f:
        skills = load(f)
    
        json_data = [None] + [
            skill.tojson() if skill else None
            for skill in skills[1:]  # Skip first element
        ]
        
        with open("OUT/Data/Skills.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)


    return

    # Dead parser code
    parser = argparse.ArgumentParser(description="Convert and extract tilesets from RPG Maker VX/Ace to RPG Maker MZ")
    parser.add_argument("rvdata", help="Tilesets.rvdata2 from RPG Maker VX/Ace")
    parser.add_argument("-t", "--tileset", type=int, help="Tileset index you want to get")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("-o", "--output", type=str, help="File where the JSON will be printed")
    output_group.add_argument("-a", "--append", type=str, help="Append the tileset to a tilesets.json file")


    # Simulate parsed arguments
    @dataclass
    class Commands:
        rvdata: str = 'OUT/Data/Tilesets.rvdata2'
        tileset: int = None
        output: str = 'MV/tilesets.json'
        append: str = None
    
    commands = Commands()  # parser.parse_args()

    jsonObj = []

    content = ""
    with open(commands.rvdata, "rb") as fd:
        content = load(fd)

    if commands.tileset != None:
        if commands.tileset > len(content) or commands.tileset <= 0:
            print("Error : Tileset index out of range")
            return

        jsonObj.append(None)
        jsonObj.append(content[commands.tileset].tojson())

    else:
        for i in content:
            if i is not None:
                jsonObj.append(i.tojson())
            else:
                jsonObj.append(i)


    if commands.output:
        with open(commands.output, "w") as fd:
            json.dump(jsonObj, fd)
    
    if commands.append:
        jsonIn = {}

        with open(commands.append, "r") as fd:
            jsonIn = json.load(fd)

        maxId = maxId = max(node["id"] for node in jsonIn[1:])
        maxId += 1

        for tileset in jsonObj[1:]:
            tileset["id"] = maxId
            maxId += 1

        for tileset in jsonObj[1:]:
            jsonIn.append(tileset)

        with open(commands.append, "w") as fd:
            json.dump(jsonIn, fd)

    if commands.output is None and commands.append is None:
        print(json.dumps(jsonObj))

    return

if __name__ == "__main__":
    main()