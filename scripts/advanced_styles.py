import os
import csv
import json
import random
import re
from PIL import Image as PILImage, ImageDraw, ImageFont
import gradio as gr
from modules import scripts

# 拡張機能のスクリプトディレクトリ
SCRIPT_DIR = scripts.basedir()
# データ保存用JSON
DATA_FILE = os.path.join(SCRIPT_DIR, "styles_v2.json")
# サムネイル保存用ディレクトリ
THUMB_DIR = os.path.join(SCRIPT_DIR, "thumbnails")

class AdvancedStyles(scripts.Script):
    def title(self):
        return "Advanced Styles Manager"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    # --- ヘルパー関数 ---
    def ensure_thumb_dir(self):
        if not os.path.exists(THUMB_DIR): os.makedirs(THUMB_DIR)

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', '_', name)

    def get_thumb_path(self, group, style):
        safe_group = self.sanitize_filename(group)
        safe_style = self.sanitize_filename(style)
        group_dir = os.path.join(THUMB_DIR, safe_group)
        if not os.path.exists(group_dir): os.makedirs(group_dir)
        return os.path.join(group_dir, f"{safe_style}.webp")

    def save_thumbnail(self, image, group, style):
        if image is None: return
        try:
            path = self.get_thumb_path(group, style)
            image.thumbnail((512, 512))
            image.save(path, format="WEBP")
        except Exception as e:
            print(f"[Advanced Styles] Error saving thumbnail: {e}")

    def load_thumbnail(self, group, style):
        path = self.get_thumb_path(group, style)
        if os.path.exists(path): return path
        return None

    def delete_thumbnail_file(self, group, style):
        path = self.get_thumb_path(group, style)
        if os.path.exists(path):
            try:
                os.remove(path)
                group_dir = os.path.dirname(path)
                if not os.listdir(group_dir): os.rmdir(group_dir)
            except: pass

    # サムネイルがない場合のプレースホルダー生成
    def create_placeholder_image(self, text):
        img = PILImage.new('RGB', (512, 512), color=(60, 60, 60))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        d.text((20, 240), text[:50], fill=(200, 200, 200), font=font)
        if len(text) > 50:
            d.text((20, 280), text[50:100] + "...", fill=(200, 200, 200), font=font)
            
        return img

    # --- データ操作 ---
    def load_styles(self):
        if not os.path.exists(DATA_FILE): return {"default": {}}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if data else {"default": {}}
        except: return {"default": {}}

    def save_styles_to_json(self, data):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_groups(self): return sorted(list(self.load_styles().keys()))
    def get_styles_in_group(self, group): return sorted(list(self.load_styles().get(group, {}).keys()))

    # --- インポート ---
    def import_csv_logic(self, target_group):
        webui_root = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
        csv_path = os.path.join(webui_root, "styles.csv")
        if not os.path.exists(csv_path): csv_path = "styles.csv"
        if not os.path.exists(csv_path): return "Error: 'styles.csv' not found."

        if not target_group: target_group = "default"
        
        current_data = self.load_styles()
        if target_group not in current_data: current_data[target_group] = {}

        count = 0
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 1: continue
                    if row[0].lower() == "id" or row[0] == "name": continue
                    name, prompt = row[0], row[1] if len(row) > 1 else ""
                    negative = row[2] if len(row) > 2 else ""
                    current_data[target_group][name] = {"prompt": prompt, "negative": negative}
                    count += 1
            self.save_styles_to_json(current_data)
            return f"Success: Imported {count} styles into '{target_group}' group."
        except Exception as e: return f"Error reading CSV: {str(e)}"

    # --- UI ---
    def ui(self, is_img2img):
        self.ensure_thumb_dir()
        initial_data = self.load_styles()
        initial_groups = sorted(list(initial_data.keys()))
        default_group = initial_groups[0] if initial_groups else "default"
        initial_styles = sorted(list(initial_data.get(default_group, {}).keys()))
        default_style = initial_styles[0] if initial_styles else None
        
        active_styles_state = gr.State([]) 
        selected_index_state = gr.State(None)

        # 【変更点】タブごとにIDをユニーク化する
        tab_key = "img2img" if is_img2img else "txt2img"
        unique_id = f"advanced_styles_wrapper_{tab_key}"

        with gr.Column(elem_id=unique_id):
            
            with gr.Accordion("Advanced Styles (Group & Order)", open=False):
                
                # =========================================================
                # Tab 1: Apply Styles
                # =========================================================
                with gr.Tab("Apply Styles"):
                    with gr.Row():
                        # --- 左カラム: 操作系 ---
                        with gr.Column(scale=3):
                            # 行1
                            with gr.Row(variant="compact"):
                                group_dd = gr.Dropdown(label="Group", choices=initial_groups, value=default_group, scale=4)
                                filter_txt = gr.Textbox(label="Filter Styles", placeholder="Search...", lines=1, scale=4)
                                refresh_btn = gr.Button("↻", variant="secondary", scale=1, min_width=50)

                            # 行2
                            with gr.Row(variant="compact"):
                                search_scope = gr.Radio(["Current Group", "All Groups"], label="Scope", value="Current Group", scale=1)
                                search_target = gr.CheckboxGroup(["Name", "Prompt"], label="Target", value=["Name"], scale=1)

                            # 行3
                            style_dd = gr.Dropdown(label="Style", choices=initial_styles, value=default_style)

                            # 行4
                            with gr.Row():
                                add_btn = gr.Button("Add to Chain", variant="primary", scale=1)
                                add_group_random_btn = gr.Button("🎲 Add Group (Random)", variant="secondary", scale=1)
                        
                        # --- 右カラム: ギャラリー ---
                        with gr.Column(scale=1):
                            style_gallery = gr.Gallery(label="Visual Selector (Click to Add)", show_label=True, columns=2, height=300, allow_preview=False, interactive=False)

                    # 登録済みチェーン一覧
                    selected_display = gr.Dataframe(
                        headers=["Group", "Name", "Prompt", "Negative"],
                        datatype=["str", "str", "str", "str"],
                        label="Active Styles Chain",
                        interactive=False,
                        elem_id="adv_styles_dataframe",
                        wrap=True
                    )
                    
                    with gr.Row():
                        move_up_btn = gr.Button("↑ Up")
                        move_down_btn = gr.Button("↓ Down")
                        remove_btn = gr.Button("Remove Selected")
                        clear_btn = gr.Button("Clear All")

                # =========================================================
                # Tab 2: Manage Styles
                # =========================================================
                with gr.Tab("Manage Styles (Edit / Delete)"):
                    gr.Markdown("### Edit Existing or Create New")
                    with gr.Row():
                        with gr.Column(scale=3):
                            with gr.Row(variant="compact"):
                                edit_group_dd = gr.Dropdown(label="Select Group to Edit", choices=initial_groups, value=default_group, scale=2)
                                edit_filter_txt = gr.Textbox(label="Filter", placeholder="Search...", lines=1, scale=2)
                            
                            with gr.Row(variant="compact"):
                                edit_search_scope = gr.Radio(["Current Group", "All Groups"], label="Scope", value="Current Group")
                                edit_search_target = gr.CheckboxGroup(["Name", "Prompt"], label="Target", value=["Name"])
                            
                            with gr.Row():
                                edit_style_dd = gr.Dropdown(label="Select Style to Edit", choices=initial_styles, value=default_style, scale=3)
                                load_btn = gr.Button("Load Data", variant="secondary", scale=1)

                            gr.HTML('<hr style="border-top: 1px solid #444; margin: 10px 0;">')
                            
                            with gr.Row():
                                save_group = gr.Dropdown(label="Target Group", choices=initial_groups, value=default_group, allow_custom_value=True, scale=1)
                                save_name = gr.Textbox(label="Style Name", scale=1, placeholder="Name")
                            
                            save_prompt = gr.Textbox(label="Prompt", lines=3)
                            save_neg = gr.Textbox(label="Negative Prompt", lines=3)
                            
                            with gr.Row():
                                save_btn = gr.Button("Save / Update", variant="primary")
                                delete_btn = gr.Button("Delete Style", variant="stop")
                                status_msg = gr.HTML(visible=False)
                        
                        with gr.Column(scale=1):
                            manage_thumb_img = gr.Image(label="Thumbnail (Upload/Paste)", sources=["upload", "clipboard"], type="pil", height=250)

                    # --- Import Section ---
                    gr.HTML("""
                        <div style="border-top: 1px solid #444; margin-top: 20px; margin-bottom: 10px;"></div>
                        <h3 style="margin: 0 0 5px 0;">Import Utilities</h3>
                    """)
                    with gr.Row():
                        import_target_dd = gr.Dropdown(label="Import to Group", choices=initial_groups, value=default_group, allow_custom_value=True, scale=1)
                        import_btn = gr.Button("Import from styles.csv", variant="secondary", scale=1)
                    
                    gr.Markdown("NOTE: Imports from `styles.csv` in WebUI root.", elem_id="adv_import_note")
                    import_status = gr.HTML(visible=False)

        # =========================================================================
        # Logic: Helper
        # =========================================================================
        def parse_selection(selection, current_group):
            if selection and " :: " in selection:
                parts = selection.split(" :: ", 1)
                return parts[0], parts[1]
            return current_group, selection
        
        def get_gallery_items(group):
            styles = self.get_styles_in_group(group)
            items = []
            for s in styles:
                thumb_path = self.load_thumbnail(group, s)
                if thumb_path:
                    items.append((thumb_path, s))
                else:
                    items.append((self.create_placeholder_image(s), s))
            return items

        # =========================================================================
        # Logic: Filter & Display
        # =========================================================================
        
        def apply_filter(current_group, query, scope, targets):
            all_data = self.load_styles()
            candidates = [] 
            if scope == "All Groups":
                for g, styles in all_data.items():
                    for s_name, s_data in styles.items():
                        candidates.append((g, s_name, s_data))
            else:
                styles = all_data.get(current_group, {})
                for s_name, s_data in styles.items():
                    candidates.append((current_group, s_name, s_data))
            
            if not query:
                results = []
                for g, n, d in candidates:
                    display = f"{g} :: {n}" if scope == "All Groups" else n
                    results.append(display)
                return gr.update(choices=results, value=results[0] if results else None)

            filtered_results = []
            query_lower = query.lower()
            target_name = "Name" in targets
            target_prompt = "Prompt" in targets
            
            for g, n, d in candidates:
                match = False
                if target_name and query_lower in n.lower(): match = True
                if not match and target_prompt:
                    if query_lower in d.get("prompt", "").lower() or query_lower in d.get("negative", "").lower():
                        match = True
                if match:
                    display = f"{g} :: {n}" if scope == "All Groups" else n
                    filtered_results.append(display)
            
            return gr.update(choices=filtered_results, value=filtered_results[0] if filtered_results else None)

        filter_inputs = [group_dd, filter_txt, search_scope, search_target]
        filter_txt.change(fn=apply_filter, inputs=filter_inputs, outputs=[style_dd])
        search_scope.change(fn=apply_filter, inputs=filter_inputs, outputs=[style_dd])
        search_target.change(fn=apply_filter, inputs=filter_inputs, outputs=[style_dd])

        edit_filter_inputs = [edit_group_dd, edit_filter_txt, edit_search_scope, edit_search_target]
        edit_filter_txt.change(fn=apply_filter, inputs=edit_filter_inputs, outputs=[edit_style_dd])
        edit_search_scope.change(fn=apply_filter, inputs=edit_filter_inputs, outputs=[edit_style_dd])
        edit_search_target.change(fn=apply_filter, inputs=edit_filter_inputs, outputs=[edit_style_dd])

        def on_group_change(g):
            styles = self.get_styles_in_group(g)
            first = styles[0] if styles else None
            gal_items = get_gallery_items(g)
            return gr.update(choices=styles, value=first), gal_items
        group_dd.change(fn=on_group_change, inputs=[group_dd], outputs=[style_dd, style_gallery])

        def on_group_change_manage(g):
            styles = self.get_styles_in_group(g)
            first = styles[0] if styles else None
            return gr.update(choices=styles, value=first)
        edit_group_dd.change(fn=on_group_change_manage, inputs=[edit_group_dd], outputs=[edit_style_dd])

        # =========================================================================
        # Logic: Add / Save / Load
        # =========================================================================

        def add(curr, g_val, s_val):
            if not s_val: return curr, self.format_for_df(curr)
            real_g, real_s = parse_selection(s_val, g_val)
            data = self.load_styles().get(real_g, {}).get(real_s)
            if data: 
                curr.append({"group": real_g, "name": real_s, "prompt": data.get("prompt",""), "negative": data.get("negative","")})
            return curr, self.format_for_df(curr)
        add_btn.click(fn=add, inputs=[active_styles_state, group_dd, style_dd], outputs=[active_styles_state, selected_display])

        def on_gallery_select(curr, g_val, evt: gr.SelectData):
            styles = self.get_styles_in_group(g_val)
            if evt.index is not None and evt.index < len(styles):
                s_name = styles[evt.index]
                data = self.load_styles().get(g_val, {}).get(s_name)
                if data:
                    curr.append({"group": g_val, "name": s_name, "prompt": data.get("prompt",""), "negative": data.get("negative","")})
            return curr, self.format_for_df(curr)
        style_gallery.select(fn=on_gallery_select, inputs=[active_styles_state, group_dd], outputs=[active_styles_state, selected_display])

        def load_style_data(g_val, s_val):
            if not s_val: return gr.update(), gr.update(), gr.update(), gr.update(), None
            real_g, real_s = parse_selection(s_val, g_val)
            data = self.load_styles().get(real_g, {}).get(real_s, {})
            thumb = self.load_thumbnail(real_g, real_s)
            return real_g, real_s, data.get("prompt", ""), data.get("negative", ""), thumb

        edit_style_dd.change(fn=load_style_data, inputs=[edit_group_dd, edit_style_dd], outputs=[save_group, save_name, save_prompt, save_neg, manage_thumb_img])
        load_btn.click(fn=load_style_data, inputs=[edit_group_dd, edit_style_dd], outputs=[save_group, save_name, save_prompt, save_neg, manage_thumb_img])

        def on_select(evt: gr.SelectData): return evt.index[0]
        selected_display.select(fn=on_select, inputs=[], outputs=[selected_index_state])

        def move_up(curr, idx):
            if idx is None or idx <= 0: return curr, self.format_for_df(curr), idx
            curr[idx], curr[idx-1] = curr[idx-1], curr[idx]
            return curr, self.format_for_df(curr), idx - 1
        move_up_btn.click(fn=move_up, inputs=[active_styles_state, selected_index_state], outputs=[active_styles_state, selected_display, selected_index_state])

        def move_down(curr, idx):
            if idx is None or idx >= len(curr) - 1: return curr, self.format_for_df(curr), idx
            curr[idx], curr[idx+1] = curr[idx+1], curr[idx]
            return curr, self.format_for_df(curr), idx + 1
        move_down_btn.click(fn=move_down, inputs=[active_styles_state, selected_index_state], outputs=[active_styles_state, selected_display, selected_index_state])

        def remove_sel(curr, idx):
            if idx is None: 
                if curr: curr.pop()
            elif 0 <= idx < len(curr): curr.pop(idx)
            return curr, self.format_for_df(curr), None
        remove_btn.click(fn=remove_sel, inputs=[active_styles_state, selected_index_state], outputs=[active_styles_state, selected_display, selected_index_state])
        
        def add_group_random(curr, g):
            if not g: return curr, self.format_for_df(curr)
            display_name = f"<Random: {g}>"
            curr.append({"group": g, "name": display_name, "prompt": "__DYNAMIC_RANDOM__", "negative": "__DYNAMIC_RANDOM__"})
            return curr, self.format_for_df(curr)
        add_group_random_btn.click(fn=add_group_random, inputs=[active_styles_state, group_dd], outputs=[active_styles_state, selected_display])
        
        clear_btn.click(fn=lambda: ([], [], None), outputs=[active_styles_state, selected_display, selected_index_state])

        def refresh_all_dropdowns():
            d = self.load_styles()
            groups = sorted(list(d.keys()))
            def_g = groups[0] if groups else "default"
            u_g = gr.update(choices=groups, value=def_g)
            styles = sorted(list(d.get(def_g, {}).keys()))
            u_s = gr.update(choices=styles, value=styles[0] if styles else None)
            gal = get_gallery_items(def_g)
            return u_g, u_s, gr.update(value=""), gal, u_g, u_s, gr.update(value=""), None, u_g, u_g

        refresh_btn.click(fn=refresh_all_dropdowns, outputs=[group_dd, style_dd, filter_txt, style_gallery, edit_group_dd, edit_style_dd, edit_filter_txt, manage_thumb_img, save_group, import_target_dd])

        def save_style(g, n, p, neg, img):
            if not g or not n: return gr.update(value="Error: Group and Name required.", visible=True), *([gr.update()]*10)
            d = self.load_styles()
            if g not in d: d[g] = {}
            d[g][n] = {"prompt": p, "negative": neg}
            self.save_styles_to_json(d)
            if img is not None: self.save_thumbnail(img, g, n)
            return gr.update(value=f"<b>Saved:</b> {g} / {n}", visible=True), *refresh_all_dropdowns()

        save_btn.click(fn=save_style, inputs=[save_group, save_name, save_prompt, save_neg, manage_thumb_img], outputs=[status_msg, group_dd, style_dd, filter_txt, style_gallery, edit_group_dd, edit_style_dd, edit_filter_txt, manage_thumb_img, save_group, import_target_dd])

        def delete_style(g_val, s_val):
            real_g, real_s = parse_selection(s_val, g_val)
            if not real_g or not real_s: return gr.update(value="Error: Select style.", visible=True), *([gr.update()]*10)
            d = self.load_styles()
            if real_g in d and real_s in d[real_g]:
                del d[real_g][real_s]
                if not d[real_g]: del d[real_g]
                self.save_styles_to_json(d)
                self.delete_thumbnail_file(real_g, real_s)
                return gr.update(value=f"<b style='color:red;'>Deleted:</b> {real_g} / {real_s}", visible=True), *refresh_all_dropdowns()
            return gr.update(value="Error: Not found.", visible=True), *([gr.update()]*10)

        delete_btn.click(fn=delete_style, inputs=[edit_group_dd, edit_style_dd], outputs=[status_msg, group_dd, style_dd, filter_txt, style_gallery, edit_group_dd, edit_style_dd, edit_filter_txt, manage_thumb_img, save_group, import_target_dd])

        def do_import(target):
            msg = self.import_csv_logic(target)
            return gr.update(value=msg, visible=True), *refresh_all_dropdowns()
        import_btn.click(fn=do_import, inputs=[import_target_dd], outputs=[import_status, group_dd, style_dd, filter_txt, style_gallery, edit_group_dd, edit_style_dd, edit_filter_txt, manage_thumb_img, save_group, import_target_dd])

        return [active_styles_state]

    def format_for_df(self, s_list): 
        return [[s["group"], s["name"], s["prompt"], s["negative"]] for s in s_list]

    def setup(self, p, active_styles):
        if not active_styles: return
        stored_data = self.load_styles()
        final_prompts, final_negatives = [], []

        for s in active_styles:
            group, name = s["group"], s["name"]
            if s.get("prompt") == "__DYNAMIC_RANDOM__":
                group_styles = list(stored_data.get(group, {}).keys())
                if group_styles:
                    chosen = random.choice(group_styles)
                    chosen_data = stored_data[group][chosen]
                    if chosen_data.get("prompt"): final_prompts.append(chosen_data["prompt"])
                    if chosen_data.get("negative"): final_negatives.append(chosen_data["negative"])
                    print(f"[Advanced Styles] Randomly picked '{chosen}' from group '{group}'")
            else:
                if s.get("prompt"): final_prompts.append(s["prompt"])
                if s.get("negative"): final_negatives.append(s["negative"])

        combined_prompt = ", ".join(final_prompts)
        combined_negative = ", ".join(final_negatives)

        if combined_prompt: p.prompt = f"{p.prompt}, {combined_prompt}" if p.prompt else combined_prompt
        if combined_negative: p.negative_prompt = f"{p.negative_prompt}, {combined_negative}" if p.negative_prompt else combined_negative

        if combined_prompt or combined_negative:
            if p.all_prompts: p.all_prompts = [p.prompt] * len(p.all_prompts)
            if p.all_negative_prompts: p.all_negative_prompts = [p.negative_prompt] * len(p.all_negative_prompts)

        print(f"[Advanced Styles] Setup applied {len(active_styles)} styles.")

    def process(self, p, active_styles): pass