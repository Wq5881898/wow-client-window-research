Title: C_Map.GetPlayerMapPosition

URL Source: https://warcraft.wiki.gg/wiki/API:C_Map.GetPlayerMapPosition

Published Time: 2004-11-22T19:15:54Z

Markdown Content:
[](https://warcraft.wiki.gg/wiki/API:C_Map.GetPlayerMapPosition)

From Warcraft Wiki

[Jump to navigation](https://warcraft.wiki.gg/wiki/API:C_Map.GetPlayerMapPosition#mw-head)[Jump to search](https://warcraft.wiki.gg/wiki/API:C_Map.GetPlayerMapPosition#searchInput)

| Game Types |
| --- |
| [![Image 1: 12.1.5 (69594)](https://warcraft.wiki.gg/images/thumb/Midnight-Petopia-Logo.png/36px-Midnight-Petopia-Logo.png?28a8f3)](https://github.com/search?q=repo:Ketho/wow-ui-source-standard-ptr+C_Map.GetPlayerMapPosition&type=code "12.1.5 (69594)")[standard](https://github.com/search?q=repo:Ketho/wow-ui-source-standard-ptr+C_Map.GetPlayerMapPosition&type=code)+[8.0.1](https://warcraft.wiki.gg/wiki/Patch_8.0.1/API_changes "Patch 8.0.1/API changes") [![Image 2: 1.60.1 (69913)](https://warcraft.wiki.gg/images/thumb/WoWForever-Icon.png/22px-WoWForever-Icon.png?3aa161)](https://github.com/search?q=repo:Ketho/wow-ui-source-forever+C_Map.GetPlayerMapPosition&type=code "1.60.1 (69913)")[forever](https://github.com/search?q=repo:Ketho/wow-ui-source-forever+C_Map.GetPlayerMapPosition&type=code)+[1.60.1](https://warcraft.wiki.gg/wiki/Patch_1.60.1/API_changes "Patch 1.60.1/API changes") [![Image 3: 5.5.4 (68077)](https://warcraft.wiki.gg/images/thumb/Mists-Logo-Small.png/36px-Mists-Logo-Small.png?f96b23)](https://github.com/search?q=repo:Ketho/wow-ui-source-mists+C_Map.GetPlayerMapPosition&type=code "5.5.4 (68077)")[mists](https://github.com/search?q=repo:Ketho/wow-ui-source-mists+C_Map.GetPlayerMapPosition&type=code)+[1.13.2](https://warcraft.wiki.gg/wiki/Patch_1.13.2/API_changes "Patch 1.13.2/API changes") [![Image 4: 2.5.6 (68184)](https://warcraft.wiki.gg/images/Bc_icon.gif?6fe702)](https://github.com/search?q=repo:Ketho/wow-ui-source-tbc+C_Map.GetPlayerMapPosition&type=code "2.5.6 (68184)")[tbc](https://github.com/search?q=repo:Ketho/wow-ui-source-tbc+C_Map.GetPlayerMapPosition&type=code)+[1.13.2](https://warcraft.wiki.gg/wiki/Patch_1.13.2/API_changes "Patch 1.13.2/API changes") [![Image 5: World of Warcraft](https://warcraft.wiki.gg/images/WoW_Icon_update.png?d4be1e)](https://github.com/search?q=repo:Ketho/wow-ui-source-vanilla+C_Map.GetPlayerMapPosition&type=code "1.15.9 (69109)")[vanilla](https://github.com/search?q=repo:Ketho/wow-ui-source-vanilla+C_Map.GetPlayerMapPosition&type=code)+[1.13.2](https://warcraft.wiki.gg/wiki/Patch_1.13.2/API_changes "Patch 1.13.2/API changes") |
| Links |
| [![Image 6: GitHub Octocat.png](https://warcraft.wiki.gg/images/thumb/GitHub_Octocat.png/16px-GitHub_Octocat.png?e90c6c)](https://github.com/search?type=code&q=/(?-i)C_Map\.GetPlayerMapPosition/+language:Lua+NOT+is:fork+NOT+(path:Blizzard+OR+path:Interface+OR+path:AddOns+OR+path:Documentation+OR+path:FrameXML+OR+path:GlueXML+OR+path:SharedXML+OR+path:.luacheckrc+OR+path:api.lua+OR+path:luaserver.lua+OR+path:textentry.lua+OR+path:DataStore+OR+path:ElvUI+OR+path:Questie+OR+path:WeakAuras)+NOT+(owner:ChrisKader+OR+owner:CucFlavius+OR+owner:Ellypse+OR+owner:Ketho+OR+owner:ketho-wow+OR+owner:Logonz+OR+owner:mrbuds+OR+owner:nebularg+OR+owner:QartemisT+OR+owner:Resike+OR+owner:wowless+OR+owner:92Garfield+OR+owner:arkanoid1+OR+owner:Bhahlou+OR+owner:BreakBB+OR+owner:clicketz+OR+owner:Falkicon+OR+owner:MrMartin92+OR+owner:nwpark+OR+owner:papa-smurf+OR+owner:refaim+OR+owner:torresdrew+OR+owner:ZenonWow+OR+owner:Zetaprime82+OR+owner:zol-wow))[GitHub search](https://github.com/search?type=code&q=/(?-i)C_Map\.GetPlayerMapPosition/+language:Lua+NOT+is:fork+NOT+(path:Blizzard+OR+path:Interface+OR+path:AddOns+OR+path:Documentation+OR+path:FrameXML+OR+path:GlueXML+OR+path:SharedXML+OR+path:.luacheckrc+OR+path:api.lua+OR+path:luaserver.lua+OR+path:textentry.lua+OR+path:DataStore+OR+path:ElvUI+OR+path:Questie+OR+path:WeakAuras)+NOT+(owner:ChrisKader+OR+owner:CucFlavius+OR+owner:Ellypse+OR+owner:Ketho+OR+owner:ketho-wow+OR+owner:Logonz+OR+owner:mrbuds+OR+owner:nebularg+OR+owner:QartemisT+OR+owner:Resike+OR+owner:wowless+OR+owner:92Garfield+OR+owner:arkanoid1+OR+owner:Bhahlou+OR+owner:BreakBB+OR+owner:clicketz+OR+owner:Falkicon+OR+owner:MrMartin92+OR+owner:nwpark+OR+owner:papa-smurf+OR+owner:refaim+OR+owner:torresdrew+OR+owner:ZenonWow+OR+owner:Zetaprime82+OR+owner:zol-wow)) [![Image 7: Townlong-Yak Globe.png](https://warcraft.wiki.gg/images/thumb/Townlong-Yak_Globe.png/16px-Townlong-Yak_Globe.png?680b35)](https://www.townlong-yak.com/globe/wut/#q:C_Map.GetPlayerMapPosition)[Globe](https://www.townlong-yak.com/globe/wut/#q:C_Map.GetPlayerMapPosition) [![Image 8: Townlong-Yak BAD.png](https://warcraft.wiki.gg/images/thumb/Townlong-Yak_BAD.png/16px-Townlong-Yak_BAD.png?ca02cf)](https://www.townlong-yak.com/framexml/ptr/Blizzard_APIDocumentation#C_Map.GetPlayerMapPosition)[Townlong Yak](https://www.townlong-yak.com/framexml/ptr/Blizzard_APIDocumentation#C_Map.GetPlayerMapPosition) [![Image 9: Blizz.gif](https://warcraft.wiki.gg/images/Blizz.gif?984542)](https://github.com/search?type=code&q=/(?-i)%22GetPlayerMapPosition%22/+repo:Ketho/wow-ui-source-standard-ptr+path:/^Interface\/AddOns\/Blizzard_APIDocumentationGenerated\/MapDocumentation.lua/)[Blizzard Docs](https://github.com/search?type=code&q=/(?-i)%22GetPlayerMapPosition%22/+repo:Ketho/wow-ui-source-standard-ptr+path:/^Interface\/AddOns\/Blizzard_APIDocumentationGenerated\/MapDocumentation.lua/) |
| System: [MapUI](https://warcraft.wiki.gg/wiki/Category:API_systems/MapUI "Category:API systems/MapUI") |
| Predicates |
| [AllowedWhenUntainted](https://warcraft.wiki.gg/wiki/Secret_Values#Secret_arguments "Secret Values") |

| [Main Menu](https://warcraft.wiki.gg/wiki/Warcraft_Wiki:Interface_customization "Warcraft Wiki:Interface customization") |
| --- |
| * [WoW API](https://warcraft.wiki.gg/wiki/World_of_Warcraft_API "World of Warcraft API") * [Lua API](https://warcraft.wiki.gg/wiki/Lua_functions "Lua functions") * [Widget API](https://warcraft.wiki.gg/wiki/Widget_API "Widget API") * [ScriptObject API](https://warcraft.wiki.gg/wiki/ScriptObject_API "ScriptObject API") * [XML schema](https://warcraft.wiki.gg/wiki/XML "XML") * [FrameXML](https://warcraft.wiki.gg/wiki/FrameXML_functions "FrameXML functions") * [Events](https://warcraft.wiki.gg/wiki/Events "Events") * [CVars](https://warcraft.wiki.gg/wiki/Console_variables "Console variables") * * * * [Combat Log](https://warcraft.wiki.gg/wiki/COMBAT_LOG_EVENT "COMBAT LOG EVENT") * [Escape sequences](https://warcraft.wiki.gg/wiki/UI_escape_sequences "UI escape sequences") * [API changes](https://warcraft.wiki.gg/wiki/API_change_summaries "API change summaries") * [HOWTOs](https://warcraft.wiki.gg/wiki/HOWTOs "HOWTOs") * ![Image 10: Warcraft Wiki icon stamp.svg](https://warcraft.wiki.gg/images/Warcraft_Wiki_icon_stamp.svg?c7645a)[Redirect](https://www.wiki.gg/redirect), [Google](https://www.google.com/preferences/source?q=warcraft.wiki.gg) * ![Image 11: Discord logo.png](https://warcraft.wiki.gg/images/thumb/Discord_logo.png/14px-Discord_logo.png?4d7bc2)[WoWUIDev](https://discord.gg/txUg39Vhc6) |

![Image 12: Icon-addon-48x48.png](https://warcraft.wiki.gg/images/Icon-addon-48x48.png?9b3b13)**This function is [restricted](https://warcraft.wiki.gg/wiki/Category:API_functions/restricted "Category:API functions/restricted").**
**`#noinstance`** - This only works outdoors and not in instanced content (dungeons/raids/battlegrounds/arena).

Returns the location of the unit on a map.

position = C_Map.GetPlayerMapPosition(uiMapID, unitToken)

## Arguments

uiMapID number: [UiMapID](https://warcraft.wiki.gg/wiki/UiMapID "UiMapID")unitToken[UnitToken](https://warcraft.wiki.gg/wiki/UnitToken "UnitToken"): string
## Returns

position[vector2](https://warcraft.wiki.gg/wiki/Vector2DMixin "Vector2DMixin")?
## Example

Prints the current map coords for the player.

local map = C_Map.GetBestMapForUnit("player")
local position = C_Map.GetPlayerMapPosition(map, "player")
print(position:GetXY()) -- 0.54766619205475, 0.54863452911377

[![Image 13](https://warcraft.wiki.gg/images/thumb/API_C_Map.GetUserWaypointHyperlink.png/320px-API_C_Map.GetUserWaypointHyperlink.png?3efce1)](https://warcraft.wiki.gg/wiki/File:API_C_Map.GetUserWaypointHyperlink.png)

Sending a map pin for a target

Sends a map pin to General chat for the target (but still uses your own location).

/run local c,p,t,m=C_Map,"player","target"m=c.GetBestMapForUnit(p)c.SetUserWaypoint{uiMapID=m,position=c.GetPlayerMapPosition(m,p)}SendChatMessage(format("%%t (%d%%)%s",UnitHealth(t)/UnitHealthMax(t)*100,c.GetUserWaypointHyperlink()),"CHANNEL",nil,1)

## Patch changes

## See also

*   WoWInterface: [C_Map.GetPlayerMapPosition Memory Usage](https://www.wowinterface.com/forums/showthread.php?t=56290)
