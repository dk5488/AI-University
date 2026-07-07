"""Fix curriculum_polity.json:
1. Remove prerequisite references to non-existent node IDs
2. Remove hollow chapter nodes (chapters with no children)
"""
import json

INPUT = 'data/curriculum_polity.json'
OUTPUT = 'data/curriculum_polity.json'

with open(INPUT) as f:
    d = json.load(f)

node_map = {n['id']: n for n in d}
child_map = {n['id']: [] for n in d}
for n in d:
    pid = n.get('parent_id')
    if pid and pid in child_map:
        child_map[pid].append(n['id'])

# Step 1: Find hollow chapters (chapters with no children)
hollow_chapters = {n['id'] for n in d if n['level'] == 'chapter' and len(child_map[n['id']]) == 0}
print(f"Hollow chapters to remove: {len(hollow_chapters)}")
for hid in hollow_chapters:
    node = node_map[hid]
    print(f"  Removing: [{node['level']}] {node['title']}")

# Step 2: Remove hollow chapters from the node list
d_clean = [n for n in d if n['id'] not in hollow_chapters]

# Step 3: Remove references to hollow chapters from other nodes
removed_ids = hollow_chapters
for n in d_clean:
    n['prerequisites'] = [p for p in n.get('prerequisites', []) if p not in removed_ids]
    n['dependencies'] = [dep for dep in n.get('dependencies', []) if dep not in removed_ids]
    n['child_nodes'] = [c for c in n.get('child_nodes', []) if c not in removed_ids]
    n['child_ids'] = [c for c in n.get('child_ids', []) if c not in removed_ids]

# Step 4: Fix missing prerequisite references (remove stale IDs)
node_map_clean = {n['id']: n for n in d_clean}
fixed_prereqs = 0
for n in d_clean:
    before = len(n.get('prerequisites', []))
    n['prerequisites'] = [p for p in n.get('prerequisites', []) if p in node_map_clean]
    after = len(n.get('prerequisites', []))
    fixed_prereqs += before - after

print(f"Fixed stale prerequisite references: {fixed_prereqs}")
print(f"Final node count: {len(d_clean)}")

with open(OUTPUT, 'w') as f:
    json.dump(d_clean, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")

# Verify
with open(OUTPUT) as f:
    verify = json.load(f)

vmap = {n['id']: n for n in verify}
missing_parents = [n for n in verify if n.get('parent_id') and n['parent_id'] not in vmap]
missing_prereqs = [(n['id'], p) for n in verify for p in n.get('prerequisites', []) if p not in vmap]
child_map2 = {n['id']: [] for n in verify}
for n in verify:
    pid = n.get('parent_id')
    if pid and pid in child_map2:
        child_map2[pid].append(n)
hollow = [n for n in verify if len(child_map2[n['id']]) == 0 and n['level'] in ('module', 'unit', 'chapter', 'phase')]

print()
print("=== VERIFICATION ===")
print(f"Total nodes:       {len(verify)}")
print(f"Missing parents:   {len(missing_parents)}")
print(f"Missing prereqs:   {len(missing_prereqs)}")
print(f"Hollow parents:    {len(hollow)}")
if not missing_parents and not missing_prereqs and not hollow:
    print("All clear! Curriculum is structurally complete.")
