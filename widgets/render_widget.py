from gui_utils import imgui_utils
from imgui_bundle import imgui


class RenderWidget:
    def __init__(self, viz):
        self.viz = viz
        self.render_alpha = False
        self.render_depth = False
        self.render_gan_image = False
        self.resolution = 1024

    @imgui_utils.scoped_by_object_id
    def __call__(self, show=True, decoder=False):
        viz = self.viz
        if show:
            imgui.text("Resolution")
            imgui.same_line(viz.label_w)
            _changed, self.resolution = imgui.input_int("##Resolution", self.resolution, 128)

            imgui.text("Render Alpha")
            imgui.same_line(viz.label_w)
            alpha_changed, self.render_alpha = imgui.checkbox("##RenderAlpha", self.render_alpha)

            imgui.text("Render Depth")
            imgui.same_line(viz.label_w)
            depth_changed, self.render_depth = imgui.checkbox("##RenderDepth", self.render_depth)
            if decoder:
                imgui.text("Render GAN")
                imgui.same_line(viz.label_w)
                _, self.render_gan_image = imgui.checkbox("##RenderGAN", self.render_gan_image)

            if self.render_alpha and alpha_changed:
                self.render_depth = False
            if self.render_depth and depth_changed:
                self.render_alpha = False

        viz.args.resolution = self.resolution
        viz.args.render_alpha = self.render_alpha
        viz.args.render_depth = self.render_depth
        viz.args.render_gan_image = self.render_gan_image
