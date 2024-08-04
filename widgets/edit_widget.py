import os.path
import time
import uuid
from dnnlib import EasyDict
from gui_utils import imgui_utils
import json
from imgui_bundle import imgui, imgui_color_text_edit as edit
import inspect

from scene.cameras import CustomCam
# from viz.gaussian_renderer import GaussianRenderer
from scene.gaussian_model import GaussianModel


default_preset = """gaussian._xyz = gaussian._xyz
gaussian._rotation = gaussian._rotation
gaussian._scaling = gaussian._scaling
gaussian._opacity = gaussian._opacity
gaussian._features_dc = gaussian._features_dc
gaussian._features_rest = gaussian._features_rest
self.bg_color[:] = 0
"""


def get_description(obj):
    attr_list = sorted(inspect.getmembers(obj), key=lambda x: x[0])
    res_string = str(obj.__name__) + "\n"
    for attr in attr_list:
        if attr[0].startswith("__"):
            continue
        res_string += "\t" + attr[0] + "\n"
    return res_string


class Slider(object):
    def __init__(self, key, value, min_value, max_value, _id=None):
        if _id is None:
            _id = str(uuid.uuid4())
        self.key = key
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self._id = _id

    def render(self):
        _changed, self.value = imgui.slider_float(
            self.key + f"##{self._id}",
            self.value,
            self.min_value,
            self.max_value,
        )


class EditWidget:
    def __init__(self, viz):
        self.viz = viz

        cur_time = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime())
        self.current_session_name = f"Restore Session {cur_time}"
        self.presets = {}
        self.history = {}
        self.history_size = 5
        self.load_presets()
        self.safe_load = False

        self.editor = edit.TextEditor()
        language = edit.TextEditor.LanguageDefinition.python()
        self.last_text = ""

        custom_identifiers = {
            # "self": edit.TextEditor.Identifier(m_declaration=get_description(GaussianRenderer)),
            "gaussian": edit.TextEditor.Identifier(m_declaration=get_description(GaussianModel)),
            "render_cam": edit.TextEditor.Identifier(m_declaration=get_description(CustomCam)),
            "render": edit.TextEditor.Identifier(
                m_declaration=get_description(
                    EasyDict(render=0, viewspace_points=0, visibility_filter=0, radii=0, alpha=0, depth=0)
                )
            ),
            "slider": edit.TextEditor.Identifier(m_declaration=get_description(Slider)),
        }

        copy_identifiers = language.m_identifiers.copy()
        copy_identifiers.update(custom_identifiers)
        language.m_identifiers = copy_identifiers
        self.editor.set_language_definition(language)
        self.editor.set_text(self.presets["Default"]["edit_text"])
        self.sliders = [Slider(**dict_values) for dict_values in self.presets["Default"]["slider"]]

        self.var_names = "xyzijklmnuvwabcdefghopqrst"
        self.var_name_index = 1
        self._cur_min_slider = -10
        self._cur_max_slider = 10
        self._cur_val_slider = 0
        self._cur_name_slider = self.var_names[self.var_name_index]
        self._cur_preset_name = ""

    @imgui_utils.scoped_by_object_id
    def __call__(self, show=True):
        viz = self.viz
        if show:
            self.render_sliders()
            imgui.new_line()

            _changed, self.safe_load = imgui.checkbox("Safe Load", self.safe_load)

            if imgui_utils.button("Browse Presets", width=self.viz.button_large_w):
                imgui.open_popup("browse_presets")
            if imgui.begin_popup("browse_presets"):
                for preset_key in sorted(self.presets.keys()):
                    clicked = imgui.menu_item_simple(preset_key)
                    if clicked:
                        edit_text = self.presets[preset_key]["edit_text"]
                        self.sliders = [Slider(**dict_values) for dict_values in self.presets[preset_key]["slider"]]

                        if self.safe_load:
                            edit_text = f"''' # REMOVE THIS LINE\n{edit_text}\n''' # REMOVE THIS LINE"
                        self.editor.set_text(edit_text)
                imgui.end_popup()

            imgui.same_line(viz.button_large_w * 2)
            if imgui_utils.button("Browse History", width=self.viz.button_large_w):
                imgui.open_popup("browse_history")
            if imgui.begin_popup("browse_history"):
                for history_key in sorted(self.history.keys()):
                    name = "Current Session" if history_key == self.current_session_name else history_key
                    clicked = imgui.menu_item_simple(name)
                    if clicked:
                        edit_text = self.history[history_key]["edit_text"]
                        self.sliders = [Slider(**dict_values) for dict_values in self.history[history_key]["slider"]]
                        if self.safe_load:
                            edit_text = f"''' # REMOVE THIS LINE\n{edit_text}\n''' # REMOVE THIS LINE"
                        self.editor.set_text(edit_text)
                imgui.end_popup()

            with imgui_utils.change_font(self.viz._imgui_fonts_code[self.viz._cur_font_size]):
                line_height = self.editor.get_total_lines() * viz._cur_font_size
                max_height = viz._cur_font_size * 30
                editor_height = min(line_height, max_height)
                self.editor.render("Python Edit Code", a_size=imgui.ImVec2(viz.pane_w - 50, editor_height))

            imgui.new_line()
            imgui.text("Preset Name")
            imgui.same_line()
            _changed, self._cur_preset_name = imgui.input_text("##preset_name", self._cur_preset_name)
            imgui.same_line()
            if imgui_utils.button("Save as Preset", width=self.viz.button_large_w):
                self.presets[self._cur_preset_name] = dict(
                    edit_text=self.editor.get_text(), slider=[vars(slider) for slider in self.sliders]
                )
                with open("./presets.json", "w", encoding="utf-8") as f:
                    json.dump(self.presets, f)
                self._cur_preset_name = ""

            edit_text = self.editor.get_text()
            if self.last_text != edit_text:
                self.history[self.current_session_name] = dict(
                    edit_text=self.editor.get_text(), slider=[vars(slider) for slider in self.sliders]
                )
                with open("./history.json", "w", encoding="utf-8") as f:
                    json.dump(self.history, f)
            self.last_text = edit_text

        viz.args.edit_text = self.last_text
        viz.args.update({slider.key: slider.value for slider in self.sliders})

    def load_presets(self):
        if not os.path.exists("./presets.json"):
            with open("./presets.json", "w", encoding="utf-8") as f:
                json.dump(dict(Default=dict(edit_text=default_preset, slider=[vars(Slider("x", 1, 0, 10))])), f)

        with open("./presets.json", "r", encoding="utf-8") as f:
            self.presets = json.load(f)

        if os.path.exists("./history.json"):
            with open("./history.json", "r", encoding="utf-8") as f:
                history_all = json.load(f)
                keys = sorted(history_all.keys())
                num_keep = min(len(keys), self.history_size)
                keys = keys[-num_keep:]
                self.history = {key: history_all[key] for key in keys}

    def render_sliders(self):
        delete_keys = []
        for i, slider in enumerate(self.sliders):
            slider.render()
            imgui.same_line()
            if imgui_utils.button("Remove " + slider.key + f"##{slider._id}"):
                delete_keys.append(i)

        for i in delete_keys[::-1]:
            del self.sliders[i]

        imgui.push_item_width(70)
        imgui.text("Var name")
        imgui.same_line()
        _changed, self._cur_name_slider = imgui.input_text("##input_name", self._cur_name_slider)

        imgui.same_line()
        imgui.text("min")
        imgui.same_line()
        _changed, self._cur_min_slider = imgui.input_int("##input_min", self._cur_min_slider, 0)

        imgui.same_line()
        imgui.text("val")
        imgui.same_line()
        _changed, self._cur_val_slider = imgui.input_int("##input_val", self._cur_val_slider, 0)

        imgui.same_line()
        imgui.text("max")
        imgui.same_line()
        _changed, self._cur_max_slider = imgui.input_int("##input_max", self._cur_max_slider, 0)
        imgui.pop_item_width()

        imgui.same_line()
        if imgui_utils.button("Add Slider", width=self.viz.button_w):
            self.sliders.append(
                Slider(
                    key=self._cur_name_slider,
                    value=self._cur_val_slider,
                    min_value=self._cur_min_slider,
                    max_value=self._cur_max_slider,
                )
            )
            self.var_name_index += 1
            self._cur_name_slider = self.var_names[self.var_name_index % len(self.var_names)]
