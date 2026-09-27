"""A* solver for Sokoban levels (UI-agnostic)."""

from __future__ import print_function

import heapq
import json
import time

DIRS = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}

MAX_TREE_NODES = 400
MAX_TREE_EDGES = 800


def _parse_level(level_info):
    worker_pos = None
    box_pos = []
    dock_pos = []
    wall_pos = []
    for i, line in enumerate(level_info):
        for j, tile in enumerate(line):
            pos = (j, i)
            if tile in ('@', '+'):
                worker_pos = pos
            if tile in ('$', '*'):
                box_pos.append(pos)
            if tile in ('.', '*', '+'):
                dock_pos.append(pos)
            if tile == '#':
                wall_pos.append(pos)
    return worker_pos, box_pos, dock_pos, wall_pos


def _extract_level(level_data_or_world):
    if hasattr(level_data_or_world, "worker_pos"):
        worker = level_data_or_world.worker_pos[0]
        boxes = list(level_data_or_world.box_pos)
        docks = list(level_data_or_world.dock_pos)
        walls = list(level_data_or_world.wall_pos)
        return worker, boxes, docks, walls
    return _parse_level(level_data_or_world)


def _is_corner(pos, walls_set):
    x, y = pos
    left = (x - 1, y) in walls_set
    right = (x + 1, y) in walls_set
    up = (x, y - 1) in walls_set
    down = (x, y + 1) in walls_set
    return (left and up) or (left and down) or (right and up) or (right and down)


def _heuristic(boxes, targets, walls_set, target_set):
    # Heuristic: sum of Manhattan distances to the closest target for each box.
    total = 0
    for box in boxes:
        if box not in target_set and _is_corner(box, walls_set):
            return float("inf")
        min_dist = min(
            abs(box[0] - target[0]) + abs(box[1] - target[1])
            for target in targets
        )
        total += min_dist
    return total


def solve_astar(
    level_data_or_world,
    tree_limits=(MAX_TREE_NODES, MAX_TREE_EDGES),
    trace_limit=0,
):
    """Solve a Sokoban level using A*.

    Returns dict with:
      moves: list of "U/D/L/R"
      moves_str: concatenated string
      cost: g(goal) or -1 if no solution
      expanded: number of expanded states
      generated: number of generated states (pushed to frontier)
      max_frontier: maximum frontier size
      expanded_by_depth: dict of expansions per g depth
      tree: dict with nodes/edges for visualization
      trace: dict with trace lines
      time_sec: total wall time in seconds
    """
    start_time = time.time()
    trace_data = {"lines": [], "limit": trace_limit, "truncated": False}
    trace_state_id = {}
    trace_next_id = 0
    trace_entries = 0

    def trace_sid(state):
        nonlocal trace_next_id
        state_id = trace_state_id.get(state)
        if state_id is None:
            state_id = trace_next_id
            trace_next_id += 1
            trace_state_id[state] = state_id
        return state_id

    def trace_state_label(state):
        player, boxes_tuple = state
        boxes_str = ",".join(
            "({0},{1})".format(pos[0], pos[1]) for pos in boxes_tuple
        )
        return "P({0},{1}) B{{{2}}}".format(player[0], player[1], boxes_str)
    worker, boxes, docks, walls = _extract_level(level_data_or_world)
    if tree_limits is None:
        max_tree_nodes = None
        max_tree_edges = None
    else:
        max_tree_nodes, max_tree_edges = tree_limits

    tree_nodes = {}
    tree_edges = []
    node_id_by_state = {}
    tree_truncated = False
    next_node_id = 0
    root_id = None
    came_from = {}

    def record_expansion(state, g_val, h_val, force=False):
        nonlocal next_node_id, tree_truncated, root_id
        if max_tree_nodes is not None and len(tree_nodes) >= max_tree_nodes and not force:
            tree_truncated = True
            return None

        node_id = node_id_by_state.get(state)
        if node_id is None:
            node_id = next_node_id
            next_node_id += 1
            node_id_by_state[state] = node_id
            player, boxes_tuple = state
            node_data = {
                "g": g_val,
                "h": h_val,
                "f": g_val + h_val,
                "goal": False,
                "state_label": trace_state_label(state),
                "player": [player[0], player[1]],
                "boxes": [[pos[0], pos[1]] for pos in boxes_tuple],
            }
            if state in came_from:
                _, move, pushed = came_from[state]
                node_data["move"] = move
                node_data["pushed"] = bool(pushed)
            tree_nodes[node_id] = node_data
            if state == start_state:
                root_id = node_id
            parent_state = None
            if state in came_from:
                parent_state = came_from[state][0]
            if parent_state is not None:
                parent_id = node_id_by_state.get(parent_state)
                if (
                    parent_id is not None
                    and (max_tree_edges is None or len(tree_edges) < max_tree_edges)
                ):
                    tree_edges.append((parent_id, node_id))
            return node_id

        node = tree_nodes[node_id]
        if g_val < node["g"]:
            node["g"] = g_val
            node["h"] = h_val
            node["f"] = g_val + h_val
            if state in came_from:
                _, move, pushed = came_from[state]
                node["move"] = move
                node["pushed"] = bool(pushed)
        return node_id

    if worker is None:
        return {
            "moves": [],
            "moves_str": "",
            "cost": -1,
            "expanded": 0,
            "generated": 0,
            "max_frontier": 0,
            "expanded_by_depth": {},
            "tree": None,
            "trace": trace_data,
            "time_sec": 0.0,
        }

    walls_set = set(walls)
    target_set = set(docks)
    targets = list(docks)

    start_boxes = tuple(sorted(boxes))
    start_state = (worker, start_boxes)

    expanded = 0
    generated = 0
    max_frontier = 1
    expanded_by_depth = {}
    h_cache = {}

    def heuristic_for_boxes(boxes_tuple):
        if boxes_tuple in h_cache:
            return h_cache[boxes_tuple]
        h_val = _heuristic(boxes_tuple, targets, walls_set, target_set)
        h_cache[boxes_tuple] = h_val
        return h_val

    start_h = heuristic_for_boxes(start_boxes)

    if all(box in target_set for box in start_boxes):
        record_expansion(start_state, 0, start_h)
        if root_id is not None:
            tree_nodes[root_id]["goal"] = True
        return {
            "moves": [],
            "moves_str": "",
            "cost": 0,
            "expanded": 0,
            "generated": 0,
            "max_frontier": 0,
            "expanded_by_depth": {},
            "tree": {
                "nodes": tree_nodes,
                "edges": tree_edges,
                "root": root_id,
                "truncated": tree_truncated,
                "max_nodes": max_tree_nodes,
                "max_edges": max_tree_edges,
            },
            "trace": trace_data,
            "time_sec": time.time() - start_time,
        }

    if start_h == float("inf"):
        record_expansion(start_state, 0, start_h)
        return {
            "moves": [],
            "moves_str": "",
            "cost": -1,
            "expanded": 0,
            "generated": 0,
            "max_frontier": 0,
            "expanded_by_depth": {},
            "tree": {
                "nodes": tree_nodes,
                "edges": tree_edges,
                "root": root_id,
                "truncated": tree_truncated,
                "max_nodes": max_tree_nodes,
                "max_edges": max_tree_edges,
            },
            "trace": trace_data,
            "time_sec": time.time() - start_time,
        }

    # A*: f = g + h where g is cost so far, h is heuristic estimate.
    open_heap = []
    counter = 0
    heapq.heappush(open_heap, (start_h, 0, counter, start_state))

    best_g = {start_state: 0}

    while open_heap:
        _, g_val, _, state = heapq.heappop(open_heap)
        if g_val != best_g.get(state):
            continue

        expanded += 1
        expanded_by_depth[g_val] = expanded_by_depth.get(g_val, 0) + 1
        worker_pos, boxes_tuple = state
        h_val = heuristic_for_boxes(boxes_tuple)
        record_expansion(state, g_val, h_val)
        trace_this = trace_limit is None or trace_entries < trace_limit
        if trace_limit == 0:
            trace_this = False
        if trace_limit is not None and trace_entries >= trace_limit:
            trace_data["truncated"] = True
            trace_this = False
        if trace_this:
            node_id = trace_sid(state)
            trace_data["lines"].append(
                "S{0}: {1}     g={2}  h={3}  f={4}".format(
                    node_id, trace_state_label(state), g_val, h_val, g_val + h_val
                )
            )

        if all(box in target_set for box in boxes_tuple):
            moves = []
            cur_state = state
            while cur_state in came_from:
                parent_info = came_from[cur_state]
                cur_state = parent_info[0]
                moves.append(parent_info[1])
            moves.reverse()
            goal_id = node_id_by_state.get(state)
            if goal_id is None:
                record_expansion(state, g_val, h_val, force=True)
                goal_id = node_id_by_state.get(state)
            if goal_id is not None:
                tree_nodes[goal_id]["goal"] = True
            return {
                "moves": moves,
                "moves_str": "".join(moves),
                "cost": g_val,
                "expanded": expanded,
                "generated": generated,
                "max_frontier": max_frontier,
                "expanded_by_depth": expanded_by_depth,
                "tree": {
                    "nodes": tree_nodes,
                    "edges": tree_edges,
                    "root": root_id,
                    "truncated": tree_truncated,
                    "max_nodes": max_tree_nodes,
                    "max_edges": max_tree_edges,
                },
                "trace": trace_data,
                "time_sec": time.time() - start_time,
            }

        boxes_set = set(boxes_tuple)
        parent_state = None
        if state in came_from:
            parent_state = came_from[state][0]
        for move, (dx, dy) in DIRS.items():
            next_pos = (worker_pos[0] + dx, worker_pos[1] + dy)
            if next_pos in walls_set:
                continue

            if next_pos in boxes_set:
                push_pos = (next_pos[0] + dx, next_pos[1] + dy)
                if push_pos in walls_set or push_pos in boxes_set:
                    continue
                if push_pos not in target_set and _is_corner(push_pos, walls_set):
                    if trace_this:
                        trace_data["lines"].extend(
                            [
                                "   |",
                                "   | {0} (cout 1) [pousse | deadlock]".format(move),
                                "   v",
                                "X: etat impossible (deadlock)",
                            ]
                        )
                    continue

                new_boxes_set = set(boxes_set)
                new_boxes_set.remove(next_pos)
                new_boxes_set.add(push_pos)
                new_boxes_tuple = tuple(sorted(new_boxes_set))
                new_state = (next_pos, new_boxes_tuple)
                pushed = True
            else:
                new_state = (next_pos, boxes_tuple)
                pushed = False

            new_g = g_val + 1
            prev_g = best_g.get(new_state, float("inf"))
            accepted = new_g < prev_g
            h_next = None
            if trace_this or accepted:
                h_next = heuristic_for_boxes(new_state[1])
                if h_next == float("inf"):
                    if trace_this:
                        note_parts = []
                        if pushed:
                            note_parts.append("pousse")
                        note_parts.append("deadlock")
                        note = " [" + " | ".join(note_parts) + "]"
                        trace_data["lines"].extend(
                            [
                                "   |",
                                "   | {0} (cout 1){1}".format(move, note),
                                "   v",
                                "X: etat impossible (deadlock)",
                            ]
                        )
                    continue

            if trace_this:
                note_parts = []
                if pushed:
                    note_parts.append("pousse")
                if parent_state is not None and new_state == parent_state:
                    note_parts.append("retour")
                if not accepted:
                    note_parts.append("deja vu -> ignore par CLOSED")
                note = ""
                if note_parts:
                    note = " [" + " | ".join(note_parts) + "]"

                next_id = trace_sid(new_state)
                disp_g = prev_g if not accepted and prev_g != float("inf") else new_g
                disp_h = h_next if h_next is not None else 0
                disp_f = disp_g + disp_h
                trace_data["lines"].extend(
                    [
                        "   |",
                        "   | {0} (cout 1){1}".format(move, note),
                        "   v",
                        "S{0}: {1}     g={2}  h={3}  f={4}".format(
                            next_id,
                            trace_state_label(new_state),
                            disp_g,
                            disp_h,
                            disp_f,
                        ),
                    ]
                )

            if accepted:
                best_g[new_state] = new_g
                came_from[new_state] = (state, move, pushed)
                generated += 1
                counter += 1
                heapq.heappush(open_heap, (new_g + h_next, new_g, counter, new_state))
                if len(open_heap) > max_frontier:
                    max_frontier = len(open_heap)

        if trace_this:
            trace_data["lines"].append("")
            trace_entries += 1
    return {
        "moves": [],
        "moves_str": "",
        "cost": -1,
        "expanded": expanded,
        "generated": generated,
        "max_frontier": max_frontier,
        "expanded_by_depth": expanded_by_depth,
        "tree": {
            "nodes": tree_nodes,
            "edges": tree_edges,
            "root": root_id,
            "truncated": tree_truncated,
            "max_nodes": max_tree_nodes,
            "max_edges": max_tree_edges,
        },
        "trace": trace_data,
        "time_sec": time.time() - start_time,
    }


def format_search_report(result, max_width=40, max_rows=None):
    """Returns a multi-line text report with an ASCII graph (French)."""
    if not result:
        return "Aucune donnee de solveur."

    cost = result.get("cost", -1)
    expanded = result.get("expanded", 0)
    generated = result.get("generated", 0)
    max_frontier = result.get("max_frontier", 0)
    time_sec = result.get("time_sec", 0.0)
    moves_str = result.get("moves_str", "")

    lines = ["Rapport A*"]
    lines.append(
        "cout={0} explores={1} generes={2} frontiere_max={3} temps={4:.3f}s".format(
            cost, expanded, generated, max_frontier, time_sec
        )
    )
    if moves_str:
        lines.append("mouvements={0}".format(moves_str))
    if cost < 0:
        lines.append("statut=Aucune solution")

    tree = result.get("tree") or {}


    expanded_by_depth = result.get("expanded_by_depth", {})
    if not expanded_by_depth:
        lines.append("expansions_par_profondeur: (aucune donnee)")
        return "\n".join(lines)

    lines.append("expansions_par_profondeur (g):")
    items = sorted(expanded_by_depth.items())
    max_count = max(expanded_by_depth.values()) or 1
    truncated = False
    if max_rows is not None and len(items) > max_rows:
        items = items[:max_rows]
        truncated = True

    for depth, count in items:
        bar_len = int(float(count) / max_count * max_width)
        bar = "#" * max(1, bar_len)
        lines.append("g={0:>3} | {1} ({2})".format(depth, bar, count))

    if truncated:
        lines.append("... {0} more rows".format(len(expanded_by_depth) - max_rows))

    return "\n".join(lines)


def format_summary(result):
    """Returns a short one-line French summary."""
    if not result:
        return "Aucune donnee de solveur."
    return (
        "A*: cout={0} explores={1} generes={2} frontiere_max={3} temps={4:.3f}s"
    ).format(
        result.get("cost", -1),
        result.get("expanded", 0),
        result.get("generated", 0),
        result.get("max_frontier", 0),
        result.get("time_sec", 0.0),
    )


def format_details(result):
    """Returns a multi-line French detail block (no ASCII graph)."""
    if not result:
        return "Aucune donnee de solveur."
    cost = result.get("cost", -1)
    expanded = result.get("expanded", 0)
    generated = result.get("generated", 0)
    max_frontier = result.get("max_frontier", 0)
    time_sec = result.get("time_sec", 0.0)
    moves_str = result.get("moves_str", "")
    expanded_by_depth = result.get("expanded_by_depth", {})

    lines = ["Rapport A* (detaille)"]
    lines.append(
        "cout={0} explores={1} generes={2} file-max={3} temps={4:.3f}s".format(
            cost, expanded, generated, max_frontier, time_sec
        )
    )
    if moves_str:
        lines.append("mouvements={0}".format(moves_str))
    if cost < 0:
        lines.append("statut=Aucune solution")
    tree = result.get("tree") or {}
    
    return "\n".join(lines)


def format_trace_text(result):
    """Returns a multi-line French trace text."""
    trace = (result or {}).get("trace") or {}
    lines = list(trace.get("lines") or [])
    if not lines:
        return "Aucune trace disponible."
    if trace.get("truncated"):
        lines.append("trace_tronquee=oui")
    return "\n".join(lines)


def export_trace_text(result, path):
    """Exports the trace text to a file."""
    text = format_trace_text(result)
    with open(path, "w") as handle:
        handle.write(text)
        handle.write("\n")
    return True


def filter_tree_topk(tree, k):
    """Returns a filtered tree keeping only top-K nodes per depth by f=g+h."""
    if not tree or not tree.get("nodes"):
        return tree

    nodes = tree.get("nodes", {})
    edges = tree.get("edges", [])
    root = tree.get("root")

    nodes_by_depth = {}
    for node_id, data in nodes.items():
        depth = data.get("g", 0)
        nodes_by_depth.setdefault(depth, []).append(node_id)

    keep = set()
    for depth, ids in nodes_by_depth.items():
        ids_sorted = sorted(
            ids,
            key=lambda i: (
                nodes[i].get("f", 0),
                nodes[i].get("h", 0),
                i,
            ),
        )
        keep.update(ids_sorted[:k])

    if root is not None:
        keep.add(root)
    for node_id, data in nodes.items():
        if data.get("goal"):
            keep.add(node_id)

    parent_by_child = {}
    for parent_id, child_id in edges:
        if child_id not in parent_by_child:
            parent_by_child[child_id] = parent_id

    for node_id in list(keep):
        cur = node_id
        while cur in parent_by_child:
            parent_id = parent_by_child[cur]
            if parent_id in keep:
                break
            keep.add(parent_id)
            cur = parent_id

    new_nodes = {node_id: nodes[node_id] for node_id in keep}
    new_edges = [
        (parent_id, child_id)
        for parent_id, child_id in edges
        if parent_id in keep and child_id in keep
    ]

    filtered = dict(tree)
    filtered["nodes"] = new_nodes
    filtered["edges"] = new_edges
    filtered["filtered_k"] = k
    return filtered


def export_tree_json(tree, path):
    """Exports tree to a JSON file for external viewers."""
    if not tree or not tree.get("nodes"):
        return False

    nodes_out = []
    for node_id in sorted(tree["nodes"]):
        data = tree["nodes"][node_id]
        node_out = {
            "id": node_id,
            "g": data.get("g", 0),
            "h": data.get("h", 0),
            "f": data.get("f", 0),
            "goal": bool(data.get("goal")),
        }
        if data.get("state_label"):
            node_out["state_label"] = data.get("state_label")
        if data.get("player") is not None:
            node_out["player"] = data.get("player")
        if data.get("boxes") is not None:
            node_out["boxes"] = data.get("boxes")
        if data.get("move"):
            node_out["move"] = data.get("move")
        if "pushed" in data:
            node_out["pushed"] = bool(data.get("pushed"))
        nodes_out.append(node_out)

    edges_out = []
    for parent_id, child_id in tree.get("edges", []):
        edge_out = {"source": parent_id, "target": child_id}
        child = tree["nodes"].get(child_id, {})
        if child.get("move"):
            edge_out["move"] = child.get("move")
            edge_out["pushed"] = bool(child.get("pushed"))
        edges_out.append(edge_out)

    payload = {
        "root": tree.get("root"),
        "nodes": nodes_out,
        "edges": edges_out,
        "truncated": tree.get("truncated", False),
        "max_nodes": tree.get("max_nodes", 0),
        "max_edges": tree.get("max_edges", 0),
    }

    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2)
    return True


def export_tree_dot(tree, path):
    """Exports tree to Graphviz DOT format."""
    if not tree or not tree.get("nodes"):
        return False

    lines = []
    lines.append("digraph AStar {")
    lines.append("  rankdir=TB;")
    lines.append("  node [shape=circle, fontsize=10];")

    root = tree.get("root")
    nodes = tree["nodes"]
    edges = tree.get("edges", [])

    # Find the goal node
    goal_node = None
    for node_id, data in nodes.items():
        if data.get("goal") or data.get("h", 0) == 0:
            goal_node = node_id
            break

    # Build path edges and nodes from root to goal
    path_edges = set()
    path_nodes = set()
    if goal_node is not None:
        # Build child -> parent mapping
        child_to_parent = {}
        for parent_id, child_id in edges:
            child_to_parent[child_id] = parent_id
        # Trace back from goal to root
        current = goal_node
        while current != root and current in child_to_parent:
            parent = child_to_parent[current]
            path_edges.add((parent, current))
            path_nodes.add(current)
            current = parent
        path_nodes.add(root)
        path_nodes.add(goal_node)

    for node_id in sorted(nodes):
        data = nodes[node_id]
        state_label = data.get("state_label")
        if state_label:
            label = "S{0}\\n {1}\\n g={2} h={3} f={4}".format(
                node_id,
                state_label,
                data.get("g", 0),
                data.get("h", 0),
                data.get("f", 0),
            )
        else:
            label = "N{0}\\n g={1} h={2} f={3}".format(
                node_id,
                data.get("g", 0),
                data.get("h", 0),
                data.get("f", 0),
            )
        label = label.replace('"', '\\"')
        attrs = ['label="{0}"'.format(label)]
        is_goal = data.get("goal") or data.get("h", 0) == 0
        if is_goal:
            attrs.append("shape=doublecircle")
            attrs.append('style="filled"')
            attrs.append('fillcolor="#b6f2a1"')
        elif node_id == root:
            attrs.append('style="filled"')
            attrs.append('fillcolor="#b3d9ff"')
        elif node_id in path_nodes:
            attrs.append('style="filled"')
            attrs.append('fillcolor="orange"')
        lines.append("  n{0} [{1}];".format(node_id, ", ".join(attrs)))

    for parent_id, child_id in edges:
        child = nodes.get(child_id, {})
        move = child.get("move")
        pushed = child.get("pushed")
        edge_attrs = []
        if move:
            label_parts = [move]
            if pushed:
                label_parts.append("pousse")
            label_text = "{0} (cout 1)".format(" ".join(label_parts))
            label_text = label_text.replace('"', '\\"')
            edge_attrs.append('label="{0}"'.format(label_text))
        if (parent_id, child_id) in path_edges:
            edge_attrs.append('color="orange"')
            edge_attrs.append('penwidth=2')
        if edge_attrs:
            lines.append("  n{0} -> n{1} [{2}];".format(parent_id, child_id, ", ".join(edge_attrs)))
        else:
            lines.append("  n{0} -> n{1};".format(parent_id, child_id))

    lines.append("}")
    with open(path, "w") as handle:
        handle.write("\n".join(lines))
    return True
