# HkbEditor v0.21.0 template
# Bind Slowenemy to playbackSpeed on every hkbClipGenerator without
# overwriting a pre-existing playbackSpeed binding.

from hkb_editor.templates import *


VARIABLE_NAME = "Slowenemy"
VARIABLE_INDEX = 199
TARGET_BINDING_SET_ID = "object10356"
MEMBER_PATH = "playbackSpeed"


def _get_name(ctx: TemplateContext, clip):
    name = ctx.get(clip, "name", default="")
    return name if name else "<Unnamed>"


def _get_animation_name(ctx: TemplateContext, clip):
    return ctx.get(clip, "animationName", default="")


def _find_path_bindings(binding_set, member_path):
    return [
        binding
        for binding in binding_set["bindings"]
        if binding["memberPath"].get_value() == member_path
    ]


def _validate_variable(ctx: TemplateContext):
    # create=False guarantees that this template never registers a variable.
    try:
        variable = ctx.variable(VARIABLE_NAME, create=False)
    except (ValueError, IndexError):
        print(f"ERROR: Variable '{VARIABLE_NAME}' was not found.")
        return None

    if variable.index != VARIABLE_INDEX:
        print(
            f"ERROR: Variable '{VARIABLE_NAME}' uses index {variable.index}, "
            f"expected {VARIABLE_INDEX}."
        )
        return None

    return variable


def _validate_target_binding_set(ctx: TemplateContext):
    target = ctx.resolve_object(TARGET_BINDING_SET_ID)
    if target is None:
        print(f"ERROR: {TARGET_BINDING_SET_ID} was not found.")
        return None

    if target.type_name != "hkbVariableBindingSet":
        print(
            f"ERROR: {TARGET_BINDING_SET_ID} is {target.type_name}, "
            "expected hkbVariableBindingSet."
        )
        return None

    path_bindings = _find_path_bindings(target, MEMBER_PATH)
    if len(path_bindings) != 1:
        print(
            f"ERROR: {TARGET_BINDING_SET_ID} must contain exactly one "
            f"binding for '{MEMBER_PATH}', found {len(path_bindings)}."
        )
        return None

    target_index = path_bindings[0]["variableIndex"].get_value()
    if target_index != VARIABLE_INDEX:
        print(
            f"ERROR: {TARGET_BINDING_SET_ID} binds '{MEMBER_PATH}' to "
            f"variable index {target_index}, expected {VARIABLE_INDEX}."
        )
        return None

    return target


def _binding_set_key(binding_set):
    # hkbVariableBindingSet objects should have an object ID. The fallback keeps
    # the scan safe even if an unusual file contains an anonymous record.
    return binding_set.object_id or id(binding_set)


def run(ctx: TemplateContext):
    """
    Bind Slowenemy (index 199) to playbackSpeed on every hkbClipGenerator
    while preserving all pre-existing bindings.

    The template performs a full preflight scan first. If a clip already binds
    playbackSpeed to another variable, no changes are made because HkbEditor's
    documented bind_variable behavior would replace that binding.
    """
    variable = _validate_variable(ctx)
    if variable is None:
        return

    target = _validate_target_binding_set(ctx)
    if target is None:
        return

    clips = ctx.find_all("type=hkbClipGenerator")
    if not clips:
        print("No hkbClipGenerator nodes found. No changes were made.")
        return

    animation_names = {
        animation_name
        for clip in clips
        if (animation_name := _get_animation_name(ctx, clip))
    }

    unbound_clips = []
    sets_to_extend = {}
    extendable_clip_count = 0
    clips_with_binding_before = 0
    clips_with_non_target_binding_before = 0
    clips_already_using_target = 0
    already_bound = 0
    conflicts = []
    scan_errors = []
    existing_set_keys = set()
    non_target_set_keys = set()

    # Preflight only: do not modify anything in this loop.
    for clip in clips:
        name = _get_name(ctx, clip)
        binding_set_ptr = clip.get_field("variableBindingSet", default=None)

        if binding_set_ptr is None:
            scan_errors.append(
                f"{name} (ID: {clip.object_id}) does not expose variableBindingSet"
            )
            continue

        binding_set_id = binding_set_ptr.get_value()
        if not binding_set_id:
            unbound_clips.append(clip)
            continue

        clips_with_binding_before += 1

        try:
            existing_set = binding_set_ptr.get_target()
        except KeyError:
            existing_set = None

        if existing_set is None:
            scan_errors.append(
                f"{name} (ID: {clip.object_id}) has a dangling "
                f"variableBindingSet reference: {binding_set_id}"
            )
            continue

        set_key = _binding_set_key(existing_set)
        existing_set_keys.add(set_key)

        if existing_set.object_id == target.object_id:
            clips_already_using_target += 1
        else:
            clips_with_non_target_binding_before += 1
            non_target_set_keys.add(set_key)

        path_bindings = _find_path_bindings(existing_set, MEMBER_PATH)
        if not path_bindings:
            extendable_clip_count += 1
            # Extend each shared binding-set object only once. This avoids
            # duplicate entries when several clips reuse the same object.
            sets_to_extend.setdefault(set_key, (existing_set, clip))
            continue

        existing_indices = [
            binding["variableIndex"].get_value() for binding in path_bindings
        ]
        if len(path_bindings) == 1 and existing_indices[0] == VARIABLE_INDEX:
            already_bound += 1
            continue

        conflicts.append(
            (
                name,
                clip.object_id,
                existing_set.object_id,
                existing_indices,
            )
        )

    print("Preflight summary:")
    print(f"  hkbClipGenerator nodes: {len(clips)}")
    print(f"  Unique non-empty animationName values: {len(animation_names)}")
    print(f"  Clips with any variableBindingSet before run: {clips_with_binding_before}")
    print(f"  Clips without variableBindingSet before run: {len(unbound_clips)}")
    print(
        "  Clips with a pre-existing non-target binding set: "
        f"{clips_with_non_target_binding_before}"
    )
    print(f"  Unique binding-set objects already referenced: {len(existing_set_keys)}")
    print(f"  Unique non-target binding-set objects: {len(non_target_set_keys)}")
    print(f"  Clips already using {TARGET_BINDING_SET_ID}: {clips_already_using_target}")
    print(f"  Clips already bound to variable index {VARIABLE_INDEX}: {already_bound}")
    print(f"  Clips whose existing set can be safely extended: {extendable_clip_count}")
    print(f"  Unique existing sets to extend: {len(sets_to_extend)}")
    print(f"  Conflicting playbackSpeed bindings: {len(conflicts)}")
    print(f"  Scan errors: {len(scan_errors)}")

    if conflicts:
        print("Conflicts detected; no changes were made.")
        print(
            "A playbackSpeed path can only be safely assigned to one variable "
            "through the documented bind_variable operation."
        )
        for name, clip_id, binding_set_id, indices in conflicts:
            print(
                f"  [CONFLICT] {name} (ID: {clip_id}) | "
                f"variableBindingSet: {binding_set_id} | "
                f"playbackSpeed variable indices: {indices}"
            )
        return

    if scan_errors:
        print("Scan errors detected; no changes were made.")
        for message in scan_errors:
            print(f"  [ERROR] {message}")
        return

    linked_to_target = 0
    extended_sets = 0
    errors = 0

    # Clips with no binding set can safely share the user's prepared object.
    for clip in unbound_clips:
        name = _get_name(ctx, clip)
        try:
            clip["variableBindingSet"].set_value(target)
            linked_to_target += 1
            print(
                f"[LINKED] {name} (ID: {clip.object_id}) -> "
                f"{TARGET_BINDING_SET_ID}"
            )
        except (KeyError, ValueError, AttributeError) as exc:
            errors += 1
            print(f"[ERROR] {name} (ID: {clip.object_id}): {exc}")

    # Existing binding sets are preserved. bind_variable is only called after
    # confirming that playbackSpeed is absent, so it appends rather than
    # replacing an original binding.
    for existing_set, representative_clip in sets_to_extend.values():
        name = _get_name(ctx, representative_clip)
        try:
            result_set = ctx.bind_variable(
                representative_clip,
                MEMBER_PATH,
                variable,
            )
            extended_sets += 1
            print(
                f"[EXTENDED] variableBindingSet {result_set.object_id} "
                f"(representative clip: {name}, ID: "
                f"{representative_clip.object_id})"
            )
        except (KeyError, ValueError, AttributeError, IndexError) as exc:
            errors += 1
            print(
                f"[ERROR] Could not extend variableBindingSet "
                f"{existing_set.object_id}: {exc}"
            )

    print("Binding summary:")
    print(f"  Clips linked to {TARGET_BINDING_SET_ID}: {linked_to_target}")
    print(f"  Existing binding-set objects extended: {extended_sets}")
    print(f"  Clips covered by those extended sets: {extendable_clip_count}")
    print(f"  Clips already correctly bound: {already_bound}")
    print(f"  Errors while applying changes: {errors}")
    print(f"  Total hkbClipGenerator nodes: {len(clips)}")
