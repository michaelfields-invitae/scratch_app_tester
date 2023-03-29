from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt, QUrl, QObject, pyqtSignal
from PyQt5.QtWidgets import QLineEdit, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem

class LineEditDnD(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()

            urls_txt = event.mimeData().urls()[0].toLocalFile()

            self.setText(urls_txt)

            # For appending multiple files
            # if self.text() == "":
            #     self.setText(urls_txt)
            # else:
            #     self.setText(self.text() + "," + urls_txt)


class ListViewDnD(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.model = QStandardItemModel()
        self.setModel(self.model)
        self.selectionModel().selectionChanged.connect(
            self.handle_selection_changed
        )
        self.selected_item_index = None
        self.selected_item = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            urls_txt = event.mimeData().urls()

            for url in urls_txt:
                self.model.appendRow(QStandardItem(str(url.toLocalFile())))

    def handle_selection_changed(self):
        count = 0
        item = None

        for index in self.selectedIndexes():
            item = self.model.itemFromIndex(index)
            count += 1

        if item is not None:
            self.selected_item = item.text()
            self.selected_item_index = count
        else:
            self.selected_item = None
            self.selected_item_index = None

        # self.selected_item = item.text() if not None else None
        # self.selected_item_index = count if not None else None


class ListViewModel(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        self.setModel(self.model)
        self.selectionModel().selectionChanged.connect(
            self.handle_selection_changed
        )
        self.selected_item_index = None
        self.selected_item = None

    def handle_selection_changed(self):
        count = 0
        item = None

        for index in self.selectedIndexes():
            item = self.model.itemFromIndex(index)
            count += 1

        if item is not None:
            self.selected_item = item.text()
            self.selected_item_index = count
        else:
            self.selected_item = None
            self.selected_item_index = None