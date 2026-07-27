import json

with open('data/curriculum_polity.json') as f:
    d = json.load(f)

node_map = {n['id']: n for n in d}
child_map = {n['id']: [] for n in d}
for n in d:
    pid = n.get('parent_id')
    if pid and pid in child_map:
        child_map[pid].append(n)

# Level breakdown
levels = {}
for n in d:
    levels[n['level']] = levels.get(n['level'], 0) + 1

# Structural checks
missing_parents = [n for n in d if n.get('parent_id') and n['parent_id'] not in node_map]
missing_prereqs = [(n['id'], p) for n in d for p in n.get('prerequisites', []) if p not in node_map]
missing_child_ids = [(n['id'], c) for n in d for c in n.get('child_ids', []) if c not in node_map]
leaf_nodes = [n for n in d if len(child_map[n['id']]) == 0]
hollow_parents = [n for n in d if len(child_map[n['id']]) == 0 and n['level'] in ('module', 'unit', 'chapter', 'phase')]
root_nodes = [n for n in d if not n.get('parent_id')]

print("=" * 55)
print("CURRICULUM INTEGRITY REPORT")
print("=" * 55)
print(f"Total nodes:        {len(d)}")
print(f"Root nodes:         {len(root_nodes)}")
print(f"Leaf nodes:         {len(leaf_nodes)}")
print()
print("Level breakdown:")
for k, v in sorted(levels.items()):
    print(f"  {k:<15} {v}")
print()
print("Integrity checks:")
print(f"  Missing parents:   {len(missing_parents)}")
print(f"  Missing prereqs:   {len(missing_prereqs)}")
print(f"  Missing child_ids: {len(missing_child_ids)}")
print(f"  Hollow parents:    {len(hollow_parents)}")
print()
if missing_parents:
    print("WARNING - Missing parent nodes:")
    for n in missing_parents[:5]:
        print(f"  {n['id']} -> {n['parent_id']}")
if hollow_parents:
    print("WARNING - Non-leaf nodes with no children:")
    for n in hollow_parents[:5]:
        print(f"  [{n['level']}] {n['title']}")
if not missing_parents and not missing_prereqs and not hollow_parents:
    print("All checks passed! Curriculum is structurally complete.")
print()
print("Top-level structure:")
for root in root_nodes:
    print(f"  [{root['level']}] {root['title']}")
    for phase in sorted(child_map[root['id']], key=lambda x: x['learning_order']):
        mc = len(child_map[phase['id']])
        print(f"    [{phase['level']}] {phase['title']} ({mc} modules)")
        for mod in sorted(child_map[phase['id']], key=lambda x: x['learning_order']):
            lc = len(child_map[mod['id']])
            tc = sum(1 for n in d if n.get('parent_id') and n['id'] in node_map and n['level'] in ('topic','concept') and n.get('parent_id','').startswith(mod['id']))
            print(f"      [{mod['level']}] {mod['title']} ({lc} units)")
