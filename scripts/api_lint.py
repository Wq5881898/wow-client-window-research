from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DUMPS = ROOT / "sources" / "forever_dumps"
RESULT_JSON = ROOT / "results" / "api_lint.json"
RESULT_MD = ROOT / "results" / "api_lint_report.md"
BASE_URL = (
    "https://raw.githubusercontent.com/Ketho/wow-ui-source-forever/forever/"
    "Interface/AddOns/Blizzard_APIDocumentationGenerated/"
)

REQUIRED_DUMPS = [
    "AddOnsDocumentation.lua",
    "AddOnProfilerDocumentation.lua",
    "AddOnProfilerConstantsDocumentation.lua",
    "AssistedCombatDocumentation.lua",
    "BuildDocumentation.lua",
    "ChatInfoDocumentation.lua",
    "ContainerDocumentation.lua",
    "MapDocumentation.lua",
    "MinimapDocumentation.lua",
    "PlayerInteractionManagerConstantsDocumentation.lua",
    "RestrictedActionsDocumentation.lua",
    "RestrictedActionsConstantsDocumentation.lua",
    "SystemTimeDocumentation.lua",
    "TargetScriptDocumentation.lua",
    "UnitDocumentation.lua",
    "WorldLootObjectDocumentation.lua",
]

# The manifest turns the prose probe design into explicit callable names and arities.
# argc is the number of arguments the planned probe will pass, not the API maximum.
PROBE_CALLS = [
    ("G1", "GetBuildInfo", 0, "GetBuildInfo", "client build/version"),
    ("G1", "C_AddOns.GetAddOnSecurity", 1, "C_AddOns.GetAddOnSecurity", "addon name"),
    ("G1", "C_AddOns.GetScriptsDisallowedForBeta", 0, "GetScriptsDisallowedForBeta", "old design omitted namespace"),
    ("G1", "C_RestrictedActions.GetAddOnRestrictionState", 1, "GetAddOnRestrictionState", "old design omitted namespace"),
    ("G1", "C_RestrictedActions.IsAddOnRestrictionActive", 1, "IsAddOnRestrictionActive", "old design omitted namespace"),
    ("G1", "InCombatLockdown", 0, "InCombatLockdown", "global API"),
    ("G2", "GetTime", 0, "GetTime", "global API"),
    ("G2", "GetServerTime", 0, "GetServerTime", "global API"),
    ("G2", "GetSessionTime", 0, "GetSessionTime", "global API"),
    ("G2", "GetTickTime", 0, "GetTickTime", "global API"),
    ("G2", "IsUsingFixedTimeStep", 0, "IsUsingFixedTimeStep", "global API"),
    ("G3", "C_Map.GetBestMapForUnit", 1, "C_Map.GetBestMapForUnit", "player"),
    ("G3", "C_Map.GetPlayerMapPosition", 2, "GetPlayerMapPosition", "old design omitted namespace on second call"),
    ("G4", "UnitHealth", 1, "UnitHealth", "unit token"),
    ("G4", "UnitHealthMax", 1, "UnitHealthMax", "unit token"),
    ("G4", "UnitPower", 1, "UnitPower", "optional power type omitted"),
    ("G4", "UnitPowerMax", 1, "UnitPowerMax", "optional power type omitted"),
    ("G4", "UnitCastingInfo", 1, "UnitCastingInfo", "unit token"),
    ("G4", "UnitChannelInfo", 1, "UnitChannelInfo", "unit token"),
    ("G4", "UnitExists", 1, "UnitExists", "unit token"),
    ("G4", "UnitIsDeadOrGhost", 1, "UnitIsDeadOrGhost", "unit token"),
    ("G4", "UnitDistanceSquared", 1, "UnitDistanceSquared", "unit token"),
    ("G4", "UnitAffectingCombat", 1, "UnitAffectingCombat", "unit token"),
    ("G4", "UnitLevel", 1, "UnitLevel", "unit token"),
    ("G4", "UnitIsEnemy", 2, "UnitIsEnemy", "player and observed unit"),
    ("G4", "C_Secrets.ShouldUnitHealthMaxBeSecret", 1, "C_Secrets.Should*BeSecret", "expanded from non-callable wildcard"),
    ("G4", "C_Secrets.ShouldUnitPowerBeSecret", 1, "C_Secrets.Should*BeSecret", "expanded from non-callable wildcard"),
    ("G4", "C_Secrets.ShouldUnitPowerMaxBeSecret", 1, "C_Secrets.Should*BeSecret", "expanded from non-callable wildcard"),
    ("G4", "C_Secrets.ShouldUnitSpellCastingBeSecret", 1, "C_Secrets.Should*BeSecret", "expanded from non-callable wildcard"),
    ("G5", "TargetNearestEnemy", 0, "TargetNearestEnemy", "optional reverse omitted"),
    ("G5", "AttackTarget", 0, "AttackTarget", "global API"),
    ("G5", "IsTargetLoose", 0, "IsTargetLoose", "global API"),
    ("G6", "C_WorldLootObject.GetWorldLootObjectDistanceSquared", 1, "C_WorldLootObject.GetWorldLootObjectDistanceSquared", "unit token"),
    ("G6", "C_WorldLootObject.IsWorldLootObjectInRange", 1, "IsWorldLootObjectInRange", "old design omitted namespace"),
    ("G6", "C_Container.CalculateTotalNumberOfFreeBagSlots", 0, "C_Container.CalculateTotalNumberOfFreeBagSlots", "no arguments"),
    ("G6", "C_Container.GetContainerItemDurability", 2, "GetContainerItemDurability", "old design omitted namespace"),
    ("G7", "C_AssistedCombat.IsAvailable", 0, "C_AssistedCombat.IsAvailable", "no arguments"),
    ("G7", "C_AssistedCombat.GetRotationSpells", 0, "GetRotationSpells", "old design omitted namespace"),
    ("G7", "C_AssistedCombat.GetNextCastSpell", 0, "GetNextCastSpell", "optional checkForVisibleButton omitted"),
    ("G8", "C_ChatInfo.SendChatMessage", 4, "SendChatMessage", "channel form; old design omitted namespace"),
    ("G9", "C_Minimap.GetViewRadius", 0, "C_Minimap.GetViewRadius", "returns yards in the static documentation"),
    ("G9", "C_Minimap.GetUiMapID", 0, "GetUiMapID", "old design omitted namespace"),
    ("G9", "C_Minimap.GetNumTrackingTypes", 0, "GetNumTrackingTypes", "old design omitted namespace"),
    ("G9", "C_Minimap.GetTrackingInfo", 1, "GetTrackingInfo", "old design omitted namespace"),
    ("G9", "C_Minimap.SetTracking", 2, "SetTracking", "old design omitted namespace"),
    ("G10", "C_AddOnProfiler.IsEnabled", 0, "AddOnProfiler related API", "concrete replacement for vague reference"),
    ("G10", "C_AddOnProfiler.GetAddOnMetric", 2, "AddOnProfiler related API", "addon name and metric enum"),
]

PROBE_EVENTS = [
    ("G1", "ADDON_ACTION_BLOCKED"),
    ("G1", "ADDON_ACTION_FORBIDDEN"),
    ("G1", "ADDON_RESTRICTION_STATE_CHANGED"),
    ("G1", "MACRO_ACTION_BLOCKED"),
    ("G1", "MACRO_ACTION_FORBIDDEN"),
    ("G6", "LOOT_OPENED"),
    ("G6", "LOOT_CLOSED"),
    ("G9", "MINIMAP_UPDATE_TRACKING"),
]

NON_API_ITEMS = [
    ("G2", "OnUpdate", "frame script callback; runtime measurement required"),
    ("G5", "SendInput", "Windows input API, not a WoW Lua API"),
    ("G5", "hwevent", "runtime execution-context property, not a callable API"),
    ("G8", "SavedVariables", "persistence mechanism, not a callable API"),
    ("G8", "Logs/WoWChatLog.txt", "client file output, requires runtime measurement"),
    ("G9", "minimap icon coordinates", "no named API is specified in the probe design"),
]

ENUM_CHECKS = [
    (
        "G1",
        "RestrictedActionsConstantsDocumentation.lua",
        "AddOnRestrictionType",
        ["Combat", "Encounter", "ChallengeMode", "PvPMatch", "Map", "Chat"],
    ),
    (
        "G6",
        "PlayerInteractionManagerConstantsDocumentation.lua",
        "PlayerInteractionType",
        ["Herbalism", "Mining", "Skinning", "GameObjectLoot"],
    ),
    (
        "G10",
        "AddOnProfilerConstantsDocumentation.lua",
        "AddOnProfilerMetric",
        ["RecentAverageTime", "PeakTime", "CountTimeOver1Ms"],
    ),
]

MEMBER_RE = re.compile(
    r'\{\s*\n\s*Name = "([A-Za-z0-9_]+)",\s*\n\s*Type = "(Function|Event)",(.*?)\n\t\t\},',
    re.S,
)


def fetch_missing() -> list[str]:
    downloaded = []
    DUMPS.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_DUMPS:
        path = DUMPS / filename
        if path.exists():
            continue
        request = urllib.request.Request(BASE_URL + filename, headers={"User-Agent": "api-lint/1.0"})
        with urllib.request.urlopen(request, timeout=45) as response:
            path.write_bytes(response.read())
        downloaded.append(filename)
    return downloaded


def parse_args(body: str) -> list[dict[str, Any]]:
    match = re.search(r"\n\s*Arguments\s*=\s*\n\s*\{(.*?)(?:\n\s*Returns\s*=|\Z)", body, re.S)
    if not match:
        return []
    args = []
    for line in match.group(1).splitlines():
        item = re.search(r'\{\s*Name = "([^"]+)"(.*?)\},?\s*$', line)
        if not item:
            continue
        attrs = item.group(2)
        args.append(
            {
                "name": item.group(1),
                "nilable": 'Nilable = true' in attrs,
                "has_default": "Default =" in attrs,
                "stride": "StrideIndex =" in attrs,
            }
        )
    return args


def parse_dumps() -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    functions: dict[str, list[dict[str, Any]]] = {}
    events: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(DUMPS.glob("*.lua")):
        text = path.read_text(encoding="utf-8")
        functions_at = text.find("Functions =")
        header = text[:functions_at] if functions_at >= 0 else text[:1000]
        namespace_match = re.search(r'Namespace = "([^"]*)"', header)
        system_namespace = namespace_match.group(1) if namespace_match else ""
        for match in MEMBER_RE.finditer(text):
            name, kind, body = match.groups()
            line = text.count("\n", 0, match.start()) + 1
            if kind == "Event":
                literal = re.search(r'LiteralName = "([^"]+)"', body)
                if literal:
                    events.setdefault(literal.group(1), []).append(
                        {"source": path.name, "line": line, "member": name}
                    )
                continue
            local_namespace = re.search(r'\n\s*Namespace = "([^"]*)"', body)
            namespace = local_namespace.group(1) if local_namespace else system_namespace
            canonical = f"{namespace}.{name}" if namespace else name
            args = parse_args(body)
            required = sum(not arg["nilable"] and not arg["has_default"] and not arg["stride"] for arg in args)
            variadic = any(arg["stride"] for arg in args)
            functions.setdefault(canonical, []).append(
                {
                    "source": path.name,
                    "line": line,
                    "arguments": args,
                    "min_args": required,
                    "max_args": None if variadic else len(args),
                    "secret_arguments": "SecretArguments" in body,
                    "has_restrictions": "HasRestrictions = true" in body,
                    "may_return_nothing": "MayReturnNothing = true" in body,
                }
            )
    return functions, events


def lint_calls(functions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for group, api, argc, written_as, note in PROBE_CALLS:
        matches = functions.get(api, [])
        if not matches:
            rows.append({"group": group, "api": api, "argc": argc, "status": "MISSING", "written_as": written_as, "note": note})
            continue
        signature = matches[0]
        max_args = signature["max_args"]
        valid = argc >= signature["min_args"] and (max_args is None or argc <= max_args)
        status = "OK" if valid else "ARITY_MISMATCH"
        rows.append(
            {
                "group": group,
                "api": api,
                "argc": argc,
                "status": status,
                "written_as": written_as,
                "canonicalized": written_as != api,
                "note": note,
                "signature": signature,
                "duplicate_definitions": len(matches),
            }
        )
    return rows


def lint_events(events: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        {
            "group": group,
            "event": event,
            "status": "OK" if event in events else "MISSING",
            "definitions": events.get(event, []),
        }
        for group, event in PROBE_EVENTS
    ]


def lint_enums() -> list[dict[str, Any]]:
    rows = []
    for group, filename, enum_name, expected in ENUM_CHECKS:
        text = (DUMPS / filename).read_text(encoding="utf-8")
        start = text.find(f'Name = "{enum_name}"')
        if start < 0:
            rows.append(
                {
                    "group": group,
                    "enum": f"Enum.{enum_name}",
                    "status": "MISSING_ENUM",
                    "expected_fields": expected,
                    "missing_fields": expected,
                    "source": filename,
                }
            )
            continue
        next_table = text.find('\n\t\t{\n\t\t\tName = "', start + 1)
        block = text[start : next_table if next_table >= 0 else len(text)]
        fields = re.findall(r'\{ Name = "([^"]+)", Type = "[^"]+", EnumValue = ', block)
        missing = [name for name in expected if name not in fields]
        rows.append(
            {
                "group": group,
                "enum": f"Enum.{enum_name}",
                "status": "OK" if not missing else "MISSING_EXPECTED_FIELDS",
                "expected_fields": expected,
                "missing_fields": missing,
                "documented_field_count": len(fields),
                "source": filename,
            }
        )
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    call_counts = Counter(item["status"] for item in payload["calls"])
    event_counts = Counter(item["status"] for item in payload["events"])
    enum_counts = Counter(item["status"] for item in payload["enums"])
    lines = [
        "# API 静态对账结果",
        "",
        f"生成：{payload['generated_at']}  ",
        f"来源：项目本地归档的第三方 GitHub 镜像生成文档，共 {payload['dump_count']} 份；不是从本机已安装客户端直接提取，静态存在性不代表真机可用。",
        "",
        "## 摘要",
        "",
        f"- 调用：{dict(call_counts)}",
        f"- 事件：{dict(event_counts)}",
        f"- 枚举假设：{dict(enum_counts)}",
        f"- 旧设计中需改为完整命名空间：{sum(row.get('canonicalized', False) for row in payload['calls'])} 项",
        f"- 非 WoW API / 仍需运行时验证：{len(payload['non_api_items'])} 项",
        "",
        "## 调用",
        "",
        "| 组 | 规范名称 | 计划参数数 | 签名 | 状态 | 转储位置 | 备注 |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in payload["calls"]:
        sig = row.get("signature")
        if sig:
            maximum = "*" if sig["max_args"] is None else str(sig["max_args"])
            signature = f"{sig['min_args']}..{maximum}"
            source = f"`{sig['source']}:{sig['line']}`"
        else:
            signature = "-"
            source = "-"
        notes = [row["note"]]
        if row.get("canonicalized"):
            notes.append(f"原文 `{row['written_as']}`，实现须用规范名")
        lines.append(
            f"| {row['group']} | `{row['api']}` | {row['argc']} | {signature} | {row['status']} | {source} | {'；'.join(notes)} |"
        )
    lines.extend(["", "## 事件", "", "| 组 | 事件字面量 | 状态 | 转储位置 |", "|---|---|---|---|"])
    for row in payload["events"]:
        refs = ", ".join(f"`{item['source']}:{item['line']}`" for item in row["definitions"]) or "-"
        lines.append(f"| {row['group']} | `{row['event']}` | {row['status']} | {refs} |")
    lines.extend(["", "## 枚举假设", "", "| 组 | 枚举 | 期望成员 | 缺失成员 | 状态 | 来源 |", "|---|---|---|---|---|---|"])
    for row in payload["enums"]:
        expected = ", ".join(f"`{name}`" for name in row["expected_fields"])
        missing = ", ".join(f"`{name}`" for name in row["missing_fields"]) or "-"
        lines.append(
            f"| {row['group']} | `{row['enum']}` | {expected} | {missing} | {row['status']} | `{row['source']}` |"
        )
    lines.extend(["", "## 非 API 与未闭合项", ""])
    for item in payload["non_api_items"]:
        lines.append(f"- **{item['group']} `{item['item']}`**：{item['reason']}")
    lines.extend(
        [
            "",
            "## 静态结论边界",
            "",
            "- `OK` 只说明名称及计划参数数与项目归档的第三方镜像生成文档一致。",
            "- 镜像分支、目标客户端 build 和运行时文档可能不同；目标 build 和对应文档尚未取得。",
            "- `SecretArguments`、`HasRestrictions` 和返回值限制仍须在目标客户端、目标场景中测试。",
            "- 无拦截事件不等于成功；实际返回/动作与 NIL、SECRET、ERROR、FORBIDDEN 是不同的运行时记录字段。",
            "- SavedVariables、聊天日志、外部输入和小地图图标坐标均不能由本报告证明可用。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint the Forever probe API manifest against archived third-party generated documentation.")
    parser.add_argument("--fetch-missing", action="store_true", help="download only required missing generated documentation")
    args = parser.parse_args()

    downloaded = fetch_missing() if args.fetch_missing else []
    missing_dumps = [name for name in REQUIRED_DUMPS if not (DUMPS / name).exists()]
    if missing_dumps:
        print("Missing required dumps: " + ", ".join(missing_dumps), file=sys.stderr)
        print("Re-run with --fetch-missing.", file=sys.stderr)
        return 2

    functions, events = parse_dumps()
    calls = lint_calls(functions)
    event_rows = lint_events(events)
    enum_rows = lint_enums()
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dump_count": len(list(DUMPS.glob("*.lua"))),
        "source_kind": "archived third-party GitHub mirror of generated API documentation",
        "source_base_url": BASE_URL,
        "downloaded": downloaded,
        "calls": calls,
        "events": event_rows,
        "enums": enum_rows,
        "non_api_items": [
            {"group": group, "item": item, "reason": reason} for group, item, reason in NON_API_ITEMS
        ],
    }
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    RESULT_MD.write_text(render_markdown(payload), encoding="utf-8")

    bad_calls = [row for row in calls if row["status"] != "OK"]
    bad_events = [row for row in event_rows if row["status"] != "OK"]
    bad_enums = [row for row in enum_rows if row["status"] != "OK"]
    print(f"API calls: {len(calls) - len(bad_calls)}/{len(calls)} OK")
    print(f"Events: {len(event_rows) - len(bad_events)}/{len(event_rows)} OK")
    print(f"Enum assumptions: {len(enum_rows) - len(bad_enums)}/{len(enum_rows)} OK")
    print(f"Reports: {RESULT_JSON} | {RESULT_MD}")
    return 1 if bad_calls or bad_events or bad_enums else 0


if __name__ == "__main__":
    raise SystemExit(main())
