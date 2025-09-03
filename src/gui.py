import wx
import os
from pathlib import Path
from PIL import Image

import config
import annotator

class ImagePanel(wx.Panel):
    def __init__(self, parent, annotator):
        super().__init__(parent)
        self.image = None
        self.bitmap = None
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.dragging = False
        self.drag_start = (0, 0)
        self.annotator = annotator

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        self.SetBackgroundColour(wx.Colour(200, 200, 200))

    def load_image(self, path):
        self.annotator.load_image(path)
        self.image = self.annotator.masked_image
        self.update_bitmap()
        self.center_image()
        self.zoom_fit()

    def update_bitmap(self):
        if self.image is not None:
            h, w = self.image.shape[:2]
            wx_image = wx.Image(w, h)
            wx_image.SetData(self.image.tobytes())
            self.bitmap = wx.Bitmap(wx_image)
        else:
            self.bitmap = None

    def center_image(self):
        if self.bitmap:
            panel_w, panel_h = self.GetSize()
            img_w = int(self.bitmap.GetWidth() * self.zoom)
            img_h = int(self.bitmap.GetHeight() * self.zoom)
            self.offset_x = (panel_w - img_w) // 2
            self.offset_y = (panel_h - img_h) // 2

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        if self.bitmap:
            w = int(self.bitmap.GetWidth() * self.zoom)
            h = int(self.bitmap.GetHeight() * self.zoom)
            scaled = self.bitmap.ConvertToImage().Scale(w, h,
                                                        wx.IMAGE_QUALITY_HIGH)
            bmp = wx.Bitmap(scaled)
            x = int(self.offset_x)
            y = int(self.offset_y)
            dc.DrawBitmap(bmp, x, y, True)

            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0), width=1))
            radius = 4
            colors = [wx.Colour(255, 0, 0), wx.Colour(0, 255, 0)]
            for p, b in zip(self.annotator.points, self.annotator.labels):
                sx, sy = self.to_screen_coords(p[0], p[1])
                dc.SetBrush(wx.Brush(colors[b], wx.BRUSHSTYLE_SOLID))
                dc.DrawCircle(sx, sy, radius)

    def _panning(self):
        return not wx.GetKeyState(wx.WXK_SHIFT)

    def on_left_down(self, event):
        if self.image is not None:
            if self._panning():
                self.dragging = True
                self.drag_start = (event.GetX(), event.GetY())
                self.CaptureMouse()
            else:
                self.annotator.add_point(
                    self.to_image_coords(event.GetX(), event.GetY()), True)
                self.image = self.annotator.masked_image
                self.update_bitmap()
                self.Refresh()

    def on_left_up(self, event):
        if self.image is not None and self.dragging:
            self.dragging = False
            #self.center_image()
            if self.HasCapture():
                self.ReleaseMouse()
            self.Refresh()

    def on_right_down(self, event):
        if self.image is not None and not self._panning():
            self.annotator.add_point(
                self.to_image_coords(event.GetX(), event.GetY()), False)
            self.image = self.annotator.masked_image
            self.update_bitmap()
            self.Refresh()
            
    def on_motion(self, event):
        if self.dragging and event.Dragging() and event.LeftIsDown():
            dx = event.GetX() - self.drag_start[0]
            dy = event.GetY() - self.drag_start[1]
            self.offset_x += dx
            self.offset_y += dy
            self.drag_start = (event.GetX(), event.GetY())
            self.Refresh()

    def on_mousewheel(self, event):
        rotation = event.GetWheelRotation()
        if rotation > 0:
            self.zoom *= 1.1
        else:
            self.zoom /= 1.1
        self.center_image()
        self.Refresh()

    def zoom_in(self, event=None):
        self.zoom *= 1.1
        self.center_image()
        self.Refresh()

    def zoom_out(self, event=None):
        self.zoom /= 1.1
        self.center_image()
        self.Refresh()

    def zoom_1_1(self, event=None):
        self.zoom = 1.0
        self.center_image()
        self.Refresh()

    def zoom_fit(self, event=None):
        if self.bitmap:
            panel_w, panel_h = self.GetSize()
            img_w, img_h = self.bitmap.GetWidth(), self.bitmap.GetHeight()
            scale_w = panel_w / img_w
            scale_h = panel_h / img_h
            self.zoom = min(scale_w, scale_h)
            self.offset_x = (panel_w - img_w * self.zoom) // 2
            self.offset_y = (panel_h - img_h * self.zoom) // 2
            self.Refresh()

    def reset(self, clear_image=False):
        self.annotator.reset(clear_image)
        self.image = self.annotator.masked_image
        self.update_bitmap()
        self.Refresh()

    def undo(self):
        self.annotator.undo_last()
        self.image = self.annotator.masked_image
        self.update_bitmap()
        self.Refresh()        

    def to_image_coords(self, x, y):
        w = self.bitmap.GetWidth() * self.zoom
        h = self.bitmap.GetHeight() * self.zoom
        real_w, real_h = self.annotator.get_size()
        scale_w = real_w / w
        scale_h = real_h / h
        return (int(round((x - self.offset_x) * scale_w)),
                int(round((y - self.offset_y) * scale_h)))

    def to_screen_coords(self, x, y):
        w = self.bitmap.GetWidth() * self.zoom
        h = self.bitmap.GetHeight() * self.zoom
        real_w, real_h = self.annotator.get_size()
        scale_w = real_w / w
        scale_h = real_h / h
        return (int(round(x / scale_w + self.offset_x)),
                int(round(y / scale_h + self.offset_y)))

# end of class ImagePanel


class MainFrame(wx.Frame):
    def __init__(self, conf, annotator):
        super().__init__(None, title="SMART AI mask builder",
                         size=conf.window_size)

        self.annotator = annotator
        self.filename = None

        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("Ready")
        
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Menu Bar
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
        self.Bind(wx.EVT_MENU, self.on_open_image, open_item)
        file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q")
        menubar.Append(file_menu, "&File")
        self.SetMenuBar(menubar)

        # Toolbar
        toolbar = self.CreateToolBar()

        repl = b'#ffffff' if wx.SystemSettings.GetAppearance().IsDark() \
            else b'#000000'
        d = Path(__file__).resolve().parent.parent / 'icons'
        sz = wx.Size(16, 16)
        def svg(pth):
            with open(d / pth, 'rb') as f:
                data = f.read().replace(b'#2a7fff', repl)
                return wx.BitmapBundle.FromSVG(data, sz)

        tb_open = toolbar.AddTool(
            wx.ID_OPEN, "Open", svg('folder-open.svg'),
            shortHelp="Open image...")
        tb_save = toolbar.AddTool(
            wx.ID_SAVE, "Save", svg('save.svg'),
            shortHelp="Save mask...")
        tb_reset = toolbar.AddTool(
            wx.ID_ANY, "Reset", svg('undo-all.svg'),
            shortHelp="Remove all points")
        tb_undo = toolbar.AddTool(
            wx.ID_ANY, "Undo", svg('undo.svg'),
            shortHelp="Remove last added point")
        tb_zoom_in = toolbar.AddTool(
            wx.ID_ZOOM_IN, "Zoom In", svg('magnifier-plus.svg'),
            shortHelp="Zoom in")
        tb_zoom_out = toolbar.AddTool(
            wx.ID_ZOOM_OUT, "Zoom Out", svg('magnifier-minus.svg'),
            shortHelp="Zoom out")
        tb_zoom_1_1 = toolbar.AddTool(
            wx.ID_ANY, "Zoom 1:1", svg('magnifier-1to1.svg'),
            shortHelp="Zoom to 100%")
        tb_zoom_fit = toolbar.AddTool(
            wx.ID_ANY, "Zoom Fit", svg('magnifier-fit.svg'),
            shortHelp="Zoom to fit")
        toolbar.Realize()

        self.Bind(wx.EVT_TOOL, self.on_open_image, tb_open)
        self.Bind(wx.EVT_TOOL, self.panel_zoom_in, tb_zoom_in)
        self.Bind(wx.EVT_TOOL, self.panel_zoom_out, tb_zoom_out)
        self.Bind(wx.EVT_TOOL, self.panel_zoom_1_1, tb_zoom_1_1)
        self.Bind(wx.EVT_TOOL, self.panel_zoom_fit, tb_zoom_fit)
        self.Bind(wx.EVT_TOOL, self.on_save, tb_save)
        self.Bind(wx.EVT_TOOL, self.on_reset, tb_reset)
        self.Bind(wx.EVT_TOOL, self.on_undo, tb_undo)

        # Main layout
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.image_panel = ImagePanel(self, annotator)
        hbox.Add(self.image_panel, proportion=1, flag=wx.EXPAND)

        vbox.Add(hbox, proportion=1, flag=wx.EXPAND)
        self.SetSizer(vbox)
        self.Raise()

    def on_open_image(self, event):
        with wx.FileDialog(
                self, "Open Image file",
                wildcard="Image files (*.png;*.jpg;*.jpeg;*.tif;*.tiff)" \
                "|*.png;*.jpg;*.jpeg;*.tif;*.tiff",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            self.load_image(fd.GetPath())

    def load_image(self, path):
        try:
            self.image_panel.load_image(path)
            self.filename = Path(self.annotator.image_filename)
            self.statusbar.SetStatusText(f"loaded image: {self.filename}")
        except Exception as e:
            self.image_panel.reset(True)
            wx.MessageDialog(self, f"Error loading image:\n{e}",
                             "Load Error",
                             wx.OK | wx.ICON_ERROR).ShowModal()        

    def panel_zoom_in(self, event):
        self.image_panel.zoom_in()

    def panel_zoom_out(self, event):
        self.image_panel.zoom_out()

    def panel_zoom_1_1(self, event):
        self.image_panel.zoom_1_1()

    def panel_zoom_fit(self, event):
        self.image_panel.zoom_fit()

    def on_save(self, event):
        if self.filename is None:
            self.statusbar.SetStatusText("No mask to save")
            return
        dd = str(self.filename.parent)
        df = str(self.filename.stem + "_mask.png")
        with wx.FileDialog(self, "Save Mask",
                           wildcard="PNG files (*.png)|*.png",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                           defaultDir=dd, defaultFile=df) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            path = fd.GetPath()
            try:
                self.annotator.save_mask(path)
                self.statusbar.SetStatusText(f"mask saved to {path}")
            except Exception as e:
                wx.MessageDialog(self, f"Error saving mask:\n{e}",
                                 "Save Error",
                                 wx.OK | wx.ICON_ERROR).ShowModal()

    def on_reset(self, event):
        self.image_panel.reset()

    def on_undo(self, event):
        self.image_panel.undo()

# end of class MainFrame


def main(conf, filename=None):
    app = wx.App(False)
    ann = annotator.Annotator(conf)
    frame = MainFrame(conf, ann)
    frame.Show()
    if filename is not None:
        wx.CallAfter(lambda : frame.load_image(filename))
    app.MainLoop()
