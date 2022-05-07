# This Python file uses the following encoding: utf-8
import os
import re
import math
from pathlib import Path
import sys

from PySide2.QtGui import QCursor, QPainter, QPen, QColor, QRegion
from PySide2.QtWidgets import QApplication, QWidget, QPushButton
from PySide2.QtCore import QFile, QPoint, Qt, QRectF, QRect, QSize
from PySide2.QtUiTools import QUiLoader
from subprocess import check_call, check_output, CalledProcessError


def log(func):
    def func_wrapper(*args, **kwargs):
        print(f'{func.__name__}(args={args}, kwargs={kwargs}) triggered')
        return func(*args, **kwargs)
    return func_wrapper


class Xrandr:

    @staticmethod
    def list_monitors():
        output = check_output(["xrandr", "--listmonitors"]).decode('utf-8')
        return re.findall(r'\s+(\d+):\s+(\S+)\s+(\S+)\s*(\S*)\n', output, re.DOTALL)

    @staticmethod
    def del_monitor(name):
        try:
            check_call(["xrandr", "--delmonitor", f'PYR-{name}'])
            return True
        except CalledProcessError:
            return False

    @staticmethod
    def set_monitor(name, width, height, offset_x, offset_y, device='none'):
        try:
            check_call([
                "xrandr",
                "--setmonitor",
                f'PYR-{name}',
                f'{width}/1x{height}/1+{offset_x}+{offset_y}',
                device
            ])
        except CalledProcessError:
            return False


class VirtualDisplayManager:

    def __init__(self, main_window):
        self.main_window = main_window
        self.screen = app.primaryScreen()
        self.enabled_displays = dict(
            select_region=False,
            full_screen=False,
            right_half=False,
            left_half=False,
            left_third=False,
            center_third=False,
            right_third=False,
            top_left_quarter=False,
            top_right_quarter=False,
            bottom_left_quarter=False,
            bottom_right_quarter=False,
            top_left_sixth=False,
            top_center_sixth=False,
            top_right_sixth=False,
            bottom_left_sixth=False,
            bottom_center_sixth=False,
            bottom_right_sixth=False
        )
        self.rectangles = {}
        self.init_active_monitors()

    def init_active_monitors(self):
        for _, name, dimensions, _ in Xrandr.list_monitors():
            if name.startswith('PYR-') and name[4:] in self.enabled_displays:
                name = name.replace('PYR-', '')
                w, h, x, y = (int(i) for i in re.findall(r'(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)', dimensions)[0])
                self.draw_outline(name, w, h, x, y)
                self.set_state(name, True)

    def check_invalid_state(self, area, enabled):
        return enabled == self.enabled_displays[area]

    def set_state(self, area, enabled):
        if self.check_invalid_state(area, enabled):
            return False
        self.enabled_displays[area] = enabled
        self.main_window.findChild(QPushButton, f'push_button_{area}').setChecked(enabled)

        if not enabled and area in self.rectangles:
            self.rectangles[area].destroy()
            del self.rectangles[area]
        return True

    @property
    def screen_dimensions(self):
        return self.screen.size().width(), self.screen.size().height()

    @log
    def select_region(self, enabled):
        if not self.set_state('select_region', enabled):
            return

        if enabled:
            self.main_window.region_selector.start(self.complete_region_selection, self.cancel_region_selection)
        else:
            Xrandr.del_monitor('select_region')

    def complete_region_selection(self, start, end):
        self.rectangles['select_region'] = OutlineWidget(start, end)
        Xrandr.set_monitor('select_region', end.x() - start.x(), end.y() - start.y(), start.x(), start.y())

    def cancel_region_selection(self):
        self.set_state('select_region', False)

    @log
    def select_full_screen(self, enabled):
        if not self.set_state('full_screen', enabled):
            return

        if enabled:
            w, h = self.screen_dimensions
            Xrandr.set_monitor('full_screen', w, h, 0, 0)
            self.rectangles['full_screen'] = OutlineWidget(QPoint(0, 0), QPoint(w, h))
        else:
            Xrandr.del_monitor('full_screen')

    def divide_screen(self, parts):
        rows = 2 if parts > 3 else 1
        result = []

        w, h = self.screen_dimensions
        pw = math.ceil(w / parts * rows)
        ph = math.ceil(h / rows)

        for r in range(rows):
            result.append([])
            for c in range(parts // rows):
                result[r].append((pw, ph, pw * c, ph * r))

        return result

    def draw_outline(self, area, w, h, x, y):
        if area in self.rectangles:
            self.rectangles[area].destroy()
        self.rectangles[area] = OutlineWidget(QPoint(x, y), QPoint(x + w, y + h))

    @log
    def select_left_half(self, enabled):
        if not self.set_state('left_half', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(2)[0][0]
            Xrandr.set_monitor('left_half', *dimensions)
            self.draw_outline('left_half', *dimensions)
        else:
            Xrandr.del_monitor('left_half')

    @log
    def select_right_half(self, enabled):
        if not self.set_state('right_half', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(2)[0][1]
            Xrandr.set_monitor('right_half', *dimensions)
            self.draw_outline('right_half', *dimensions)
        else:
            Xrandr.del_monitor('right_half')

    @log
    def select_left_third(self, enabled):
        if not self.set_state('left_third', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(3)[0][0]
            Xrandr.set_monitor('left_third', *dimensions)
            self.draw_outline('left_third', *dimensions)
        else:
            Xrandr.del_monitor('left_third')

    @log
    def select_center_third(self, enabled):
        if not self.set_state('center_third', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(3)[0][1]
            Xrandr.set_monitor('center_third', *dimensions)
            self.draw_outline('center_third', *dimensions)
        else:
            Xrandr.del_monitor('center_third')

    @log
    def select_right_third(self, enabled):
        if not self.set_state('right_third', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(3)[0][2]
            Xrandr.set_monitor('right_third', *dimensions)
            self.draw_outline('right_third', *dimensions)
        else:
            Xrandr.del_monitor('right_third')

    @log
    def select_top_left_quarter(self, enabled):
        if not self.set_state('top_left_quarter', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(4)[0][0]
            Xrandr.set_monitor('top_left_quarter', *dimensions)
            self.draw_outline('top_left_quarter', *dimensions)
        else:
            Xrandr.del_monitor('top_left_quarter')

    @log
    def select_top_right_quarter(self, enabled):
        if not self.set_state('top_right_quarter', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(4)[0][1]
            Xrandr.set_monitor('top_right_quarter', *dimensions)
            self.draw_outline('top_right_quarter', *dimensions)
        else:
            Xrandr.del_monitor('top_right_quarter')

    @log
    def select_bottom_left_quarter(self, enabled):
        if not self.set_state('bottom_left_quarter', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(4)[1][0]
            Xrandr.set_monitor('bottom_left_quarter', *dimensions)
            self.draw_outline('bottom_left_quarter', *dimensions)
        else:
            Xrandr.del_monitor('bottom_left_quarter')

    @log
    def select_bottom_right_quarter(self, enabled):
        if not self.set_state('bottom_right_quarter', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(4)[1][1]
            Xrandr.set_monitor('bottom_right_quarter', *dimensions)
            self.draw_outline('bottom_right_quarter', *dimensions)
        else:
            Xrandr.del_monitor('bottom_right_quarter')

    @log
    def select_top_left_sixth(self, enabled):
        if not self.set_state('top_left_sixth', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(6)[0][0]
            Xrandr.set_monitor('top_left_sixth', *dimensions)
            self.draw_outline('top_left_sixth', *dimensions)
        else:
            Xrandr.del_monitor('top_left_sixth')

    @log
    def select_top_center_sixth(self, enabled):
        if not self.set_state('top_center_sixth', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(6)[0][1]
            Xrandr.set_monitor('top_center_sixth', *dimensions)
            self.draw_outline('top_center_sixth', *dimensions)
        else:
            Xrandr.del_monitor('top_center_sixth')

    @log
    def select_top_right_sixth(self, enabled):
        if not self.set_state('top_right_sixth', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(6)[0][2]
            Xrandr.set_monitor('top_right_sixth', *dimensions)
            self.draw_outline('top_right_sixth', *dimensions)
        else:
            Xrandr.del_monitor('top_right_sixth')

    @log
    def select_bottom_left_sixth(self, enabled):
        if not self.set_state('bottom_left_sixth', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(6)[1][0]
            Xrandr.set_monitor('bottom_left_sixth', *dimensions)
            self.draw_outline('bottom_left_sixth', *dimensions)
        else:
            Xrandr.del_monitor('bottom_left_sixth')

    @log
    def select_bottom_center_sixth(self, enabled):
        if not self.set_state('bottom_center_sixth', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(6)[1][1]
            Xrandr.set_monitor('bottom_center_sixth', *dimensions)
            self.draw_outline('bottom_center_sixth', *dimensions)
        else:
            Xrandr.del_monitor('bottom_center_sixth')

    @log
    def select_bottom_right_sixth(self, enabled):
        if not self.set_state('bottom_right_sixth', enabled):
            return

        if enabled:
            dimensions = self.divide_screen(6)[1][2]
            Xrandr.set_monitor('bottom_right_sixth', *dimensions)
            self.draw_outline('bottom_right_sixth', *dimensions)
        else:
            Xrandr.del_monitor('bottom_right_sixth')


class SnippingWidget(QWidget):
    is_snipping = False

    def __init__(self, parent=None):
        super(SnippingWidget, self).__init__()
        self.parent = parent
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        self.screen = app.primaryScreen()
        self.setGeometry(0, 0, self.screen.size().width(), self.screen.size().height())
        self.begin = QPoint()
        self.end = QPoint()
        self.onSnippingCompleted = None
        self.onSnippingCancelled = None

    def start(self, region_selected_callback=None, selection_cancelled_callback=None):
        SnippingWidget.is_snipping = True
        self.onSnippingCompleted = region_selected_callback
        self.onSnippingCancelled = selection_cancelled_callback
        self.parent.setWindowState(Qt.WindowMinimized)
        self.setWindowOpacity(0.3)
        QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
        self.setWindowState(Qt.WindowFullScreen)
        self.show()

    def paintEvent(self, event):
        if SnippingWidget.is_snipping:
            brush_color = (128, 128, 255, 100)
            lw = 3
            opacity = 0.3
        else:
            self.begin = QPoint()
            self.end = QPoint()
            brush_color = (0, 0, 0, 0)
            lw = 0
            opacity = 0

        self.setWindowOpacity(opacity)
        qp = QPainter(self)
        qp.setPen(QPen(QColor('black'), lw))
        qp.setBrush(QColor(*brush_color))
        rect = QRectF(self.begin, self.end)
        qp.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        SnippingWidget.is_snipping = False
        QApplication.restoreOverrideCursor()
        x1 = min(self.begin.x(), self.end.x())
        y1 = min(self.begin.y(), self.end.y())
        x2 = max(self.begin.x(), self.end.x())
        y2 = max(self.begin.y(), self.end.y())

        self.repaint()
        self.parent.setWindowState(Qt.WindowActive)
        QApplication.processEvents()

        if self.onSnippingCompleted is not None:
            self.onSnippingCompleted(QPoint(x1, y1), QPoint(x2, y2))

        self.onSnippingCompleted = None
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.restoreOverrideCursor()
            self.repaint()
            self.parent.setWindowState(Qt.WindowActive)
            QApplication.processEvents()
            self.onSnippingCompleted = None

            if self.onSnippingCancelled is not None:
                self.onSnippingCancelled()

            self.onSnippingCancelled = None
            self.close()


class OutlineWidget(QWidget):

    def __init__(self, start, end):
        super(OutlineWidget, self).__init__()
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(start.x(), start.y(), end.x() - start.x(), end.y() - start.y())
        self.start = start
        self.end = end
        self.show()

    @property
    def coordinates(self):
        return self.start.x(), self.start.y()

    @property
    def size(self):
        return self.end.x() - self.start.x(), self.end.y() - self.start.y()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor('red'), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRect(QPoint(*self.coordinates), QSize(*self.size)))
        painter.end()

    def resizeEvent(self, event):
        x, y = self.coordinates
        w, h = self.size
        r1 = QRegion(x, y, w, h, QRegion.Rectangle)
        r2 = QRegion(x+3, y+3, w - 6, h - 6, QRegion.Rectangle)
        self.setMask(r1.xored(r2))


class PyRandrWidget(QWidget):
    def __init__(self):
        super(PyRandrWidget, self).__init__()
        self.load_ui()
        self.manager = VirtualDisplayManager(self)
        self.connect_ui()
        self.region_selector = SnippingWidget(self)
        self.setWindowTitle('XranDream')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):
        sys.exit(0)

    def connect_ui(self):
        push_button_select_region = self.findChild(QPushButton, "push_button_select_region")
        push_button_select_region.toggled.connect(self.manager.select_region)

        push_button_full_screen = self.findChild(QPushButton, "push_button_full_screen")
        push_button_full_screen.toggled.connect(self.manager.select_full_screen)

        # Select half buttons
        push_button_right_half = self.findChild(QPushButton, "push_button_right_half")
        push_button_right_half.toggled.connect(self.manager.select_right_half)

        push_button_left_half = self.findChild(QPushButton, "push_button_left_half")
        push_button_left_half.toggled.connect(self.manager.select_left_half)

        # Select third buttons
        push_button_right_third = self.findChild(QPushButton, "push_button_right_third")
        push_button_right_third.toggled.connect(self.manager.select_right_third)

        push_button_center_third = self.findChild(QPushButton, "push_button_center_third")
        push_button_center_third.toggled.connect(self.manager.select_center_third)

        push_button_left_third = self.findChild(QPushButton, "push_button_left_third")
        push_button_left_third.toggled.connect(self.manager.select_left_third)

        # Select quarter buttons
        push_button_top_right_quarter = self.findChild(QPushButton, "push_button_top_right_quarter")
        push_button_top_right_quarter.toggled.connect(self.manager.select_top_right_quarter)

        push_button_bottom_right_quarter = self.findChild(QPushButton, "push_button_bottom_right_quarter")
        push_button_bottom_right_quarter.toggled.connect(self.manager.select_bottom_right_quarter)

        push_button_bottom_left_quarter = self.findChild(QPushButton, "push_button_bottom_left_quarter")
        push_button_bottom_left_quarter.toggled.connect(self.manager.select_bottom_left_quarter)

        push_button_top_left_quarter = self.findChild(QPushButton, "push_button_top_left_quarter")
        push_button_top_left_quarter.toggled.connect(self.manager.select_top_left_quarter)

        # Select sixth buttons
        push_button_top_left_sixth = self.findChild(QPushButton, "push_button_top_left_sixth")
        push_button_top_left_sixth.toggled.connect(self.manager.select_top_left_sixth)

        push_button_top_center_sixth = self.findChild(QPushButton, "push_button_top_center_sixth")
        push_button_top_center_sixth.toggled.connect(self.manager.select_top_center_sixth)

        push_button_top_right_sixth = self.findChild(QPushButton, "push_button_top_right_sixth")
        push_button_top_right_sixth.toggled.connect(self.manager.select_top_right_sixth)

        push_button_bottom_left_sixth = self.findChild(QPushButton, "push_button_bottom_left_sixth")
        push_button_bottom_left_sixth.toggled.connect(self.manager.select_bottom_left_sixth)

        push_button_bottom_center_sixth = self.findChild(QPushButton, "push_button_bottom_center_sixth")
        push_button_bottom_center_sixth.toggled.connect(self.manager.select_bottom_center_sixth)

        push_button_bottom_right_sixth = self.findChild(QPushButton, "push_button_bottom_right_sixth")
        push_button_bottom_right_sixth.toggled.connect(self.manager.select_bottom_right_sixth)

    def load_ui(self):
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()


if __name__ == "__main__":
    app = QApplication([])
    widget = PyRandrWidget()
    widget.show()
    sys.exit(app.exec_())
