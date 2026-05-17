import ast
import csv
import html
import json
import os
import random
import re
import shutil
from json import JSONDecodeError

import gradio as gr
from PIL import Image as PILImage, ImageDraw, ImageFont
from modules import scripts


# 拡張機能のルートディレクトリ
SCRIPT_DIR = scripts.basedir()

# データ保存用JSON
DATA_FILE = os.path.join(SCRIPT_DIR, "styles_v2.json")
BACKUP_FILE = DATA_FILE + ".bak"

# サムネイル保存用ディレクトリ
THUMB_DIR = os.path.join(SCRIPT_DIR, "thumbnails")


class AdvancedStyles(scripts.Script):
    def title(self):
        return "Advanced Styles Manager"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    # =========================================================================
    # Helpers
    # =========================================================================

    def log(self, message):
        print(f"[Advanced Styles] {message}")

    def ensure_thumb_dir(self):
        os.makedirs(THUMB_DIR, exist_ok=True)

    def sanitize_filename(self, name):
        name = str(name or "untitled").strip()
        name = re.sub(r'[\\/*?:"<>|]', "_", name)
        name = re.sub(r"\s+", " ", name)
        return name[:120] or "untitled"

    def get_thumb_path(self, group, style, create_dir=False):
        safe_group = self.sanitize_filename(group)
        safe_style = self.sanitize_filename(style)
        group_dir = os.path.join(THUMB_DIR, safe_group)

        if create_dir:
            os.makedirs(group_dir, exist_ok=True)

        return os.path.join(group_dir, f"{safe_style}.webp")

    def save_thumbnail(self, image, group, style):
        if image is None:
            return

        try:
            path = self.get_thumb_path(group, style, create_dir=True)
            img = image.copy() if hasattr(image, "copy") else image
            img.thumbnail((512, 512))
            img.save(path, format="WEBP", quality=90, method=6)
        except Exception as e:
            self.log(f"Error saving thumbnail: {e}")

    def load_thumbnail(self, group, style):
        path = self.get_thumb_path(group, style, create_dir=False)
        if os.path.exists(path):
            return path
        return None

    def delete_thumbnail_file(self, group, style):
        path = self.get_thumb_path(group, style, create_dir=False)

        if not os.path.exists(path):
            return

        try:
            os.remove(path)
            group_dir = os.path.dirname(path)
            if os.path.isdir(group_dir) and not os.listdir(group_dir):
                os.rmdir(group_dir)
        except Exception as e:
            self.log(f"Error deleting thumbnail: {e}")

    def create_placeholder_image(self, text):
        img = PILImage.new("RGB", (512, 512), color=(60, 60, 60))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        title = str(text or "No thumbnail")
        lines = [title[i : i + 32] for i in range(0, min(len(title), 96), 32)]
        if len(title) > 96 and lines:
            lines[-1] = lines[-1] + "..."

        y = 220
        for line in lines or ["No thumbnail"]:
            draw.text((24, y), line, fill=(200, 200, 200), font=font)
            y += 32

        return img

    # =========================================================================
    # Data
    # =========================================================================

    def normalize_styles_data(self, data):
        if not isinstance(data, dict) or not data:
            return {"default": {}}

        normalized = {}

        for group, styles in data.items():
            group_name = str(group or "default")

            if not isinstance(styles, dict):
                normalized[group_name] = {}
                continue

            normalized[group_name] = {}

            for style_name, style_data in styles.items():
                if not isinstance(style_data, dict):
                    style_data = {"prompt": str(style_data), "negative": ""}

                normalized[group_name][str(style_name)] = {
                    "prompt": str(style_data.get("prompt", "") or ""),
                    "negative": str(style_data.get("negative", "") or ""),
                }

        if not normalized:
            return {"default": {}}

        return normalized

    def load_json_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_styles(self):
        if not os.path.exists(DATA_FILE):
            return {"default": {}}

        try:
            data = self.load_json_file(DATA_FILE)
            return self.normalize_styles_data(data)
        except JSONDecodeError as e:
            self.log(f"JSON decode error in {DATA_FILE}: {e}")
        except Exception as e:
            self.log(f"Error loading {DATA_FILE}: {e}")

        if os.path.exists(BACKUP_FILE):
            try:
                self.log("Trying to load backup file.")
                data = self.load_json_file(BACKUP_FILE)
                return self.normalize_styles_data(data)
            except Exception as e:
                self.log(f"Error loading backup file: {e}")

        return {"default": {}}

    def save_styles_to_json(self, data):
        normalized = self.normalize_styles_data(data)
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

        tmp_file = DATA_FILE + ".tmp"

        if os.path.exists(DATA_FILE):
            try:
                shutil.copy2(DATA_FILE, BACKUP_FILE)
            except Exception as e:
                self.log(f"Backup failed: {e}")

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=4, ensure_ascii=False)

        os.replace(tmp_file, DATA_FILE)

    def get_groups(self):
        return sorted(list(self.load_styles().keys()))

    def get_styles_in_group(self, group):
        return sorted(list(self.load_styles().get(group, {}).keys()))

    def get_gallery_items(self, group):
        styles = self.get_styles_in_group(group)
        items = []

        for style_name in styles:
            thumb_path = self.load_thumbnail(group, style_name)
            if thumb_path:
                items.append((thumb_path, style_name))
            else:
                items.append((self.create_placeholder_image(style_name), style_name))

        return items

    def format_for_df(self, styles_list):
        styles_list = styles_list or []
        return [
            [
                str(style.get("group", "")),
                str(style.get("name", "")),
                str(style.get("prompt", "")),
                str(style.get("negative", "")),
            ]
            for style in styles_list
        ]

    def choice_label(self, value):
        """
        WebUIの日本語化がDropdownの選択肢を翻訳してしまう問題を避けるため、
        表示文字列の末尾にゼロ幅スペースを付与する。

        reForge環境のGradioでは (label, value) 形式のchoicesがそのまま表示される場合があるため、
        choicesには文字列だけを渡し、Python側でゼロ幅スペースを除去して元の値へ戻す。
        """
        if value is None:
            return None
        return f"{str(value)}\u200b"

    def normalize_ui_value(self, value):
        """
        Dropdownから返ってきた表示用文字列を、JSON上の実キーへ戻す。
        途中版でchoicesにタプルを渡した場合の値も一応吸収する。
        """
        if value is None:
            return None

        if isinstance(value, (list, tuple)) and len(value) >= 2:
            value = value[1]

        value = str(value)

        # 途中版のGradioで "('default\\u200b', 'default')" のような文字列が返る場合の保険。
        if value.startswith("(") and value.endswith(")"):
            try:
                parsed = ast.literal_eval(value)
                if isinstance(parsed, (list, tuple)) and len(parsed) >= 2:
                    value = str(parsed[1])
            except Exception:
                pass

        return value.replace("\u200b", "").strip()

    def choice_list(self, values):
        return [self.choice_label(value) for value in (values or [])]

    # =========================================================================
    # Import
    # =========================================================================

    def find_styles_csv(self):
        candidates = []

        # Stable Diffusion WebUIを起動したカレントディレクトリ
        candidates.append(os.path.abspath("styles.csv"))

        # 拡張機能ルートから見たWebUIルート想定
        candidates.append(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "styles.csv")))
        candidates.append(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "styles.csv")))

        seen = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            if os.path.exists(path):
                return path

        return None

    def import_csv_logic(self, target_group):
        csv_path = self.find_styles_csv()
        if not csv_path:
            return "Error: 'styles.csv' not found."

        target_group = str(target_group or "default").strip() or "default"

        current_data = self.load_styles()
        current_data.setdefault(target_group, {})

        count = 0

        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)

                for row in reader:
                    if not row:
                        continue

                    first_cell = str(row[0] or "").strip()
                    if not first_cell:
                        continue

                    if first_cell.lower() in {"id", "name"}:
                        continue

                    name = first_cell
                    prompt = row[1] if len(row) > 1 else ""
                    negative = row[2] if len(row) > 2 else ""

                    current_data[target_group][name] = {
                        "prompt": str(prompt or ""),
                        "negative": str(negative or ""),
                    }
                    count += 1

            self.save_styles_to_json(current_data)
            return f"Success: Imported {count} styles into '{html.escape(target_group)}' group."
        except Exception as e:
            return f"Error reading CSV: {html.escape(str(e))}"

    # =========================================================================
    # UI
    # =========================================================================

    def ui(self, is_img2img):
        self.ensure_thumb_dir()

        initial_data = self.load_styles()
        initial_groups = sorted(list(initial_data.keys())) or ["default"]
        default_group = initial_groups[0]
        initial_styles = sorted(list(initial_data.get(default_group, {}).keys()))
        default_style = initial_styles[0] if initial_styles else None
        initial_gallery_items = self.get_gallery_items(default_group)

        active_styles_state = gr.State([])
        selected_index_state = gr.State(None)

        tab_key = "img2img" if is_img2img else "txt2img"
        wrapper_id = f"advanced_styles_wrapper_{tab_key}"
        dataframe_id = f"adv_styles_dataframe_{tab_key}"
        import_note_id = f"adv_import_note_{tab_key}"

        with gr.Column(elem_id=wrapper_id):
            with gr.Accordion("Advanced Styles (Group & Order)", open=False):
                # =============================================================
                # Tab 1: Apply Styles
                # =============================================================
                with gr.Tab("Apply Styles"):
                    with gr.Row():
                        with gr.Column(scale=3):
                            with gr.Row(variant="compact"):
                                group_dd = gr.Dropdown(
                                    label="Group",
                                    choices=self.choice_list(initial_groups),
                                    value=self.choice_label(default_group),
                                    scale=4,
                                )
                                filter_txt = gr.Textbox(
                                    label="Filter Styles",
                                    placeholder="Search...",
                                    lines=1,
                                    scale=4,
                                )
                                refresh_btn = gr.Button(
                                    "↻",
                                    variant="secondary",
                                    scale=1,
                                    min_width=50,
                                )

                            with gr.Row(variant="compact"):
                                search_scope = gr.Radio(
                                    ["Current Group", "All Groups"],
                                    label="Scope",
                                    value="Current Group",
                                    scale=1,
                                )
                                search_target = gr.CheckboxGroup(
                                    ["Name", "Prompt"],
                                    label="Target",
                                    value=["Name"],
                                    scale=1,
                                )

                            style_dd = gr.Dropdown(
                                label="Style",
                                choices=self.choice_list(initial_styles),
                                value=self.choice_label(default_style),
                            )

                            with gr.Row():
                                add_btn = gr.Button("Add to Chain", variant="primary", scale=1)
                                add_group_random_btn = gr.Button(
                                    "🎲 Add Group (Random)",
                                    variant="secondary",
                                    scale=1,
                                )

                        with gr.Column(scale=1):
                            style_gallery = gr.Gallery(
                                label="Visual Selector (Click to Add)",
                                value=initial_gallery_items,
                                show_label=True,
                                columns=2,
                                height=300,
                                allow_preview=False,
                                interactive=False,
                            )

                    selected_display = gr.Dataframe(
                        headers=["Group", "Name", "Prompt", "Negative"],
                        datatype=["str", "str", "str", "str"],
                        label="Active Styles Chain",
                        interactive=False,
                        elem_id=dataframe_id,
                        wrap=True,
                    )

                    with gr.Row():
                        move_up_btn = gr.Button("↑ Up")
                        move_down_btn = gr.Button("↓ Down")
                        remove_btn = gr.Button("Remove Selected")
                        clear_btn = gr.Button("Clear All")

                # =============================================================
                # Tab 2: Manage Styles
                # =============================================================
                with gr.Tab("Manage Styles (Edit / Delete)"):
                    gr.Markdown("### Edit Existing or Create New")

                    with gr.Row():
                        with gr.Column(scale=3):
                            with gr.Row(variant="compact"):
                                edit_group_dd = gr.Dropdown(
                                    label="Select Group to Edit",
                                    choices=self.choice_list(initial_groups),
                                    value=self.choice_label(default_group),
                                    scale=2,
                                )
                                edit_filter_txt = gr.Textbox(
                                    label="Filter",
                                    placeholder="Search...",
                                    lines=1,
                                    scale=2,
                                )

                            with gr.Row(variant="compact"):
                                edit_search_scope = gr.Radio(
                                    ["Current Group", "All Groups"],
                                    label="Scope",
                                    value="Current Group",
                                )
                                edit_search_target = gr.CheckboxGroup(
                                    ["Name", "Prompt"],
                                    label="Target",
                                    value=["Name"],
                                )

                            with gr.Row():
                                edit_style_dd = gr.Dropdown(
                                    label="Select Style to Edit",
                                    choices=self.choice_list(initial_styles),
                                    value=self.choice_label(default_style),
                                    scale=3,
                                )
                                load_btn = gr.Button("Load Data", variant="secondary", scale=1)

                            gr.HTML('<hr style="border-top: 1px solid #444; margin: 10px 0;">')

                            with gr.Row():
                                save_group = gr.Dropdown(
                                    label="Target Group",
                                    choices=self.choice_list(initial_groups),
                                    value=self.choice_label(default_group),
                                    allow_custom_value=True,
                                    scale=1,
                                )
                                save_name = gr.Textbox(
                                    label="Style Name",
                                    scale=1,
                                    placeholder="Name",
                                )

                            save_prompt = gr.Textbox(label="Prompt", lines=3)
                            save_neg = gr.Textbox(label="Negative Prompt", lines=3)

                            with gr.Row():
                                save_btn = gr.Button("Save / Update", variant="primary")
                                delete_btn = gr.Button("Delete Style", variant="stop")
                                status_msg = gr.HTML(visible=False)

                        with gr.Column(scale=1):
                            manage_thumb_img = gr.Image(
                                label="Thumbnail (Upload/Paste)",
                                sources=["upload", "clipboard"],
                                type="pil",
                                height=250,
                            )

                    gr.HTML(
                        """
                        <div style="border-top: 1px solid #444; margin-top: 20px; margin-bottom: 10px;"></div>
                        <h3 style="margin: 0 0 5px 0;">Import Utilities</h3>
                        """
                    )

                    with gr.Row():
                        import_target_dd = gr.Dropdown(
                            label="Import to Group",
                            choices=self.choice_list(initial_groups),
                            value=self.choice_label(default_group),
                            allow_custom_value=True,
                            scale=1,
                        )
                        import_btn = gr.Button("Import from styles.csv", variant="secondary", scale=1)

                    gr.Markdown("NOTE: Imports from `styles.csv` in WebUI root.", elem_id=import_note_id)
                    import_status = gr.HTML(visible=False)

        # =========================================================================
        # UI Logic Helpers
        # =========================================================================

        def noop_updates(count):
            return [gr.update() for _ in range(count)]

        def parse_selection(selection, current_group):
            selection = self.normalize_ui_value(selection)
            current_group = self.normalize_ui_value(current_group)

            if selection and " :: " in selection:
                parts = str(selection).split(" :: ", 1)
                return self.normalize_ui_value(parts[0]), self.normalize_ui_value(parts[1])

            return current_group, selection

        def refresh_all_dropdowns(preferred_group=None, preferred_style=None, clear_filters=True):
            data = self.load_styles()
            groups = sorted(list(data.keys())) or ["default"]

            group_value = preferred_group if preferred_group in groups else groups[0]
            styles = sorted(list(data.get(group_value, {}).keys()))

            if preferred_style in styles:
                style_value = preferred_style
            else:
                style_value = styles[0] if styles else None

            gallery_items = self.get_gallery_items(group_value)
            filter_update = gr.update(value="") if clear_filters else gr.update()

            group_update = gr.update(choices=self.choice_list(groups), value=self.choice_label(group_value))
            style_update = gr.update(choices=self.choice_list(styles), value=self.choice_label(style_value))

            return (
                group_update,
                style_update,
                filter_update,
                gallery_items,
                gr.update(choices=self.choice_list(groups), value=self.choice_label(group_value)),
                gr.update(choices=self.choice_list(styles), value=self.choice_label(style_value)),
                filter_update,
                None,
                gr.update(choices=self.choice_list(groups), value=self.choice_label(group_value)),
                gr.update(choices=self.choice_list(groups), value=self.choice_label(group_value)),
            )

        # =========================================================================
        # Filter & Display
        # =========================================================================

        def apply_filter(current_group, query, scope, targets):
            current_group = self.normalize_ui_value(current_group)
            all_data = self.load_styles()
            candidates = []
            targets = targets or []
            query = str(query or "").strip()

            if scope == "All Groups":
                for group, styles in all_data.items():
                    for style_name, style_data in styles.items():
                        candidates.append((group, style_name, style_data))
            else:
                styles = all_data.get(current_group, {})
                for style_name, style_data in styles.items():
                    candidates.append((current_group, style_name, style_data))

            if not query:
                results = []
                for group, style_name, _style_data in candidates:
                    display = f"{group} :: {style_name}" if scope == "All Groups" else style_name
                    results.append(display)
                return gr.update(choices=self.choice_list(results), value=self.choice_label(results[0]) if results else None)

            filtered_results = []
            query_lower = query.lower()
            target_name = "Name" in targets
            target_prompt = "Prompt" in targets

            for group, style_name, style_data in candidates:
                match = False

                if target_name and query_lower in str(style_name).lower():
                    match = True

                if not match and target_prompt:
                    prompt_text = str(style_data.get("prompt", ""))
                    negative_text = str(style_data.get("negative", ""))
                    if query_lower in prompt_text.lower() or query_lower in negative_text.lower():
                        match = True

                if match:
                    display = f"{group} :: {style_name}" if scope == "All Groups" else style_name
                    filtered_results.append(display)

            return gr.update(
                choices=self.choice_list(filtered_results),
                value=self.choice_label(filtered_results[0]) if filtered_results else None,
            )

        filter_inputs = [group_dd, filter_txt, search_scope, search_target]
        filter_txt.change(fn=apply_filter, inputs=filter_inputs, outputs=[style_dd])
        search_scope.change(fn=apply_filter, inputs=filter_inputs, outputs=[style_dd])
        search_target.change(fn=apply_filter, inputs=filter_inputs, outputs=[style_dd])

        edit_filter_inputs = [edit_group_dd, edit_filter_txt, edit_search_scope, edit_search_target]
        edit_filter_txt.change(fn=apply_filter, inputs=edit_filter_inputs, outputs=[edit_style_dd])
        edit_search_scope.change(fn=apply_filter, inputs=edit_filter_inputs, outputs=[edit_style_dd])
        edit_search_target.change(fn=apply_filter, inputs=edit_filter_inputs, outputs=[edit_style_dd])

        def on_group_change(group):
            group = self.normalize_ui_value(group)
            styles = self.get_styles_in_group(group)
            first = styles[0] if styles else None
            gallery_items = self.get_gallery_items(group)
            return gr.update(choices=self.choice_list(styles), value=self.choice_label(first)), gallery_items

        group_dd.change(fn=on_group_change, inputs=[group_dd], outputs=[style_dd, style_gallery])

        def on_group_change_manage(group):
            group = self.normalize_ui_value(group)
            styles = self.get_styles_in_group(group)
            first = styles[0] if styles else None
            return gr.update(choices=self.choice_list(styles), value=self.choice_label(first))

        edit_group_dd.change(fn=on_group_change_manage, inputs=[edit_group_dd], outputs=[edit_style_dd])

        # =========================================================================
        # Add / Save / Load
        # =========================================================================

        def add(curr, group_value, style_value):
            curr = list(curr or [])

            if not style_value:
                return curr, self.format_for_df(curr)

            real_group, real_style = parse_selection(style_value, group_value)
            data = self.load_styles().get(real_group, {}).get(real_style)

            if data:
                curr.append(
                    {
                        "group": real_group,
                        "name": real_style,
                        "prompt": data.get("prompt", ""),
                        "negative": data.get("negative", ""),
                    }
                )

            return curr, self.format_for_df(curr)

        add_btn.click(
            fn=add,
            inputs=[active_styles_state, group_dd, style_dd],
            outputs=[active_styles_state, selected_display],
        )

        def on_gallery_select(curr, group_value, evt: gr.SelectData):
            curr = list(curr or [])
            group_value = self.normalize_ui_value(group_value)
            styles = self.get_styles_in_group(group_value)

            index = evt.index
            if isinstance(index, (list, tuple)):
                index = index[0]

            if isinstance(index, int) and 0 <= index < len(styles):
                style_name = styles[index]
                data = self.load_styles().get(group_value, {}).get(style_name)
                if data:
                    curr.append(
                        {
                            "group": group_value,
                            "name": style_name,
                            "prompt": data.get("prompt", ""),
                            "negative": data.get("negative", ""),
                        }
                    )

            return curr, self.format_for_df(curr)

        style_gallery.select(
            fn=on_gallery_select,
            inputs=[active_styles_state, group_dd],
            outputs=[active_styles_state, selected_display],
        )

        def load_style_data(group_value, style_value):
            if not style_value:
                return gr.update(), gr.update(), gr.update(), gr.update(), None

            real_group, real_style = parse_selection(style_value, group_value)
            data = self.load_styles().get(real_group, {}).get(real_style, {})
            thumb = self.load_thumbnail(real_group, real_style)

            return (
                real_group,
                real_style,
                data.get("prompt", ""),
                data.get("negative", ""),
                thumb,
            )

        edit_style_dd.change(
            fn=load_style_data,
            inputs=[edit_group_dd, edit_style_dd],
            outputs=[save_group, save_name, save_prompt, save_neg, manage_thumb_img],
        )
        load_btn.click(
            fn=load_style_data,
            inputs=[edit_group_dd, edit_style_dd],
            outputs=[save_group, save_name, save_prompt, save_neg, manage_thumb_img],
        )

        def on_select(evt: gr.SelectData):
            index = evt.index
            if isinstance(index, (list, tuple)):
                return index[0]
            if isinstance(index, int):
                return index
            return None

        selected_display.select(fn=on_select, inputs=[], outputs=[selected_index_state])

        def move_up(curr, index):
            curr = list(curr or [])

            if index is None or index <= 0 or index >= len(curr):
                return curr, self.format_for_df(curr), index

            curr[index], curr[index - 1] = curr[index - 1], curr[index]
            return curr, self.format_for_df(curr), index - 1

        move_up_btn.click(
            fn=move_up,
            inputs=[active_styles_state, selected_index_state],
            outputs=[active_styles_state, selected_display, selected_index_state],
        )

        def move_down(curr, index):
            curr = list(curr or [])

            if index is None or index < 0 or index >= len(curr) - 1:
                return curr, self.format_for_df(curr), index

            curr[index], curr[index + 1] = curr[index + 1], curr[index]
            return curr, self.format_for_df(curr), index + 1

        move_down_btn.click(
            fn=move_down,
            inputs=[active_styles_state, selected_index_state],
            outputs=[active_styles_state, selected_display, selected_index_state],
        )

        def remove_sel(curr, index):
            curr = list(curr or [])

            if index is None:
                if curr:
                    curr.pop()
            elif 0 <= index < len(curr):
                curr.pop(index)

            return curr, self.format_for_df(curr), None

        remove_btn.click(
            fn=remove_sel,
            inputs=[active_styles_state, selected_index_state],
            outputs=[active_styles_state, selected_display, selected_index_state],
        )

        def add_group_random(curr, group_value):
            curr = list(curr or [])
            group_value = self.normalize_ui_value(group_value)

            if not group_value:
                return curr, self.format_for_df(curr)

            display_name = f"<Random: {group_value}>"
            curr.append(
                {
                    "group": group_value,
                    "name": display_name,
                    "prompt": "__DYNAMIC_RANDOM__",
                    "negative": "__DYNAMIC_RANDOM__",
                }
            )

            return curr, self.format_for_df(curr)

        add_group_random_btn.click(
            fn=add_group_random,
            inputs=[active_styles_state, group_dd],
            outputs=[active_styles_state, selected_display],
        )

        def clear_all():
            return [], [], None

        clear_btn.click(
            fn=clear_all,
            outputs=[active_styles_state, selected_display, selected_index_state],
        )

        refresh_btn.click(
            fn=refresh_all_dropdowns,
            outputs=[
                group_dd,
                style_dd,
                filter_txt,
                style_gallery,
                edit_group_dd,
                edit_style_dd,
                edit_filter_txt,
                manage_thumb_img,
                save_group,
                import_target_dd,
            ],
        )

        def save_style(group, name, prompt, negative, image):
            group = self.normalize_ui_value(group)
            name = str(name or "").strip()

            if not group or not name:
                return (
                    gr.update(value="Error: Group and Name required.", visible=True),
                    *noop_updates(10),
                )

            data = self.load_styles()
            data.setdefault(group, {})
            data[group][name] = {
                "prompt": str(prompt or ""),
                "negative": str(negative or ""),
            }

            try:
                self.save_styles_to_json(data)
                if image is not None:
                    self.save_thumbnail(image, group, name)
            except Exception as e:
                return (
                    gr.update(value=f"Error: {html.escape(str(e))}", visible=True),
                    *noop_updates(10),
                )

            status = f"<b>Saved:</b> {html.escape(group)} / {html.escape(name)}"
            return (
                gr.update(value=status, visible=True),
                *refresh_all_dropdowns(preferred_group=group, preferred_style=name),
            )

        save_btn.click(
            fn=save_style,
            inputs=[save_group, save_name, save_prompt, save_neg, manage_thumb_img],
            outputs=[
                status_msg,
                group_dd,
                style_dd,
                filter_txt,
                style_gallery,
                edit_group_dd,
                edit_style_dd,
                edit_filter_txt,
                manage_thumb_img,
                save_group,
                import_target_dd,
            ],
        )

        def delete_style(group_value, style_value):
            real_group, real_style = parse_selection(style_value, group_value)

            if not real_group or not real_style:
                return (
                    gr.update(value="Error: Select style.", visible=True),
                    *noop_updates(10),
                )

            data = self.load_styles()

            if real_group in data and real_style in data[real_group]:
                del data[real_group][real_style]
                if not data[real_group]:
                    del data[real_group]

                try:
                    self.save_styles_to_json(data)
                    self.delete_thumbnail_file(real_group, real_style)
                except Exception as e:
                    return (
                        gr.update(value=f"Error: {html.escape(str(e))}", visible=True),
                        *noop_updates(10),
                    )

                status = f"<b style='color:red;'>Deleted:</b> {html.escape(real_group)} / {html.escape(real_style)}"
                return (
                    gr.update(value=status, visible=True),
                    *refresh_all_dropdowns(preferred_group=real_group),
                )

            return (
                gr.update(value="Error: Not found.", visible=True),
                *noop_updates(10),
            )

        delete_btn.click(
            fn=delete_style,
            inputs=[edit_group_dd, edit_style_dd],
            outputs=[
                status_msg,
                group_dd,
                style_dd,
                filter_txt,
                style_gallery,
                edit_group_dd,
                edit_style_dd,
                edit_filter_txt,
                manage_thumb_img,
                save_group,
                import_target_dd,
            ],
        )

        def do_import(target):
            target = self.normalize_ui_value(target) or "default"
            message = self.import_csv_logic(target)
            return (
                gr.update(value=message, visible=True),
                *refresh_all_dropdowns(preferred_group=target),
            )

        import_btn.click(
            fn=do_import,
            inputs=[import_target_dd],
            outputs=[
                import_status,
                group_dd,
                style_dd,
                filter_txt,
                style_gallery,
                edit_group_dd,
                edit_style_dd,
                edit_filter_txt,
                manage_thumb_img,
                save_group,
                import_target_dd,
            ],
        )

        return [active_styles_state]

    # =========================================================================
    # Apply styles on generation
    # =========================================================================

    def setup(self, p, active_styles):
        if not active_styles:
            return

        stored_data = self.load_styles()
        final_prompts = []
        final_negatives = []

        for style in active_styles:
            if not isinstance(style, dict):
                continue

            group = style.get("group")

            if style.get("prompt") == "__DYNAMIC_RANDOM__":
                group_styles = list(stored_data.get(group, {}).keys())

                if not group_styles:
                    continue

                chosen = random.choice(group_styles)
                chosen_data = stored_data[group][chosen]

                if chosen_data.get("prompt"):
                    final_prompts.append(chosen_data["prompt"])
                if chosen_data.get("negative"):
                    final_negatives.append(chosen_data["negative"])

                self.log(f"Randomly picked '{chosen}' from group '{group}'")
                continue

            if style.get("prompt"):
                final_prompts.append(style["prompt"])
            if style.get("negative"):
                final_negatives.append(style["negative"])

        combined_prompt = ", ".join([p for p in final_prompts if p])
        combined_negative = ", ".join([n for n in final_negatives if n])

        if combined_prompt:
            p.prompt = f"{p.prompt}, {combined_prompt}" if p.prompt else combined_prompt

        if combined_negative:
            p.negative_prompt = (
                f"{p.negative_prompt}, {combined_negative}"
                if p.negative_prompt
                else combined_negative
            )

        if combined_prompt or combined_negative:
            if getattr(p, "all_prompts", None):
                p.all_prompts = [p.prompt] * len(p.all_prompts)
            if getattr(p, "all_negative_prompts", None):
                p.all_negative_prompts = [p.negative_prompt] * len(p.all_negative_prompts)

        self.log(f"Setup applied {len(active_styles)} styles.")

    def process(self, p, active_styles):
        pass
