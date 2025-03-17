from rubymarshal.reader import load
from rubymarshal.classes import RubyObject, RubyString, UserDef, registry, Symbol
from struct import *
import json
import ctypes
import os
import re

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


def get_damage(dmg):
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


def get_actions(actions):
    return [{
        "conditionParam1": act.attributes.get("@condition_param1", 0),
        "conditionParam2": act.attributes.get("@condition_param2", 0),
        "conditionType": act.attributes.get("@condition_type", 0),
        "rating": act.attributes.get("@rating", 5),
        "skillId": act.attributes.get("@skill_id", 1)
    } for act in actions]

def get_drop_items(drop_items):
    return [{
        "dataId": di.attributes.get("@data_id", 1),
        "denominator": di.attributes.get("@denominator", 1),
        "kind": di.attributes.get("@kind", 0)
    } for di in drop_items]

def get_troop_members(members):
    return [{
        "enemyId": m.attributes.get("@enemy_id", 0),
        "x": m.attributes.get("@x", 0),
        "y": m.attributes.get("@y", 0),
        "hidden": m.attributes.get("@hidden", False)
    } for m in members]

def get_troop_pages(pages):
    converted_pages = []
    for idx, page in enumerate(pages, 1):
        # print(f"  Processing page {idx}")

        cond = page.attributes.get("@condition", None)
        conditions = {
            "actorHp": cond.attributes.get("@actor_hp", 50) if cond else 50,
            "actorId": cond.attributes.get("@actor_id", 1) if cond else 1,
            "actorValid": cond.attributes.get("@actor_valid", False) if cond else False,
            "enemyHp": cond.attributes.get("@enemy_hp", 50) if cond else 50,
            "enemyIndex": cond.attributes.get("@enemy_index", 0) if cond else 0,
            "enemyValid": cond.attributes.get("@enemy_valid", False) if cond else False,
            "switchId": cond.attributes.get("@switch_id", 1) if cond else 1,
            "switchValid": cond.attributes.get("@switch_valid", False) if cond else False,
            "turnA": cond.attributes.get("@turn_a", 0) if cond else 0,
            "turnB": cond.attributes.get("@turn_b", 0) if cond else 0,
            "turnEnding": cond.attributes.get("@turn_ending", False) if cond else False,
            "turnValid": cond.attributes.get("@turn_valid", False) if cond else False
        } if cond else {}

        converted_pages.append({
            "conditions": conditions,
            "list": get_command_list(page.attributes.get("@list", [])),
            "span": page.attributes.get("@span", 0)
        })
    return converted_pages

_convert_map = {
    "$game_actors[": "$gameActors._data[",
    ".change_equip_by_id(": ".changeEquipById(",
    "$game_variables[": "$gameVariables._data[",
    "$game_switches[": "$gameSwitches._data[",
    "$game_self_switches[": "$gameSelfSwitches._data[",
    "$game_player.": "$gamePlayer.",
    "$game_temp.": "$gameTemp.",
    "Input.press?(:CTRL)": "Input.isPressed('control')",
    "else": "} else {",
    "end": "}",
    "= nil": "= null",
    "fps_mode_change(2)": "Graphics.showFps()",
    "fps_mode_change(1)": "Graphics.hideFps()",
    "Window_Base.new(": "new Window_Base(",
    ".draw_text(": ".drawText(",
    "SceneManager.scene.log_window.add_text(": "SceneManager._scene._logWindow.addText(",
    # Disabled
    "wait(": "// wait(",
    "adv_pcture_number(": "// adv_pcture_number(",
}

_convert_pat = {
    r'^if\s+(.*)$': r'if (\1) {'
}

def convert_to_js(params): # Convert some commands to the MV / JS equivalent.
    out = []
    for p in params:
        if not isinstance(p, str):
            p = str(p)
        
        # Apply simple replacements from _convert_map
        for src, dst in _convert_map.items():
            p = p.replace(src, dst)
        
        # Apply regex patterns from _convert_pat at the end
        for pattern, replacement in _convert_pat.items():
            p = re.sub(pattern, replacement, p)
        
        out.append(p)

    return out
    

def get_command_list(commands):
    if not commands:
        return [{"code":0,"indent":0,"parameters":[]}] # TODO !!!
    converted = []
    for idx, cmd in enumerate(commands):
        # Handle special command cases
        code = cmd.attributes.get("@code", 0)
        params = cmd.attributes.get("@parameters", []).copy()

        # Command-specific processing
        if code == 102:  # Show Choices
            params[0] = [convert_str(p) for p in params[0]]
            params[1] -= 1
            if params[1] == 4:
                params[1] = -2    # Adjust cancel branch
            
            while len(params) < 5: # Ensure length
                params.append(0)

            params[2] = 0  # Default choice
            params[3] = 2  # Window position
            params[4] = 0  # Window background
        elif code == 104:  # Key Item Processing
            params[1] = 2  # Key item type
        elif code in (108, 408):  # Comment
            print(params[0])
        elif code == 111:  # Conditional Branch
            if params[0] == 11:  # Key Pressed
                key_mapping = {
                    14: ("A", 12, "Input.isTriggered('A')"),
                    15: ("S", 12, "Input.isTriggered('S')"),
                    16: ("D", 12, "Input.isTriggered('D')")
                }
                if params[1] in key_mapping:
                    new_key = key_mapping[params[1]]
                    params = [new_key[1], new_key[2]]
                else:
                    key_names = ['', '', 'down', '', 'left', '', 'right', '', 'up',
                                '', '', 'shift', 'cancel', 'ok', '', '', '', 
                                'pageup', 'pagedown']
                    params[1] = key_names[params[1]]
            elif params[0] == 12:  # Script
                print('Conditional Branch script call', params[1])
        elif code == 122:  # Control Variables
            if params[3] == 4:  # Script
                print('Control Variables script call', params[4])
        elif code == 231:  # Show Picture (with subtract blend mode)
            if params[9] == 2:
                code = 355
                params = [
                    f'$gameScreen.showPicture({params[0]}, "{params[1]}", {params[2]}, '
                    f'{_var_or_value(params[3], params[4])}, '
                    f'{_var_or_value(params[3], params[5])}, '
                    f'{params[6]}, {params[7]}, {params[8]}, {params[9]})'
                ]
        elif code == 223:
            if len(params) == 3:
                params[0] = [0, 0, 0, 0]
        elif code == 224:
            if len(params) == 3:
                params[0] = [255, 255, 255, 255]
        elif code == 232:  # Move Picture
            params[1] = 0  # Unused parameter
            if params[9] == 2:
                code = 355
                wait_str = f'; this.wait({params[10]})' if params[11] else ''
                params = [
                    f'$gameScreen.movePicture({params[0]}, {params[2]}, '
                    f'{_var_or_value(params[3], params[4])}, '
                    f'{_var_or_value(params[3], params[5])}, '
                    f'{params[6]}, {params[7]}, {params[8]}, {params[9]}, '
                    f'{params[10]}){wait_str}'
                ]
        # elif code == 250:
        # elif code == 241:
        elif code == 224:
            if len(params) == 0: # Skip invalid / empty ?
                continue
        elif code == 285:  # Get Location Info
            if params[1] == 5:
                params[1] = 6  # Adjust region ID
        elif code == 319:  # Change Equipment
            params[1] += 1
        elif code == 302:  # Shop Processing
            while len(params) < 4: # Ensure length
                params.append(0)
            
            params[3] = params[3] or 0
        elif code == 322:  # Change Actor Graphic
            while len(params) < 6:
                params.append(0)
            params[4] = 0  # Clear SV graphic
            params[5] = ''
        elif code in (355, 655):  # Script call
            params = convert_to_js(convert_parameters(params))
            # print('Script call', params[0])
        elif code == 505:  # Move Route
            mvrcmd = params[0]
            if mvrcmd.attributes.get("@code", 0) == 45:  # Script in move route
                print('Move Route Script call', mvrcmd.attributes.get("@parameters", []))

        # Convert command to dict
        converted.append({
            "code": code,
            "indent": cmd.attributes.get("@indent", 0),
            "parameters": convert_parameters(params)
        })
    
    return converted

def _var_or_value(is_variable, value):
    return (f'$gameVariables.value({value})' 
            if is_variable == 1 else str(value))

def get_move_route(move_route):
    if not move_route:
        return {"list":[{"code":0,"parameters":[]}],"repeat":True,"skippable":False,"wait":False}
    return {
        "list": [process_move_command(cmd) for cmd in move_route.attributes.get("@list", [])],
        "repeat": move_route.attributes.get("@repeat", False),
        "skippable": move_route.attributes.get("@skippable", False),
        "wait": move_route.attributes.get("@wait", True)
    }

def process_move_command(cmd):
    code = cmd.attributes.get("@code", 0)
    params = cmd.attributes.get("@parameters", []).copy()
    
    if code == 43 and params[0] == 2:  # Blend mode change
        code = 45
        params = ["this.setBlendMode(2);"]
    
    return {
        "code": code,
        "indent": None,
        "parameters": convert_parameters(params)
    }

def convert_parameters(params):
    converted = []
    for param in params:
        if isinstance(param, RubyObject):
            if param.ruby_class_name == "RPG::MoveRoute":
                converted.append(get_move_route(param))
            elif param.ruby_class_name == "RPG::MoveCommand":
                converted.append(process_move_command(param))
            elif param.ruby_class_name in ("RPG::AudioFile", "RPG::SE", "RPG::BGM", "RPG::BGS", "RPG::ME"):
                converted.append(get_audio(param))
            # elif isinstance(param, (Tone, Color)):
            #     converted.append(convert_color_tone(param))
            elif isinstance(param, RubyString):
                converted.append(convert_str(str(param)))
        elif isinstance(param, str):
            converted.append(convert_str(param))
        elif isinstance(param, bytes):
            converted.append(param.decode("utf-8"))
        elif isinstance(param, Symbol):
            converted.append(convert_str(str(param.name)))
        else:
            converted.append(param)
    return converted

def get_anim_frames(anim):
    out = []
    frame_max = anim.attributes.get("@frame_max", 0)
    frame_list = anim.attributes.get("@frames", [])
    for f in range(frame_max):
        if f < len(frame_list):
            frame = frame_list[f]
            cell_data = frame.attributes.get('@cell_data', [])
            cell_max = frame.attributes.get('@cell_max', 0)
            out.append([
                [
                    int(ctypes.c_int16(cell_data.flags[i]).value) 
                    for i in range(offset, len(cell_data.flags), cell_max)
                ] for offset in range(cell_max)
            ])
        else:
            out.append([])
    return out

def get_color(color):
    if not color:
        return [255,255,255,255]
    return [color.red, color.green, color.blue, color.alpha]

def get_tone(tone):
    if not tone:
        return [255,255,255,255]
    return [tone.red, tone.green, tone.blue, tone.gray]

def get_audio(audio):
    if not audio:
        return {"name":"Fire1","pan":0,"pitch":100,"volume":100}
    return {
        "name": convert_str(audio.attributes.get("@name", "")),
        "pan": 0,  # MV/MZ always uses 0 pan for compatibility
        "pitch": audio.attributes.get("@pitch", 100),
        "volume": audio.attributes.get("@volume", 100)
    }

def get_anim_timings(anim):
    timings = []
    for timing in getattr(anim, "timings", []):
        se = timing.attributes.get("@se", None)
        timings.append({
            "frame": timing.attributes.get("@frame", 0),
            "flashScope": timing.attributes.get("@flash_scope", 0),
            "flashColor": get_color(timing.attributes.get("@flash_color", None)),
            "flashDuration": timing.attributes.get("@flash_duration", 0),
            "se": get_audio(se) if se and se.name != "" else None
        })
    return timings

def get_attack_motions():
    return [
        {"type":0,"weaponImageId":0},{"type":1,"weaponImageId":1},
        {"type":1,"weaponImageId":2},{"type":1,"weaponImageId":3},
        {"type":1,"weaponImageId":4},{"type":1,"weaponImageId":5},
        {"type":1,"weaponImageId":6},{"type":2,"weaponImageId":7},
        {"type":2,"weaponImageId":8},{"type":2,"weaponImageId":9},
        {"type":0,"weaponImageId":10},{"type":0,"weaponImageId":11},
        {"type":0,"weaponImageId":12}
    ]

def get_vehicle(vehicle):
    if not vehicle: return {}
    return {
        "bgm": get_audio(vehicle.attributes.get("@bgm", None)),
        "characterIndex": vehicle.attributes.get("@character_index", 0),
        "characterName": vehicle.attributes.get("@character_name", ""),
        "startMapId": vehicle.attributes.get("@start_map_id", 0),
        "startX": vehicle.attributes.get("@start_x", 0),
        "startY": vehicle.attributes.get("@start_y", 0)
    }

def get_system_sounds(system):
    return [get_audio(sound) for sound in system.attributes.get("@sounds", [])]

def get_system_messages():
    return {
        "actionFailure":    "There was no effect on %1!",
        "actorDamage":      "%1 took %2 damage!",
        "actorDrain": 		"%1 was drained of %2 %3!",
        "actorGain": 		"%1 gained %2 %3!",
        "actorLoss": 		"%1 lost %2 %3!",
        "actorNoDamage": 	"%1 took no damage!",
        "actorNoHit": 		"Miss! %1 took no damage!",
        "actorRecovery": 	"%1 recovered %2 %3!",
        "alwaysDash": 		"Always Dash",
        "bgmVolume": 		"BGM Volume",
        "bgsVolume": 		"BGS Volume",
        "buffAdd": 		    "%1's %2 went up!",
        "buffRemove": 		"%1''s %2 returned to normal!",
        "commandRemember": 	"Command Remember",
        "counterAttack": 	"%1 counterattacked!",
        "criticalToActor": 	"A painful blow!!",
        "criticalToEnemy": 	"An excellent hit!!",
        "debuffAdd": 		"%1's %2 went down!",
        "defeat": 		    "%1 was defeated.",
        "emerge": 		    "%1 emerged!",
        "enemyDamage": 		"%1 took %2 damage!",
        "enemyDrain": 		"%1 was drained of %2 %3!",
        "enemyGain": 		"%1 gained %2 %3!",
        "enemyLoss": 		"%1 lost %2 %3!",
        "enemyNoDamage": 	"%1 took no damage!",
        "enemyNoHit": 		"Miss! %1 took no damage!",
        "enemyRecovery": 	"%1 recovered %2 %3!",
        "escapeFailure": 	"However, it was unable to escape!",
        "escapeStart": 		"%1 has started to escape!",
        "evasion": 		    "%1 evaded the attack!",
        "expNext": 		    "To Next %1",
        "expTotal": 		"Current %1",
        "file": 		    "File",
        "levelUp": 		    "%1 is now %2 %3!",
        "loadMessage": 		"Load which file?",
        "magicEvasion": 	"%1 nullified the magic!",
        "magicReflection": 	"%1 reflected the magic!",
        "meVolume": 		"ME Volume",
        "obtainExp": 		"%1 %2 received!",
        "obtainGold": 		"%1\\G found!",
        "obtainItem": 		"%1 found!",
        "obtainSkill": 		"%1 learned!",
        "partyName": 		"%1's Party",
        "possession": 		"Possession",
        "preemptive": 		"%1 got the upper hand!",
        "saveMessage": 		"Save to which file?",
        "seVolume": 		"SE Volume",
        "substitute": 		"%1 protected %2!",
        "surprise": 		"%1 was surprised!",
        "useItem": 		    "%1 uses %2!",
        "victory": 		    "%1 was victorious!"
    }

def get_test_battlers(battlers):
    return [{
        "actorId": b.attributes.get("@actor_id", 0),
        "equips": b.attributes.get("@equips", []),
        "level": b.attributes.get("@level", 1)
    } for b in battlers]

def find_ruby_string(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, RubyString):
                print(f"Found RubyString at key '{key}': {value}")
            else:
                find_ruby_string(value)  # Recurse for nested objects
    elif isinstance(data, list):
        for i, value in enumerate(data):
            if isinstance(value, RubyString):
                print(f"Found RubyString at index {i}: {value}")
            else:
                find_ruby_string(value)

def convert_ruby_strings(data):
    if isinstance(data, dict):
        return {k: convert_ruby_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_ruby_strings(v) for v in data]
    elif isinstance(data, RubyString):
        return str(data)  # Convert to regular string
    elif isinstance(data, bytes):
        return str(data.decode('utf-8'))  # Convert to regular string
    else:
        return data

def get_encounter_list(encounters):
    return [{
        "regionSet": enc.region_set,
        "troopId": enc.troop_id,
        "weight": enc.weight
    } for enc in encounters]

def get_map_data(data, events, width: int, height: int):
    layers = []
    
    for z in range(2): # First 2 layers
        layer = data.flags[width*height * z: width*height * (z+1)]
        # for y in range(width): # data.attributes.get("@ysize", 0)):
        #     for x in range(height): # data.attributes.get("@xsize", 0)):
        #         layer.append(data[x, y, z])
        layers.extend(layer)
    
    # Layers 3 and 4 with tile events
    upper1 = []
    upper2 = []
    z = 2
    for y in range(height): # data.ysize):
        for x in range(width): # data.xsize):
            tile_events = [evt for evt in events.values() 
                          if evt and evt.attributes.get("@x") == x and evt.attributes.get("@y") == y 
                          and is_tile_event(evt)]
            if tile_events and len(tile_events) > 0:
                upper1.append(data.flags[
                    width*height*z + (x+y*width)
                ])
                pages = tile_events[0].attributes.get("@pages", None)
                if pages:
                    graphic = pages[0].attributes.get("@graphic",None)
                    if graphic:
                        upper2.append(graphic.attributes.get("@tile_id", 0))
                        continue
                
                upper2.append(0)
            else:
                upper1.append(0)
                upper2.append(data.flags[
                    width*height*z + (x+y*width)
                ]) # data[x+y*width]
    layers.extend(upper1 + upper2)
    
    # Shadow layer
    z = 3
    layers.append(data.flags[width*height * z: width*height * (z+1)])

    # for y in range(width): # data.ysize):
    #     for x in range(height): # data.xsize):
    #         layers.append(0) # data[x, y, z]) # z4
    
    # Region layer
    layers.append([
        i >> 8
        for i in data.flags[width*height * z: width*height * (z+1)]
    ])
    # for y in range(width): # data.ysize):
    #     for x in range(height): # data.xsize):
    #         layers.append(data.flags[x+y*width] >> 8) # z3
    
    return layers

def is_tile_event(event):
    pages = event.attributes.get("@pages", [])
    if len(pages) != 1:
        return False
    page = pages[0]
    graphic = page.attributes.get("@graphic", None)
    cond = page.attributes.get("@condition", None)
    if (
        not cond or
        # len(page.attributes.get("@list", [])) < 1 or
        not graphic or
        graphic.attributes.get("@tile_id", 0) == 0
    ):
        return False
    
    return not any([
        cond.attributes.get("@switch1_valid", False),
        cond.attributes.get("@switch2_valid", False),
        cond.attributes.get("@variable_valid", False),
        cond.attributes.get("@self_switch_valid", False),
        cond.attributes.get("@item_valid", False),
        cond.attributes.get("@actor_valid", False)
    ])

def get_map_events(events):
    if not events:
        return []
    max_id = max(events.keys())
    return [
        get_event(events[x]) if x in events and not is_tile_event(events[x]) 
        else None
        for x in range(max_id + 1)
    ]

def get_event(event):
    return {
        "id": event.attributes.get("@id", 0),
        "name": convert_str(event.attributes.get("@name", "EV")),
        "note": "",
        "pages": [get_page(page) for page in event.attributes.get("@pages", [])],
        "x": event.attributes.get("@x", 0),
        "y": event.attributes.get("@y", 0)
    }

def get_page(page):
    cond = page.attributes.get("@condition", None)
    if not cond:
        conditions = {"actorId":1,"actorValid":False,"itemId":1,"itemValid":False,"selfSwitchCh":"A","selfSwitchValid":False,"switch1Id":1,"switch1Valid":False,"switch2Id":1,"switch2Valid":False,"variableId":1,"variableValid":False,"variableValue":0}
    else:
        conditions = {
            "actorId": cond.attributes.get("@actor_id", 1),
            "actorValid": cond.attributes.get("@actor_valid", False),
            "itemId": cond.attributes.get("@item_id", 1),
            "itemValid": cond.attributes.get("@item_valid", False),
            "selfSwitchCh": convert_str(cond.attributes.get("@self_switch_ch", "A")),
            "selfSwitchValid": cond.attributes.get("@self_switch_valid", False),
            "switch1Id": cond.attributes.get("@switch1_id", 1),
            "switch1Valid": cond.attributes.get("@switch1_valid", False),
            "switch2Id": cond.attributes.get("@switch2_id", 1),
            "switch2Valid": cond.attributes.get("@switch2_valid", False),
            "variableId": cond.attributes.get("@variable_id", 1),
            "variableValid": cond.attributes.get("@variable_valid", False),
            "variableValue": cond.attributes.get("@variable_value", 0)
        }
    
    graphic = page.attributes.get("@graphic", None)
    if not graphic:
        image = {"characterIndex":0,"characterName":"","direction":2,"pattern":0,"tileId":0}
    else:
        image = {
            "characterIndex": graphic.attributes.get("@character_index", 0),
            "characterName": convert_str(graphic.attributes.get("@character_name", "")),
            "direction": graphic.attributes.get("@direction", 2),
            "pattern": graphic.attributes.get("@pattern", 0),
            "tileId": graphic.attributes.get("@tile_id", 0)
        }

    
    return {
        "conditions": conditions,
        "directionFix": page.attributes.get("@direction_fix", False),
        "image": image,
        "moveFrequency": page.attributes.get("@move_frequency", 3),
        "moveRoute": get_move_route(page.attributes.get("@move_route", None)),
        "moveSpeed": page.attributes.get("@move_speed", 3),
        "moveType": page.attributes.get("@move_type", 0),
        "priorityType": page.attributes.get("@priority_type", 0),
        "stepAnime": page.attributes.get("@step_anime", False),
        "through": page.attributes.get("@through", False),
        "trigger": page.attributes.get("@trigger", 0),
        "walkAnime": page.attributes.get("@walk_anime", True),
        "list": get_command_list(page.attributes.get("@list", []))
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
        # Handle flags array (0-8191 elements)
        flags = self.attributes.get("@flags", None)
        flags_list = flags.flags[:8192] if flags and hasattr(flags, "flags") else [0]*8192

        # Convert tileset names with proper encoding
        tileset_names = [
            convert_str(name) if name else ""
            for name in self.attributes.get("@tileset_names", [])
        ]

        return {
            "id": self.attributes.get("@id", 0),
            "flags": flags_list,
            "mode": self.attributes.get("@mode", 1),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "tilesetNames": tileset_names
        }
    
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

class Item(RubyObject):
    ruby_class_name = "RPG::Item"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "animationId": self.attributes.get("@animation_id", 0),
            "consumable": self.attributes.get("@consumable", False),
            "damage": get_damage(self.attributes.get("@damage", None)),
            "description": convert_str(self.attributes.get("@description", "")),
            "effects": get_effects(self.attributes.get("@effects", [])),
            "hitType": self.attributes.get("@hit_type", 0),
            "iconIndex": self.attributes.get("@icon_index", 0),
            "itypeId": self.attributes.get("@itype_id", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "occasion": self.attributes.get("@occasion", 0),
            "price": self.attributes.get("@price", 0),
            "repeats": self.attributes.get("@repeats", 1),
            "scope": self.attributes.get("@scope", 0),
            "speed": self.attributes.get("@speed", 0),
            "successRate": self.attributes.get("@success_rate", 100),
            "tpGain": self.attributes.get("@tp_gain", 0)
        }

class Weapon(RubyObject):
    ruby_class_name = "RPG::Weapon"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "animationId": self.attributes.get("@animation_id", 0),
            "description": convert_str(self.attributes.get("@description", "")),
            "etypeId": 1,  # Hardcoded at 1 for MV compatibility, instead of 0 in Ace
            "traits": get_traits(self.attributes.get("@features", [])),
            "iconIndex": self.attributes.get("@icon_index", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "params": self.attributes.get("@params", [0, 0, 10, 0, 0, 0, 0, 0]),
            "price": self.attributes.get("@price", 500),
            "wtypeId": self.attributes.get("@wtype_id", 0)
        }

class Armor(RubyObject):
    ruby_class_name = "RPG::Armor"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "atypeId": self.attributes.get("@atype_id", 0),
            "description": convert_str(self.attributes.get("@description", "")),
            "etypeId": self.attributes.get("@etype_id", 0),
            "traits": get_traits(self.attributes.get("@features", [])),
            "iconIndex": self.attributes.get("@icon_index", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "params": self.attributes.get("@params", [0,0,0,10,0,0,0,0]),
            "price": self.attributes.get("@price", 300)
        }

class Enemy(RubyObject):
    ruby_class_name = "RPG::Enemy"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "actions": get_actions(self.attributes.get("@actions", [])),
            "battlerHue": self.attributes.get("@battler_hue", 0),
            "battlerName": convert_str(self.attributes.get("@battler_name", "")),
            "dropItems": get_drop_items(self.attributes.get("@drop_items", [])),
            "exp": self.attributes.get("@exp", 0),
            "traits": get_traits(self.attributes.get("@features", [])),
            "gold": self.attributes.get("@gold", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "note": convert_str(self.attributes.get("@note", "")),
            "params": self.attributes.get("@params", [200,0,30,30,30,30,30,30])
        }

class Troop(RubyObject):
    ruby_class_name = "RPG::Troop"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "members": get_troop_members(self.attributes.get("@members", [])),
            "pages": get_troop_pages(self.attributes.get("@pages", []))
        }

class State(RubyObject):
    ruby_class_name = "RPG::State"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "iconIndex": self.attributes.get("@icon_index", 0),
            "priority": self.attributes.get("@priority", 50),
            "restriction": self.attributes.get("@restriction", 0),
            "autoRemovalTiming": self.attributes.get("@auto_removal_timing", 0),
            "minTurns": self.attributes.get("@min_turns", 1),
            "maxTurns": self.attributes.get("@max_turns", 1),
            "removeByDamage": self.attributes.get("@remove_by_damage", 0),
            "removeByWalking": self.attributes.get("@remove_by_walking", 0),
            "removeByRestriction": self.attributes.get("@remove_by_restriction", False),
            "removeAtBattleEnd": self.attributes.get("@remove_at_battle_end", False),
            "chanceByDamage": self.attributes.get("@chance_by_damage", 0),
            "stepsToRemove": self.attributes.get("@steps_to_remove", 0),
            "message1": convert_str(self.attributes.get("@message1", "")),
            "message2": convert_str(self.attributes.get("@message2", "")),
            "message3": convert_str(self.attributes.get("@message3", "")),
            "message4": convert_str(self.attributes.get("@message4", "")),
            "motion": 0,  # MV-specific field
            "overlay": 0, # MV-specific field
            "note": convert_str(self.attributes.get("@note", "")),
            "traits": get_traits(self.attributes.get("@features", []))
        }

class Animation(RubyObject):
    ruby_class_name = "RPG::Animation"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "name": convert_str(self.attributes.get("@name", "")),
            "position": self.attributes.get("@position", 0),
            "animation1Name": convert_str(self.attributes.get("@animation1_name", "")),
            "animation1Hue": self.attributes.get("@animation1_hue", 0),
            "animation2Name": convert_str(self.attributes.get("@animation2_name", "")),
            "animation2Hue": self.attributes.get("@animation2_hue", 0),
            "frames": get_anim_frames(self),
            "timings": get_anim_timings(self)
        }

class CommonEvent(RubyObject):
    ruby_class_name = "RPG::CommonEvent"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "list": get_command_list(self.attributes.get("@list", [])),
            "name": convert_str(self.attributes.get("@name", "")),
            "switchId": self.attributes.get("@switch_id", 0),
            "trigger": self.attributes.get("@trigger", 0)
        }

class System(RubyObject):
    ruby_class_name = "RPG::System"

    def tojson(self):
        equipTypes = [""]
        terms_basic = []
        terms_commands = []
        terms_params = []

        terms = self.attributes.get("@terms", {})
        if terms:
            equipTypes = [""] + terms.attributes.get("@etypes", [])
            terms_basic = terms.attributes.get("@basic", [])
            terms_commands = terms.attributes.get("@commands", [])
            terms_params = terms.attributes.get("@params", [])

        return {
            "airship": get_vehicle(self.attributes.get("@airship", None)),
            "armorTypes": self.attributes.get("@armor_types", []),
            "attackMotions": get_attack_motions(),
            "battleBgm": get_audio(self.attributes.get("@battle_bgm", None)),
            "battleBack1Name": self.attributes.get("@battleback1_name", ""),
            "battleBack2Name": self.attributes.get("@battleback2_name", ""),
            "battlerHue": self.attributes.get("@battler_hue", 0),
            "battlerName": self.attributes.get("@battler_name", ""),
            "boat": get_vehicle(self.attributes.get("@boat", None)),
            "currencyUnit": self.attributes.get("@currency_unit", ""),
            "defeatMe": {"name": "Defeat1", "pan": 0, "pitch": 100, "volume": 90},
            "editMapId": self.attributes.get("@edit_map_id", 0),
            "elements": self.attributes.get("@elements", [""]),
            "equipTypes": equipTypes,
            "gameTitle": convert_str(self.attributes.get("@game_title", "")),
            "gameoverMe": get_audio(self.attributes.get("@gameover_me", None)),
            "locale": "en_US",
            "magicSkills": [1],
            "menuCommands": [True, True, True, True, True, True],
            "optDisplayTp": bool(self.attributes.get("@opt_display_tp", False)),
            "optDrawTitle": bool(self.attributes.get("@opt_draw_title", False)),
            "optExtraExp": bool(self.attributes.get("@opt_extra_exp", False)),
            "optFloorDeath": bool(self.attributes.get("@opt_floor_death", False)),
            "optFollowers": bool(self.attributes.get("@opt_followers", False)),
            "optSideView": False,
            "optSlipDeath": bool(self.attributes.get("@opt_slip_death", False)),
            "optTransparent": bool(self.attributes.get("@opt_transparent", False)),
            "partyMembers": self.attributes.get("@party_members", []),
            "ship": get_vehicle(self.attributes.get("@ship", None)),
            "skillTypes": self.attributes.get("@skill_types", [""]),
            "sounds": get_system_sounds(self),
            "startMapId": self.attributes.get("@start_map_id", 0),
            "startX": self.attributes.get("@start_x", 0),
            "startY": self.attributes.get("@start_y", 0),
            "switches": [""] + self.attributes.get("@switches", [""])[1:],
            "terms": {
                "basic": ["", "Lv", "HP", "MP", "TP"] + terms_basic,
                "commands": ["", "Buy", "Sell"] + terms_commands,
                "params": ["", "Hit", "Evasion"] + terms_params,
                "messages": get_system_messages()
            },
            "testBattlers": get_test_battlers(self.attributes.get("@test_battlers", [])),
            "testTroopId": self.attributes.get("@test_troop_id", 0),
            "title1Name": self.attributes.get("@title1_name", ""),
            "title2Name": self.attributes.get("@title2_name", ""),
            "titleBgm": get_audio(self.attributes.get("@title_bgm", None)),
            "variables": [""] + self.attributes.get("@variables", [""])[1:],
            "versionId": self.attributes.get("@version_id", 0),
            "victoryMe": get_audio(self.attributes.get("@battle_end_me", None)),
            "weaponTypes": self.attributes.get("@weapon_types", [""]),
            "windowTone": [0,0,0,0] # get_tone(self.attributes.get("@window_tone", None))
        }

class MapInfo(RubyObject):
    ruby_class_name = "RPG::MapInfo"

    def tojson(self):
        return {
            "id": self.attributes.get("@id", 0),
            "expanded": self.attributes.get("@expanded", False),
            "name": convert_str(self.attributes.get("@name", "")),
            "order": self.attributes.get("@order", 0),
            "parentId": self.attributes.get("@parent_id", 0),
            "scrollX": self.attributes.get("@scroll_x", 0),
            "scrollY": self.attributes.get("@scroll_y", 0)
        }

class Map(RubyObject):
    ruby_class_name = "RPG::Map"

    def tojson(self):
        width = self.attributes.get("@width", 1)
        height = self.attributes.get("@height", 1)

        return {
            "autoplayBgm": self.attributes.get("@autoplay_bgm", False),
            "autoplayBgs": self.attributes.get("@autoplay_bgs", False),
            "battleback1Name": convert_str(self.attributes.get("@battleback1_name", "")),
            "battleback2Name": convert_str(self.attributes.get("@battleback2_name", "")),
            "bgm": get_audio(self.attributes.get("@bgm", None)),
            "bgs": get_audio(self.attributes.get("@bgs", None)),
            "disableDashing": self.attributes.get("@disable_dashing", False),
            "displayName": convert_str(self.attributes.get("@display_name", "")),
            "encounterList": get_encounter_list(self.attributes.get("@encounter_list", [])),
            "encounterStep": self.attributes.get("@encounter_step", 30),
            "height": height,
            "note": convert_str(self.attributes.get("@note", "")),
            "parallaxLoopX": self.attributes.get("@parallax_loop_x", False),
            "parallaxLoopY": self.attributes.get("@parallax_loop_y", False),
            "parallaxName": convert_str(self.attributes.get("@parallax_name", "")),
            "parallaxShow": self.attributes.get("@parallax_show", True),
            "parallaxSx": self.attributes.get("@parallax_sx", 0),
            "parallaxSy": self.attributes.get("@parallax_sy", 0),
            "scrollType": self.attributes.get("@scroll_type", 0),
            "specifyBattleback": self.attributes.get("@specify_battleback", False),
            "tilesetId": self.attributes.get("@tileset_id", 1),
            "width": width,
            "data": get_map_data(self.attributes.get("@data", None), self.attributes.get("@events", {}), width, height),
            "events": get_map_events(self.attributes.get("@events", []))
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
registry.register(Item)
registry.register(Weapon)
registry.register(Armor)
registry.register(Enemy)
registry.register(Troop)
registry.register(State)
registry.register(Animation)
registry.register(CommonEvent)
registry.register(MapInfo)
registry.register(System)
registry.register(Map)
    
import json
import argparse
import sys
from dataclasses import dataclass


def main():

    for item in [
        "Actors", "Classes", "Skills", "Items", "Weapons", "Armors", "Enemies", "Troops", "States", "Animations", "Tilesets", "CommonEvents"
    ]:
        with open(f"OUT/Data/{item}.rvdata2", "rb") as f:
            classes = load(f)
            json_data = [None] + [cls.tojson() if cls else None for cls in classes[1:]]
            
            with open(f"OUT/Data/{item}.json", "w", encoding="utf-8") as out:
                json.dump(json_data, out, ensure_ascii=False, indent=2)
    
    # MapInfos is special
    with open(f"OUT/Data/MapInfos.rvdata2", "rb") as f:
        classes = load(f)

        json_data = [None]
        
        for id in classes:
            obj = classes[id].tojson()
            obj["id"] = id
            json_data.append(obj)
        
        with open(f"OUT/Data/MapInfos.json", "w", encoding="utf-8") as out:
            json.dump(json_data, out, ensure_ascii=False, indent=2)

    # System is also special
    maps = [
        i.split(".")[0] for i in os.listdir("OUT/Data/")
        if i.startswith("Map") and i.endswith(".rvdata2") and not i.startswith("MapInfos")
    ]

    for item in [
        "System"
    ]:
        with open(f"OUT/Data/{item}.rvdata2", "rb") as f:
            classes = load(f)
            json_data = convert_ruby_strings(classes.tojson())
            
            with open(f"OUT/Data/{item}.json", "w", encoding="utf-8") as out:
                json.dump(json_data, out, ensure_ascii=False, indent=2)

    for map in maps:
        with open(f"OUT/Data/{map}.rvdata2", "rb") as f:
            classes = load(f)
            json_data = convert_ruby_strings(classes.tojson())
            
            with open(f"OUT/Data/{map}.json", "w", encoding="utf-8") as out:
                json.dump(json_data, out, ensure_ascii=False, indent=2)


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